"""SOUL — the agent's editable persona, waku-style.

WHAT THIS IS. A plain-markdown identity/behaviour file that becomes the TOP of
the system prompt every turn. It is the equivalent of waku's SOUL.md: the agent's
standing character and rules, separate from the code-built freshness/delegation
guidance layered underneath it.

WHY A FILE, NOT CODE. Two reasons. A human can edit the persona without touching
Python, and — the point of this module — the AGENT can edit it at runtime via the
`update_soul` tool. When the user teaches a standing preference ("always answer in
British English", "never book without confirming twice"), the model appends it as
a learned rule that takes effect next turn. That is the simplest form of learning
from correction: the fix persists in the persona instead of being forgotten when
the thread ends.

APPEND-ONLY FOR THE AGENT. `update_soul` can only ADD a learned rule; it cannot
rewrite or delete the persona. So the agent can accrue standing instructions but
cannot quietly edit away its own honesty rules. A human does full rewrites by
editing the file directly.

PERSISTENCE. The file lives at AGENT_SOUL_PATH (default prompts/soul.md in the
repo). Locally that persists across restarts. In a multi-pod deploy a repo file
does NOT persist — point AGENT_SOUL_PATH at a mounted volume or a workspace path
there. Kept simple here; local-first first.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.tools import tool

# The default persona, written to the SOUL file on first load if none exists. It
# is deliberately short — the code-built layers (freshness, delegation, browsing)
# carry the operational detail; this carries character and standing rules.
_DEFAULT_SOUL = """\
# Agent persona

You are the Enterprise Agent — a capable, honest assistant that gets real tasks \
done for the user: research, and acting on the web (shopping, booking, forms).

## Rules
- Be concise and direct. Say what you did and where results live; never claim \
something happened that you cannot see in a tool's output.
- For anything that DOES something irreversible on a website — a payment, order, \
booking, or form submission — show the user exactly what will happen and get their \
explicit confirmation first. Never guess a login, card number, or one-time code; \
ask for it.
- Prefer delegating fan-out research and browser actions to the appropriate \
subagent, and synthesise their results rather than dumping raw tool output.
- If the user teaches you a standing preference or corrects you, save it with \
update_soul so you remember it in future conversations.

## Learned rules
"""

# A generous cap so a runaway append loop cannot bloat the prompt indefinitely.
_SOUL_MAX_CHARS = 8000

_LEARNED_HEADER = "## Learned rules"


def soul_path() -> Path:
    return Path(os.getenv("AGENT_SOUL_PATH") or (Path(__file__).parents[1] / "prompts" / "soul.md"))


def load_soul() -> str:
    """The persona text. Seeds the default file on first use so it always exists."""
    path = soul_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DEFAULT_SOUL, encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def append_learned_rule(rule: str) -> str:
    """Append one behaviour rule under '## Learned rules'. Append-only.

    Returns a short status the tool relays to the model. Refuses when the file is
    at its size cap (a human should prune it in that case), and creates the
    Learned-rules section if the persona does not have one yet.
    """
    rule = rule.strip().lstrip("-").strip()
    if not rule:
        return "Nothing to add — the rule was empty."

    path = soul_path()
    text = load_soul()
    if len(text) >= _SOUL_MAX_CHARS:
        return (
            "SOUL is at its size limit — ask a human to prune prompts/soul.md before adding more."
        )

    if _LEARNED_HEADER not in text:
        text = text.rstrip() + f"\n\n{_LEARNED_HEADER}\n"
    text = text.rstrip() + f"\n- {rule}\n"
    path.write_text(text, encoding="utf-8")
    return f"Saved to my persona — I'll remember to: {rule}"


@tool
def update_soul(rule: str) -> str:
    """Save a durable rule about how you should behave for this user.

    Use this when the user tells you a standing preference or corrects how you act
    ("always do X", "never do Y", "from now on…"). The rule is appended to your
    persona and takes effect on the next turn. It persists across conversations.
    Provide ONE behaviour rule, phrased as a short imperative.
    """
    return append_learned_rule(rule)
