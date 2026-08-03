---
title: "Property 32: A tool call carries both identities, and access is their intersection"
type: property
tags: [property, tools, authz]
aliases: ["Property 32"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# Property 32: A tool call carries both identities, and access is their intersection

Part of [[correctness-properties|Correctness Properties]].

For all tool calls `c` reaching the MCP Gateway: `c.agent_id` resolves to an **authenticated** agent identity, `c.on_behalf_of` is a **present, non-null** `UserPrincipal`, and the effective permission is the **intersection** of the agent's policy grant and the user's `data_scopes` — never the union, and never the agent's grant alone. Four clauses, all required ([[ADR-010]]):

1. **Agent authentication precedes authorization.** An unauthenticated agent identity is denied before any grant is evaluated, regardless of how legitimate `on_behalf_of` is.
2. **`on_behalf_of` is never null.** A turn with no human behind it carries an explicit **service principal** with its own narrow scopes. Absence must never read as absence of restriction.
3. **Intersection, not union.** For any `(agent, user, tool, args)` where the agent is granted the tool but the user's `data_scopes` do not cover the target data, the call is **denied**. An agent can never be used to reach data its delegated user could not reach directly.
4. **The decision cache is keyed on the user too.** No cached allow decision for user `u1` is ever served for a call whose `on_behalf_of` is `u2`, at equal `(tenant, agent, policy_version)`.

This is the **confused deputy** property. Clause 3 is the substance and clause 4 is where it realistically breaks — an implementation can satisfy 1 through 3 and still leak through a cache key that omits the user, which is why the clause is stated separately and tested separately. Enforcement is at the MCP Gateway because that is the only point where tenant, agent, user, tool, and arguments are simultaneously known; the L1 gateway cannot make this decision because the tool is not yet known there. *(property-based: arbitrary agent-grant × user-scope × tool × argument combinations, and arbitrary interleavings of calls from different users on one agent against a warm decision cache)*
