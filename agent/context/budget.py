"""
Token budget — tracks how many tokens a session has consumed and signals
when the agent should stop spawning sub-agents or tool calls.

Why this exists: an unbudgeted agentic loop can rack up enormous costs in
a single session (especially with multi-hop web research). The budget is
set per-session and checked at each tool dispatch node in the graph.

Budget is approximate: Bedrock does not return token counts synchronously
on every call. We use tiktoken with the cl100k_base encoding as a proxy —
accurate enough to enforce a soft ceiling without requiring an extra API
round-trip.
"""

from __future__ import annotations

import os

_DEFAULT_BUDGET = int(os.getenv("SESSION_TOKEN_BUDGET", "100000"))

# Rough character-to-token ratio used when tiktoken is not available.
_CHARS_PER_TOKEN = 4


def _count(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // _CHARS_PER_TOKEN


class TokenBudget:
    """
    Tracks token usage for one session.

    Usage:
        budget = TokenBudget()
        budget.consume(messages)          # call after each LLM invocation
        if budget.exhausted():
            raise BudgetExhausted(...)
    """

    def __init__(self, limit: int = _DEFAULT_BUDGET) -> None:
        self.limit = limit
        self._spent = 0

    def consume(self, texts: list[str]) -> None:
        self._spent += sum(_count(t) for t in texts)

    @property
    def spent(self) -> int:
        return self._spent

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self._spent)

    def exhausted(self) -> bool:
        return self._spent >= self.limit


class BudgetExhausted(RuntimeError):
    """Raised when a session has consumed its token budget."""
