---
title: "Property 31: System-generated events do not extend session freshness"
type: property
tags: [property, session-state]
aliases: ["Property 31"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 31: System-generated events do not extend session freshness

Part of [[correctness-properties|Correctness Properties]].

For all system-generated events `e` — heartbeats, scheduled wakeups, internal notifications, compaction bookkeeping, memory flushes — applied to session `s`: `s.updated_at` may advance and `s.last_interaction_at` is **unchanged**. For all genuine user and channel turns, **both** advance. `last_interaction_at` is the only input to idle expiry.

Without this, a background job keeps an abandoned conversation alive indefinitely, sessions never expire, the per-tenant expiry policy becomes decorative, and the storage bill does not. `session_started_at` is written once at session creation and never mutated. *(property-based: arbitrary interleavings of system events and real interactions)*
