---
title: "3.5 Context Compaction Points (summary)"
type: section
tags: [section, compaction, context-engineering]
aliases: ["§3.5"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 3.5 Context Compaction Points (summary)

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

Compaction happens at three points, all restorable ([[P4]]):

- **Tool-output offload (step 12):** raw outputs → external memory; context keeps a reference.
- **Structurally-lossless trimming:** strip raw blobs/base64/tool metadata from history while keeping user/assistant turns verbatim.
- **Anchored iterative summary:** a persistent structured summary updated incrementally for long sessions, stored in the session cache and recited alongside `todo.md`.

None of these touch the stable prefix, so the KV-cache stays warm across compaction. All three are recorded as **appended `CompactionEntry` values** ([[§3.1]].11) rather than in-place rewrites, and each is preceded — once per compaction cycle, on a writable workspace — by the **memory flush** ([[ADR-006c]]). No boundary chosen by any of them may separate a tool call from its result ([[ADR-006]] rule 5, [[Property 27]]).

**The full lifecycle, with the two defensive paths that are easy to leave out.** The early path (memory flush) fires *deliberately*, while there is room to spend a turn well. The late path (mid-turn precheck) fires *defensively*, and its entire job is to refuse to fix the problem itself.

```mermaid
flowchart TB
    TS[Turn start<br/>estimate prompt pressure<br/>ONE estimator, reused everywhere] --> Q1{Occupancy}

    Q1 -- "below the soft threshold" --> RUN[Run the turn]
    Q1 -- "crossed the SOFT threshold<br/>a token gap BELOW compaction" --> FQ{Flush already run<br/>this compaction cycle?}

    FQ -- "yes - once per cycle" --> COMP
    FQ -- "no" --> WQ{Workspace writable?}
    WQ -- "no" --> SKIP[Record a skip<br/>no turn spent on a write that cannot land]
    SKIP --> COMP
    WQ -- "yes" --> FL[MEMORY FLUSH - a SILENT TURN<br/>the agent writes its own reasoning state<br/>conclusions, live hypothesis, what is ruled out,<br/>what it intends next<br/>routable to a cheaper model]

    FL --> COMP[COMPACT<br/>choose first_kept_entry_id<br/>NEVER between a tool call and its result]
    COMP --> APP[APPEND a CompactionEntry<br/>summary, cut point, tokens_before,<br/>provider, memory_flush_entry_id<br/>nothing in history is rewritten]
    APP --> RUN

    RUN --> TR[Tool result appended]
    TR --> PC{Mid-turn precheck<br/>SAME estimator as turn start}
    PC -- "still fits" --> MC[Next model call]
    PC -- "does not fit" --> SIG[Raise a STRUCTURED SIGNAL<br/>stop the submission<br/>NEVER compact inline - that stalls a live turn]
    SIG --> OL{Outer run loop decides}
    OL -- "truncating the oversized result is enough" --> MC
    OL -- "not enough" --> COMP

    MC --> OV{Provider returned<br/>a context-overflow error?}
    OV -- "no" --> DONE[Turn completes]
    OV -- "yes - matched as an ERROR FAMILY,<br/>not one provider's wording" --> EM[Emergency trim, then ONE retry<br/>use the provider's reported count if it gave one,<br/>else a minimally over-budget synthetic count<br/>session mapping PRESERVED - never rotate to a fresh session]
    EM --> MC

    style FL stroke-width:3px
    style SIG stroke-dasharray: 5 5
    style EM stroke-dasharray: 5 5
```

Three invariants the picture is meant to make hard to violate: **flush precedes compact, never the reverse** ([[Property 28]]); **the precheck signals and the outer loop acts** ([[ADR-006]] rule 6); and **no arrow anywhere touches the stable prefix** ([[Property 8]]).
