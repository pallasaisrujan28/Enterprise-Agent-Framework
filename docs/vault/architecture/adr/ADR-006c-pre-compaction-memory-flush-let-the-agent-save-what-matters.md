---
title: "ADR-006c: Pre-compaction memory flush — let the agent save what matters before you compact"
type: adr
tags: [adr, compaction]
aliases: ["ADR-006c"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-006c: Pre-compaction memory flush — let the agent save what matters before you compact

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Immediately **before** compaction runs, trigger a **silent agentic turn** ([[ADR-006d]]) in which the agent writes its own durable state to the session workspace — conclusions reached, working hypotheses, what has been ruled out, what it intends to do next. Compaction then proceeds. The flush fires at a **soft threshold below the compaction threshold**, runs **once per compaction cycle**, is invisible to the user, may be **routed to a cheaper model**, and is **skipped when the workspace is read-only**.

**Context.** This closes a gap the rest of [[ADR-006]] does not touch, and it is the most valuable finding in this revision. Restorable compression protects **tool outputs** — the artifacts. It does nothing whatsoever to protect the agent's own **reasoning state**: the conclusion it drew three turns ago, the hypothesis it is currently testing, the four approaches it has already eliminated. None of that is an artifact with a `Reference`. It exists only as text in the volatile tail, and when the tail is summarized, a summarizer *guesses* at which of it mattered.

That guess is the weakest link in the whole compaction design. A summarizer optimizes for a readable précis of what happened; an agent mid-task needs the specific, unglamorous facts that let it continue — *"the staging credentials are the ones that work"*, *"the ID format is prefixed, not bare"*, *"do not try the bulk endpoint, it 413s above 200 rows"*.

**Rationale.** The agent knows which of its own conclusions are load-bearing. Nothing else does. So ask it, on the record, while it still has the context — the same argument that justifies the self-compaction trigger in [[§2.10]], applied one step earlier. Framed as a principle: **let the agent save what matters before you compact, rather than trusting a summarizer to guess.**

**Mechanism, with the specifics that make it work.**

| Aspect | Decision | Why this way |
| --- | --- | --- |
| Trigger point | A **soft threshold a configurable token gap below** the compaction threshold (a 4,000-token gap is a reasonable default) | The flush is itself a turn and costs tokens. Firing it *at* the compaction threshold means the flush can trip the very overflow it exists to survive. |
| Frequency | **Once per compaction cycle**, tracked in the session record via `memory_flush_compaction_count` ([[§2.10]]) | Without a counter, a session hovering around the threshold flushes repeatedly and pays for it every time. |
| Visibility | **None.** Uses the silent-turn mechanism ([[ADR-006d]]) | Housekeeping is not a message. A user watching an agent narrate its own filing is worse than a user seeing nothing. |
| Destination | A dated memory file in the session workspace (T0, promoted to T1 like any artifact) | Disk survives compaction. Context does not. |
| Model route | **May be routed to a different, cheaper model** than the conversation, via the model proxy ([[ADR-011]]) | Otherwise local housekeeping silently bills at the conversation model's rate, which is the kind of cost leak nobody notices until the invoice. |
| Read-only workspace | **Skipped entirely** | A flush that cannot write is a turn spent producing nothing. Skip it and record the skip. |

**Consequences.**
- (+) Reasoning state survives compaction as **the agent's own words**, not a summarizer's paraphrase. Post-compaction continuity improves for exactly the facts that are hardest to summarize and most expensive to lose.
- (+) The flushed file is durable, greppable with ordinary `file_*` tools, and inspectable by a human debugging the session. It is also an unusually good eval artifact: it is the agent stating what it believed at a point in time.
- (+) Cheap-model routing keeps a per-cycle overhead from scaling with conversation model cost.
- (−) It is **an extra turn with an extra cost**, on a cadence tied to compaction. The soft-threshold gap and the once-per-cycle counter are what bound it; both are configurable and both need to be set deliberately.
- (−) The flush is only as good as the agent's own judgement about what matters. A poor flush is a plausible-looking file that omits the load-bearing fact.
- (−) Another ordering constraint in the compaction path: flush, *then* compact. Getting it backwards produces a memory file written from an already-compacted context, which is the failure this ADR exists to prevent and is worth a deterministic test ([[Property 28]]).

**Alternatives considered.** **(a) Trust the summarizer with reasoning state** — rejected; that is the status quo this ADR corrects, and the summarizer has neither the agent's intent nor its sense of what is still open. **(b) Auto-extract reasoning state with a separate heuristic pass** — rejected; a heuristic guessing at conclusions is the same guess with an extra component to maintain. **(c) Flush on every turn** — rejected; the cost is unbounded and most turns change nothing worth persisting. **(d) Make it a visible turn** — rejected; it trains users to ignore agent output, and there is a purpose-built silent path ([[ADR-006d]]).
