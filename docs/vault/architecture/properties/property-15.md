---
title: "Property 15: Session write serialization"
type: property
tags: [property, session-state]
aliases: ["Property 15"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 15: Session write serialization

Part of [[correctness-properties|Correctness Properties]].

For all sessions: concurrent writes to the same `tenant_id:session_id` serialize under a lock or transactional write, so no interleaved or partially-applied history is ever observable. *(property-based: arbitrary concurrent write schedules)*
