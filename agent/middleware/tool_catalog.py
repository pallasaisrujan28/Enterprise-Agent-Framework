"""Tool catalog — load specialist tools on demand instead of on every call.

WHY. Every model call carries the JSON schema of every bound tool. Measured on
this agent: 19 tools, ~5,300 tokens of schema per call, paid on every step of
every turn whether or not the turn touches email, calendar or memory. As tools
are added (Gmail write, local-machine tools) that cost only grows.

HOW. Tools are split in two:
  core      always visible: filesystem, planning, delegation, web search/fetch,
            and `find_tools` itself.
  deferred  registered with the agent (so they can run) but HIDDEN from the
            model's tool list until unlocked.

`find_tools(query)` searches the deferred tools' descriptions SEMANTICALLY:
each "name: description" is embedded once per process (Bedrock Titan v2, the
embedder memory already uses), the query is embedded, and tools are ranked by
cosine similarity plus a small keyword-overlap bonus. The top matches are
unlocked for the rest of the thread (state key `unlocked_tools`, persisted by the
checkpointer) and appear in the tool list from the next model step. If the
embedder is unavailable, ranking falls back to keyword overlap alone, so the
catalog degrades rather than breaking.

The prompt carries a one-line index of capability AREAS (not schemas), so the
model knows to look. A deferred tool the model calls by name without searching
still runs — hiding is a context-budget measure, not a permission boundary;
permissions are enforced by the tools themselves and by HumanInTheLoop gates.

Custom middleware, per coding-standards: langchain's LLMToolSelectorMiddleware
needs an extra LLM call before EVERY turn and is not semantic retrieval;
ProviderToolSearchMiddleware relies on provider-native tool search, which Kimi
on Bedrock does not offer.
"""

from __future__ import annotations

import math
import re
import threading
from collections.abc import Callable, Sequence
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain.tools import ToolRuntime
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command

Embed = Callable[[str], list[float]]

# Tools returned per find_tools call.
TOP_K = 3
# Weight of keyword overlap added to cosine similarity. Small: it breaks ties
# and rescues exact-name queries ("read_email") without overriding meaning.
_LEXICAL_WEIGHT = 0.15
# A result must score at least this fraction of the best match to be loaded.
_RELATIVE_CUTOFF = 0.8


