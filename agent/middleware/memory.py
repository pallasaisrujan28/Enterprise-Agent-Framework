"""Durable memory as middleware — waku's strategy on Graphiti.

Three jobs, wired into the harness so every entry point gets them:

  before_agent   RETRIEVAL GATE + recall. A cheap model decides whether the turn
                 needs long-term memory; if so, we search Graphiti and stash the
                 facts on state. Gated so we do not query the graph every turn.
  wrap_model_call INJECT. The recalled facts are appended to the system prompt
                 for this turn's model calls — the model simply sees what we know.
  after_agent    CONSOLIDATE. Every N turns, the recent exchange is written to
                 Graphiti as an episode (fire-and-forget, so the ~20s extraction
                 never sits on the response path). Graphiti derives the durable
                 facts and supersedes stale ones — the self-reviving write-path.

OFF BY DEFAULT. Memory needs Neo4j (AGENT_MEMORY=on). With it off, every hook
returns immediately and nothing connects — so tests and bare deploys are
unaffected. Memory failures are caught and never break a turn: an assistant that
cannot reach its memory should still answer, just without recall.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import SystemMessage

from agent.memory import retrieval_gate, semantic

_CONSOLIDATE_EVERY = int(os.getenv("MEMORY_CONSOLIDATE_EVERY", "3"))


class MemoryState(AgentState):
    """State this middleware writes. Declared, or LangGraph drops the keys."""

    recalled_memory: NotRequired[str]
    memory_turns: NotRequired[int]


def _latest_human(messages: list[Any]) -> str:
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            return m.text if hasattr(m, "text") else str(m.content)
    return ""


def _recent_exchange(messages: list[Any], pairs: int) -> str:
    """The last `pairs` user/assistant turns as plain text, for consolidation."""
    kept: list[str] = []
    for m in reversed(messages):
        t = getattr(m, "type", "")
        if t == "human":
            kept.append(f"User: {m.text if hasattr(m, 'text') else m.content}")
        elif t == "ai":
            text = m.text if hasattr(m, "text") else str(m.content)
            if text.strip():
                kept.append(f"Assistant: {text}")
        if len(kept) >= pairs * 2:
            break
    return "\n".join(reversed(kept))


class MemoryMiddleware(AgentMiddleware[MemoryState, ContextT, ResponseT]):
    """Gated recall + injection + batched, non-blocking consolidation."""

    name = "MemoryMiddleware"
    state_schema = MemoryState

    def __init__(self, router: Any = None, group_id: str | None = None) -> None:
        super().__init__()
        self._router = router
        self._group = group_id or semantic.DEFAULT_GROUP

    # ── recall (gated) ──────────────────────────────────────────────────────
    def before_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        if not semantic.memory_enabled():
            return None
        message = _latest_human(state.get("messages") or [])
        if not message:
            return None
        try:
            retrieve, query = retrieval_gate.should_retrieve(self._router, message)
            if not retrieve:
                return {"recalled_memory": ""}
            facts = semantic.recall(query, group_id=self._group)
            if not facts:
                return {"recalled_memory": ""}
            block = "## What you remember about the user\n" + "\n".join(f"- {f}" for f in facts)
            return {"recalled_memory": block}
        except Exception as exc:  # noqa: BLE001 — memory must never break a turn
            print(f"memory recall skipped: {type(exc).__name__}: {exc}", flush=True)
            return {"recalled_memory": ""}

    # ── inject ──────────────────────────────────────────────────────────────
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> Any:
        recalled = ""
        try:
            recalled = str((request.state or {}).get("recalled_memory") or "")
        except Exception:  # noqa: BLE001 - defensive
            recalled = ""
        if recalled:
            existing = request.system_message
            base = str(getattr(existing, "content", existing) or "")
            request.system_message = SystemMessage(
                content=f"{base}\n\n{recalled}" if base else recalled
            )
        return handler(request)

    # ── consolidate (batched, non-blocking) ─────────────────────────────────
    def after_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        if not semantic.memory_enabled():
            return None
        turns = int(state.get("memory_turns", 0)) + 1
        if turns < _CONSOLIDATE_EVERY:
            return {"memory_turns": turns}
        try:
            text = _recent_exchange(state.get("messages") or [], _CONSOLIDATE_EVERY)
            if text.strip():
                semantic.remember_nowait(text, name="conversation", group_id=self._group)
        except Exception as exc:  # noqa: BLE001 — consolidation must never break a turn
            print(f"memory consolidation skipped: {type(exc).__name__}: {exc}", flush=True)
        return {"memory_turns": 0}
