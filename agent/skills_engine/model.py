"""What a skill IS — the data model for the unit of enterprise capability.

A skill is one file describing one procedure the business is willing to have an
agent perform. It carries three things that serve three different purposes:

  body            markdown GUIDANCE. Goes into the prompt. Makes the right
                  behaviour likely. The model reads it.
  required_tools  the CAPABILITY the procedure needs. Goes into tool selection
                  and is validated against the pinned catalog at load.
  obligations     machine-checkable ASSERTIONS. Go into the gate. Make the right
                  behaviour verifiable. The model never sees them and cannot
                  talk its way past them.

All three ship in one file with one version, so guidance, capability and
enforcement cannot drift apart. That is the whole point: instructions alone are
advisory, and an advisory instruction is indistinguishable from one the model
quietly ignored.

Naming: this was called a "rule" while it only held the third of those. Once it
also named its tools and carried the procedure, "rule" described a third of the
file. A skill grants capability; the obligations are the price of exercising it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# An obligation is either advisory (log the violation, deliver anyway) or
# binding (refuse to deliver). New skills start in OBSERVE and are promoted to
# ENFORCE once real traffic shows the violation rate is low — you cannot write a
# skill correctly on the first attempt, and a gate that blocks good answers on
# day one gets switched off by the first person it inconveniences.
MODE_OBSERVE = "observe"
MODE_ENFORCE = "enforce"
MODES = (MODE_OBSERVE, MODE_ENFORCE)

# Hermes' number, adopted with their reasoning: a long description bloats the
# always-resident skill index and dilutes the model's attention across a large
# skill set. The index line is the ONLY part of a skill that every request pays
# for, so it is the one field with a hard limit.
MAX_DESCRIPTION_CHARS = 60


@dataclass(frozen=True)
class Obligation:
    """One checkable assertion drawn from a skill's frontmatter."""

    kind: str
    params: dict[str, Any]
    mode: str = MODE_ENFORCE

    @property
    def blocking(self) -> bool:
        return self.mode == MODE_ENFORCE


@dataclass(frozen=True)
class Skill:
    """One skill file, parsed."""

    name: str
    description: str
    version: str
    body: str
    obligations: tuple[Obligation, ...]
    source: Path
    # The tools this procedure needs, named by the author. Three jobs:
    #
    #   1. Validation — every name must resolve in the pinned catalog, so a skill
    #      referencing a deleted tool fails at load rather than mid-conversation.
    #   2. Cross-checking semantic search (ADR-021) — search returns a RANKING,
    #      and a ranking can be wrong silently. A skill that names its tools makes
    #      a bad ranking detectable instead of invisible.
    #   3. Declared selection — for an agent in `declared` mode, this IS the
    #      selector, and it cannot be wrong because it is a lookup.
    required_tools: tuple[str, ...] = ()
    # Must be a SUBSET of the agent's own grants. A skill can narrow access or
    # use what the agent already holds; it can never widen it.
    required_scopes: tuple[str, ...] = ()

    def index_line(self) -> str:
        """The one line that lives in the cached prefix.

        Every skill pays for this on every request, so it is name + description
        and nothing else. The body is pulled into the tail only when the skill
        is triggered.
        """
        return f"- {self.name}: {self.description}"


@dataclass(frozen=True)
class Violation:
    """An obligation that did not hold."""

    skill: str
    obligation: str
    detail: str
    blocking: bool

    def __str__(self) -> str:
        severity = "BLOCK" if self.blocking else "observe"
        return f"[{severity}] {self.skill}/{self.obligation}: {self.detail}"


@dataclass(frozen=True)
class Draft:
    """A candidate answer, in structured form, before it is allowed out.

    Deliberately NOT a bare string. Obligations that had to inspect prose would
    be reduced to substring matching, which produces both false passes and
    false failures — the two worst outcomes for a control. So the model returns
    structure (constrained decoding), and the gate checks fields.
    """

    answer: str
    citations: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()
    tools_called: tuple[str, ...] = ()
    asked_user: bool = False
    approvals: tuple[str, ...] = ()
    # Facts the turn established about the world — inputs an obligation may
    # need that are not visible in the answer itself, e.g. whether the
    # provision has amendments in force but not yet applied to the text.
    facts: dict[str, Any] | None = None

    def fact(self, key: str) -> Any:
        return (self.facts or {}).get(key)
