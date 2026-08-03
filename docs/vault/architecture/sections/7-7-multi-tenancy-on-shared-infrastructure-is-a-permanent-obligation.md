---
title: "7.7 Multi-tenancy on shared infrastructure is a permanent obligation"
type: section
tags: [section, multi-tenancy]
aliases: ["§7.7"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 7.7 Multi-tenancy on shared infrastructure is a permanent obligation

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Partitioned-data multi-tenancy is cheaper than per-tenant clusters, and it means every store access, every cache key, every artifact reference, and every log line carries a correctness requirement forever. One missing partition filter is a cross-tenant data leak. This is why `tenant_id` comes only from a verified token claim, why the policy engine fails closed, and why cross-tenant isolation is tested as a deterministic gate rather than trusted.
