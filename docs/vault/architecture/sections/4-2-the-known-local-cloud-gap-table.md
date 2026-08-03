---
title: "4.2 The known local/cloud gap table"
type: section
tags: [section, local-first]
aliases: ["§4.2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 4.2 The known local/cloud gap table

Part of [[4-service-selection-and-local-first-development|4. Service Selection and Local-First Development]].

Properties that **cannot** be validated locally, listed so nobody is surprised at the checkpoint. Each one is a **mandatory re-validation item** when the move to cloud happens ([[§8]]).

| Property | What local gives | What must be re-validated in cloud |
| --- | --- | --- |
| **Object-store latency** | MinIO on a local disk — functionally correct S3 API, unrelated latency profile | Every latency assumption in the [[ADR-016]] tiering (T1 single-digit-ms, T1→T2 archive timing) and the cost model built on it |
| **Sandbox isolation strength** | Docker with dropped capabilities, read-only root, no network | The **isolation boundary for model-authored code** against a gVisor/Firecracker-class runtime. **Not proven locally** |
| **Autoscaling behaviour** | Nothing — Compose has no HPA, no KEDA, no node pressure | Every per-tier saturation signal in [[§5.7]].1, scale-down stabilization against bursty traffic, and that node-group provisioning limits actually clamp ([[§5.7]].3) |
| **Network-policy isolation** | Coarse Compose networks; a service can be reachable that should not be | Default-deny per namespace with explicit egress allowlists — "the `db` pool cannot reach the internet" as an enforced fact ([[ADR-003]]) |
| **IAM / least privilege** | No equivalent at all | Per-workload ServiceAccount → least-privilege IAM, and that a sandbox pod has no IAM path to tenant data beyond its own session prefix |
| **Secrets handling** | A `.env` file behind the resolver interface | Secrets Manager + KMS behind the *same* interface, plus per-tenant vault keys ([[ADR-009]]) |
| **Multi-AZ behaviour** | Nothing — one machine | The T1 single-AZ tradeoff and executor co-location ([[§5.7]].3), and behaviour under an AZ loss |
| **Real multi-tenant load and isolation** | Two synthetic tenants at hand-driven volume | Cross-tenant isolation under concurrent real load, quota fairness, and whether one tenant can starve another |

Stated plainly, because it affects how the rest of the document should be read: **the [[§5.7]] scaling model is a hypothesis, not a validated design, until it is load-tested on a cluster.** Everything in it is reasoned from the workload shape rather than measured, and the reasoning may be right and still not survive contact with an autoscaler.
