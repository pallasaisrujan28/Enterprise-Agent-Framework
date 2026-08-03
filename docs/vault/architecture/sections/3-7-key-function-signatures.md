---
title: "3.7 Key Function Signatures"
type: section
tags: [section]
aliases: ["§3.7"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T20:03:07+00:00
---

# 3.7 Key Function Signatures

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

The seams that matter, as signatures. Types reference [[§3.1]].

```python
# ---- Gateway ----
def admit(raw: HttpRequest) -> tuple[InboundRequest, TenantContext] | Rejection: ...
def authorize(request: AuthzRequest, bundle: TenantPolicyBundle) -> Decision: ...  # §3.2.3


# ---- Guardrails & PII ----
def run_rails(stage: Stage, text: str, policy: GuardrailPolicy) -> GuardrailVerdict: ...
def tokenize_pii(text: str, tenant_id: str) -> tuple[str, list[PiiToken]]: ...
def rehydrate_pii(text: str, tokens: list[PiiToken], recipient: Principal) -> str: ...


# ---- Classification (ADR-013) ----
# ONE seam. Today: declared intent, else one Bedrock call. Swapping in a self-hosted
# classifier later is a change to this body and nothing else.
def classify(request: InboundRequest) -> RoutingDecision: ...
def log_routing_outcome(
    decision: RoutingDecision, outcome: Outcome
) -> None: ...  # the training set


# ---- Planning & execution ----
def plan(task: str, ctx: TenantContext) -> TaskPlan: ...
def replan(
    plan: TaskPlan, summary: FailureSummary
) -> TaskPlan: ...  # scope 3: SUMMARY, not raw trajectory
def run_executor(handoff: SubAgentHandoff) -> SubAgentResult: ...  # may return status=REROUTE


# ---- Retry, recovery, failure scoping (§2.13) ----
def distill_failure(
    attempt: AttemptRecord,
    failed_trajectory_ref: Reference,
) -> FailureLesson: ...  # Properties 12 and 23 both live on this
def detect_failure_loop(
    recent_failures: list[ErrorRecord],
    threshold: int = 3,
) -> LoopVerdict: ...  # Property 22
def reattempt_task(
    handoff: SubAgentHandoff,
    lesson: FailureLesson,
) -> SubAgentResult: ...  # FRESH executor, CLEAN context; carries the lesson and nothing else


# ---- Skills (ADR-002b) ----
def validate_skill(
    skill: Skill, catalog: ToolCatalogVersion, grants: list[ToolGrant]
) -> Validation: ...
def build_skill_index(
    agent_id: str, granted: list[SkillManifest]
) -> SkillIndexVersion: ...  # L1 prefix
def load_skill_body(name: str, version: str) -> str: ...  # L2 progressive disclosure -> tail
def read_skill_reference(ref: Reference) -> str: ...  # L3 reference: COSTS tokens, goes to tail
def run_skill_script(
    ref: Reference,
    args: Json,
    sandbox: SandboxHandle,
) -> (
    ToolResult
): ...  # L3 script: EXECUTED, never read into context. Zero context cost — Property 25
def skill_search(query: str, index: SkillIndexVersion) -> list[str]: ...  # past the index ceiling
def evaluate_skill(skill: Skill) -> Scores: ...  # promotion gate; never optional


# ---- Sub-graphs as tools (§2.12.1) ----
def invoke_subgraph(
    name: str,
    args: Json,
    handoff: SubAgentHandoff,
) -> SubAgentResult: ...  # REJECTS if handoff.depth + 1 > limit — Property 24
def derive_context_mode(
    plan_complexity: Complexity,
    parent_branch_tokens: int,
) -> ContextMode: ...  # ISOLATED above the cap regardless of complexity; no override — Property 30


# ---- Prompt assembly (the cache-critical seam) ----
def assemble(
    session: SessionManifest,
    plan: TaskPlan,
    mask: ToolMask,
    artifact_version: str,
) -> AssembledPrompt: ...
def prefix_hash(prompt: AssembledPrompt) -> str: ...  # Property 4 lives on this
def derive_mask(decision: Decision, state: LoopState) -> ToolMask: ...  # ADR-005


# ---- Tools and catalog evolution (§3.8) ----
def dispatch(call: ToolCall, ctx: TenantContext) -> ToolResult: ...
def resolve_pool(tool_name: str) -> RegistryEntry: ...
def register_mcp_server(ref: McpServerRef) -> Validation: ...  # schema + prefix ownership
def cut_catalog_version(servers: list[McpServerRef]) -> ToolCatalogVersion: ...
def pin_catalog(session_key: str, version: str) -> None: ...  # at session start — Property 26
def tool_search(
    query: str, catalog: ToolCatalogVersion
) -> list[ToolDef]: ...  # past the prefix ceiling


# ---- Session storage tiers (ADR-016) ----
def put_artifact(data: bytes, session: SessionManifest, tier: Tier = Tier.T1) -> Reference: ...
def get_artifact(ref: Reference) -> bytes: ...  # Property 9
def promote(ref: Reference, to_tier: Tier) -> Reference: ...
def manifest_append(session_key: str, entry: ManifestEntry) -> SessionManifest: ...  # Property 15


# ---- Compaction (never touches the prefix; never blocks a turn) ----
def compact(
    session: SessionManifest,
    trigger: CompactionTrigger,
    observed_tokens: int | None = None,  # provider-reported count wins over ours (rule 7)
) -> CompactionEntry: ...  # APPENDS an entry — Properties 7, 8, 27, 28
def trim_lossless(history: list[Message]) -> list[Message]: ...
def summarize_anchored(cold: list[Message], prior: str | None) -> str: ...
def choose_split_boundary(
    entries: list[TranscriptEntry],
    target_share: float,
) -> str: ...  # returns first_kept_entry_id; NEVER splits a call/result pair — Property 27
def precheck_prompt_pressure(
    session: SessionManifest,
    pending: ToolResult,
) -> None: ...  # raises ContextPressureSignal; does NOT compact inline — rule 6
def classify_overflow_error(
    err: ProviderError,
) -> OverflowVerdict: ...  # error FAMILY, not one string


# ---- Pre-compaction memory flush + silent turns (ADR-006c, ADR-006d) ----
def should_flush_memory(session: SessionManifest, cfg: FlushConfig) -> bool: ...
def flush_memory(
    session: SessionManifest,
    model_route: ModelRoute,  # MAY be a cheaper model than the conversation
) -> TranscriptEntry | Skipped: ...  # silent turn; Skipped iff workspace is read-only
def is_silent(output: str) -> bool: ...  # exact sentinel match
def suppress_if_silent(chunk: StreamChunk | Response) -> Delivered | Suppressed: ...  # Property 29


# ---- Transcript tree (§3.1.11) ----
def append_entry(session_key: str, entry: TranscriptEntry) -> TranscriptEntry: ...  # Property 15
def fork(parent_entry_id: str) -> Branch:
    ...  # REFUSES while the parent has an active run;
    # child gets FRESH token counters


def visible_history(branch: Branch) -> list[TranscriptEntry]: ...  # latest CompactionEntry + tail
def touch_freshness(session_key: str, source: EventSource) -> None:
    ...
    # updates updated_at always; last_interaction_at ONLY for USER/CHANNEL — Property 31


# ---- Knowledge (§3.6): Terraform owns resources; this code only syncs into them ----
def validate_ingestion_config(
    raw: dict,
) -> IngestionConfig: ...  # narrow + fail-closed, Property 17
def sync_documents(config: IngestionConfig, since: datetime | None = None) -> SyncReport: ...
def retrieve(query: RetrievalQuery, strategy: RetrievalStrategy) -> RetrievalResult: ...
def score_retrieval(strategy: RetrievalStrategy, labeled_set: str) -> RetrievalAccuracyReport: ...


# ---- Observability & improvement ----
def record(span: Span | LlmCallRecord | AuditEvent) -> None: ...
def finalize_trajectory(request_id: str, outcome: Outcome) -> TrajectoryRecord: ...  # Property 13
def evaluate(dataset: str, artifact_version: str) -> Scores: ...
def promote_artifact(version: str, env: Env, scores: Scores) -> PromotionResult: ...  # Property 16
```

Three signatures carry most of the design's weight: `assemble` (everything about cost), `compact` (everything about long-horizon feasibility), and `authorize` (everything about tenant safety). Two more carry the corrections in this revision: `distill_failure` (the difference between recovering and accumulating wreckage) and `build_skill_index` (the difference between cheap extensibility and prefix bloat).
