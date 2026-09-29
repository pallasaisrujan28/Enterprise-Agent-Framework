"""Browser control as an MCP plug-in — Playwright behind the Model Context Protocol.

WHY PLAYWRIGHT MCP, AND NOT browser-use's OWN AGENT.
The browsing/action agent needs to drive a real browser on ANY site a person can
use (shopping, booking, visa forms) — universal, not per-site connectors. Two
open-source routes were considered:

  browser-use runs its OWN LLM loop. Its Bedrock support for TEMPORARY
  credentials (which this project uses — the STS keys expire hourly) only works
  through `ChatAnthropicBedrock`, i.e. Anthropic models; `ChatAWSBedrock` ignores
  `AWS_SESSION_TOKEN`. Our verified, billable stack is gpt-oss / nova on
  `ChatBedrockConverse`, and Anthropic models are payment-blocked in this account
  bar the priciest one. So browser-use would force a costly/blocked model.

  Playwright MCP (Microsoft) has NO LLM. It exposes browser actions over MCP and
  drives Chromium via structured ACCESSIBILITY SNAPSHOTS — no vision model
  needed. OUR existing agent, on OUR existing Bedrock model, is the brain and
  calls these tools step by step. That is exactly what the obligation gate and
  the confirm-before-commit flow need: the agent reasons and acts one deterministic
  step at a time, and can stop to ask the user before anything irreversible.

So this mirrors agent/tools/searxng_mcp.py: name a stdio MCP server, surface a
curated set of its tools, and share the async bridge in agent/tools/mcp_runtime.py.

THE PERSISTENT PROFILE MATTERS. A real browser profile (cookies, logins, a
consistent fingerprint) beats fingerprint-forging against bot walls, and it keeps
the user logged in across turns. Playwright MCP uses a persistent profile by
default; we do NOT pass --isolated. `BROWSER_USER_DATA_DIR` pins where it lives.

HEADED BY DEFAULT so a human can watch it work (a trust requirement) and solve a
CAPTCHA in the real window when one appears. Set BROWSER_MCP_HEADLESS=1 for a
server without a display.
"""

from __future__ import annotations

import os

from langchain_core.tools import BaseTool

from agent.tools.mcp_runtime import McpToolRuntime

# The curated tool set surfaced to the agent. Deliberately NOT every tool the
# server offers: `browser_evaluate` (arbitrary JS), `browser_install`, and tab
# teardown are escape hatches we do not want the model reaching for by default.
# This covers navigate → perceive → act → upload → confirm across all the target
# workflows. Override with BROWSER_MCP_TOOLS (comma-separated) if a deployment
# needs a different set.
_DEFAULT_TOOLS = (
    "browser_navigate",
    "browser_navigate_back",
    "browser_snapshot",
    "browser_take_screenshot",
    "browser_click",
    "browser_type",
    "browser_fill_form",
    "browser_select_option",
    "browser_press_key",
    "browser_hover",
    "browser_file_upload",
    "browser_wait_for",
    "browser_handle_dialog",
    "browser_tabs",
    "browser_console_messages",
    "browser_network_requests",
)


def browser_enabled() -> bool:
    """Whether the browsing/action capability is switched on.

    Opt-in via AGENT_BROWSER, exactly like AGENT_MEMORY for durable memory. Off by
    default so tests, CI, and browser-less deploys never spawn Chromium or require
    Node + Playwright to be present. A deployment that wants the agent to browse
    and act sets AGENT_BROWSER=on.
    """
    return os.getenv("AGENT_BROWSER", "").strip().lower() in {"1", "on", "true", "yes"}


def _expose() -> set[str]:
    override = os.getenv("BROWSER_MCP_TOOLS", "").strip()
    if override:
        return {t.strip() for t in override.split(",") if t.strip()}
    return set(_DEFAULT_TOOLS)


def _server_args() -> list[str]:
    """Launch args for `npx @playwright/mcp`, from the environment.

    Headed + persistent profile by default (see module docstring). Everything is
    overridable so the same code serves a dev laptop and a headless pod.
    """
    args = ["-y", "@playwright/mcp@latest"]

    if os.getenv("BROWSER_MCP_HEADLESS", "").lower() in {"1", "true", "yes"}:
        args.append("--headless")

    # A pinned, persistent profile dir keeps logins and a stable fingerprint
    # across runs. Left unset, the server manages its own persistent profile.
    user_data_dir = os.getenv("BROWSER_USER_DATA_DIR", "").strip()
    if user_data_dir:
        args += ["--user-data-dir", user_data_dir]

    # Where screenshots / downloads land, if pinned.
    output_dir = os.getenv("BROWSER_MCP_OUTPUT_DIR", "").strip()
    if output_dir:
        args += ["--output-dir", output_dir]

    # Chromium unless told otherwise (chromium | firefox | webkit | msedge).
    browser = os.getenv("BROWSER_MCP_BROWSER", "").strip()
    if browser:
        args += ["--browser", browser]

    extra = os.getenv("BROWSER_MCP_ARGS", "").strip()
    if extra:
        args += extra.split()

    return args


def _server() -> dict[str, object]:
    return {
        "command": "npx",
        "args": _server_args(),
        "transport": "stdio",
    }


def build_browser_tools() -> list[BaseTool]:
    """The Playwright MCP browser tools, wrapped to work from sync and async code.

    Memoised by the shared runtime: brain.py and the browsing subagent share one
    browser session and one Chromium subprocess rather than each launching their
    own — so the agent and its delegate act in the SAME browser, keeping login
    and page state coherent across a task.
    """
    return McpToolRuntime.get("browser", _server(), _expose()).load()
