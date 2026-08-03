---
title: "ADR-015: Terraform owns infrastructure; a narrow typed config owns only chunking and embeddings; everything else is code"
type: adr
tags: [adr, infrastructure]
aliases: ["ADR-015"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-015: Terraform owns infrastructure; a narrow typed config owns only chunking and embeddings; everything else is code

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Three distinct ownership boundaries, and nothing crosses them:

| Concern | Owner | Change mechanism |
| --- | --- | --- |
| Vector store, graph store, buckets, indexes, IAM, network — **all cloud resources** | **Terraform** | A Terraform PR and an apply |
| Source location, **chunking strategy + parameters**, **embedding model + dimensions**, target index name, optionally retrieval mode + `top_k` | **A narrow typed config** (a small Pydantic model, not a DSL) | A config PR, validated at load |
| Ingestion pipeline, retrieval strategy, fusion, reranking, GraphRAG extraction, agent definitions | **Code** | An ordinary code PR, versioned as an artifact |

The ingestion pipeline is **code that syncs documents into resources that already exist** — created and owned by Terraform. It never creates a store, an index, or a bucket. Retrieval strategy is code, versioned as an artifact ([[ADR-014]]), and paired with an **accuracy evaluation harness** that scores strategies against a labeled set so "did this change help" is a measured answer rather than an opinion.

**Agents are defined in code. Skills are the configuration surface for capability** ([[ADR-002b]], [[P12]]). There is no agent-graph YAML.

**Context.** The previous version of this ADR proposed full declarative YAML for both knowledge pipelines and agent graphs, modeled on a general pipeline-serialization format. That was wrong on two counts, and the review that killed it was right on both. First, **Terraform already owns resource lifecycle** — every cloud team has it, it has state, drift detection, and a plan/apply review model that a bespoke config loader will never match. A config format that also creates stores and indexes duplicates that ownership and creates two sources of truth for the same resource. Second, the honest answer to "how flexible is configuring these pipelines through YAML?" is: **only chunking and embeddings genuinely want to be configurable.** Those are the knobs a domain expert actually turns per corpus. Everything else in the pipeline — how documents are fetched, how they are transformed, how retrieval fuses and reranks — is code that changes for engineering reasons, and expressing it as config buys nothing while costing a great deal.

**Rationale.** Narrowing the configurable surface to a typed Pydantic model with about six fields makes it *actually* reviewable by a non-engineer, which the general DSL never was — a 90-line component graph with named socket connections is not more accessible than Python, it is Python with worse tooling. Meanwhile the things that genuinely need to be swappable per corpus (chunking strategy, embedding model and dimensions) are exactly the things with narrow, typed, enumerable options.

Making retrieval strategy **code with an accuracy harness** is the other half of the correction. A retrieval change is only meaningful if it is measurable, so the harness is a first-class component ([[§3.6]]) with real metrics: **recall@k**, **MRR / nDCG**, and **answer-level groundedness**. That answers "calculate accuracy metrics against the retrieval strategy" with a number rather than a config diff.

**Why the full pipeline-as-YAML was rejected — recorded so it is not re-proposed.**
1. **It is a framework-building project, not a platform feature.** Component registries, socket type systems, connection validators, migration machinery — that is a product in itself, and it is not the product we are building.
2. **It moves defects from compile time to load time.** A type error caught by `mypy` in CI becomes a schema error discovered when a config loads, and the validator becomes critical-path code with its own bug surface.
3. **Expressiveness ceilings are unavoidable.** Anything genuinely novel needs a new component type registered in code — so config composes existing components and never invents them. You pay the whole framework cost and still write code for the interesting cases.
4. **Terraform already owns resource lifecycle.** Config that also creates resources duplicates that ownership and produces drift between two systems that both believe they own the index.

**Consequences.**
- (+) One source of truth per concern: infrastructure in Terraform state, behaviour in code artifacts, per-corpus knobs in a typed config.
- (+) The remaining config is small enough to validate exhaustively and small enough for a domain expert to own genuinely rather than nominally.
- (+) Retrieval quality becomes a measured, gated property (recall@k, MRR/nDCG, groundedness) with a CI regression gate ([[§5.5]]) instead of a vibe.
- (+) No YAML loader, no component registry, no schema-migration machinery to build, test, or operate. That is a substantial amount of work removed from [[Phase 3]].
- (−) Changing anything outside chunking/embeddings/index-target is a code deploy. That is the intended trade: fewer knobs, sharper tools, defects caught by the type checker.
- (−) Two review paths for one logical change — a new corpus may need a Terraform PR (create the index) *and* a config PR (point ingestion at it). The ordering must be documented so the config PR does not land first against a nonexistent index.

**Alternatives considered.**
- **(a) Full pipeline-as-YAML with a component registry (the previous decision)** — rejected for the four reasons above.
- **(b) Agent-graph YAML** — rejected. Agents are code; skills are the configuration surface for capability ([[ADR-002b]]). Declaring agents in YAML recreates the topology-growth pressure [[ADR-012]] exists to resist, and it competes with skills for the same job while being strictly worse at it.
- **(c) Config creates its own infrastructure** — rejected. Two owners for one resource is drift by construction.
- **(d) Everything in code, no config at all** — rejected. Chunking strategy and embedding model genuinely vary per corpus and are tuned by people who should not need a deploy to try `split_length: 8`.
- **(e) Database-stored config edited through a UI** — rejected, loses git review, diffing, and artifact immutability.
