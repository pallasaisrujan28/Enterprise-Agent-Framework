---
title: "Components and Interfaces"
type: hub
tags: [hub]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-04T10:12:35+00:00
---

# Components and Interfaces

Consolidated index of every framework component, its interface surface, and the axis it scales on. Details are in the referenced sections.

| Component | Interface (primary operations) | Responsibility | Scales with |
| --- | --- | --- | --- |
| Agent Gateway ([[§2.2]]) | `invoke(InboundRequest) -> Accepted \| Rejected` | AuthN, schema validation, rate limits, input rails | Request rate |
| Policy Decision Point ([[§3.2]]) | `authorize(request, bundle) -> Decision` | Tenant/agent tool grants, arg constraints, budgets | Decision rate (cached) |
| Classification (§[[ADR-013]]) | `classify(request) -> RoutingDecision`, `log_routing_outcome(decision, outcome)` | Declared-intent short-circuit, else one Bedrock call. One swappable seam; decisions and outcomes logged but not yet consumed | Request rate (bounded by Bedrock quota) |
| Planner Sub-agent (§[[ADR-002]]) | `plan(task) -> TaskPlan`, `replan(TaskPlan, errors) -> TaskPlan` | Decomposition, `todo.md` ownership, re-planning | Concurrent tasks |
| Prompt Assembler ([[§3.1]].4) | `assemble(session, plan, mask) -> AssembledPrompt` | Stable prefix (tool defs + skill index) + append-only tail, `prefix_hash` emission | Turns/sec |
| Skills Engine (§[[ADR-002b]]) | `load_skill`, `load_skillset`, `build_skill_index`, `validate_against_catalog`, `validate_scopes`, `load_skill_body`, `read_skill_reference`, `run_skill_script` | In the request path. Loads skills across three levels — metadata in the prefix, bodies on demand, bundled resources on demand with **scripts executed rather than read**; refuses at load anything it cannot enforce; can never widen access | Skill count (index has a ceiling) |
| Skill Registry (§[[ADR-002b]]) | `promote_skill`, `evaluate_skill`, `grant_skill`, `rollback_pointer`, `skill_search` | Never in the request path. Versioned skill artifacts, eval-gated promotion, canary and pointer rollback under [[ADR-014]], policy grants per agent | Artifact count and version retention |
| Sub-graph Registry ([[§2.12]].1) | `invoke_subgraph(name, args, handoff) -> SubAgentResult` | Compiled units with their own prefix and isolated context; invoked **as a tool**; depth-limited at dispatch | Sub-graph count (parent topology constant) |
| Retry / Failure Scoping ([[§2.13]]) | `detect_failure_loop`, `distill_failure`, `reattempt_task` | Three retry scopes; distilled lesson forward, full record durable; breaks identical-failure loops | Failure rate |
| Model Proxy (§[[ADR-011]]) | `complete(AssembledPrompt) -> Completion` | Model routing, prompt caching, egress redaction | Turns/sec |
| Executor Sub-agent ([[§6.2]]) | `run(SubAgentHandoff) -> SubAgentResult` | Isolated agentic loop per specialty | Concurrent tasks |
| Tool Dispatch ([[§3.3]]) | `call(ToolCall) -> ToolResult` | Trace propagation, offload on large results | Tool calls/sec |
| MCP Gateway (§[[ADR-003]]) | `dispatch(ToolCall) -> ToolResult` | Authz re-check, schema validation, registry resolve, breaker | Tool calls/sec |
| Tool Pool (per domain) | MCP tool schema per tool | Execution, containment, egress allowlist | Per-domain load |
| Tool Registry ([[§3.1]].5) | `resolve(tool_name) -> RegistryEntry`, `watch()` | Strongly consistent `tool -> pool` mapping | Tool count |
| Compaction Worker (§[[ADR-006]]) | `compact(session, trigger, observed_tokens) -> CompactionEntry`, `choose_split_boundary`, `precheck_prompt_pressure`, `classify_overflow_error` | Tiered, restorable, async, prefix-preserving; **appends** a compaction entry rather than rewriting; never splits a tool call from its result; signals mid-turn pressure instead of compacting inline; summarization is a pluggable provider with built-in fallback | Session volume |
| Memory Flush (§[[ADR-006c]]) | `should_flush_memory`, `flush_memory(session, model_route)` | A **silent turn** before compaction in which the agent writes durable reasoning state; once per cycle, cheap-model routable, skipped on a read-only workspace | Compaction cycles |
| Delivery Layer (§[[ADR-006d]]) | `is_silent`, `suppress_if_silent` | Strips the sentinel and suppresses silent-turn output on **both** the buffered and streaming paths; silent turns stay fully logged and costed | Turns/sec |
| Transcript Store ([[§3.1]].11) | `append_entry`, `fork(parent_entry_id)`, `visible_history`, `touch_freshness` | Append-only **tree** of entries; forking for sub-graph spawn and scope-2 re-attempt; refuses a fork during an active parent run; fresh token counters per child; freshness updated per event source | Session volume |
| Guardrail Pipeline ([[§2.6]]) | `check(stage, text) -> GuardrailVerdict` | Input/retrieved/output rails | Turns/sec |
| PII Vault ([[§2.7]]) | `tokenize(text) -> (text, tokens)`, `rehydrate(tokens) -> values` | Reversible tokenization, tenant-scoped keys | PII volume |
| HITL Controller ([[§2.4]]) | `gate(candidate) -> Approved \| Edited \| Rejected` | Approval queues, obligations from policy | Escalation rate |
| Knowledge Layer (§[[ADR-007]]) | `retrieve(RetrievalQuery, RetrievalStrategy) -> RetrievalResult` | Vector + fulltext + graph behind a versioned code strategy | Corpus size, QPS |
| Document Sync Pipeline ([[§3.6]].1) | `sync_documents(config, since) -> SyncReport` | Idempotent sync **into Terraform-created resources**; never provisions | Corpus size, change rate |
| Ingestion Config Validator ([[§3.6]].2) | `validate_ingestion_config(raw) -> IngestionConfig` | Narrow typed validation, fail-closed; asserts the target index exists and is partition-scoped | Corpus count |
| Retrieval Accuracy Harness ([[§3.6]].4) | `score_retrieval(strategy, labeled_set) -> RetrievalAccuracyReport` | recall@k, MRR/nDCG, groundedness, latency, cost; CI regression gate | Labeled-set size |
| Tool Catalog ([[§3.8]]) | `register_mcp_server`, `cut_catalog_version`, `pin_catalog`, `tool_search` | Versioned tool definitions; per-session pinning; new tools with no platform redeploy | Tool count |
| Sandbox Runtime ([[§2.10]]) | POSIX filesystem + shell/code execution | T0 scratch the agent navigates with `file_*` tools | Concurrent sessions |
| Session Storage Tiers (§[[ADR-016]]) | `put_artifact`, `get_artifact`, `promote`, `manifest_append` | T0 scratch / T1 session-durable / T2 archive / T3 hot state | Artifact volume |
| External Memory (§[[ADR-006]]) | `put(bytes) -> Reference`, `get(Reference) -> bytes` | Agent working memory, restorable artifacts | Artifact volume |
| Learned Router / Bandit Policy (§[[ADR-008]] Phase B) | `route(features) -> arm`, `update(arm, reward)` | Model selection and escalation from logged outcomes | Decision volume |
| Trajectory Store ([[§3.1]].7) | `append(TrajectoryRecord)`, `query(filters)` | Durable record of every request | Traffic |
| Artifact Registry (§[[ADR-014]]) | `resolve(tenant, agent) -> version`, `promote(version, env)` | Immutable prompts/policies, canary pointers | Agent × tenant count |
| Eval Harness ([[§5.3]], [[§5.4]]) | `run(dataset, artifact_version) -> Scores` | Quality gate for both improvement tracks | Dataset size |
