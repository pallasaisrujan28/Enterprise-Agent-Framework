"""
EAF Agent entry point — the deployed HTTP service.

Request flow per turn:
  guardrails.check(input)       → block harmful input
  policies.evaluate(input)      → block policy violations
  brain.build_agent(task)       → ReAct agent with top-k relevant tools
  agent.invoke(messages)        → LangGraph loop
  guardrails.check(output)      → block harmful output
  → ChatResponse

TWO ENTRY POINTS, ONE BRAIN. Both call agent.brain.build_agent(), so they share a
loop, a model layer, a checkpointer and the obligation gate:

  python -m agent          this file. FastAPI on 8080, the container's CMD.
  agent dashboard          agent/cli.py. The local dashboard on 7788.

That mattered enough to consolidate for: there were briefly two harnesses, and
the obligation gate was wired into only one of them. It now lives in the harness
middleware stack, which is the only place that makes it impossible to skip.

The difference that remains is deliberate. This door adds Bedrock Guardrails and
platform policy rules around the turn; the dashboard adds streaming and shows the
gate's verdict. Both are channel concerns, not turn concerns.
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

    agent = brain.build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": safe_input}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    # `.text`, not `.content`. A reasoning model returns content as a LIST of
    # blocks — reasoning first, then the answer — so `.content` handed pydantic a
    # list and ChatResponse failed validation on every turn. `.text` is
    # langchain-core's own accessor: it concatenates the text blocks, drops the
    # reasoning, and still returns the string unchanged for non-reasoning models.
    #
    # Dropping the reasoning is the point, not a side effect. It is the model's
    # scratchpad, and returning it to a caller as the reply presents
    # chain-of-thought as an answer.
    draft = result["messages"][-1].text

    try:
        reply = guardrails.check(draft, source="OUTPUT")
    except GuardrailBlocked as exc:
        raise HTTPException(status_code=500, detail=f"Output blocked: {exc.reasons}") from exc

    return ChatResponse(reply=reply, thread_id=thread_id)


if __name__ == "__main__":
    uvicorn.run("agent.__main__:app", host="0.0.0.0", port=8080, reload=False)
