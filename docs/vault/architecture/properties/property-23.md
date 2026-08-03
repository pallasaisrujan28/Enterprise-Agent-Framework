---
title: "Property 23: A re-attempt context contains a lesson, not a trajectory"
type: property
tags: [property, context-engineering]
aliases: ["Property 23"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 23: A re-attempt context contains a lesson, not a trajectory

Part of [[correctness-properties|Correctness Properties]].

For all scope-2 task re-attempts with `FailureLesson` `l`: the fresh executor's context contains `l.lesson_text` and `l.do_not_repeat` and **no** message, tool result, or error text originating from the failed attempt; and `l.failed_trajectory_ref` resolves to the complete failed trajectory in the archive tier. Both halves are required — a re-attempt that inherits the failed trajectory violates this, and so does a lesson whose full trajectory is unrecoverable. *(property-based: arbitrary failed trajectories of arbitrary length)*
