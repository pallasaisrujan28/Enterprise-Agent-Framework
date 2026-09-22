"""The obligation gate, as deepagents middleware.

WHY THIS IS CUSTOM WHEN ALMOST NOTHING ELSE SHOULD BE
`.kiro/steering/coding-standards.md` says to find the deepagents component before
writing anything. There is none for this. `SkillsMiddleware` loads skills and
discloses them to the model; `RubricMiddleware` scores an answer after the fact;
`HumanInTheLoopMiddleware` pauses for a person. None of them *withhold* an answer
because a published obligation was not met, and that is the one thing this
platform exists to do — the model must not be able to reason its way past it.

WHAT THIS ENFORCES: POLICIES, NOT SKILLS
After the reconciliation (see agent/obligation_policy.py) a skill is pure
capability and carries no obligations. Enforcement lives in obligation POLICIES,
declared in `obligations/*.yaml` and enforced by DOMAIN — independent of whether
a matching skill is installed. This middleware routes the question to the
policies whose domain applies, then holds the finished answer against them.

WHY MIDDLEWARE RATHER THAN A WRAPPER AROUND THE AGENT
The previous version of this lived in a hand-rolled turn loop that reimplemented
create_deep_agent to get a place to put it. As middleware it plugs into the
harness instead of replacing it, which means:

  every entry point gets it. The HTTP service and the dashboard both call
  build_agent(), so neither can accidentally skip the gate. Two doors with
  different protections was a real defect before this.

  it composes with the rest. Summarisation, skills, sub-agents and the filesystem
  keep working, rather than being things a custom loop would have to re-add.

WHERE IT RUNS: `after_agent`
The gate needs a FINISHED answer, so it runs once the agent has stopped rather
than on each model call. `after_model` fires mid-loop, including on turns whose
"answer" is actually a tool call, and judging a tool call against a citation
obligation is meaningless.

FAIL CLOSED, AND SAY SO
waku's gates fail open — a broken gate costs latency, never capability — because
they protect tokens. This one protects DELIVERY, so the direction is inverted: if
routing cannot determine which policies apply, the turn is reported as unverified
rather than quietly passed. An obligation check that cannot run must never look
like one that ran and approved.

THE MODEL IS THE ONLY ROUTER. An earlier version fell back to keyword matching
when the router failed, which mis-routed unrelated questions to a policy on stray
words like "about" AND hid the router failure behind a plausible-looking block.
There is no keyword fallback now — but a router failure is still CAUGHT and
surfaced as a degraded/unverified turn carrying the actual error, rather than
crashing. Graceful inference on failure is a deliberate future decision.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ResponseT,
)
from langchain_core.messages import AIMessage

from agent import gate
from agent.obligation_policy import ObligationPolicy, PolicySet, load_policies
from agent.skills_engine import Draft

OBLIGATIONS_DIR = os.getenv("AGENT_OBLIGATIONS_DIR") or str(
    Path(__file__).parents[2] / "obligations"
)

# A clarifying question is short by nature; a long essay containing a rhetorical
# question has not asked the user anything. Used to infer Draft.asked_user.
_ASK_MAX_CHARS = 600


@dataclass(frozen=True)
class Verdict:
    """What the gate decided, kept on state so a channel can render it.

    `unverified` (routing could not run) is separate from `nothing-to-enforce`
    (routing ran and no policy applied) on purpose. Collapsing them means a turn
    whose routing FAILED reports the same clean result as a genuinely unregulated
    turn — which is how a compliance gate stops being one.
    """

    decision: str
    reason: str
    policies: tuple[str, ...] = ()
    blocking: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    draft: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "policies": list(self.policies),
            "blocking": list(self.blocking),
            "observed": list(self.observed),
            "draft": self.draft,
        }


def load_obligation_policies(directory: str | None = None) -> PolicySet:
    """Obligation policies from disk, or an empty set when there are none.

    A missing directory is not an error — a harness with no policies is valid,
    just one with nothing to enforce. A MALFORMED policy is allowed to raise,
    because a policy whose obligations cannot be parsed must not be treated as
    absent; that would silently drop enforcement.
    """
    return load_policies(Path(directory or OBLIGATIONS_DIR))


def draft_from(text: str) -> Draft:
    """Build the structured Draft the gate judges, by inference from prose.

    THE WEAKEST LINK, AND WORTH BEING BLUNT. The gate checks fields; the model
    returns prose; something has to bridge that. So a URL mentioned in passing
    counts as a citation, and a question mark counts as having asked.

    Both inferences are biased towards refusing rather than delivering, which is
    the only safe direction here. Getting `asked_user` wrong was not hypothetical:
    hardcoding it False made `must_ask_when_missing` impossible to satisfy — the
    model did exactly what the procedure said, asked for the missing date, and was
    refused for not asking.

    The real fix is a structured response via `response_format`, which is on
    create_deep_agent and is the deepagents-native way to get fields instead of
    prose. Until that lands this is inference, and it is labelled as inference
    wherever the verdict is shown.
    """
    urls = tuple(
        token.strip(".,);:\"'")
        for token in text.split()
        if token.startswith(("http://", "https://"))
    )
    return Draft(answer=text, citations=urls, asked_user="?" in text and len(text) < _ASK_MAX_CHARS)


class ObligationState(AgentState):
    """Extra state this middleware writes.

    Declared, because LangGraph SILENTLY DROPS an update for a key the schema does
    not know. Without this the gate blocked correctly and the verdict vanished, so
    a channel had no way to show why — the reply changed and nothing explained it.
    `SkillsMiddleware` declares its own `SkillsState` the same way.
    """

    obligation_verdict: NotRequired[dict[str, Any]]


class ObligationGateMiddleware(AgentMiddleware[ObligationState, ContextT, ResponseT]):
    """Withholds an answer that does not satisfy the obligations of a live policy.

    `router` is a LangChain chat model used to decide which policies apply — pass
    the FAST model. It is the ONLY router: there is no keyword/lexical fallback.
    If the router is absent or fails, the failure is CAUGHT and the turn is
    reported as `unverified` (degraded), with the error in the reason — never
    silently replaced by a weaker matcher, and never crashing the turn. Graceful
    inference on failure is left as a future decision.
    """

    name = "ObligationGateMiddleware"
    state_schema = ObligationState

    def __init__(self, router: Any = None, policies_dir: str | None = None) -> None:
        super().__init__()
        self._router = router
        self._policies_dir = policies_dir

    # ── routing ───────────────────────────────────────────────────────────────

    def _route(
        self, message: str, policyset: PolicySet
    ) -> tuple[tuple[ObligationPolicy, ...], str, bool]:
        """Which policies apply, why, and whether the answer is trustworthy.

        THE MODEL IS THE ONLY ROUTER. There is no keyword/lexical fallback — a
        second, dumber matcher that fired on function words like "about" was
        mis-routing unrelated questions to a policy and blocking them. That is
        gone.

        But a router OUTAGE (a raised exception, or no router wired at all) is
        caught, not left to crash the turn. It is reported as a distinct degraded
        state so it never looks like a clean result:

        The third element is `degraded`: True means routing could not run, so
        NOTHING was checked — reported to the caller as `unverified`, with the
        actual error in the reason. It is deliberately separate from "no policy
        applied": a check that could not run must not read like one that ran and
        approved.
        """
        if not policyset.policies:
            return (), "no obligation policies are loaded, so there is nothing to enforce", False

        if self._router is None:
            return (
                (),
                "no router is configured, so which policies apply could not be "
                "determined and NO obligation was checked",
                True,
            )

        try:
            policies, reason = self._route_with_model(message, policyset)
            return policies, reason, False
        except Exception as exc:  # noqa: BLE001 — any router failure is degraded, reported not raised
            # Caught, logged, and surfaced as degraded — never silently replaced
            # by a weaker matcher, and never crashing the whole turn.
            print(f"obligation-gate ROUTER ERROR: {type(exc).__name__}: {exc}", flush=True)
            reason = (
                f"the obligation router failed ({type(exc).__name__}: {exc}), so "
                "which policies apply could not be determined and NO obligation "
                "was checked"
            )
            return (), reason, True

    def _route_with_model(
        self, message: str, policyset: PolicySet
    ) -> tuple[tuple[ObligationPolicy, ...], str]:
        """Ask a cheap model which policies apply, from the one-line index.

        This is what `ObligationPolicy.index_line()` exists for, and it reads the
        DOMAIN of a question rather than its surface words — which is why it
        catches "Equality Act 2010" as a legislation question that plain keyword
        matching would miss.

        The reply is not trusted: only names present in the policy set are
        accepted, so a hallucinated name is dropped rather than enabling nothing
        silently.
        """
        prompt = (
            "Which of these obligation policies apply to the user's message? A "
            "policy applies if its description covers the DOMAIN of the question "
            "being asked.\n\n"
            f"{policyset.index_block()}\n\n"
            f"User message: {message}\n\n"
            "Reply with the applicable policy names, comma separated, and nothing "
            "else. Reply with exactly NONE if none apply."
        )
        answer = self._router.invoke(prompt).text.strip()
        named = {t.strip().strip(".,`'\"").lower() for t in answer.replace("\n", ",").split(",")}
        policies = tuple(p for p in policyset.policies if p.name.lower() in named)
        if not policies:
            return (), f"router judged that no policy applies (said: {answer[:60]!r})"
        return policies, "router selected " + ", ".join(p.name for p in policies)

    # ── the hook ──────────────────────────────────────────────────────────────

    def after_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Judge the finished answer, and replace it if an obligation blocks."""
        messages = state.get("messages") or []
        if not messages:
            return None

        final = messages[-1]
        if not isinstance(final, AIMessage):
            return None

        answer = (final.text or "").strip()
        if not answer:
            return None

        first_user = next(
            (m.text for m in messages if getattr(m, "type", "") == "human"),
            "",
        )
        policyset = load_obligation_policies(self._policies_dir)
        policies, reason, degraded = self._route(first_user, policyset)
        result = gate.evaluate(draft_from(answer), policies)

        if degraded:
            # Routing could not run. Nothing was checked, and the verdict says so
            # plainly rather than passing the answer off as verified.
            verdict = Verdict(
                "unverified",
                "could not determine which policies apply, so NO obligation was "
                f"checked on this answer — {reason}",
                draft=answer,
            )
        elif not policies:
            verdict = Verdict("nothing-to-enforce", reason, draft=answer)
        elif result.passed:
            verdict = Verdict(
                "pass",
                f"{len(policies)} policy(ies) checked, no blocking violation",
                tuple(p.name for p in policies),
                observed=tuple(str(v) for v in result.observed),
                draft=answer,
            )
        else:
            verdict = Verdict(
                "block",
                result.reason(),
                tuple(p.name for p in policies),
                tuple(str(v) for v in result.blocking),
                tuple(str(v) for v in result.observed),
                answer,
            )

        update: dict[str, Any] = {"obligation_verdict": verdict.as_dict()}
        if verdict.decision == "block":
            # The withheld text stays in the verdict, never in the message. A
            # refusal nobody can inspect is unauditable, but the draft must not be
            # what the caller reads — and it must not re-enter the thread as
            # history the model can build on, which would undo the refusal a turn
            # later.
            update["messages"] = [
                AIMessage(content=_refusal(result), id=final.id),
            ]
        return update


def _refusal(result: gate.GateResult) -> str:
    """What the user sees when the gate blocks.

    Names the obligation that failed. A bare "I can't help with that" trains
    people to rephrase at random; naming it is both more useful and auditable.
    """
    lines = [
        "**Withheld by the obligation gate.** The model produced an answer, but it "
        "did not satisfy the obligations of the policy that governs this domain, "
        "so it was not delivered.",
        "",
    ]
    lines += [f"- {v}" for v in result.blocking]
    return "\n".join(lines)
