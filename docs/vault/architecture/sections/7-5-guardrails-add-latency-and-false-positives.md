---
title: "7.5 Guardrails add latency and false positives"
type: section
tags: [section, guardrails]
aliases: ["§7.5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.5 Guardrails add latency and false positives

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Every rail is a checkpoint on the hot path, and PII detectors over-trigger on names, addresses, and identifiers that resemble sensitive entities. Aggressive masking can also degrade agent reasoning by removing information it legitimately needs. Mitigations we accept: rails run concurrently where they are independent, detector thresholds are tuned per tenant, `allow_internal` exists as a PII policy tier for low-risk internal deployments, and false-positive rate is tracked as a metric ([[§5.6]]) rather than assumed to be zero.
