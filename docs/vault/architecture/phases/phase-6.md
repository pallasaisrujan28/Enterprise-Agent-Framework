---
title: "Phase 6 — Enhancements: the self-hosted PII stack"
type: phase
tags: [phase, pii]
aliases: ["Phase 6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Phase 6 — Enhancements: the self-hosted PII stack

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Ship:** local NER PII detection (Presidio plus a GLiNER-PII-class model) covering unstructured entities — names, addresses, free-text and contextual identifiers; the **tenant-scoped, KMS-encrypted PII vault** with its own retention and deletion policy so a tenant offboard destroys the mapping; **reversible tokenization** at the gateway before egress; authorized **re-hydration** at delivery only; tokenized-only persistence across traces, spans, trajectories, audit events, and eval datasets; the broadened no-raw-PII-egress gate over the full NER entity set; false-positive rate tracked per entity type and tuned per tenant.

**Why last.** It is the largest single safety project in the document and the one that benefits most from a stable platform underneath it — vault integration touches the gateway, the model proxy, the trajectory writer, the trace pipeline, and eval dataset construction. Building it against a moving topology would mean building it twice. The deterministic structured-entity gate from [[Phase 1]] carries the highest-consequence leak class in the meantime ([[ADR-009]]).

**The cost of it being last, stated plainly:** Phases 1–5 cannot serve regulated data. See the precondition above and [[§7.10]].

**Exit criterion:** an unstructured-PII red-team suite passes — names and addresses in free text and in retrieved corpus content are tokenized before provider egress; re-hydration is denied to an unauthorized recipient in a test; a simulated tenant offboard destroys the vault mapping and the deletion is verified; the broadened egress gate is green; **the onboarding restriction is formally lifted**, which is the actual deliverable of this phase.
