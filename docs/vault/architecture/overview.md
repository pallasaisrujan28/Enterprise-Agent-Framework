---
title: "Overview"
type: hub
tags: [hub]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T00:37:16+00:00
---

# Overview

The Enterprise Agent Framework is a multi-tenant, horizontally scalable agentic platform. It draws on production context-engineering lessons (Manus) and the enterprise MCP gateway topology, and is intended to grow along **two independent scaling axes**:

1. **Tenant scale** — serving many customers on shared infrastructure with strict isolation, per-tenant policy, quotas, and cost accounting.
2. **Capability scale** — adding more agents, tools, and task classifications without the combinatorial blow-up that a single flat orchestration graph produces.

The platform does **not** abandon LangGraph. Instead of one giant graph where every node is an agent and a central router touches every classification, LangGraph is used as the **per-sub-agent execution substrate** — each sub-agent is a small, self-contained graph. Scaling is solved with **architectural layering** (Gateway → Orchestrator → Tool Pools) and **context isolation** (each sub-agent gets a clean, minimal context window), not by growing one monolithic graph.

The design is deliberately opinionated. It records architecture **decisions** as ADR-style entries so the team can "stick to the principles" as the system evolves. The governing principles are drawn from the research grounding below and are treated as invariants of the platform.

## In this section

- [[guiding-principles-invariants|Guiding Principles (Invariants)]]
- [[where-the-platform-actually-runs-today|Where the Platform Actually Runs Today]]
- [[document-structure|Document Structure]]
- [[research-grounding-and-attribution|Research Grounding and Attribution]]
- [[terminology-hygiene-read-this-before-6|Terminology Hygiene (read this before §6)]]
- [[the-five-layer-cumulative-stack|The Five-Layer Cumulative Stack]]
- [[the-anchor-use-case-legislation-and-compliance-research-chatbot|The Anchor Use Case: Legislation and Compliance Research Chatbot]]
