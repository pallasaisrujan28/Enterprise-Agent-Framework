---
title: "7.8 The stable-prefix discipline fights normal development"
type: section
tags: [section, kv-cache]
aliases: ["§7.8"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# 7.8 The stable-prefix discipline fights normal development

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Nothing about "never mutate the prefix" is enforced by a type system. Adding a timestamp, a feature flag, a reordered tool list, or a non-deterministic JSON serializer to a prompt is a one-line change that any reviewer might wave through, and the only symptom is a bill. The `prefix_hash` metric and the CI cost gate exist because the discipline will not survive on good intentions.
