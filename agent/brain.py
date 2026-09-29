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
from datetime import date
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware import SummarizationMiddleware
from langchain.agents.middleware import ToolErrorMiddleware
from langchain.agents.middleware.types import AgentMiddleware

from agent.backends import EAFBackend
from agent.delegation import (
    DELEGATION_GUIDANCE,
    build_interpreter_middleware,
    build_subagents,
)
from agent.memory import semantic
from agent.memory.checkpointer import get_checkpointer
from agent.memory.tools import manage_memory, save_note
from agent.middleware.context import (
    SUMMARY_KEEP,
    SUMMARY_TRIGGER,
    context_editing,
    planning_middleware,
)
from agent.middleware.debug import PromptDebugMiddleware
from agent.middleware.memory import MemoryMiddleware
from agent.middleware.obligations import ObligationGateMiddleware
from agent.model import get_fast_model, get_model, get_model_named
from agent.skills_engine.author import create_skill
from agent.soul import load_soul, update_soul
from agent.tools.browser_mcp import browser_enabled
from agent.tools.calendar import list_calendar_events
from agent.tools.fetch import fetch_url
from agent.tools.gmail import list_recent_emails, read_email
from agent.tools.searxng_mcp import build_search_tools

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
            # Rooted AT the skills dir so the virtual mount `/skills` maps to it:
            # CompositeBackend strips the route prefix and hands the remainder to
            # this backend, which resolves it under root_dir. The TRAILING SLASH on
            # the key is load-bearing: CompositeBackend remaps returned paths with
            # `route_prefix[:-1]`, so a key of "/skills" (no slash) drops the "s"
            # and emits "/skill/…" paths that no longer route back — the skill was
            # found, then lost on the follow-up download. "/skills/" remaps cleanly.
            "/skills/": FilesystemBackend(root_dir=SKILLS_DIR),
        },
    )


def _system_prompt() -> str:
    """The agent's authored system prompt: a freshness anchor + delegation rules.

    The DATE matters. Without it the model anchors "now" to its training cutoff
    and will confidently return stale facts for time-sensitive questions. Stating
    today's date and telling it to verify anything time-sensitive via web_search
    (with a recency filter) is what turns "correct but outdated" into "current".

    Built here rather than as a constant because the date is only right at build
    time; build_agent runs per request, so a long-lived process still refreshes it
    whenever a new agent is built.
    """
    freshness = (
        f"Today's date is {date.today().isoformat()}. Your training data has a "
        "cutoff and may be out of date. For anything time-sensitive — recent "
        "events, latest versions, current prices, who currently holds a role — do "
        "NOT answer from memory. Use the web search tool and base the answer on "
        "what you find, citing the sources. When searching, prefer plain keyword "
        "queries and use `site:` filters sparingly — not every search engine "
        "supports them, so an over-constrained query can come back empty. If a "
        "search returns no results, rephrase with simpler terms or open the site "
        "directly rather than treating it as an outage."
    )
    # SOUL is the editable persona (agent/soul.py) — the TOP layer, waku-style.
    # It carries character + standing/learned rules and is editable by the agent
    # via update_soul. Loaded fresh each build so a rule the agent saved last turn
    # is in force this turn. The code-built freshness + delegation guidance layer
    # underneath it.
    # GROUNDING. Measured failure: the model presented 18 "exact" emails built
    # from 140-char previews, and re-ran identical searches whose results were
    # already in context. waku's rules (runtime/session.py DEFAULT_SOUL) cover the
    # second; the first is ours.
    grounding = (
        "Grounding: state only what a tool actually returned. Never present a "
        "preview, snippet, or summary as a quote or as 'exact content' — open the "
        "full item first (e.g. read_email) or say you only have a preview. Give "
        "counts only as the tool reported them, and say when results were capped. "
        "Do not re-run a tool call whose result is already in this conversation; "
        "answer from that result."
    )
    prompt = f"{load_soul()}\n\n{freshness}\n\n{grounding}\n\n{DELEGATION_GUIDANCE}"

    # When the browsing/action capability is on, tell the top-level agent to route
    # "do something on a website" tasks to the `browsing` subagent (which owns the
    # browser tools and the confirm-before-commit contract), and to honour that
    # same rule itself: a purchase, booking, or submission is never made without
    # the user's explicit confirmation in chat.
    if browser_enabled():
        prompt += (
            "\n\nYou can act on websites — shopping, booking (flights, tickets, "
            "events), and filling forms like visa applications — by delegating to "
            "the `browsing` subagent, which drives a real browser. Route any task "
            "whose goal is to DO something on a site (not just read it) to it. "
            "CONFIRM BEFORE COMMIT: never let a payment, order, booking, or form "
            "submission happen without first showing the user exactly what will "
            "occur (items, total, recipient, key values) and getting their "
            "explicit confirmation in the chat. If a login, card, or one-time code "
            "is needed and was not provided, ask the user for it rather than "
            "guessing."
        )

    return prompt


