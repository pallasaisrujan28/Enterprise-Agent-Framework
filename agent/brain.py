"""
Agent brain — LangGraph StateGraph wiring the ReAct loop.

Graph:
  START → agent_node ⟶ tool_node ⟶ agent_node (loop until no tool calls)
                     ↘ END

The agent_node queries ToolRegistry each turn so only the 4 most relevant
tool schemas enter the context window — not all of them.
"""

from __future__ import annotations

import os

from langchain_aws import ChatBedrockConverse
from langgraph.prebuilt import create_react_agent

from agent.filesystem.workspace import read_workspace_file, write_workspace_file
from agent.registry import ToolRegistry
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
TOP_K = int(os.getenv("TOOL_REGISTRY_TOP_K", "4"))

# All tools the agent may use. ToolRegistry embeds descriptions at startup
# and selects the top-k most relevant per turn — no hardcoded list passed
# to the model on every call.
_ALL_TOOLS = [web_search, fetch_and_store, search_memory, read_workspace_file, write_workspace_file]
_registry = ToolRegistry(tools=_ALL_TOOLS, top_k=TOP_K)


def build_agent(task: str):
    """Return a compiled LangGraph agent scoped to tools relevant for *task*."""
    tools = _registry.get_relevant_tools(task=task)
    llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION)
    return create_react_agent(llm, tools=tools)
