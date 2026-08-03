---
title: "Property 35: An effects publication replaces the effect set; it never merges into it"
type: property
tags: [property]
aliases: ["Property 35"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T00:37:16+00:00
---

# Property 35: An effects publication replaces the effect set; it never merges into it

Part of [[correctness-properties|Correctness Properties]].

For all Publication Log entries with content type `changes` for item `i`: the platform **replaces** the stored effect set for `i` rather than upserting into it, and any stored effect for `i` no longer present upstream is **removed**.

The upstream model permits effects to be **deleted by a publication event**, and effects are only ever published, never withdrawn — so there is no deletion signal to key on. An upsert-shaped sync therefore accumulates amendments that upstream has retracted, and the resulting answer cites a repeal that no longer exists. Additionally, the watermark for all content types is `updated` and **never `published`**, which may be absent for material first published before 5 July 2023 (§ anchor use case). *(property-based: arbitrary sequences of effects publications including ones that shrink the set, and arbitrary sync restarts mid-sequence)*
