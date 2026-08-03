---
title: "4.3 Local Compose topology"
type: section
tags: [section, local-first]
aliases: ["§4.3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# 4.3 Local Compose topology

Part of [[4-service-selection-and-local-first-development|4. Service Selection and Local-First Development]].

One container per architectural layer, so the layer boundaries in [[§2.1]] and the contracts in [[§3.1]] are crossed over a real network hop rather than collapsed in-process. **A developer machine cannot comfortably run everything at once**, so the stack is split into profiles.

```mermaid
graph TB
    subgraph App["Application containers - all profiles"]
        GW[gateway<br/>authn, schema, rate limit, input rails]
        OR[orchestrator<br/>planner, prompt assembler, output rails, HITL<br/>+ model proxy]
        EX[executor<br/>LangGraph loop per agent type]
        SBX[sandbox<br/>dropped caps, read-only root, no network]
        MCP[mcp-gateway<br/>+ tool pools: db, file, search]
        EX <--> SBX
    end

    subgraph Min["MINIMAL PROFILE - enough for Phase 0 and Phase 1"]
        RD[(redis:7-alpine<br/>T3 session manifest, budgets, locks)]
        MIN[(minio<br/>S3 API: T1 artifacts + T2 archive)]
        PG[(pgvector/pgvector<br/>Postgres + pgvector)]
        OPA[opa<br/>policy decision point]
        ETCD[(etcd<br/>tool registry)]
        JG[jaeger<br/>OTel trace backend]
    end

    subgraph Know["OPTIONAL PROFILE: knowledge - Phase 3"]
        OS[(opensearch<br/>fulltext / hybrid - heavyweight JVM)]
        NEO[(neo4j<br/>GraphRAG entity graph - Cypher both envs)]
    end

    subgraph Mod["NOT A CONTAINER - reached over the network in every environment"]
        OLL[AWS Bedrock<br/>all model calls, local included<br/>ADR-011 - the one P16 exemption]
    end

    subgraph Met["OPTIONAL PROFILE: metrics"]
        PROM[prometheus]
        GRAF[grafana]
    end

    GW --> OR --> EX --> MCP
    GW <--> OPA
    OR <--> RD
    SBX -->|offload T0 to T1| MIN
    MIN -->|archive| MIN
    MCP <--> ETCD
    MCP --> PG
    MCP --> OS
    MCP --> NEO
    OR --> OLL
    GW & OR & EX & MCP -.otlp.-> JG
    GW & OR & EX & MCP -.otlp.-> PROM --> GRAF

    style Know stroke-dasharray: 5 5
    style Mod stroke-dasharray: 5 5
    style Met stroke-dasharray: 5 5
```

**The profile split, and why it exists.**

| Profile | Services | Enough for |
| --- | --- | --- |
| **minimal** (default) | Redis, MinIO, Postgres+pgvector, OPA, etcd, Jaeger | **[[Phase 0]] and [[Phase 1]] in full.** The vertical slice needs no search engine and no graph |
| **knowledge** (opt-in) | OpenSearch, Neo4j | [[Phase 3]]. Both are heavyweight; OpenSearch especially. Off until the knowledge layer exists |
| ~~**models**~~ | *(removed)* | **There is no local model profile.** All model calls go to Bedrock in every environment ([[ADR-011]]), so there is no inference container to run |
| **metrics** (opt-in) | Prometheus, Grafana | Dashboard work. Traces alone (Jaeger) cover most local debugging |

**Compose conventions**, in brief — the authoritative copy is `.kiro/steering/local-development.md` and is deliberately not restated here:

- **Pinned exact image tags.** Never `:latest`.
- **Health checks on every service**, with `depends_on: { condition: service_healthy }` enforcing the **same startup ordering as production** — registry → orchestrator → pools → gateway ([[§2.8]], [[§5.7]].5). Ordering bugs surface on a laptop instead of in a cluster.
- **Named volumes** for anything stateful, so a restart is not data loss.
- **One `docker compose up` brings the stack to a working state.** If onboarding needs a runbook, the Compose file is wrong.
- **Resource limits** on containers, so behaviour under constraint is at least directionally informative.

**Terraform is not used locally at all.** Compose covers the local resource lifecycle. [[ADR-015]]'s "Terraform owns infrastructure" boundary is unchanged, but it applies to **cloud** resources and therefore activates **post-checkpoint** ([[§8]]). Writing Terraform for a laptop would be ceremony with no consumer.
