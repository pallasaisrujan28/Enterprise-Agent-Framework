---
title: "Document Structure"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# Document Structure

Part of [[overview|Overview]].

This document is organized around the required deliverables plus three closing sections:

1. **Architecture Decisions** — ADR-style records (decision, context, rationale, consequences, alternatives).
2. **High-Level Architecture** — component and flow diagrams (framework components only), human-in-the-loop, failures/escalations, guardrails, PII.
3. **Low-Level Architecture** — data contracts between components, the access-policy model (user authn at L1, agent authn plus tool authz plus user RBAC at L3), interaction mechanics, and an end-to-end single-request walkthrough.
4. **Service Selection and Local-First Development** — *current state*: every service with its rationale and accepted tradeoff, the known local/cloud gap table, the local Compose topology and profiles, and the three CI gates that are actually wired up.
5. **AWS Deployment & Evaluation** — ***future state, not built***: deployment topology, LangSmith evaluation, DeepEval automated testing, the target CI/CD pipeline, and the scaling model. Gated by the checkpoint in [[§8]]. (LangSmith and DeepEval are the exception — both work from local development today.)
6. **Correcting the Current LangGraph Architecture** — a direct assessment of the existing mega-graph approach and the migration path.
7. **Honest Tradeoffs & Counterarguments** — where this design is overkill, where the industry framing is marketing, where the recommended techniques can regress, and what local-first costs.
8. **Phased Delivery Plan** — [[Phase 0]] (local foundation and service selection) plus six phases, exit criteria per phase, the **cloud readiness checkpoint**, and a capability → phase matrix covering every capability in this document.

Closing reference sections consolidate the material for reviewers: **Components and Interfaces**, **Data Models**, **Correctness Properties**, **Error Handling**, **Testing Strategy**, **Dependencies**, and **References**.

Operational standards live in steering rules rather than being duplicated here: `.kiro/steering/local-development.md` (portability rules, Compose conventions, known gaps), `.kiro/steering/git-workflow.md` (branching, commits, and the CI gate-growth path), and `.kiro/steering/kubernetes-operations.md` (**future state** — not an active review gate while the platform runs on Compose).
