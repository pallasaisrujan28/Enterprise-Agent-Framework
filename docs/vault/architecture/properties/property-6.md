---
title: "Property 6: History is append-only"
type: property
tags: [property]
aliases: ["Property 6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 6: History is append-only

Part of [[correctness-properties|Correctness Properties]].

For all turns: no prior message in the history is edited, reordered, or deleted in place. Compaction replaces raw payloads with references but preserves message positions and user/assistant text verbatim. *(property-based: arbitrary interleavings of appends and compactions)*
