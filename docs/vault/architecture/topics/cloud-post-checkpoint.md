---
title: "Cloud (post-checkpoint)"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Cloud (post-checkpoint)

Part of [[dependencies|Dependencies]].

**None of this is installed.** It arrives only when the checkpoint in [[§8]] passes, and each entry is the managed counterpart of a local dependency above — reached through the same interface, selected by config, with no application code change ([[P16]], [[ADR-019]]).

| Concern | Managed counterpart | Substitution cost |
| --- | --- | --- |
| Session hot state | **ElastiCache** for Redis | Config only — identical protocol |
| Object store | **S3 Express One Zone** (T1) + **S3 Standard** (T2, artifact bundles) | Config only — identical API. **Latency profile must be re-measured** ([[§4.2]]) |
| Relational + vector | **Aurora PostgreSQL + pgvector** | Config only — identical extension |
| Fulltext / hybrid | Managed **OpenSearch** | Config only — same engine family |
| Graph store | **Neo4j** self-hosted or Aura | Config only, by the [[§4.1]].1 decision |
| Tool registry | **etcd** on the cluster (deliberately not DynamoDB — [[§4.1]]) | Config only |
| Model access | **Amazon Bedrock** plus external providers, behind the same model proxy | Config only. The proxy becomes an **HA requirement** |
| Traces / metrics | **X-Ray + CloudWatch**, or the same self-hosted stack | Config only — OTel is the seam |
| Secrets | **Secrets Manager + KMS** behind the resolver interface | Config only |
| Sandbox isolation | **gVisor- or Firecracker-class** runtime on a dedicated node group, plus **NVMe instance-store nodes** for T0 | **Not a config swap — a real isolation upgrade, and a mandatory re-validation** ([[§4.2]]) |

**Infrastructure as code (post-checkpoint):** **Terraform** — owns the lifecycle of every cloud resource: vector and fulltext indexes, graph store, buckets (T1/T2 and artifact bundles), Redis, IAM, KMS keys, node groups, and network policy ([[ADR-015]]). Nothing in the application path provisions a resource. **There is no Terraform for local** — Compose covers the local resource lifecycle, and `terraform validate` earns a CI gate only post-checkpoint ([[§4.3]], [[§4.4]]).

**Orchestration (post-checkpoint; decided, not substitutable — [[ADR-018]]):** **Kubernetes**, with **Amazon EKS** as the managed control plane; **Helm** for workload packaging; **ECR** for images with immutable tags. One namespace per architectural layer, default-deny NetworkPolicy per namespace, ServiceAccount per workload with least-privilege IAM.

**Autoscaling stack (post-checkpoint, [[§5.7]]):** **HPA** with custom and external metrics; **KEDA** for queue- and event-driven scaling; **Cluster Autoscaler or Karpenter** for node capacity with hard per-node-group provisioning limits; a metrics adapter to expose the [[§5.6]] platform metrics to HPA. All of it a hypothesis until load-tested ([[§4.2]]).

**Cloud platform (post-checkpoint):** ALB/API Gateway, WAF, OTel Collector as a DaemonSet, CloudWatch, X-Ray, Kinesis Firehose + S3 + Athena for the trajectory lake and cost analytics, and the full GitHub Actions deployment pipelines ([[§5.5]]).
