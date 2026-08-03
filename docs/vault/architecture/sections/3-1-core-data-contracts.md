---
title: "3.1 Core Data Contracts"
type: section
tags: [section]
aliases: ["§3.1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T23:15:35+00:00
---

# 3.1 Core Data Contracts

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

#### 3.1.1 Inbound Request & Tenant Context

```pascal
STRUCTURE InboundRequest
  request_id: UUID            // generated at gateway, used as trace root
  tenant_id: String           // from validated JWT claim
  agent_id: String            // logical agent the client is invoking
  session_id: String          // conversation/session key (Redis)
  input_text: String          // raw user input (pre-redaction)
  attachments: List<Reference>// optional object-store references
  metadata: Map<String,String>// channel, locale, etc. (NO per-second timestamps in prefix)
END STRUCTURE

STRUCTURE TenantContext
  tenant_id: String
  // ---- The DELEGATED USER: established at L1, carried everywhere (ADR-010) ----
  user: UserPrincipal         // WHO the agent is acting FOR. Never optional.
  // ---- The ACTING AGENT: authenticated separately at L3 ----
  agent_id: String            // which agent is acting
  scopes: List<String>        // granted OAuth scopes
  tool_allowlist: List<String>// per-agent allowed tool prefixes/names (OPA-resolved)
  rate_limit: RatePolicy      // requests/tokens per window
  data_partition: String      // isolation key for memory/registry/vault
END STRUCTURE

STRUCTURE UserPrincipal        // the on-behalf-of identity; the input to L3 check 3
  subject: String              // OAuth/JWT subject of the HUMAN, not the agent
  roles: List<String>          // resolved from the tenant's identity provider
  data_scopes: List<String>    // what THIS USER may reach, independent of the agent
  auth_time: Timestamp         // when the user actually authenticated
END STRUCTURE
```

**Why `user` is not optional, stated as a rule rather than a convention.** An agent's effective access is the **intersection** of what the agent is granted and what its delegated user may reach — never the union, and never just the agent's grant. Making the field nullable would make the intersection unenforceable in exactly the case that matters (a background or system-initiated turn), and "no user" would silently read as "no user restriction." Where a turn genuinely has no human behind it — a scheduled job, a system notification — it carries an explicit **service principal** with its own narrow `data_scopes`, not a null. This is [[Property 32]].

#### 3.1.2 Guardrail & PII Contracts

```pascal
STRUCTURE GuardrailVerdict
  stage: Enum{INPUT, RETRIEVED, OUTPUT}
  allowed: Boolean
  violations: List<Violation>       // e.g., JAILBREAK, TOPIC, MODERATION, UNGROUNDED
  redacted_text: String             // text with PII replaced by tokens
  pii_tokens: List<PiiToken>        // reversible token references (values in vault)
END STRUCTURE

STRUCTURE PiiToken
  token: String                     // e.g., "<PII_EMAIL_1>"
  entity_type: String               // EMAIL, PHONE, SSN, NAME, ...
  vault_ref: String                 // tenant-scoped encrypted vault key
END STRUCTURE
```

#### 3.1.3 Planner Handoff & Sub-agent Contracts

```pascal
STRUCTURE TaskPlan
  plan_id: UUID
  todo: List<TodoItem>              // recited at context tail (goal recitation)
  complexity: Enum{SIMPLE, COMPLEX}
END STRUCTURE

STRUCTURE TodoItem
  id: String
  description: String
  status: Enum{PENDING, IN_PROGRESS, DONE, BLOCKED}
  assigned_agent_type: String       // coding | research | math | ...

// Handoff scales with complexity (ADR-002 / P5)
STRUCTURE SubAgentHandoff
  handoff_id: UUID
  agent_type: String
  instructions: String              // minimal for SIMPLE tasks
  shared_trajectory_ref: Reference? // present only for COMPLEX tasks
  shared_fs_handle: Reference?      // sandbox/object-store scope for COMPLEX tasks
  allowed_tools: List<String>       // subset of tenant tool_allowlist
  granted_skills: List<String>      // skill names in the pinned skill index (ADR-002b)
  catalog_version: String           // pinned tool catalog version (§3.8)
  depth: Integer = 0                // sub-graph nesting depth; dispatch REJECTS depth > 2 (§2.12.1)
  parent_entry_id: String?          // branch point in the transcript TREE (§3.1.11); spawn is a FORK
  parent_branch_tokens: Integer     // size of the parent branch at spawn; see the cap below
  context_mode: Enum{MINIMAL, SHARED, ISOLATED}  // DERIVED, not requested — see the cap
  attempt_number: Integer = 1       // scope-2 re-attempt counter (§2.13)
  failure_lesson: FailureLesson?    // present ONLY on a scope-2 re-attempt; NEVER a raw trajectory
END STRUCTURE
```

**The size cap overrides the complexity flag ([[§2.12]].1, [[Property 30]]).** `context_mode` is *derived at dispatch*, never taken from the caller:

```pascal
PROCEDURE derive_context_mode(plan_complexity, parent_branch_tokens)
  INPUT:  plan_complexity ∈ {SIMPLE, COMPLEX}
          parent_branch_tokens (measured, not declared)
  OUTPUT: context_mode ∈ {MINIMAL, SHARED, ISOLATED}

  SEQUENCE
    // The defensive cap runs FIRST and is not conditional on the flag.
    IF parent_branch_tokens > PARENT_BRANCH_TOKEN_CAP THEN     // ~100K; NOT configurable
      RETURN ISOLATED
    END IF

    IF plan_complexity = COMPLEX THEN
      RETURN SHARED                    // trajectory ref + filesystem handle
    ELSE
      RETURN MINIMAL                   // instructions only
    END IF
  END SEQUENCE
END PROCEDURE
```

**Preconditions.** `parent_branch_tokens` is measured from the parent branch at spawn time, not supplied by the caller; `PARENT_BRANCH_TOKEN_CAP` is a build-time constant with no configuration override.
**Postconditions.** `context_mode = ISOLATED` whenever the cap is exceeded, for **every** value of `plan_complexity`. A `COMPLEX` handoff off an oversized parent is isolated, and this is not overridable at runtime.
**Loop invariants.** None — the procedure is branch-only, deliberately, so it cannot be made to do more than it does.

```pascal
// Structured return via submit-results tool with constrained decoding
STRUCTURE SubAgentResult
  handoff_id: UUID
  status: Enum{SUCCESS, PARTIAL, FAILED, REROUTE}   // REROUTE: wrong agent, not a failure (ADR-013)
  summary: String                   // compact, goes into orchestrator context
  artifacts: List<Reference>        // full outputs offloaded to external memory (P4)
  errors: List<ErrorRecord>         // always written durably (P6); context inclusion is scoped (§2.13)
  reroute_hint: RerouteHint?        // present iff status = REROUTE
END STRUCTURE

STRUCTURE RerouteHint                // ADR-013: the router must be recoverable, not perfect
  suggested_agent_type: String       // where this actually belongs
  observed_intent: String            // what the task actually looks like, in one line
  confidence: Float                  // executor's confidence in the suggestion
  // Logged with the original routing decision + tier; becomes a training label for T3/T4.
END STRUCTURE
```

#### 3.1.4 Prompt Assembly Contract (KV-cache-first)

```pascal
STRUCTURE AssembledPrompt
  // ----- STABLE PREFIX (never mutates within a session) -----
  system_prompt: String             // fixed text, no timestamps
  tool_definitions: List<ToolDef>   // FULL set from the PINNED catalog version, FIXED order (§3.8)
  skill_index: List<SkillIndexEntry>// name + ONE-LINE description ONLY; pinned per session (ADR-002b)
  few_shot: List<Exemplar>          // fixed exemplars
  cache_breakpoint: Marker          // explicit KV-cache boundary here
  // ----- VOLATILE TAIL (append-only) -----
  task_state: String                // compact
  todo_recitation: String           // todo.md re-rendered at the tail
  loaded_skill_bodies: List<String> // progressive disclosure: full bodies land HERE, never in the prefix
  failure_lesson: FailureLesson?    // scope-2 re-attempts only (§2.13); never a raw failed trajectory
  history: List<Message>            // append-only; tool results are REFERENCES
  tool_mask: LogitMask              // allowlist for THIS state (masking, not mutation)
END STRUCTURE

STRUCTURE SkillIndexEntry           // the ONLY part of a skill that costs prefix tokens
  name: String
  description: String               // hard length budget; enforced at skill validation
  version: String                   // for trajectory attribution
END STRUCTURE

STRUCTURE ToolDef
  name: String                      // consistent prefix: browser_*, db_*, file_*, search_*
  description: String
  input_schema: JsonSchema          // deterministic key ordering
```

**Assembly order (MUST be stable):** `system_prompt → tool_definitions (fixed order, pinned catalog) → skill_index (fixed order, pinned) → few_shot → [CACHE BREAKPOINT] → task_state → todo_recitation → loaded_skill_bodies → failure_lesson? → append-only history`. Three things vary per state without touching the prefix: the tool **mask** ([[ADR-005]]), which **skill bodies** are loaded ([[ADR-002b]] progressive disclosure), and whether a **failure lesson** is present ([[§2.13]]). The tool **definitions** and the **skill index** never change within a session — both are pinned at session start and change only at a version boundary. Any mutation of the prefix invalidates the cache and is treated as a defect; the assembler emits a `prefix_hash` span so cache-busting regressions are caught in observability.

#### 3.1.5 Tool Call & Result Contracts (through MCP Gateway)

```pascal
STRUCTURE ToolCall
  call_id: UUID
  tenant_id: String
  agent_id: String                  // the ACTING agent — authenticated at the MCP gateway
  on_behalf_of: UserPrincipal       // the DELEGATED user — required for L3 check 3 (ADR-010).
                                    // Without this the gateway can only check the agent, which
                                    // is the confused-deputy hole. Property 32.
  tool_name: String                 // resolved to a pool via registry
  arguments: Json                   // deterministic key ordering
  trace_context: SpanContext        // propagates the distributed trace
END STRUCTURE

STRUCTURE ToolResult
  call_id: UUID
  status: Enum{OK, TOOL_ERROR, TIMEOUT, CIRCUIT_OPEN}
  // Full vs compact representation (P3/P4):
  compact: String                   // short summary kept in context
  artifact_ref: Reference?          // full result offloaded to external memory
  metrics: ToolMetrics              // latency, bytes, pool, replica
END STRUCTURE

STRUCTURE RegistryEntry
  tool_name: String
  pool: String                      // e.g., "db-pool"
  network_policy: String
  circuit_breaker: BreakerPolicy
END STRUCTURE
```

#### 3.1.6 Retrieval Contracts (RAG + GraphRAG)

```pascal
STRUCTURE RetrievalQuery
  query_text: String
  strategy: Enum{VECTOR, GRAPH, HYBRID}   // router-selected (ADR-007)
  tenant_id: String
  top_k: Integer

STRUCTURE RetrievalResult
  chunks: List<Chunk>               // vector recall
  graph_context: List<GraphPath>    // multi-hop paths / community summaries
  citations: List<Reference>        // for grounding checks in output rails
```

#### 3.1.7 Observability Contract (the per-request trace)

```pascal
STRUCTURE TrajectoryRecord
  request_id: UUID
  tenant_id: String
  spans: List<Span>                 // gateway → orchestrator → tool pool
  llm_calls: List<LlmCallRecord>    // inputs/outputs/retrieved/tool calls/latency
  token_accounting: TokenLedger     // prompt/completion, cached vs uncached
  kv_cache_hit_rate: Float          // north-star cost metric (P1)
  guardrail_events: List<GuardrailVerdict>
  catalog_version: String           // tool catalog that governed this request (§3.8)
  skill_index_version: String       // skill index that governed this request (ADR-002b)
  skills_loaded: List<String>       // which skill bodies were actually disclosed, for eval attribution
  routing_decisions: List<RoutingDecision>  // tier, label, confidence, and outcome (ADR-013 training set)
  attempts: List<AttemptRecord>     // every attempt at every scope, INCLUDING failed ones (P6, §2.13)
  outcome: Enum{DELIVERED, ESCALATED, BLOCKED, FAILED}

STRUCTURE RoutingDecision           // logged for later; nothing trains on it yet (ADR-013)
  source: Enum{DECLARED, MODEL}     // declared intent short-circuit, or the Bedrock call
  label: String                     // chosen agent_type
  confidence: Float                 // MODEL only; DECLARED is certain by construction
  downstream_outcome: Enum{SUCCESS, REROUTED, FAILED}   // ground-truth label, logged not consumed

STRUCTURE AttemptRecord             // durable record of a scope-1/2/3 attempt (P6 is total here)
  attempt_number: Integer
  scope: Enum{STEP_RETRY, TASK_REATTEMPT, REPLAN}
  errors: List<ErrorRecord>         // verbatim, tokenized
  lesson_emitted: FailureLesson?    // what was distilled forward, if anything
  loop_detected: Boolean            // §2.13 detector fired

STRUCTURE TokenLedger
  cached_input_tokens: Integer
  uncached_input_tokens: Integer
  completion_tokens: Integer
  estimated_cost: Float
```

#### 3.1.8 Wire Examples

The structures above define the contracts; these are the concrete payloads that cross the wire. Keys are emitted in a fixed order ([[P2]]) — a serializer that sorts keys differently between turns is a cache-busting defect.

**Gateway → Orchestrator** (post-redaction, post-authorization):

```json
{
  "request_id": "01JD8ZC7Q3K9V2F5M8N1P4R7T0",
  "tenant_id": "tnt_4471",
  "agent_id": "support_resolver",
  "session_id": "sess_a91f",
  "input_text": "Refund the order for <PII_EMAIL_1>, card ending <PII_CARD_1>",
  "pii_tokens": [
    { "token": "<PII_EMAIL_1>", "entity_type": "EMAIL",       "vault_ref": "tnt_4471/v1/9c2a" },
    { "token": "<PII_CARD_1>",  "entity_type": "CREDIT_CARD", "vault_ref": "tnt_4471/v1/9c2b" }
  ],
  "tenant_context": {
    "auth_subject": "svc:zendesk-bridge",
    "scopes": ["agent.invoke", "orders.read"],
    "data_partition": "tnt_4471",
    "policy_version": "sha256:9f2c1d",
    "tool_mask": { "mode": "auto", "allow_prefixes": ["db_", "search_", "file_read"], "deny": ["file_delete"] }
  },
  "guardrail": { "stage": "INPUT", "allowed": true, "violations": [] }
}
```

**Orchestrator → MCP Gateway** (one tool call):

```json
{
  "call_id": "01JD8ZCA1M4X8Q2B7H3S6W9Y2E",
  "request_id": "01JD8ZC7Q3K9V2F5M8N1P4R7T0",
  "tenant_id": "tnt_4471",
  "agent_id": "support_resolver",
  "tool_name": "db_read",
  "arguments": { "query_id": "order_by_email", "params": { "email_token": "<PII_EMAIL_1>" } },
  "policy_version": "sha256:9f2c1d",
  "trace_context": { "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7" }
}
```

**Tool Pool → Orchestrator** (large result already offloaded):

```json
{
  "call_id": "01JD8ZCA1M4X8Q2B7H3S6W9Y2E",
  "status": "OK",
  "compact": "1 order found: ORD-88213, total 149.00 EUR, status SHIPPED, placed 2026-02-11",
  "artifact_ref": "s3://eaf-tnt4471-artifacts/sess_a91f/01JD8ZCA.json",
  "metrics": { "latency_ms": 84, "bytes": 41822, "pool": "db-pool", "replica": "db-pool-7f4c9" }
}
```

Only `compact` and `artifact_ref` enter the context; the 41 KB payload stays in the store and is re-fetchable by reference ([[P4]]).

#### 3.1.9 Failure Scoping Contract

The contract that makes [[§2.13]] scope 2 work: what a fresh attempt is *allowed* to know about the attempt before it.

```pascal
STRUCTURE FailureLesson              // distilled; NEVER contains the failed trajectory itself
  attempt_number: Integer            // which re-attempt this lesson is being handed to
  failed_step: String                // the step/todo id that failed, not its transcript
  root_cause_class: Enum{
    ARG_FORMAT,                      // wrong shape/format of an argument
    ARG_VALUE,                       // plausible shape, wrong value
    MISSING_PRECONDITION,            // acted before a required prior step
    WRONG_TOOL,                      // reached for a tool that cannot do the job
    PERMISSION,                      // policy denied it; retrying identically cannot help
    UPSTREAM_ERROR,                  // the target system failed, not the agent
    LOOP_DETECTED,                   // §2.13 loop detector fired
    UNKNOWN
  }
  lesson_text: String                // ONE short paragraph, e.g. "the policy ID format was wrong"
  do_not_repeat: List<String>        // explicit negative constraints for this attempt
  failed_trajectory_ref: Reference   // FULL failed trajectory in the T2 archive (audit/eval/RL)
END STRUCTURE
```

**The two-part guarantee.** `failed_trajectory_ref` always resolves — nothing is lost ([[Property 12]]). And the retrying executor's context contains `lesson_text` + `do_not_repeat` and **nothing else** from the failed attempt — no accumulated wreckage ([[Property 23]]). A `FailureLesson` whose `lesson_text` is a paste of the failed transcript is a defect, and its length is bounded at construction for exactly that reason.

**Wire example** (orchestrator → fresh executor on a scope-2 re-attempt):

```json
{
  "attempt_number": 2,
  "failed_step": "todo-3",
  "root_cause_class": "ARG_FORMAT",
  "lesson_text": "A previous attempt failed because the policy ID was passed as an integer; this API requires the prefixed string form.",
  "do_not_repeat": ["passing policy_id as a bare integer"],
  "failed_trajectory_ref": "s3://eaf-tnt4471-archive/traj/01JD8ZC7/attempt-1.json"
}
```

#### 3.1.10 Skill and Tool Catalog Contracts

`SkillManifest` and `Skill` are defined in [[ADR-002b]]. The two version artifacts that pin a session are here.

```pascal
STRUCTURE SkillIndexVersion          // pinned at session start; contributes to the STABLE PREFIX
  version: String                    // content hash over the ordered index entries
  agent_id: String
  entries: List<SkillIndexEntry>     // §3.1.4; fixed order, deterministic serialization (P2)
  entry_count: Integer               // validated against the per-agent skill-count ceiling
END STRUCTURE

STRUCTURE ToolCatalogVersion         // §3.8; pinned at session start; STABLE PREFIX content
  version: String                    // content hash over the ordered tool definitions
  tools: List<ToolDef>               // fixed order, deterministic key ordering (P2)
  mcp_servers: List<McpServerRef>    // which server provides which tool, for audit
  created_at: Timestamp              // metadata only — NEVER rendered into the prefix
END STRUCTURE

STRUCTURE McpServerRef
  server_id: String
  owner: String                      // team or tenant that authored it
  tool_prefixes: List<String>        // e.g. ["db_"], enforced so a server cannot squat another family
  schema_validated: Boolean          // gateway-verified; false never reaches a catalog version
END STRUCTURE
```

`catalog_version` and `skill_index_version` are recorded in the `SessionManifest` ([[§2.10]]) and in the `TrajectoryRecord` (§3.1.7), so any trajectory can be replayed against the exact tool set and skill index that governed it.

#### 3.1.11 Transcript Tree and Compaction Entries

The transcript is a **tree**, not a list ([[ADR-006]] rule 4), and compaction is an **appended entry**, not an in-place rewrite ([[ADR-006]] rule 3). Both are data-model decisions rather than behavioural ones, which is why they are [[Phase 1]] ([[§8]]) even though the compaction tiers that use them are [[Phase 4]] — retrofitting the shape means touching every reader, replayer, and eval consumer.

```pascal
STRUCTURE TranscriptEntry               // the unit of session history; append-only, forever
  id: String                            // stable, sortable (ULID)
  parent_id: String?                    // null ONLY for the root entry. This makes it a TREE.
  kind: Enum{USER, ASSISTANT, TOOL_CALL, TOOL_RESULT, COMPACTION, SYSTEM}
  payload: Json                         // deterministic key ordering (P2)
  silent: Boolean = FALSE               // ADR-006d: recorded normally, delivery suppressed
  created_at: Timestamp                 // metadata only — NEVER rendered into the prefix
END STRUCTURE

STRUCTURE CompactionEntry               // kind = COMPACTION; appended, never a replacement
  summary: String                       // what the compacted span amounted to
  first_kept_entry_id: String           // THE CUT POINT: read this entry + everything AFTER this id
  tokens_before: Integer                // occupancy at the moment of compaction (an ESTIMATE, §2.10)
  provider: String                      // which summarization provider produced it (ADR-006 rule 8)
  fell_back_to_builtin: Boolean         // true if the pluggable provider failed or returned empty
  memory_flush_entry_id: String?        // the ADR-006c flush that preceded this — Property 28
END STRUCTURE
```

**How a turn reads history after compaction.** Take the **latest** `CompactionEntry` on the current branch; the visible history is that entry's `summary` plus every entry after `first_kept_entry_id`. Everything before the cut point is still in the record, still addressable, and simply not read. There is no mutation step, so:

- **Append-only is unconditional** ([[Property 6]] needs no compaction carve-out).
- **The cut point is a field**, so "what did the agent stop seeing, and when" is a lookup rather than an inference.
- **Compactions stack.** A second compaction appends a second entry with a later cut point; the compaction history is itself history.

**Branching, and what it is for.** `parent_id` is what makes a fork a parent pointer rather than a copy-with-correlation-ids. Two existing mechanisms are branches, not new unrelated records:

| Mechanism | Branch point | Why a branch and not a new record |
| --- | --- | --- |
| **Sub-graph spawn** ([[§2.12]].1) | The parent entry at the moment of `subgraph_invoke` | The child's provenance is structural. Replay and cost attribution follow the edge instead of reconstructing it. |
| **Scope-2 re-attempt** ([[§2.13]]) | The last good entry before the failure | The failed attempt stays on its own branch — durable and addressable ([[Property 12]] clause 1) while absent from the new context ([[Property 23]]). The tree is what lets both hold without special-casing. |

Two constraints travel with forking, both adopted: **a fork is refused while the parent has an active run** (the parent state is indeterminate mid-run, so the child would inherit something that no longer exists by the time it reads it), and **a forked child starts with fresh token counters** rather than inheriting the parent's spent ledger, so a child's budget is genuinely its own and a chain of spawns does not arrive pre-exhausted.
