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

THE SYNC/ASYNC BRIDGE, AND WHY THIS FILE LOOKS THE WAY IT DOES.
MCP is async and stdio-based; the dashboard drives the graph SYNCHRONOUSLY. A
naive `get_tools()` also spawns the `npx` subprocess on every call. So this owns
a single background event loop on its own thread that:
  - keeps ONE long-lived MCP session (one subprocess) for the process lifetime,
  - runs each tool call on that loop, serving both sync callers (`.result()`) and
    async callers (`wrap_future`) without blocking the caller's own loop.
The tools are loaded once and memoised, so brain.py and the delegation roster
share the same session rather than each starting their own.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import threading
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://127.0.0.1:8088")

# The server exposes several tools; we surface only web search. Fetching stays
# with our own fetch_and_store (which writes to session memory), so we don't
# introduce a second, overlapping fetch tool here.
_EXPOSE = {"searxng_web_search"}

_SERVER: dict[str, Any] = {
    "searxng": {
        "command": "npx",
        "args": ["-y", "mcp-searxng"],
        "env": {"SEARXNG_URL": SEARXNG_URL},
        "transport": "stdio",
    }
}


class _McpRuntime:
    """A background loop with ONE long-lived session task that services calls.

    WHY A SINGLE TASK AND A QUEUE, NOT just "enter the session and keep it".
    The MCP stdio client is built on anyio cancel scopes that MUST be entered
    and exited in the SAME task. Entering the session in one task and then
    invoking tools from other tasks (what run_coroutine_threadsafe does per call)
    trips "attempted to exit cancel scope in a different task". So `_serve`
    opens the session with `async with`, keeps it open for its whole life, and
    runs EVERY tool call itself — pulled from a queue. Enter, all calls, and exit
    happen in one task; the anyio invariant holds.

    Callers hand work in over a thread-safe queue and wait on a
    concurrent.futures.Future — sync callers block on it, async callers wrap it,
    so neither blocks its own event loop.
    """

    _instance: _McpRuntime | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True, name="mcp-loop").start()
        self._queue: asyncio.Queue[Any] | None = None
        self._tools: list[BaseTool] | None = None
        self._ready = threading.Event()
        self._error: BaseException | None = None
        asyncio.run_coroutine_threadsafe(self._serve(), self._loop)
        if not self._ready.wait(timeout=60):
            raise RuntimeError("SearXNG MCP session did not become ready within 60s")
        if self._error is not None:
            raise RuntimeError(f"SearXNG MCP session failed to start: {self._error}")

    @classmethod
    def get(cls) -> _McpRuntime:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def _serve(self) -> None:
        """Own the session for life; execute every tool call in THIS task."""
        try:
            self._queue = asyncio.Queue()
            client = MultiServerMCPClient(_SERVER)
            async with client.session("searxng") as session:
                raw = await load_mcp_tools(session)
                self._tools = [self._wrap(t) for t in raw if t.name in _EXPOSE]
                self._ready.set()
                while True:
                    item = await self._queue.get()
                    if item is None:  # shutdown sentinel
                        break
                    tool, args, fut = item
                    try:
                        fut.set_result(await tool.ainvoke(args))
                    except Exception as exc:  # noqa: BLE001 — relayed to the caller's future
                        fut.set_exception(exc)
        except BaseException as exc:  # noqa: BLE001 — surfaced to the constructor
            self._error = exc
            self._ready.set()

    def load(self) -> list[BaseTool]:
        return self._tools or []

    def _call(self, tool: BaseTool, args: dict[str, Any]) -> concurrent.futures.Future[Any]:
        """Enqueue a tool call onto the session task; return a Future for it."""
        fut: concurrent.futures.Future[Any] = concurrent.futures.Future()
        loop, queue = self._loop, self._queue
        assert queue is not None
        loop.call_soon_threadsafe(queue.put_nowait, (tool, args, fut))
        return fut

    def _wrap(self, tool: BaseTool) -> StructuredTool:
        """A sync+async StructuredTool that routes calls through the session task."""
        runtime = self

        def _sync(**kwargs: Any) -> Any:
            return runtime._call(tool, kwargs).result()

        async def _async(**kwargs: Any) -> Any:
            return await asyncio.wrap_future(runtime._call(tool, kwargs))

        return StructuredTool(
            name=tool.name,
            description=tool.description or "",
            args_schema=tool.args_schema or {"type": "object", "properties": {}},
            func=_sync,
            coroutine=_async,
        )


def build_search_tools() -> list[BaseTool]:
    """The SearXNG MCP search tool(s), wrapped to work from sync and async code.

    Memoised: repeated calls (brain.py and the delegation roster both call this)
    share one MCP session and subprocess rather than starting their own.
    """
    return _McpRuntime.get().load()
