"""
EAF Agent entry point.

Request flow per turn:
  guardrails.check(input)       → block harmful input
  policies.evaluate(input)      → block policy violations
  brain.build_agent(task)       → ReAct agent with top-k relevant tools
  agent.invoke(messages)        → LangGraph loop
  guardrails.check(output)      → block harmful output
  → ChatResponse
"""

from __future__ import annotations

import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import brain
from agent.guardrails import bedrock as guardrails
from agent.guardrails.bedrock import GuardrailBlocked
from agent.memory.checkpointer import get_checkpointer
from agent.policies.loader import evaluate as policy_evaluate
from agent.policies.loader import load_policies

_POLICIES = load_policies()
_CHECKPOINTER = get_checkpointer()

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

    try:
        safe_input = guardrails.check(req.message, source="INPUT")
    except GuardrailBlocked as exc:
        raise HTTPException(status_code=400, detail=f"Input blocked: {exc.reasons}") from exc

    violations = [v for v in policy_evaluate(safe_input, _POLICIES) if v.action == "deny"]
    if violations:
        raise HTTPException(
            status_code=400, detail=f"Policy violation: {violations[0].description}"
        )

    agent = brain.build_agent(task=safe_input)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": safe_input}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    draft = result["messages"][-1].content

    try:
        reply = guardrails.check(draft, source="OUTPUT")
    except GuardrailBlocked as exc:
        raise HTTPException(status_code=500, detail=f"Output blocked: {exc.reasons}") from exc

    return ChatResponse(reply=reply, thread_id=thread_id)


if __name__ == "__main__":
    uvicorn.run("agent.__main__:app", host="0.0.0.0", port=8080, reload=False)
