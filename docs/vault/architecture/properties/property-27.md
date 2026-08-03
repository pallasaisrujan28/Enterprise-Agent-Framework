---
title: "Property 27: No compaction boundary separates a tool call from its result"
type: property
tags: [property, compaction, tools]
aliases: ["Property 27"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 27: No compaction boundary separates a tool call from its result

Part of [[correctness-properties|Correctness Properties]].

For all compaction operations over all transcripts: the chosen `first_kept_entry_id` never falls between an assistant tool-call entry and its matching tool-result entry. Three clauses, all required ([[ADR-006]] rule 5):

1. **Shift, never separate.** If a proportional token-share split would land inside a call/result pair, the boundary moves back to the **assistant tool-call entry**, so the pair travels together.
2. **A trailing pending result block is preserved.** If a trailing tool-result block would push a chunk over target, the unsummarized tail is kept intact rather than the pair being split to hit a size number. Chunk sizes are therefore approximate **by design**; code assuming exact splits is wrong.
3. **Aborted and errored call blocks do not hold a split open.** They have no result to pair with, so they split freely — without this exception a run of aborted calls can make a chunk unsplittable.

A surviving context containing a tool call with no result is a defect, not a degradation: the model sees itself having asked for something and never learning the answer. Tested deterministically. *(property-based: arbitrary transcripts with arbitrary call/result interleavings, arbitrary abort placements, and arbitrary split targets)*
