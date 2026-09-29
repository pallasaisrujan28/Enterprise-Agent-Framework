"""Gmail — read the user's email so the agent can answer "what's in my inbox?",
"any email from X?", "what exactly did I send to Y?".

Shares the Google OAuth in agent/tools/google_auth.py with the calendar tool —
one sign-in grants both read scopes, so if calendar is connected, email is too.

LIST vs READ, the waku pattern (waku/tools/github.py: compact list rows, full
`view` text truncated with an explicit notice):
  list_recent_emails  compact rows — id, from, to, subject, date, a SHORT preview.
                      It says plainly that previews are not the full message and
                      when more results exist than were returned.
  read_email          the full plain-text body of ONE message, truncated with an
                      explicit notice. This is the only source of "exact content".
The split is what stops fabrication: before it, the list tool returned 140-char
snippets and the model presented 18 "exact" emails it had never read.

READ-ONLY (gmail.readonly). Best-effort and never fatal: a missing dependency,
an unconnected account, or a transient error returns a SENTENCE, not an
exception. A mail hiccup must not take down a chat turn.
"""

from __future__ import annotations

import base64
import html
import re
from typing import Any

from langchain_core.tools import tool

from agent.tools import google_auth

_MAX_LIST = 25
_PREVIEW_CHARS = 140
_MAX_BODY_CHARS = 8000


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _service() -> tuple[Any, str | None]:
    """(gmail service, None) or (None, a readable reason it's unavailable)."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None, google_auth.INSTALL_HINT
    creds = google_auth.load_credentials()
    if creds is None:
        return None, google_auth.SETUP_HINT
    return build("gmail", "v1", credentials=creds, cache_discovery=False), None


def _decode(data: str) -> str:
    """Gmail bodies are base64url without padding."""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", errors="replace"
        )
    except Exception:  # noqa: BLE001 — a malformed part is skipped, not fatal
        return ""


_TAG = re.compile(r"<[^>]+>")
_BLANKS = re.compile(r"\n\s*\n\s*\n+")


def _html_to_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", markup)
    return _BLANKS.sub("\n\n", html.unescape(_TAG.sub("", markup))).strip()


def _body_text(payload: dict[str, Any]) -> str:
    """The message's readable text: text/plain parts preferred, else HTML stripped.
    Walks nested multipart structures depth-first."""
    plain: list[str] = []
    rich: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            rich.append(_html_to_text(_decode(data)))
        for sub in part.get("parts") or []:
            walk(sub)

    walk(payload)
    text = "\n".join(plain) if plain else "\n".join(rich)
    return _BLANKS.sub("\n\n", text).strip()


# The line a mail client writes above quoted history ("On Mon, 14 Sep 2026 at
# 11:14, Simon <…> wrote:"), possibly wrapped over two lines.
_QUOTE_HEADER = re.compile(r"^\s*On .{5,300}?wrote:\s*$", re.MULTILINE | re.DOTALL)


def _strip_quoted(text: str) -> tuple[str, bool]:
    """Drop quoted reply history so the body is what THIS message's author wrote.
    In an 18-message thread every reply embeds all earlier ones — keeping them
    multiplies tokens and blurs who said what. Returns (text, was_stripped)."""
    cut = len(text)
    m = _QUOTE_HEADER.search(text)
    if m:
        cut = m.start()
    lines = text[:cut].splitlines()
    while lines and lines[-1].lstrip().startswith(">"):
        lines.pop()
    kept = "\n".join(ln for ln in lines if not ln.lstrip().startswith(">")).rstrip()
    return (kept, True) if len(kept) < len(text.rstrip()) and kept else (text, False)


@tool
def list_recent_emails(query: str = "", limit: int = 10) -> str:
    """List the user's Gmail messages matching a search — compact rows, NOT full content.

    `query` uses Gmail search syntax (space = AND, `OR` in caps, quotes for
    phrases). Leave empty for the inbox. Examples:
      `from:<company-domain>`, `to:<person name or address>`, `from:me to:<name>`,
      `subject:offer`, `"Simon Moore"`, `astrazeneca newer_than:30d`, `is:unread`.
    Do NOT write `from: or subject:` — an operator needs a value right after it.
    `limit` is capped at 25.

    Each row: `id | From | To | Subject | Date — preview`. The preview is only the
    first ~140 characters. To quote or summarise what an email actually says, call
    `read_email` with its id. Read-only.
    """
    service, reason = _service()
    if service is None:
        return reason or google_auth.SETUP_HINT

    q = query.strip() or "in:inbox"
    cap = max(1, min(int(limit or 10), _MAX_LIST))
    try:
        listing = service.users().messages().list(userId="me", q=q, maxResults=cap).execute()
    except Exception as exc:  # noqa: BLE001 — a mail outage must not kill the turn
        return google_auth.api_error_message(exc, "Gmail")

    ids = [m["id"] for m in listing.get("messages", [])]
    if not ids:
        return f"No emails found for query {q!r}. Try a simpler query (e.g. one keyword or from:domain)."

    lines = []
    for mid in ids:
        try:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=mid,
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
                .execute()
            )
        except Exception:  # noqa: BLE001 — skip one unreadable message, keep the rest
            continue
        headers = msg.get("payload", {}).get("headers", [])
        frm = _header(headers, "From")
        to = _header(headers, "To")
        subj = _header(headers, "Subject") or "(no subject)"
        date = _header(headers, "Date")
        snippet = html.unescape((msg.get("snippet", "") or "").strip())
        if len(snippet) > _PREVIEW_CHARS:
            snippet = snippet[:_PREVIEW_CHARS] + "…"
        lines.append(
            f"{mid} | {frm} | {to} | {subj} | {date}" + (f" — {snippet}" if snippet else "")
        )

    if not lines:
        return f"No readable emails for query {q!r}."

    # Honest framing, stated IN the output so the model can't miss it.
    more = bool(listing.get("nextPageToken"))
    footer = [
        f"[{len(lines)} message(s) for {q!r}"
        + (f"; MORE exist beyond this limit of {cap} — narrow the query" if more else "")
        + "]",
        "[Previews only — not full content. Use read_email(id) before quoting any email.]",
    ]
    return "\n".join(lines + footer)


@tool
def read_email(message_id: str) -> str:
    """Read ONE email in full — headers plus the plain-text body.

    Use the `id` from a list_recent_emails row. This is the only way to get what
    an email actually says; quote from this output, not from list previews. Long
    bodies are truncated with an explicit notice. Read-only.
    """
    service, reason = _service()
    if service is None:
        return reason or google_auth.SETUP_HINT
    mid = (message_id or "").strip()
    if not mid:
        return "read_email needs a message id from list_recent_emails."
    try:
        msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
    except Exception as exc:  # noqa: BLE001
        return google_auth.api_error_message(exc, "Gmail")

    payload = msg.get("payload", {}) or {}
    headers = payload.get("headers", [])
    head = "\n".join(
        f"{name}: {_header(headers, name)}"
        for name in ("From", "To", "Cc", "Date", "Subject")
        if _header(headers, name)
    )
    body, stripped = _strip_quoted(_body_text(payload))
    body = body or "(no readable text body)"
    if stripped:
        body += "\n[earlier quoted messages in this reply were removed — read those emails by id]"
    if len(body) > _MAX_BODY_CHARS:
        body = (
            body[:_MAX_BODY_CHARS]
            + f"\n… [truncated at {_MAX_BODY_CHARS} chars of {len(body)}; the rest is not shown]"
        )
    return f"id: {mid}\n{head}\n\n{body}"
