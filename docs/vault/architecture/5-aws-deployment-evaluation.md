---
title: "5. AWS Deployment & Evaluation"
type: hub
tags: [hub, deployment, evals]
aliases: ["§5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 5. AWS Deployment & Evaluation

> ### FUTURE STATE — not built
>
> **Nothing in this section exists yet.** It is the designed cloud target, **gated by the cloud readiness checkpoint ([[§8]])**. The platform currently runs on Docker Compose ([[ADR-019]], [[§4]]); Kubernetes and EKS are the **eventual** deployment target, not the active one ([[ADR-018]]).
>
> The content is unchanged and still authoritative as a *design* — deliberately, so the eventual move is execution against a written plan rather than design under deployment pressure. Read every latency, scaling, and isolation claim below as a **hypothesis pending validation**, against the gap table in [[§4.2]]. The evaluation subsections ([[§5.3]] LangSmith, [[§5.4]] DeepEval) are the exception: **LangSmith and DeepEval both work from local development today** and are not gated by the checkpoint.

## In this section

- [[5-1-deployment-topology|5.1 Deployment Topology]]
- [[5-2-environments-and-promotion|5.2 Environments and Promotion]]
- [[5-3-evaluation-with-langsmith|5.3 Evaluation with LangSmith]]
- [[5-4-automated-testing-with-deepeval|5.4 Automated Testing with DeepEval]]
- [[5-5-github-actions-ci-cd|5.5 GitHub Actions CI/CD]]
- [[5-6-observability-metrics-first-class-not-incidental|5.6 Observability Metrics (first-class, not incidental)]]
- [[5-7-scaling-and-service-management|5.7 Scaling and Service Management]]
