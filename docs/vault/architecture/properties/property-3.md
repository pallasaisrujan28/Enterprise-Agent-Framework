---
title: "Property 3: Default deny and deny precedence"
type: property
tags: [property]
aliases: ["Property 3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 3: Default deny and deny precedence

Part of [[correctness-properties|Correctness Properties]].

For all policy bundles `b` and all tool names `t`: if no grant in `b` matches `t`, the decision is `Deny`; and if any matching grant has `effect = deny`, the decision is `Deny` regardless of how many allows match or in what order rules appear. *(property-based: arbitrary grant sets and orderings)*
