"""The obligation library — the parameterised checks a rule author can use.

This library is the load-bearing bet of the whole design: a domain expert must
be able to make a rule BINDING without writing code. They pick a kind from this
registry and fill in parameters in the rule's frontmatter.

If this library cannot express ~80% of real enterprise rules, the design
collapses back to "rules as prompt text and hope", so the set is kept small and
deliberately generic. Adding a kind here is a platform decision, not a routine
change — every kind is a promise we have to keep working.

Each checker returns None when the obligation holds, or a human-readable reason
when it does not. Checkers are pure functions of the draft: no model call, no
network, no judgement. That is what makes them testable and what makes a
violation something you can argue with.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from agent.rules.model import Draft, Obligation

# A checker inspects a draft and returns None (holds) or a reason (violated).
Checker = Callable[[Draft, Obligation], str | None]

_REGISTRY: dict[str, Checker] = {}


def register(kind: str) -> Callable[[Checker], Checker]:
    def decorate(fn: Checker) -> Checker:
        if kind in _REGISTRY:
            raise ValueError(f"obligation kind '{kind}' is already registered")
        _REGISTRY[kind] = fn
        return fn

    return decorate


def known_kinds() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def check(draft: Draft, obligation: Obligation) -> str | None:
    checker = _REGISTRY.get(obligation.kind)
    if checker is None:
        # Fail closed. An unknown obligation kind means the rule file expects a
        # guarantee this build cannot provide, and silently ignoring it would
        # hand the tenant a control that does nothing.
        return f"unknown obligation kind '{obligation.kind}'"
    return checker(draft, obligation)


# --------------------------------------------------------------------------
# The kinds
# --------------------------------------------------------------------------

# A version-pinned legislation.gov.uk citation carries a date segment, e.g.
# /ukpga/2006/46/section/172/2021-03-01. Without it the citation names a
# provision but not WHICH VERSION of it, which for statute is the difference
# between right and confidently wrong.
_DATE_SEGMENT = re.compile(r"/\d{4}-\d{2}-\d{2}(?:/|$)")


@register("must_cite")
def _must_cite(draft: Draft, ob: Obligation) -> str | None:
    """The answer must cite at least one source, optionally version-pinned.

    params:
      contains       substring every citation must contain (e.g. a host)
      version_pinned bool — each citation must identify a point in time
      min_count      int, default 1
    """
    min_count = int(ob.params.get("min_count", 1))
    contains = ob.params.get("contains")
    pinned = bool(ob.params.get("version_pinned", False))

    citations = [c for c in draft.citations if c.strip()]
    if contains:
        citations = [c for c in citations if contains in c]

    if len(citations) < min_count:
        want = f"{min_count} citation(s)"
        if contains:
            want += f" containing '{contains}'"
        return f"answer cites {len(citations)} of the required {want}"

    if pinned:
        unpinned = [c for c in citations if not _DATE_SEGMENT.search(c)]
        if unpinned:
            return f"citation(s) are not version-pinned: {', '.join(unpinned)}"
    return None


@register("must_ask_when_missing")
def _must_ask_when_missing(draft: Draft, ob: Obligation) -> str | None:
    """If a required input was never established, the turn must ask, not guess.

    params:
      fields  list of fact keys that must be present

    This is the obligation that turns "the model should ask if it is unsure"
    from a hope into a guarantee. Model self-reported uncertainty is poorly
    calibrated; a missing field is a fact.
    """
    fields = ob.params.get("fields") or []
    missing = [f for f in fields if draft.fact(f) in (None, "", [])]
    if not missing:
        return None
    if draft.asked_user:
        return None
    return f"answered without establishing {', '.join(missing)} and without asking"


@register("must_disclose")
def _must_disclose(draft: Draft, ob: Obligation) -> str | None:
    """When a condition holds, the answer must carry a named disclosure.

    params:
      when      fact key that triggers the requirement
      disclose  the disclosure label that must be present

    Checked against structured disclosures rather than the prose, so a rule
    cannot be satisfied by wording that merely resembles a disclosure.
    """
    when = ob.params.get("when")
    label = ob.params.get("disclose") or when
    if not when:
        return "must_disclose requires a 'when' fact key"
    if not draft.fact(when):
        return None
    if label in draft.disclosures:
        return None
    return f"'{when}' holds but the answer does not disclose '{label}'"


@register("requires_approval_when")
def _requires_approval_when(draft: Draft, ob: Obligation) -> str | None:
    """A named tool may only have run if a human approved it this turn.

    params:
      tool  the tool name that requires approval
    """
    tool = ob.params.get("tool")
    if not tool:
        return "requires_approval_when requires a 'tool'"
    if tool not in draft.tools_called:
        return None
    if tool in draft.approvals:
        return None
    return f"'{tool}' was called without a recorded approval"


@register("must_not_call")
def _must_not_call(draft: Draft, ob: Obligation) -> str | None:
    """A named tool must not be used under this rule at all.

    params:
      tools  list of forbidden tool names
    """
    forbidden = set(ob.params.get("tools") or [])
    used = forbidden.intersection(draft.tools_called)
    if not used:
        return None
    return f"called forbidden tool(s): {', '.join(sorted(used))}"
