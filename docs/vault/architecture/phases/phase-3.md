---
title: "Phase 3 — Knowledge layer: document sync, hybrid retrieval, accuracy harness"
type: phase
tags: [phase, retrieval, evals]
aliases: ["Phase 3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Phase 3 — Knowledge layer: document sync, hybrid retrieval, accuracy harness

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Runs locally on Compose — this is the phase that turns on the `knowledge` optional profile** (OpenSearch and, if GraphRAG is enabled, Neo4j — [[§4.3]]). Both are heavyweight on a laptop, which is why they were off until now.

**Ship:** the knowledge resources declared where they are owned — **locally in the Compose `knowledge` profile** (vector index in Postgres+pgvector, fulltext index in OpenSearch, buckets in MinIO, the Neo4j graph store when GraphRAG is enabled), and **in Terraform post-checkpoint**; the **document sync pipeline** as code, syncing into those existing resources and never creating them ([[§3.6]].1); the **narrow typed ingestion config** with fail-closed validation ([[§3.6]].2); retrieval strategy as a versioned code artifact with vector, fulltext, hybrid fusion, and reranking ([[§3.6]].3); the **retrieval accuracy evaluation harness** with labeled sets per corpus and recall@k / MRR / nDCG / groundedness, wired as a CI regression gate ([[§3.6]].4); retrieved-content rails. **GraphRAG lands in the second half of this phase, opt-in per corpus** — entity/relationship extraction, community summaries, multi-hop traversal, and retrieval-mode selection.

**Explicitly not shipped:** a YAML pipeline loader, a component registry, schema versioning, or config migrations. [[ADR-015]] removed all of it. Cloud infrastructure is Terraform (post-checkpoint) and local infrastructure is Compose; pipelines and retrieval are code; the only config is the six-field ingestion model.

**Exit criterion:** a new corpus is onboarded with a **resource-declaration PR** (Compose service or index creation locally; a Terraform PR post-checkpoint) plus an ingestion-config PR (point sync at it) and **no pipeline code change**; hybrid retrieval beats vector-only on the labeled set by a measured margin on recall@10 and MRR; the accuracy harness runs as a blocking CI gate; for at least one corpus the harness answers whether graph mode moved the numbers — and if it did not, graph mode is turned off for that corpus ([[§7.4]]).
