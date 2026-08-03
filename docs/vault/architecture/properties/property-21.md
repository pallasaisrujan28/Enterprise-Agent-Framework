---
title: "Property 21: Session resume from manifest"
type: property
tags: [property, session-state]
aliases: ["Property 21"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 21: Session resume from manifest

Part of [[correctness-properties|Correctness Properties]].

For all sessions `s` and all orchestrator restarts occurring between turns of `s`: a replacement orchestrator reconstructs an equivalent agent-visible context from `SessionManifest(s)` plus T1/T2 alone, with no dependence on the prior process's memory — including the pinned `catalog_version` and `skill_index_version`, so the resumed prefix is byte-identical to the pre-restart prefix. *(property-based: arbitrary restart points in a turn sequence)*
