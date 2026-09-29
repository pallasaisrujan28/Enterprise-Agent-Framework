"""Web search as an MCP plug-in — SearXNG behind the Model Context Protocol.

WHY MCP RATHER THAN AN IN-REPO TOOL.
Search used to be our own Python (`web_search` + `search_backend`, DuckDuckGo or
a direct SearXNG HTTP call). That worked, but the *capability* was welded into
our codebase: swapping engines meant editing code. Moving search behind MCP makes
the engine a PLUG-IN — the model still calls one `searxng_web_search` tool, but
what serves it is an external MCP server chosen by configuration. Point it at a
local SearXNG in dev, the cluster's SearXNG in prod, or a different search MCP
entirely, with no change to the harness. That is the flexibility MCP buys.

The server is `mcp-searxng` (npx), which talks to a SearXNG INSTANCE — it does
not replace SearXNG, it fronts it. `SEARXNG_URL` points at that instance
(default: the local docker one on :8088).

THE SYNC/ASYNC BRIDGE lives in agent/tools/mcp_runtime.py, shared with the
Playwright browser plug-in — both need one long-lived subprocess and a
background loop that serves sync and async callers. This module just names the
SearXNG server and the one tool we surface from it.
"""

from __future__ import annotations

import os

from langchain_core.tools import BaseTool

from agent.tools.mcp_runtime import McpToolRuntime

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://127.0.0.1:8088")

# The server exposes several tools; we surface only web search. Fetching stays
# with our own fetch_url (which returns markdown into context), so we don't
# introduce a second, overlapping fetch tool here.
_EXPOSE = {"searxng_web_search"}

_SERVER = {
    "command": "npx",
    "args": ["-y", "mcp-searxng"],
    "env": {"SEARXNG_URL": SEARXNG_URL},
    "transport": "stdio",
}


def build_search_tools() -> list[BaseTool]:
    """The SearXNG MCP search tool(s), wrapped to work from sync and async code.

    Memoised by the shared runtime: repeated calls (brain.py and the delegation
    roster both call this) share one MCP session and subprocess rather than
    starting their own.
    """
    return McpToolRuntime.get("searxng", _SERVER, _EXPOSE).load()
