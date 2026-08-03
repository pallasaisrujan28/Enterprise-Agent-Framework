"""Reading rule files, and refusing the ones that are not enforceable.

A rule file is markdown with YAML frontmatter:

    ---
    name: legislation_advice
    description: How to answer questions about UK statute.
    obligations:
      - must_cite: {contains: legislation.gov.uk, version_pinned: true}
      - must_ask_when_missing: {fields: [as_at_date]}
    ---

    ## Procedure
    ...

Validation is strict and fails at load, not at run. A rule that cannot be
enforced is worse than no rule: the tenant believes a control exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from eaf.rules import obligations as ob_lib
from eaf.rules.model import (
    MAX_DESCRIPTION_CHARS,
    MODE_ENFORCE,
    MODES,
    Obligation,
    Rule,
)

_FRONTMATTER = "---"


class RuleError(ValueError):
    """A rule file is malformed or unenforceable."""


@dataclass(frozen=True)
class RuleSet:
    """The rules granted to one agent, pinned for the life of a session.

    Pinned because the index lives in the cached prefix: adding a rule
    mid-session would rewrite the prefix and invalidate the cache for every
    turn that follows. New rules take effect for sessions started after
    promotion.
    """

    rules: tuple[Rule, ...]
    version: str

    def by_name(self, name: str) -> Rule | None:
        return next((r for r in self.rules if r.name == name), None)

    def index_block(self) -> str:
        """The rule index, for the stable prefix."""
        if not self.rules:
            return "(no rules granted)"
        return "\n".join(r.index_line() for r in self.rules)


def _split_frontmatter(text: str, source: Path) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER:
        raise RuleError(f"{source}: must begin with a '---' frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _FRONTMATTER)
    except StopIteration:
        raise RuleError(f"{source}: frontmatter block is never closed") from None
    meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(meta, dict):
        raise RuleError(f"{source}: frontmatter must be a mapping")
    return meta, "\n".join(lines[end + 1 :]).strip()


def _parse_obligations(raw: object, source: Path) -> tuple[Obligation, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise RuleError(f"{source}: 'obligations' must be a list")

    parsed: list[Obligation] = []
    for entry in raw:
        if not isinstance(entry, dict) or len(entry) != 1:
            raise RuleError(
                f"{source}: each obligation must be a single-key mapping, got {entry!r}"
            )
        kind, params = next(iter(entry.items()))
        params = dict(params or {})
        mode = str(params.pop("mode", MODE_ENFORCE))
        if mode not in MODES:
            raise RuleError(f"{source}: obligation '{kind}' has unknown mode '{mode}'")
        if kind not in ob_lib.known_kinds():
            raise RuleError(
                f"{source}: unknown obligation kind '{kind}'. "
                f"Known kinds: {', '.join(ob_lib.known_kinds())}"
            )
        parsed.append(Obligation(kind=kind, params=params, mode=mode))
    return tuple(parsed)


def load_rule(path: Path) -> Rule:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text, path)

    name = meta.get("name")
    if not name:
        raise RuleError(f"{path}: 'name' is required")

    description = (meta.get("description") or "").strip()
    if not description:
        raise RuleError(
            f"{path}: 'description' is required — it is how the model selects this rule"
        )
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise RuleError(
            f"{path}: description is {len(description)} chars, limit is {MAX_DESCRIPTION_CHARS}. "
            "It sits in the always-resident index that every request pays for."
        )

    if not body:
        raise RuleError(f"{path}: rule body is empty — there is no guidance to give the model")

    return Rule(
        name=str(name),
        description=description,
        # Content-addressed, so a rule version is the rule. Two deployments
        # claiming the same version cannot be holding different text.
        version=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        body=body,
        obligations=_parse_obligations(meta.get("obligations"), path),
        source=path,
    )


def load_ruleset(directory: Path) -> RuleSet:
    """Load every rule in a directory, sorted by name for a stable prefix.

    Sorted because the index goes into the cached prefix: filesystem iteration
    order is not guaranteed, and a reordered index is a different prefix and
    therefore a cache miss on every session.
    """
    if not directory.is_dir():
        raise RuleError(f"{directory}: not a directory")

    rules = tuple(sorted((load_rule(p) for p in directory.glob("*.md")), key=lambda r: r.name))

    names = [r.name for r in rules]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise RuleError(f"{directory}: duplicate rule name(s): {', '.join(sorted(duplicates))}")

    digest = hashlib.sha256("".join(f"{r.name}:{r.version}" for r in rules).encode()).hexdigest()
    return RuleSet(rules=rules, version=digest[:16])
