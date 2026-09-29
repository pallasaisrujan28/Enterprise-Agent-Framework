"""Tests for the shared Google OAuth module — no network, no OAuth, no browser.

Pins the "never crash a turn" contract and the security-relevant bits: EAF_HOME
is honoured, is_connected is side-effect free, connect degrades to a sentence
without credentials/libs, and the cached token is written owner-only (0600) —
it holds a refresh token.
"""

from __future__ import annotations

import stat

import pytest

from agent.tools import google_auth as ga


def test_eaf_home_honours_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("EAF_HOME", str(tmp_path))
    assert ga.eaf_home() == tmp_path


def test_is_connected_false_without_token(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("EAF_HOME", str(tmp_path))
    assert ga.is_connected() is False


def test_connect_without_credentials_is_graceful(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("EAF_HOME", str(tmp_path))
    out = ga.connect()
    assert "oauth client" in out.lower() or "not installed" in out.lower()


def test_write_token_is_owner_only(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The cached token holds a refresh token — it must be 0600 (owner-only)."""
    monkeypatch.setenv("EAF_HOME", str(tmp_path))

    class _FakeCreds:
        def to_json(self) -> str:
            return '{"refresh_token": "secret"}'

    ga._write_token(_FakeCreds())
    token = ga.token_path()
    assert token.exists()
    assert stat.S_IMODE(token.stat().st_mode) == 0o600


def test_scopes_are_readonly() -> None:
    """Every granted scope must be a readonly scope — the agent never writes."""
    assert all("readonly" in s for s in ga.SCOPES)
    assert any("calendar" in s for s in ga.SCOPES)
    assert any("gmail" in s for s in ga.SCOPES)
