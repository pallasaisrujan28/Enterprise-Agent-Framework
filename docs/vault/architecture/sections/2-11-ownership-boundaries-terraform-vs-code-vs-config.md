---
title: "2.11 Ownership Boundaries: Terraform vs Code vs Config"
type: section
tags: [section, infrastructure]
aliases: ["§2.11"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 2.11 Ownership Boundaries: Terraform vs Code vs Config

Part of [[architecture|Architecture]].

There is no general pipeline configuration language in this platform ([[ADR-015]]). Three owners, one concern each, and nothing crosses the line.

> **While development is local ([[ADR-019]]), the "Terraform" box is played by Docker Compose.** The boundary is unchanged — *something declarative owns resource lifecycle, and neither code nor config ever creates a resource* — but the declarative thing is a Compose file, not Terraform. **There is no Terraform for local**; it arrives post-checkpoint, along with the cloud resources it would own ([[§4.3]], [[§8]]). Read "Terraform" below as "whatever owns resource lifecycle in this environment."

```mermaid
flowchart LR
    subgraph TF["Terraform - owns infrastructure lifecycle"]
        TFA[Vector store + indexes]
        TFB[Graph store]
        TFC[Buckets - T1/T2, artifact bundles]
        TFD[IAM, KMS, network, egress]
    end

    subgraph CODE["Code - owns behaviour, versioned as artifacts"]
        CA[Document sync pipeline<br/>syncs INTO resources that already exist]
        CB[Retrieval strategy<br/>modes, fusion, reranking]
        CC[Agent definitions + executor loops]
        CD[GraphRAG extraction + community building]
    end

    subgraph CFG["Narrow typed config - the ONLY config surface"]
        CFA[source location]
        CFB[chunking strategy + parameters]
        CFC[embedding model + dimensions]
        CFD[target index name]
        CFE[retrieval mode + top_k - optional]
    end

    subgraph SKILL["Skills - the config surface for CAPABILITY"]
        SK[manifest + body + resources + eval cases<br/>no code, no redeploy - ADR-002b]
    end

    TF -->|creates| STORES[(Vector / fulltext / graph stores + indexes)]
    CFG -->|validated - target index MUST already exist| CA
    CA -->|writes documents| STORES
    CB -->|reads| STORES
    CB --> EVALH[Retrieval accuracy harness<br/>recall@k, MRR/nDCG, groundedness]
    EVALH -->|CI regression gate| CB
    SKILL -->|policy grant + pointer promotion| CC
    CODE -.->|artifacts under ADR-014| ART[(Artifact registry<br/>content-hashed, canaried)]
    SKILL -.-> ART
```

Three rules make the boundary hold: **config never creates a resource** (Terraform owns lifecycle; a config referencing a nonexistent index fails validation), **code never hardcodes a per-corpus knob** (chunking and embeddings belong in config because they are tuned per corpus by people who should not need a deploy), and **capability arrives as a skill, not as config** ([[ADR-002b]], [[P12]]). Full detail in [[§3.6]] (document sync + ingestion config + accuracy harness) and [[§3.8]] (tool onboarding).
