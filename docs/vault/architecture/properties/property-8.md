---
title: "Property 8: Compaction preserves the cached prefix"
type: property
tags: [property, kv-cache, compaction]
aliases: ["Property 8"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 8: Compaction preserves the cached prefix

Part of [[correctness-properties|Correctness Properties]].

For all compaction operations: the stable prefix is byte-identical before and after. Compaction never rewrites cached content.
