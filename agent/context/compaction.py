"""
Context compaction — summarises older turns to keep the active context
window below the model's practical limit while retaining key facts.

Why this exists: a long agentic session accumulates many tool call /
tool result pairs. Past a certain point, old content wastes tokens and
can even degrade reasoning. Compaction runs when the message count
crosses a threshold, replacing the oldest messages with a summary.
"""

from __future__ import annotations

import os

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

COMPACT_AFTER = int(os.getenv("CONTEXT_COMPACT_AFTER", "40"))
KEEP_RECENT = int(os.getenv("CONTEXT_KEEP_RECENT", "10"))


def maybe_compact(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Return compacted messages if over threshold, else return unchanged."""
    if len(messages) <= COMPACT_AFTER:
        return messages
    to_summarise = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]
    summary = _summarise(to_summarise)
    return [HumanMessage(content=f"[Summary of prior conversation]\n{summary}")] + recent


def _summarise(messages: list[BaseMessage]) -> str:
    llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION)
    prompt = [
        SystemMessage(
            content=(
                "Summarise the following conversation history concisely. "
                "Preserve all key facts, decisions, and findings. Output plain text, no headers."
            )
        ),
        *messages,
    ]
    response = llm.invoke(prompt)
    return str(response.content)
