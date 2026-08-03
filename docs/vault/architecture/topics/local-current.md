---
title: "Local (current)"
type: topic
tags: [topic, local-first]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# Local (current)

Part of [[dependencies|Dependencies]].

Every backing service is a **pinned container image** on Docker Compose ([[ADR-019]]). Nothing here needs a cloud account.

| Concern | Local dependency | Profile |
| --- | --- | --- |
| Agent execution substrate | **LangGraph**, pinned exact — in the application images | all |
| Tool servers | An **MCP-compatible tool server framework** — in the application images | all |
| Policy decision point | **OPA** — `openpolicyagent/opa` | minimal |
| Session hot state (T3) | **Redis** — `redis:7-alpine` | minimal |
| Object store (T1 + T2) | **MinIO** via the **S3 API** — `minio/minio` | minimal |
| Relational + vector store | **Postgres + pgvector** — `pgvector/pgvector:pg16` | minimal |
| Tool registry | **etcd** — `quay.io/coreos/etcd` | minimal |
| Traces | **OpenTelemetry** instrumentation → **Jaeger** — `jaegertracing/all-in-one` | minimal |
| Metrics | **OpenTelemetry** → **Prometheus + Grafana** — `prom/prometheus`, `grafana/grafana` | metrics |
| Fulltext / hybrid search | **OpenSearch** — `opensearchproject/opensearch` | knowledge |
| Graph store (GraphRAG) | **Neo4j** — `neo4j` (Cypher in both environments, [[§4.1]].1) | knowledge |
| Model inference | **AWS Bedrock** — not a container; reached over the network in every environment, including local ([[ADR-011]]). Requires AWS credentials and incurs spend during local development | all |
| Sandbox (T0) | **Docker** with dropped capabilities, read-only root, no network by default | all |
| Secrets | A **resolver interface** over `.env` / Docker secrets | all |
| Orchestration | **Docker Compose** | — |

**Local CI:** `ruff` (lint + format), `pip-audit` (dependency vulnerabilities), `trivy` (image scan), `gitleaks` (secret scanning). That is the entire pipeline ([[§4.4]]).
