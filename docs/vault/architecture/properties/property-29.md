---
title: "Property 29: A silent turn delivers nothing, on either path"
type: property
tags: [property, compaction]
aliases: ["Property 29"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 29: A silent turn delivers nothing, on either path

Part of [[correctness-properties|Correctness Properties]].

For all turns `t` whose assistant output begins with the exact silent sentinel: **no output reaches the client through the buffered path and no output reaches the client through the streaming path** — including the **first partial chunk**, which must be checked before it is flushed. And the converse holds: a turn whose output does not begin with the exact sentinel **is** delivered, so superficially similar leading text is not silently swallowed.

Both paths are tested, because passing on one and failing on the other is the realistic defect — buffered suppression is the obvious half, and a streaming path that emits chunks as they arrive leaks the agent's private housekeeping before anything checks. Silent turns remain fully recorded in the transcript, the trajectory, and token accounting; **only delivery is suppressed** ([[ADR-006d]]).
