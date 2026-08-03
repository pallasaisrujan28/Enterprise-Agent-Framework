---
title: "Error Handling"
type: hub
tags: [hub]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Error Handling

Flows are in [[§2.5]] (retry → breaker → fallback → escalate) and [[§2.8]] (operational failure modes). This is the taxonomy and the committed policy per class.

| Class | Examples | Retry | Terminal behaviour |
| --- | --- | --- | --- |
| `AUTH_DENIED` | Bad token, unknown agent, explicit policy deny | Never | `4xx` + audit event; no model call is made |
| `QUOTA_EXCEEDED` | Rate limit, token budget, per-task call cap | Never (client backs off) | `429` with retry hint; partial results preserved in trajectory |
| `GUARDRAIL_BLOCK` | Jailbreak detected, output moderation fail, ungrounded answer | Once with corrective instruction, then stop | Escalate to HITL or return a safe refusal; violation logged |
| `TOOL_TRANSIENT` | Timeout, 5xx from a pool replica, connection reset | Scope 1: capped, jittered exponential backoff, error verbatim in context | Breaker opens for the pool; on exhaustion escalate to scope 2 (fresh executor, distilled lesson), then scope 3 (re-plan) |
| `TOOL_PERMANENT` | Invalid arguments, unsupported operation, 4xx from target system | Scope 1 once with the error **verbatim** so the agent can correct the call; never a blind repeat | If the corrected call fails the same way, the loop detector fires and escalates to scope 2 |
| `FAILURE_LOOP` | Identical tool + identical canonical arguments + identical error class N times (default 3) | No further step retries — the loop is broken deliberately | Escalate to scope 2 with `root_cause_class = LOOP_DETECTED`; the wasted-token path is closed ([[Property 22]]) |
| `WRONG_ROUTE` | Executor determines it is the wrong agent for this task | Not a retry — a re-dispatch | `SubAgentResult.status = REROUTE` with a hint; the cascade re-dispatches with a **clean** context and logs the outcome as a training label ([[ADR-013]]) |
| `SUBGRAPH_DEPTH_EXCEEDED` | A sub-graph invocation would exceed the depth limit | Never | Rejected at dispatch before any model call; surfaced to the caller as a tool error ([[Property 24]]) |
| `CIRCUIT_OPEN` | Pool unhealthy | No call attempted | Fallback: alternate pool, degraded tool, or cached result; else escalate |
| `CONTEXT_PRESSURE` | The mid-turn precheck finds the prompt no longer fits after a tool result was appended | Not a retry — a **structured signal**. The prompt submission stops and the **outer run loop** recovers: truncate oversized tool results if that suffices, else compact and retry the turn | Never compacted inline, so no turn blocks on a summarizer ([[ADR-006]] rule 6) |
| `MODEL_ERROR` | Provider 5xx, context overflow, content filter | Retry on 5xx. On overflow — recognized as an **error family**, not one vendor's wording — trigger compaction and retry once, **forwarding the provider's reported attempted token count** when there is one, or a **minimally over-budget synthetic count** when overflow is confirmed but no count is parseable | Route to fallback model in the allowlist; else escalate. If overflow recovery still fails: **surface explicit guidance and preserve the session mapping — never silently rotate to a fresh session** ([[ADR-006]] rule 7) |
| `FORK_REFUSED` | A sub-graph spawn or scope-2 branch is requested while the parent has an active run | Never — the parent state is indeterminate mid-run | Rejected at dispatch; the caller waits for the parent run to settle ([[ADR-006]] rule 4, [[Property 30]]) |
| `SUMMARIZER_UNAVAILABLE` | A pluggable compaction provider fails or returns empty | Not retried against the same provider | **Automatic fallback to built-in summarization**, recorded as `fell_back_to_builtin`. Genuine abort/timeout signals are **re-thrown, never swallowed**, so cancellation is always respected ([[ADR-006]] rule 8) |
| `POLICY_UNAVAILABLE` | PDP unreachable and no valid cached decision | No | **Fail closed** — deny |
| `STATE_CONFLICT` | Concurrent session write, lock contention | Retry with backoff on lock acquisition | Abort the turn rather than write interleaved history |
| `INTERNAL` | Unhandled defect | No | `5xx`, full trace retained, alarm raised |

Four rules govern all classes: every failure is **durably recorded** and never swallowed ([[P6]]); what enters a **retry context** is scoped — verbatim at scope 1, a distilled lesson at scope 2, a summary at scope 3 ([[§2.13]]); every terminal outcome emits a span with status plus a `TrajectoryRecord` outcome; and no error path is allowed to leak raw PII into a message or log.
