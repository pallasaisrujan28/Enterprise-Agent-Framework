"""
Conversation checkpointer — persists LangGraph thread state (the message
history of each chat thread) so a conversation survives a process restart.

Selection, first match wins:
  AGENTCORE_MEMORY_ID set  → AgentCoreMemorySaver (managed, for the cluster)
  CHECKPOINT_DB set        → SqliteSaver at that path (local, durable)
  neither                  → MemorySaver (in-process; LOST on restart — warned)

Before this, only the first and last existed — and AgentCoreMemorySaver is not
in the installed langchain-aws, so every run silently used MemorySaver and the
dashboard forgot every thread on restart. SQLite is LangGraph's own saver
(langgraph-checkpoint-sqlite), install with `pip install -e '.[local]'`.

Usage:
    from agent.memory.checkpointer import get_checkpointer
    agent = create_deep_agent(..., checkpointer=get_checkpointer())
"""

from __future__ import annotations

import contextlib
import os
import warnings
from pathlib import Path
from typing import Any


def _memory_saver(reason: str) -> Any:
    from langgraph.checkpoint.memory import MemorySaver

    warnings.warn(
        f"{reason} — using in-process MemorySaver. Threads will NOT persist.", stacklevel=3
    )
    return MemorySaver()


def _sqlite_saver(path: str) -> Any:
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(path).expanduser()
    db.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the dashboard serves each request on its own
    # thread (ThreadingHTTPServer). SqliteSaver serialises access with its own
    # lock, so sharing one connection across threads is safe.
    conn = sqlite3.connect(str(db), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    with contextlib.suppress(OSError):
        os.chmod(db, 0o600)  # conversation history is private data
    return saver


def get_checkpointer() -> Any:
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if memory_id:
        try:
            from langchain_aws.memory.agentcore import (
                AgentCoreMemorySaver,  # type: ignore[import-not-found]
            )

            return AgentCoreMemorySaver(memory_id=memory_id)
        except ImportError:
            warnings.warn(
                "AGENTCORE_MEMORY_ID is set but AgentCoreMemorySaver is not installed.",
                stacklevel=2,
            )

    db_path = os.getenv("CHECKPOINT_DB")
    if db_path:
        try:
            return _sqlite_saver(db_path)
        except ImportError:
            return _memory_saver("CHECKPOINT_DB set but langgraph-checkpoint-sqlite not installed")

    return _memory_saver("No AGENTCORE_MEMORY_ID or CHECKPOINT_DB")
