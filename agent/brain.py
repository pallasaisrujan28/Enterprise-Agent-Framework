"""
Agent brain — deepagents harness wired to Bedrock via ChatBedrockConverse.

Middleware stack (assembled by create_deep_agent + user-supplied):

  deepagents built-in — create_deep_agent appends these itself, verified against
  the pinned version rather than assumed:
    SkillsMiddleware        — loads skills/ and discloses them progressively
    FilesystemMiddleware    — read_file, write_file, ls, grep, glob, edit, execute
    SubAgentMiddleware      — task tool (delegation, isolated sub-agents)
    MemoryMiddleware        — long-term memory sources
    PatchToolCallsMiddleware— cleans up dangling tool calls
    HumanInTheLoopMiddleware— when interrupt_on is set
    Prompt caching          — Bedrock cache control

  user-supplied:
    TodoListMiddleware      — write_todos, from langchain.agents.middleware.todo
    SummarizationMiddleware — context compaction and tool-result offload.
                              deepagents does NOT add this automatically, despite
                              an earlier note here claiming it did; it is opt-in
                              and is passed below.

NO CUSTOM MIDDLEWARE. Per .kiro/steering/coding-standards.md, a component is only
written here when deepagents has none. The one that used to live in this list,
ContentOverflowMiddleware, was both invalid — a plain class with no `name`, so the
harness rejected it and every build raised AttributeError — and redundant, since
SummarizationMiddleware already offloads history and clips oversized tool results.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware import SummarizationMiddleware
from langchain.agents.middleware import ToolErrorMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware  # type: ignore[import-not-found]
from langchain.agents.middleware.types import AgentMiddleware

from agent.backends import EAFBackend
from agent.delegation import build_interpreter_middleware, build_subagents
from agent.memory.checkpointer import get_checkpointer
from agent.middleware.obligations import ObligationGateMiddleware
from agent.model import get_fast_model, get_model, get_model_named
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
WORKSPACE_BUCKET = os.getenv("WORKSPACE_BUCKET", "")
SKILLS_DIR = str(Path(__file__).parents[1] / "skills")
OBLIGATIONS_DIR = str(Path(__file__).parents[1] / "obligations")

_checkpointer = get_checkpointer()


def _tool_error_message(exc: Exception, request: Any) -> str:
    """Turn a tool exception into an observation the model can act on.

    The handler ToolErrorMiddleware calls per failure. Returning a string makes
    the failure a `ToolMessage(status="error")` the model reads and works around;
    returning None would re-raise and end the turn, which is the behaviour being
    fixed. Names the tool so the model knows which call not to simply retry.
    """
    tool_call = getattr(request, "tool_call", None) or {}
    tool = tool_call.get("name") if isinstance(tool_call, dict) else None
    return (
        f"Error running tool {tool or '?'}: {type(exc).__name__}: {exc}. "
        "This tool is unavailable right now; answer without it or use another."
    )


def _build_backend() -> CompositeBackend:
    """
    /workspace → EAFBackend (S3, persistent)
    /skills    → FilesystemBackend (pod disk, read-only)
    default    → StateBackend (RAM, ephemeral scratch)
    """
    if not WORKSPACE_BUCKET:
        warnings.warn(
            "WORKSPACE_BUCKET not set — /workspace writes use in-memory StateBackend.",
            stacklevel=2,
        )
        workspace_backend: EAFBackend | StateBackend = StateBackend()
    else:
        workspace_backend = EAFBackend(bucket=WORKSPACE_BUCKET, region=REGION)

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace": workspace_backend,
            "/skills": FilesystemBackend(),
        },
    )


def build_agent(model_id: str | None = None):
    """Build the EAF agent. Called once per request — stateless.

    `model_id` lets a caller switch model for one conversation; the dashboard's
    picker uses it. It is validated against the verified list rather than passed
    through, because an unknown id fails at Bedrock with a far less useful error.
    """
    backend = _build_backend()

    # Annotated, because a bare list literal makes mypy JOIN the element types and
    # then reject every member that is not the joined one. The annotation says what
    # create_deep_agent actually accepts.
    middleware: list[AgentMiddleware[Any, Any, Any]] = [
        TodoListMiddleware(),
        # A failing tool comes back as an error MESSAGE the model can read and
        # work around, not an exception that ends the turn. This was not
        # academic: web_search succeeded, the model also called fetch_and_store,
        # Firecrawl is not in the local stack, and the ConnectError killed the
        # whole turn — losing the good search result too. langchain ships this;
        # the topology's old note about "we have not wired ToolErrorMiddleware" is
        # now wired.
        #
        # on_error returns a string, which turns the exception into a
        # ToolMessage(status="error"). Returning None would re-raise, which is the
        # behaviour we are fixing. The tool name is included so the model knows
        # which call to avoid retrying.
        ToolErrorMiddleware(on_error=_tool_error_message),
        # Replaces the repo's own ContentOverflowMiddleware, which was a plain
        # class rather than an AgentMiddleware subclass — it had no `name`, so the
        # harness rejected it and every build raised AttributeError. It was also
        # solving a problem deepagents already solves: this middleware offloads
        # conversation history to the backend and clips oversized tool results on
        # the overflow path.
        #
        # Summarising runs on the FAST model deliberately. It is cheap mechanical
        # work and it fires on long sessions — the worst place to pay flagship
        # rates.
        SummarizationMiddleware(model=get_fast_model(), backend=backend),
        # The obligation gate. Inside the middleware stack rather than wrapped
        # around the agent, so EVERY entry point gets it: the HTTP service and the
        # dashboard both call build_agent(), and neither can skip it. Two doors
        # with different protections was a real defect before this.
        #
        # Routing uses the fast model — choosing which obligation policies apply
        # is a classification over one line per policy, not an answer. Policies
        # are enforcement, declared in obligations/*.yaml, distinct from the
        # skills below which are pure capability disclosed by SkillsMiddleware.
        ObligationGateMiddleware(router=get_fast_model(), policies_dir=OBLIGATIONS_DIR),
        # The interpreter that makes the sub-agent roster DYNAMIC (adds `eval`
        # and the `task()` global) and bridges these read-only tools into
        # interpreter code via PTC. Defined in agent/delegation so this builder
        # stays plumbing, not policy. PTC allowlist is a permission boundary —
        # only these retrieval tools, nothing that mutates durable state.
        build_interpreter_middleware([web_search, fetch_and_store, search_memory]),
    ]

    return create_deep_agent(
        model=get_model_named(model_id) if model_id else get_model(),
        tools=[web_search, fetch_and_store, search_memory],
        backend=backend,
        middleware=middleware,
        checkpointer=_checkpointer,
        # The subagent roster the interpreter's `task()` dispatches. Defined in
        # agent/delegation, not here — this builder only assembles the harness.
        subagents=build_subagents(),
        # `skills`, a list of SOURCES — not `skills_dir`, which this called and
        # which create_deep_agent has never accepted in the pinned version. The
        # whole harness raised TypeError on every build, so no turn had ever run.
        # deepagents turns this into a SkillsMiddleware internally, which is the
        # progressive-disclosure loader we should be using rather than our own.
        skills=[SKILLS_DIR],
    )
