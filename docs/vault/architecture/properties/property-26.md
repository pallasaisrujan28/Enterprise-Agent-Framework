---
title: "Property 26: Tool sets and skill indexes are pinned per session and versioned across sessions"
type: property
tags: [property, skills, tools, session-state]
aliases: ["Property 26"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 26: Tool sets and skill indexes are pinned per session and versioned across sessions

Part of [[correctness-properties|Correctness Properties]].

For all sessions `s`: `catalog_version` and `skill_index_version` are fixed at session start and identical on every turn of `s`; a new catalog or index version affects only sessions started after its promotion, and an in-flight session completes on the version it pinned. Every `TrajectoryRecord` carries both versions, so a trajectory can be replayed against the exact tool set and skill index that governed it. This is what makes [[ADR-005]]'s stability requirement compatible with continuous tool and skill addition ([[§3.8]]). *(property-based: arbitrary interleavings of session starts and version promotions)*
