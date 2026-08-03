---
title: "5.2 Environments and Promotion"
type: section
tags: [section]
aliases: ["§5.2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 5.2 Environments and Promotion

Part of [[5-aws-deployment-evaluation|5. AWS Deployment & Evaluation]].

| Environment | Purpose | Data | Models |
| --- | --- | --- | --- |
| `dev` | Feature work, local LangGraph server for agent tests | Synthetic + tokenized fixtures | Cheap models, low limits |
| `staging` | Full topology, eval suites, load tests, chaos drills | Tokenized production-shaped data | Production models, capped budget |
| `canary` | 1–5% of production traffic per tenant opt-in | Real, partitioned | Production |
| `prod` | All traffic | Real, partitioned | Production |

Prompt/policy artifact versions are promoted **by pointer** across these environments ([[ADR-014]]) and can be pinned per tenant, so one tenant can hold a known-good prompt version while others move forward.
