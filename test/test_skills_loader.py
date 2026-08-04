"""Loading skills, and refusing the ones that would be a lie.

A malformed skill must fail at load, loudly. A skill that silently loads without
its enforcement is worse than no skill at all: the tenant believes a control
exists and it does not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.skills_engine import (
    SkillError,
    load_skill,
    load_skillset,
    validate_against_catalog,
    validate_scopes,
)

GOOD = """---
name: demo
description: A short description.
obligations:
  - must_cite: {min_count: 1}
---

Body text.
"""


def _write(tmp_path, text, name="demo.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_a_well_formed_skill(tmp_path):
    skill = load_skill(_write(tmp_path, GOOD))
    assert skill.name == "demo"
    assert skill.body == "Body text."
    assert len(skill.obligations) == 1
    assert skill.obligations[0].blocking is True


def test_version_is_content_addressed(tmp_path):
    first = load_skill(_write(tmp_path, GOOD, "a.md"))
    same = load_skill(_write(tmp_path, GOOD, "b.md"))
    changed = load_skill(_write(tmp_path, GOOD.replace("Body text.", "Different."), "c.md"))
    assert first.version == same.version
    assert first.version != changed.version


def test_rejects_an_overlong_description(tmp_path):
    """The index line is the only part every request pays for, so it is capped."""
    long_desc = "x" * 61
    text = GOOD.replace("A short description.", long_desc)
    with pytest.raises(SkillError, match="limit is 60"):
        load_skill(_write(tmp_path, text))


def test_rejects_an_unknown_obligation_kind(tmp_path):
    """Fail closed: the file expects a guarantee this build cannot provide."""
    text = GOOD.replace("must_cite: {min_count: 1}", "must_be_nice: {}")
    with pytest.raises(SkillError, match="unknown obligation kind"):
        load_skill(_write(tmp_path, text))


def test_rejects_an_empty_body(tmp_path):
    text = "---\nname: demo\ndescription: Short.\n---\n"
    with pytest.raises(SkillError, match="body is empty"):
        load_skill(_write(tmp_path, text))


def test_rejects_a_missing_description(tmp_path):
    text = "---\nname: demo\n---\n\nBody.\n"
    with pytest.raises(SkillError, match="'description' is required"):
        load_skill(_write(tmp_path, text))


def test_rejects_unclosed_frontmatter(tmp_path):
    text = "---\nname: demo\ndescription: Short.\n\nBody.\n"
    with pytest.raises(SkillError, match="never closed"):
        load_skill(_write(tmp_path, text))


def test_observe_mode_obligations_do_not_block(tmp_path):
    """A new skill starts advisory and is promoted once traffic shows it is safe."""
    text = GOOD.replace("{min_count: 1}", "{min_count: 1, mode: observe}")
    skill = load_skill(_write(tmp_path, text))
    assert skill.obligations[0].blocking is False


def test_skillset_index_is_sorted_for_a_stable_prefix(tmp_path):
    """Filesystem order is not guaranteed; a reordered index is a cache miss."""
    _write(tmp_path, GOOD.replace("name: demo", "name: zebra"), "z.md")
    _write(tmp_path, GOOD.replace("name: demo", "name: alpha"), "a.md")
    skillset = load_skillset(tmp_path)
    assert [s.name for s in skillset.skills] == ["alpha", "zebra"]
    assert skillset.index_block().splitlines()[0].startswith("- alpha:")


def test_skillset_rejects_duplicate_names(tmp_path):
    _write(tmp_path, GOOD, "one.md")
    _write(tmp_path, GOOD, "two.md")
    with pytest.raises(SkillError, match="duplicate skill name"):
        load_skillset(tmp_path)


# --- Declared tools and scopes (ADR-021) -----------------------------------
#
# Semantic tool search returns a RANKING, and a ranking can be wrong without
# saying so. A skill that names its own tools turns a silent bad ranking into a
# detectable one, so the parsing of those names has to be strict.


def test_declared_tools_and_scopes_are_parsed(tmp_path):
    text = GOOD.replace(
        "obligations:",
        "required_tools: [leg_get_provision, leg_get_contents]\n"
        "required_scopes: [legislation:read]\n"
        "obligations:",
    )
    skill = load_skill(_write(tmp_path, text))
    assert skill.required_tools == ("leg_get_contents", "leg_get_provision")
    assert skill.required_scopes == ("legislation:read",)


def test_declared_tools_default_to_empty(tmp_path):
    """Omitting the field is legal: a semantic-mode agent need not declare."""
    skill = load_skill(_write(tmp_path, GOOD))
    assert skill.required_tools == ()
    assert skill.required_scopes == ()


def test_declared_tools_are_sorted_and_deduplicated(tmp_path):
    """Order feeds catalog composition, which feeds the cached prefix."""
    text = GOOD.replace(
        "obligations:", "required_tools: [zeta, alpha, zeta, ' alpha ']\nobligations:"
    )
    skill = load_skill(_write(tmp_path, text))
    assert skill.required_tools == ("alpha", "zeta")


def test_rejects_a_bare_string_where_a_list_is_required(tmp_path):
    """A YAML scalar would silently iterate as characters. Refuse it instead."""
    text = GOOD.replace("obligations:", "required_tools: leg_get_provision\nobligations:")
    with pytest.raises(SkillError, match="must be a list of strings"):
        load_skill(_write(tmp_path, text))


def test_rejects_a_non_string_entry(tmp_path):
    text = GOOD.replace("obligations:", "required_tools: [leg_get_provision, 7]\nobligations:")
    with pytest.raises(SkillError, match="non-string or empty entry"):
        load_skill(_write(tmp_path, text))


def test_rejects_an_empty_entry(tmp_path):
    text = GOOD.replace("obligations:", "required_tools: [leg_get_provision, '  ']\nobligations:")
    with pytest.raises(SkillError, match="non-string or empty entry"):
        load_skill(_write(tmp_path, text))


def test_rejects_a_mapping_where_a_list_is_required(tmp_path):
    text = GOOD.replace("obligations:", "required_scopes: {a: b}\nobligations:")
    with pytest.raises(SkillError, match="must be a list of strings"):
        load_skill(_write(tmp_path, text))


def test_catalog_validation_names_every_missing_tool(tmp_path):
    """Returns all problems rather than raising on the first, so one report
    covers a whole skillset instead of one skill at a time."""
    text = GOOD.replace("obligations:", "required_tools: [present, gone, also_gone]\nobligations:")
    skill = load_skill(_write(tmp_path, text))
    assert validate_against_catalog(skill, {"present", "unrelated"}) == ["also_gone", "gone"]


def test_catalog_validation_passes_when_every_tool_resolves(tmp_path):
    text = GOOD.replace("obligations:", "required_tools: [present]\nobligations:")
    skill = load_skill(_write(tmp_path, text))
    assert validate_against_catalog(skill, {"present", "spare"}) == []


def test_scope_validation_catches_a_skill_widening_access(tmp_path):
    """A skill may narrow access or use what the agent holds. Never widen it."""
    text = GOOD.replace(
        "obligations:", "required_scopes: [legislation:read, hr:write]\nobligations:"
    )
    skill = load_skill(_write(tmp_path, text))
    assert validate_scopes(skill, {"legislation:read"}) == ["hr:write"]


def test_scope_validation_passes_within_the_agents_grants(tmp_path):
    text = GOOD.replace("obligations:", "required_scopes: [legislation:read]\nobligations:")
    skill = load_skill(_write(tmp_path, text))
    assert validate_scopes(skill, {"legislation:read", "legislation:search"}) == []


def test_the_shipped_legislation_skill_declares_only_catalog_tools():
    """The real skill file, checked against the tool names the design commits to.
    Catches a rename in one file that was not made in the other."""
    repo_root = Path(__file__).resolve().parent.parent
    skill = load_skill(repo_root / "skills" / "legislation_advice.md")
    catalog = {
        "leg_resolve_identifier",
        "leg_get_contents",
        "leg_get_provision",
        "leg_traverse_amendments",
    }
    assert validate_against_catalog(skill, catalog) == []
    assert validate_scopes(skill, {"legislation:read"}) == []
