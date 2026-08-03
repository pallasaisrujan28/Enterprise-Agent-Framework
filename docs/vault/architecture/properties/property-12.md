---
title: "Property 12: Failures are durably preserved, and context inclusion is scoped"
type: property
tags: [property, context-engineering, failure-handling]
aliases: ["Property 12"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 12: Failures are durably preserved, and context inclusion is scoped

Part of [[correctness-properties|Correctness Properties]].

Two clauses, and both must hold ([[P6]], [[§2.13]]):

1. **Durability is total.** For all failed tool or model calls at any retry scope: a complete failure record exists in the durable trajectory (T2), tokenized but never summarized away and never silently swallowed.
2. **Context inclusion is scoped.** For a scope-1 same-step retry the error appears in context **verbatim**; for a scope-2 task re-attempt the new context contains a `FailureLesson` and **no** content from the failed trajectory; for a scope-3 re-plan the planner receives a failure **summary** and never the raw trajectory.

Clause 1 without clause 2 is the flaw this revision corrects — accumulating wreckage is not the same thing as preserving it. *(property-based: arbitrary failure sequences across scopes)*
