"""
Agent brain — deepagents harness wired to Bedrock via ChatBedrockConverse.

Middleware stack (assembled by create_deep_agent + user-supplied):

  deepagents built-in (always-on, no config needed):
    FilesystemMiddleware    — read_file, write_file, ls, grep, glob, edit, execute
    SubAgentMiddleware      — task tool (delegation, isolated sub-agents)
    SummarizationMiddleware — auto-compacts context when token budget exceeded
    PatchToolCallsMiddleware— cleans up dangling tool calls (internal)
    Prompt caching          — Anthropic/Bedrock cache control (automatic)

  langchain built-in (user-supplied):
    TodoListMiddleware      — write_todos tool for structured task tracking
                              from langchain.agents.middleware.todo

  EAF custom middleware:
    ContentOverflowMiddleware — offloads large tool results to /workspace/
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain.agents.middleware.todo import TodoListMiddleware  # type: ignore[import-not-found]

from agent.backends import EAFBackend
from agent.memory.checkpointer import get_checkpointer
from agent.middleware.content import ContentOverflowMiddleware
from agent.model import get_model
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
            "/skills": FilesystemBackend(root=str(Path(__file__).parents[1])),  # type: ignore[call-arg],
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
            ContentOverflowMiddleware(backend=backend),
        ],
        checkpointer=_checkpointer,
        skills_dir=SKILLS_DIR,
    )
