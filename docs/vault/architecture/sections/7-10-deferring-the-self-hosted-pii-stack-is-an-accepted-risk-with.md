---
title: "7.10 Deferring the self-hosted PII stack is an accepted risk with regulatory teeth"
type: section
tags: [section, pii]
aliases: ["§7.10"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.10 Deferring the self-hosted PII stack is an accepted risk with regulatory teeth

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

**The risk.** Until [[Phase 6]], PII detection covers **structured entities only** — credit card, SSN, email, phone — via deterministic pattern matching ([[ADR-009]]). Unstructured PII (names, addresses, free-text identifiers, contextual PII) is **not detected**. A tenant's document corpus or a user's free-text message containing a patient name, a home address, or a case identifier would reach a model provider unmasked.

**Why the deferral is nonetheless the right call.** The full stack — local NER, the tenant-scoped vault, reversible tokenization, authorized re-hydration — is a genuine project. Building it in [[Phase 1]] delays the vertical slice that makes everything else measurable, and half-building it is worse than not building it, because a partial vault is a compliance surface with no compliance benefit. The deterministic gate is a week of work and closes the highest-frequency, highest-consequence leak class.

**The mitigation, which is a constraint and not a control.** The platform **must not onboard tenants with regulated data (PHI, PCI cardholder data, or regulated PII) until the [[Phase 6]] stack lands.** Supporting measures: the deterministic "no raw PII in an outbound provider payload" test is a hard CI gate from [[Phase 1]] ([[Property 10]]); a managed PII detection service can narrow the gap as an interim option; and [[Phase 6]] is scoped and sequenced in [[§8]] rather than left as "later."

**Why this one is called out separately from every other deferral in [[§8]].** Every other phase boundary trades capability for time. This one trades *regulatory exposure* for time, and the mitigation is a restriction on who we can sell to — which is a commercial decision, not an engineering one. It has to be visible in onboarding and in sales conversations, not just in this document. An accepted risk that only the authors know about is not accepted; it is hidden.
