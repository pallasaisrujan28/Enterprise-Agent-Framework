---
title: "Terminology Hygiene (read this before §6)"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Terminology Hygiene (read this before [[§6]])

Part of [[overview|Overview]].

Two similarly-named ideas appear in this document and must not be conflated:

| Term | Layer | What it means here |
| --- | --- | --- |
| **Graph engineering** | Execution topology | Declaring valid *paths* between agent steps and the checks between them (LangGraph `StateGraph`, AutoGen `GraphFlow`, Google ADK, A2A). Concerned with control flow. |
| **GraphRAG** | Data modeling | Extracting an entity/relationship knowledge graph from a corpus and building community summaries to answer multi-hop and global questions. Concerned with retrieval. |

They are orthogonal. A system can use a single agentic loop (no execution graph) and still use GraphRAG, and vice versa. Whenever "graph" appears below, it is qualified.
