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

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware import SummarizationMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware  # type: ignore[import-not-found]

from agent.backends import EAFBackend
from agent.memory.checkpointer import get_checkpointer
from agent.model import get_fast_model, get_model
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
WORKSPACE_BUCKET = os.getenv("WORKSPACE_BUCKET", "")
SKILLS_DIR = str(Path(__file__).parents[1] / "skills")

_checkpointer = get_checkpointer()


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


def build_agent():
    """Build the EAF agent. Called once per request — stateless."""
    backend = _build_backend()

    return create_deep_agent(
        model=get_model(),
        tools=[web_search, fetch_and_store, search_memory],
        backend=backend,
        middleware=[
            TodoListMiddleware(),
            # Replaces the repo's own ContentOverflowMiddleware, which was a plain
            # class rather than an AgentMiddleware subclass — it had no `name`, so
            # the harness rejected it and every build raised AttributeError. It was
            # also solving a problem deepagents already solves: this middleware
            # offloads conversation history to the backend and clips oversized tool
            # results on the overflow path.
            #
            # Summarising runs on the FAST model deliberately. It is cheap
            # mechanical work, and it fires on long sessions — the worst place to
            # be paying flagship rates.
            SummarizationMiddleware(model=get_fast_model(), backend=backend),
        ],
        checkpointer=_checkpointer,
        # `skills`, a list of SOURCES — not `skills_dir`, which this called and
        # which create_deep_agent has never accepted in the pinned version. The
        # whole harness raised TypeError on every build, so no turn had ever run.
        # deepagents turns this into a SkillsMiddleware internally, which is the
        # progressive-disclosure loader we should be using rather than our own.
        skills=[SKILLS_DIR],
    )
