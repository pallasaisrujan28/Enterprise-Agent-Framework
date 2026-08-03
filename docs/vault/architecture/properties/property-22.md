---
title: "Property 22: Identical failures terminate"
type: property
tags: [property, failure-handling]
aliases: ["Property 22"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 22: Identical failures terminate

Part of [[correctness-properties|Correctness Properties]].

For all executor attempts and all failure sequences: if the last `threshold` failures (default 3) are identical in tool name, canonicalized arguments, and error class, the step-retry scope terminates and control escalates to a scope-2 re-attempt. No agent issues the same failing call an unbounded number of times, and the loop is broken by the detector rather than by a budget cap. *(property-based: arbitrary failure sequences with arbitrary repeat patterns)*
