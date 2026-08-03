---
title: "7.1 This layered topology is overkill at small scale"
type: section
tags: [section, scaling]
aliases: ["§7.1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.1 This layered topology is overkill at small scale

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Below roughly **5 tools, ~200 requests/second, and a single team**, the Gateway → Orchestrator → isolated pool topology costs more than it returns: more deploy units, more network hops, more failure surface, and more people-time than a single well-instrumented service.

**Kubernetes and per-tier autoscaling are part of what is overkill below that threshold**, and that is worth saying plainly now that Kubernetes is a recorded decision ([[ADR-018]]) rather than an implicit assumption. A cluster to upgrade, node groups to size, eight autoscaling configurations to tune and load-test, and PDBs and grace periods to get right ([[§5.7]]) is a real fixed cost that buys independent scaling, isolation, and rollback the small case does not need. At that scale a single well-instrumented service on a simpler runtime is the better answer, and [[ADR-018]]'s rejected alternatives — ECS, or plain VMs with a supervisor — are rejected *for this design at its target scale*, not universally.

**Local-first is precisely the response to this critique**, which is why this tradeoff now reads as resolved rather than as an unresolved tension in the document. [[ADR-019]] declines to pay that fixed cost until something concrete is blocked: the platform runs on Compose, the cluster is designed but unbuilt, and the checkpoint in [[§8]] is the mechanism that converts "we are past the threshold" from a feeling into a checklist. The layered *topology* is kept — one container per layer, so the boundaries stay real and the contracts stay exercised — while the *infrastructure* that the topology eventually wants is deferred. The critique was never that layering is wrong at small scale; it was that the operational surface is expensive. Not standing it up yet is the honest answer to that.

Two further honest caveats:

- **Tool execution time dominates routing overhead by one to two orders of magnitude.** Do not micro-optimize gateway hops before measuring where time actually goes. A 3 ms authorization check next to a 900 ms browser call is noise.
- The pieces that pay off *immediately at any scale* are the cheap ones: stable-prefix caching, restorable offload, trajectory capture, and the deterministic PII gate. Those are worth landing before any topology change.

**Where the layering does earn its cost:** multi-tenant isolation obligations, tool domains with genuinely different security and reliability profiles, more than one team shipping tools independently, and any requirement to prove what an agent was permitted to do.
