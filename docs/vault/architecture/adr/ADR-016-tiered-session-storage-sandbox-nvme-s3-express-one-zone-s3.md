---
title: "ADR-016: Tiered session storage — sandbox NVMe, S3 Express One Zone, S3 Standard, Redis"
type: adr
tags: [adr, retrieval, storage, session-state]
aliases: ["ADR-016"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-016: Tiered session storage — sandbox NVMe, S3 Express One Zone, S3 Standard, Redis

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** The per-session agent filesystem is **four tiers with distinct jobs**, not one store:

| Tier | Technology | Semantics | Job | Lifetime |
| --- | --- | --- | --- | --- |
| T0 — scratch | Sandbox-local NVMe instance store | Full POSIX (`ls`, `grep`, `glob`, `cat`, `sed`) | Working set the agent reads/writes while running code or shell | Session, ephemeral |
| T1 — session artifacts | S3 Express One Zone | Object, single-digit-ms, single-AZ | Durable store for offloaded tool outputs and handoff artifacts read many times within a session | Session + short tail |
| T2 — trajectory archive | S3 Standard | Object, cheap, multi-AZ | Replay, evals, Track B/C training data, audit | Retention-bounded (months) |
| T3 — hot state | ElastiCache Redis | Key/value + structures | Session manifest, plan/`todo.md` pointer, budgets, locks, breaker state | Session, evictable |

Promotion is one-directional and explicit: an agent writes to T0, the offload path copies to T1 and records a `Reference` ([[ADR-006]]), and the trajectory writer lands the durable record in T2. T3 holds the **manifest** — the index of what exists in T0/T1 for this session — never the payloads.

**Local mapping ([[ADR-019]]).** The **tier boundaries are what this ADR decides**, and they hold in both environments; only the backing service differs. Locally: T0 is a sandbox container volume, T1 and T2 are both **MinIO** buckets behind the S3 API, and T3 is the **Redis** container. **The one thing that does not carry over is latency.** MinIO on a local disk has a completely different profile from a managed low-latency tier, so **T1's single-digit-ms characterization and the cost model built on it are unverified until measured in cloud** ([[§4.1]], [[§4.2]]). The single-AZ tradeoff below has no local analogue at all.

**Context.** Context engineering was the highest-priority requirement, and the concrete need is that tool outputs go to a *filesystem the agent can navigate with ordinary shell tools*, while the platform still needs durability across orchestrator restarts and a durable trajectory record for evaluation. One store cannot do all three: POSIX semantics, single-digit-ms shared durability, and cheap long retention are different products.

**Rationale.** Splitting by access pattern is what keeps this cheap. T0 gives the agent real `grep`/`glob` over a real filesystem, which is the thing that makes filesystem-as-context work at all — a retrieval ranker cannot substitute for exact-path addressing ([[P11]]). T1 gives cross-restart durability at latency low enough to sit on the agent's critical path. T2 is priced for volume, and it is the tier both improvement tracks read from. T3 is what makes the orchestrator genuinely stateless: because the session manifest lives in Redis rather than in orchestrator memory, an orchestrator pod can be killed mid-task and a replacement pod resumes from the manifest plus T1/T2 ([[§2.8]]).

**Single-AZ is a deliberate acceptance, not an oversight.** T1's single-AZ durability profile is acceptable *because* T1 is session-scoped and the authoritative record is T2. A lost AZ costs in-flight sessions, which are recoverable by replay from T2, not customer data.

**Consequences.**
- (+) Agent-visible POSIX semantics without paying network-filesystem latency on every `cat`.
- (+) Orchestrator restarts do not drop sessions; the manifest is external.
- (+) The archive tier doubles as the eval and RL corpus, so observability spend is not duplicated.
- (−) Four tiers means a promotion path to get right, and a `Reference` must encode its tier so resolution is unambiguous.
- (−) T0 is ephemeral by construction: anything not promoted to T1 before the sandbox dies is gone. The offload path must be synchronous with respect to the artifact becoming referenceable.

**Alternatives considered and rejected.**
- **A single stateful process owning all session state, with per-agent local storage** — rejected, and worth naming explicitly because it is the topology of a well-regarded reference implementation whose *compaction mechanics* this design adopts wholesale ([[ADR-006]], [[ADR-006c]], [[ADR-006d]]). It is a single point of failure and it does not partition by tenant. See **[[§7.12]]** for the full reasoning; it is recorded there so a future reader does not "simplify" toward it.
- **Amazon EFS as the session filesystem** — rejected. It offers POSIX across nodes, but at meaningfully higher per-operation latency than local NVMe, and the POSIX requirement is already satisfied by T0 where the agent actually runs. Paying network-filesystem latency for every `ls` in an agent loop is the wrong trade, and EFS's cross-AZ durability is a property T2 already provides more cheaply.
- **FSx for Lustre** — rejected. It is built for high-throughput parallel HPC and ML training I/O. Session scratch for an agent is small-file, low-concurrency, bursty, and short-lived — the opposite of the profile Lustre is priced and tuned for. It would be both overkill and mispriced.
- **Everything in S3 Standard** — rejected. Latency is wrong for in-loop reads, and it provides no POSIX surface.
- **Everything in Redis** — rejected. Artifacts are large and binary; using a memory-priced store as an object store is the most expensive possible mistake here.
- **Sandbox NVMe only** — rejected. No durability across restarts, no trajectory record, so no evals and no RL corpus.
