"""
Semantic tool registry — selects tools relevant to the current task using
Bedrock Titan Embeddings instead of passing every tool schema to the model.

Architecture (current — direct):
  Tools are Python @tool functions registered in brain.py.
  ToolRegistry embeds their descriptions at startup, picks top-k per turn.
  Tool calls go directly from the agent to the backend (SearXNG, Crawl4AI, etc).

Architecture (target — AgentCore Gateway):
  Tools are registered as MCP servers in AgentCore Gateway (eu-west-2).
  AgentCore Gateway provides:
    - Central access control (IAM per tool — who can call what)
    - Rate limiting and quota enforcement
    - Full audit trail of every tool invocation
    - MCP ListTools discovery (new tools appear without a code deploy)
  ToolRegistry will query the Gateway MCP endpoint at startup to discover
  tools, embed their descriptions, then rank per turn. Tool calls go:
    agent → ToolRegistry.get_relevant_tools() → AgentCore Gateway (MCP) → backend
  Required: AGENTCORE_GATEWAY_ENDPOINT env var pointing to the Gateway URL.

Why not a hardcoded list?
  20 tool schemas on every turn wastes ~2k context tokens and confuses the
  model with irrelevant options. The registry picks only the top-k most
  similar to the current task — focused context, better reasoning. Adding
  a tool only requires registering it (in brain.py now, in Gateway later).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import boto3
import numpy as np
from langchain_core.tools import BaseTool

EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
VECTOR_SIZE = 512
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def _embed(text: str) -> list[float]:
    resp = _bedrock.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text[:2048], "dimensions": VECTOR_SIZE, "normalize": True}),
    )
    return json.loads(resp["body"].read())["embedding"]


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return float(np.dot(va, vb) / denom) if denom else 0.0


@dataclass
class _Entry:
    tool: BaseTool
    embedding: list[float]


class ToolRegistry:
    """
    Holds all available tools with pre-computed description embeddings.
    Call get_relevant_tools(task) each turn to retrieve only the most relevant.

    Future: when AGENTCORE_GATEWAY_ENDPOINT is set, populate from the Gateway
    MCP ListTools endpoint instead of receiving a local Python tools list.
    """

    def __init__(self, tools: list[BaseTool], top_k: int = 4) -> None:
        self._top_k = top_k
        self._entries: list[_Entry] = [
            _Entry(tool=t, embedding=_embed(f"{t.name}: {t.description}")) for t in tools
        ]

    def get_relevant_tools(self, task: str) -> list[BaseTool]:
        if not self._entries:
            return []
        query_emb = _embed(task)
        scored = sorted(self._entries, key=lambda e: _cosine(query_emb, e.embedding), reverse=True)
        return [e.tool for e in scored[: self._top_k]]