def build_agent(model_id: str | None = None):
    """Build the EAF agent. Called once per request — stateless.

    `model_id` lets a caller switch model for one conversation; the dashboard's
    picker uses it. It is validated against the verified list rather than passed
    through, because an unknown id fails at Bedrock with a far less useful error.
    """
    backend = _build_backend()
    # Web search is now an MCP plug-in (SearXNG behind the Model Context
    # Protocol), not an in-repo tool. Loaded once and shared with the delegation
    # roster. See agent/tools/searxng_mcp.py.
    search_tools = build_search_tools()

    # Annotated, because a bare list literal makes mypy JOIN the element types and
    # then reject every member that is not the joined one. The annotation says what
    # create_deep_agent actually accepts.
    middleware: list[AgentMiddleware[Any, Any, Any]] = [
        # Planning, with a short prompt that keeps write_todos for genuinely
        # multi-step work (measured: 4 of 7 calls in an email lookup were todo
        # bookkeeping). See agent/middleware/context.py.
        planning_middleware(),
        # Once the prompt grows past a threshold, older tool OUTPUTS are replaced
        # by a placeholder (latest few kept) — langchain's ContextEditing.
        context_editing(),
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
        #
        # An explicit trigger is REQUIRED: constructed without one, this
        # middleware never summarises proactively (trigger=None → no clauses),
        # only on a context-overflow error. That was the state until now.
        SummarizationMiddleware(
            model=get_fast_model(),
            backend=backend,
            trigger=SUMMARY_TRIGGER,
            keep=SUMMARY_KEEP,
        ),
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
        build_interpreter_middleware([*search_tools, fetch_url]),
    ]

    # Durable memory (Graphiti on Neo4j) — added only when AGENT_MEMORY=on, so
    # tests and Neo4j-less deploys are unaffected. The fast model runs the
    # retrieval gate that decides when a turn needs long-term recall.
    if semantic.memory_enabled():
        middleware.append(MemoryMiddleware(router=get_fast_model()))

    # Debug view of the assembled prompt + tools, only when AGENT_DEBUG_PROMPT is
    # set. Appended last so it sees the prompt after our own layers (memory).
    middleware.append(PromptDebugMiddleware())

    return create_deep_agent(
        model=get_model_named(model_id) if model_id else get_model(),
        # The agency tools that let the agent LEARN by editing its own context:
        #   update_soul   — persist a standing behaviour rule (persona)
        #   save_note     — save a durable fact on request (explicit memory)
        #   manage_memory — search / correct / forget facts (fixes wrong memory)
        #   create_skill  — author a reusable SKILL.md (procedural memory)
        # All on the main agent only, and deliberately NOT in the interpreter's
        # PTC allowlist, because they mutate durable state (persona file, Graphiti,
        # skill files) — that allowlist is read-only by design. The memory tools
        # self-gate: they return a clear message when AGENT_MEMORY is off.
        tools=[
            *search_tools,
            fetch_url,
            update_soul,
            save_note,
            manage_memory,
            create_skill,
            # Read-only Google Calendar + Gmail (shared sign-in). Self-gating:
            # both return a setup hint when not connected, so always safe to expose.
            list_calendar_events,
            list_recent_emails,
            read_email,
        ],
        # Freshness anchor (today's date + "verify time-sensitive facts") plus the
        # delegation guidance that replaces the interpreter's "say 'workflow'"
        # heuristic with a judgement on the shape of the task.
        system_prompt=_system_prompt(),
        backend=backend,
        middleware=middleware,
        checkpointer=_checkpointer,
        # The subagent roster the interpreter's `task()` dispatches. Defined in
        # agent/delegation, not here — this builder only assembles the harness.
        subagents=build_subagents(),
        # The VIRTUAL mount, not the absolute path. Skill sources are resolved
        # THROUGH the backend, and our CompositeBackend routes by the `/skills`
        # prefix to a FilesystemBackend rooted at the real skills dir. Passing the
        # absolute repo path here matched no route and fell through to the empty
        # in-memory StateBackend, so the catalogue always read "No skills
        # available" — the loader was fine; the source path was unroutable.
        skills=["/skills"],
    )
