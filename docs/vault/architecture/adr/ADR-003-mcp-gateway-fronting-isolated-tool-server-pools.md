---
title: "ADR-003: MCP gateway fronting isolated tool-server pools"
type: adr
tags: [adr, tools]
aliases: ["ADR-003"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# ADR-003: MCP gateway fronting isolated tool-server pools

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** All tool execution goes through an **MCP Gateway**. Tools are grouped into **domain pools** (e.g., `browser`, `db`, `file`, `search`), each a separately deployed MCP server with 3+ replicas, a **circuit breaker**, and a **per-pool network policy**. A **tool registry** maps `tool → pool`.

**Context.** Capability scale means many tools across many domains with different reliability, security, and scaling profiles.

**Rationale.** Isolation limits blast radius and lets each domain scale and fail independently. The registry keeps `tool → pool` resolution out of prompts, preserving prefix stability ([[P2]]). Mutual TLS and per-pool NetworkPolicy enforce least privilege.

**Consequences.**
- (+) Independent scaling, independent failure domains, per-domain security posture.
- (+) New tool domains are added as new pools without touching existing pools.
- (−) Registry and gateway become critical infrastructure needing HA.

**Alternatives considered.** Direct tool calls from the orchestrator — rejected (no isolation, no uniform authz). One shared tool server — rejected (single failure domain, coarse security).
