"""Tests for the Gmail read tool — the graceful, no-network path.

Only pins the "never crash a turn" contract: when Google isn't connected (or the
libs aren't installed), list_recent_emails returns a readable setup hint, not an
exception. The shared OAuth is tested in test_google_auth.
"""

from __future__ import annotations

import pytest

from agent.tools import gmail, google_auth


def test_list_emails_returns_hint_when_not_connected(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("EAF_HOME", str(tmp_path))
    monkeypatch.setattr(google_auth, "load_credentials", lambda: None)
    out = gmail.list_recent_emails.invoke({})
    assert "not connected" in out.lower() or "not installed" in out.lower()


def test_header_lookup_is_case_insensitive() -> None:
    headers = [{"name": "From", "value": "a@x.com"}, {"name": "subject", "value": "Hi"}]
    assert gmail._header(headers, "from") == "a@x.com"
    assert gmail._header(headers, "Subject") == "Hi"
    assert gmail._header(headers, "Date") == ""


# ── list vs read: honesty about previews, full bodies, quoted history ────────

import base64  # noqa: E402


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


class _Exec:
    def __init__(self, value: object) -> None:
        self._value = value

    def execute(self) -> object:
        return self._value


class _Messages:
    def __init__(self, listing: dict, messages: dict) -> None:
        self._listing, self._messages = listing, messages

    def list(self, **_: object) -> _Exec:
        return _Exec(self._listing)

    def get(self, *, id: str, **_: object) -> _Exec:  # noqa: A002 — Gmail's kwarg name
        return _Exec(self._messages[id])


class _Service:
    def __init__(self, listing: dict, messages: dict) -> None:
        self._m = _Messages(listing, messages)

    def users(self) -> _Service:
        return self

    def messages(self) -> _Messages:
        return self._m


def _fake(monkeypatch: pytest.MonkeyPatch, listing: dict, messages: dict) -> None:
    monkeypatch.setattr(gmail, "_service", lambda: (_Service(listing, messages), None))


def _hdrs(**kv: str) -> list[dict]:
    return [{"name": k, "value": v} for k, v in kv.items()]


def test_list_rows_carry_ids_and_say_previews_are_not_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    msg = {
        "snippet": "Thanks for the offer",
        "payload": {"headers": _hdrs(From="me", Subject="Re: offer")},
    }
    _fake(monkeypatch, {"messages": [{"id": "abc"}], "nextPageToken": "t"}, {"abc": msg})
    out = gmail.list_recent_emails.invoke({"query": "to:simon"})
    assert out.startswith("abc | me |")
    assert "Previews only" in out
    assert "MORE exist" in out  # capped results are declared, not hidden


def test_read_email_returns_full_body_without_quoted_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = (
        "Hi Simon,\nI accept the offer.\n\nOn Mon, 14 Sep 2026, Simon <s@x.com> wrote:\n> old text"
    )
    msg = {
        "payload": {
            "headers": _hdrs(From="me", To="Simon", Subject="Re: offer"),
            "mimeType": "multipart/alternative",
            "parts": [{"mimeType": "text/plain", "body": {"data": _b64(body)}}],
        }
    }
    _fake(monkeypatch, {}, {"abc": msg})
    out = gmail.read_email.invoke({"message_id": "abc"})
    assert "I accept the offer." in out
    assert "old text" not in out
    assert "quoted messages" in out


def test_read_email_falls_back_to_html_and_truncates_with_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    big = "<p>" + ("word " * 3000) + "</p>"
    msg = {"payload": {"headers": [], "mimeType": "text/html", "body": {"data": _b64(big)}}}
    _fake(monkeypatch, {}, {"abc": msg})
    out = gmail.read_email.invoke({"message_id": "abc"})
    assert "<p>" not in out
    assert "truncated at 8000" in out
