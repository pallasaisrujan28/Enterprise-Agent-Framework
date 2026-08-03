---
title: "ADR-010: Multi-tenancy, and a three-check authorization model split across two gateways"
type: adr
tags: [adr, multi-tenancy, model-routing]
aliases: ["ADR-010"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# ADR-010: Multi-tenancy, and a three-check authorization model split across two gateways

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Authentication and authorization are **two different jobs at two different boundaries**, and conflating them was a real error in an earlier draft of this design.

| Boundary | Authenticates | Decides | Does **not** decide |
| --- | --- | --- | --- |
| **L1 — API / Auth Gateway** (user boundary) | The **end user** (OAuth/JWT), server-side | May this user talk to the platform at all? Which tenant are they? Are they within quota? | Anything about agents or tools — neither is known yet |
| **L3 — MCP Gateway** (agent boundary) | The **agent** (its own credential/identity) | (1) Is this a valid agent identity? (2) Is this agent granted this tool? (3) Does the **delegated user** have rights to this action and data? | User login — already established upstream |

All three L3 checks are derived from **one OPA policy bundle** per tenant, versioned as an artifact ([[ADR-014]]), and all three **fail closed**. Per-tenant isolation of data, memory, and registry entries is enforced at every hop.

**The contract requirement this creates.** Check 3 is only possible if the **delegated user principal travels with the tool call**. The MCP Gateway cannot evaluate a user's rights from an agent identity alone. So `ToolCall`/`TenantContext` carry both the **acting agent** and the **on-behalf-of user** ([[§3.1]], [[§3.2]]), and the policy input includes both. This is [[Property 32]].

**Context.** The earlier version described an "Agent Gateway (L1)" that authenticated the user *and* held per-agent tool allowlists. Two problems. First, the name was wrong — L1 is a conventional user-facing auth server, nothing about it is agent-aware. Second, and more seriously, it placed tool authorization at a point where **the tool is not yet known**, which means the check either happens too early to be meaningful or silently degenerates into a coarse per-agent grant that ignores arguments. The MCP Gateway is the only place where agent, tool, arguments, and delegated user are all in hand simultaneously, which makes it the only place a real decision can be made.

The related risk this reframing surfaces is the **confused deputy**: an agent authenticates correctly and is then used as a lever to reach data the requesting user was never entitled to. Agent authentication alone does not prevent it; user RBAC at the point of tool invocation is what prevents it.

**Rationale.** Centralizing authz in OPA keeps policy declarative and testable; enforcing at both gateway and pool provides defense-in-depth. Tenant-scoped memory/registry prevents cross-tenant leakage.

**Consequences.**
- (+) Declarative, auditable, least-privilege access; clean tenant isolation.
- (−) Policy management overhead; OPA becomes part of the request path (cached decisions mitigate latency).

**Alternatives considered.** Hard-coded checks in services — rejected (not auditable/uniform). Network isolation only — rejected (does not express per-agent tool scope).
