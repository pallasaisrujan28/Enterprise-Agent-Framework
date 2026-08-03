---
title: "Property 30: Inherited context is size-capped regardless of the complexity flag"
type: property
tags: [property, context-engineering]
aliases: ["Property 30"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 30: Inherited context is size-capped regardless of the complexity flag

Part of [[correctness-properties|Correctness Properties]].

For all sub-agent handoffs `h` where `h.parent_branch_tokens > PARENT_BRANCH_TOKEN_CAP`: `h.context_mode == ISOLATED`, for **every** value of the plan's `complexity` and with **no configuration override available**. The cap is evaluated at dispatch, before any model call, alongside the depth check ([[Property 24]]) — `depth` bounds how deep the tree goes, the cap bounds how heavy any single edge in it is.

Two fork constraints hold with it: a fork is **refused** while the parent has an active run, and a forked child starts with **fresh token counters** rather than inheriting the parent's spent ledger.

The cap does not trust the complexity flag because a flag is set by a planner and a planner can be wrong about a branch that has grown to a quarter-million tokens. It is deliberately automatic and deliberately not configurable — a knob here gets turned off under deadline pressure and the resulting failure is diffuse and expensive ([[§2.12]].1). *(property-based: arbitrary parent branch sizes × arbitrary complexity flags)*
