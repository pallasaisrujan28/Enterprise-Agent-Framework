---
title: "Phase 4 — Orchestration maturity, sub-graphs, and context depth"
type: phase
tags: [phase, context-engineering, graph]
aliases: ["Phase 4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:08:18+00:00
---

# Phase 4 — Orchestration maturity, sub-graphs, and context depth

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Runs locally on Compose**, with model calls to Bedrock as in every other phase ([[ADR-011]]). Nothing in this phase needs a local model runtime any more — the self-hosted classifier work that used to live here was cut in [[ADR-013]].

**Ship:** the planner sub-agent owning `todo.md` with goal recitation at the tail; minimal-vs-full handoff by complexity; `submit_results` with constrained decoding including `REROUTE`; the read-only verifier node with escalation-below-threshold; the **sub-graph registry** with agent-as-tool invocation, independent prefixes and contexts, independent versioning and evals, and the enforced depth limit ([[§2.12]].1); collapse of legacy classifier and procedural nodes per the [[§6.3]] migration (most of them into **skills**); `skill_search` if the skill index has reached its ceiling; `tool_search` if the catalog has reached its prefix ceiling ([[§3.8]].3); full compaction tiers — structurally lossless trimming, async anchored summarization, and the agent-invoked `context_compact` tool — with all triggers from [[§2.10]], plus the **pre-compaction memory flush** ([[ADR-006c]]), the **silent-turn mechanism** it rides on ([[ADR-006d]]), the **mid-turn precheck that signals rather than compacting inline**, the **pluggable summarization provider with automatic built-in fallback**, and the strengthened overflow recovery that reads the provider's reported token count; bounded observation variation after the breakpoint; model routing by task type through the model proxy; the T2 archive as the eval and training corpus; the complete observability metric set ([[§5.6]]) with alarms; DeepEval full suite, red-team suite, chaos drills, and the CI cost gate.

**Exit criterion:** tool calls per task and tokens per task both drop measurably against the [[Phase 3]] baseline at equal or better eval scores; **re-route rate is measured** and classification cost is visible as a share of model spend (the two numbers that would justify ever restoring a self-hosted classifier — [[ADR-013]]); a sub-graph is invoked as a tool and a depth-limit violation is rejected at dispatch in a test; **a compaction cycle on a writable workspace is preceded by exactly one completed memory flush, the flush is invisible on both delivery paths, and a mid-turn pressure signal is recovered by the outer loop without any turn blocking on a summarizer**; a session survives an **orchestrator container kill** and resumes from the manifest (the same drill against a pod kill, a node drain, and a PDB is **post-checkpoint** — [[§4.2]]); the harness-quality test is run — swap in a stronger model, and if results do not improve, fix the harness before proceeding to [[Phase 5]].
