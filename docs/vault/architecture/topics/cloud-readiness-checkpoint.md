---
title: "Cloud Readiness Checkpoint"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# Cloud Readiness Checkpoint

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

A cross-phase gate, not a phase. It decides one question — *does the platform move off a developer machine yet* — and it is the only thing that activates [[ADR-018]], [[§5]], the cloud pipelines, and Terraform.

**Cadence: reviewed after every three features.** On delivery, not on a calendar. Three features is frequent enough that a genuine blocker never waits long, and infrequent enough that it does not become a standing agenda item nobody prepares for.

**The default answer is STAY LOCAL.** Stated plainly because the failure mode of a recurring checkpoint is that it becomes a countdown. **The checkpoint exists to catch the moment staying local stops being the right answer — not to build migration momentum.** A checkpoint that concludes "stay local" for the eighth time in a row is the checkpoint working correctly, not the checkpoint being useless. **"It feels like time" is explicitly not a criterion.**

**Trigger criteria — move only when something concrete is blocked.** Evaluate as a checklist. **Any one** being *genuinely* true justifies the move; none being true means the answer is stay local.

- [ ] **1. A single machine no longer suffices.** Memory, CPU, or disk exhausted by the **minimal** profile — not by running every optional profile at once, which is a profile-discipline problem rather than a capacity one.
- [ ] **2. A property only a cluster can validate is now on the critical path.** Autoscaling behaviour, network-policy isolation, IAM least-privilege, or multi-AZ behaviour — and *on the critical path*, meaning a committed deliverable depends on it, not that it would be interesting to know.
- [ ] **3. Data exists that must not be lost.** Local volumes are not a durability story. A named volume on one laptop has no backup, no replication, and no recovery objective.
- [ ] **4. Someone outside the development machine needs access.** A stakeholder demo, a second developer, or an integration partner. Sharing a laptop is not an access model.
- [ ] **5. A self-hosted model is required** — most likely the classifier [[ADR-013]] deferred, restored because a regulated tenant cannot send text to a provider or because classification cost became a measurable share of spend. Until that happens there is **no local inference at all** ([[ADR-011]]), so this criterion is currently inert rather than pending.
- [ ] **6. Real multi-tenant load or isolation testing is required** and cannot be simulated — concurrent tenant load, quota fairness, one tenant starving another.
- [ ] **7. Storage-tier latency assumptions must be measured** for a real cost model. [[ADR-016]]'s tiering is priced on latency characteristics that MinIO-on-local-disk cannot demonstrate ([[§4.2]]).

**Recommend local Kubernetes (kind / k3d) as the intermediate step when the blocker is specifically criterion 2.** It validates manifests, probes, resource requests, and startup ordering — the things [[ADR-018]] and [[§5.7]].5 actually assert — with **no cloud spend**, and it is strictly cheaper than standing up a cluster. Criterion 2 is the one trigger where the cheaper option genuinely resolves the blocker; the other six are not fixed by a local control plane.

**What changes when the checkpoint passes.** The migration is **execution, not design** — that is the whole return on having written [[§5]] up front:

1. **Stand up Terraform** for the cluster and every cloud resource ([[ADR-015]]). This is the first Terraform in the repository; there is deliberately none for local ([[§4.3]]).
2. **Swap config to managed service endpoints** — MinIO → S3, local Postgres → Aurora, Redis → ElastiCache, Jaeger → X-Ray or a self-hosted stack. **No application code change**, per [[ADR-019]]'s portability rule. If any of these turns out to require a code change, that is a portability-seam defect and it is fixed as one.
3. **Expand CI per the gate-growth table** ([[§4.4]]), including `terraform validate`, which earns its place here and only here.
4. **Add the dev and prod pipelines** with the manual approval gate and the canary ([[§5.5]], `.kiro/steering/git-workflow.md`).
5. **Re-validate every property in the [[§4.2]] gap table.** This is the non-negotiable item. Object-store latency, sandbox isolation strength, autoscaling behaviour, network-policy isolation, IAM, secrets handling, multi-AZ, and multi-tenant load all move from hypothesis to measured — or they get fixed.

**Each checkpoint produces a dated decision record.** The criteria evaluated, the outcome, and the reasoning — appended to this document or to the vault. Without the record, the same arguments get re-litigated from memory every three features, and a "no" from six months ago carries no weight because nobody can say why it was a no.

| Checkpoint | Date | Criteria met | Outcome | Reasoning |
| --- | --- | --- | --- | --- |
| _(none yet — the first is due after the third feature ships)_ | — | — | — | — |
