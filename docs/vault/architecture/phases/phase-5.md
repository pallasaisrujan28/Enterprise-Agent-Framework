---
title: "Phase 5 — Improvement layer"
type: phase
tags: [phase, improvement-layer]
aliases: ["Phase 5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Phase 5 — Improvement layer

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Runs locally on Compose.** The tuning loop (ADR-008a) is a scheduled job plus a PR, and LangSmith and DeepEval both work from local development, so nothing here is blocked on cloud. The **canary stage** is the exception: canarying at limited traffic needs traffic, so until then the gate is benchmark plus human review plus a rollback drill against local traffic replay.

**Ship, in order and only in order:** **RL Phase A** — GEPA/DSPy reflective prompt optimization over curated failure trajectories, running as a scheduled job that opens a PR with eval scores attached, never a live write. Then **RL Phase B** — a learned router, contextual bandits for model selection and escalation thresholds, and a verifier/judge model trained on logged outcomes. Then, **only if volume and ROI justify it, RL Phase C** — RLVR/GRPO fine-tuning of a small open model for the single highest-volume classifier/router node, via Agent Lightning against the existing harness.

**Exit criterion for A:** at least one optimization pass clears the eval threshold on a held-out set, survives canary, and is rolled back cleanly in a drill. **For B:** the learned policy beats the fixed policy on logged outcomes net of cost. **For C:** it stays unbuilt unless A and B have plateaued and the arithmetic is written down. Note that the cascade's tier-4 classifier ([[Phase 4]]) is the natural Phase C candidate — the same component [[ADR-008]] identified.
