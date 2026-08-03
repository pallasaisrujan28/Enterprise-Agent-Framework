---
title: "Property 24: Sub-graph invocation depth is bounded and enforced before any model call"
type: property
tags: [property, graph, model-routing]
aliases: ["Property 24"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 24: Sub-graph invocation depth is bounded and enforced before any model call

Part of [[correctness-properties|Correctness Properties]].

For all sub-graph invocations with handoff depth `d`: dispatch admits the invocation only if `d + 1 <= 2`, or `d + 1 == 3` and the target sub-graph's registry entry carries a recorded `max_depth_signoff`. A rejection occurs at dispatch, **before** any model call or token spend, and depth 4 is not expressible. *(property-based: arbitrary nesting sequences)*
