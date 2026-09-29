"""Context and token budget — configuring the framework's own middleware.

No new middleware here: langchain/deepagents already ship every mechanism we
need; they were just left at settings that never fire, or too verbose for this
model. What the eval measured (one "pull my emails" turn):

  7 model calls, 186k input tokens for 5k output. 4 of the 7 calls were
  write_todos bookkeeping, each re-sending the full context. No prompt-cache
  hits (Bedrock caching only applies to Claude/Nova, not DeepSeek), so every
  call pays full price. Summarization never ran: our SummarizationMiddleware was
  built with trigger=None, which means "never proactively".

Three knobs, each the framework's documented one:
  planning_middleware()    TodoListMiddleware with a SHORT prompt/description that
                           keeps write_todos for genuinely multi-step work. The
                           stock description is 3.9k chars sent on every call.
  context_editing()        ContextEditingMiddleware + ClearToolUsesEdit: once the
                           prompt passes a threshold, older tool OUTPUTS are
                           replaced by a placeholder (the last few are kept).
  SUMMARY_TRIGGER/KEEP     a real trigger for SummarizationMiddleware so long
                           threads get compacted instead of growing unbounded.
"""

from __future__ import annotations

import os
from typing import Literal

from langchain.agents.middleware import ClearToolUsesEdit, ContextEditingMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware  # type: ignore[import-not-found]

# ── planning ──────────────────────────────────────────────────────────────────

TODO_SYSTEM_PROMPT = (
    "## `write_todos`\n"
    "A planning tool for complex work only. Use it when a request needs several "
    "DIFFERENT actions or deliverables (e.g. research, then compare, then book). "
    "Do NOT use it to look something up and answer, to run one tool a few times, "
    "or for anything you can finish in about three tool calls. Each call costs a "
    "full model round-trip: write the plan once, update it only when a step is "
    "actually finished or the plan changes, and never call it just to mark the "
    "last step done before answering."
)

TODO_TOOL_DESCRIPTION = (
    "Create or update a task list for a complex, multi-step job. Pass the whole "
    "list each time; each item has `content` and `status` "
    "(pending | in_progress | completed). Keep exactly one item in_progress. "
    "Skip this tool for simple or single-purpose requests."
)


def planning_middleware() -> TodoListMiddleware:
    return TodoListMiddleware(
        system_prompt=TODO_SYSTEM_PROMPT, tool_description=TODO_TOOL_DESCRIPTION
    )


# ── clearing old tool outputs ─────────────────────────────────────────────────

# Approximate prompt tokens before older tool outputs are cleared. The measured
# fixed cost (system prompt + tool schemas) is ~11k, so 40k leaves room for a
# few turns of real tool data before anything is dropped.
CLEAR_TOOLS_TRIGGER = int(os.getenv("CONTEXT_CLEAR_TOOLS_AT", "40000"))
CLEAR_TOOLS_KEEP = 4

# The placeholder is what the model sees instead of the output — it must say
# what happened, or the model treats the cleared call as having returned nothing.
_CLEARED = (
    "[older tool output cleared to save context. If you need that exact data "
    "again, call the tool again.]"
)


def context_editing() -> ContextEditingMiddleware:
    return ContextEditingMiddleware(
        edits=[
            ClearToolUsesEdit(
                trigger=CLEAR_TOOLS_TRIGGER,
                keep=CLEAR_TOOLS_KEEP,
                # The plan is small and is the agent's own state; clearing it
                # would make the model re-plan.
                exclude_tools=("write_todos",),
                placeholder=_CLEARED,
            )
        ]
    )


# ── summarization ─────────────────────────────────────────────────────────────

# "tokens" rather than "fraction": fraction needs the model profile's
# max_input_tokens, which ChatBedrockConverse may not report for DeepSeek.
SUMMARY_TRIGGER: tuple[Literal["tokens"], int] = (
    "tokens",
    int(os.getenv("CONTEXT_SUMMARIZE_AT", "80000")),
)
SUMMARY_KEEP: tuple[Literal["messages"], int] = ("messages", 20)
