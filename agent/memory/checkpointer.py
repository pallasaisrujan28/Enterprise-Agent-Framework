"""
AgentCore memory checkpointer — persists LangGraph thread state across
sessions so the agent remembers previous conversations.

AgentCore Memory is keyed by (thread_id, actor_id). In EAF:
  thread_id  = conversation ID (UUID)
  actor_id   = user identifier

This checkpointer replaces LangGraph's default InMemorySaver. The graph
state is stored in AgentCore (eu-west-2) and restored automatically on
the next call with the same thread_id.

Usage:
    from agent.memory.checkpointer import AgentCoreMemorySaver
    checkpointer = AgentCoreMemorySaver()
    agent = create_react_agent(llm, tools=tools, checkpointer=checkpointer)
"""

from __future__ import annotations

import os

# AgentCoreMemorySaver is provided by langchain-aws >= 0.2 when the
# agentcore extra is installed, or via the aws-agentcore-client package.
# Import is deferred so the rest of the codebase loads even without it.


def get_checkpointer():
    """
    Return an AgentCoreMemorySaver instance if the package is available,
    otherwise fall back to LangGraph's InMemorySaver with a warning.

    AgentCoreMemorySaver requires:
      - AGENTCORE_MEMORY_ID env var (the AgentCore Memory resource ARN)
      - IRSA / pod identity with bedrock-agentcore:* permissions
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
