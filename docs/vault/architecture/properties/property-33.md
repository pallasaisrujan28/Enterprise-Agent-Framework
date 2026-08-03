---
title: "Property 33: Nothing unredacted or cross-tenant reaches managed memory"
type: property
tags: [property, multi-tenancy]
aliases: ["Property 33"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:35:49+00:00
---

# Property 33: Nothing unredacted or cross-tenant reaches managed memory

Part of [[correctness-properties|Correctness Properties]].

For all events `e` written to AgentCore Memory ([[ADR-020]]): `e` has passed PII redaction **before** the write, and `e` lands in a memory resource scoped to `e.tenant_id`. Three clauses:

1. **Redaction precedes the write, never follows it.** Managed memory both persists the event and feeds it to an extraction model, so an unredacted write violates [[Property 10]] (no raw PII across the provider boundary) and [[Property 11]] (PII tokenized in every persisted surface) simultaneously. There is no post-hoc repair: the extraction has already happened.
2. **Tenant scoping is structural, not string-built.** Namespace templates support `{actorId}`, `{sessionId}`, and `{memoryStrategyId}` — there is **no tenant placeholder** — so containment comes from a **per-tenant memory resource**, not from encoding a tenant prefix into `actorId`. A test asserts that no memory resource is reachable with credentials scoped to a different tenant.
3. **Only the adopted strategy is enabled.** `SUMMARIZATION` and `SEMANTIC` are configured off. Enabling `SUMMARIZATION` silently reintroduces unrecoverable summarization against [[P4]], and the symptom — context that cannot be restored — appears far from the config that caused it.

Clause 2 is the one that requires a deliberate architectural choice rather than a check: with the tenant absent from the namespace grammar, isolation has to be bought at the resource boundary, and a single malformed `actorId` would otherwise cross-contaminate tenants silently. *(property-based: arbitrary event payloads containing PII patterns × arbitrary tenant/actor combinations)*
