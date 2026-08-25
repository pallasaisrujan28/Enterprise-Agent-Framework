"""
Semantic tool registry — selects tools relevant to the current task using
Bedrock Titan Embeddings instead of passing every tool schema to the model.

Two modes depending on env var configuration:

  LOCAL mode (AGENTCORE_GATEWAY_ENDPOINT not set):
    Tools are Python @tool functions passed in at construction.
    Used in development or when Gateway is not yet provisioned.

  GATEWAY mode (AGENTCORE_GATEWAY_ENDPOINT set):
    Tools are discovered dynamically by calling the AgentCore Gateway's
    MCP ListTools endpoint at startup. This is the production path:
      - No code deploy needed to add/remove tools
      - Access controlled per-tool via Cognito scope
      - Every tool call is audited by the Gateway
    The MCP tool definitions are wrapped as LangChain tools using
    langchain-mcp-adapters (MCPToolkit) so create_react_agent works unchanged.

In both modes, Bedrock Titan Embeddings rank tools by relevance to the
current task and only the top-k are passed to the LangGraph agent.
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
GATEWAY_ENDPOINT = os.getenv("AGENTCORE_GATEWAY_ENDPOINT", "")

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


def _discover_gateway_tools() -> list[BaseTool]:
    """
    Call AgentCore Gateway's MCP ListTools endpoint and return the registered
    tools as LangChain-compatible tool objects.

    Requires: langchain-mcp-adapters (mcp) package.
    """
    import httpx

    from agent.auth.cognito import auth_headers

    resp = httpx.post(
        f"{GATEWAY_ENDPOINT}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers={**auth_headers(), "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    tool_defs = resp.json().get("result", {}).get("tools", [])

    try:
        from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore[import]

        return load_mcp_tools(tool_defs, endpoint=GATEWAY_ENDPOINT, auth_headers_fn=auth_headers)
    except ImportError:
        # langchain-mcp-adapters not installed — return a minimal wrapper
        from langchain_core.tools import StructuredTool

        tools = []
        for td in tool_defs:

            def _make_call(name: str):
                def _call(**kwargs: object) -> str:
                    r = httpx.post(
                        f"{GATEWAY_ENDPOINT}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {"name": name, "arguments": kwargs},
                        },
                        headers={**auth_headers(), "Content-Type": "application/json"},
                        timeout=60,
                    )
                    r.raise_for_status()
                    return str(r.json().get("result", {}).get("content", ""))

                return _call

            tools.append(
                StructuredTool.from_function(
                    func=_make_call(td["name"]),
                    name=td["name"],
                    description=td.get("description", ""),
                )
            )
        return tools


@dataclass
class _Entry:
    tool: BaseTool
    embedding: list[float]


class ToolRegistry:
    """
    Holds all available tools with pre-computed description embeddings.
    Call get_relevant_tools(task) each turn to retrieve only the most relevant.

    If AGENTCORE_GATEWAY_ENDPOINT is set, tools are discovered from the Gateway
    at construction time (MCP ListTools). Otherwise, the provided tools list is used.
    """

    def __init__(self, tools: list[BaseTool] | None = None, top_k: int = 4) -> None:
        self._top_k = top_k
        source = _discover_gateway_tools() if GATEWAY_ENDPOINT else (tools or [])
        self._entries: list[_Entry] = [
            _Entry(tool=t, embedding=_embed(f"{t.name}: {t.description}")) for t in source
        ]

    def get_relevant_tools(self, task: str) -> list[BaseTool]:
        if not self._entries:
            return []
        query_emb = _embed(task)
        scored = sorted(self._entries, key=lambda e: _cosine(query_emb, e.embedding), reverse=True)
        return [e.tool for e in scored[: self._top_k]]
