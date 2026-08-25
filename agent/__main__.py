"""
EAF Agent entry point.

The deepagents harness handles: skills, tools, filesystem, task planning,
sub-agents, and graph execution. This module adds the EAF-specific envelope:
  guardrails → policy check → deepagents agent → obligation gate → guardrails
"""

from __future__ import annotations

import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import brain
from agent.guardrails import bedrock as guardrails
from agent.guardrails.bedrock import GuardrailBlocked
from agent.policies.loader import evaluate as policy_evaluate
from agent.policies.loader import load_policies

_POLICIES = load_policies()

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

    # 1. Guardrail on input (Bedrock Guardrails — optional, no-op if not configured)
    try:
        safe_input = guardrails.check(req.message, source="INPUT")
    except GuardrailBlocked as exc:
        raise HTTPException(status_code=400, detail=f"Input blocked: {exc.reasons}") from exc

    # 2. Platform policy check (regex rules, always-on)
    violations = [v for v in policy_evaluate(safe_input, _POLICIES) if v.action == "deny"]
    if violations:
        raise HTTPException(status_code=400, detail=f"Policy: {violations[0].description}")

    # 3. deepagents: skills + tools + filesystem + sub-agents
    agent = brain.build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": safe_input}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    draft = result["messages"][-1].content

    # 4. Guardrail on output
    try:
        reply = guardrails.check(draft, source="OUTPUT")
    except GuardrailBlocked as exc:
        raise HTTPException(status_code=500, detail=f"Output blocked: {exc.reasons}") from exc

    return ChatResponse(reply=reply, thread_id=thread_id)


if __name__ == "__main__":
    uvicorn.run("agent.__main__:app", host="0.0.0.0", port=8080, reload=False)
