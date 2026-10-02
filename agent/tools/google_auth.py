"""Shared Google OAuth — one sign-in for every Google connector we read from.

WHY THIS EXISTS. Calendar was the first Google tool; Gmail is the second, and
more (Drive, Contacts) would follow the same shape. Rather than a separate OAuth
flow and token per tool — which would make the user sign in once per connector —
this owns ONE token that carries ALL the read scopes we use. A single
`agent connect google` grants calendar + gmail read access together, and every
Google tool reads from the same cached, auto-refreshing token.

The principles carried from the calendar tool stay:

  READ scopes, plus ONE write scope: gmail.compose (create drafts and send
  them). Sending is gated by a human Send / Don't send decision in the chat
  (HumanInTheLoop on send_draft in agent/brain.py); nothing else can change
  mail, calendars, or delete anything.

  BEST-EFFORT, NEVER FATAL. Missing deps, an unconnected account, or an expired
  token return None / a sentence — never an exception. A connector hiccup must
  not take down a chat turn.

  CONSENT OUT OF BAND. The browser flow runs only in `connect()`, called from the
  CLI or the dashboard's local-only endpoint — never mid-turn.

  TOKEN OWNER-ONLY ON DISK. The refresh token grants ongoing access, so the file
  is written 0600 under a 0700 dir, and re-chmod'd on every refresh.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

GMAIL_COMPOSE = "https://www.googleapis.com/auth/gmail.compose"

# Every scope the agent uses, granted together in one consent. Adding a new
# Google connector = add its scope here (and users re-consent once).
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    GMAIL_COMPOSE,
]

INSTALL_HINT = "Google support is not installed — run: pip install -e '.[gcal]'"
SETUP_HINT = (
    "Google is not connected yet. Set it up once: save your Google 'Desktop app' "
    "OAuth client to $EAF_HOME/credentials.json, then run `agent connect google` "
    "(or use the Connections tab) to sign in. That grants read access to your "
    "calendar and email together."
)


def eaf_home() -> Path:
    """Where credentials.json and the cached token live. Configurable so a deploy
    can point it at a mounted secret volume instead of the user's home dir."""
    return Path(os.getenv("EAF_HOME") or (Path.home() / ".eaf")).expanduser()


def api_error_message(exc: Exception, service: str) -> str:
    """Turn a Google API exception into a CLEAR, COMPLETE, actionable sentence.

    WHY THIS MATTERS. The raw HttpError is long and, when truncated mid-URL,
    reads to the model like "generic 403" — which made the agent tell the user
    "Google is not connected" when in fact it WAS connected and only the API was
    disabled. So we classify the common causes and never emit a truncated URL.
    """
    import re

    s = str(exc)
    if "has not been used" in s or "is disabled" in s:
        m = re.search(r"https://console\.[^\s\"']+?project=\d+", s)
        link = m.group(0) if m else "Google Cloud Console → APIs & Services → Library"
        return (
            f"The {service} API is not enabled for your Google project (you ARE "
            f"connected — this is a project setting). Enable it here: {link} — then "
            "wait a minute and retry."
        )
    low = s.lower()
    if "insufficient" in low or "access_token_scope" in low:
        return (
            f"{service} access was not granted. Reconnect Google (Connections tab "
            f"or `agent connect google`) and approve the {service} permission."
        )
    if "invalid_grant" in low or "token has been expired or revoked" in low:
        return "Google sign-in expired or was revoked. Reconnect Google to refresh it."
    status = getattr(getattr(exc, "resp", None), "status", None)
    return f"{service} is temporarily unavailable (HTTP {status or '?'}). Please try again shortly."


def token_path() -> Path:
    return eaf_home() / "google-token.json"


def credentials_path() -> Path:
    return eaf_home() / "credentials.json"


def is_connected() -> bool:
    """True when a cached token exists. Cheap and side-effect free — never opens
    a browser or hits the network, so callers can gate on it freely."""
    return token_path().exists()


def _write_token(creds) -> None:
    """Persist the OAuth token owner-only. The refresh_token grants ongoing read
    access, so it must not be world/group readable: dir 0700, file 0600, re-set
    on every write (a refresh rewrites it) so the tightening cannot drift."""
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(path.parent, 0o700)
    path.write_text(creds.to_json(), encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)


def load_credentials():
    """Cached token → refresh if stale → None. NEVER launches a browser: that
    only happens in connect(), so a chat turn cannot block on consent."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None

    path = token_path()
    if not path.exists():
        return None
    try:
        # The token's OWN granted scopes, not SCOPES: asking to refresh with a
        # scope that was never granted (an older read-only token, before
        # gmail.compose existed) fails with invalid_scope and would break the
        # read tools too. Write tools check has_scope() and ask to reconnect.
        creds = Credentials.from_authorized_user_file(str(path))
    except Exception:  # noqa: BLE001 — a corrupt token is "not connected", not a crash
        return None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _write_token(creds)
        except Exception:  # noqa: BLE001 — a failed refresh means reconnect, not crash
            return None
    return creds if (creds and creds.valid) else None


def has_scope(creds, scope: str) -> bool:
    """Whether the cached token was granted `scope` (False if unknown)."""
    granted = getattr(creds, "granted_scopes", None) or getattr(creds, "scopes", None) or []
    return scope in set(granted)


RECONNECT_FOR_COMPOSE = (
    "Drafting and sending email needs one more Google permission. Reconnect Google "
    "(`agent connect google` or the Connections tab) and approve 'Manage drafts and "
    "send emails'. Reading email keeps working meanwhile."
)


def connect() -> str:
    """Open the browser, get consent for ALL read scopes, cache the token. The
    ONE place a browser window is allowed. Returns a human-readable outcome."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return INSTALL_HINT

    creds_file = credentials_path()
    if not creds_file.exists():
        return (
            f"No OAuth client found at {creds_file}. Create a 'Desktop app' OAuth "
            "client in Google Cloud Console (enable the Calendar and Gmail APIs), "
            "download it, and save it there — then connect again."
        )
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), scopes=SCOPES)
        # port=0 = any free local port; the redirect lands back on this machine.
        creds = flow.run_local_server(port=0)
    except Exception as exc:  # noqa: BLE001 — a cancelled/failed sign-in is not a crash
        return f"Google sign-in failed or was cancelled ({type(exc).__name__}). Nothing was saved."

    _write_token(creds)
    return (
        "Google connected (read calendar + email; draft and send email, each send "
        f"confirmed by you in the chat). Token cached (owner-only) at {token_path()}."
    )
