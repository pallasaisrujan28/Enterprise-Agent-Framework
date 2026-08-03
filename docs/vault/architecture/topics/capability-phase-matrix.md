---
title: "Capability → Phase Matrix"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# Capability → Phase Matrix

Part of [[8-phased-delivery-plan|8. Phased Delivery Plan]].

Every major capability in this document, assigned. An item appearing earlier than its phase is scope creep; later is technical debt.

| Capability | Phase | ADR / Section |
| --- | --- | --- |
| **Service selection recorded — choice, rejected alternative, tradeoff, local image, per concern** | **0** | [[ADR-019]], [[§4.1]] |
| **Graph store resolved to one query language across environments (Neo4j both)** | **0** | [[§4.1]].1 |
| **Minimal Compose profile healthy on one `docker compose up`** | **0** | [[ADR-019]], [[§4.3]] |
| **Compose conventions: pinned tags, health checks, `service_healthy` ordering, named volumes** | **0** | [[§4.3]], steering |
| **The three CI gates — lint/format, dependency audit, image scan, secret scanning** | **0** | [[§4.4]] |
| **Portability seam: secret resolver interface (no direct credential reads)** | **0** | [[ADR-019]], [[§4.1]] |
| **Portability seam: object-store interface over the S3 API** | **0** | [[ADR-019]], [[§4.1]] |
| **Portability seam: OpenTelemetry instrumentation (no vendor SDK)** | **0** | [[ADR-019]], [[§4.1]] |
| **Hello-world request crossing one layer boundary with a visible trace** | **0** | [[§4.3]] |
| **Local/cloud gap table maintained as the re-validation checklist** | **0** (and reviewed at every checkpoint) | [[§4.2]] |
| **Cloud readiness checkpoint reviewed after every three features, with a dated decision record** | **Recurring from 1** | [[ADR-019]], [[§8]] |
| Terraform ownership of all cloud resources | **Post cloud checkpoint** | [[ADR-015]], [[ADR-019]], [[§2.11]] |
| Stable-prefix prompt assembly, `prefix_hash` | 1 | [[ADR-004]], [[§3.1]].4 |
| **Skills: registry, Level-1 metadata index in prefix, on-demand Level-2 body loading, manifest validation** | **1** | [[ADR-002b]], [[§2.12]] |
| **Skills Level 3: bundled `scripts` / `references` / `assets`, with scripts EXECUTED at zero context cost** | **1** | [[ADR-002b]], [[Property 25]] |
| **Skill eval cases mandatory + enforced as a promotion gate** | **1** | [[ADR-002b]], [[§5.5]] |
| **Skill attach/detach by policy grant + pointer promotion (no redeploy)** | **1** | [[ADR-002b]], [[ADR-014]] |
| **Transcript as a TREE (`id` + `parent_id`); spawn and scope-2 re-attempt are branches** | **1** (data model — expensive to retrofit) | [[ADR-006]] rule 4, [[§3.1]].11 |
| **Compaction as an appended `CompactionEntry` (`first_kept_entry_id`, `tokens_before`)** | **1** (data model) | [[ADR-006]] rule 3, [[§3.1]].11 |
| **Tool-call/result pairing preserved across every compaction boundary** | **1** (a correctness bug if absent) | [[ADR-006]] rule 5, [[Property 27]] |
| **Fork size cap: oversized parent branch ⇒ ISOLATED child, flag ignored, not configurable** | **1** (a correctness bug if absent) | [[§2.12]].1, [[§3.1]].3, [[Property 30]] |
| **Three freshness timestamps; system events never extend `last_interaction_at`** | **1** (data model) | [[§2.10]], [[Property 31]] |
| **Per-tenant session reset/expiry policy (none / daily boundary / idle window)** | **1** | [[§2.10]] |
| **Scoped retry (step / task / re-plan), `distill_failure`, `FailureLesson`** | **1** | [[P6]], [[§2.13]], [[§3.1]].9 |
| **Failure-loop detection** | **1** | [[§2.13]], [[Property 22]] |
| Tool catalog version pinned per session | 1 | [[§3.8]], [[§3.1]].10 |
| Restorable offload T0 → T1, `Reference` re-fetch | 1 | [[ADR-006]], [[ADR-016]] |
| Session manifest in Redis (T3), stateless orchestrator | 1 | [[ADR-016]], [[§2.10]] |
| Trajectory capture to T2, LangSmith tracing | 1 | [[§3.1]].7, [[§5.3]] |
| **Deterministic structured-entity PII gate (regex + Luhn) + no-raw-PII-egress test** | **1** | [[ADR-009]] interim, [[§5.4]] |
| CI grows: types, unit, contract, skill validation, skill eval (on top of the Phase-0 three) | 1 | [[§4.4]] |
| Gateway authN + schema validation | 2 | [[§2.2]] |
| OPA policy bundles, per-agent tool allowlists, arg constraints, budgets | 2 | [[ADR-010]], [[§3.2]] |
| **Skill grants as policy; skill cannot widen access** | **2** | [[ADR-002b]], [[Property 18]] |
| Tenant partitioning + cross-tenant isolation gate | 2 | [[ADR-010]], [[Property 1]] |
| **Three-check authz split: user authn at L1, agent authn + tool authz + delegated user RBAC at L3** | **2** | [[ADR-010]], [[§3.2]] |
| **`on_behalf_of` on every tool call; access is the agent∩user intersection; user in the decision cache key** | **1** (data model — retrofitting an identity through every call path is archaeology) | [[ADR-010]], [[Property 32]] |
| Per-tenant rate limits (edge **and** orchestrator) | 2 | [[§3.2]].4 |
| MCP gateway, tool registry, mTLS, per-pool breakers | 2 | [[ADR-003]] |
| Default-deny NetworkPolicy per namespace (no Compose equivalent) | **Post cloud checkpoint** | [[ADR-003]], [[§4.2]] |
| **New-tool onboarding: MCP server registration, catalog version cut, grant, canary — no platform redeploy** | **2** | [[§3.8]] |
| **Tenant-supplied MCP servers with gateway-enforced schema, egress, authz, audit** | **2** | [[§3.8]].2 |
| Tool masking: `auto` / `required` / `specified`, prefix families | 2 | [[ADR-005]] |
| **Classification: declared-intent short-circuit, else one Bedrock call** | **1** (it is on the vertical slice's critical path) | [[ADR-013]] |
| **`REROUTE` outcome + re-route path** | **2** | [[ADR-013]], [[§3.1]].3 |
| Guardrail pipeline (input, retrieved, output rails) at the interim PII stage | 2 | [[ADR-009]], [[§2.6]] |
| HITL approval gates, interrupt/resume, escalation paths | 2 | [[§2.4]], [[§2.5]] |
| Audit events, policy fixtures in CI | 2 | [[§3.2]].4, [[§5.5]] |
| **Document sync pipeline (code) into Terraform-created resources** | **3** | [[ADR-015]], [[§3.6]].1 |
| **Narrow typed ingestion config (chunking + embeddings only), fail-closed validation** | **3** | [[ADR-015]], [[§3.6]].2, [[Property 17]] |
| Vector RAG + fulltext + hybrid fusion + reranking, as versioned code artifacts | 3 | [[ADR-007]], [[§3.6]].3 |
| **Retrieval accuracy harness (recall@k, MRR/nDCG, groundedness) + CI regression gate** | **3** | [[§3.6]].4, [[§5.5]] |
| GraphRAG: entity extraction, community summaries, multi-hop, mode selection | 3 (second half, opt-in) | [[ADR-007]] |
| Planner sub-agent, `todo.md` recitation, complexity-scaled handoff | 4 | [[ADR-002]] |
| `submit_results` with constrained decoding | 4 | [[§3.1]].3 |
| Read-only verifier node (no self-verification) | 4 | [[ADR-012]] |
| **Sub-graph registry, agent-as-tool invocation, enforced depth limit** | **4** | [[§2.12]].1, [[Property 24]] |
| ~~Self-hosted classifier tiers~~ | **cut** | [[ADR-013]] — rejected for now; restore on a regulated tenant or a routing-cost signal |
| **Legacy node collapse — most nodes become SKILLS, classifier nodes collapse into one `classify()` call** | **4** | [[ADR-002b]], [[ADR-013]], [[§6.3]] |
| **`skill_search` and `tool_search` discovery (only past their ceilings)** | **4** | [[ADR-002b]], [[§3.8]].3 |
| Lossless trimming, anchored summarization, self-compaction tool, all triggers | 4 | [[ADR-006]], [[§2.10]] |
| **Pre-compaction memory flush (soft threshold, once per cycle, cheap-model route, read-only skip)** | **4** | [[ADR-006c]], [[Property 28]] |
| **Silent turns (sentinel suppressed on buffered AND streaming paths)** | **4** | [[ADR-006d]], [[Property 29]] |
| **Mid-turn precheck that raises a structured signal instead of compacting inline** | **4** | [[ADR-006]] rule 6 |
| **Overflow recovery: error-family detection, provider-reported count forwarded, synthetic count fallback, session mapping preserved** | **4** | [[ADR-006]] rule 7, [[§2.10]] |
| **Pluggable summarization provider with automatic built-in fallback; aborts re-thrown** | **4** | [[ADR-006]] rule 8 |
| Bounded observation variation after the breakpoint | 4 | [[ADR-006b]] |
| Model routing by task type via model proxy | 4 | [[ADR-011]] |
| Full metric set + alarms, CI cost gate | 4 | [[§5.6]], [[§5.5]] |
| DeepEval full suite, red team, chaos, load | 4 | [[§5.4]] |
| Harness-quality test (stronger-model swap) | 4 | [[§5.3]], [[ADR-012]] |
| RL Phase A — GEPA/DSPy prompt optimization, eval-gated, PR-based | 5 | [[ADR-008]] |
| RL Phase B — learned routing, contextual bandits, verifier/judge model | 5 | [[ADR-008]] |
| RL Phase C — RLVR/GRPO on a small open classifier model (optional) | 5 (conditional) | [[ADR-008]], [[ADR-013]] |
| **Self-hosted PII: local NER (Presidio / GLiNER-PII class)** | **6 (final)** | [[ADR-009]], [[§2.7]] |
| **PII vault, reversible tokenization, authorized re-hydration** | **6 (final)** | [[ADR-009]], [[§2.7]] |
| **Tokenized-only persistence across all surfaces; broadened egress gate** | **6 (final)** | [[Property 11]], [[§2.7]] |
| **Lifting the regulated-data onboarding restriction** | **6 (final)** | [[ADR-009]], [[§7.10]] |
| Managed PII detection service (interim stopgap) | 1–5, optional | [[ADR-009]] |
| Kubernetes / EKS deployment, Helm packaging, one namespace per layer | **Post cloud checkpoint** | [[ADR-018]], [[ADR-019]], [[§5.1]] |
| Per-tier autoscaling (HPA / KEDA), node groups, Cluster Autoscaler or Karpenter, provisioning limits | **Post cloud checkpoint** | [[§5.7]] (hypothesis until then) |
| PDBs, `preStop` drain, `terminationGracePeriodSeconds`, rollout drills against a node drain | **Post cloud checkpoint** | [[§5.7]].4, [[§4.2]] |
| gVisor / Firecracker-class sandbox isolation for model-authored code | **Post cloud checkpoint** | [[ADR-016]], [[§4.2]] |
| Per-workload ServiceAccount → least-privilege IAM; Secrets Manager + KMS behind the resolver | **Post cloud checkpoint** | [[ADR-019]], [[§4.2]] |
| Managed service endpoints (S3, Aurora, ElastiCache) — a config swap, not a code change | **Post cloud checkpoint** | [[ADR-019]], [[§8]] |
| Dev + prod deployment pipelines, staging, canary, automatic rollback, `terraform validate` | **Post cloud checkpoint** | [[§5.5]], [[§4.4]], steering |
| Multi-AZ behaviour and the T1 single-AZ co-location tradeoff | **Post cloud checkpoint** | [[§5.7]].3, [[§4.2]] |
| Re-validation of every property in the local/cloud gap table | **Post cloud checkpoint** (mandatory) | [[§4.2]], [[§8]] |
| Dedicated-cluster tenant tier | On contract demand, **post cloud checkpoint** | [[§5.1]], [[§5.7]].6 |
---
