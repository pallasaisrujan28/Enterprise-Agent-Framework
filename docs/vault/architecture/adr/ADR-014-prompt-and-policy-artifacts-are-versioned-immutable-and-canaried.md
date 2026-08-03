---
title: "ADR-014: Prompt and policy artifacts are versioned, immutable, and canaried"
type: adr
tags: [adr, authz]
aliases: ["ADR-014"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-014: Prompt and policy artifacts are versioned, immutable, and canaried

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** System prompts, tool descriptions, few-shot sets, guardrail policies, and access policies are **immutable versioned artifacts** with a content hash, promoted through `dev → canary → prod` by reference. Runtime resolves `(tenant_id, agent_id) → artifact_version`. Rollback is a pointer change.

**Context.** Track B optimization ([[ADR-008]]) mutates prompts automatically, and reflective optimization is known to regress on some seeds. Guardrail and access policies carry the same blast radius.

**Rationale.** Immutability makes every behavioural change attributable to a specific artifact version in the trajectory record, which is what makes regression detection and rollback possible at all. Canary traffic bounds the damage of a bad candidate.

**Consequences.** (+) Deterministic rollback, per-tenant pinning, clean A/B comparison, and an audit trail. (−) Artifact registry becomes hot-path infrastructure (cached aggressively, since a lookup miss must not stall a turn).

**Alternatives considered.** Prompts in code — rejected, ties behaviour changes to deploys and blocks per-tenant pinning. Prompts in mutable config — rejected, no attribution, no rollback, no canary.
