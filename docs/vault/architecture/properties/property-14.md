---
title: "Property 14: Failure containment across pools"
type: property
tags: [property, failure-handling]
aliases: ["Property 14"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 14: Failure containment across pools

Part of [[correctness-properties|Correctness Properties]].

For all pool pairs `(p, q)` with `p != q`: an open circuit breaker on `p` does not prevent calls to a healthy `q`. There is no global breaker.
