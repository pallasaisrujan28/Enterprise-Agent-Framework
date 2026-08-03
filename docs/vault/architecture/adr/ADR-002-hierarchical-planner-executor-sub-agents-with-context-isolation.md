---
title: "ADR-002: Hierarchical planner/executor sub-agents with context isolation"
type: adr
tags: [adr, context-engineering]
aliases: ["ADR-002"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-002: Hierarchical planner/executor sub-agents with context isolation

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Use a **planner sub-agent** that decomposes tasks and maintains a rewritten `todo.md` recited at the context tail, and **executor sub-agents** that run isolated. For simple tasks the planner passes minimal instructions; for complex tasks it shares the trajectory + filesystem handle.

**Context.** Long tasks suffer "lost-in-the-middle"; shared context between agents causes cross-contamination and unbounded growth.

**Rationale.** Goal recitation at the tail keeps the objective salient ([[P2]] append-only). Context isolation ([[P5]]) means each executor reasons over a clean window. Minimal-vs-full handoff scales the amount of shared context to task difficulty.

**Consequences.**
- (+) Better long-horizon behavior; smaller, cache-friendly executor contexts.
- (+) Sub-agents are independently testable and model-routable ([[ADR-011]]).
- (−) Handoff contract must be explicit and validated (structured submit-results tool).

**Alternatives considered.** Single-agent long-context loop — rejected due to lost-in-the-middle and cost. Fully independent agents with no planner — rejected, loses global task coherence.
