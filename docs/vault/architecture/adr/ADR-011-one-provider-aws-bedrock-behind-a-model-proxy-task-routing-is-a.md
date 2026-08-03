---
title: "ADR-011: One provider (AWS Bedrock) behind a model proxy; task routing is a later config change"
type: adr
tags: [adr, model-routing]
aliases: ["ADR-011"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# ADR-011: One provider (AWS Bedrock) behind a model proxy; task routing is a later config change

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** **All model calls go to AWS Bedrock, in every environment including local development.** They go through a **model proxy** that owns provider routing, prompt caching behaviour, and PII redaction. Routing *by task type* — a cheaper model for classification, a stronger one for reasoning — is a **config change behind that proxy and is not built now**. Start with one model for everything.

**Context.** Two questions were previously answered as one. "Which provider?" and "how many models, chosen how?" are separate, and collapsing them produced a design that needed a routing policy before it needed a working request.

**Bedrock is used locally too, and that is a deliberate exemption from local-first ([[ADR-019]]).** The rest of the stack runs as pinned container images on a developer machine; the model does not. Reasons, in order of weight:

1. **Local inference is not a smaller version of the real thing, it is a different thing.** CPU inference on a laptop distorts latency measurement badly enough that any number measured against it is misleading — and latency is one of the things this platform is being designed around.
2. **A frontier-class model cannot be run locally at all.** Substituting a small local model means the harness is being developed against different behaviour than it will ship on, which is the one kind of local/cloud gap that produces rework rather than surprises.
3. **It removes a whole service class from the local stack** — no model runtime, no GPU question, no model-weight downloads in developer setup.

This is the **only** exemption to [[P16]] in the platform, and the seam is still honoured: application code calls the model proxy, never Bedrock directly, so swapping or adding a provider stays a config change. What is exempted is the *deployment* rule, not the *interface* rule.

**Consequences.**
- (+) One provider, one credential path, one set of quotas. Local and cloud behaviour are identical where it matters most.
- (+) No local model-serving runtime, no GPU dependency for development.
- (+) The proxy seam means adding a second provider or per-task routing later is config, not a refactor.
- (−) **Local development now requires AWS credentials and incurs real spend.** Previously the local stack was free to run; it is not any more. Per-developer cost needs a budget and an alert, not an assumption.
- (−) **No offline development.** No network, no agent. This is a real developer-experience cost.
- (−) A single-provider dependency is a concentration risk, accepted deliberately. The proxy is what keeps it reversible.
- (−) The proxy is on the hot path and must be cache-aware.

**Alternatives considered.**
- **Task-type routing across several providers from day one (the previous decision)** — rejected as premature. It requires a routing policy, per-task quality baselines, and multi-provider credentials before there is a single measured task.
- **A local model for development, Bedrock in cloud** — rejected, and this is the substantive one. It is the cheapest option and it silently develops the harness against the wrong behaviour and the wrong latency profile. The gap would surface as rework at exactly the point it is most expensive.
- **Per-sub-agent hard-coded provider clients** — rejected; no central caching or redaction, and it destroys the seam that makes this decision reversible.
