---
title: "ADR-006b: Observation variation is allowed only after the cache breakpoint"
type: adr
tags: [adr, kv-cache]
aliases: ["ADR-006b"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# ADR-006b: Observation variation is allowed only after the cache breakpoint

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** On long runs of structurally identical observations, apply mild serialization variation (field order in the *rendered* view, phrasing of wrappers, alternate compact templates) — but **only** in the volatile tail, never in the stable prefix.

**Context.** Two of our own principles pull against each other. [[P2]] wants byte-identical structure for cache reuse; the Manus lessons note that when a model sees a long run of near-identical observations it over-generalizes the pattern and starts producing rote actions.

**Rationale.** Making the tension explicit and resolving it by *region* keeps both properties: the prefix stays byte-stable (cache intact), while the appended tail — which is uncached anyway — can vary enough to break rote pattern-matching.

**Consequences.** (+) Reduces drift on long horizons without a cache cost. (−) Variation must be bounded and deterministic per session seed, otherwise trajectories become hard to diff in evaluation.

**Alternatives considered.** Vary everything — rejected (destroys cache). Vary nothing — rejected (accepts known drift behaviour).
