"""Loading rules, and refusing the ones that would be a lie.

A malformed rule must fail at load, loudly. A rule that silently loads without
its enforcement is worse than no rule at all: the tenant believes a control
exists and it does not.
"""

from __future__ import annotations

import pytest

from agent.rules import RuleError, load_rule, load_ruleset

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


def test_loads_a_well_formed_rule(tmp_path):
    rule = load_rule(_write(tmp_path, GOOD))
    assert rule.name == "demo"
    assert rule.body == "Body text."
    assert len(rule.obligations) == 1
    assert rule.obligations[0].blocking is True


def test_version_is_content_addressed(tmp_path):
    first = load_rule(_write(tmp_path, GOOD, "a.md"))
    same = load_rule(_write(tmp_path, GOOD, "b.md"))
    changed = load_rule(_write(tmp_path, GOOD.replace("Body text.", "Different."), "c.md"))
    assert first.version == same.version
    assert first.version != changed.version


def test_rejects_an_overlong_description(tmp_path):
    """The index line is the only part every request pays for, so it is capped."""
    long_desc = "x" * 61
    text = GOOD.replace("A short description.", long_desc)
    with pytest.raises(RuleError, match="limit is 60"):
        load_rule(_write(tmp_path, text))


def test_rejects_an_unknown_obligation_kind(tmp_path):
    """Fail closed: the file expects a guarantee this build cannot provide."""
    text = GOOD.replace("must_cite: {min_count: 1}", "must_be_nice: {}")
    with pytest.raises(RuleError, match="unknown obligation kind"):
        load_rule(_write(tmp_path, text))


def test_rejects_an_empty_body(tmp_path):
    text = "---\nname: demo\ndescription: Short.\n---\n"
    with pytest.raises(RuleError, match="body is empty"):
        load_rule(_write(tmp_path, text))


def test_rejects_a_missing_description(tmp_path):
    text = "---\nname: demo\n---\n\nBody.\n"
    with pytest.raises(RuleError, match="'description' is required"):
        load_rule(_write(tmp_path, text))


def test_rejects_unclosed_frontmatter(tmp_path):
    text = "---\nname: demo\ndescription: Short.\n\nBody.\n"
    with pytest.raises(RuleError, match="never closed"):
        load_rule(_write(tmp_path, text))


def test_observe_mode_obligations_do_not_block(tmp_path):
    """A new rule starts advisory and is promoted once traffic shows it is safe."""
    text = GOOD.replace("{min_count: 1}", "{min_count: 1, mode: observe}")
    rule = load_rule(_write(tmp_path, text))
    assert rule.obligations[0].blocking is False


def test_ruleset_index_is_sorted_for_a_stable_prefix(tmp_path):
    """Filesystem order is not guaranteed; a reordered index is a cache miss."""
    _write(tmp_path, GOOD.replace("name: demo", "name: zebra"), "z.md")
    _write(tmp_path, GOOD.replace("name: demo", "name: alpha"), "a.md")
    ruleset = load_ruleset(tmp_path)
    assert [r.name for r in ruleset.rules] == ["alpha", "zebra"]
    assert ruleset.index_block().splitlines()[0].startswith("- alpha:")


def test_ruleset_rejects_duplicate_names(tmp_path):
    _write(tmp_path, GOOD, "one.md")
    _write(tmp_path, GOOD, "two.md")
    with pytest.raises(RuleError, match="duplicate rule name"):
        load_ruleset(tmp_path)
