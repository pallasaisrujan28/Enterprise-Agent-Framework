---
title: "Property 11: PII is tokenized in every persisted surface"
type: property
tags: [property, pii]
aliases: ["Property 11"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 11: PII is tokenized in every persisted surface

Part of [[correctness-properties|Correctness Properties]].

For all persisted traces, spans, logs, audit events, and eval datasets: PII appears only in tokenized form. Re-hydration occurs only at delivery to a recipient authorized for that entity type.
