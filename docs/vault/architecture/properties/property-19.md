---
title: "Property 19: *(removed)*"
type: property
tags: [property]
aliases: ["Property 19"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 19: *(removed)*

Part of [[correctness-properties|Correctness Properties]].

The previous Property 19 asserted explicit schema-version compatibility for the YAML config loader. **That loader no longer exists** ([[ADR-015]]): there is no config schema to version, no migrations to run, and no document interpreted under assumed semantics. The property is removed rather than reassigned, and the number is retired to keep the remaining numbering stable.
