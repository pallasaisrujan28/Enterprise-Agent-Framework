---
title: "2.9 Continuous Improvement Flow (Track A / Track B)"
type: section
tags: [section, improvement-layer]
aliases: ["§2.9"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 2.9 Continuous Improvement Flow (Track A / Track B)

Part of [[architecture|Architecture]].

```mermaid
flowchart TD
    PROD[Production traffic] --> TRAJ[(Trajectory store<br/>LLM calls, tool calls, tokens, outcomes)]
    TRAJ --> CUR[Curate: failures, escalations, HITL edits, guardrail trips]
    CUR --> DS[(Eval datasets<br/>incl. injected-failure scenarios)]

    DS --> B1[Track B: reflective prompt evolution<br/>GEPA over DSPy]
    B1 --> B2{Beats baseline on held-out set<br/>by threshold?}
    B2 -->|no| B3[Discard candidate + record why]
    B2 -->|yes| B4[Promote to canary - limited traffic]
    B4 --> B5{Canary healthy?}
    B5 -->|no| B6[Pointer rollback to prior version]
    B5 -->|yes| B7[Promote artifact version to prod]

    DS --> A1[Track A: narrow sub-policy candidate<br/>high volume + verifiable reward]
    A1 --> A2{ROI provable and Track B plateaued?}
    A2 -->|no| A3[Stay on Track B]
    A2 -->|yes| A4[RFT/RLVR via Agent Lightning<br/>checklist rewards]
    A4 --> A5[Same eval gate + canary as Track B]
    A5 --> B7

    B7 --> PROD
    style A4 stroke-dasharray: 5 5
```

Nothing reaches production without clearing the same gate, whether it came from reflective optimization or weight training ([[P10]]).

The Track B loop above is the platform-level view. The **agent-level** version — the reference tuning loop as given, the three additions it needed (canary plus rollback, a human gate, a production feedback edge) and the two constraints on its gate (cost criteria, and no live prefix write) — is **ADR-008a**, with the full analysis at [`docs/vault/architecture/agent-tuning-loop.md`](../../../docs/vault/architecture/agent-tuning-loop.md).
