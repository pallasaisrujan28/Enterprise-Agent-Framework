"""
Content overflow middleware — offloads large tool outputs to the agent workspace.

Problem:
  Web search, page fetches, and API calls can return tens of thousands of tokens.
  Passing all of that directly into the context window has two failure modes:
    1. Context limit hit — the model call fails or truncates silently
    2. Context bloat — the model's reasoning degrades with irrelevant content

Solution:
  This middleware intercepts every tool call result. If the result exceeds
  MAX_CONTENT_TOKENS, it:
    1. Writes the full content to /workspace/overflow/<tool>_<timestamp>.md
       via the EAFBackend (S3, persistent)
    2. Returns a compact summary to the agent:
       "Full result saved to /workspace/overflow/web_search_20260826_143022.md
        Summary: <first 500 chars>..."

The agent can then decide whether to read the full file with read_file(),
or continue with the summary. The decision stays with the model —
the middleware just prevents accidental context explosion.

Usage in brain.py:
    from agent.middleware.content import ContentOverflowMiddleware

    agent = create_deep_agent(
        ...
        middleware=[
            ContentOverflowMiddleware(backend=workspace_backend),
            TodoListMiddleware(),
        ],
    )
"""

from __future__ import annotations

import os
from datetime import datetime

MAX_CONTENT_TOKENS = int(os.getenv("MIDDLEWARE_CONTENT_MAX_TOKENS", "4000"))
# Rough chars-per-token estimate (no tiktoken dependency needed here)
CHARS_PER_TOKEN = 4


def _token_estimate(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


class ContentOverflowMiddleware:
    """
    Intercepts tool call results and offloads large content to the workspace.

    Registered as deepagents middleware via create_deep_agent(middleware=[...]).
    The wrap_tool_call hook fires after every tool execution, before the result
    enters the agent's context window.
    """

    def __init__(self, backend=None, max_tokens: int = MAX_CONTENT_TOKENS) -> None:
        self.backend = backend
        self.max_tokens = max_tokens

    def wrap_tool_call(self, tool_name: str, result: str) -> str:
        """
        Called after every tool execution with the raw result string.
        Returns the result unchanged if it's within budget.
        Offloads to workspace and returns a compact summary if it overflows.
        """
        if _token_estimate(result) <= self.max_tokens:
            return result

        return self._offload(tool_name, result)

    def _offload(self, tool_name: str, content: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = f"/workspace/overflow/{tool_name}_{timestamp}.md"
        summary = content[: self.max_tokens * CHARS_PER_TOKEN]

        if self.backend is not None:
            try:
                self.backend.write(path, content)
                return (
                    f"[Content overflow — full result saved to {path}]\n\n"
                    f"Summary (first {self.max_tokens} tokens):\n{summary}\n\n"
                    f"Use read_file('{path}') to access the full content."
                )
            except Exception:
                pass

        # No backend or write failed — return truncated content with a note
        return (
            f"[Content overflow — result truncated to {self.max_tokens} tokens]\n\n"
            f"{summary}\n\n"
            f"[Truncated. Set WORKSPACE_BUCKET to enable full content offload.]"
        )
