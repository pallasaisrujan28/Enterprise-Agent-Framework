"""The tests that decide whether the premise holds.

The claim being tested is narrow and falsifiable: a skill can bind the agent's
behaviour in a way we can prove. If a draft answer that breaks a skill's
obligations can reach a user, the design does not work — regardless of how good
the prompt is.

None of this needs AWS, a model, or a network. That is the point of putting
enforcement outside the model: the control is testable on its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.gate import evaluate
from agent.obligation_policy import ObligationPolicy, load_policy
from agent.skills_engine import Draft, load_skillset
from agent.skills_engine.model import Obligation

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
OBLIGATIONS_DIR = Path(__file__).resolve().parent.parent / "obligations"


@pytest.fixture
def legislation_policy():
    """A STRICT policy for exercising the gate MECHANISM.

    Built inline, deliberately independent of the shipped
    obligations/legislation.yaml. The shipped policy is intentionally eased (see
    test_shipped_legislation_policy_is_eased); these tests still need the strict
    obligations to prove the gate can enforce version-pinning, ask-when-missing,
    and disclosure. Keeping them inline decouples "does the gate work" from "what
    do we currently ship".
    """
    return ObligationPolicy(
        name="legislation",
        description="statutory interpretation (test fixture)",
        obligations=(
            Obligation(
                kind="must_cite",
                params={"contains": "legislation.gov.uk", "version_pinned": True},
            ),
            Obligation(kind="must_ask_when_missing", params={"fields": ["as_at_date"]}),
            Obligation(
                kind="must_disclose",
                params={"when": "unapplied_effects_exist", "disclose": "unapplied_effects"},
            ),
        ),
    )


def _good_draft(**overrides):
    """A draft that satisfies every obligation in the legislation policy."""
    base = {
        "answer": "Section 172 requires a director to act in the way he considers...",
        "citations": ("https://www.legislation.gov.uk/ukpga/2006/46/section/172/2021-03-01",),
        "disclosures": (),
        "tools_called": ("leg_get_provision",),
        "asked_user": False,
        "approvals": (),
        "facts": {"as_at_date": "2021-03-01", "unapplied_effects_exist": False},
    }
    base.update(overrides)
    return Draft(**base)


def test_compliant_answer_is_delivered(legislation_policy):
    result = evaluate(_good_draft(), (legislation_policy,))
    assert result.passed, result.reason()
    assert result.violations == ()


def test_unpinned_citation_is_blocked(legislation_policy):
    """A citation without a date names a provision but not which version of it.

    This is the failure this domain punishes hardest: fluent, correctly cited,
    and silently about a different version of the law.
    """
    draft = _good_draft(citations=("https://www.legislation.gov.uk/ukpga/2006/46/section/172",))
    result = evaluate(draft, (legislation_policy,))
    assert not result.passed
    assert "not version-pinned" in result.reason()


def test_no_citation_at_all_is_blocked(legislation_policy):
    result = evaluate(_good_draft(citations=()), (legislation_policy,))
    assert not result.passed
    assert "must_cite" in result.reason()


def test_answering_without_a_date_is_blocked(legislation_policy):
    """THE test. The model was asked a date-less question and answered anyway.

    A prompt can only make asking likely. This makes answering impossible.
    """
    draft = _good_draft(facts={"as_at_date": None, "unapplied_effects_exist": False})
    result = evaluate(draft, (legislation_policy,))
    assert not result.passed
    assert "as_at_date" in result.reason()


def test_asking_instead_of_answering_satisfies_the_obligation(legislation_policy):
    """The escape hatch is asking, not guessing — so asking must pass."""
    draft = _good_draft(
        facts={"as_at_date": None, "unapplied_effects_exist": False},
        asked_user=True,
    )
    result = evaluate(draft, (legislation_policy,))
    assert result.passed, result.reason()


def test_undisclosed_unapplied_effects_are_blocked(legislation_policy):
    """Version-pinning is necessary but not sufficient.

    The published text at a date can lawfully omit amendments that are in force
    but not yet editorially applied. Silence there produces an answer that is
    correctly cited and still not the current law.
    """
    draft = _good_draft(facts={"as_at_date": "2021-03-01", "unapplied_effects_exist": True})
    result = evaluate(draft, (legislation_policy,))
    assert not result.passed
    assert "unapplied_effects" in result.reason()


def test_disclosing_them_satisfies_the_obligation(legislation_policy):
    draft = _good_draft(
        facts={"as_at_date": "2021-03-01", "unapplied_effects_exist": True},
        disclosures=("unapplied_effects",),
    )
    result = evaluate(draft, (legislation_policy,))
    assert result.passed, result.reason()


def test_untriggered_policies_do_not_judge_the_answer(legislation_policy):
    """A policy whose domain never applied has no business blocking.

    Obligations are the enforcement half of a specific instruction, not
    free-floating platform policy.
    """
    result = evaluate(_good_draft(citations=()), ())
    assert result.passed


def test_multiple_violations_are_all_reported(legislation_policy):
    """Report every failure, not the first.

    One at a time means the model fixes one, resubmits, fails on the next, and
    burns a turn per violation.
    """
    draft = _good_draft(
        citations=(),
        facts={"as_at_date": None, "unapplied_effects_exist": True},
    )
    result = evaluate(draft, (legislation_policy,))
    assert len(result.blocking) == 3


def test_shipped_skillset_loads_and_is_pinned():
    """The skills we ship must parse, and the set must have a stable version."""
    skillset = load_skillset(SKILLS_DIR)
    assert skillset.skills
    assert len(skillset.version) == 16
    assert load_skillset(SKILLS_DIR).version == skillset.version


def test_shipped_legislation_policy_is_eased():
    """The SHIPPED policy is deliberately lenient, distinct from the strict
    fixture above. This locks the easing so it is not silently tightened back:

      - must_ask_when_missing is OBSERVE (can't be satisfied from prose yet), so
        it records rather than blocks — otherwise every legislation answer blocks.
      - must_cite does NOT demand version-pinning (a legislation.gov.uk source
        suffices), so a correct answer is not withheld for lacking a date segment.
    """
    policy = load_policy(OBLIGATIONS_DIR / "legislation.yaml")
    by_kind = {o.kind: o for o in policy.obligations}

    assert by_kind["must_ask_when_missing"].mode == "observe"
    assert not by_kind["must_ask_when_missing"].blocking
    assert not by_kind["must_cite"].params.get("version_pinned", False)
