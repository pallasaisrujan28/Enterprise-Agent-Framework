"""
Semantic tool registry — selects which tools are relevant to the current
task using Bedrock Titan Embeddings instead of a hardcoded list.

On startup all tool descriptions are embedded. On each turn only the top-k
most similar tools are passed to the LangGraph agent so the context window
stays focused and the model does not get confused by irrelevant tool schemas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import boto3
import numpy as np
from langchain_core.tools import BaseTool

EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
VECTOR_SIZE = 512

_bedrock = boto3.client("bedrock-runtime", region_name="eu-west-2")


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
class _ToolEntry:
    tool: BaseTool
    embedding: list[float]


class ToolRegistry:
    """
    Holds all available tools with pre-computed description embeddings.
    Call get_relevant_tools(task) each turn to get only the tools that
    match the task semantically — no hardcoded list, no context bloat.
    """

    def __init__(self, tools: list[BaseTool], top_k: int = 3) -> None:
        self._top_k = top_k
        self._entries: list[_ToolEntry] = [
            _ToolEntry(tool=t, embedding=_embed(f"{t.name}: {t.description}"))
            for t in tools
        ]

    def get_relevant_tools(self, task: str) -> list[BaseTool]:
        if not self._entries:
            return []
        query_emb = _embed(task)
        scored = sorted(
            self._entries,
            key=lambda e: _cosine(query_emb, e.embedding),
            reverse=True,
        )
        return [e.tool for e in scored[: self._top_k]]
