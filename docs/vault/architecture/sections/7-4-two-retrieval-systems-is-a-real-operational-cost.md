---
title: "7.4 Two retrieval systems is a real operational cost"
type: section
tags: [section, retrieval, evals]
aliases: ["§7.4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.4 Two retrieval systems is a real operational cost

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

GraphRAG's indexing is LLM-heavy per corpus, and running vector plus fulltext plus graph means three things to index, monitor, and reconcile. For tenants whose questions are overwhelmingly single-hop lookups, graph mode is dead weight. Hence it is enabled per tenant/corpus, and the **retrieval accuracy harness** ([[§3.6]].4) must be able to answer "did graph mode actually change the numbers" — recall@k, MRR/nDCG, groundedness — for that specific corpus. If it did not, turn it off there. That is now an enforceable commitment rather than an intention, because the harness is a CI gate.
