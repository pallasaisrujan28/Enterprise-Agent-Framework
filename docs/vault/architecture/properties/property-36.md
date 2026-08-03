---
title: "Property 36: A missing edge never reads as an absent amendment"
type: property
tags: [property]
aliases: ["Property 36"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T13:52:07+00:00
---

# Property 36: A missing edge never reads as an absent amendment

Part of [[correctness-properties|Correctness Properties]].

For all traversals `t` over the lazily-populated legislative graph: `t` distinguishes **"no effect exists"** from **"no effect has been fetched"**, and any answer derived from an incomplete traversal discloses the incompleteness. Four clauses:

1. **Three-state provenance.** Every item is `never_fetched`, `fetched_with_effects`, or `fetched_and_confirmed_empty`, each with a timestamp. An empty result set is only reportable as "not amended" in the third state.
2. **Truncation is surfaced, not swallowed.** Where the depth limit, the shared upstream rate budget, or a fetch failure stops expansion, the answer states that the amendment chain was not fully traversed. A truncated traversal presented as complete is a defect, not a degradation.
3. **Staleness is bounded.** An item whose freshness has not been confirmed within the configured window is refreshed before it can support an answer, or the answer discloses the staleness. A missed feed poll must never silently become outdated law.
4. **Rate-budget exhaustion degrades honestly.** Because the upstream limit is a single shared allowance across all tenants, one tenant's traversal can exhaust it. The correct behaviour is a disclosed partial answer or a deferral — never a confident answer over whatever happened to be cached.

Why this is separate from [[Property 34]]: that property governs *the version* an answer is based on, while this one governs *whether the answer knows what it does not know*. Lazy ingestion is the right strategy for a shared, rate-limited upstream, and its characteristic failure is a silent one — a graph with a missing edge answers "no repeals found" in exactly the same words as a complete graph. In this domain, that sentence carries legal weight it has not earned. *(property-based: arbitrary query orders against a partially-populated graph, arbitrary depth limits, arbitrary rate-budget exhaustion points, and arbitrary effect retractions between fetches)*
