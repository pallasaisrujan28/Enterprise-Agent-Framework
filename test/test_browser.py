"""Guards on the browsing/action capability — the config surface and the gating.

None of this spawns a browser. The MCP runtime (Node + Playwright + Chromium) is
only touched by build_browser_tools(), which these tests never call: they either
exercise the pure config helpers or monkeypatch the tool builders to [] so the
subagent roster can be assembled without a subprocess.

What is guarded, because each is a real correctness hinge:
  - AGENT_BROWSER gating: off by default so CI and browser-less deploys never
    require Node/Chromium; on only when explicitly set.
  - the curated tool allowlist: escape-hatch tools (evaluate/install) stay off
    unless a deployment opts in via BROWSER_MCP_TOOLS.
  - launch args: headless / persistent-profile / browser choice come from the
    environment, so the same code serves a laptop and a headless pod.
  - the browsing subagent appears in the roster ONLY when the capability is on,
    and carries the confirm-before-commit contract.
"""

from __future__ import annotations

import pytest

from agent.tools import browser_mcp

# ── enable flag ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value", ["on", "1", "true", "yes", "ON", "True"])
def test_browser_enabled_when_flag_set(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AGENT_BROWSER", value)
    assert browser_mcp.browser_enabled() is True


@pytest.mark.parametrize("value", ["", "off", "0", "false", "no"])
def test_browser_disabled_by_default(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AGENT_BROWSER", value)
    assert browser_mcp.browser_enabled() is False


# ── exposed tool set ─────────────────────────────────────────────────────────


def test_default_expose_is_the_curated_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BROWSER_MCP_TOOLS", raising=False)
    exposed = browser_mcp._expose()
    assert "browser_snapshot" in exposed
    assert "browser_click" in exposed
    assert "browser_navigate" in exposed
    # Escape hatches are deliberately NOT surfaced by default.
    assert "browser_evaluate" not in exposed
    assert "browser_install" not in exposed


def test_expose_override_replaces_the_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BROWSER_MCP_TOOLS", "browser_navigate, browser_snapshot")
    assert browser_mcp._expose() == {"browser_navigate", "browser_snapshot"}


# ── launch args ──────────────────────────────────────────────────────────────


def test_server_args_default_is_headed_and_persistent(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("BROWSER_MCP_HEADLESS", "BROWSER_USER_DATA_DIR", "BROWSER_MCP_BROWSER"):
        monkeypatch.delenv(var, raising=False)
    args = browser_mcp._server_args()
    assert "@playwright/mcp@latest" in args
    # Headed (no --headless) and not --isolated: a real, persistent profile.
    assert "--headless" not in args
    assert "--isolated" not in args


def test_server_args_honour_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BROWSER_MCP_HEADLESS", "1")
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", "/tmp/eaf-browser-profile")
    monkeypatch.setenv("BROWSER_MCP_BROWSER", "chromium")
    args = browser_mcp._server_args()
    assert "--headless" in args
    assert args[args.index("--user-data-dir") + 1] == "/tmp/eaf-browser-profile"
    assert args[args.index("--browser") + 1] == "chromium"


# ── roster gating ────────────────────────────────────────────────────────────


def _stub_tool_builders(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the roster from spawning any MCP subprocess during the test."""
    from agent.delegation import subagents

    monkeypatch.setattr(subagents, "build_search_tools", lambda: [])
    monkeypatch.setattr(subagents, "build_browser_tools", lambda: [])


def test_browsing_subagent_absent_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_BROWSER", "off")
    _stub_tool_builders(monkeypatch)
    from agent.delegation.subagents import build_subagents

    names = {s["name"] for s in build_subagents()}
    assert "browsing" not in names
    assert "research" in names


def test_browsing_subagent_present_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_BROWSER", "on")
    _stub_tool_builders(monkeypatch)
    from agent.delegation.subagents import BROWSING_PROMPT, build_subagents

    roster = {s["name"]: s for s in build_subagents()}
    assert "browsing" in roster
    # The confirm-before-commit contract must actually be in the prompt.
    assert "CONFIRM BEFORE COMMIT" in BROWSING_PROMPT
    assert "never invent" in BROWSING_PROMPT.lower() or "do not invent" in BROWSING_PROMPT.lower()
