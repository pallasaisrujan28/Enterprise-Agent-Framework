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
        self._write_lock: asyncio.Lock | None = None
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

    def _run(self, coro: Any, timeout: float | None = None) -> Any:
        # timeout bounds how long the CALLER waits; the coroutine keeps running on
        # the background loop if it overruns (harmless — a slow recall finishing
        # late is just discarded). Raises concurrent.futures.TimeoutError on expiry.
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    async def _add_episode(self, text: str, name: str, group_id: str) -> Any:
        """One episode write, with the ontology, SERIALISED.

        Graphiti's docs: add episodes one at a time, each awaited before the next
        — concurrent writes race on entity resolution and edge invalidation. The
        lock is created lazily ON the background loop (an asyncio.Lock binds to
        the loop it is first used in).
        """
        from graphiti_core.nodes import EpisodeType

        from agent.memory import ontology

        if self._write_lock is None:
            self._write_lock = asyncio.Lock()
        async with self._write_lock:
            return await self._graphiti.add_episode(
                name=name,
                episode_body=text,
                source=EpisodeType.message,
                source_description="chat between the user and their AI assistant",
                reference_time=datetime.now(UTC),
                group_id=group_id,
                entity_types=ontology.ENTITY_TYPES,
                edge_types=ontology.EDGE_TYPES,
                edge_type_map=ontology.EDGE_TYPE_MAP,
                custom_extraction_instructions=ontology.EXTRACTION_INSTRUCTIONS,
            )

    def remember(self, text: str, name: str, group_id: str = DEFAULT_GROUP) -> Any:
        """Record one episode; Graphiti extracts entities/facts from it."""
        return self._run(self._add_episode(text, name, group_id))

    def remember_nowait(self, text: str, name: str, group_id: str = DEFAULT_GROUP) -> None:
        """Fire-and-forget: schedule an episode write without blocking the turn.

        add_episode runs several LLM calls (~20s) — far too slow to sit on the
        response path. So consolidation schedules the write on the background
        loop and returns immediately; failures are logged, not surfaced, because
        a dropped memory write must never fail a user's turn.
        """

        async def _write() -> None:
            try:
                await self._add_episode(text, name, group_id)
            except Exception as exc:  # noqa: BLE001 — logged, never raised into a turn
                logging.getLogger("agent.memory").warning("memory write failed: %s", exc)

        asyncio.run_coroutine_threadsafe(_write(), self._loop)

    async def _search_current(self, query: str, group_id: str, num_results: int) -> list[Any]:
        """Hybrid edge search restricted to CURRENTLY VALID facts.

        Graphiti's plain `search()` returns superseded facts too — nothing in its
        search path filters `invalid_at`/`expired_at`. So a corrected fact could
        be recalled next to the one that replaced it. `search_` with filters
        drops them. The recipe is deep-copied because setting `.limit` on the
        shared module-level config would leak into every other search.
        """
        import copy

        from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
        from graphiti_core.search.search_filters import (
            ComparisonOperator,
            DateFilter,
            SearchFilters,
        )

        config = copy.deepcopy(EDGE_HYBRID_SEARCH_RRF)
        config.limit = num_results
        is_null = [[DateFilter(comparison_operator=ComparisonOperator.is_null)]]
        results = await self._graphiti.search_(
            query,
            config=config,
            group_ids=[group_id],
            search_filter=SearchFilters(invalid_at=is_null, expired_at=is_null),
        )
        return list(results.edges)

    def recall(
        self,
        query: str,
        group_id: str = DEFAULT_GROUP,
        num_results: int = 5,
        timeout: float | None = None,
    ) -> list[str]:
        """Facts (graph edges) most relevant to the query, as readable strings.

        `timeout` bounds how long the caller waits — recall is best-effort and
        must not hang a turn; on expiry it raises so the caller can proceed."""
        edges = self._run(self._search_current(query, group_id, num_results), timeout=timeout)
        return [getattr(e, "fact", str(e)) for e in edges]

    def search_facts(
        self, query: str, group_id: str = DEFAULT_GROUP, num_results: int = 8
    ) -> list[tuple[str, str]]:
        """Like recall, but returns (edge_uuid, fact) so a fact can be updated or
        forgotten by id. The uuid is Graphiti's stable edge identifier."""
        edges = self._run(self._search_current(query, group_id, num_results))
        return [(str(getattr(e, "uuid", "")), getattr(e, "fact", str(e))) for e in edges]

    def update_fact(self, uuid: str, new_fact: str) -> bool:
        """Rewrite the text of one fact edge. Returns True if an edge matched.

        The stored vector (fact_embedding) is left as-is — a correction changes the
        text the model reads; refreshing the embedding is a nice-to-have, not
        required for the fact to be shown once recalled."""

        async def _q() -> int:
            res = await self._graphiti.driver.execute_query(
                "MATCH ()-[e:RELATES_TO {uuid: $uuid}]->() SET e.fact = $fact RETURN count(e) AS n",
                uuid=uuid,
                fact=new_fact,
            )
            return int(res.records[0]["n"]) if res.records else 0

        return self._run(_q()) > 0

    def forget_fact(self, uuid: str) -> bool:
        """Delete one fact edge by uuid. Returns True if an edge was removed.

        This is the "forget" path — a hard delete of the RELATES_TO edge. The
        entities it connected stay; only the asserted fact between them goes."""

        async def _q() -> int:
            # Count via collect() BEFORE deleting — you cannot RETURN count(e)
            # after e is deleted. Directed match returns the edge once.
            res = await self._graphiti.driver.execute_query(
                "MATCH ()-[e:RELATES_TO {uuid: $uuid}]->() "
                "WITH collect(e) AS es "
                "FOREACH (x IN es | DELETE x) "
                "RETURN size(es) AS n",
                uuid=uuid,
            )
            return int(res.records[0]["n"]) if res.records else 0

        return self._run(_q()) > 0

    def snapshot(self, group_id: str = DEFAULT_GROUP, limit: int = 100) -> dict[str, Any]:
        """A read-only view of the whole graph for one group — for the memory UI.

        Three lists straight from Cypher: facts (the RELATES_TO edges, which are
        the semantic memory), episodes (the raw events, the episodic memory), and
        entities (the nodes). Temporal values are stringified so they serialise.
        """

        async def _query(cypher: str) -> list[dict[str, Any]]:
            res = await self._graphiti.driver.execute_query(cypher, group_id=group_id, limit=limit)
            out: list[dict[str, Any]] = []
            for rec in res.records:
                out.append({k: (str(v) if v is not None else None) for k, v in dict(rec).items()})
            return out

        facts = self._run(
            _query(
                "MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity) WHERE e.group_id = $group_id "
                "RETURN e.fact AS fact, n.name AS source, m.name AS target, "
                "e.valid_at AS valid_at, e.invalid_at AS invalid_at "
                "ORDER BY e.created_at DESC LIMIT $limit"
            )
        )
        episodes = self._run(
            _query(
                "MATCH (ep:Episodic) WHERE ep.group_id = $group_id "
                "RETURN ep.name AS name, ep.content AS content, ep.valid_at AS at "
                "ORDER BY ep.valid_at DESC LIMIT $limit"
            )
        )
        entities = self._run(
            _query(
                "MATCH (n:Entity) WHERE n.group_id = $group_id "
                "RETURN n.name AS name, n.summary AS summary "
                "ORDER BY n.created_at DESC LIMIT $limit"
            )
        )
        return {"facts": facts, "episodes": episodes, "entities": entities}


