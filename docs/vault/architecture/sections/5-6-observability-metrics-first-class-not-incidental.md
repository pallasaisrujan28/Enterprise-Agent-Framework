---
title: "5.6 Observability Metrics (first-class, not incidental)"
type: section
tags: [section, observability]
aliases: ["§5.6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# 5.6 Observability Metrics (first-class, not incidental)

Part of [[5-aws-deployment-evaluation|5. AWS Deployment & Evaluation]].

| Metric | Why it exists | Alarm shape |
| --- | --- | --- |
| KV-cache hit rate (per tenant, agent, artifact version) | North-star cost metric ([[P1]]) | Drop > 10 points vs 7-day baseline |
| Cache-read / cache-write / uncached token split | Detects paying the write premium without collecting the discount | Write share trending up |
| `prefix_hash` cardinality | Direct detector of cache-busting prefix mutation | More than a handful per artifact version |
| Cost and tokens per task | Unit economics; the number that decides tenant pricing | Per-tenant p95 breach |
| Tool calls per task | Detects loops, thrash, and bookkeeping waste | p95 above agent envelope |
| Skill index size (entries and prefix tokens, per agent) | An unbounded index is prefix bloat by another name ([[§7.9]]); the budget is ≈100 tokens of metadata per skill ([[ADR-002b]]) | Approaching the per-agent ceiling |
| Skill load rate and per-skill success rate | Which skills are actually used, and which are selected but do not help | A skill with high load rate and low success rate |
| Level-2 body vs Level-3 reference token cost, per skill | Distinguishes the two things that actually cost tokens from the one that does not (scripts). A skill whose references dominate is a candidate for a script | Reference cost exceeding body cost on a hot skill |
| Memory-flush rate, cost, and skip rate ([[ADR-006c]]) | A flush per compaction cycle is a real recurring cost; a high skip rate means read-only workspaces are more common than assumed | Flush cost share rising, or skip rate above a small baseline |
| Compaction entries per session and `tokens_before` distribution | Shows whether sessions compact once or repeatedly; repeated compaction near the threshold is a soft-threshold tuning signal | More than a couple of compactions per session at p95 |
| Mid-turn precheck signal rate ([[ADR-006]] rule 6) | Counts how often pressure is detected mid-turn rather than at turn start — a rising rate means tool results are bigger than the inline budget assumes | Sustained rise, especially on one tool |
| Overflow errors surviving recovery | The recovery path failing is the case where a user sees a hard failure. Also the detector for an unrecognized provider error phrasing | Any occurrence |
| Silent-turn delivery leaks | Should be structurally zero; a non-zero value means the streaming path is not checking the sentinel | Any occurrence — page it |
| Fork size cap activations ([[§2.12]].1) | How often the defensive cap overrides a `COMPLEX` flag. A high rate means planners are marking oversized branches complex, which is a planner problem the cap is masking | Sustained rise |
| Idle-expiry candidates vs actual expiries | Catches the freshness bug directly: if candidates never become expiries, something is extending `last_interaction_at` that should not be ([[Property 31]]) | Divergence between the two |
| Re-route rate ([[ADR-013]]) | **The only quality signal for routing**, now that there is no cascade to compare tiers against. A rising rate means the classification prompt or the agent-type taxonomy needs work | Sustained rise, or a step change after a prompt version promotion |
| Declared-intent share vs model-classified share | How often the free short-circuit applies. A falling share means more requests are paying for a classification call and a data egress | Sustained fall |
| Classification cost as a share of total model spend | The number that decides whether [[ADR-013]]'s rejected self-hosted classifier should be restored | Sustained rise |
| Retry scope distribution (step / task / re-plan) | Distinguishes "recovers in place" from "keeps starting over" | Task re-attempt share rising |
| Failure-loop detections | Direct measure of tokens saved from a known waste path | Any sustained rise on one tool |
| Retrieval accuracy per corpus (recall@k, MRR/nDCG, groundedness) | Knowledge quality is otherwise invisible until a tenant complains | Drop vs the labeled-set baseline |
| Sub-graph invocation depth distribution | Detects creeping nesting before it becomes a cost incident | Any depth-3 invocation |
| Escalation rate (HITL) | Autonomy trend; also a staffing input | Sustained rise |
| Guardrail trigger rate by rail | Both attack signal and false-positive signal | Spike either direction |
| Per-tenant spend and quota burn | Prevents one tenant starving others | Approaching quota |
| Breaker state per pool | Failure containment health | Any open breaker |
| Replica count and scaling events per tier | Detects autoscaler thrash in one direction and silent under-provisioning in the other; a tier pinned at `maxReplicas` is saturated, not healthy ([[§5.7]]) | Scale events per hour above baseline, or sustained time at `maxReplicas` |
| Node group utilization (per group) | Catches a runaway scale-out while it is still a graph and not yet a cost incident ([[§5.7]].3) | Approaching the provisioning limit on any group |
| Time-to-first-token | User-visible latency, moves with cache health | p95 regression |

> **Every token-count metric above is a runtime ESTIMATE, not a strict guarantee.** Occupancy shares, soft thresholds, `tokens_before`, and split targets are computed locally and drift from what a provider's tokenizer actually charges — by model, by content, and by tool-payload serialization. Alarm thresholds should be set with that slack in mind, and where a provider returns an observed count it overrides ours ([[ADR-006]] rule 7). Stating this plainly matters: a document that implies precision it does not have produces thresholds treated as exact, and then overflow errors that "should have been impossible."

Two of these are unusual enough to call out: `prefix_hash` cardinality is the cheapest possible early warning for the most expensive mistake in the system, and tool-calls-per-task is what caught the Manus team's observation that an executor was spending roughly a third of its actions on bookkeeping — the finding that justified moving todo management into a dedicated planner sub-agent ([[ADR-002]]).
