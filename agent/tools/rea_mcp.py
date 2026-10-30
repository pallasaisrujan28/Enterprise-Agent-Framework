"""Website/API discovery as an MCP plug-in — REA (Reverse Engineer Anything).

WHY REA.
The agent is asked for data from sites it has never seen and for which nobody
wrote a connector. A person would open the page, watch DevTools' Network tab,
spot the JSON request the page makes, and reuse it. REA (npm `rea-agents`, MIT)
gives the agent that same evidence through MCP: a bounded Playwright scenario
that records every request (and, when asked, the response bodies), a passive CDP
page inspection, static analysis of the page's JavaScript bundle for fetch /
WebSocket / router endpoints, and an `api-surface` view that groups observed
requests into endpoint templates. It never calls the endpoints for the agent and
never claims it did; the agent reuses what it found and verifies it.

Tested end to end (docs/research/agent-self-discovery.md §6): REA found the
hidden `GET /api/quotes?page=1` behind quotes.toscrape.com/scroll, and a plain
HTTP call to `?page=2` with no browser returned the same shape.

WHY A CURATED SUBSET. The server exposes ~207 tools (native binaries, Android,
firmware, process capture...). Only the web-discovery ones are relevant, and
several of the rest run or attach to local programs. So, as with the browser
plug-in, we surface a small allowlist and only to the `site-discovery`
subagent — never the main agent — so the schemas cost nothing on ordinary turns.
Override with REA_MCP_TOOLS (comma-separated) if a deployment needs others.

NODE VERSION. REA 6.5.0 supports Node ^22.19 || ^24.11 || >=26 (Node 25 is not
supported). Point REA_NODE_DIR at a supported Node's `bin` directory if the
system Node is outside that range; it is prepended to PATH for this server only.

ENVIRONMENT. The subprocess gets the MCP SDK's default safe environment (PATH,
HOME, ...) — not this process's env — so AWS or Google credentials are never
visible to REA or to a page it loads.
"""

from __future__ import annotations

import os
import shlex

from langchain_core.tools import BaseTool

from agent.tools.mcp_runtime import McpToolRuntime

# Pinned, not @latest: a discovery tool that runs a browser is supply-chain
# sensitive, and REA's tool contracts change between releases.
REA_VERSION = "6.5.0"

_DEFAULT_TOOLS = (
    # Drive a bounded, headless browser scenario and record the network
    # (the only live path that can return response bodies).
    "capture_browser_scenario",
    # Passive inspection of a page in a browser the operator started with a
    # loopback CDP port (DOM, scripts, request metadata, JSON body *shapes*).
    "list_browser_targets",
    "inspect_web_page",
    # Static endpoint discovery from the page's JavaScript, without executing it.
    "analyze_web_bundle",
    "export_web_scripts",
    "analyze_javascript_application",
    # Endpoint templates from a saved HAR (e.g. one the user exported).
    "inspect_web_network_capture",
    # Summary-first: big results return a parent Evidence id, expanded here
    # (including the `api-surface` view).
    "inspect_analysis_view",
    # Tools a page declares for agents (WebMCP), listed but never invoked.
    "discover_webmcp_tools",
)


def rea_enabled() -> bool:
    """Whether the site-discovery capability is switched on (AGENT_REA).

    Off by default, like AGENT_BROWSER: tests, CI and Node-less deploys never
    spawn REA or a browser.
    """
    return os.getenv("AGENT_REA", "").strip().lower() in {"1", "on", "true", "yes"}


def browser_executable() -> str:
    """The Chrome-family binary REA launches for capture_browser_scenario.

    REA does not install a browser; the scenario must name one. Empty means
    "not configured", which the subagent prompt reports instead of guessing.
    """
    return os.getenv("REA_BROWSER_EXECUTABLE", "").strip()


def _expose() -> set[str]:
    override = os.getenv("REA_MCP_TOOLS", "").strip()
    if override:
        return {t.strip() for t in override.split(",") if t.strip()}
    return set(_DEFAULT_TOOLS)


def _command_and_args() -> tuple[str, list[str]]:
    """`npx -y rea-agents@<pinned> mcp`, or an explicit launcher.

    REA_MCP_COMMAND / REA_MCP_ARGS replace the default entirely, e.g. a local
    install: REA_MCP_COMMAND=node REA_MCP_ARGS="/opt/rea/node_modules/rea-agents/scripts/rea.mjs mcp".
    """
    command = os.getenv("REA_MCP_COMMAND", "").strip()
    if command:
        # shlex, not str.split: install paths often contain spaces; quote them.
        return command, shlex.split(os.getenv("REA_MCP_ARGS", ""))
    return "npx", ["-y", f"rea-agents@{REA_VERSION}", "mcp"]


def _env() -> dict[str, str]:
    """The SDK's safe default environment, with REA_NODE_DIR first on PATH."""
    from mcp.client.stdio import get_default_environment

    env = get_default_environment()
    node_dir = os.getenv("REA_NODE_DIR", "").strip()
    if node_dir:
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    return env


def _server() -> dict[str, object]:
    command, args = _command_and_args()
    return {"command": command, "args": args, "env": _env(), "transport": "stdio"}


def build_rea_tools() -> list[BaseTool]:
    """REA's web-discovery tools, wrapped for sync and async callers.

    Memoised by the shared runtime, so the roster and any later caller share
    one REA process.
    """
    return McpToolRuntime.get("rea", _server(), _expose()).load()
