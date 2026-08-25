"""
Agent brain — deepagents harness on top of LangGraph.

deepagents provides (used as-is, no custom wiring):
  - Skills loading from skills/ directory
  - TodoListMiddleware: structured task tracking (pending/in_progress/completed)
  - FilesystemMiddleware: S3 workspace read/write/list
  - task tool: spawns isolated sub-agents with fresh context windows
  - HITL: interrupt() for human-in-the-loop approval

Custom (EAF-specific, kept because deepagents has no equivalent):
  - web_search: SearXNG aggregated web search (all free, no API keys)
  - fetch_and_store: Crawl4AI → semantic chunks → Qdrant session memory
  - search_memory: Qdrant semantic query over content already fetched
  - Memory: Qdrant working memory + AgentCore checkpointer (see agent/memory/)
  - Guardrails + obligation gate (applied in __main__, not here)
"""

from __future__ import annotations

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware, TodoListMiddleware
from langchain_aws import ChatBedrockConverse

from agent.memory.checkpointer import get_checkpointer
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
WORKSPACE_BUCKET = os.getenv("WORKSPACE_BUCKET", "")

# skills/ dir is at repo root — deepagents loads all .md files from it automatically.
SKILLS_DIR = str(Path(__file__).parents[1] / "skills")

# Checkpointer is built once and reused across requests.
# AgentCore if AGENTCORE_MEMORY_ID is set, MemorySaver otherwise.
_checkpointer = get_checkpointer()


def _build_middleware() -> list:
    middleware: list = [TodoListMiddleware()]

    if WORKSPACE_BUCKET:
        try:
            from agent.filesystem.s3_backend import S3WorkspaceBackend
            middleware.append(
                FilesystemMiddleware(
                    backend=S3WorkspaceBackend(bucket=WORKSPACE_BUCKET, region=REGION),
                    # Tools exposed to the agent: read, write, list — no delete
                    tools=["read_file", "write_file", "ls"],
                )
            )
        except Exception:
            # Workspace bucket not configured — filesystem tools unavailable
            pass

    return middleware


def build_agent():
    """
    Build the EAF agent using the deepagents harness.
    Returns a compiled LangGraph graph ready for .invoke() / .stream().

    Called once per request in __main__ (stateless — checkpointer handles
    cross-request state via thread_id).
    """
    return create_deep_agent(
        model=ChatBedrockConverse(model=MODEL_ID, region_name=REGION),
        tools=[web_search, fetch_and_store, search_memory],
        middleware=_build_middleware(),
        checkpointer=_checkpointer,
        skills_dir=SKILLS_DIR,
    )
