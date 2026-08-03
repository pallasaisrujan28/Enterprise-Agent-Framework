---
title: "ADR-006d: Silent turns — agent turns whose output is never delivered"
type: adr
tags: [adr, compaction]
aliases: ["ADR-006d"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-006d: Silent turns — agent turns whose output is never delivered

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Support **silent turns**: an agentic turn whose output is deliberately **not delivered** to the user. The assistant output begins with an exact sentinel token; the delivery layer strips it and suppresses the message. **Streamed partial chunks beginning with the sentinel are suppressed on the streaming path as well as the buffered one.** Silent turns are restricted to genuine background work.

**Context.** Two places in this design need an agent turn with no user-facing output. The pre-compaction memory flush ([[ADR-006c]]) is one — a user should never watch an agent file its own notes. Progress emission during a long sub-graph is the other: [[§2.12]].1's fan-out can leave a user staring at nothing for tens of seconds, and the clean fix is a turn that updates internal state without producing a message.

**Rationale.** Suppression at the **delivery layer** rather than at generation keeps the turn ordinary everywhere else — it appears in the transcript, in the trajectory record, in token accounting, and in evals like any other turn. Only delivery differs. That is the property that matters: silent does not mean unlogged.

**The part that is easy to get wrong, called out because it is a leak and not a bug.** Suppressing the buffered response is the obvious half. **A streaming path that emits chunks as they arrive will leak the first chunk of a silent turn before anything checks the sentinel** — the user sees a fragment of the agent's private housekeeping appear and vanish. Both paths must check, and the streaming check must happen on the **first partial chunk**, before it is flushed to the client. This is [[Property 29]], and it is tested on **both** paths precisely because passing on one and failing on the other is the realistic defect.

**Constrained deliberately.** Silent turns are for **genuine background or no-delivery work** — housekeeping, internal state updates, progress bookkeeping. They are **not** a mechanism for handling ordinary actionable requests quietly. An agent that answers a real question on a silent turn has not been discreet, it has dropped the response, and the user has no way to tell the difference between that and a hang. Review treats an actionable silent turn as a defect.

**Consequences.**
- (+) Makes [[ADR-006c]] possible at all, and gives the [[§2.12]].1 silence problem a mechanism rather than a workaround.
- (+) Silent turns remain fully observable — logged, costed, and evaluable — because only delivery is suppressed.
- (−) A sentinel-token protocol is a string contract, and string contracts rot. It needs an exact-match test on both delivery paths and a test that a *non*-silent turn beginning with similar text is still delivered.
- (−) The mechanism is abusable in exactly the way described above, and the constraint against it is a review rule rather than something the type system enforces.

**Alternatives considered.** **(a) A boolean flag on the turn record instead of a sentinel** — rejected in this design only because the sentinel survives the model boundary: the flag has to be set by whatever *requested* the turn, and the memory flush is requested by the compaction path while the output is produced by the model, so the marker has to travel with the output. **(b) Run housekeeping outside the agentic loop entirely** — rejected for the flush specifically, because the whole value of [[ADR-006c]] is that **the agent** decides what to save; a non-agentic writer is back to guessing.
