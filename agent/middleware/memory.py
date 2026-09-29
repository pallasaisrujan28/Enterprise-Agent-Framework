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
import re
from collections.abc import Callable
from concurrent.futures import TimeoutError as FuturesTimeout
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

# How long recall may take before we proceed WITHOUT it. Recall is best-effort:
# a missed recall is recoverable, a two-minute turn is not. Generous enough that
# a healthy backend always makes it (recall is ~1-2s when the account isn't
# throttled), bounded enough that a slow/throttled backend can't hang the turn.
_RECALL_BUDGET_S = float(os.getenv("MEMORY_RECALL_TIMEOUT", "12"))


class MemoryState(AgentState):
    """State this middleware writes. Declared, or LangGraph drops the keys."""

    recalled_memory: NotRequired[str]
    memory_turns: NotRequired[int]
    # Set when recall was wanted but the backend was too slow, so the answer can
    # honestly say it proceeded without long-term memory.
    memory_skipped: NotRequired[bool]


def _latest_human(messages: list[Any]) -> str:
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            return m.text if hasattr(m, "text") else str(m.content)
    return ""


# gpt-oss (a reasoning model) emits a thinking block before its answer. It shows
# up in the message text as a <reasoning>…</reasoning> span (sometimes with a
# stray leading char, or left unclosed if the block ran to the end). That scratch
# pad is not durable knowledge — consolidating it pollutes the graph with facts
# like "Assistant: .<reasoning>Attempt to fetch…". Strip it before memory sees it.
_REASONING = re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL | re.IGNORECASE)
_REASONING_UNCLOSED = re.compile(r"<reasoning>.*\Z", re.DOTALL | re.IGNORECASE)


