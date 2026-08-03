---
title: "2.13 Retry, Recovery, and Failure Scoping"
type: section
tags: [section, failure-handling]
aliases: ["§2.13"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 2.13 Retry, Recovery, and Failure Scoping

Part of [[architecture|Architecture]].

The original version of this design said "keep errors in context ([[P6]])" and left it there. That conflated three different scopes and, at two of them, it was **wrong** — carrying accumulated failed trajectories into a fresh attempt poisons the attempt. The corrected model separates the scopes explicitly.

| Scope | Trigger | Context carried forward | Why |
| --- | --- | --- | --- |
| **1 — Retry the same step** | Malformed argument, transient error, schema violation | **The error, VERBATIM** | The model needs the exact failure text to correct the call. A summarized "it failed" is useless here. This is the scope where "keep errors in context" is exactly right. |
| **2 — Re-attempt the task** | Repeated step failure; the step-level retries are exhausted or the loop detector fired | **A FRESH executor with a CLEAN context window, carrying only a distilled `FailureLesson`** — e.g. *"a previous attempt failed because the policy ID format was wrong; do not repeat that"* | Accumulated failed trajectories crowd out the task, bias the model toward the failed approach, and cost tokens for negative value. The lesson is the signal; the wreckage is noise. |
| **3 — Re-plan** | Task attempts exhausted, or the failure indicates the plan itself is wrong | **A failure SUMMARY, never the raw failed trajectory** | The planner is deciding on a different approach. It needs the shape of what went wrong, not the transcript. |

**The corrected invariant, stated plainly:**

> **Failures are ALWAYS preserved in the durable trajectory record — for evals, audit, and RL. What is carried into a RETRY CONTEXT is a distilled lesson, not accumulated wreckage.**

These are two different questions that the original [[P6]] answered as one. Durability is non-negotiable and total (nothing is swallowed, [[Property 12]]). Context inclusion is scoped, and at scope 2 the right amount of failed trajectory in the new context is **none of it, plus one lesson**.

**Failure-loop detection.** Without it, scope-1 retries can spin: the model re-emits the same call, gets the same error, and reasons about it again. The detector is deliberately simple and deterministic:

```pascal
PROCEDURE detect_failure_loop(recent_failures, threshold)
  INPUT:  recent_failures (ordered list of (tool_name, canonical_args, error_class))
          threshold (default 3)
  OUTPUT: LoopDetected | NoLoop

  SEQUENCE
    IF length(recent_failures) < threshold THEN RETURN NoLoop END IF

    window ← last(recent_failures, threshold)
    first  ← window[0]

    // Identical tool + identical canonicalized arguments + identical error class
    FOR each f IN window DO
      IF f.tool_name ≠ first.tool_name THEN RETURN NoLoop END IF
      IF f.canonical_args ≠ first.canonical_args THEN RETURN NoLoop END IF
      IF f.error_class ≠ first.error_class THEN RETURN NoLoop END IF
    END FOR

    RETURN LoopDetected(first)        // break the loop; escalate to scope 2
  END SEQUENCE
END PROCEDURE
```

**Preconditions.** `recent_failures` are from one executor attempt, ordered oldest to newest; arguments are canonicalized with deterministic key ordering ([[P2]]) so semantically identical calls compare equal.
**Postconditions.** `LoopDetected` iff the last `threshold` failures are identical in tool, canonical arguments, and error class. On detection the step-retry scope is abandoned and control escalates to scope 2 — it does not continue spending tokens on a call that has failed identically three times.
**Loop invariant.** While scanning the window, every failure inspected so far matched `first` on all three fields; the first mismatch returns `NoLoop` immediately.

`threshold` is configurable per agent but has a hard ceiling, because "retry until the budget cap" is not a recovery strategy. Loop detection is [[Property 22]].

**How scope 2 is built.** A scope-2 re-attempt is a genuinely new executor: new context window, same goal, same tools, plus one `FailureLesson` ([[§3.1]].9) appended to the volatile tail. The failed attempt's full trajectory remains addressable in T2 via `FailureLesson.failed_trajectory_ref`, so an eval or a human debugging the case loses nothing — but the retrying model does not read it, which is the point.
---
