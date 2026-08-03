---
title: "4. Service Selection and Local-First Development"
type: hub
tags: [hub, local-first]
aliases: ["§4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 4. Service Selection and Local-First Development

**This is the current state of the platform.** Per [[ADR-019]], the platform runs on **Docker Compose on a developer machine**, every backing service is a pinned container image, and there is no cloud deployment and no cloud CI. The order of work is deliberate: first identify each service and why it was chosen, then develop locally against container images of all of them, then earn cloud infrastructure at an explicit checkpoint ([[§8]]) rather than assuming it.

This section is the answer to a specific question that the earlier drafts skipped: *which services, chosen why, at what cost?* Product names appeared throughout the document without recorded reasoning, which is exactly the failure [[ADR-018]] was written to fix for Kubernetes. [[§4.1]] fixes it for everything else.

## In this section

- [[4-1-service-selection-with-rationale-and-tradeoffs|4.1 Service selection with rationale and tradeoffs]]
- [[4-2-the-known-local-cloud-gap-table|4.2 The known local/cloud gap table]]
- [[4-3-local-compose-topology|4.3 Local Compose topology]]
- [[4-4-local-ci-the-only-three-gates|4.4 Local CI — the only three gates]]