# DeepSeek echoes its tool-call markup into text ("<｜DSML｜function_calls").
# Transport noise — it was landing verbatim in stored episodes.
_DSML = re.compile(r"<[｜|]DSML[｜|][^\n]*", re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    """Remove reasoning-model scratchpad so only the actual answer is consolidated."""
    text = _REASONING.sub("", text)
    text = _REASONING_UNCLOSED.sub("", text)  # a block left open to end-of-text
    text = _DSML.sub("", text)
    return text.strip(" \t\n.")


def _content_text(content: Any) -> str:
    """Flatten a message's content (str, or a list of blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content or "")


# An answer that IS a failure/apology, not knowledge. Consolidating "I couldn't
# reach Gmail" as a durable fact is exactly the junk we're trying to keep out —
# it later reads back as if the *user's* Gmail is permanently unreachable.
_ERROR_ANSWER = re.compile(
    r"\b("
    r"i\s+(?:could\s*n'?t|can\s*not|can'?t|was unable to|am unable to|wasn'?t able to|"
    r"do\s*n'?t have access|couldn'?t access|failed to|ran into (?:an|a)|encountered (?:an|a))|"
    r"sorry|apolog|something went wrong|an error occurred|"
    r"unable to (?:complete|access|reach|retrieve)|"
    r"(?:is|are)(?:n'?t| not) (?:currently )?(?:configured|connected|set up|available|enabled)"
    r")\b",
    re.IGNORECASE,
)

# A pure acknowledgement/greeting — nothing durable to learn from it.
_TRIVIAL_ANSWER = re.compile(
    r"^(hi|hey|hello|yo|thanks?|thank you|ok(?:ay)?|got it|sure|no problem|"
    r"you'?re welcome|np|yep|yeah|yes|no|cool|great|done)\b[\s!.,]*$",
    re.IGNORECASE,
)


def _tool_output_failed(output: str) -> bool:
    """Mirror the dashboard's error classification: a tool result that reports a
    failure. Tools report honestly (ToolErrorMiddleware makes failures readable),
    so the words carry the signal."""
    low = (output or "").lower()
    return low.startswith("error") or "failed" in low or "timed out" in low or "unavailable" in low


def _final_turn_all_tools_failed(messages: list[Any]) -> bool:
    """True when the last turn ran tools and EVERY one of them failed. Walks back
    from the end to the last human message — that span is 'this turn'."""
    tool_outputs: list[str] = []
    for m in reversed(messages):
        t = getattr(m, "type", "")
        if t == "human":
            break
        if t == "tool":
            tool_outputs.append(_content_text(getattr(m, "content", "")))
    if not tool_outputs:
        return False
    return all(_tool_output_failed(x) for x in tool_outputs)


def _final_answer(messages: list[Any]) -> str:
    """The last assistant answer, reasoning-scratchpad stripped."""
    for m in reversed(messages):
        if getattr(m, "type", "") == "ai":
            raw = m.text if hasattr(m, "text") else str(getattr(m, "content", ""))
            return _strip_reasoning(raw)
    return ""


def _worth_remembering(messages: list[Any]) -> tuple[bool, str]:
    """Quality gate for consolidation — keep only turns worth remembering.

    Consolidation runs the recent exchange through Graphiti's extractor, which
    happily mints "facts" from whatever it's given. So we refuse to feed it:
      - an empty/absent answer (nothing to learn),
      - a trivial acknowledgement or greeting,
      - an error/apology answer ("I couldn't reach Gmail") — a transient failure
        must never become a durable fact about the user,
      - a turn whose tools all failed AND whose answer is thin (a wash).
    A genuine, substantive answer that happens to follow a RECOVERED tool failure
    is kept — the failure isn't in the answer text, so it won't be stored.

    Returns (keep, reason). `reason` is for the skip log only.
    """
    answer = _final_answer(messages).strip()
    if not answer:
        return False, "no substantive answer"
    if _TRIVIAL_ANSWER.match(answer):
        return False, "trivial turn"
    if _ERROR_ANSWER.search(answer):
        return False, "error/apology answer"
    if _final_turn_all_tools_failed(messages) and len(answer) < 80:
        return False, "tool failure with thin answer"
    return True, ""


_NARRATION_CHARS = 300
_MAX_ASSISTANT_CHARS = 1200


def _recent_exchange(messages: list[Any], pairs: int) -> str:
    """The last `pairs` user TURNS as plain text, for consolidation.

    Windowed by HUMAN messages, not by message count. An agentic turn has many
    assistant messages ("Let me search…", tool call, "Now let me organise…"), so
    counting messages cut the user's question out of the episode and Graphiti
    extracted facts with no idea what was asked — e.g. "The Assistant needs to
    search for emails". The user line is the context that makes facts about the
    USER; it must always be in the window."""
    start = 0
    seen = 0
    for i in range(len(messages) - 1, -1, -1):
        if getattr(messages[i], "type", "") == "human":
            seen += 1
            start = i
            if seen >= pairs:
                break
    kept: list[str] = []
    for m in messages[start:]:
        t = getattr(m, "type", "")
        if t == "human":
            kept.append(f"User: {m.text if hasattr(m, 'text') else m.content}")
        elif t == "ai":
            raw = m.text if hasattr(m, "text") else str(m.content)
            text = _strip_reasoning(raw)
            # Narration that only precedes a tool call ("Let me search…") carries
            # no knowledge; it just dilutes the episode.
            if getattr(m, "tool_calls", None) and len(text) < _NARRATION_CHARS:
                continue
            # A long answer (an email table, a product list) is mostly retrieved
            # data, not facts about the user. Graphiti's guidance is compact
            # episodes: big ones drift entity names and drop edges ("Target entity
            # not found"). Keep the head, which is where the answer's gist lives.
            if len(text) > _MAX_ASSISTANT_CHARS:
                text = text[:_MAX_ASSISTANT_CHARS].rstrip() + " […]"
            if text:
                kept.append(f"Assistant: {text}")
    return "\n".join(kept)


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

        # THE GATE NEVER BLOCKS. It is a cheap optimizer that decides WHETHER to
        # recall — not the context itself. So on any error/slowness it fails OPEN
        # (retrieve anyway): a stale memory beats a lost one, and we must not turn
        # a gate hiccup into "no context". should_retrieve already fails open on
        # exception; this guard covers it defensively.
        try:
            retrieve, query = retrieval_gate.should_retrieve(self._router, message)
        except Exception as exc:  # noqa: BLE001 — gate failure => retrieve anyway
            print(f"memory gate failed open: {type(exc).__name__}: {exc}", flush=True)
            retrieve, query = True, message
        if not retrieve:
            return {"recalled_memory": ""}

        # RECALL IS THE CONTEXT — give it a real but BOUNDED budget. If the
        # backend is healthy it returns in ~1-2s; if it is throttled/slow, we wait
        # up to _RECALL_BUDGET_S and then proceed WITHOUT it, flagging the skip so
        # the answer can disclose it honestly rather than silently guessing.
        try:
            facts = semantic.recall(query, group_id=self._group, timeout=_RECALL_BUDGET_S)
        except FuturesTimeout:
            print(
                f"memory recall exceeded {_RECALL_BUDGET_S:.0f}s budget — answering "
                "without long-term memory this turn",
                flush=True,
            )
            return {"recalled_memory": "", "memory_skipped": True}
        except Exception as exc:  # noqa: BLE001 — memory must never break a turn
            print(f"memory recall skipped: {type(exc).__name__}: {exc}", flush=True)
            return {"recalled_memory": ""}

        if not facts:
            return {"recalled_memory": "", "memory_skipped": False}
        block = "## What you remember about the user\n" + "\n".join(f"- {f}" for f in facts)
        return {"recalled_memory": block, "memory_skipped": False}

    # ── inject ──────────────────────────────────────────────────────────────
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> Any:
        recalled = ""
        skipped = False
        try:
            state = request.state or {}
            recalled = str(state.get("recalled_memory") or "")
            skipped = bool(state.get("memory_skipped"))
        except Exception:  # noqa: BLE001 - defensive
            recalled, skipped = "", False

        addition = recalled
        if skipped:
            # Honest disclosure: recall was wanted but the backend was too slow.
            # Tell the model so it can flag it IF the answer leans on remembered
            # context, rather than silently answering as if it had checked.
            addition = (
                "## Long-term memory unavailable this turn\n"
                "Your durable memory was too slow to reach and was skipped. If the "
                "answer depends on something you'd remember about the user, say you "
                "couldn't access your memory this turn rather than guessing."
            )
        if addition:
            existing = request.system_message
            base = str(getattr(existing, "content", existing) or "")
            request.system_message = SystemMessage(
                content=f"{base}\n\n{addition}" if base else addition
            )
        return handler(request)

    # ── consolidate (batched, non-blocking) ─────────────────────────────────
    def after_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        if not semantic.memory_enabled():
            return None
        turns = int(state.get("memory_turns", 0)) + 1
        if turns < _CONSOLIDATE_EVERY:
            return {"memory_turns": turns}
        messages = state.get("messages") or []

        # QUALITY GATE. Consolidation is not free of judgement — a failed/trivial
        # turn stored here reads back later as a bogus "fact". Skip those; reset
        # the counter either way so the next good turn gets a fresh window.
        keep, reason = _worth_remembering(messages)
        if not keep:
            print(f"memory consolidation skipped: {reason}", flush=True)
            return {"memory_turns": 0}
        try:
            text = _recent_exchange(messages, _CONSOLIDATE_EVERY)
            if text.strip():
                semantic.remember_nowait(text, name="conversation", group_id=self._group)
        except Exception as exc:  # noqa: BLE001 — consolidation must never break a turn
            print(f"memory consolidation skipped: {type(exc).__name__}: {exc}", flush=True)
        return {"memory_turns": 0}
