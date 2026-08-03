---
title: "Property 34: Every legislative answer is version-pinned, or refused"
type: property
tags: [property]
aliases: ["Property 34"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T13:48:17+00:00
---

# Property 34: Every legislative answer is version-pinned, or refused

Part of [[correctness-properties|Correctness Properties]].

For all answers `a` that assert what legislation says: `a` carries the **point-in-time basis** it was derived from — a version-pinned source URI including the date segment — and the asserted text is present in that version. Three clauses:

1. **A date-ambiguous question is asked about, not guessed at.** Where the user has not established an as-at date and no tenant default applies, the agent takes the `ask` exit rather than silently answering on the latest revision.
2. **The citation resolves and supports the claim.** A cited provision that does not exist, or exists and does not say what was asserted, is a failure — not partial credit. Deterministically checkable, because the citation is a resolvable URI.
3. **Prospective amendments are labelled as such.** Where a provision has changes not yet in force, an answer that presents future text as current law is wrong even though the text is real.
4. **Outstanding unapplied effects are disclosed.** Where an effect is *in force but not yet applied* to the published text (`<UnappliedEffect>`), the answer says so. A version-pinned citation is **necessary but not sufficient**: the revised text at a date may lawfully omit in-force amendments awaiting editorial application, so silence here yields a fluent, correctly-cited answer that is not the current law.

Clause 4 is the one that cannot be satisfied by careful retrieval alone — it requires reading the effects graph *alongside* the text and reporting a gap between them, which means the answer path has to consult two sources and reconcile them rather than trusting the document it fetched.

This is the property that makes the domain safe to operate in. Retrieval over legislation has a specific and dangerous failure mode: **the answer looks authoritative, cites a real provision, and is silently the wrong version** — because whatever was ingested is what gets retrieved. Nothing about a fluent answer signals it. *(property-based: arbitrary provisions × arbitrary as-at dates, including dates before commencement and dates between an amendment being made and coming into force)*
