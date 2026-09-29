"""The retrieval gate — decides WHETHER a turn needs durable memory.

Straight from waku's playbook. Querying the knowledge graph on every turn is
both slow (a graph search before each reply) and worse: irrelevant facts bias
the answer. So before touching Graphiti, a cheap fast-model call answers one
question — does THIS message need what we remember about the user? "what's 2+2"
→ no. "what did I say about the Acme deadline?" → yes, and here is the query.

Fails OPEN: if the gate itself errors, we recall anyway — a stale memory beats a
lost one. (The gate only decides whether to LOOK; it never blocks a turn.)
"""

from __future__ import annotations

import json
from typing import Any

_GATE_PROMPT = """\
You are a retrieval gate for an assistant's long-term memory. The memory stores
facts about the user (their people, projects, preferences, past events) AND what
the assistant itself has done and found in earlier turns — products it looked at,
options it compared, pages it read, answers it gave.

Given the user's message, decide if answering well needs that stored memory.

Reply with ONLY this JSON, nothing else:
{{"retrieve": true or false, "query": "<search keywords if true, else empty>"}}

Return true when the message references:
  - the user's own life, people, plans, preferences, or history, OR
  - something the assistant did or discussed earlier — e.g. "what else did you
    consider", "the options you showed me", "what did you find", "that product
    from before", "earlier you said". These look back at the session/history and
    NEED memory even though they are phrased about the assistant.

Return false only for genuinely self-contained requests: general knowledge,
math, small talk, or a brand-new task that refers to nothing prior.

User message: {message}"""


def should_retrieve(router: Any, message: str) -> tuple[bool, str]:
    """Return (retrieve?, search_query). `router` is the fast chat model.

    Fails open (retrieve, using the raw message as the query) on any error or an
    unparseable reply, so a flaky gate never costs us a memory that would have
    helped.
    """
    try:
        answer = router.invoke(_GATE_PROMPT.format(message=message)).text.strip()
        if "{" not in answer:
            return True, message
        decision = json.loads(answer[answer.index("{") : answer.rindex("}") + 1])
        return bool(decision.get("retrieve")), decision.get("query") or message
    except Exception:  # noqa: BLE001 — fail open; the gate must never break a turn
        return True, message
