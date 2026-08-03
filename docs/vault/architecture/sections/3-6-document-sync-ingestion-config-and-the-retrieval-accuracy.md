---
title: "3.6 Document Sync, Ingestion Config, and the Retrieval Accuracy Harness"
type: section
tags: [section, retrieval, evals]
aliases: ["§3.6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 3.6 Document Sync, Ingestion Config, and the Retrieval Accuracy Harness

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

There is **no YAML pipeline DSL** and **no agent-graph YAML** in this platform. [[ADR-015]] records why. What remains is three things: a **document sync pipeline** (code), a **narrow typed ingestion config** (about six fields), and a **retrieval accuracy evaluation harness** (a first-class component, because a retrieval change that is not measured is not a change worth making).

#### 3.6.1 The Document Sync Pipeline (code)

The pipeline **syncs documents into resources that already exist**. Terraform created the vector index, the fulltext index, the graph store, and the bucket; the pipeline never creates any of them, and a config naming a target index that does not exist fails validation rather than provisioning one.

```pascal
PROCEDURE sync_documents(config, since)
  INPUT:  config (IngestionConfig, already validated)
          since (Timestamp?) — incremental watermark; NULL means full sync
  OUTPUT: SyncReport

  SEQUENCE
    // Preconditions are asserted, not assumed: Terraform owns the resource.
    ASSERT indexExists(config.target_index)                  // else fail closed (ADR-015)
    ASSERT indexPartitionMatches(config.target_index, config.tenant_id)   // Property 1

    docs      ← fetchChanged(config.source_uri, since)       // code: source adapters are code
    converted ← convert(docs)                                // code: parsing/OCR/table handling
    scrubbed  ← applyPiiPolicy(converted, config.tenant_id)  // ADR-009 stage in force for this phase
    chunks    ← chunk(scrubbed, config.chunking)             // CONFIGURABLE surface
    vectors   ← embed(chunks, config.embedding)              // CONFIGURABLE surface

    ASSERT dimension(vectors) = config.embedding.dimensions  // mismatch is a hard failure, never a coerce

    upserted  ← upsert(config.target_index, chunks, vectors) // idempotent by content digest
    IF config.graph_extraction_enabled THEN
      extractEntitiesAndCommunities(scrubbed)                // code; opt-in per corpus (ADR-007)
    END IF

    RETURN SyncReport(upserted, skipped, failed, watermark := now())
  END SEQUENCE
END PROCEDURE
```

**Preconditions.** The target index exists and is scoped to the tenant partition; the embedding model named in config is reachable and its dimension matches the index.
**Postconditions.** Every changed source document is either upserted or recorded as failed with a reason; the operation is **idempotent** — re-running with the same watermark converges to the same index state, because upsert is keyed on content digest; no resource is created as a side effect.
**Loop invariant.** For every document processed so far, either an upsert landed or a failure was recorded; the sync never leaves a document in an unknown state, and a partial run is safely resumable from the last watermark.

#### 3.6.2 The Narrow Typed Ingestion Config (the only config surface)

A small Pydantic model, not a pipeline DSL. This is the entire configurable surface for the knowledge layer.

```python
# The complete list. Adding a field here is an ADR-015 decision, not a routine change.
class ChunkingConfig(BaseModel):
    strategy: Literal["sentence", "recursive", "semantic", "markdown_section"]
    size: int = Field(gt=0, le=4096)  # tokens
    overlap: int = Field(ge=0, le=512)
    respect_headings: bool = True

    @model_validator(mode="after")
    def overlap_below_size(self):
        if self.overlap >= self.size:
            raise ValueError("overlap must be smaller than size")
        return self


class EmbeddingConfig(BaseModel):
    model: str  # named, allowlisted model id
    dimensions: int = Field(gt=0)  # MUST match the Terraform-created index
    batch_size: int = Field(gt=0, le=512, default=64)


class IngestionConfig(BaseModel):
    tenant_id: str
    source_uri: str  # s3://... | https://... (allowlisted schemes only)
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    target_index: str  # MUST already exist (Terraform); validated, never created
    retrieval_mode: Literal["vector", "fulltext", "graph", "hybrid"] = "hybrid"  # optional
    top_k: int = Field(gt=0, le=100, default=12)  # optional
    graph_extraction_enabled: bool = False  # GraphRAG is opt-in per corpus (ADR-007)
```

That is it. No components map, no socket connections, no cycle detection, no schema-migration machinery. Everything a reviewer needs to understand fits on one screen, which is the property the general DSL claimed and never delivered.

**Validation is narrow and fails closed** ([[Property 17]], retargeted): types and ranges from the model itself, `overlap < size`, `embedding.dimensions` equal to the target index dimension, `target_index` **exists** and is scoped to `tenant_id`, `source_uri` scheme allowlisted, and no inline credentials (secret references only). A config either validates completely or the sync does not run.

#### 3.6.3 Retrieval Strategy as a Versioned Code Artifact

Retrieval strategy — mode selection, fusion, reranking, graph expansion depth — is **code**, versioned as an artifact under [[ADR-014]] exactly like a prompt. A strategy change is therefore canaried and rolled back by pointer, and it is attributable in every `TrajectoryRecord` that used it.

```python
class RetrievalStrategy(Protocol):
    version: str  # content hash of the strategy implementation

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...
```

#### 3.6.4 The Retrieval Accuracy Evaluation Harness

This is the component that makes "did this retrieval change help?" a number instead of an argument. It scores a strategy version against a **labeled set** of `(query, relevant_document_ids, expected_answer)` triples per corpus.

```python
class RetrievalAccuracyReport(BaseModel):
    strategy_version: str
    corpus: str
    labeled_set_version: str
    # Retrieval-level metrics
    recall_at_k: dict[int, float]  # k in {1, 5, 10, 20}
    mrr: float  # mean reciprocal rank of the first relevant hit
    ndcg_at_k: dict[int, float]  # graded relevance, rank-discounted
    # Answer-level metric — retrieval that scores well but grounds badly is not a win
    groundedness: float  # share of answer claims supported by retrieved citations
    # Operational
    p95_latency_ms: float
    cost_per_query: float


def score_retrieval(
    strategy: RetrievalStrategy,
    labeled_set: str,
) -> RetrievalAccuracyReport: ...
```

| Metric | Answers |
| --- | --- |
| **recall@k** | Did the relevant documents make it into the candidate set at all? A reranker cannot fix what retrieval never returned. |
| **MRR / nDCG@k** | Are they ranked where the model will actually read them? Recall with bad ranking still loses inside a bounded context window. |
| **Groundedness** | Do the final answer's claims trace to the retrieved citations? This is the only metric a tenant experiences directly. |
| **p95 latency, cost/query** | The cost side of the trade, so a quality win that triples latency shows up as a trade rather than a victory. |

**How it is used.**
- **CI regression gate** ([[§5.5]]): a strategy change that lowers recall@10, MRR, or groundedness beyond a threshold on any corpus's labeled set **fails the build**. Retrieval regressions are otherwise invisible until a tenant complains.
- **The GraphRAG on/off decision** ([[§7.4]]): graph mode is enabled per corpus only if the harness shows it moved the numbers on that corpus. If it did not, it is turned off there. This harness is what makes that commitment enforceable rather than aspirational.
- **Chunking and embedding tuning:** the two configurable knobs are tuned against this harness, which is the entire reason they are the two knobs.

The labeled set is itself a versioned artifact, built from curated production traffic with PII handling per the [[ADR-009]] stage in force, and it is reviewed like a test fixture.
