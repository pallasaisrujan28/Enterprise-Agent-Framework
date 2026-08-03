---
title: "ADR-004: KV-cache-first prompt assembly"
type: adr
tags: [adr, kv-cache]
aliases: ["ADR-004"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-004: KV-cache-first prompt assembly

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Assemble every prompt as **[stable prefix] + [append-only volatile tail]** with an explicit cache breakpoint after the stable prefix. Stable prefix = system prompt + full tool definitions (fixed order) + few-shot exemplars. Volatile tail = task state, recited `todo.md`, appended observations/tool results (references, not blobs).

**Context.** Cached and uncached input tokens can differ by roughly an order of magnitude in price, and a typical agent task runs on the order of 50 tool calls with an input:output token ratio near 100:1 — so input cost dominates almost entirely ([Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)). Provider prompt caching works on **prefix match**: stable content first, a cache breakpoint, then volatile content ([Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)). [[P1]]/[[P2]].

**Rationale.** Maximizing the invariant prefix maximizes cache reuse across turns and across requests within a tenant/session. No per-second timestamps in the prefix; deterministic JSON key ordering; append-only tail.

**Consequences.**
- (+) Reported production impact of correct prefix caching on long-horizon agentic work is roughly a 45–80% API cost reduction and a 13–31% improvement in time-to-first-token ([Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)).
- (+) KV-cache hit rate becomes a measurable, optimizable metric (surfaced in [[§5.4]]).
- (−) Misuse is worse than not caching: a cache write carries a premium, so a prefix that keeps changing means paying the write premium and never collecting the discount.
- (−) Discipline required: any code that mutates the prefix is a defect. Enforced in review and via a `prefix_hash` observability check.

**Alternatives considered.** Rebuild prompt each turn for "freshness" — rejected, destroys cache. Putting volatile data early for recency — rejected, breaks the cacheable prefix.
