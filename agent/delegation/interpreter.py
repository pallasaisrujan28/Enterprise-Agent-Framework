"""The interpreter — what turns static sub-agents into DYNAMIC ones.

DECOUPLED FROM THE HARNESS. Like the roster, the decision to give the agent a
code interpreter (and which tools it may reach through it) is a delegation
concern, not harness plumbing. `brain.py` calls `build_interpreter_middleware()`
and drops the result into its middleware list.

WHAT IT IS. A sandboxed QuickJS REPL exposed to the model as an `eval` tool
(from the `langchain-quickjs` package). With the interpreter present AND
sub-agents configured, the runtime exposes a `task()` global, so the model can
write a short orchestration script — loops, branches, parallel batches — instead
of choosing one `task` tool call at a time. This is what "dynamic sub-agents"
means. Prompt the agent with the word "workflow" to trigger the path.

PTC (PROGRAMMATIC TOOL CALLING). The allowlist passed in is exposed inside the
interpreter as `tools.*` (camelCased — `web_search` becomes `tools.webSearch`),
so interpreter code can call tools in loops and filter results before anything
returns to the model. The allowlist is a PERMISSION BOUNDARY: pass only the tools
the agent may reach programmatically. Off entirely if the list is empty.

ISOLATION. QuickJS has no host filesystem, network, shell, or clock by default;
the only outside reach is the PTC allowlist and `task()`. It is a scoped
interpreter, not a full sandbox — see the deepagents Security notes.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from langchain_quickjs import CodeInterpreterMiddleware


def build_interpreter_middleware(ptc_tools: Sequence[BaseTool]) -> CodeInterpreterMiddleware:
    """Build the QuickJS interpreter middleware, with PTC scoped to `ptc_tools`.

    `subagents=True` exposes the `task()` global so the roster in
    `subagents.py` can be dispatched from interpreter code. Passing an empty
    `ptc_tools` leaves programmatic tool calling disabled while still enabling
    dynamic sub-agents.
    """
    return CodeInterpreterMiddleware(
        subagents=True,
        ptc=list(ptc_tools) or None,
    )
