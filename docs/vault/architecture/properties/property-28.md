---
title: "Property 28: A memory flush completes before the compaction entry is written"
type: property
tags: [property, compaction]
aliases: ["Property 28"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 28: A memory flush completes before the compaction entry is written

Part of [[correctness-properties|Correctness Properties]].

For all compaction cycles `c` in a session whose workspace is **writable** and for which the pre-compaction flush is **enabled**: a memory-flush entry exists, it completed, and it precedes the `CompactionEntry` for `c` in the transcript — recorded as `CompactionEntry.memory_flush_entry_id`. Exactly **one** flush runs per cycle, enforced by `memory_flush_compaction_count` on the `SessionManifest`.

Where the workspace is **read-only** or the flush is disabled, a **skip** is recorded and compaction proceeds — a skip is an expected outcome, not a failure. Getting the ordering backwards produces a memory file written from an already-compacted context, which is precisely the loss [[ADR-006c]] exists to prevent, so the ordering is asserted rather than assumed. *(property-based: arbitrary compaction cycle sequences, arbitrary writable/read-only workspace states)*
