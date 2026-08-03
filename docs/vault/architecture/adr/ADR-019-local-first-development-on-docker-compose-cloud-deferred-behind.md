---
title: "ADR-019: Local-first development on Docker Compose; cloud deferred behind an explicit checkpoint"
type: adr
tags: [adr, local-first]
aliases: ["ADR-019"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T00:04:06+00:00
---

# ADR-019: Local-first development on Docker Compose; cloud deferred behind an explicit checkpoint

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** The platform runs on **Docker Compose on a developer machine**, and there is **no cloud deployment and no cloud CI** — but local development is **not cloud-free**. A deliberately small, explicitly named set of **real AWS services is consumed from local development**, because for those services a container substitute would be measuring the wrong thing. Everything else is a **pinned container image**.

> **Local development is a hybrid, and the expectation is set here rather than discovered later.** "Local-first" in this document means *we do not deploy to the cloud yet*. It does not mean *the stack has no cloud dependencies*. Running locally requires an AWS account, credentials, and a spend budget from day one.

| | Runs as a local container | Consumed as a real AWS service, locally |
| --- | --- | --- |
| **Container** | Object store, Postgres/pgvector, graph store, Redis, OPA, telemetry backend | — |
| **Real AWS, locally** | — | **IAM**, **Bedrock** ([[ADR-011]]), **Cognito**, **AgentCore Gateway**, **AgentCore Memory** (`USER_PREFERENCE` strategy only) — the closed set fixed by **[[ADR-020]]** |
| **Excluded** | — | **EKS and ECR** (cloud deployment — deferred to the [[§8]] checkpoint), **AgentCore Runtime** (it would own prompt assembly, against [[P1]]/[[P2]]/[[ADR-004]]) |

**Non-AWS external dependencies exist too, and they are deliberate.** The anchor use case calls **real third-party APIs** — Stripe Billing Entitlements and a real issue tracker — from local development. They are not AWS, so [[ADR-020]]'s closed set does not govern them, but the same honesty applies: local development depends on them, needs credentials for them, and does not work offline without recorded interactions. The reasoning is in the anchor use case: a stand-in cannot produce real rate limits, token expiry, pagination, or provider error taxonomies, so building against one means designing for conditions that never occur.

**The set is closed, and the test for reopening it is stated.** [[ADR-020]] fixes the five. Adding a sixth requires an ADR answering: **would a local substitute cause us to design against different behaviour, rather than merely different latency?** If yes, use the real service and pay for it. If no, use a container. Bedrock qualifies — a small local model is a *different thing*, not a smaller one. Cognito qualifies for a subtler reason: a managed AWS gateway cannot reach a discovery URL on a developer's laptop, so a local IdP would force local dev onto a different identity provider from every other environment. **Nothing is added without recording it**, because an unbounded set of cloud dependencies is cloud deployment arriving one service at a time without a decision. Kubernetes/EKS ([[ADR-018]]) is re-scoped from "the deployment target" to "the **eventual** deployment target, not yet active." Moving to cloud requires an explicit **cloud readiness checkpoint** ([[§8]]) to pass; until it does, the cloud design in [[§5]] is documentation, not infrastructure. The service-by-service selection, the local topology, and the three CI gates that are actually wired up are [[§4]].

**Context.** Cloud infrastructure is a large fixed cost paid *before* any of it is needed — a cluster to upgrade, IAM to debug, autoscalers to tune, spend accruing while the platform does nothing useful yet — and **none of it validates whether the architecture is right**. Every architectural decision in this document is about platform *shape*: layering ([[ADR-001]]), context engineering ([[ADR-004]], [[ADR-005]], [[ADR-006]]), skills ([[ADR-002b]]), retry scoping ([[§2.13]]), classification ([[ADR-013]]), storage tiering by access pattern ([[ADR-016]]). Not one of those is a statement about hosting, and not one of them is invalidated by running on one machine.

**Rationale.** A full stack on one machine gives a fast feedback loop and low infrastructure spend — **not zero: the real AWS services above are billed from day one** — and it still exercises the layer boundaries — Compose runs one container per layer, so the contracts in [[§3.1]] are crossed over a real network hop rather than in-process. Deferring is **not the same as being unprepared**: the cloud design already exists in [[§5]], so the eventual move is execution against a written design rather than design under deployment pressure.

**The portability rule that makes this cheap.** Stated prominently because everything else in this ADR depends on it:

> **Application code must never know which environment it is in.** Every backing service is reached through an interface whose concrete implementation is selected by **config**. Swapping MinIO for S3, or local Postgres for a managed one, is a **config change and never a code change**.

The specific portability seams, named so they are checkable in review:

| Seam | The rule | Why this specific seam |
| --- | --- | --- |
| Object storage | The **S3 API** — never a MinIO-specific client | The same calls address MinIO locally and S3 later |
| Vector + relational | **Standard Postgres + pgvector** — never a managed-only extension | The extension is byte-identical local and managed |
| Telemetry | **OpenTelemetry** — never a vendor SDK | The backend becomes swappable with no application change |
| Hot state | The **Redis protocol** — never a managed-cache-only feature | Identical protocol local and managed |
| Models | Provider-specific calls confined **behind the model proxy** | A model backend becomes a config entry |
| Secrets | A **resolver interface** — never a direct credential read from the environment | A local `.env` and a secrets manager are two implementations of one seam |

**Anything reachable only via one vendor's API is a migration cliff** and needs its own ADR recording the lock-in as deliberately accepted. Detail on Compose conventions and the seams lives in `.kiro/steering/local-development.md` and is not restated here.

**Consequences.**
- (+) **A fast iteration loop with most of the stack on one machine**, and no cluster, IAM surface, or autoscaler to operate.
- (−) **Not free, and not offline.** The named AWS dependencies bill from day one and require connectivity. Per-developer cost needs a budget and an alert rather than an assumption, and the set is capped by the test above precisely so this cost stays bounded.
- (−) **Two credential paths from day one** — a local `.env` for container services and real AWS credentials for the consumed services. Both go through the secrets resolver seam so there is one interface, but there are genuinely two backends now, and that is more surface for a local-only habit to leak into.
- (+) **Layer boundaries are still exercised** — one container per layer, real network hops, the [[§2.8]] startup ordering enforced by health checks.
- (+) **The cloud design is already done**, so the eventual move is execution rather than design.
- (−) **Several properties are not validatable locally** — object-store latency, sandbox isolation strength, autoscaling, network policy, IAM, multi-AZ, real multi-tenant load. They are enumerated in the gap table ([[§4.2]]) and **must be re-validated in cloud**. The honest cost of that deferral is recorded as a tradeoff in [[§7.11]].
- (−) **Compose is not Kubernetes**: no HPA, no PDB, no NetworkPolicy. The [[§5.7]] scaling model therefore remains a **design hypothesis until load-tested on a cluster**, and should be read that way everywhere it appears.
- (−) **Risk of local-only patterns leaking toward production**, most acutely in secrets handling. Mitigated by reading every secret through a **resolver interface from day one**, so the local `.env` and a real secrets manager are two implementations of one seam rather than two code paths.

**Alternatives considered.**
- **(a) Cloud from day one** — rejected. It pays the full fixed infrastructure cost before anything is learned, and the spend accrues against an architecture that has not yet been validated. Being cloud-ready on paper is worth more here than being cloud-deployed in fact.
- **(b) Local Kubernetes (kind / minikube / k3d)** — rejected **as the default**, but noted honestly as the natural intermediate step. It validates manifests, probes, and startup ordering with **no cloud spend**, and it is the **recommended first move if the checkpoint later identifies Kubernetes-specific behaviour as the blocker** (criterion 2 in [[§8]]). Compose is chosen now for a materially faster loop and lower cognitive overhead — a developer debugging prompt assembly should not also be debugging a local control plane.
- **(c) A managed dev environment (Codespaces-class, or a shared dev cluster)** — rejected. It costs money and adds a dependency on connectivity, and returns no architectural insight in exchange.
