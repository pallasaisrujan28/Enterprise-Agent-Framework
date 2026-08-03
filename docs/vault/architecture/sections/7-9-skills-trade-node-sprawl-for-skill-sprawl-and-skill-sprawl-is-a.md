---
title: "7.9 Skills trade node sprawl for skill sprawl, and skill sprawl is a real failure mode"
type: section
tags: [section, skills, failure-handling]
aliases: ["§7.9"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.9 Skills trade node sprawl for skill sprawl, and skill sprawl is a real failure mode

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

Skills are the best answer this design has to extensibility, and they have a failure mode with the same shape as the one they fix. **An unbounded skill index is prefix bloat by another name.** Every skill contributes a line to the stable prefix; a few hundred skills is a large, permanently cached block of description text that every session on that agent pays for, and the whole argument for progressive disclosure quietly inverts.

Three further failure modes worth naming plainly:

- **Ambiguous overlap.** Two skills whose descriptions both plausibly match a request produce worse selection than one skill with a sharp boundary. Skill selection degrades with index size the same way tool selection degrades with catalog size, and for the same reason.
- **Skills as a dumping ground.** "Make it a skill" is an easier sell than "add a node," which means it will attract requests that should have been *nothing at all* — a paragraph in the system prompt, or a better tool description. Cheap extension mechanisms accumulate junk faster than expensive ones.
- **Eval theatre.** Mandatory eval cases guarantee eval cases exist, not that they are good. A skill with three trivially-passing cases satisfies the gate and tests nothing.

What we accept and how it is bounded: a hard one-line description budget, a per-agent skill-count ceiling enforced at validation, `skill_search` as the mandatory mechanism past the ceiling, skill index size as a monitored metric with an alarm ([[§5.6]]), per-skill success rate tracked so an unused or unhelpful skill is visible and removable, and skill review treated as real review. None of that makes sprawl impossible — it makes it observable, which is the most that can be honestly claimed.
