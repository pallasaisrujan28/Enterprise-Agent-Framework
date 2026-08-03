---
title: "Property 1: Tenant partition containment"
type: property
tags: [property, multi-tenancy]
aliases: ["Property 1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 1: Tenant partition containment

Part of [[correctness-properties|Correctness Properties]].

For all requests `r` and all storage reads or writes `s` performed while handling `r`: `s.partition == r.tenant_context.data_partition`. No access escapes the tenant partition, and `tenant_id` originates only from a verified token claim. *(property-based: arbitrary request/tenant pairs)*
