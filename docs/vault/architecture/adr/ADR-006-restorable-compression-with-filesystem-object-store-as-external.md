---
title: "ADR-006: Restorable compression with filesystem/object store as external memory"
type: adr
tags: [adr]
aliases: ["ADR-006"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-006: Restorable compression with filesystem/object store as external memory

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Large tool outputs are written to an **object store / sandbox filesystem**; the context retains only a **restorable reference** (path/URL + compact summary). Compaction is **restorable**, preferred over lossy summarization. A persistent **anchored summary** is updated incrementally for long sessions.

**Context.** Tool outputs (web pages, query results, files) blow up context and cost; naive summarization loses information needed later. The governing rule from the Manus write-up: **never drop information that has no path back**. Restorable offload beats lossy summarization because it defers the "what matters" judgement to the agent at the moment of need instead of guessing earlier.

**Rationale.** External memory ([[P4]]) keeps the context small and cache-friendly while preserving full fidelity for re-fetch. The strategy is **tiered**, cheapest and safest first:

| Tier | Technique | Reported effect |
| --- | --- | --- |
| 1 | Cache-stable prefix ([[ADR-004]]) | Largest cost lever; nothing is lost |
| 2 | Structurally lossless trimming — strip raw tool outputs, base64 images, metadata; keep user/assistant messages verbatim | ~20% mean token reduction, up to ~86% on bloated sessions |
| 3 | Restorable offload to object store, reference in context | Bounded growth, fully recoverable |
| 4 | Async anchored summarization of cold segments (persistent structured summary, incrementally updated as segments roll off) | Agent-decided ("active") compaction reports ~22.7% token reduction at equal accuracy, up to ~57% on individual tasks; ACON-style compression reports 26–54% peak reduction with largely preserved task performance |
| 5 | Semantic/exact response caching for repeated queries | Avoids the call entirely |

**Two hard rules.**
1. **Never compress the cached prefix.** Compression that rewrites the prefix can cost more than it saves. The decision must be driven by a two-tier cost model (cache-read price vs standard input price), not by token count alone.
2. **Never block inference on summarization.** Blocking LLM-based summarization stalls a turn for tens of seconds; compaction runs asynchronously, off the critical path, and its output is swapped in at the next natural turn boundary.

The mechanics below are corrected against the [OpenClaw session-management and compaction internals](https://github.com/openclaw/openclaw/blob/main/docs/reference/session-management-compaction.md). Their *mechanics* transfer directly; their *state topology* does not, and [[§7.12]] records why so a future reader does not simplify toward it.

> Content from the OpenClaw session-management documentation was rephrased for compliance with licensing restrictions.

**Rule 3 — compaction is an appended ENTRY, not a payload replacement.** The first draft described compaction as swapping payloads for references in place, which made "append-only" true with an asterisk. The cleaner mechanism: **append a `compaction` entry** to the transcript carrying the summary plus `first_kept_entry_id` and `tokens_before` ([[§3.1]].11). Future turns read that entry's summary plus every entry after the cut point, and ignore everything before it. Nothing is edited. Three things follow:

- **Append-only becomes literally true**, not true-modulo-compaction. [[Property 6]] stops needing a carve-out.
- **The cut point is inspectable and auditable.** "What did the agent stop being able to see, and when" is a field lookup rather than a reconstruction.
- **Compaction is idempotent and stackable.** A second compaction appends a second entry with a later cut point; the history of compactions is itself history.

**Rule 4 — the transcript is a TREE, not a list.** Every entry carries `id` and `parent_id`. This is not bookkeeping for its own sake — it is what makes **forking** native, and forking is exactly what two existing parts of this design need:

- **Sub-graph spawn ([[§2.12]].1)** is a branch from the parent entry at the point of invocation, not an unrelated record that has to be correlated back afterwards.
- **Scope-2 re-attempt ([[§2.13]])** is a branch from the last good entry. The failed attempt stays on its own branch — durable, addressable, and *not* in the new context. The tree is the structure that makes [[Property 12]]'s two clauses coexist without effort.

A flat list forces branching to be simulated with correlation identifiers and copies. A tree makes it a parent pointer. Two constraints come with it, both adopted: **a fork is refused while the parent has an active run** (forking a moving target produces a child whose parent state is indeterminate), and **a forked child starts with fresh token counters** rather than inheriting the parent's, so a child's budget is its own and a deep chain does not inherit a spent ledger.

**Rule 5 — a compaction boundary must never split a tool call from its result.** This is a silent correctness bug, not a tuning concern. If a token-share split lands between an assistant tool call and its matching tool result, the surviving context contains a call with no result — the model sees itself having asked for something and never learning the answer, and reasons accordingly. Three sub-rules:

1. **Shift, do not separate.** If a proportional split would land between a tool call and its result, move the boundary **back to the assistant tool-call message** so the pair travels together.
2. **Preserve a trailing pending block.** If a trailing tool-result block would push the chunk over target, keep it — leave the unsummarized tail intact rather than splitting the pair to hit a size number.
3. **Aborted and errored tool-call blocks do not hold a split open.** There is no result to pair with and no comprehension to protect, so they split freely. Without this exception a long run of aborted calls can make a chunk unsplittable.

This is [[Property 27]] and it is tested deterministically. It is cheap to implement and expensive to discover in production, which is why it is [[Phase 1]] ([[§8]]).

**Rule 6 — the mid-turn precheck SIGNALS; it never compacts inline.** Rule 2 is hardest to honour in one specific place: after a tool result has been appended and before the next model call, mid-turn. That is precisely where the temptation to "just compact quickly" is strongest and where doing so stalls a live turn. The mechanism that makes rule 2 honourable rather than aspirational:

- After a tool result lands and **before** the next model call, estimate prompt pressure using the **same budget logic used at turn start** — one estimator, not a second approximate one that can disagree with the first.
- If the prompt no longer fits, **do not compact inline.** Raise a **structured signal**, stop the current prompt submission, and hand recovery to the **outer run loop** — which truncates oversized tool results if that is sufficient, and otherwise triggers compaction and retries the turn.

The division of labour is the point: the inner path *detects*, the outer loop *decides*. Nothing blocks on a summarizer.

**Rule 7 — overflow recovery reads the provider's numbers rather than re-guessing them.** The existing overflow trigger ([[§2.10]]) is strengthened with four specifics:

- **Recognize the error family, not one string.** Providers report context overflow through a variety of differently-worded errors; matching one vendor's phrasing means the recovery path silently stops working when another provider is added or a message is reworded.
- **Forward the provider's attempted token count into compaction** when it reports one. It is an observed number from the party that actually did the counting; re-estimating it locally throws away better information than we have.
- **When overflow is confirmed but no count is parseable, pass a minimally over-budget synthetic count** so compaction and diagnostics still have a number to work with. A missing number must not turn into a zero or a silent skip.
- **If overflow recovery still fails, surface explicit guidance and preserve the session mapping.** Never silently rotate to a fresh session — that discards the user's context and disguises a platform failure as amnesia.

**Rule 8 — the summarization step is a pluggable provider with a built-in fallback.** Summarization is the one part of compaction with a genuine quality dimension, so it sits behind an interface and can be swapped (a different model, a different prompt strategy, a tenant-supplied summarizer). Two behaviours are mandatory: **if a provider fails or returns empty, fall back automatically to built-in summarization** — a compaction cycle must not fail because a pluggable component did — and **genuine abort or timeout signals are re-thrown, never swallowed by the fallback**, so cancellation is always respected. Swallowing an abort into a fallback is how a cancelled request keeps spending money.

**Consequences.**
- (+) Bounded context growth; full recoverability; cheaper long tasks.
- (+) Offloaded artifacts are natural trajectory/eval assets ([[§5.3]]).
- (+) Compaction-as-entry makes the append-only property unconditional and the cut point auditable.
- (+) The tree transcript gives sub-graph spawn and scope-2 re-attempt a native representation instead of a correlation convention.
- (−) Requires a durable store and a re-fetch tool; references must be tenant-scoped and access-controlled.
- (−) Async compaction introduces eventual consistency in the session record; the session store must tolerate a compaction landing after a turn started.
- (−) A tree transcript is a data-model decision that is **expensive to retrofit** — every reader, replayer, and eval consumer assumes the shape. This is why it is [[Phase 1]] despite full compaction being [[Phase 4]].
- (−) The pairing rule means chunk sizes are approximate by design. Code that assumes exact token-share splits will be wrong.

**Alternatives considered.** Aggressive LLM summarization only — rejected (lossy, unrecoverable, and blocking). Unbounded context — rejected (cost, lost-in-the-middle). **In-place payload replacement** — rejected in this revision in favour of rule 3; it works, but it makes append-only conditional and the cut point implicit. **Flat transcript with correlation IDs for branches** — rejected; it reimplements a parent pointer badly and every consumer has to agree on the convention.
