"""When to delegate — guidance that replaces the magic word "workflow".

THE PROBLEM. The QuickJS interpreter middleware ships a system-prompt block that
tells the model to fan work out to subagents "if the user's request mentions the
word 'workflow'". That is a bad contract to put on a user — nobody should have to
learn a keyword to get parallel research. But we also do not want the interpreter
firing on trivial questions.

THE FIX. This guidance is layered in as the agent's own system prompt (passed to
create_deep_agent). It keys the decision on the SHAPE of the task, not on any
keyword, so the model chooses to orchestrate when the work is genuinely fan-out
shaped and answers directly otherwise. It is additive to the middleware's own
prompt; the intent is to override the "say workflow" heuristic with a judgement
the user never has to think about.
"""

from __future__ import annotations

DELEGATION_GUIDANCE = (
    "## Deciding when to orchestrate\n"
    "\n"
    "You have an interpreter (the `eval` tool) and a `task()` global that "
    "dispatches subagents. Decide whether to use them from the SHAPE of the "
    "request — never require the user to use any special word.\n"
    "\n"
    "Orchestrate with the interpreter (write JavaScript in `eval` that calls "
    "`task()` and combines the results) when the work is naturally parallel or "
    "repetitive:\n"
    "- several distinct subjects to research, compare, or summarise;\n"
    "- the same operation applied across a batch of items;\n"
    "- anything needing many independent lookups whose intermediate output would "
    "otherwise flood the conversation.\n"
    "Fan those out in parallel and synthesise the results, rather than grinding "
    "through them one tool call at a time.\n"
    "\n"
    "Do NOT use the interpreter for a single, simple question. Answer directly, "
    "or with one or two ordinary tool calls. Reaching for orchestration on a "
    "trivial task just adds latency.\n"
)
