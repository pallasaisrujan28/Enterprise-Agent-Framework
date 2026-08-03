---
title: "7. Honest Tradeoffs & Counterarguments"
type: hub
tags: [hub]
aliases: ["§7"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 7. Honest Tradeoffs & Counterarguments

Recording the arguments against this design so future readers can re-open decisions with the same information rather than rediscovering the objections by surprise.

## In this section

- [[7-1-this-layered-topology-is-overkill-at-small-scale|7.1 This layered topology is overkill at small scale]]
- [[7-2-graph-engineering-is-substantially-a-rebrand|7.2 "Graph engineering" is substantially a rebrand]]
- [[7-3-reflective-prompt-optimization-can-make-things-worse|7.3 Reflective prompt optimization can make things worse]]
- [[7-4-two-retrieval-systems-is-a-real-operational-cost|7.4 Two retrieval systems is a real operational cost]]
- [[7-5-guardrails-add-latency-and-false-positives|7.5 Guardrails add latency and false positives]]
- [[7-6-track-a-weight-training-may-never-be-worth-it|7.6 Track A (weight training) may never be worth it]]
- [[7-7-multi-tenancy-on-shared-infrastructure-is-a-permanent-obligation|7.7 Multi-tenancy on shared infrastructure is a permanent obligation]]
- [[7-8-the-stable-prefix-discipline-fights-normal-development|7.8 The stable-prefix discipline fights normal development]]
- [[7-9-skills-trade-node-sprawl-for-skill-sprawl-and-skill-sprawl-is-a|7.9 Skills trade node sprawl for skill sprawl, and skill sprawl is a real failure mode]]
- [[7-10-deferring-the-self-hosted-pii-stack-is-an-accepted-risk-with|7.10 Deferring the self-hosted PII stack is an accepted risk with regulatory teeth]]
- [[7-11-local-first-defers-validation-so-the-scaling-and-isolation|7.11 Local-first defers validation, so the scaling and isolation designs stay unproven for longer]]
- [[7-12-we-borrowed-openclaw-s-compaction-mechanics-and-deliberately|7.12 We borrowed OpenClaw's compaction mechanics and deliberately rejected its state topology]]
