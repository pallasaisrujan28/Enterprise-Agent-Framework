"""The obligation gate — the last thing between a draft answer and the user.

This module is why the platform exists. Everything else — the loop, the tools,
the retrieval — is commodity work that any competent team can build. The gate is
the part that lets a customer say "our agent follows our procedures" and be able
to prove it rather than assert it.

Two properties matter more than anything else here:

  It runs OUTSIDE the model. The model is not asked whether it complied. It
  cannot reason its way to a pass, and it cannot be persuaded by a user to skip
  a check, because it is not the thing doing the checking.

  It fails CLOSED. An error inside the gate blocks delivery. That is the
  opposite of how presentation concerns should behave — a streaming glitch
  should degrade gracefully — and it is deliberate. A control that fails open
  is a control that is absent exactly when something has gone wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent.skills_engine import obligations as ob_lib
from agent.skills_engine.model import Draft, Obligation, Violation


class Governed(Protocol):
    """Anything the gate can enforce: it has a name and a list of obligations.

    Both an ObligationPolicy and a Skill satisfy this structurally, so the gate
    does not need to know which it was handed — which is the whole point of
    splitting policy from capability. In practice the middleware passes policies.

    Declared as read-only properties rather than bare attributes: a plain
    `obligations: tuple[...]` on a Protocol is invariant and settable, which a
    frozen dataclass field does not satisfy. Read-only properties are what a
    frozen dataclass actually provides.
    """

    @property
    def name(self) -> str: ...

    @property
    def obligations(self) -> tuple[Obligation, ...]: ...


@dataclass(frozen=True)
class GateResult:
    """The verdict on one draft."""

    violations: tuple[Violation, ...]

    @property
    def blocking(self) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.blocking)

    @property
    def observed(self) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if not v.blocking)

    @property
    def passed(self) -> bool:
        """True when nothing blocks delivery.

        Note that observe-mode violations do NOT block. They are recorded so an
        obligation can be tuned against real traffic before it is promoted to
        enforcing — the alternative is a gate that blocks good answers on its
        first day and gets disabled by the first person it inconveniences.
        """
        return not self.blocking

    def reason(self) -> str:
        """Why delivery was refused, for the retry prompt and the audit record."""
        return "; ".join(f"{v.source}/{v.obligation}: {v.detail}" for v in self.blocking)


def evaluate(draft: Draft, triggered: tuple[Governed, ...]) -> GateResult:
    """Check a draft against the obligations of every policy that applies.

    Only applicable policies are checked — a policy whose domain the question is
    not in has no business judging the answer. Obligations are the enforcement
    half of a specific domain contract, not free-floating platform policy;
    platform policy (PII, jailbreak, tenant isolation) is enforced elsewhere and
    always.

    Duck-typed over `Governed`: it works on an ObligationPolicy or a Skill or
    anything else carrying `.name` and `.obligations`, so the source of the
    obligations can change without touching the gate.
    """
    violations: list[Violation] = []

    for governed in triggered:
        for obligation in governed.obligations:
            try:
                detail = ob_lib.check(draft, obligation)
            except Exception as exc:  # noqa: BLE001 — see the fail-closed note above
                detail = f"obligation raised {type(exc).__name__}: {exc}"
            if detail is None:
                continue
            violations.append(
                Violation(
                    source=governed.name,
                    obligation=obligation.kind,
                    detail=detail,
                    blocking=obligation.blocking,
                )
            )

    return GateResult(violations=tuple(violations))
