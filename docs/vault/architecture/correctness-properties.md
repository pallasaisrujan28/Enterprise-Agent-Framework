---
title: "Correctness Properties"
type: hub
tags: [hub]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T13:52:07+00:00
---

# Correctness Properties

Properties stated as universals. Each maps to a deterministic test in [[§5.4]], and the ones marked *(property-based)* are cheap to express in Hypothesis over generated inputs.

> **Traceability note.** This is a design-first spec, so requirements have not been derived yet. Each property below will gain an explicit `Validates: Requirements X.Y` reference during the requirements phase, when acceptance criteria are numbered. The properties are written first deliberately — they are the invariants the requirements must encode, not the other way around.

## In this section

- [[property-1|Property 1: Tenant partition containment]]
- [[property-2|Property 2: Authorization independent of masking]]
- [[property-3|Property 3: Default deny and deny precedence]]
- [[property-4|Property 4: Stable-prefix invariance within a session]]
- [[property-5|Property 5: Tool definitions constant, only masks vary]]
- [[property-6|Property 6: History is append-only]]
- [[property-7|Property 7: Nothing is dropped without a path back]]
- [[property-8|Property 8: Compaction preserves the cached prefix]]
- [[property-9|Property 9: Offload round-trip fidelity]]
- [[property-10|Property 10: No raw PII crosses the provider boundary]]
- [[property-11|Property 11: PII is tokenized in every persisted surface]]
- [[property-12|Property 12: Failures are durably preserved, and context inclusion is scoped]]
- [[property-13|Property 13: Exactly one terminal trajectory per request]]
- [[property-14|Property 14: Failure containment across pools]]
- [[property-15|Property 15: Session write serialization]]
- [[property-16|Property 16: Gated promotion and pointer rollback]]
- [[property-17|Property 17: Ingestion config validation is narrow, total, and fail-closed]]
- [[property-18|Property 18: A skill can never widen an agent's access]]
- [[property-19|Property 19: *(removed)*]]
- [[property-20|Property 20: Every referenced artifact resides in a resolvable tier]]
- [[property-21|Property 21: Session resume from manifest]]
- [[property-22|Property 22: Identical failures terminate]]
- [[property-23|Property 23: A re-attempt context contains a lesson, not a trajectory]]
- [[property-24|Property 24: Sub-graph invocation depth is bounded and enforced before any model call]]
- [[property-25|Property 25: The skill index is bounded and each of the three skill levels stays in its own region]]
- [[property-26|Property 26: Tool sets and skill indexes are pinned per session and versioned across sessions]]
- [[property-27|Property 27: No compaction boundary separates a tool call from its result]]
- [[property-28|Property 28: A memory flush completes before the compaction entry is written]]
- [[property-29|Property 29: A silent turn delivers nothing, on either path]]
- [[property-30|Property 30: Inherited context is size-capped regardless of the complexity flag]]
- [[property-31|Property 31: System-generated events do not extend session freshness]]
- [[property-32|Property 32: A tool call carries both identities, and access is their intersection]]
- [[property-33|Property 33: Nothing unredacted or cross-tenant reaches managed memory]]
- [[property-34|Property 34: Every legislative answer is version-pinned, or refused]]
- [[property-35|Property 35: An effects publication replaces the effect set; it never merges into it]]
- [[property-36|Property 36: A missing edge never reads as an absent amendment]]
