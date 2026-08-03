---
title: "3.3 How Systems Interact"
type: section
tags: [section]
aliases: ["§3.3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 3.3 How Systems Interact

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

- **Gateway ↔ Orchestrator:** Gateway forwards a validated, PII-redacted request plus the resolved `TenantContext` (including OPA `tool_allowlist`). The orchestrator trusts the gateway's authn but the MCP gateway **re-checks** authz (defense-in-depth, [[ADR-010]]).
- **Orchestrator ↔ Session Cache:** The orchestrator is stateless; all session state (history references, plan, anchored summary) is read/written to Redis keyed by `tenant_id:session_id`.
- **Orchestrator ↔ Model Proxy:** The assembled prompt goes to the model proxy, which routes by task type ([[ADR-011]]), applies prompt caching at the cache breakpoint, and re-checks PII redaction before provider egress.
- **Orchestrator ↔ Executors:** Handoffs are minimal for SIMPLE tasks and include trajectory + filesystem handles for COMPLEX tasks. Results return via the constrained `submit-results` tool, with `REROUTE` as a first-class outcome ([[ADR-013]]).
- **Orchestrator ↔ Skill Registry:** At session start the orchestrator resolves the agent's granted skills into a pinned `SkillIndexVersion` whose one-line entries enter the stable prefix. During the loop, a skill **body** is fetched and appended to the volatile tail on demand — never into the prefix ([[ADR-002b]]).
- **Executors ↔ Sub-graph Registry:** A sub-graph is invoked **as a tool** with a `depth` counter; dispatch rejects invocations past the depth limit before any model call. The sub-graph runs on its own stable prefix and its own isolated context and returns through the same `submit_results` contract ([[§2.12]].1).
- **Retry scoping ↔ Executors:** A scope-2 re-attempt is a **new** executor with a clean context carrying only a `FailureLesson`; the failed attempt's full trajectory stays addressable in T2 and is not read by the retrying model ([[§2.13]]).
- **Dispatch ↔ MCP Gateway ↔ Pools:** Dispatch sends a `ToolCall` with propagated trace context; the MCP gateway validates schema, re-checks the allowlist, resolves `tool → pool` via the registry, and forwards over mutual TLS to a pool replica behind a circuit breaker.
- **Pools ↔ Memory/Knowledge:** `file_*` pools read/write external memory; `search_*` pools query the vector store and knowledge graph through a versioned retrieval strategy. Large outputs are offloaded and only a `Reference` returns ([[P4]]). All of those stores were created by Terraform; nothing in this path provisions a resource ([[ADR-015]]).
- **Tool authors ↔ MCP Gateway:** A new or updated MCP server registers with the gateway, which validates its tool schemas and name-prefix ownership; a new `ToolCatalogVersion` is cut and promoted. In-flight sessions finish on their pinned version ([[§3.8]]).
- **Everything ↔ Observability:** Every hop emits a span; every LLM call emits a record with token accounting and cache stats; the stitched `TrajectoryRecord` is persisted for eval and RL.
