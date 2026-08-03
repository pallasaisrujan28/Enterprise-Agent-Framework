---
title: "ADR-017: Phased delivery — one thin vertical slice, then widen"
type: adr
tags: [adr]
aliases: ["ADR-017"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-017: Phased delivery — one thin vertical slice, then widen

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Build in **[[Phase 0]] plus six phases** ([[§8]]). **[[Phase 0]]** settles the service selection, the minimal Compose profile, the three CI gates, and the portability seams ([[ADR-019]]). [[Phase 1]] is then a **thin vertical slice**: one tenant, one agent loop, one tool pool, stable-prefix assembly, restorable offload, trajectory capture, and a deterministic PII gate — end to end **on the local stack**. Nothing in later phases starts until the slice below it is running with its metrics visible. [[Phase 6]] is a final **enhancements** phase carrying the self-hosted PII stack ([[ADR-009]]), which gates which tenants can be onboarded before it lands.

**Context.** The requirement was explicit: phase-wise development, not everything at once. This design describes a large system, and a large system built breadth-first produces seven half-finished layers and no working request path.

**Rationale.** A thin vertical slice forces every layer boundary to be real on day one — the contracts in [[§3.1]] get exercised rather than reviewed. It also front-loads the cheap high-return work (prefix caching, offload, trajectory capture) that pays off at any scale ([[§7.1]]) and defers the expensive optional work (GraphRAG indexing, weight training, dedicated tenant clusters) until there is data to justify it. Every capability in this document carries a phase assignment so scope creep is visible as a phase violation rather than an argument.

**Consequences.** (+) A working, observable path early; each phase is independently valuable and reversible. (+) The eval harness exists before the risky behavioural refactor ([[§6.3]] step 5). (+) With [[ADR-019]], no phase waits on infrastructure — the slice runs on one machine. (−) [[Phase 1]] deliberately ships without multi-tenancy, GraphRAG, HITL, or optimization, which must be communicated so it is not mistaken for the finished platform. (−) Some [[Phase 1]] code is knowingly provisional; the contracts are what carry forward, not every implementation behind them. (−) **Deferring the self-hosted PII stack to [[Phase 6]] is a binding constraint on tenant onboarding, not a soft preference** — Phases 1–5 may not serve regulated data ([[ADR-009]], [[§7.10]]).

**Alternatives considered.** Layer-by-layer horizontal build (all of the gateway, then all of the orchestrator) — rejected, nothing works until the last layer lands and integration risk is deferred to the end. Big-bang cutover from the existing mega-graph — rejected, no baseline, no rollback, and behavioural regressions arrive all at once.
