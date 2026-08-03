---
title: "6.3 Migration Path"
type: section
tags: [section]
aliases: ["§6.3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:08:18+00:00
---

# 6.3 Migration Path

Part of [[6-correcting-the-current-langgraph-architecture|6. Correcting the Current LangGraph Architecture]].

Ordered so each step is independently shippable and reversible:

1. **Instrument before restructuring.** Land trajectory capture, token accounting, and `prefix_hash` on the current graph. You cannot tell whether a refactor helped without a baseline, and the baseline is cheap to get.
2. **Inventory every node against the extension ladder ([[§2.12]]) first, then the [[ADR-012]] forcing-function list.** Label each node with one of four destinations, in this order of preference:

   | Label | When | Destination |
   | --- | --- | --- |
   | **→ Skill** | The node encodes a *procedure* over tools that already exist | A folder: manifest, body, eval cases ([[ADR-002b]]). No code, no node. |
   | **→ Classification** | The node is a classifier | Deleted as a node. It becomes either a declared-intent short-circuit or part of the single Bedrock classification call ([[ADR-013]]) |
   | **→ Collapse into a loop** | The node is a thin reformat/glue step with no independent identity | Deleted; the loop does it |
   | **→ Keep (as a node or a sub-graph)** | One of the six [[ADR-012]] forcing functions genuinely applies | A node in a small graph, or a registered sub-graph invoked **as a tool** ([[§2.12]].1) |

   Expect the **Skill** column to be the largest by a wide margin, and the **Keep** column to be small. If Keep is large, the inventory was done with the old options in mind.
3. **Stand up the skill mechanism early** — the registry, the index in the prefix, on-demand body loading, manifest validation, and the eval gate. It is cheap to build relative to its leverage, and it is the destination for most of step 2's inventory, so building it early is what unblocks the bulk of the migration. Convert two or three procedural nodes to skills first and compare on the eval suite before converting the rest.
4. **Extract tools to MCP pools** behind the gateway, one domain at a time, starting with the highest-blast-radius domain (usually `db_*` or anything with write access). Cut the first tool catalog version and pin it per session ([[§3.8]]). The existing graph keeps working; only the call path changes.
5. **Introduce the stable-prefix assembler** for one agent type — including the skill index in the prefix — measure cache hit rate and cost per task, then roll out. This step usually pays for the whole migration on its own.
6. **Convert the labelled classifier nodes into the cascade**, tiers 1 and 2 first (free and deterministic), then train tier 3 from the routing decisions you have been logging since step 1. Add the `REROUTE` path before you delete any classifier node — recoverability is what makes an imperfect cascade safe.
7. **Collapse the remaining labelled nodes into 2–4 executor loops**, one at a time, keeping the old node behind a flag and comparing on the eval suite from [[§5.3]]/[[§5.4]]. Behavioural regressions surface here, which is why the eval harness precedes this step.
8. **Introduce the planner and `submit_results`** so the orchestrator stops shuttling raw state between agents, and land **scoped retry** ([[§2.13]]) at the same time — the planner is the scope-3 consumer, and building it against the old "carry everything forward" model just means rebuilding it.
9. **Register genuine sub-graphs** for the small Keep set, invoked as tools with the depth limit enforced.
10. **Add per-tenant policy, masking, and quotas** to turn the single-tenant runtime into a multi-tenant one.
11. **Only then start Track B optimization** ([[ADR-008]]). Optimizing prompts on a topology you are about to replace is wasted work.

The risky step is 7. It is behavioural, not structural, and it is the one that needs the eval gate in place first — which is why steps 1 and 5 come before it. Step 3 is the highest-leverage step: it is cheap, it is reversible (a skill is a pointer), and it converts the largest share of the inventory without touching topology at all.
---
