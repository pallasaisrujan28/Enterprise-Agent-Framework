"""
Sub-agent delegation — task tool configuration and sub-agent builders.

deepagents ships the `task` tool which spawns an isolated sub-agent.
This package defines:
  - Which tool subsets each sub-agent type gets (scoped, not the full list)
  - Which backend each sub-agent gets (isolated EAFBackend instance)
  - Factory functions that build pre-configured sub-agents for common tasks

Sub-agent isolation properties (enforced by deepagents):
  - Fresh context window (no parent conversation history)
  - Its own backend instance (workspace prefix scoped to sub-task)
  - Scoped tool list (only the tools the sub-task needs)
  - Returns ONE structured result to the parent
  - Parent context stays clean — no reasoning bleed-through

TODO: implement sub-agent builders as delegation patterns grow.
"""
