---
title: "ADR-007: Hybrid RAG + GraphRAG retrieval"
type: adr
tags: [adr, graph, retrieval, evals]
aliases: ["ADR-007"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-007: Hybrid RAG + GraphRAG retrieval

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Provide **baseline vector RAG** for semantic recall and **GraphRAG** (LLM-extracted entity/relationship graph + community summaries) for multi-hop and global-corpus questions. Retrieval is **hybrid**: vector search + graph traversal, with a router selecting strategy per query.

**Context.** Vector RAG is strong for local semantic lookup but weak on multi-hop reasoning and "global" questions about a corpus.

**Rationale.** GraphRAG reports the semantic structure of a corpus and supports multi-hop traversal; vector RAG is cheaper for direct recall. A hybrid maximizes answer quality across query types.

In practice this means three retrieval modes behind one interface: **vector** similarity, **fulltext/BM25** for exact terms and identifiers, and **graph traversal** (Cypher-style expansion over an entity graph). [Microsoft GraphRAG](https://microsoft.github.io/graphrag/) uses an LLM to extract entities and relationships from documents and then builds community summaries, which is what enables global "what is in this corpus" questions and multi-hop causal chains that pure vector similarity misses.

**Resolving the apparent contradiction with Manus.** The Manus write-up argues *against* RAG for agents, in favour of a filesystem with `grep`/`glob`. That is not a conflict with this ADR because the two solve different problems, and we keep them as separate subsystems ([[P11]]):

| Concern | Mechanism | Lifetime | Owner |
| --- | --- | --- | --- |
| Agent **working memory** — intermediate artifacts, fetched pages, scratch files, tool outputs | Sandbox filesystem + object store, navigated with `file_*` tools | Session / task | Executor sub-agent |
| Enterprise **knowledge retrieval** — tenant corpora, policies, tickets, docs | Vector + fulltext + GraphRAG behind `search_*` tools | Long-lived, indexed | Knowledge layer |

Collapsing these into one abstraction is the mistake: indexing scratch files pollutes the knowledge base, and routing working memory through a retrieval ranker loses the exact-path addressing that restorable compression ([[ADR-006]]) depends on.

**Consequences.**
- (+) Handles both local recall and global/multi-hop reasoning.
- (+) Working memory stays exact-addressable and cheap; knowledge stays curated and governed.
- (−) Graph construction/maintenance cost; indexing pipeline plus two retrieval systems to operate.
- (−) GraphRAG indexing is LLM-heavy and therefore a real per-corpus cost; it is enabled per tenant/corpus, not globally by default.

**Alternatives considered.** Vector-only — rejected (weak multi-hop/global). Graph-only — rejected (overkill and slower for simple recall). Filesystem-only (strict Manus position) — rejected for the enterprise knowledge case, where corpora are shared across sessions and need governance, versioning, and access control that a scratch filesystem does not provide.
