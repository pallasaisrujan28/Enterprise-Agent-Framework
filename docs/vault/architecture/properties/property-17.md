---
title: "Property 17: Ingestion config validation is narrow, total, and fail-closed"
type: property
tags: [property]
aliases: ["Property 17"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 17: Ingestion config validation is narrow, total, and fail-closed

Part of [[correctness-properties|Correctness Properties]].

*(Retargeted in this revision. The previous version covered general pipeline-config validation; that config surface no longer exists — [[ADR-015]].)*

For all raw ingestion config documents `d`: `validate_ingestion_config(d)` returns either an `IngestionConfig` or a complete list of violations — never a partially usable config, and never a success on a document where `chunking.overlap >= chunking.size`, `embedding.dimensions` differs from the target index dimension, `target_index` does not already exist, `target_index` is not scoped to `tenant_id`, `source_uri` uses a non-allowlisted scheme, or a credential appears inline. **Validation never creates a resource** — a missing index is an error, not a provisioning trigger (Terraform owns lifecycle). *(property-based: arbitrary and mutated config documents)*
