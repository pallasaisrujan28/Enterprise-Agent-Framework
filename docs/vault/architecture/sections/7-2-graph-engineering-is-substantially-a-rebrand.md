---
title: "7.2 'Graph engineering' is substantially a rebrand"
type: section
tags: [section, graph]
aliases: ["§7.2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.2 "Graph engineering" is substantially a rebrand

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

**Provenance, recorded honestly because you asked.** "Graph engineering" is a term that originated on X in mid-2026 and spread quickly through agent-engineering commentary. It is **not** a Karpathy-authored essay, despite being frequently discussed as though it were part of that lineage alongside "context engineering" — worth stating plainly, because the misattribution is doing real work in how seriously teams treat it. Its mechanics predate the label by a wide margin: LangGraph `StateGraph`, AutoGen `GraphFlow`, Google ADK, and the A2A protocol all shipped the substance before anyone needed a name for it. LangGraph's own creator publicly questioned whether the term names anything new. Treat it as **useful shared vocabulary for an existing practice**, not as a paradigm to adopt.

The vocabulary is newer than the capability. Declaring nodes, edges, conditional routing, fan-out/fan-in, and review steps has been available in LangGraph `StateGraph`, AutoGen `GraphFlow`, and Google ADK for a while, and A2A covers cross-agent messaging. Treating "graph engineering" as a new discipline to adopt risks the exact failure this design is correcting — adding nodes because the framing rewards nodes. The durable part of the idea is the *discriminator* (who decides the path: the agent or you), not the terminology. The genuinely useful contribution of the framing is the **cumulative stack** (prompt → context → harness → loop → graph) and the discipline of reaching for the outermost layer last ([[P9]], [[ADR-012]]) — which is an argument for *fewer* graphs, not more.
