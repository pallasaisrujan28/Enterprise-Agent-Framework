"""Sub-agent delegation — the roster and the interpreter, decoupled from the harness.

deepagents ships the `task` tool that spawns an isolated sub-agent, and
`langchain-quickjs` adds an interpreter that turns those sub-agents DYNAMIC (the
model orchestrates them from code via a `task()` global). Both are delegation
concerns, kept out of `brain.py` so the harness builder only has to assemble
them, not define them.

This package owns:
  - `build_subagents()`      — the sub-agent roster (scoped tools, own context)
  - `build_interpreter_middleware(ptc_tools)` — the QuickJS interpreter that
                                enables dynamic dispatch + programmatic tool calls

Sub-agent isolation properties (enforced by deepagents):
  - Fresh context window (no parent conversation history)
  - Scoped tool list (only the tools the sub-task needs)
  - Returns ONE structured result to the parent — no reasoning bleed-through

The obligation gate still judges the parent's final answer, so delegation is
never a way around it.
"""

from agent.delegation.interpreter import build_interpreter_middleware
from agent.delegation.prompt import DELEGATION_GUIDANCE
from agent.delegation.subagents import build_subagents

__all__ = ["DELEGATION_GUIDANCE", "build_interpreter_middleware", "build_subagents"]
