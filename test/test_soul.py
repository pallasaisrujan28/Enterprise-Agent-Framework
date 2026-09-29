"""Tests for the editable SOUL persona.

Pins the behaviour that matters: it seeds a default when absent, appends learned
rules under the right header (append-only), refuses past the size cap, and the
update_soul tool routes to the append path. All against a tmp file via
AGENT_SOUL_PATH — no repo file is touched.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def soul(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AGENT_SOUL_PATH", str(tmp_path / "soul.md"))
    import agent.soul as soul_mod

    return importlib.reload(soul_mod)


def test_load_seeds_default_when_missing(soul) -> None:
    text = soul.load_soul()
    assert "Agent persona" in text
    assert soul.soul_path().exists()  # seeded on first load


def test_append_adds_under_learned_rules(soul) -> None:
    soul.load_soul()
    status = soul.append_learned_rule("always answer in British English")
    assert "remember" in status.lower()
    text = soul.load_soul()
    assert "## Learned rules" in text
    assert "- always answer in British English" in text


def test_append_is_additive_not_overwriting(soul) -> None:
    soul.append_learned_rule("rule one")
    soul.append_learned_rule("rule two")
    text = soul.load_soul()
    assert "- rule one" in text
    assert "- rule two" in text


def test_empty_rule_is_rejected(soul) -> None:
    assert "empty" in soul.append_learned_rule("   ").lower()


def test_size_cap_refuses(soul, monkeypatch: pytest.MonkeyPatch) -> None:
    soul.soul_path().write_text("x" * (soul._SOUL_MAX_CHARS + 1), encoding="utf-8")
    assert "size limit" in soul.append_learned_rule("another rule").lower()


def test_update_soul_tool_appends(soul) -> None:
    soul.update_soul.invoke({"rule": "confirm twice before any payment"})
    assert "confirm twice before any payment" in soul.load_soul()
