---
title: "5.1 Deployment Topology"
type: section
tags: [section, deployment]
aliases: ["§5.1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 5.1 Deployment Topology

Part of [[5-aws-deployment-evaluation|5. AWS Deployment & Evaluation]].

**The eventual deployment target is Kubernetes — containers on Amazon EKS, one namespace per architectural layer, Terraform owning cluster and cloud resource lifecycle, Helm packaging the workloads ([[ADR-018]]).** Stated here so a reader of [[§5]] does not have to infer it from the diagram. The scaling architecture that follows from that decision — what each tier scales on and why — is [[§5.7]]. For what actually runs today, and the local image behind each service below, see [[§4.1]].

```mermaid
graph TB
    subgraph Edge["Edge"]
        R53[Route 53]
        WAF[AWS WAF]
        ALB[ALB / API Gateway]
    end

    subgraph EKS["Amazon EKS - private subnets, one namespace per layer"]
        subgraph NSGW["ns: gateway"]
            GWP[Agent Gateway pods<br/>authn, schema, rate limit, input rails]
            OPAP[OPA sidecar - PDP<br/>policy bundles from S3]
        end
        subgraph NSOR["ns: orchestrator"]
            ORP[Orchestrator pods - stateless<br/>router, planner, prompt assembler, output rails, HITL]
            MPP[Model Proxy pods<br/>model routing, prompt cache, egress redaction]
            CMP[Async Compaction workers]
        end
        subgraph NSEX["ns: executors"]
            EXP[Executor sub-agent pods<br/>LangGraph loop per agent type]
            SBX[Sandbox pods - NVMe instance store<br/>T0 POSIX scratch: ls, grep, glob, cat<br/>code/shell execution, gVisor isolation]
            EXP <--> SBX
        end
        subgraph NSMCP["ns: mcp"]
            MGP[MCP Gateway pods]
            PB[browser pool - 3+ replicas]
            PD[db pool - 3+ replicas]
            PF[file pool - 3+ replicas]
            PS[search pool - 3+ replicas]
        end
    end

    subgraph Data["Data & State"]
        REDIS[(T3 - ElastiCache Redis<br/>session manifest, budgets, locks, breakers)]
        ETCD[(Tool Registry - etcd<br/>chosen over DynamoDB for portability - 4.1)]
        S3A[(T1 - S3 Express One Zone<br/>session artifacts, single-digit-ms, single-AZ)]
        S3ARC[(T2 - S3 Standard<br/>artifact + trajectory archive)]
        S3P[(S3 - artifact bundles, content-hashed<br/>prompts, policies, SKILLS, tool catalogs,<br/>retrieval strategies, ingestion configs)]
        DDB[(DynamoDB - tenant + agent metadata)]
        AURORA[(Aurora PostgreSQL + pgvector<br/>vector RAG)]
        OS[(OpenSearch - fulltext / hybrid)]
        NEP[(Neo4j - GraphRAG entity graph<br/>Cypher in both environments - 4.1.1)]
        SM[Secrets Manager + KMS<br/>PII vault keys]
        VAULT[(PII Vault - DynamoDB, KMS-encrypted, TTL)]
    end

    subgraph Models["Model Access"]
        BR[Amazon Bedrock]
        EXTM[External providers via NAT + egress allowlist]
    end

    subgraph Obs["Observability & Learning"]
        OTEL[OTel Collector - DaemonSet]
        CW[CloudWatch metrics + alarms]
        XR[AWS X-Ray - traces]
        LS[LangSmith - traces, datasets, evals]
        FH[Kinesis Firehose]
        S3T[(S3 - trajectory lake)]
        GLUE[Athena / Glue - cost + cache analytics]
        SM2[SageMaker - Track A RFT jobs, optional]
    end

    R53 --> WAF --> ALB --> GWP
    GWP <--> OPAP
    OPAP -.bundle pull.-> S3P
    GWP --> ORP
    ORP <--> REDIS
    ORP --> MPP
    ORP --> EXP
    ORP --> CMP --> S3A
    EXP --> MGP
    MGP <--> ETCD
    MGP --> PB & PD & PF & PS
    PF --> S3A
    SBX -->|offload T0 to T1| S3A
    S3A -->|async archive| S3ARC
    S3ARC ---|same T2 tier: artifacts + traces| S3T
    ORP -.prompt + skill + tool-catalog artifacts.-> S3P
    PS -.retrieval strategy + ingestion config.-> S3P
    PS --> AURORA & OS & NEP
    PD --> AURORA
    PB --> EXTM
    MPP --> BR
    MPP --> EXTM
    GWP --> VAULT
    ORP --> VAULT
    VAULT -.keys.-> SM
    ORP -.metadata.-> DDB
    GWP & ORP & MGP & EXP -.otlp.-> OTEL
    OTEL --> CW
    OTEL --> XR
    OTEL --> LS
    OTEL --> FH --> S3T --> GLUE
    S3T --> SM2
```

**Isolation and scaling notes.**

- Each layer is its own namespace with a **default-deny NetworkPolicy** and an explicit egress allowlist. The `db` pool cannot reach the internet; the `browser` pool can reach only allowlisted domains via NAT.
- Gateway, orchestrator, and model proxy are **stateless** and scale on request rate and in-flight-turn count. Tool pools scale independently per domain — `browser` pods are memory-hungry and slow, `db` pods are cheap and fast, and coupling their autoscaling wastes money. The full per-tier saturation signal, minimum replica counts, and autoscaling mechanism are in **[[§5.7]].1**.
- Tenancy is **shared-infrastructure, partitioned-data** by default: one EKS cluster, per-tenant `data_partition` on every store, per-tenant KMS keys for the vault. A dedicated-cluster tier exists for tenants whose contracts require physical isolation; the architecture does not change, only the deployment target.
- **Startup order is enforced by readiness gates**, not by luck: registry → orchestrator → pools → gateway. Orchestrator readiness fails until the tool registry snapshot is loaded ([[§2.8]]).
- Model access defaults to Bedrock inside the VPC; external providers egress through NAT with an allowlist, and the model proxy re-checks redaction immediately before egress.
- **Storage tiers map to distinct services on purpose** ([[ADR-016]]): T0 is the sandbox pod's NVMe instance store on a storage-optimized node group, T1 is an S3 Express One Zone directory bucket in the same AZ as the executor node group (co-location is what buys the latency), T2 is S3 Standard with lifecycle rules to cheaper classes past the eval retention window, T3 is ElastiCache Redis. Sandbox pods run under a stronger isolation boundary (gVisor or Firecracker-backed nodes) because they execute model-authored code; they get a dedicated node group with no IAM path to tenant data beyond their own session prefix.
- **Terraform owns every resource in the Data & State and Edge groups above** ([[ADR-015]]): the vector index, fulltext index, graph store, buckets, Redis, IAM, KMS keys, node groups, and network policy. The ingestion pipeline syncs documents into those resources and never creates them.
- **Artifacts are deployed as pointers, not baked into images.** Prompt, policy, **skill**, tool-catalog, retrieval-strategy, and ingestion-config bundles land in S3, are content-hashed, and are resolved by pointer at load — so attaching a skill, adding a tool, or changing a chunking parameter is a **promotion, not a rebuild** ([[ADR-002b]], [[ADR-014]], [[ADR-015]], [[§3.8]]).
