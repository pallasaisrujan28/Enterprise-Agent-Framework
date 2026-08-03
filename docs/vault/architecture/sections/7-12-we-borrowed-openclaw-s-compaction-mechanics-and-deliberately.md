---
title: "7.12 We borrowed OpenClaw's compaction mechanics and deliberately rejected its state topology"
type: section
tags: [section, compaction]
aliases: ["§7.12"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.12 We borrowed OpenClaw's compaction mechanics and deliberately rejected its state topology

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Recorded because the temptation to take the whole package is real, and taking the whole package would be a mistake that is hard to reverse.

[[ADR-006]]'s corrected mechanics, [[ADR-006c]], and [[ADR-006d]] are drawn from the [OpenClaw session-management and compaction internals](https://github.com/openclaw/openclaw/blob/main/docs/reference/session-management-compaction.md), and they are drawn on approvingly — compaction as an appended entry, the transcript as a tree, tool-call/result pairing, the pre-compaction memory flush, silent turns, the mid-turn signal. Those are mechanics, they are correct, and none of them assumes anything about where state lives.

**The state topology is a different matter and it does not transfer.** OpenClaw runs a **single Gateway process that owns all session state**, with per-agent local storage. For what it is — a self-hosted, single-user assistant — that is the right call: no coordination, no serialization protocol, no distributed state, and the failure domain is one person's tool. **For us it is wrong on two counts:** it is a single point of failure, and it does not partition by tenant. Multi-tenancy on shared infrastructure makes partitioning a correctness requirement that never expires ([[§7.7]]), and a process that owns all session state cannot be horizontally replicated without becoming the thing it was designed to avoid.

Our answer is the one already recorded: a **stateless orchestrator plus an externalized session manifest** ([[ADR-016]], [[§2.10]]). Any orchestrator can serve any turn, session state lives in T3 with the payloads in T1/T2, and an orchestrator dying mid-task costs a resume rather than a session ([[Property 21]]).

| | OpenClaw | This platform |
| --- | --- | --- |
| Session state owner | A single Gateway process | Externalized manifest in T3; orchestrator is stateless |
| Storage | Per-agent local | Tiered T0–T3, tenant-partitioned |
| Failure domain | The process — one user | One turn — resumable by any replica |
| Tenancy | Single user, no partitioning needed | Partitioning is a permanent correctness obligation ([[§7.7]], [[Property 1]]) |
| Correct for its context | **Yes** | — |

**The line to hold: their compaction *mechanics* transfer directly; their state *topology* does not.** This is written down because the OpenClaw model is genuinely simpler, and "why do we have four storage tiers and an external manifest when the reference implementation just keeps it in one process" is a reasonable-sounding question that a future reader will ask. The answer is tenancy and availability, and it is not negotiable while the platform is multi-tenant.

**What would change our mind:** nothing, as long as the platform is multi-tenant. If the product ever narrowed to a genuinely single-tenant self-hosted deployment, the OpenClaw topology would become the correct simplification, and this section is where to start that conversation rather than a code review.
---
