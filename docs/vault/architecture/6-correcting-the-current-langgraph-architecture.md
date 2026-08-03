---
title: "6. Correcting the Current LangGraph Architecture"
type: hub
tags: [hub, graph]
aliases: ["§6"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 6. Correcting the Current LangGraph Architecture

You asked to be told if the current approach is wrong. The short version: **the tool choice is fine, the topology is not.** LangGraph is not the problem — using it as one flat mega-graph where every agent is a node and orchestrators classify between them is. That shape has a built-in scaling ceiling, and you are hitting it.

## In this section

- [[6-1-why-the-mega-graph-stops-scaling|6.1 Why the Mega-Graph Stops Scaling]]
- [[6-2-the-corrected-shape|6.2 The Corrected Shape]]
- [[6-3-migration-path|6.3 Migration Path]]
