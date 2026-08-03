---
title: "ADR-009: Guardrail pipeline + PII strategy, delivered in two stages"
type: adr
tags: [adr, pii, guardrails]
aliases: ["ADR-009"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-009: Guardrail pipeline + PII strategy, delivered in two stages

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Implement a **guardrail pipeline**: **input rails** (PII redaction, jailbreak/topic detection) run pre-LLM; **output rails** (moderation, PII scan, RAG grounding check) run post-LLM; **retrieved content** is also scanned. Use policy-driven guardrails (Colang-style policies). **No raw PII leaves the corporate boundary**, and that guarantee is a deterministic CI gate from [[Phase 1]] onward.

PII detection itself is delivered in **two stages**, because the full stack is expensive to build and the deterministic part carries most of the regulatory weight:

| Stage | Mechanism | Phase | Covers |
| --- | --- | --- | --- |
| **Interim — deterministic gate** | Pattern/regex matching for high-confidence **structured** entities only: credit card (with Luhn), SSN, email, phone. Optionally a **managed** detection service (e.g. Amazon Comprehend PII) as a stopgap. Plus the deterministic "no raw PII in an outbound provider payload" test as a **hard, non-negotiable** CI gate. | **1** | Structured identifiers, which are the highest-frequency and highest-consequence leak class |
| **Final — self-hosted stack** | Local NER (Presidio + a GLiNER-PII-class model), the tenant-scoped **PII vault**, reversible tokenization, and authorized re-hydration — the design in [[§2.7]] | **6 (final)** | Unstructured entities: names, addresses, free-text identifiers, contextual PII |

**Context.** Enterprise deployment demands regulatory compliance, jailbreak resistance, and grounded outputs. The self-hosted NER + vault + tokenization stack is genuinely valuable and genuinely a project; the deterministic structured-entity gate is a week of work and blocks the leaks that regulators care most about.

**Rationale.** A single detector is insufficient; layered rails cover distinct threat classes at distinct points ([[P7]]). Structured entities are exactly where deterministic matching is *better* than a model — a regex plus Luhn does not have a false-negative rate that varies with phrasing. Unstructured entity coverage needs NER, and NER we host ourselves needs the vault and tokenization plumbing around it to be useful, which is why it lands as one coherent final-phase deliverable rather than half-built early.

**The gating condition, stated as a decision and not an omission.** Until the final-phase stack lands, **the platform MUST NOT onboard tenants with regulated data (PHI, PCI cardholder data, or regulated PII)**. This is a hard precondition on Phases 1–5, recorded as an accepted risk with its mitigation in [[§7.10]], and it is the deferral in this document with actual regulatory teeth. A managed detection service narrows the gap but does not close it, because the vault and reversible tokenization — not just detection — are what make the guarantee auditable.

**Consequences.**
- (+) Defense-in-depth; auditable policy; the highest-consequence leak class is closed in [[Phase 1]].
- (+) The hard CI gate exists from the first phase, so the guarantee is never retrofitted onto a system that has been leaking.
- (−) Unstructured PII (names, addresses, free-text identifiers) is **not** covered until the final phase. That directly constrains which tenants can be onboarded, and it must be visible in sales and onboarding, not just in this document.
- (−) Added latency at interception points; requires tuning to control false positives.

**Alternatives considered.** Single moderation call — rejected (no PII, no grounding, no jailbreak coverage). Post-hoc only — rejected (PII would already have egressed). **Building the full self-hosted stack in [[Phase 1]]** — rejected on sequencing: it is a large project that would delay the vertical slice, and the deterministic gate plus an onboarding restriction gets the same safety outcome for the tenants we can actually serve early. **Shipping without any PII gate and adding it later** — rejected outright; a leak in [[Phase 1]] is not recoverable by a [[Phase 6]] fix.
