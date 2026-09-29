"""Tests for the calendar read tool — the graceful, no-network path.

The OAuth plumbing now lives in agent/tools/google_auth (tested separately). Here
we only pin that list_calendar_events degrades to a readable setup hint when
Google isn't connected, rather than raising.
"""

from __future__ import annotations

import pytest

from agent.tools import calendar as cal
from agent.tools import google_auth


def test_list_events_returns_hint_when_not_connected(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("EAF_HOME", str(tmp_path))
    # Force "not signed in" independent of whether the google libs are installed.
    monkeypatch.setattr(google_auth, "load_credentials", lambda: None)
    out = cal.list_calendar_events.invoke({})
    assert "not connected" in out.lower() or "not installed" in out.lower()


def test_calendar_reexports_shared_auth() -> None:
    """calendar.connect / is_connected must stay wired to the shared module."""
    assert cal.connect is google_auth.connect
    assert cal.is_connected is google_auth.is_connected
