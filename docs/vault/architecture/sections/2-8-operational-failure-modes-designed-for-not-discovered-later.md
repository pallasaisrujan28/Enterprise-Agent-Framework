---
title: "2.8 Operational Failure Modes (designed-for, not discovered later)"
type: section
tags: [section, failure-handling]
aliases: ["§2.8"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 2.8 Operational Failure Modes (designed-for, not discovered later)

Part of [[architecture|Architecture]].

These are the failure modes this topology is known to produce. Each has a committed mitigation.

| Failure mode | Symptom | Mitigation |
| --- | --- | --- |
| Tool pool crash loop | Pool replicas restart repeatedly; tool family unavailable | Explicit memory limits, `terminationGracePeriodSeconds` 20–30s so in-flight calls drain, backoff on restart, breaker opens rather than retry-storming |
| Circuit breaker avalanche | One pool's failure cascades as all callers retry in lockstep | Jittered exponential backoff, per-pool breakers (never one global breaker), half-open probe after cooldown |
| Registration storm | After a registry leader election, every pool re-registers simultaneously | Client-side jitter of 1–5s on registration and re-watch |
| Session state corruption | Concurrent tool results write the same session key; history interleaves | Distributed lock or transactional/CAS write per `tenant_id:session_id`; append-only history makes conflicts detectable |
| In-flight session loss on backup/restore | Sessions mid-task vanish or replay incorrectly | Treat session cache as recoverable-but-not-authoritative; the trajectory log is the durable record and can rehydrate a session |
| Cold registry on startup | Orchestrator serves traffic before `tool → pool` is loaded and every call 404s | Readiness probe must confirm the registry loaded; liveness only checks the process. Start order: registry → orchestrator → pools → gateway |
| Cache-busting regression | Costs jump with no traffic change | `prefix_hash` cardinality alert per `(tenant, agent, artifact_version)`; a new hash per request is a defect |
| Prompt-artifact regression | Quality drops after an automated Track B promotion | Eval-gated promotion, canary traffic, pointer rollback ([[ADR-014]]) |
| Ingestion config points at a nonexistent or wrong index | Sync job writes nowhere, or into the wrong tenant's index | Typed config validation at load asserts the target index **exists** (Terraform created it) and is partition-scoped; a post-sync smoke retrieval runs before the strategy version is promoted ([[§3.6]]) |
| Retrieval strategy regression | A code change to retrieval quietly lowers answer quality | Retrieval accuracy harness (recall@k, MRR/nDCG, groundedness) as a CI regression gate ([[§3.6]], [[§5.5]]); strategy is an artifact, rolled back by pointer |
| Failure loop | Agent repeats the same tool with the same arguments and gets the same error, burning tokens until a budget cap | Loop detector: identical `(tool, canonical_args, error_class)` N times (default 3) breaks the loop and escalates the retry scope ([[§2.13]], [[Property 22]]) |
| Retry context poisoning | Quality degrades across attempts because failed trajectories accumulated in context | Scope 2 re-attempts spawn a **fresh executor with a clean window** carrying only a `FailureLesson`; the full trajectory stays in T2 ([[§2.13]], [[Property 23]]) |
| Skill index bloat | Prefix grows silently as skills are added; cache economics degrade | Hard one-line description budget per skill and a per-agent skill-count ceiling, both enforced at validation; past the ceiling, `skill_search` replaces the flat index ([[ADR-002b]], [[Property 25]]) |
| Bad skill promoted | A skill loads but produces wrong behaviour | Skill eval cases are mandatory and gate promotion ([[§5.5]]); a skill is canaried and rolled back by pointer like any artifact |
| Sub-graph recursion | Nested sub-graph invocation blows up token spend | Depth counter in the handoff contract, hard limit 2 (3 only with sign-off), enforced at dispatch ([[§2.12]], [[Property 24]]) |
| Sandbox loss mid-task (T0 gone) | Agent references a path that no longer exists | Offload to T1 is synchronous with respect to referenceability ([[Property 20]]); manifest resolution falls back to T1/T2, never to a bare T0 path |
| Redis eviction of a session manifest | Session appears to vanish between turns | Manifest is rebuildable from T2 trajectory records; eviction policy excludes manifest keys; resume path is tested ([[Property 21]]) |
| Autoscaler thrash | Pods scale up and down repeatedly during bursty agent traffic; cost and tail latency both worsen | Generous scale-down stabilization windows; concurrency- or queue-depth signals instead of CPU ([[§5.7]].2); the autoscaling configuration is load-tested before it is trusted ([[§5.7]], Testing Strategy) |
| In-flight session killed by a rollout | Sessions fail during a deploy or a node drain | Drain-before-kill via a `preStop` hook that deregisters first, `terminationGracePeriodSeconds` sized to the longest expected tool call, `maxUnavailable: 0` on request-path rolling updates, and a PodDisruptionBudget per tier ([[§5.7]].4) |
