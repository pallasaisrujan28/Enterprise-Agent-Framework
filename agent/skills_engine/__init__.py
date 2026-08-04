"""Skills Engine — the machinery that reads, validates and enforces skills.

Deliberately named apart from the `skills/` directory at the repository root.
That directory holds the ARTIFACTS: one markdown file per procedure, authored by
the business, no code. This package is the ENGINE that loads them, refuses the
ones that cannot be enforced, and hands their obligations to the gate. Content
and machinery under one name was a genuine source of confusion.

model.py        what a skill is: guidance + tools + obligations + version
loader.py       reading skill files, and refusing unenforceable ones
obligations.py  the parameterised checks a skill author can use without code
"""

from agent.skills_engine.loader import (
    SkillError,
    SkillSet,
    load_skill,
    load_skillset,
    validate_against_catalog,
    validate_scopes,
)
from agent.skills_engine.model import Draft, Obligation, Skill, Violation

__all__ = [
    "Draft",
    "Obligation",
    "Skill",
    "SkillError",
    "SkillSet",
    "Violation",
    "load_skill",
    "load_skillset",
    "validate_against_catalog",
    "validate_scopes",
]
