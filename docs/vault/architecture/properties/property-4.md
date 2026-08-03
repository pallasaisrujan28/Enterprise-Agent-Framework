---
title: "Property 4: Stable-prefix invariance within a session"
type: property
tags: [property, kv-cache, session-state]
aliases: ["Property 4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 4: Stable-prefix invariance within a session

Part of [[correctness-properties|Correctness Properties]].

For all consecutive turns `t_i, t_{i+1}` in one session under one artifact version: `prefix_hash(t_i) == prefix_hash(t_{i+1})`. *(property-based: arbitrary turn sequences and tool-result sizes)*
