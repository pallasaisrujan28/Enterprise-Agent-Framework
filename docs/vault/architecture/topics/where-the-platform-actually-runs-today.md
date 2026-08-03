---
title: "Where the Platform Actually Runs Today"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# Where the Platform Actually Runs Today

Part of [[overview|Overview]].

**Local, on Docker Compose. There is no cloud *deployment* — but there are cloud *dependencies* ([[ADR-019]]).** Most backing services are pinned container images on a developer machine; a small named set is consumed as real AWS services even locally, starting with Bedrock for every model call ([[ADR-011]]). So local development needs an AWS account, credentials, and a spend budget, and it does not work offline. CI is three gates — lint/format and vulnerability scanning — and nothing more. The AWS design in [[§5]] is the **eventual** target and is **not built**; it activates only when the **cloud readiness checkpoint** in [[§8]] passes, reviewed after every three features with **stay local** as the default answer.

This is a sequencing decision, not an architectural one. Every ADR below describes the platform's *shape* — layering, context engineering, skills, retry scoping, classification, storage tiering — and none of them is a statement about hosting. What the local-first decision adds is a hard portability rule ([[P16]]): the environment is a config choice, never a code path.

[[P16]] holds with one honest amendment: for the services we **consume** from AWS locally, the portability seam is a **credential and endpoint config**, not an image swap — there is no local substitute to swap to. The interface rule is intact (application code calls the model proxy, never Bedrock directly); what is exempted is the "runs as a local container" rule. The set of such services is named in [[ADR-019]] and capped by a stated test, so it does not grow silently.
