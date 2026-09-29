"""A debug middleware that prints the assembled prompt + tools each model call.

WHY. "What does the model actually see each turn?" is the hardest thing to
visualise — the system prompt is assembled from layers (SOUL, freshness,
delegation, the skills catalogue appended by SkillsMiddleware, the filesystem
tool prose, and any recalled memory), and the tools live in a separate channel.
With AGENT_DEBUG_PROMPT=on this prints, per model call: the system prompt it sees
at this layer, and the tool names attached.

CAVEAT ON LAYERING. This prints what the prompt looks like AT THIS MIDDLEWARE'S
position in the wrap chain, which may be before some deepagents-appended layers.
LangSmith logs the BYTE-EXACT final prompt for every model call (the llm run's
input messages) — treat that as the source of truth; this is the quick local view.

OFF BY DEFAULT and a no-op unless the flag is set, so it never adds noise or cost
to a normal run.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)


def prompt_debug_enabled() -> bool:
    return os.getenv("AGENT_DEBUG_PROMPT", "").strip().lower() in {"1", "on", "true", "yes"}


class PromptDebugMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    """Prints the system prompt and tool list on each model call when enabled."""

    name = "PromptDebugMiddleware"

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> Any:
        if prompt_debug_enabled():
            sys_msg = getattr(request, "system_message", None)
            content = getattr(sys_msg, "content", sys_msg)
            tools = getattr(request, "tools", None) or []
            names = [getattr(t, "name", str(t)) for t in tools]
            bar = "=" * 70
            print(f"\n{bar}\n[PROMPT DEBUG] system prompt this call:\n{bar}", flush=True)
            print(str(content), flush=True)
            print(f"{bar}\n[PROMPT DEBUG] tools ({len(names)}): {names}\n{bar}\n", flush=True)
        return handler(request)
