"""Durable semantic + episodic memory — Graphiti on Neo4j, via a sync bridge.

This is the "holistic, self-reviving" memory: what the assistant learns from
conversations and keeps across sessions. One `add_episode` records the raw event
(EPISODIC) and lets Graphiti extract entities and facts from it (SEMANTIC), all
in one temporal graph whose edges carry validity dates — so a corrected fact
supersedes the old one rather than sitting beside it.

WHY A BACKGROUND LOOP. Graphiti is async and holds a Neo4j driver; the harness
drives turns synchronously. As with the search MCP, a single private event loop
on its own thread owns the Graphiti instance for the process lifetime, and sync
callers hand work to it and block on a future. One connection, no per-call setup.

OPT-IN. Memory needs Neo4j running, which not every environment has (CI, a bare
deploy). So it is enabled by AGENT_MEMORY=on and initialised LAZILY on first use;
with it off, the middleware is a no-op and nothing connects. A connection failure
is surfaced, not swallowed — an unavailable memory must not look like an empty one.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import UTC, datetime
from typing import Any

DEFAULT_GROUP = os.getenv("MEMORY_GROUP_ID", "default")

# Neo4j emits a WARNING notification for every property key a query mentions that
# does not exist yet (normal on a fresh/small graph — e.g. `fact_embedding`
# before any edge is written). They are harmless and extremely noisy, so quiet
# the notification logger; real errors still raise as exceptions.
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)


def memory_enabled() -> bool:
    """True when durable memory is switched on for this process."""
    return (os.getenv("AGENT_MEMORY") or "").lower() in ("1", "true", "on", "yes")


class _GraphitiRuntime:
    """A private loop owning one Graphiti instance for the process lifetime."""

    _instance: _GraphitiRuntime | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True, name="graphiti-loop").start()
        self._graphiti: Any = None
        self._ready = threading.Event()
        self._error: BaseException | None = None
        asyncio.run_coroutine_threadsafe(self._ainit(), self._loop)
        if not self._ready.wait(timeout=120):
            raise RuntimeError("Graphiti did not initialise within 120s")
        if self._error is not None:
            raise RuntimeError(f"Graphiti init failed: {self._error}")

    @classmethod
    def get(cls) -> _GraphitiRuntime:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def _ainit(self) -> None:
        try:
            from graphiti_core import Graphiti

            from agent.memory.graphiti_clients import (
                BedrockEmbedder,
                BedrockLLMClient,
                PassthroughReranker,
            )

            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "eaflocal-dev-password")
            g = Graphiti(
                uri,
                user,
                password,
                llm_client=BedrockLLMClient(),
                embedder=BedrockEmbedder(),
                cross_encoder=PassthroughReranker(),
            )
            await g.build_indices_and_constraints()
            self._graphiti = g
            self._ready.set()
        except BaseException as exc:  # noqa: BLE001 — surfaced to the constructor
            self._error = exc
            self._ready.set()

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def remember(self, text: str, name: str, group_id: str = DEFAULT_GROUP) -> Any:
        """Record one episode; Graphiti extracts entities/facts from it."""
        from graphiti_core.nodes import EpisodeType

        return self._run(
            self._graphiti.add_episode(
                name=name,
                episode_body=text,
                source=EpisodeType.message,
                source_description="conversation",
                reference_time=datetime.now(UTC),
                group_id=group_id,
            )
        )

    def remember_nowait(self, text: str, name: str, group_id: str = DEFAULT_GROUP) -> None:
        """Fire-and-forget: schedule an episode write without blocking the turn.

        add_episode runs several LLM calls (~20s) — far too slow to sit on the
        response path. So consolidation schedules the write on the background
        loop and returns immediately; failures are logged, not surfaced, because
        a dropped memory write must never fail a user's turn.
        """
        from graphiti_core.nodes import EpisodeType

        async def _write() -> None:
            try:
                await self._graphiti.add_episode(
                    name=name,
                    episode_body=text,
                    source=EpisodeType.message,
                    source_description="conversation",
                    reference_time=datetime.now(UTC),
                    group_id=group_id,
                )
            except Exception as exc:  # noqa: BLE001 — logged, never raised into a turn
                logging.getLogger("agent.memory").warning("memory write failed: %s", exc)

        asyncio.run_coroutine_threadsafe(_write(), self._loop)

    def recall(self, query: str, group_id: str = DEFAULT_GROUP, num_results: int = 5) -> list[str]:
        """Facts (graph edges) most relevant to the query, as readable strings."""
        edges = self._run(
            self._graphiti.search(query, group_ids=[group_id], num_results=num_results)
        )
        return [getattr(e, "fact", str(e)) for e in edges]


def remember(text: str, name: str, group_id: str = DEFAULT_GROUP) -> Any:
    return _GraphitiRuntime.get().remember(text, name, group_id)


def remember_nowait(text: str, name: str, group_id: str = DEFAULT_GROUP) -> None:
    _GraphitiRuntime.get().remember_nowait(text, name, group_id)


def recall(query: str, group_id: str = DEFAULT_GROUP, num_results: int = 5) -> list[str]:
    return _GraphitiRuntime.get().recall(query, group_id, num_results)
