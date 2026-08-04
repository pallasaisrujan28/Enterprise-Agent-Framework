"""The obligation library, checker by checker.

Every path here is a fail-closed path. A checker that quietly returns None when
it cannot do its job hands the tenant a control that does nothing, which is
strictly worse than having no control — they would have compensated for an
absence, but not for a lie.
"""

from __future__ import annotations

import pytest

from agent.gate import evaluate
from agent.skills_engine.model import Draft, Obligation, Skill
from agent.skills_engine.obligations import check, known_kinds, register


def _skill(*obligations: Obligation) -> Skill:
    return Skill(
        name="s",
        description="Test skill.",
        version="deadbeef",
        body="body",
        obligations=obligations,
        source=None,  # type: ignore[arg-type]
    )


def _draft(**kw) -> Draft:
    return Draft(answer="a", **kw)


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------


def test_the_documented_kinds_are_all_registered():
    assert set(known_kinds()) == {
        "must_ask_when_missing",
        "must_cite",
        "must_disclose",
        "must_not_call",
        "requires_approval_when",
    }


def test_registering_a_duplicate_kind_is_refused():
    """Two checkers claiming one name means one of them silently never runs."""
    with pytest.raises(ValueError, match="already registered"):
        register("must_cite")(lambda d, o: None)


def test_an_unknown_kind_fails_closed():
    detail = check(_draft(), Obligation(kind="must_levitate", params={}))
    assert detail is not None
    assert "unknown obligation kind" in detail


# --------------------------------------------------------------------------
# must_cite
# --------------------------------------------------------------------------


def test_must_cite_filters_by_substring():
    ob = Obligation(kind="must_cite", params={"contains": "legislation.gov.uk"})
    assert check(_draft(citations=("https://example.com/x",)), ob) is not None
    assert check(_draft(citations=("https://www.legislation.gov.uk/x",)), ob) is None


def test_must_cite_honours_min_count():
    ob = Obligation(kind="must_cite", params={"min_count": 2})
    assert check(_draft(citations=("a",)), ob) is not None
    assert check(_draft(citations=("a", "b")), ob) is None


def test_must_cite_ignores_blank_citations():
    """An empty string is not a citation, and must not be counted as one."""
    ob = Obligation(kind="must_cite", params={})
    assert check(_draft(citations=("", "   ")), ob) is not None


# --------------------------------------------------------------------------
# must_ask_when_missing
# --------------------------------------------------------------------------


def test_must_ask_treats_empty_values_as_missing():
    """None, empty string and empty list are all "never established"."""
    ob = Obligation(kind="must_ask_when_missing", params={"fields": ["extent"]})
    for empty in (None, "", []):
        assert check(_draft(facts={"extent": empty}), ob) is not None
    assert check(_draft(facts={"extent": "England"}), ob) is None


def test_must_ask_with_no_fields_configured_holds_trivially():
    ob = Obligation(kind="must_ask_when_missing", params={})
    assert check(_draft(), ob) is None


# --------------------------------------------------------------------------
# must_disclose
# --------------------------------------------------------------------------


def test_must_disclose_requires_a_when_key():
    """A misconfigured obligation is a violation, not a pass."""
    detail = check(_draft(), Obligation(kind="must_disclose", params={}))
    assert detail is not None
    assert "requires a 'when'" in detail


def test_must_disclose_defaults_the_label_to_the_fact_key():
    ob = Obligation(kind="must_disclose", params={"when": "is_repealed"})
    assert check(_draft(facts={"is_repealed": True}), ob) is not None
    assert check(_draft(facts={"is_repealed": True}, disclosures=("is_repealed",)), ob) is None


# --------------------------------------------------------------------------
# requires_approval_when
# --------------------------------------------------------------------------


def test_requires_approval_needs_a_tool_configured():
    detail = check(_draft(), Obligation(kind="requires_approval_when", params={}))
    assert detail is not None
    assert "requires a 'tool'" in detail


def test_requires_approval_only_fires_when_the_tool_ran():
    ob = Obligation(kind="requires_approval_when", params={"tool": "register_write"})
    assert check(_draft(tools_called=("leg_get_provision",)), ob) is None
    assert check(_draft(tools_called=("register_write",)), ob) is not None
    assert (
        check(_draft(tools_called=("register_write",), approvals=("register_write",)), ob) is None
    )


# --------------------------------------------------------------------------
# must_not_call
# --------------------------------------------------------------------------


def test_must_not_call_names_every_forbidden_tool_used():
    ob = Obligation(kind="must_not_call", params={"tools": ["shell", "http_post"]})
    assert check(_draft(tools_called=("leg_search",)), ob) is None
    detail = check(_draft(tools_called=("shell", "http_post")), ob)
    assert detail is not None
    assert "http_post" in detail and "shell" in detail


# --------------------------------------------------------------------------
# the gate around them
# --------------------------------------------------------------------------


def test_gate_records_observe_mode_violations_without_blocking():
    skill = _skill(Obligation(kind="must_cite", params={}, mode="observe"))
    result = evaluate(_draft(citations=()), (skill,))
    assert result.passed
    assert len(result.observed) == 1
    assert result.blocking == ()


def test_gate_fails_closed_when_a_checker_raises():
    """An exception inside the gate must block, not wave the answer through.

    This is the opposite of how a streaming glitch should behave, and it is
    deliberate: a control that fails open is absent exactly when something has
    already gone wrong.
    """
    boom = Obligation(kind="must_ask_when_missing", params={"fields": "not-a-list"})
    # params.fields is a string, so the checker iterates characters and then
    # calls draft.fact() on each — the point is that whatever goes wrong, the
    # gate does not let the answer past.
    skill = _skill(boom)
    result = evaluate(_draft(facts={}), (skill,))
    assert not result.passed


def test_violation_renders_its_severity():
    skill = _skill(Obligation(kind="must_cite", params={}))
    result = evaluate(_draft(citations=()), (skill,))
    assert str(result.blocking[0]).startswith("[BLOCK]")
