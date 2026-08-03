---
title: "Architecture"
type: hub
tags: [hub]
aliases: ["§2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Architecture

**Deliverable 2 — High-Level Architecture (§2).** This section shows **only the components of our agentic framework** (not generic infrastructure). The components below are **runtime-agnostic**: they are the same containers on Compose today and on Kubernetes eventually. Which concrete service backs each one locally is [[§4.1]]; the local Compose topology is [[§4.3]]; the deployment mapping to AWS is [[§5]] and is **future state, not built** ([[ADR-019]]).

## In this section

- [[the-anatomy-of-an-agent-read-this-before-2-1|The Anatomy of an Agent (read this before §2.1)]]
- [[2-1-component-diagram|2.1 Component Diagram]]
- [[2-2-layer-responsibilities|2.2 Layer Responsibilities]]
- [[2-3-request-flow-high-level|2.3 Request Flow (High-Level)]]
- [[2-4-human-in-the-loop-flow|2.4 Human-in-the-Loop Flow]]
- [[2-5-failures-escalations-flow|2.5 Failures & Escalations Flow]]
- [[2-6-guardrails-strategy|2.6 Guardrails Strategy]]
- [[2-7-pii-masking-strategy-final-phase-target-design-with-the-phase-1|2.7 PII Masking Strategy (final-phase target design, with the Phase-1 interim state)]]
- [[2-8-operational-failure-modes-designed-for-not-discovered-later|2.8 Operational Failure Modes (designed-for, not discovered later)]]
- [[2-9-continuous-improvement-flow-track-a-track-b|2.9 Continuous Improvement Flow (Track A / Track B)]]
- [[2-10-context-engineering-session-filesystem-and-storage-tiers|2.10 Context Engineering: Session Filesystem and Storage Tiers]]
- [[2-11-ownership-boundaries-terraform-vs-code-vs-config|2.11 Ownership Boundaries: Terraform vs Code vs Config]]
- [[2-12-capability-extension-ladder|2.12 Capability Extension Ladder]]
- [[2-13-retry-recovery-and-failure-scoping|2.13 Retry, Recovery, and Failure Scoping]]
