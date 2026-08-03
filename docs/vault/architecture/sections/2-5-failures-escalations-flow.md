---
title: "2.5 Failures & Escalations Flow"
type: section
tags: [section, failure-handling, scaling]
aliases: ["§2.5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# 2.5 Failures & Escalations Flow

Part of [[architecture|Architecture]].

```mermaid
flowchart TD
    T[Tool call / model call] --> C{Outcome}
    C -->|success| OK[Return result]
    C -->|wrong agent for this task| RR[REROUTE hint returned]
    RR --> CLS[Re-dispatch to the hinted agent type<br/>CLEAN context, decision + outcome logged]
    CLS --> OK

    C -->|transient or malformed-arg error| S1[SCOPE 1 - retry SAME step<br/>error kept VERBATIM in context]
    S1 -->|recovered| OK
    S1 --> LOOP{Same tool + same args<br/>+ same error x N?}
    LOOP -->|yes| BREAK[Break the loop - do not burn tokens]
    LOOP -->|no| S1
    S1 -->|step attempts exhausted| S2[SCOPE 2 - re-attempt TASK<br/>FRESH executor, CLEAN context window<br/>carries distilled FailureLesson only]
    BREAK --> S2
    S2 -->|recovered| OK
    S2 -->|task attempts exhausted| S3[SCOPE 3 - RE-PLAN<br/>planner gets failure SUMMARY, never raw trajectory]
    S3 -->|new approach| OK
    S3 -->|no viable approach| ESC[Escalate]

    C -->|pool unhealthy| CB{Circuit breaker state}
    CB -->|open| FB[Fallback: alternate replica / degraded tool / cached result]
    FB -->|available| OK
    FB -->|unavailable| ESC
    C -->|guardrail block| ESC
    ESC --> HITL[Human-in-the-loop]

    S1 -. full failure record .-> DUR[(Durable trajectory - T2<br/>evals, audit, RL)]
    S2 -. full failure record .-> DUR
    S3 -. full failure record .-> DUR
    OK -. span+status .-> TRACE[(Tracing)]
    ESC -. incident .-> TRACE
```

Key rules: retries are **scoped** ([[§2.13]]) — verbatim error for a same-step retry, a distilled lesson for a fresh task attempt, a summary for a re-plan; failures are **always** written to the durable trajectory regardless of scope; identical tool + identical arguments + identical error N times (default 3) **breaks the loop** rather than continuing to burn tokens; per-pool circuit breakers prevent cascading failure; a routing mistake is recovered by `REROUTE` rather than treated as a task failure; unrecoverable or policy-blocked cases escalate to HITL. Every outcome emits a span with status.
