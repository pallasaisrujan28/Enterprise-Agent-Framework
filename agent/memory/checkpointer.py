"""
AgentCore memory checkpointer — persists LangGraph thread state across
sessions so the agent remembers previous conversations.

Usage:
    from agent.memory.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()
    agent = create_deep_agent(..., checkpointer=checkpointer)
"""

from __future__ import annotations

import os


def get_checkpointer():
    """
    Return an AgentCoreMemorySaver if AGENTCORE_MEMORY_ID is set,
    otherwise fall back to LangGraph's in-process MemorySaver with a warning.
    """
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if not memory_id:
        import warnings

        from langgraph.checkpoint.memory import MemorySaver

        warnings.warn(
            "AGENTCORE_MEMORY_ID not set — using in-process MemorySaver. "
            "State will NOT persist across pod restarts.",
            stacklevel=2,
        )
        return MemorySaver()

    try:
        from langchain_aws.memory.agentcore import AgentCoreMemorySaver  # type: ignore[import]

        return AgentCoreMemorySaver(memory_id=memory_id)
    except ImportError:
        import warnings

        from langgraph.checkpoint.memory import MemorySaver

        warnings.warn(
            "AgentCoreMemorySaver not available (install langchain-aws[agentcore]). "
            "Falling back to in-process MemorySaver.",
            stacklevel=2,
        )
        return MemorySaver()