def _union(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Reducer: unlocks only accumulate, so two find_tools calls in one step merge."""
    out = list(left or [])
    out += [n for n in (right or []) if n not in out]
    return out


class CatalogState(AgentState):
    """State this middleware writes. Declared, or LangGraph drops the key."""

    unlocked_tools: NotRequired[Annotated[list[str], _union]]


_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower().replace("_", " ")))


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _titan_embed() -> Embed:
    """The memory embedder's Titan v2 call, reused (bounded retries/timeouts)."""
    from agent.memory.graphiti_clients import BedrockEmbedder

    return BedrockEmbedder()._embed_one


def _tool_text(tool: BaseTool) -> str:
    return f"{tool.name}: {tool.description or ''}".strip()


class ToolCatalog:
    """The deferred tools plus their (lazily computed, cached) embeddings."""

    def __init__(
        self, tools: Sequence[BaseTool], areas: dict[str, str], embed: Embed | None = None
    ) -> None:
        self.tools = {t.name: t for t in tools}
        # tool name -> capability area ("email", "calendar", ...), for the prompt index.
        self.areas = areas
        self._embed = embed
        self._vectors: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._embed_failed = False

    def _embedder(self) -> Embed | None:
        if self._embed is None and not self._embed_failed:
            try:
                self._embed = _titan_embed()
            except Exception:  # noqa: BLE001 — no embedder => keyword ranking
                self._embed_failed = True
        return self._embed

    def _vector(self, name: str, embed: Embed) -> list[float]:
        with self._lock:
            if name not in self._vectors:
                self._vectors[name] = embed(_tool_text(self.tools[name]))
            return self._vectors[name]

    def search(self, query: str, k: int = TOP_K) -> list[tuple[str, float]]:
        """(tool name, score), best first. Semantic when the embedder works."""
        qwords = _words(query)
        lexical = {
            n: (len(qwords & _words(_tool_text(t))) / len(qwords) if qwords else 0.0)
            for n, t in self.tools.items()
        }
        scores = dict(lexical)
        embed = self._embedder()
        if embed is not None:
            try:
                qv = embed(query)
                scores = {
                    n: _cosine(qv, self._vector(n, embed)) + _LEXICAL_WEIGHT * lexical[n]
                    for n in self.tools
                }
            except Exception:  # noqa: BLE001 — a failed embedding call => keyword ranking
                scores = dict(lexical)
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        if not ranked or ranked[0][1] <= 0:
            return []
        # Relative cutoff: only tools close to the best match, so "read my email"
        # loads the email tools and not the calendar one that merely ranks third.
        floor = ranked[0][1] * _RELATIVE_CUTOFF
        return [(n, s) for n, s in ranked[:k] if s >= floor]

    def index_line(self) -> str:
        areas = sorted(set(self.areas.values()))
        return (
            "More tools are available on demand: "
            + ", ".join(areas)
            + ". They are not loaded until needed — call `find_tools` with a short "
            "description of what you need (e.g. 'read my email', 'what is on my "
            "calendar'), then call the tools it returns."
        )


def build_find_tools(catalog: ToolCatalog) -> BaseTool:
    def find_tools(query: str, runtime: ToolRuntime) -> Command:
        hits = catalog.search(query)
        names = [n for n, _ in hits]
        lines = [
            f"- {n}: {(catalog.tools[n].description or '').strip().splitlines()[0][:160]}"
            for n in names
        ]
        print(f"tool catalog: {query[:80]!r} -> {names}", flush=True)
        body = (
            "Loaded these tools; they are available from your next step — call them directly:\n"
            + "\n".join(lines)
            if names
            else "No matching tools."
        )
        return Command(
            update={
                "unlocked_tools": names,
                "messages": [
                    ToolMessage(
                        content=body, tool_call_id=runtime.tool_call_id or "", name="find_tools"
                    )
                ],
            }
        )

    return StructuredTool.from_function(
        func=find_tools,
        name="find_tools",
        description=(
            "Find and load specialist tools that are not currently in your tool list "
            "(email, calendar, long-term memory management, persona rules, skill "
            "authoring, ...). Give a short description of the capability you need. "
            "The best-matching tools become callable from your next step."
        ),
    )


class ToolCatalogMiddleware(AgentMiddleware[CatalogState, ContextT, ResponseT]):
    """Hides deferred tools from the model until `find_tools` unlocks them."""

    name = "ToolCatalogMiddleware"
    state_schema = CatalogState

    def __init__(self, catalog: ToolCatalog) -> None:
        super().__init__()
        self.catalog = catalog
        self.tools = [build_find_tools(catalog)]

    def _filter(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        state: dict[str, Any] = dict(request.state or {})
        unlocked = set(state.get("unlocked_tools") or [])
        hidden = set(self.catalog.tools) - unlocked
        tools = [t for t in request.tools if getattr(t, "name", None) not in hidden]
        index = self.catalog.index_line()
        sys_msg = request.system_message
        base = sys_msg.content if sys_msg is not None else ""
        # Keep content blocks (e.g. cache markers) intact when the prompt is a list.
        content: Any = (
            [*base, {"type": "text", "text": index}]
            if isinstance(base, list)
            else f"{base}\n\n{index}".strip()
        )
        return request.override(tools=tools, system_message=SystemMessage(content=content))

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> Any:
        return handler(self._filter(request))

    async def awrap_model_call(self, request: ModelRequest[ContextT], handler: Any) -> Any:
        return await handler(self._filter(request))
