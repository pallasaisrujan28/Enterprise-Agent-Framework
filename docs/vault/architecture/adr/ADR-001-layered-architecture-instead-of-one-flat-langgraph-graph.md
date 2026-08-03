---
title: "ADR-001: Layered architecture instead of one flat LangGraph graph"
type: adr
tags: [adr, graph]
aliases: ["ADR-001"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-001: Layered architecture instead of one flat LangGraph graph

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Adopt a three-tier topology — **Gateway → Orchestrator → isolated Tool Pools** — and use LangGraph only *inside* individual sub-agents. Do not model the whole platform as a single graph where every agent is a node and a central router edges to all classifications.

**Context.** The current system uses one LangGraph graph: each node is an agent, and a central orchestrator routes everything. As the number of agents and task classifications grows, the router prompt, the edge set, and the shared context grow super-linearly. Routing accuracy degrades, prompts bloat, and the cache-friendly prefix keeps changing.

**Rationale.** Layering decouples the two scaling axes. Tenant scale is handled at the Gateway/Orchestrator tier (stateless, horizontally replicated). Capability scale is handled by adding tool pools and sub-agents behind stable interfaces. A small sub-agent graph keeps each context window clean ([[P5]]) and each prompt prefix stable ([[P2]]).

**Consequences.**
- (+) Independent scaling and deployment per layer and per tool pool.
- (+) Failures are contained within a pool (circuit breakers) instead of taking down a monolith.
- (+) Router complexity is bounded — the orchestrator routes to a small set of sub-agent *types*, not to every classification.
- (−) More moving parts, network hops, and operational surface than a single process.
- (−) Requires explicit contracts between layers (addressed in [[§3]]).

**Alternatives considered.** (a) Keep the flat graph and optimize the router prompt — rejected, does not address prefix instability or context growth. (b) One "mega-agent" with all tools — rejected, violates [[P3]] (large toolset) and [[P5]] (no isolation).
