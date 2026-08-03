---
title: "Property 5: Tool definitions constant, only masks vary"
type: property
tags: [property, tools]
aliases: ["Property 5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 5: Tool definitions constant, only masks vary

Part of [[correctness-properties|Correctness Properties]].

For all turns in a session: the tool definition set is identical in content and in order. Any per-state restriction is expressed as a mask, never as a definition change.
