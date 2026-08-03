---
title: "The Five-Layer Cumulative Stack"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:58:20+00:00
---

# The Five-Layer Cumulative Stack

Part of [[overview|Overview]].

Capability is added in this order, and each layer is only reached after the one below it is exhausted:

```mermaid
flowchart BT
    L1[1. Prompt - instruction quality]
    L2[2. Context - what the model can see]
    L3[3. Harness - tools, sandbox, memory, feedback]
    L4[4. Loop - agent chooses its own route to a goal + bar]
    L5[5. Graph - you declare valid paths and checks]
    L1 --> L2 --> L3 --> L4 --> L5
    style L5 stroke-dasharray: 5 5
```

The graph layer is the **outermost** layer and the **last** one to reach for ([[P9]]). Most scaling pain that looks like "we need a bigger graph" is actually a harness or context problem one or two layers down. A useful diagnostic from the Manus write-up: swap in a stronger model — if results do not improve, the bottleneck is the harness, not the model or the topology.
