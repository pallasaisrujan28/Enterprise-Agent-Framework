"""Google Calendar — read the user's real schedule so the agent can answer
"what meetings do I have?".

The OAuth plumbing (sign-in, token cache, refresh, permissions) lives in
agent/tools/google_auth.py and is SHARED with Gmail — one sign-in grants both.
This module is just the calendar read: turn a cached credential into events.

Best-effort and never fatal: a missing dependency, an unconnected account, or an
expired token returns a SENTENCE telling the user what to do — never an
exception. A calendar hiccup must not take down a chat turn.
"""

from __future__ import annotations

import datetime as _dt

from langchain_core.tools import tool

from agent.tools import google_auth

# Re-exported so existing callers (cli.py, dashboard server) keep working after
# the OAuth plumbing moved to google_auth.
connect = google_auth.connect
is_connected = google_auth.is_connected


@tool
def list_calendar_events(start: str = "", end: str = "", limit: int = 20) -> str:
    """Read the user's Google Calendar to answer what's on their schedule.

    Use whenever the user asks what meetings/events they have for a day, week,
    "today", "tomorrow", etc. `start` and `end` are ISO dates (YYYY-MM-DD);
    resolve relative dates ("today", "tomorrow") from the current date in your
    system prompt. Omit both to list today's events. Returns one event per line
    as "title | start | attendees", or a sentence explaining setup if Google is
    not connected.
    """
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return google_auth.INSTALL_HINT

    creds = google_auth.load_credentials()
    if creds is None:
        return google_auth.SETUP_HINT

    today = _dt.date.today().isoformat()
    s = (start or today)[:10]
    e = (end or s)[:10]
    # Google wants RFC3339 with an offset; local midnight to local midnight+1d so
    # "today" means the user's today, not UTC's.
    tz = _dt.datetime.now().astimezone().tzinfo
    try:
        lo = _dt.datetime.fromisoformat(s).replace(tzinfo=tz)
        hi = _dt.datetime.fromisoformat(e).replace(tzinfo=tz) + _dt.timedelta(days=1)
    except ValueError:
        return "I could not parse those dates — use ISO format like 2026-09-30."

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        resp = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=lo.isoformat(),
                timeMax=hi.isoformat(),
                singleEvents=True,  # expand recurring series into instances
                orderBy="startTime",
                maxResults=max(1, min(int(limit or 20), 100)),
            )
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — a calendar outage must not kill the turn
        return google_auth.api_error_message(exc, "Google Calendar")

    items = resp.get("items", [])
    if not items:
        return f"No calendar events between {s} and {e}."
    lines = []
    for ev in items:
        when = ev.get("start", {})
        at = when.get("dateTime") or when.get("date") or "?"
        who = ", ".join(a.get("email", "") for a in ev.get("attendees", []) if a.get("email"))
        lines.append(f"{ev.get('summary', '(no title)')} | {at}" + (f" | {who}" if who else ""))
    return "\n".join(lines)
