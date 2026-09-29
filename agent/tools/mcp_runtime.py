"""A reusable sync/async bridge to a stdio MCP server.

WHY THIS EXISTS AS ITS OWN MODULE.
Search (SearXNG) was the first MCP plug-in, and its bridge lived inside
`searxng_mcp.py`. A second plug-in — the Playwright browser server — needs the
exact same machinery: one long-lived subprocess, one background event loop, and
a queue that lets both sync callers (the dashboard drives the graph
synchronously) and async callers use the same session. Rather than copy that
subtle anyio-safe code twice, it lives here once, parameterised by server name,
launch spec, and which tools to expose.

THE ANYIO INVARIANT, AND WHY THIS LOOKS THE WAY IT DOES.
The MCP stdio client is built on anyio cancel scopes that MUST be entered and
exited in the SAME task. Entering the session in one task and then invoking tools
from other tasks (what `run_coroutine_threadsafe` does per call) trips "attempted
to exit cancel scope in a different task". So `_serve` opens the session with
`async with`, keeps it open for its whole life, and runs EVERY tool call itself —
pulled from a queue. Enter, all calls, and exit happen in one task; the invariant
holds.

Callers hand work in over a thread-safe queue and wait on a
`concurrent.futures.Future` — sync callers block on it, async callers wrap it, so
neither blocks its own event loop.

ONE RUNTIME PER SERVER. Instances are memoised by server name, so every caller
that asks for the same server shares one subprocess and one session rather than
each starting their own.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import Iterable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# How long to wait for the subprocess + session handshake before giving up. The
# browser server downloads/launches Chromium on first use, so this is generous.
_READY_TIMEOUT_S = 120


class McpToolRuntime:
    """A background loop with ONE long-lived session task that services calls.

    See the module docstring for why a single task and a queue, rather than just
    "enter the session and keep it".
    """

    _instances: dict[str, McpToolRuntime] = {}
    _lock = threading.Lock()

    def __init__(self, name: str, server_spec: dict[str, Any], expose: set[str] | None) -> None:
        self._name = name
        # Annotated Any because MultiServerMCPClient wants a precisely-typed
        # connection mapping; the original searxng module got this for free by
        # typing its module-level _SERVER as dict[str, Any].
        self._server_spec: dict[str, Any] = {name: server_spec}
        self._expose = expose
        self._loop = asyncio.new_event_loop()
        threading.Thread(
            target=self._loop.run_forever, daemon=True, name=f"mcp-{name}-loop"
        ).start()
        self._queue: asyncio.Queue[Any] | None = None
        self._tools: list[BaseTool] | None = None
        self._ready = threading.Event()
        self._error: BaseException | None = None
        asyncio.run_coroutine_threadsafe(self._serve(), self._loop)
        if not self._ready.wait(timeout=_READY_TIMEOUT_S):
            raise RuntimeError(
                f"{name} MCP session did not become ready within {_READY_TIMEOUT_S}s"
            )
        if self._error is not None:
            raise RuntimeError(f"{name} MCP session failed to start: {self._error}")

    @classmethod
    def get(
        cls, name: str, server_spec: dict[str, Any], expose: Iterable[str] | None = None
    ) -> McpToolRuntime:
        """The runtime for `name`, created once and shared thereafter.

        `expose` restricts which of the server's tools are surfaced; None exposes
        all of them. It is only read on first creation — the memoised instance
        keeps whatever filter it was built with.
        """
        with cls._lock:
            existing = cls._instances.get(name)
            if existing is None:
                existing = cls(name, server_spec, set(expose) if expose is not None else None)
                cls._instances[name] = existing
            return existing

    async def _serve(self) -> None:
        """Own the session for life; execute every tool call in THIS task."""
        try:
            self._queue = asyncio.Queue()
            client = MultiServerMCPClient(self._server_spec)
            async with client.session(self._name) as session:
                raw = await load_mcp_tools(session)
                self._tools = [
                    self._wrap(t) for t in raw if self._expose is None or t.name in self._expose
                ]
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
