---
title: "Property 10: No raw PII crosses the provider boundary"
type: property
tags: [property, pii]
aliases: ["Property 10"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 10: No raw PII crosses the provider boundary

Part of [[correctness-properties|Correctness Properties]].

For all payloads sent to a model provider: no raw value stored in the PII vault appears in the payload, in any encoding.
