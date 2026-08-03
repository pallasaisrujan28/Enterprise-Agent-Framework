---
title: "2.4 Human-in-the-Loop Flow"
type: section
tags: [section]
aliases: ["§2.4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 2.4 Human-in-the-Loop Flow

Part of [[architecture|Architecture]].

```mermaid
flowchart TD
    S[Candidate response / action] --> C1{Trigger?}
    C1 -->|low confidence| H[Enqueue for human review]
    C1 -->|policy-sensitive action| H
    C1 -->|guardrail flag| H
    C1 -->|explicit approval gate| H
    C1 -->|none| AUTO[Proceed automatically]

    H --> Q[(Review Queue - tenant-scoped)]
    Q --> R{Human decision}
    R -->|approve| AUTO
    R -->|edit| E[Apply edited response/action]
    R -->|reject| X[Block + log reason]
    E --> AUTO
    AUTO --> OUT[Deliver / execute]
    X --> OUT
    H -. logged .-> TRAJ[(Trajectory Log)]
    R -. logged .-> TRAJ
```

HITL triggers: low model confidence, policy-sensitive/irreversible actions (e.g., writes via `db_*`/`file_*` to production resources), guardrail flags, or an explicit approval gate configured per tenant/agent. All decisions are recorded in the trajectory for audit and RL.
