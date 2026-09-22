"""Obligation policies — the enforceable half, split out from skills.

THE RECONCILIATION, IN ONE FILE.

A skill used to be two things fused together: *know-how* (how to answer a
question) and *obligations* (rules the answer must satisfy). That fusion is why
we had two incompatible notions of "skill" — ours, with obligations baked into
the frontmatter and enforced by the gate, and the deepagents/`SKILL.md` kind that
`npx skills add` installs and that carries no obligations at all. You could not
install a third-party skill through the gate, and our skills could not be
installed the normal way.

The fix is to stop fusing them:

  A SKILL is pure capability. One format — deepagents `SKILL.md` — loaded by
  SkillsMiddleware, disclosed into the prompt, installable from a GitHub URL.
  It teaches; it does not bind.

  An OBLIGATION POLICY is pure enforcement. Declared here, in `obligations/*.yaml`,
  by us or the business — never inside a third-party skill's file. The gate reads
  policies and enforces them by DOMAIN, independent of whether any skill fired.

So a third-party skill (archify) carries no policy and is never blocked, and a
governed domain (legislation) carries policy whether or not a matching skill is
installed. The two finally compose.

A policy declares a `description` (what domain it governs — used to route) and a
list of `obligations` (what the gate enforces). Nothing else.

NOTE ON NAMING: `agent/policies/` (plural) is a different, older thing — the
platform content rules (regex deny/log) applied to every request. These
obligation policies are per-domain answer contracts. Distinct concepts; the
`ObligationPolicy` name keeps them apart.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.skills_engine import obligations as ob_lib
from agent.skills_engine.model import MAX_DESCRIPTION_CHARS, Obligation


class PolicyError(ValueError):
    """An obligation policy file is malformed."""


@dataclass(frozen=True)
class ObligationPolicy:
    """One domain's answer contract: when it applies, and what it requires.

    Structurally compatible with Skill on purpose — both expose `.name` and
    `.obligations` — so `gate.evaluate` takes either without knowing which.
    """

    name: str
    description: str
    obligations: tuple[Obligation, ...] = ()
    source: Path | None = None

    def index_line(self) -> str:
        """One line for the router's index: what domain this governs."""
        return f"- {self.name}: {self.description}"


@dataclass(frozen=True)
class PolicySet:
    policies: tuple[ObligationPolicy, ...] = ()

    def index_block(self) -> str:
        if not self.policies:
            return "(no obligation policies)"
        return "\n".join(p.index_line() for p in self.policies)

    def __iter__(self) -> Iterator[ObligationPolicy]:
        return iter(self.policies)

    def __bool__(self) -> bool:
        return bool(self.policies)


def load_policy(path: Path) -> ObligationPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise PolicyError(f"{path}: policy file must be a YAML mapping")

    name = str(data.get("name") or "").strip()
    if not name:
        raise PolicyError(f"{path}: 'name' is required")

    description = str(data.get("description") or "").strip()
    if not description:
        raise PolicyError(
            f"{path}: 'description' is required — the router uses it to decide "
            "whether this policy's domain applies to a question"
        )
    if len(description) > MAX_DESCRIPTION_CHARS * 3:
        # A policy description is not in the KV-cached prefix (unlike a skill
        # index line), so the limit is looser — but still bounded, because it is
        # fed to the router every turn.
        raise PolicyError(f"{path}: description is too long ({len(description)} chars)")

    try:
        obligations = ob_lib.parse_obligations(data.get("obligations"), str(path))
    except ValueError as exc:
        raise PolicyError(str(exc)) from exc

    return ObligationPolicy(
        name=name, description=description, obligations=obligations, source=path
    )


def load_policies(directory: Path) -> PolicySet:
    """Every policy in a directory, sorted by name.

    A missing directory is not an error — a deployment with no obligation
    policies is valid, just one that enforces nothing. A malformed policy IS an
    error and raises, because a policy that cannot be parsed must not be silently
    treated as absent: the tenant believes a control exists.
    """
    if not directory.is_dir():
        return PolicySet()

    policies = tuple(
        sorted((load_policy(p) for p in directory.glob("*.yaml")), key=lambda p: p.name)
    )
    names = [p.name for p in policies]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise PolicyError(f"{directory}: duplicate policy name(s): {', '.join(sorted(duplicates))}")
    return PolicySet(policies=policies)
