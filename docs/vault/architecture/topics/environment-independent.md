---
title: "Environment-independent"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# Environment-independent

Part of [[dependencies|Dependencies]].

**Configuration (narrow):** Pydantic for the ingestion config model and its validation ([[§3.6]].2). **Removed in this revision:** the YAML pipeline loader, the component registry, config schema-migration tooling, and Haystack-as-schema-pattern — [[ADR-015]] replaced all of it with Terraform plus code plus a six-field typed config.

**Skills:** a markdown-plus-manifest artifact format, the skill registry backed by the same content-hashed artifact store as prompts and policies, and a skill eval runner in CI ([[ADR-002b]]). No new external dependency — skills are deliberately boring.

**Guardrails & PII:** NeMo Guardrails (Colang policy orchestration) from [[Phase 2]]. Interim PII detection ([[Phase 1]]) is deterministic pattern matching plus Luhn validation, optionally a managed service such as Amazon Comprehend PII. The **final-phase** stack ([[Phase 6]]) adds Presidio (PII detection/redaction), a GLiNER-PII-class model (broad-category NER, toxicity, jailbreak, refusal), and a KMS-encrypted vault store for reversible tokens ([[ADR-009]], [[§7.10]]).

**Knowledge:** an embedding model, **Postgres + pgvector** for vector search and **OpenSearch** for fulltext (the same engines local and managed — [[§4.1]]), **Neo4j** for the GraphRAG entity graph in **both** environments ([[§4.1]].1 — Neptune is a rejected alternative, not a substitutable one), a GraphRAG extraction implementation in code, and a retrieval-accuracy metric implementation (recall@k, MRR, nDCG, groundedness) with per-corpus labeled sets.

**Classification:** nothing beyond the model proxy and Bedrock ([[ADR-013]]). No embedding model, no classifier head, no training dependency. If the deferred self-hosted classifier is ever restored, it adds a small embedding model plus a lightweight head (centroid, kNN, or logistic regression) — recorded here so the cost of reversing is visible.

**Evaluation & improvement:** LangSmith (tracing, datasets, eval runs), DeepEval (pytest-native assertions in CI), Hypothesis (property-based tests), DSPy + GEPA (RL Phase A reflective optimization), a contextual-bandit implementation for RL Phase B routing and escalation policies, Agent Lightning (RL Phase C over the existing stack, optional; verl/verl-agent, OpenPipe ART, OpenRLHF, SkyRL, NVIDIA Polar, Agent-R1, RAGEN as alternatives).

**Note on evaluation tooling and local development:** DeepEval and Hypothesis run locally with no infrastructure. **LangSmith is SaaS, so trajectories leave the machine** — acceptable against synthetic fixtures, and a real consideration once tenant data exists ([[§4.1]], [[ADR-009]]).

The **orchestration, autoscaling, sandbox-isolation, and cloud-platform dependencies** that previously sat here are now in the **Cloud (post-checkpoint)** group above, because none of them is installed. Kubernetes, EKS, Helm, ECR, Terraform, HPA/KEDA/Karpenter, the gVisor-class runtime, NVMe instance-store nodes, ALB/WAF, CloudWatch, X-Ray, and the Firehose/Athena trajectory lake are all future state ([[ADR-018]], [[ADR-019]]).

**Dependencies are pinned to exact versions — code packages and container image tags alike. Nothing floats, and never `:latest`.**

---
