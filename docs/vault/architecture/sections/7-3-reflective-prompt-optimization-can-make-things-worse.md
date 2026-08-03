---
title: "7.3 Reflective prompt optimization can make things worse"
type: section
tags: [section]
aliases: ["§7.3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 7.3 Reflective prompt optimization can make things worse

Part of [[7-honest-tradeoffs-counterarguments|7. Honest Tradeoffs & Counterarguments]].

GEPA's reported results are strong, but the "Reflection in the Dark" analysis found it degrading accuracy on some seeds, including a case dropping from roughly 23.81% to 13.50%. Any system that lets an optimizer rewrite production prompts unattended will eventually ship a regression. That is precisely why [[ADR-014]] makes artifacts immutable and versioned, and why Track B lands as a **PR with eval scores attached** rather than a live write. If the eval suite is thin, Track B is not safe to enable — the gate is only as good as the dataset behind it.
