---
title: "Property 16: Gated promotion and pointer rollback"
type: property
tags: [property]
aliases: ["Property 16"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 16: Gated promotion and pointer rollback

Part of [[correctness-properties|Correctness Properties]].

For all artifact versions reaching `prod`: an eval run exists on a held-out dataset meeting or exceeding the promotion threshold, a canary window completed without degradation, and rollback to the previous `prod` version is achievable by pointer change alone with no rebuild.
