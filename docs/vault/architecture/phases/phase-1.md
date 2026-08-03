---
title: "Phase 1 — Thin vertical slice (the whole path, minimally)"
type: phase
tags: [phase]
aliases: ["Phase 1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T00:04:06+00:00
---

# Phase 1 — Thin vertical slice (the whole path, minimally)

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Runs locally on Compose (minimal profile).**

**Ship:** one hard-coded tenant; one executor loop with fewer than ten tools; one tool pool with a **pinned tool catalog version**; the stable-prefix assembler with `prefix_hash` emission; **the skill mechanism at all three levels** — registry, Level-1 metadata index in the stable prefix, on-demand Level-2 body loading, **Level-3 bundled resources including executable scripts that run without entering context**, manifest validation, and the mandatory skill eval gate, with two or three real skills shipped through it; **the transcript tree (`id` + `parent_id`) and compaction-as-an-appended-entry**, with the tool-call/result pairing rule enforced; **the three freshness timestamps** with system events barred from extending `last_interaction_at`; **the fork size cap on inherited context**; **scoped retry with failure-loop detection and `distill_failure`**; restorable offload T0 → T1 with a `file_read`-by-reference tool; the session manifest in Redis; trajectory capture to T2; LangSmith tracing; the **deterministic structured-entity PII gate** (regex + Luhn for card/SSN/email/phone) with the no-raw-PII-egress test as a hard gate; and **CI grown per the gate-growth table** ([[§4.4]]) — types, unit, contract, skill-validation, skill-eval, compaction-pairing, fork-cap, and freshness jobs added on top of the Phase-0 three, because this is the phase in which the components those gates protect come into existence.

**Why skills are in Phase 1 rather than later.** They are the primary extensibility mechanism ([[P15]]) and cheap to build — a registry, an index, a loader, and a validator. Building them first means every subsequent phase adds capability as skills instead of as nodes, so the topology never accumulates the debt [[§6]] exists to pay down. Deferring skills means paying for node sprawl and then migrating away from it. All **three levels** land together because they are one mechanism, not three features — and the third level (executable scripts at zero context cost) is the cheapest capability in the document, so shipping the first two without it means authoring skills against the wrong economics from day one ([[ADR-002b]]).

**Why the transcript tree and compaction-as-entry are in Phase 1 even though compaction is [[Phase 4]].** They are **data-model decisions**, and the data model is what every reader, replayer, forker, and eval consumer is written against. Retrofitting `parent_id` onto a flat list, or converting in-place compaction into appended entries, means touching all of them at once — the definition of an expensive retrofit. The full compaction *tiers* wait for [[Phase 4]]; the *shape* they compact does not.

**Why tool-call/result pairing and the fork size cap are in Phase 1.** Both are **correctness bugs if absent**, not optimizations, and both are cheap. A boundary that splits a call from its result leaves the model reasoning about a question it never got an answer to; an oversized inherited context repeals [[P5]] while a flag says everything is fine. Each is a small deterministic gate, and each failure is silent without one.

**Why the freshness timestamps are in Phase 1.** Data model again. Adding `last_interaction_at` later means auditing every existing write path to decide which ones were "real interaction" — an archaeology exercise. Deciding it once, at the point each writer is authored, costs nothing.

**Why scoped retry is in Phase 1.** It is a context-shaping decision, and retrofitting it means unwinding a codebase that assumed failures accumulate forward. It is cheap now and expensive later.

**Deliberately absent:** multi-tenancy, OPA, GraphRAG, HITL, planner/executor split, sub-graph registry, compaction beyond offload (the *entry and tree shape* land here; the trimming, summarization, memory-flush, silent-turn, and mid-turn-precheck machinery is [[Phase 4]]), any optimization, **the self-hosted PII stack** ([[Phase 6]] — see the precondition above).

**Exit criterion:** a real request completes end to end **on the local stack, against the real third-party APIs of the anchor use case** (Stripe Billing Entitlements and a real issue tracker) with account records we own, and the local dashboard shows KV-cache hit rate, tokens and cost per task, skill index size, and one `TrajectoryRecord` per request. At least one skill is attached to an agent **by pointer promotion with no redeploy**, and it passed its own eval cases in CI. The structured-PII gate passes as a deterministic test. A failure loop is detected and broken in a test. If cache hit rate is not measurable at the end of Phase 1, Phase 1 is not done — everything downstream is priced off it.
