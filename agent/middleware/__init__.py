"""
EAF Middleware — cross-cutting concerns that intercept agent execution.

Middleware in EAF is anything that needs to wrap tool calls or model calls
across the whole system, regardless of which tool or skill triggered it.

Current middleware:
  ContentOverflowMiddleware — when a tool returns too much content, offload
    it to /workspace/ and return a summary + file reference instead.
    Prevents context window overflow from large web search results.

Adding new middleware:
  1. Create a new module in this package
  2. Implement the deepagents Middleware protocol (before_agent, before_model,
     wrap_tool_call, wrap_model_call, after_model, after_agent hooks)
  3. Register it in brain.py's middleware list

Examples of future middleware:
  - TokenBudgetMiddleware  — refuse model calls when session budget is exhausted
  - MemoryInjector        — prepend relevant Qdrant chunks before each model call
  - AuditLogger           — write every tool action + result to Langfuse
  - PIIScrubber           — strip PII from model output before it enters context
"""

from agent.middleware.content import ContentOverflowMiddleware

__all__ = ["ContentOverflowMiddleware"]
