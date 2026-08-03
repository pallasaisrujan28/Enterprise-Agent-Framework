---
title: "Data Models"
type: hub
tags: [hub, model-routing]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# Data Models

Every contract is defined in [[§3.1]]; this is the index plus the two persistence models that live outside the request path.

| Model | Defined in | Crosses |
| --- | --- | --- |
| `InboundRequest`, `TenantContext` | [[§3.1]].1 | Client → Gateway → Orchestrator |
| `GuardrailVerdict`, `PiiToken` | [[§3.1]].2 | Rails → Orchestrator → Vault |
| `TaskPlan`, `TodoItem`, `SubAgentHandoff`, `SubAgentResult`, `RerouteHint` | [[§3.1]].3 | Planner ↔ Executors ↔ Sub-graphs ↔ Cascade |
| `AssembledPrompt`, `ToolDef`, `SkillIndexEntry` | [[§3.1]].4 | Assembler → Model Proxy |
| `ToolCall`, `ToolResult`, `RegistryEntry` | [[§3.1]].5 | Dispatch → MCP Gateway → Pools |
| `RetrievalQuery`, `RetrievalResult` | [[§3.1]].6 | Executors → Knowledge Layer |
| `TrajectoryRecord`, `TokenLedger`, `RoutingDecision`, `AttemptRecord` | [[§3.1]].7 | Everything → Observability (and the cascade training set) |
| `FailureLesson` | [[§3.1]].9 | Retry scoping → fresh executor (scope 2) |
| `SkillManifest`, `BundledResources`, `Skill` | [[ADR-002b]] | Skill Registry → Prompt Assembler (L1) / Skill Loader (L2) / Sandbox (L3 scripts) |
| `SkillIndexVersion`, `ToolCatalogVersion`, `McpServerRef` | [[§3.1]].10 | Artifact registry → session pinning → prompt prefix |
| `TranscriptEntry`, `CompactionEntry` | [[§3.1]].11 | Session history (tree) ↔ Compaction Worker ↔ replay, evals, forks |
| `TenantPolicyBundle`, `AgentPolicy`, `ToolGrant`, `ArgConstraint` | [[§3.2]].1 | Policy Store → PDP |
| `Decision` | [[§3.2]].2 | PDP → Gateway PEP, MCP PEP |
| `SessionManifest`, `ManifestEntry` | [[§2.10]] | Orchestrator ↔ Redis (T3) ↔ Executors |
| `IngestionConfig`, `ChunkingConfig`, `EmbeddingConfig` | [[§3.6]].2 | Config artifact → Validator → Document sync |
| `SyncReport` | [[§3.6]].1 | Document sync → Observability |
| `RetrievalAccuracyReport` | [[§3.6]].4 | Accuracy harness → CI gate / GraphRAG on-off decision |

**Removed in this revision** (recorded rather than silently dropped, per [[ADR-015]]): the knowledge-pipeline YAML config model, the agent-graph YAML config model, and `ValidatedConfig` / `ValidationErrors` for the general pipeline loader. Infrastructure moved to Terraform, pipelines and agents to code, and the only surviving config surface is `IngestionConfig`. Capability configuration is now `SkillManifest` ([[ADR-002b]]).

Two additional persisted models:

```pascal
STRUCTURE ArtifactVersion            // immutable; ADR-014
  artifact_id: String                // "prompt:support_resolver" | "policy:tnt_4471"
  version: String                    // content hash
  body: Bytes                        // prompt text / policy bundle
  eval_scores: Map<String,Float>     // scores that justified promotion
  provenance: Enum{HUMAN, TRACK_B, TRACK_A}
  promoted_to: List<Enum{DEV, STAGING, CANARY, PROD}>
END STRUCTURE

STRUCTURE AuditEvent                 // §3.2.4; append-only, retention-bounded
  decision_id: UUID
  request_id: UUID
  tenant_id: String
  agent_id: String
  tool_name: String?
  outcome: Enum{ALLOW, ALLOW_WITH_OBLIGATION, DENY}
  reason: String                     // "explicit_deny" | "arg_constraint:query" | ...
  policy_version: String
  scrubbed_arguments: Json           // PII-tokenized before write
END STRUCTURE
```

**Validation rules that hold for all models:** deterministic key ordering on serialization ([[P2]]); `tenant_id` is populated only from a verified token claim; any field carrying free text has passed a guardrail stage before it is persisted; artifact bodies are immutable once written.
