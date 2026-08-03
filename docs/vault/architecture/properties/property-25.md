---
title: "Property 25: The skill index is bounded and each of the three skill levels stays in its own region"
type: property
tags: [property, skills]
aliases: ["Property 25"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Property 25: The skill index is bounded and each of the three skill levels stays in its own region

Part of [[correctness-properties|Correctness Properties]].

*(Extended in this revision from a two-footprint model to the three-level loading model — [[ADR-002b]].)*

For all agents `a` and all skill index versions `v` built for `a`: every entry's description is within the description-length budget, `v.entry_count` is within the per-agent skill-count ceiling (derived from the ≈100-tokens-of-metadata-per-skill budget), and past the ceiling index construction **fails** and `skill_search` is required.

The three-level invariant, all three clauses required:

1. **Level 1 only, in the prefix.** The prefix contribution of a skill is exactly its metadata entry — constant per skill, and independent of body or resource size.
2. **Level 2 never in the prefix.** A skill **body** does not appear in the stable prefix at any point in any session; it is appended to the volatile tail on trigger and nowhere else.
3. **Level 3 scripts never in context at all.** A bundled **script** is dispatched for execution and is never read into the context window — only its (compact or offloaded) output returns. A Level-3 **reference** document may enter the tail when read, and costs tokens accordingly; a script must not.

*(property-based: arbitrary skill sets, arbitrary description lengths, arbitrary body and resource sizes)*
