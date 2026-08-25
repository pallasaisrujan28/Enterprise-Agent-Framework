"""
EAF Agent entry point.

Exposes:
  GET  /health  — liveness / readiness probe
  POST /chat    — single-turn conversation with the LangGraph ReAct agent

The ToolRegistry selects tools semantically on each turn (Bedrock Titan
Embeddings) so the agent never receives an overwhelming list of schemas.
"""

from __future__ import annotations

import os
import uuid

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_aws import ChatBedrockConverse
from langgraph.prebuilt import create_react_agent

from agent.registry import ToolRegistry
from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.search_memory import search_memory
from agent.tools.web_search import web_search

# ── Config ─────────────────────────────────────────────────────────────────────

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
TOP_K_TOOLS = int(os.getenv("TOOL_REGISTRY_TOP_K", "3"))

# ── Registry (embeddings computed once at startup) ─────────────────────────────

_registry = ToolRegistry(
    tools=[web_search, fetch_and_store, search_memory],
    top_k=TOP_K_TOOLS,
)

# ── FastAPI ────────────────────────────────────────────────────────────────────

app = FastAPI(title="EAF Agent")


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    thread_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())

    tools = _registry.get_relevant_tools(task=req.message)
    llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION)
    agent = create_react_agent(llm, tools=tools)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    reply = result["messages"][-1].content

    return ChatResponse(reply=reply, thread_id=thread_id)


if __name__ == "__main__":
    uvicorn.run("agent.__main__:app", host="0.0.0.0", port=8080, reload=False)
