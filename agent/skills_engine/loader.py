"""Reading skill files, and refusing the ones that are not enforceable.

A skill file is markdown with YAML frontmatter:

    ---
    name: legislation_advice
    description: Answering questions about UK statute.
    required_tools: [leg_get_provision]
    required_scopes: [legislation:read]
    obligations:
      - must_cite: {contains: legislation.gov.uk, version_pinned: true}
      - must_ask_when_missing: {fields: [as_at_date]}
    ---

    ## Procedure
    ...

Validation is strict and fails at load, not at run. A skill that cannot be
enforced is worse than no skill: the tenant believes a control exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.skills_engine import obligations as ob_lib
from agent.skills_engine.model import (
    MAX_DESCRIPTION_CHARS,
    MODE_ENFORCE,
    MODES,
    Obligation,
    Skill,
)

_FRONTMATTER = "---"


class SkillError(ValueError):
    """A skill file is malformed or unenforceable."""


@dataclass(frozen=True)
class SkillSet:
    """The skills granted to one agent, pinned for the life of a session.

    Pinned because the index lives in the cached prefix: attaching a skill
    mid-session would rewrite the prefix and invalidate the cache for every
    turn that follows. Newly granted skills take effect for sessions started
    after promotion.
    """

    skills: tuple[Skill, ...]
    version: str

    def by_name(self, name: str) -> Skill | None:
        return next((s for s in self.skills if s.name == name), None)

    def index_block(self) -> str:
        """The skill index, for the stable prefix."""
        if not self.skills:
            return "(no skills granted)"
        return "\n".join(s.index_line() for s in self.skills)


def _split_frontmatter(text: str, source: Path) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER:
        raise SkillError(f"{source}: must begin with a '---' frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _FRONTMATTER)
    except StopIteration:
        raise SkillError(f"{source}: frontmatter block is never closed") from None
    meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(meta, dict):
        raise SkillError(f"{source}: frontmatter must be a mapping")
    return meta, "\n".join(lines[end + 1 :]).strip()


def _str_tuple(raw: object, field: str, source: Path) -> tuple[str, ...]:
    """Parse a list-of-strings frontmatter field, sorted and de-duplicated.

    Sorted because these feed catalog composition, and catalog composition feeds
    the cached prefix — an unstable order is an unstable prefix and therefore a
    cache miss on every session.
    """
    if raw is None:
        return ()
    if isinstance(raw, str) or not isinstance(raw, list):
        raise SkillError(f"{source}: '{field}' must be a list of strings, got {raw!r}")
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise SkillError(f"{source}: '{field}' contains a non-string or empty entry: {item!r}")
    return tuple(sorted({item.strip() for item in raw}))


def validate_against_catalog(skill: Skill, catalog_tools: set[str]) -> list[str]:
    """Names in `required_tools` that do not exist in the pinned catalog.

    Separate from load_skill because loading a skill file and knowing the catalog
    are different concerns that happen at different times — skills are parsed
    from disk, the catalog comes from the gateway. Returns the problems rather
    than raising, so a caller can report every broken skill at once instead of
    failing on the first.
    """
    return sorted(set(skill.required_tools) - catalog_tools)


def validate_scopes(skill: Skill, agent_scopes: set[str]) -> list[str]:
    """Scopes the skill asks for that the agent does not hold.

    Non-empty means the skill would widen the agent's access, which is refused —
    a skill is not a side door around policy.
    """
    return sorted(set(skill.required_scopes) - agent_scopes)


def _parse_obligations(raw: object, source: Path) -> tuple[Obligation, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SkillError(f"{source}: 'obligations' must be a list")

    parsed: list[Obligation] = []
    for entry in raw:
        if not isinstance(entry, dict) or len(entry) != 1:
            raise SkillError(
                f"{source}: each obligation must be a single-key mapping, got {entry!r}"
            )
        kind, params = next(iter(entry.items()))
        params = dict(params or {})
        mode = str(params.pop("mode", MODE_ENFORCE))
        if mode not in MODES:
            raise SkillError(f"{source}: obligation '{kind}' has unknown mode '{mode}'")
        if kind not in ob_lib.known_kinds():
            raise SkillError(
                f"{source}: unknown obligation kind '{kind}'. "
                f"Known kinds: {', '.join(ob_lib.known_kinds())}"
            )
        parsed.append(Obligation(kind=kind, params=params, mode=mode))
    return tuple(parsed)


def load_skill(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text, path)

    name = meta.get("name")
    if not name:
        raise SkillError(f"{path}: 'name' is required")

    description = (meta.get("description") or "").strip()
    if not description:
        raise SkillError(
            f"{path}: 'description' is required — it is how the model selects this skill"
        )
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise SkillError(
            f"{path}: description is {len(description)} chars, limit is {MAX_DESCRIPTION_CHARS}. "
            "It sits in the always-resident index that every request pays for."
        )

    if not body:
        raise SkillError(f"{path}: skill body is empty — there is no guidance to give the model")

    return Skill(
        name=str(name),
        description=description,
        required_tools=_str_tuple(meta.get("required_tools"), "required_tools", path),
        required_scopes=_str_tuple(meta.get("required_scopes"), "required_scopes", path),
        # Content-addressed, so a skill version is the skill. Two deployments
        # claiming the same version cannot be holding different text.
        version=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        body=body,
        obligations=_parse_obligations(meta.get("obligations"), path),
        source=path,
    )


def load_skillset(directory: Path) -> SkillSet:
    """Load every skill in a directory, sorted by name for a stable prefix.

    Sorted because the index goes into the cached prefix: filesystem iteration
    order is not guaranteed, and a reordered index is a different prefix and
    therefore a cache miss on every session.
    """
    if not directory.is_dir():
        raise SkillError(f"{directory}: not a directory")

    skills = tuple(sorted((load_skill(p) for p in directory.glob("*.md")), key=lambda s: s.name))

    names = [s.name for s in skills]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise SkillError(f"{directory}: duplicate skill name(s): {', '.join(sorted(duplicates))}")

    digest = hashlib.sha256("".join(f"{s.name}:{s.version}" for s in skills).encode()).hexdigest()
    return SkillSet(skills=skills, version=digest[:16])
