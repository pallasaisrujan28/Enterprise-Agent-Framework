---
title: "Property 18: A skill can never widen an agent's access"
type: property
tags: [property, skills, authz]
aliases: ["Property 18"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 18: A skill can never widen an agent's access

Part of [[correctness-properties|Correctness Properties]].

*(Retargeted in this revision from configs to skills, which are now the capability-configuration surface — [[ADR-002b]], [[P12]].)*

For all skills `s` attached to agent `a` under tenant bundle `b`: every tool in `s.manifest.required_tools` exists in the pinned `ToolCatalogVersion`, and every scope in `s.manifest.required_scopes` is a subset of `a`'s effective grants under `b`. A skill can narrow or use what the agent already has; it can never grant a tool or scope the tenant policy denies, and a skill that tries fails validation before it is ever loaded. *(property-based: arbitrary skill manifests against arbitrary grant sets)*
