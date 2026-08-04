"""What a rule IS — the data model for the two-form rule.

A rule file carries two things that serve two different purposes:

  body          markdown GUIDANCE. Goes into the prompt. Makes the right
                behaviour likely. The model reads it.
  obligations   machine-checkable ASSERTIONS. Go into the gate. Make the right
                behaviour verifiable. The model never sees them and cannot
                talk its way past them.

Both ship in one file with one version, so guidance and enforcement cannot
drift apart. That is the whole point: instructions alone are advisory, and an
advisory rule is indistinguishable from a rule the model quietly ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A rule is either advisory (log the violation, deliver anyway) or binding
# (refuse to deliver). New rules start in OBSERVE and are promoted to ENFORCE
# once real traffic shows the violation rate is low — you cannot write a rule
# correctly on the first attempt, and a gate that blocks good answers on day
# one gets switched off by the first person it inconveniences.
MODE_OBSERVE = "observe"
MODE_ENFORCE = "enforce"
MODES = (MODE_OBSERVE, MODE_ENFORCE)

# Hermes' number, adopted with their reasoning: a long description bloats the
# always-resident rule index and dilutes the model's attention across a large
# rule set. The index line is the ONLY part of a rule that every request pays
# for, so it is the one field with a hard limit.
MAX_DESCRIPTION_CHARS = 60


@dataclass(frozen=True)
class Obligation:
    """One checkable assertion drawn from a rule's frontmatter."""

    kind: str
    params: dict[str, Any]
    mode: str = MODE_ENFORCE

    @property
    def blocking(self) -> bool:
        return self.mode == MODE_ENFORCE


@dataclass(frozen=True)
class Rule:
    """One rule file, parsed."""

    name: str
    description: str
    version: str
    body: str
    obligations: tuple[Obligation, ...]
    source: Path

    def index_line(self) -> str:
        """The one line that lives in the cached prefix.

        Every rule pays for this on every request, so it is name + description
        and nothing else. The body is pulled into the tail only when the rule
        is triggered.
        """
        return f"- {self.name}: {self.description}"


@dataclass(frozen=True)
class Violation:
    """An obligation that did not hold."""

    rule: str
    obligation: str
    detail: str
    blocking: bool

    def __str__(self) -> str:
        severity = "BLOCK" if self.blocking else "observe"
        return f"[{severity}] {self.rule}/{self.obligation}: {self.detail}"


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
