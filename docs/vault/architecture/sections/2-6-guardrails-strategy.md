---
title: "2.6 Guardrails Strategy"
type: section
tags: [section, guardrails]
aliases: ["§2.6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 2.6 Guardrails Strategy

Part of [[architecture|Architecture]].

```mermaid
flowchart LR
    subgraph IN[Input Rails - pre-LLM, at Gateway]
        I1[PII detection + redaction - Presidio/GLiNER]
        I2[Jailbreak / prompt-injection detection]
        I3[Topic / policy checks - Colang]
    end
    subgraph RET[Retrieved-content Rails]
        R1[Scan RAG/GraphRAG results for PII]
        R2[Grounding / source trust check]
    end
    subgraph OUT[Output Rails - post-LLM, at Orchestrator]
        O1[Moderation]
        O2[PII scan of generated text]
        O3[RAG grounding / hallucination check]
    end
    USERIN[User input] --> IN --> LLM[LLM / Sub-agent]
    RET --> LLM
    LLM --> OUT --> DELIVER[Deliver]
    IN -. violations .-> LOG[(Guardrail Audit Log)]
    OUT -. violations .-> LOG
```

Guardrails are a **pipeline** ([[P7]]): input rails run before the model, retrieved content is scanned before it enters context, and output rails run before delivery. Policies are declarative (Colang-style). Violations are logged for audit and feed evaluation.
