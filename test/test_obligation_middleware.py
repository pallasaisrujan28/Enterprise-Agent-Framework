"""Tests for the parts of the obligation gate that actually broke.

DELIBERATELY NARROW. These do not re-test the harness or the model — they pin the
handful of behaviours that were subtle enough to ship wrong and cheap enough to
regress silently:

  - `asked_user` inference. Hardcoded False once, which made an obligation
    IMPOSSIBLE to satisfy — the model asked for the missing field, as told, and
    was refused for not asking.
  - the degraded distinction. A broken router must report `unverified`, not the
    same clean `nothing-to-enforce` a genuinely unregulated turn gets, or the
    gate silently stops being one.
  - the block verdict withholds the answer but keeps the draft for audit.
  - a failing tool becomes a readable message, not a crash.

All run with no network and no credentials: the router is a fake, and obligation
policies load from a tmp directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agent.middleware import obligations as ob
from agent.obligation_policy import PolicySet, load_policies

# A policy whose must_cite obligation is easy to violate and easy to satisfy.
CITE_POLICY = """
name: legislation
description: Answering questions about UK statute.
obligations:
  - must_cite: {contains: legislation.gov.uk, min_count: 1}
"""


class FakeRouter:
    """A stand-in chat model. `.invoke(prompt).text` is all the gate calls."""

    def __init__(self, reply: str = "NONE", *, boom: bool = False) -> None:
        self._reply = reply
        self._boom = boom

    def invoke(self, _prompt: Any) -> Any:
        if self._boom:
            raise RuntimeError("router is down")
        return type("R", (), {"text": self._reply})()


@pytest.fixture
def policies(tmp_path: Path) -> PolicySet:
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    return load_policies(tmp_path)


def ai(text: str) -> Any:
    """A minimal stand-in for an AIMessage: has .text and a type of 'ai'."""
    from langchain_core.messages import AIMessage

    return AIMessage(content=text)


def human(text: str) -> Any:
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=text)


# ── draft_from: the asked_user regression ─────────────────────────────────────


def test_a_clarifying_question_is_read_as_having_asked() -> None:
    """The exact shape that was refused for not asking, when it had."""
    draft = ob.draft_from("Which date did you mean? UK law changes over time.")
    assert draft.asked_user is True


def test_a_long_assertive_answer_is_not_read_as_asking() -> None:
    """A rhetorical question buried in an essay has not asked the user anything.

    Biased towards NOT claiming a question, because a false 'asked' would let an
    answer through that should have paused for input.
    """
    essay = "The answer is definitely yes. " * 40 + "Is that not obvious?"
    draft = ob.draft_from(essay)
    assert draft.asked_user is False


def test_urls_become_citations() -> None:
    draft = ob.draft_from("See https://www.legislation.gov.uk/ukpga/2010/15 for the detail.")
    assert any("legislation.gov.uk" in c for c in draft.citations)


# ── routing: the degraded distinction ────────────────────────────────────────


def test_a_working_router_that_finds_nothing_is_not_degraded(policies: PolicySet) -> None:
    gate = ob.ObligationGateMiddleware(router=FakeRouter("NONE"))
    selected, _reason, degraded = gate._route("what is 2 plus 2", policies)
    assert selected == ()
    assert degraded is False


def test_a_failed_router_is_degraded_and_surfaces_the_error(policies: PolicySet) -> None:
    """A router failure is CAUGHT — not swallowed silently, not replaced by a
    keyword matcher, and not left to crash the turn.

    It yields no policies, marks the turn degraded (reported as `unverified`), and
    carries the actual error in the reason so the failure is visible.
    """
    gate = ob.ObligationGateMiddleware(router=FakeRouter(boom=True))
    selected, reason, degraded = gate._route(
        "does an employer have to give a written statement", policies
    )
    assert selected == ()
    assert degraded is True
    assert "router failed" in reason
    assert "RuntimeError" in reason


def test_no_router_configured_is_degraded_not_a_clean_pass(policies: PolicySet) -> None:
    """No router means routing cannot run — degraded, not a silent 'nothing'."""
    gate = ob.ObligationGateMiddleware(router=None)
    selected, _reason, degraded = gate._route("a legislation question", policies)
    assert selected == ()
    assert degraded is True


def test_an_unrelated_question_is_not_mis_routed(policies: PolicySet) -> None:
    """Regression: the old keyword fallback matched a LinkedIn request to the
    legislation policy on stray words like 'about'/'their' (both in the policy
    description prose) and blocked it. With the model as the only router, an
    unrelated question the router judges NONE simply has nothing to enforce."""
    gate = ob.ObligationGateMiddleware(router=FakeRouter("NONE"))
    selected, _reason, degraded = gate._route(
        "can you search about Data Reply UK and fetch their LinkedIn posts", policies
    )
    assert selected == ()
    assert degraded is False


def test_the_router_only_selects_policies_that_exist(policies: PolicySet) -> None:
    """A hallucinated policy name is dropped, not turned into a KeyError."""
    gate = ob.ObligationGateMiddleware(router=FakeRouter("made_up_policy, legislation"))
    selected, _reason, _degraded = gate._route("a legislation question", policies)
    assert [p.name for p in selected] == ["legislation"]


# ── after_agent: the verdicts ─────────────────────────────────────────────────


def _run(gate: ob.ObligationGateMiddleware, user: str, answer: str) -> dict:
    state = {"messages": [human(user), ai(answer)]}
    return gate.after_agent(state, runtime=None) or {}


def test_block_withholds_the_answer_but_keeps_the_draft(
    policies: PolicySet, tmp_path: Path
) -> None:
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    gate = ob.ObligationGateMiddleware(router=FakeRouter("legislation"), policies_dir=str(tmp_path))
    update = _run(gate, "a legislation question", "Employers must comply. No citation here.")
    verdict = update["obligation_verdict"]
    assert verdict["decision"] == "block"
    # the withheld draft is kept for audit
    assert "No citation here." in verdict["draft"]
    # but what the user now sees is the refusal, not the draft
    assert update["messages"], "a block must replace the message"
    assert "No citation here." not in update["messages"][0].text
    assert "must_cite" in update["messages"][0].text


def test_a_satisfied_obligation_passes(policies: PolicySet, tmp_path: Path) -> None:
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    gate = ob.ObligationGateMiddleware(router=FakeRouter("legislation"), policies_dir=str(tmp_path))
    update = _run(
        gate,
        "a legislation question",
        "Per https://www.legislation.gov.uk/ukpga/2010/15 employers must comply.",
    )
    assert update["obligation_verdict"]["decision"] == "pass"
    # a pass does not rewrite the message
    assert "messages" not in update


def test_no_policy_is_nothing_to_enforce_not_a_pass(policies: PolicySet, tmp_path: Path) -> None:
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    gate = ob.ObligationGateMiddleware(router=FakeRouter("NONE"), policies_dir=str(tmp_path))
    update = _run(gate, "what is 2 plus 2", "4")
    assert update["obligation_verdict"]["decision"] == "nothing-to-enforce"


def test_a_broken_router_reports_unverified(policies: PolicySet, tmp_path: Path) -> None:
    """A router failure during a real turn is caught and reported as `unverified`
    — nothing was checked, the verdict says so, and the answer is not rewritten.

    `unverified` does NOT withhold the message: reporting that nothing could be
    checked is not the same as refusing, and whether to refuse on a routing
    outage is a separate policy decision made elsewhere.
    """
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    gate = ob.ObligationGateMiddleware(router=FakeRouter(boom=True), policies_dir=str(tmp_path))
    update = _run(
        gate, "does an employer have to give a written statement", "Some answer, no citation."
    )
    verdict = update["obligation_verdict"]
    assert verdict["decision"] == "unverified"
    assert "NO obligation was checked" in verdict["reason"]
    assert "messages" not in update


def test_an_empty_answer_is_left_alone(policies: PolicySet, tmp_path: Path) -> None:
    (tmp_path / "legislation.yaml").write_text(CITE_POLICY)
    gate = ob.ObligationGateMiddleware(router=FakeRouter("NONE"), policies_dir=str(tmp_path))
    assert _run(gate, "hello", "   ") == {}


# ── tool errors: crash becomes message ───────────────────────────────────────


def test_tool_error_becomes_a_readable_string_naming_the_tool() -> None:
    """ToolErrorMiddleware turns a returned string into a ToolMessage the model
    reads; returning None would re-raise and end the turn — the behaviour being
    prevented. Verified: web_search once succeeded and a failing fetch_and_store
    killed the whole turn, losing the good result."""
    from agent.brain import _tool_error_message

    class Req:
        tool_call = {"name": "fetch_and_store"}

    out = _tool_error_message(ConnectionError("no route to host"), Req())
    assert isinstance(out, str)
    assert "fetch_and_store" in out
    assert "ConnectionError" in out