def remember(text: str, name: str, group_id: str = DEFAULT_GROUP) -> Any:
    return _GraphitiRuntime.get().remember(text, name, group_id)


def remember_nowait(text: str, name: str, group_id: str = DEFAULT_GROUP) -> None:
    _GraphitiRuntime.get().remember_nowait(text, name, group_id)


def recall(
    query: str,
    group_id: str = DEFAULT_GROUP,
    num_results: int = 5,
    timeout: float | None = None,
) -> list[str]:
    return _GraphitiRuntime.get().recall(query, group_id, num_results, timeout=timeout)


def save_fact(subject: str, content: str, group_id: str = DEFAULT_GROUP) -> Any:
    """Explicit user-directed save ("remember that …"). Recorded as an episode so
    Graphiti indexes and extracts it exactly as it does consolidated memory —
    synchronous so the tool can confirm the write actually happened."""
    return _GraphitiRuntime.get().remember(
        f"{subject}: {content}", name="user note", group_id=group_id
    )


def search_facts(
    query: str, group_id: str = DEFAULT_GROUP, num_results: int = 8
) -> list[tuple[str, str]]:
    return _GraphitiRuntime.get().search_facts(query, group_id, num_results)


def update_fact(uuid: str, new_fact: str) -> bool:
    return _GraphitiRuntime.get().update_fact(uuid, new_fact)


def forget_fact(uuid: str) -> bool:
    return _GraphitiRuntime.get().forget_fact(uuid)


def snapshot(group_id: str = DEFAULT_GROUP, limit: int = 100) -> dict[str, Any]:
    return _GraphitiRuntime.get().snapshot(group_id, limit)
