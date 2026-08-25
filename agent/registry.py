"""
Semantic tool registry — selects tools relevant to the current task using
Bedrock Titan Embeddings instead of passing every tool schema to the model.

Why not a hardcoded list?
  A list of 20 tools passed on every turn wastes ~2k tokens of context
  window, confuses the model with irrelevant schemas, and does not scale
  as more tools are added. The registry embeds tool descriptions once at
  startup and retrieves only the top-k most similar tools per turn.

How it works:
  1. At startup: embed f"{tool.name}: {tool.description}" for every tool.
  2. Each turn: embed the current user task and rank tools by cosine similarity.
  3. Pass only the top-k tools to create_react_agent for that turn.

Adding a new tool: register it in agent/brain.py — no other change needed.
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
    Call get_relevant_tools(task) each turn to get only the most relevant ones.
    """

    def __init__(self, tools: list[BaseTool], top_k: int = 4) -> None:
        self._top_k = top_k
        self._entries: list[_Entry] = [
            _Entry(tool=t, embedding=_embed(f"{t.name}: {t.description}"))
            for t in tools
        ]

    def get_relevant_tools(self, task: str) -> list[BaseTool]:
        if not self._entries:
            return []
        query_emb = _embed(task)
        scored = sorted(self._entries, key=lambda e: _cosine(query_emb, e.embedding), reverse=True)
        return [e.tool for e in scored[: self._top_k]]
