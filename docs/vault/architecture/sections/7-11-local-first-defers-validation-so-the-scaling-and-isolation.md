---
title: "7.11 Local-first defers validation, so the scaling and isolation designs stay unproven for longer"
type: section
tags: [section, local-first, scaling]
aliases: ["§7.11"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.11 Local-first defers validation, so the scaling and isolation designs stay unproven for longer

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

The honest cost of [[ADR-019]], stated as a cost rather than as a footnote to a benefit.

Running on Compose means the **scaling model in [[§5.7]] and the isolation boundary for model-authored code are hypotheses for as long as we stay local** — reasoned carefully from the workload shape, written down in detail, and **not measured**. Every per-tier saturation signal, every scale-down stabilization window, every claim about a default-deny network boundary, and every latency assumption underneath the [[ADR-016]] storage tiering is unvalidated. Cloud-from-day-one would have surfaced those problems earlier, and some of them will be genuinely unpleasant to discover late: an autoscaling signal that thrashes, a co-location assumption that does not hold, a latency profile that changes the cost model.

There is a second-order version of the same cost. **A design that is never executed drifts.** [[§5]] is maintained as prose while the rest of the platform moves, and prose does not fail a build. The longer the gap, the more likely some part of [[§5]] quietly stops matching what [[§2]] and [[§3]] have become.

**What we accept and how it is bounded:** the gap table in [[§4.2]] names every unvalidated property explicitly rather than letting them sit implicit; [[§5.7]] carries a hypothesis marker at the top so nobody reads it as measured; **re-validating the full gap table is a mandatory, non-negotiable item** at the checkpoint ([[§8]]); local Kubernetes is the recommended cheap intermediate step precisely when a cluster-only property lands on the critical path; and the portability seams ([[P16]]) are what keep the eventual move an execution exercise rather than a rewrite. None of that removes the risk — it makes the risk enumerated and scheduled, which is the most that can be honestly claimed.

**What would change our mind:** if the checkpoint criteria keep coming up "no" while unvalidated properties keep accumulating on the critical path, that is the signal that the checkpoint is measuring the wrong thing, and criterion 2 should be read more liberally rather than more strictly.
