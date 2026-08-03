---
title: "ADR-005: Tool masking (logit/allowlist) instead of dynamic add/remove"
type: adr
tags: [adr, tools]
aliases: ["ADR-005"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# ADR-005: Tool masking (logit/allowlist) instead of dynamic add/remove

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Keep the **full tool definition set stable and always present** in the prefix. Constrain which tools are callable *per state* using **logit masking / allowlists** (constrained decoding), keyed by consistent name prefixes.

**Context.** Tool compaction is widely misread as "remove tools the agent should not use right now." Removing or reordering definitions does two bad things at once: it invalidates the KV-cache from the point of change onward, and it creates a contradiction where the conversation history references a tool that is no longer defined ([Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)). Capability scale multiplies both problems.

**Rationale.** Masking preserves the stable prefix ([[P3]], [[P2]]) while still restricting behavior. Prefix-based names (`browser_*`, `db_*`) let an entire family be masked with a single prefix rule. The core toolset stays small — Manus reports keeping under roughly 20 atomic tools, because selection quality degrades as the toolset grows.

**Three masking modes** are supported at decode time:

| Mode | Constraint | Typical use |
| --- | --- | --- |
| `auto` | Model may call a tool or answer directly | Default conversational turns |
| `required` | Model must call *some* tool | Steps where a bare answer is invalid (e.g., must retrieve before answering) |
| `specified` | Prefilled token prefix constrains to one family (`db_`, `browser_`) | Policy-scoped or plan-scoped steps |

**Consequences.**
- (+) Cache stays warm; behavior still gated by state and policy.
- (+) The mask is how access policy is *reflected into the model* ([[§3.2]]) so it does not waste turns on calls that would be denied. The **MCP gateway remains the place the decision is actually made** — the mask is a hint, never the boundary ([[Property 2]]).
- (−) Requires a decoding/provider layer that supports allowlist or logit masking; providers without it fall back to gateway-side rejection only.

**Alternatives considered.** Add/remove tools per state — rejected (cache invalidation + history contradiction). Prompt-only instructions "don't use X" — rejected (unreliable, not enforceable, not auditable).
