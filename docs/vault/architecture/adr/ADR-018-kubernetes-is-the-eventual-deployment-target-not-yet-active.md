---
title: "ADR-018: Kubernetes is the eventual deployment target (not yet active)"
type: adr
tags: [adr, deployment]
aliases: ["ADR-018"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-018: Kubernetes is the eventual deployment target (not yet active)

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

> **Re-scoped by [[ADR-019]].** Kubernetes is the **eventual** deployment target, **not yet active**. The platform currently runs on Docker Compose on a developer machine ([[ADR-019]]), and nothing below is built. Everything in this ADR remains the decided shape of the eventual cloud deployment — the rationale, the consequences, and the rejected alternatives all still hold. What changed is *when*, not *what*. The move is gated by the cloud readiness checkpoint ([[§8]]).

**Decision.** Every component of this platform ships as a **container**, and the **eventual** deployment target for those containers is **Kubernetes**, with **Amazon EKS** as the managed control plane. **One namespace per architectural layer** (gateway, orchestrator, executors, mcp, and one per tool-pool domain), each a network and policy boundary rather than a naming convention. **Terraform owns the cluster and the lifecycle of every cloud resource** ([[ADR-015]]); application manifests never provision infrastructure. **Helm** packages the workloads. Scaling architecture is [[§5.7]]. **None of this is active** — see [[ADR-019]] for the current runtime and the checkpoint that activates this one.

**Context.** EKS was mentioned incidentally in [[§5.1]] from the first draft but was never actually *decided* anywhere, which meant the most consequential infrastructure commitment in the document had no recorded rationale and no rejected alternatives. That is now fixed, because the choice is load-bearing rather than incidental.

The platform has tiers with **genuinely different scaling profiles and genuinely different blast-radius requirements** ([[ADR-001]], [[ADR-003]]): a stateless gateway that scales on request rate, an orchestrator that scales on in-flight turns, tool pools whose resource profiles differ by an order of magnitude between domains, and a **sandbox tier that executes model-authored code** and must be isolated more strongly than an ordinary workload. It also needs per-pool deployment and rollback that do not touch neighbouring pools. Namespaces, network policies, per-deployment autoscaling, and pod disruption budgets are precisely the primitives that problem shape calls for.

**Rationale.** The layered topology in this document is only real if the layers can **scale, fail, and deploy independently**. Kubernetes supplies exactly those: per-tier horizontal scaling, per-namespace network isolation, per-workload identity (ServiceAccount → least-privilege IAM), declarative rollout and rollback, and a mature autoscaling story (HPA for metric-driven pod scaling, KEDA where the signal is a queue or event stream, Cluster Autoscaler or Karpenter for node capacity). It also supplies the **strong-isolation escape hatch** the sandbox tier needs — gVisor- or Firecracker-backed node groups — without a separate execution platform bolted onto the side.

**Consequences.**
- (+) Independent scaling and independent deployment per tier and per tool pool, which is what [[ADR-001]] and [[ADR-003]] assume rather than merely hope for.
- (+) Real network isolation as a **policy boundary** — default-deny per namespace with an explicit egress allowlist, so "the `db` pool cannot reach the internet" is enforced rather than documented.
- (+) Declarative rollout and rollback; a bad deploy is reverted by reconciling to the previous manifest, mirroring the pointer-rollback property artifacts already have ([[ADR-014]]).
- (+) Portable across clouds if a tenant contract or a regional obligation ever requires it, because the workloads are containers and the cloud coupling is confined to Terraform.
- (−) **Substantial operational surface.** Cluster upgrades, autoscaler tuning, node-group lifecycle, and network-policy debugging are real ongoing work, and they require a team that owns infrastructure. This is the single largest fixed cost the design takes on.
- (−) **Kubernetes autoscaling defaults are wrong for LLM-bound workloads.** CPU is nearly meaningless as a saturation signal when a pod spends its time waiting on a model provider or a tool call, so scaling metrics have to be chosen deliberately per tier rather than inherited from the default HPA template ([[§5.7]].2).
- (−) **Overkill below the scale threshold in [[§7.1]].** Stated plainly: a single team with a handful of tools and modest traffic gets less from this than it pays for, and the honest recommendation there is a single well-instrumented service. [[§7.1]] records that consistently now that Kubernetes is a decision rather than an assumption.

**Alternatives considered.**
- **Serverless (Lambda, or Fargate-only)** — rejected. Agent turns are long-running and hold in-flight tool calls for tens of seconds; the sandbox tier needs **persistent local NVMe scratch** for T0 ([[ADR-016]]), which a function runtime does not offer; and cold starts plus execution-duration ceilings fight directly against long-horizon tasks. The economics are attractive for spiky short work, which is not the workload here.
- **ECS** — rejected, though it is genuinely workable and the closest call of the four. It gives weaker per-namespace policy isolation and a less mature autoscaling and policy ecosystem than the per-pool isolation this design leans on, and the isolation story for model-authored code execution is thinner.
- **Plain VMs with a process supervisor** — rejected. It loses rolling deploys, self-healing, and declarative rollback, all of which this design depends on. The gateway/orchestrator/registry/pool pattern is orchestrator-agnostic in principle, but re-implementing scheduling, health management, and rollout primitives to get there is not a good trade.
- **A managed agent platform** — rejected. The context-engineering control this entire design rests on — stable prefix assembly ([[ADR-004]]), tool masking rather than mutation ([[ADR-005]]), tiered session storage ([[ADR-016]]) — requires **owning the harness**. A platform that assembles the prompt for you takes [[P1]] and [[P2]] out of our hands.
