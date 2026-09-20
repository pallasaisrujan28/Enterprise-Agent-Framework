---
title: "ADR-019: Local-first development on Docker Compose; EKS only after the local stack proves a feature"
type: adr
tags: [adr, local-first]
aliases: ["ADR-019"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T00:04:06+00:00
revised: 2026-08-30
---

# ADR-019: Local-first development on Docker Compose; EKS only after the local stack proves a feature

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

> **Revised 2026-08-30.** The direction of this ADR has not changed and did not need to. What changed is that it is now **true**: the Compose stack it mandated exists, and the checkpoint that gates EKS is written down here with criteria that can be checked, instead of pointing at a section that listed none. The revision also records that the rule was broken — an EKS cluster was built and destroyed while this ADR was in force — because an ADR that quietly omits its own violation is a worse guide than one that admits it.

**Decision.** The platform runs on **Docker Compose on a developer machine**, and **EKS is not built until a feature has been demonstrated working on that local stack**. There is no cloud deployment and no cloud CI. Local development is **not cloud-free**: a deliberately small, explicitly named set of **real AWS services is consumed from local development**, because for those a container substitute would be measuring the wrong thing. Everything else is a **pinned container image**.

> **Local development is a hybrid, and the expectation is set here rather than discovered later.** "Local-first" in this document means *we do not deploy to the cloud yet*. It does not mean *the stack has no cloud dependencies*. Running locally requires an AWS account, credentials, and a spend budget from day one.

| | Runs as a local container | Consumed as a real AWS service, locally |
| --- | --- | --- |
| **Container** | Object store, vector store, search, Postgres/pgvector, graph store, Redis, OPA, telemetry backend | — |
| **Real AWS, locally** | — | **IAM**, **Bedrock** ([[ADR-011]]), **Cognito**, **AgentCore Gateway**, **AgentCore Memory** (`USER_PREFERENCE` strategy only) — the closed set fixed by **[[ADR-020]]** |
| **Excluded** | — | **EKS and ECR** (cloud deployment — deferred behind the checkpoint below), **AgentCore Runtime** (it would own prompt assembly, against [[P1]]/[[P2]]/[[ADR-004]]) |

## The checkpoint that activates EKS

Previously this ADR deferred to "the cloud readiness checkpoint ([[§8]])" without stating what the checkpoint was. That is the gap this revision closes, because a gate nobody can evaluate is not a gate — and in practice it was not one: a cluster got built anyway.

**EKS is built when, and not before, all four hold:**

1. **A user-visible feature works end to end against the local stack**, demonstrated by `make local-check` passing and by exercising the feature itself. Not "the code is written" and not "the container starts" — a request goes in and a correct answer comes out.
2. **The obligation gate is enforcing on that feature.** The gate is the reason this platform exists rather than a wrapper around a model, so a feature that bypasses it is not a feature that is ready to deploy.
3. **The local stack covers every backing service that feature touches.** A service reached only in cloud is a service whose failure modes are first seen in cloud.
4. **The reason for deploying is a property that cannot be observed locally** — and it is named. The list is short and known: object-store latency, sandbox isolation strength, autoscaling behaviour, NetworkPolicy, IAM boundaries, multi-AZ, real multi-tenant load ([[§4.2]]). "It feels more real in the cloud" is not one of them.

**Criterion 4 is the one that was violated.** A cluster was stood up, cost money, and was destroyed again without any of 1–3 being true, which meant it validated nothing that a laptop could not have. The recommended intermediate step, if criterion 4 ever *is* the blocker, remains **local Kubernetes** (kind/minikube/k3d) — it validates manifests, probes and startup ordering at zero cloud spend, and it is a strictly smaller step than EKS.

## What the local stack actually is

`docker-compose.yml` at the repository root, with `make local-up` / `make local-check`. It covers **only services some code actually reads**:

| Service | Serves | Cloud counterpart |
| --- | --- | --- |
| Qdrant | session working memory, `search_memory` | Qdrant in the `tools` namespace |
| SearXNG | `web_search` | SearXNG in the `tools` namespace |
| MinIO | agent workspace read/write | S3, over the same API |
| *(not a container)* | every model call | **Bedrock, in every environment** |

**Deliberately absent, and why.** The topology in [[§4.3]] also lists Postgres/pgvector, Redis, OPA, etcd and Jaeger. Nothing in the tree reads them today. Starting containers no code connects to is the same mistake as a CI gate for a component that does not exist: it manufactures confidence and trains people to ignore the stack. Each arrives with its consumer.

**One genuine gap, stated rather than hidden.** `fetch_and_store` and `crawl_site` call Firecrawl, whose self-hosted form is its own multi-service Compose project rather than one pinned image. Those two tools therefore **cannot be tested locally** without running Firecrawl's project alongside and pointing `FIRECRAWL_URL` at it. Until that is done, criterion 3 above is **not satisfied for any feature that fetches a page**.

**Context.** Cloud infrastructure is a large fixed cost paid *before* any of it is needed — a cluster to upgrade, IAM to debug, autoscalers to tune, spend accruing while the platform does nothing useful yet — and **none of it validates whether the architecture is right**. Every architectural decision in this document is about platform *shape*: layering ([[ADR-001]]), context engineering ([[ADR-004]], [[ADR-005]], [[ADR-006]]), skills ([[ADR-002b]]), retry scoping ([[§2.13]]), classification ([[ADR-013]]), storage tiering by access pattern ([[ADR-016]]). Not one of those is a statement about hosting, and not one of them is invalidated by running on one machine.

**Rationale.** A full stack on one machine gives a fast feedback loop and low infrastructure spend — **not zero: the real AWS services above are billed from day one** — and it still exercises the layer boundaries, because Compose runs one container per service and the contracts in [[§3.1]] are crossed over a real network hop rather than in-process. Deferring is **not the same as being unprepared**: the cloud design already exists in [[§5]], so the eventual move is execution against a written design rather than design under deployment pressure.

**The set of cloud dependencies is closed, and the test for reopening it is stated.** [[ADR-020]] fixes the five. Adding a sixth requires an ADR answering: **would a local substitute cause us to design against different behaviour, rather than merely different latency?** If yes, use the real service and pay for it. If no, use a container. Bedrock qualifies — a small local model is a *different thing*, not a smaller one, and prompt behaviour tuned against one would not transfer. Cognito qualifies for a subtler reason: a managed AWS gateway cannot reach a discovery URL on a developer's laptop, so a local IdP would force local dev onto a different identity provider from every other environment. **Nothing is added without recording it**, because an unbounded set of cloud dependencies is cloud deployment arriving one service at a time without a decision.

**Non-AWS external dependencies exist too, and they are deliberate.** The anchor use case calls **real third-party APIs** — Stripe Billing Entitlements and a real issue tracker — from local development. They are not AWS, so [[ADR-020]]'s closed set does not govern them, but the same honesty applies: local development depends on them, needs credentials for them, and does not work offline without recorded interactions. A stand-in cannot produce real rate limits, token expiry, pagination, or provider error taxonomies, so building against one means designing for conditions that never occur.

**The portability rule that makes this cheap.** Stated prominently because everything else in this ADR depends on it:

> **Application code must never know which environment it is in.** Every backing service is reached through an interface whose concrete implementation is selected by **config**. Swapping MinIO for S3, or local Postgres for a managed one, is a **config change and never a code change**.

The specific portability seams, named so they are checkable in review:

| Seam | The rule | Why this specific seam |
| --- | --- | --- |
| Object storage | The **S3 API** — never a MinIO-specific client | The same calls address MinIO locally and S3 later |
| Vector + relational | **Standard Postgres + pgvector**, and a vector store addressed by URL — never a managed-only extension | The extension is byte-identical local and managed |
| Telemetry | **OpenTelemetry** — never a vendor SDK | The backend becomes swappable with no application change |
| Hot state | The **Redis protocol** — never a managed-cache-only feature | Identical protocol local and managed |
| Models | Provider-specific calls confined **behind the model seam** (`agent/models/`) | A model backend becomes a config entry |
| Secrets | A **resolver interface** (`agent/config.py`) — never a direct credential read scattered through the code | A local `.env` and a secrets manager are two implementations of one seam |

**Two of those seams were aspirational until this revision, and are worth naming because a seam that does not work is worse than an absent one — it is a claim.** The object-storage seam was declared and then bypassed: `agent/filesystem/workspace.py` built a plain S3 client with no endpoint override, so it could only ever talk to real AWS and the local stack was unusable for workspace work. It now honours an endpoint and optional S3-scoped credentials, the latter because **boto3 has no per-service credential resolution** — one credential pair serves every client in a process, so Bedrock and MinIO otherwise fight and one of them always fails. The model seam likewise did not exist until `agent/models/` was written; before that, provider calls were made directly.

**Anything reachable only via one vendor's API is a migration cliff** and needs its own ADR recording the lock-in as deliberately accepted. Detail on Compose conventions lives in `.kiro/steering/local-development.md`.

**Consequences.**
- (+) **A fast iteration loop with most of the stack on one machine**, and no cluster, IAM surface, or autoscaler to operate.
- (+) **The gate is checkable.** `make local-check` makes the same call the application makes against each service, so "it works locally" is a command rather than an opinion. A container being *healthy* is not the same as a service *answering*: SearXNG runs perfectly while refusing JSON, which is precisely the failure the check catches.
- (−) **Not free, and not offline.** The named AWS dependencies bill from day one and require connectivity. Per-developer cost needs a budget and an alert rather than an assumption, and the set is capped by the test above precisely so this cost stays bounded.
- (−) **Two credential paths from day one** — a local `.env.local` for container services and real AWS credentials for the consumed services. Both go through the config seam so there is one interface, but there are genuinely two backends, and that is more surface for a local-only habit to leak into.
- (+) **Layer boundaries are still exercised** — real network hops, and the [[§2.8]] startup ordering enforced by `depends_on: { condition: service_healthy }`, so an ordering bug surfaces on a laptop instead of during a rollout.
- (+) **The cloud design is already done**, so the eventual move is execution rather than design.
- (−) **Several properties are not validatable locally** — object-store latency, sandbox isolation strength, autoscaling, network policy, IAM, multi-AZ, real multi-tenant load. They are enumerated in [[§4.2]] and **must be re-validated in cloud**; they are also the only legitimate reasons to trigger the checkpoint.
- (−) **Compose is not Kubernetes**: no HPA, no PDB, no NetworkPolicy. The [[§5.7]] scaling model therefore remains a **design hypothesis until load-tested on a cluster**, and should be read that way everywhere it appears.
- (−) **Page-fetching tools are not covered**, per the Firecrawl gap above.

**Alternatives considered.**
- **(a) Cloud from day one** — rejected, and the rejection has now been tested the expensive way. A cluster was built, billed, and destroyed without validating anything a laptop could not. Being cloud-ready on paper is worth more here than being cloud-deployed in fact.
- **(b) Local Kubernetes (kind / minikube / k3d)** — rejected **as the default**, but noted honestly as the natural intermediate step and the **recommended first move if the checkpoint's criterion 4 is ever the genuine blocker**. Compose is chosen now for a materially faster loop: a developer debugging prompt assembly should not also be debugging a local control plane.
- **(c) A managed dev environment (Codespaces-class, or a shared dev cluster)** — rejected. It costs money and adds a dependency on connectivity, and returns no architectural insight in exchange.
- **(d) Mocking Bedrock locally to remove the last cloud dependency** — rejected, and this is the one people keep proposing. A local stand-in model produces different text, different latency, different tool-calling behaviour and different refusals. Every prompt and every obligation would be tuned against behaviour that does not exist upstream, which is worse than paying for the real thing. `AGENT_PROVIDER=echo` exists for UI work with zero spend and is deliberately incapable of being mistaken for a model.
