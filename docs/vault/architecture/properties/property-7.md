---
title: "Property 7: Nothing is dropped without a path back"
type: property
tags: [property]
aliases: ["Property 7"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 7: Nothing is dropped without a path back

Part of [[correctness-properties|Correctness Properties]].

For all compaction operations: every element removed from context is retrievable through a `Reference` the agent holds a tool to resolve. Lossy removal with no restore path is a defect.
