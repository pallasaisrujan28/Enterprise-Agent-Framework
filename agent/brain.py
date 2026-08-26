"""
Agent brain — deepagents harness wired to Bedrock via ChatBedrockConverse.

What this file does:
  1. Builds the CompositeBackend:
       /workspace → EAFBackend (S3, persistent workspace)
       /skills    → FilesystemBackend (pod disk, read-only, baked in image)
       default    → StateBackend (in-memory scratch, ephemeral)

  2. Calls create_deep_agent with:
       model      — ChatBedrockConverse (IRSA auth, eu-west-2, no stored creds)
       backend    — the CompositeBackend above
       tools      — web_search, fetch_and_store, search_memory
       middleware — TodoListMiddleware (task tracking)
       checkpointer — AgentCore or in-process MemorySaver (see memory/checkpointer.py)
       skills_dir — loads skills/*.md automatically

deepagents wires the rest: skills, task tool (delegation), HITL, file tools.

Model call path:
  create_deep_agent → LangGraph StateGraph
    → ChatBedrockConverse.invoke(messages)
    → Bedrock bedrock-runtime.eu-west-2.amazonaws.com
    → anthropic.claude-3-5-sonnet-20241022-v2:0 (or BEDROCK_MODEL_ID)
  Auth: pod IRSA role → sts:AssumeRoleWithWebIdentity → bedrock:InvokeModel
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware import TodoListMiddleware
from langchain_aws import ChatBedrockConverse

from agent.backends import EAFBackend
from agent.memory.checkpointer import get_checkpointer
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

# ── Config ─────────────────────────────────────────────────────────────────────

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
WORKSPACE_BUCKET = os.getenv("WORKSPACE_BUCKET", "")

# skills/ lives at the repo root; baked into the Docker image at /app/skills/
SKILLS_DIR = str(Path(__file__).parents[1] / "skills")

# Checkpointer built once — AgentCore if AGENTCORE_MEMORY_ID is set,
# in-process MemorySaver otherwise (state lost on pod restart).
_checkpointer = get_checkpointer()


# ── Backend ────────────────────────────────────────────────────────────────────


def _build_backend() -> CompositeBackend:
    """
    CompositeBackend routes filesystem calls to the right storage by path prefix.

    /workspace  → EAFBackend (S3)
                  Persistent. Survives pod restarts. Used for reports, outputs,
                  anything the user or agent wants to keep.

    /skills     → FilesystemBackend (pod disk at /app/skills/)
                  Read-only. Skills are baked into the Docker image at build time.
                  The agent can read skills but cannot write to this path.

    default     → StateBackend (LangGraph graph state, RAM)
                  Ephemeral. Used for /scratch/ temp notes during a single session.
                  Disappears when the session ends or the pod restarts.
    """
    if not WORKSPACE_BUCKET:
        warnings.warn(
            "WORKSPACE_BUCKET env var not set. "
            "/workspace writes will use in-memory StateBackend (not persistent). "
            "Set WORKSPACE_BUCKET in k8s/deployment.yaml.",
            stacklevel=2,
        )
        workspace_backend: EAFBackend | StateBackend = StateBackend()
    else:
        workspace_backend = EAFBackend(bucket=WORKSPACE_BUCKET, region=REGION)

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace": workspace_backend,
            "/skills": FilesystemBackend(root=str(Path(__file__).parents[1])),
        },
    )


# ── Agent ──────────────────────────────────────────────────────────────────────


def build_agent():
    """
    Build and return the EAF agent.

    Called once per request in __main__.py. The agent is stateless —
    all cross-request state is handled by the checkpointer via thread_id.

    Model call:
      ChatBedrockConverse → bedrock-runtime.eu-west-2.amazonaws.com
      Auth: IRSA (no stored credentials in the pod)
      Model: BEDROCK_MODEL_ID env var (default: claude-3-5-sonnet)

    Returns a compiled LangGraph graph (deepagents harness).
    Invoke with:
      agent.invoke(
          {"messages": [{"role": "user", "content": "..."}]},
          config={"configurable": {"thread_id": "..."}},
      )
    """
    return create_deep_agent(
        # Model: ChatBedrockConverse calls Bedrock inference endpoint.
        # IRSA auth — no API keys, no stored credentials.
        model=ChatBedrockConverse(model=MODEL_ID, region_name=REGION),
        # Tools: passed to ToolRegistry for semantic selection each turn.
        # Only top-k most relevant tools reach the model context window.
        tools=[web_search, fetch_and_store, search_memory],
        # Backend: CompositeBackend routes /workspace → S3, /skills → pod disk.
        backend=_build_backend(),
        # Middleware: TodoListMiddleware gives the agent structured task tracking.
        middleware=[TodoListMiddleware()],
        # Checkpointer: persists LangGraph state across requests via thread_id.
        checkpointer=_checkpointer,
        # Skills directory: deepagents loads all *.md files from here at startup.
        skills_dir=SKILLS_DIR,
    )
