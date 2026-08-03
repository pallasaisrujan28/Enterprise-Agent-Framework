---
title: "Property 13: Exactly one terminal trajectory per request"
type: property
tags: [property]
aliases: ["Property 13"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 13: Exactly one terminal trajectory per request

Part of [[correctness-properties|Correctness Properties]].

For all requests: exactly one `TrajectoryRecord` exists with a terminal outcome in `{DELIVERED, ESCALATED, BLOCKED, FAILED}`, and it carries the token ledger, cache hit rate, guardrail events, and artifact versions used.
