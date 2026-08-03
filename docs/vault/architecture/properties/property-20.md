---
title: "Property 20: Every referenced artifact resides in a resolvable tier"
type: property
tags: [property]
aliases: ["Property 20"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 20: Every referenced artifact resides in a resolvable tier

Part of [[correctness-properties|Correctness Properties]].

For all `ManifestEntry` values `e` reachable from a live session: `e.restorable == true` and `get_artifact(e.reference)` resolves in the tier named by `e.tier`. Nothing referenced in context exists only in ephemeral T0. *(property-based: arbitrary offload and promotion sequences)*
