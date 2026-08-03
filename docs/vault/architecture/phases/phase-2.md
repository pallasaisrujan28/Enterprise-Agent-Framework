---
title: "Phase 2 — Multi-tenancy, access policy, tool isolation, safety"
type: phase
tags: [phase, multi-tenancy, tools, authz]
aliases: ["Phase 2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:08:18+00:00
---

# Phase 2 — Multi-tenancy, access policy, tool isolation, safety

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

**Runs locally on Compose (minimal profile).** One caveat recorded honestly: **NetworkPolicy has no Compose equivalent**, so per-pool network isolation is *designed* here and *enforced* post-checkpoint. Compose networks give a coarse approximation and nothing more ([[§4.2]]).

**Ship:** gateway authN (OAuth/JWT) and schema validation; OPA PDP with `TenantPolicyBundle`, per-agent tool allowlists, arg constraints, budgets, default-deny, fail-closed; **skill grants as policy** with the containment check that a skill can never widen access ([[Property 18]]); tenant `data_partition` on every store plus the cross-tenant isolation test as a deterministic gate; per-tenant rate limits at both edge and orchestrator; MCP gateway with the tool registry, mTLS, per-pool circuit breakers and default-deny NetworkPolicies; **tool catalog versioning and the full new-tool onboarding path** ([[§3.8]]) including tenant-supplied MCP server registration and validation; three domain pools (`db_*`, `file_*`, `search_*`); tool masking (`auto` / `required` / `specified`); classification as **one Bedrock call with a declared-intent short-circuit** ([[ADR-013]]) plus the `REROUTE` path; the guardrail pipeline (input, retrieved, output rails) at the [[ADR-009]] **interim** stage; HITL approval gates and interrupt/resume; audit events; policy fixtures in CI.

**Exit criterion:** two tenants served on shared infrastructure with a passing cross-tenant isolation suite; a denied tool is provably never executed even when the model attempts it; **a new tool is onboarded end to end with no platform redeploy** — MCP server registered, catalog version cut, granted by policy, canaried, promoted — while an in-flight session finishes on the prior catalog version; a skill that requests a scope outside its agent's grants fails validation; an approval gate interrupts and resumes a live session.
