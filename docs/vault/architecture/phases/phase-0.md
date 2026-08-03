---
title: "Phase 0 — Local foundation and service selection"
type: phase
tags: [phase, local-first]
aliases: ["Phase 0"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# Phase 0 — Local foundation and service selection

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Ship:** the **service choices settled and recorded** in [[§4.1]] — every concern in the platform has a named choice, a rejected alternative, a recorded tradeoff, and a pinned local image; the **minimal Compose profile** standing up (Redis, MinIO, Postgres+pgvector, OPA, etcd, Jaeger) with pinned tags, health checks, `depends_on: service_healthy` enforcing the production startup order, named volumes, and resource limits; the **three CI gates** wired (lint/format, dependency audit, image scan, secret scanning — [[§4.4]]) and nothing else; the **portability seams** established before any code depends on them — the **secret resolver interface**, the **object-store interface over the S3 API**, and **OpenTelemetry instrumentation**; and a **hello-world request crossing one layer boundary** — gateway → orchestrator over a real network hop.

**Why this is a phase rather than setup.** Two of these are genuinely load-bearing and expensive to retrofit. The **portability seams** are the thing that makes [[ADR-019]]'s "config change, never a code change" true; added after fifty modules read `os.environ` for credentials and construct clients inline, they are a refactor rather than an interface. And the **service selection** itself is the user-facing deliverable of this phase: an unexplained product name in a design document is a decision nobody made.

**Deliberately absent:** anything cloud *to deploy into*. No Terraform, no manifests, no deploy job. Also no OpenSearch and no Neo4j — those are optional profiles that arrive with the phases that need them ([[§4.3]]). **Bedrock access is the exception and is required from Phase 0**, because there is no local model runtime at all ([[ADR-011]]); AWS credentials and a spend alert are Phase 0 setup, not later work.

**Exit criterion:** `docker compose up` brings the minimal stack to **healthy** with no manual steps; the **three CI gates pass on a real PR**; and a request traverses **gateway → orchestrator** with a **trace visible in the local trace backend**. If the trace is not visible, Phase 0 is not done — [[Phase 1]] prices everything off observability ([[P8]]).
