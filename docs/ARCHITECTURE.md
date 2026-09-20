# EAF Agentic System — Architecture Reference

This document is the single source of truth for every design decision about the EAF agent.
Update it when decisions change. Never let it drift from the code.

---

## 1. Framework Choice

**Framework: `deepagents`** (langchain-ai/deepagents, `pip install deepagents>=0.7`)

```
LangGraph          ← graph execution engine (lowest level, fully custom graphs)
  └── deepagents   ← opinionated harness (batteries included)
        └── EAF    ← our additions (memory, tools, guardrails, backend)
```

We chose deepagents because:
- Skills, filesystem, task planning, sub-agents, HITL come for free
- LangGraph StateGraph underneath — graph engineering, not loop engineering
- Karpathy's point: graph > loop. deepagents compiles to a StateGraph.
- `create_deep_agent` gives us the harness; we only write what is EAF-specific.

### What deepagents provides (no custom code needed)
| Feature | What it does |
|---------|-------------|
| Skills | Loads `skills/*.md` at startup, JIT full load when triggered |
| `TodoListMiddleware` | Task tracking: pending → in_progress → completed |
| `task` tool | Delegation — spawns isolated sub-agent, returns one result |
| `interrupt()` | HITL — pauses graph for human approval |
| `CompositeBackend` | Routes filesystem calls to different backends by path prefix |
| `FilesystemBackend` | Reads pod local disk (baked-in image files) |
| `StateBackend` | Ephemeral in-memory storage per session |

### What we build (EAF-specific)
| Module | What it does |
|--------|-------------|
| `agent/filesystem/eaf_backend.py` | Full S3 BackendProtocol (workspace files) |
| `agent/memory/working.py` | Qdrant session working memory |
| `agent/memory/checkpointer.py` | AgentCore cross-session checkpointer |
| `agent/tools/web_search.py` | SearXNG aggregated web search |
| `agent/tools/fetch_and_store.py` | Crawl4AI → embed → Qdrant |
| `agent/tools/search_memory.py` | Qdrant semantic query |
| `agent/registry.py` | Bedrock Titan semantic tool discovery |
| `agent/gate.py` | Obligation gate (runs outside the model, fails closed) |
| `agent/guardrails/bedrock.py` | Bedrock Guardrails API (input + output) |
| `agent/policies/loader.py` | Regex platform rules from `policies/*.yaml` |
| `agent/auth/cognito.py` | Cognito client_credentials token manager |

---

## 2. Full Request Flow

```
User
  │
  ▼
FastAPI  POST /chat
  │
  ├── Bedrock Guardrails ── INPUT check (harmful content, PII, jailbreak)
  ├── Policy Engine ──────── regex rules from policies/*.yaml (always-on)
  │
  ▼
deepagents harness  (create_deep_agent)
  │
  ├── Skills from skills/*.md
  │     Frontmatter only loaded at startup (keeps context compact).
  │     Full content loaded JIT when a skill triggers on a turn.
  │     Obligations checked by gate.py after the model responds.
  │
  ├── TodoListMiddleware
  │     Agent can create structured tasks and track progress.
  │
  ├── CompositeBackend (filesystem routing)
  │     /workspace  → EAFBackend  (S3, persistent workspace)
  │     /skills     → FilesystemBackend (pod disk, read-only)
  │     default     → StateBackend (RAM, ephemeral scratch)
  │     Agent calls read_file/write_file with a path.
  │     CompositeBackend routes to the right storage silently.
  │
  ├── Tools (selected semantically per turn)
  │     web_search      → SearXNG :8080       (K8s internal DNS)
  │     fetch_and_store → Crawl4AI :11235 + Qdrant :6333
  │     search_memory   → Qdrant :6333
  │
  │     ToolRegistry at startup:
  │       embed each tool description with Bedrock Titan
  │     Per turn:
  │       embed user task → cosine similarity → top-k tools only
  │       only top-k schemas reach the model (no context bloat)
  │
  ├── Delegation (task tool — deepagents built-in)
  │     Parent spawns sub-agent with:
  │       - Fresh isolated context (no parent history)
  │       - Its own backend instance (isolated workspace)
  │       - Scoped tool subset (only what the sub-task needs)
  │     Sub-agent runs to completion → ONE structured result back
  │     Parent context stays clean — no reasoning bleed-through
  │
  ▼
LangGraph StateGraph  (deepagents compiles to this)
  │
  ▼
Obligation Gate  (gate.py — outside the model)
  Checks draft against obligations of every triggered skill.
  Fails CLOSED: an error inside the gate BLOCKS delivery.
  Can never be persuaded by the model to skip a check.
  │
  ▼
Bedrock Guardrails ── OUTPUT check
  │
  ▼
Response to user
```

---

## 3. Backend System

### What a backend is

A backend is the **storage layer** behind all filesystem tools (`read_file`, `write_file`,
`ls`, `grep`, `glob`, `edit`). Scoped entirely to filesystem/storage — no model or memory
backends.

### BackendProtocol — the contract every backend must follow

```python
class BackendProtocol(abc.ABC):
    # READ
    def ls(self, path: str) -> LsResult
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult
    def grep(self, pattern: str, path: str | None, glob: str | None) -> GrepResult
    def glob(self, pattern: str, path: str | None) -> GlobResult
    # WRITE
    def write(self, file_path: str, content: str) -> WriteResult
    def edit(self, file_path: str, old_string: str, new_string: str) -> EditResult
    def delete(self, file_path: str) -> DeleteResult
    # TRANSFER
    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]
    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]
    # All methods have async variants: aread, awrite, als, aglob, etc.
    # None are @abstractmethod — implement only what you need.
```

`SandboxBackendProtocol(BackendProtocol)` adds command execution:
```python
    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse
    async def aexecute(...)
    @property id(self) -> str   # unique sandbox ID
```

A sandbox IS a backend. `BaseSandbox` implements all BackendProtocol methods by
building shell commands and delegating to `execute()`.

### How CompositeBackend routes calls

```python
# deepagents ships this class. We configure it, we don't build it.
composite = CompositeBackend(
    default=StateBackend(),            # fallback if no route matches
    routes={
        "/workspace": EAFBackend(...), # our S3 backend
        "/skills":    FilesystemBackend(root="/app"),
    }
)
agent = create_deep_agent(backend=composite, ...)
```

Runtime call `read_file("/workspace/report.md")`:
```
read_file("/workspace/report.md")
    ↓ composite.read("/workspace/report.md")
    ↓ _route checks: path starts with "/workspace"? YES
    ↓ EAFBackend.read("/workspace/report.md")
    ↓ S3 get_object(Bucket="eaf-dev-workspace-...", Key="report.md")
    ↓ content returned to agent
```

Runtime call `read_file("/skills/legislation_advice.md")`:
```
read_file("/skills/legislation_advice.md")
    ↓ composite.read(...)
    ↓ _route checks: "/skills"? YES
    ↓ FilesystemBackend.read("/skills/legislation_advice.md")
    ↓ opens /app/skills/legislation_advice.md from pod disk
    ↓ content returned to agent
```

### StateBackend vs graph state

- **Graph state** = the entire working memory dict during execution
  (messages, tool results, everything the graph carries between nodes)
- **StateBackend** = stores file-like content INSIDE that graph state dict
  — a `/scratch/` area that lives and dies with the graph execution

They use the same underlying storage. Different purposes.

### How the agent decides which path to use

The agent (LLM) reads the tool description and system prompt, which say:
- `/workspace/` = persistent files (survive pod restart)
- `/scratch/` = temporary notes during current task
- `/skills/` = read-only (do not write here)

The LLM generates the path as text. CompositeBackend routes silently underneath.

### EAFBackend (to build — `agent/filesystem/eaf_backend.py`)

Full `BackendProtocol` backed by S3. Methods:

| Method | S3 operation |
|--------|-------------|
| `read(path, offset, limit)` | `get_object` + slice by line |
| `write(path, content)` | `put_object` |
| `ls(path)` | `list_objects_v2` with delimiter |
| `grep(pattern, path, glob)` | list objects → fetch → `re.search` per line |
| `glob(pattern, path)` | list objects → `fnmatch` filter |
| `edit(path, old, new)` | read → replace → write |
| `delete(path)` | `delete_object` |
| `upload_files(files)` | `put_object` for each binary |
| `download_files(paths)` | `get_object` for each path |
| all async variants | `asyncio.to_thread` wrapping sync methods |

---

## 4. Sandbox

A sandbox = a backend that can also `execute()` shell commands in an isolated
environment. deepagents ships several:

| Sandbox | Isolation |
|---------|-----------|
| `LocalShellBackend` | subprocess on the pod (DEV ONLY — not safe in prod) |
| `LangSmithSandbox` | LangSmith managed cloud sandbox |
| `DaytonaSandbox` | Remote Daytona workspace (partner package) |
| `ModalSandbox` | Modal.com serverless sandbox |
| `RunloopSandbox` | Runloop environment |
| `VercelSandbox` | Vercel sandbox |
| `QuickJSSandbox` | JavaScript QuickJS sandbox |

### EAF sandbox decision

We do NOT use a shell sandbox. The security boundary in EAF is:
1. **IAM** — IRSA role only permits specific AWS API calls
2. **K8s NetworkPolicy** — pod only reaches registered internal services
3. **Tool whitelist** — agent only gets top-k semantically selected tools
4. **Obligation gate** — checks output before delivery, fails closed
5. **No `execute()`** — agent cannot run arbitrary shell commands

If code execution is needed in future: use `DaytonaSandbox` or `ModalSandbox`
(isolated remote environments). Not `LocalShellBackend`.

---

## 5. Delegation

deepagents ships the `task` tool. How it works:

```
Parent agent: "Research RAG papers, write summary to /workspace/rag_summary.md"
    ↓
task tool called:
  prompt: "Research RAG papers 2024-2025 and return a 500-word summary"
  tools: [web_search, fetch_and_store, search_memory]  ← scoped subset
  backend: fresh EAFBackend instance  ← isolated, not shared with parent
  context: EMPTY  ← sub-agent starts with no parent history

Sub-agent runs (isolated):
  web_search("RAG papers 2025") → finds 10 results
  fetch_and_store(url1, session_id) → stores chunks in Qdrant
  fetch_and_store(url2, session_id) → stores more chunks
  search_memory("RAG retrieval techniques", session_id) → finds relevant chunks
  reasons across 20+ tool calls and intermediate notes in /scratch/
  returns: "Summary: RAG has evolved in three key directions..."

Parent receives ONE string:
  "Summary: RAG has evolved in three key directions..."
Parent writes it to /workspace/rag_summary.md
Parent context: user request + one result. Clean.
```

Key property: parent context stays clean. Sub-agent's 20 tool calls never
enter the parent's context window. This is the "deep" in deep agents.

---

## 6. Memory

### Working memory (per session)

| Property | Value |
|----------|-------|
| Storage | Qdrant (EKS `tools` namespace) |
| Key | `session_id` (= `thread_id`) |
| Content | Semantic chunks of web pages fetched this session |
| TTL | Ephemeral — cleared when session ends |
| Written by | `fetch_and_store` tool (Crawl4AI → Bedrock Titan → Qdrant upsert) |
| Read by | `search_memory` tool (Bedrock Titan embed → cosine search) |
| Purpose | Re-use content from earlier in session without re-fetching URLs |

### Persistent memory (cross-session)

| Property | Value |
|----------|-------|
| Storage | AgentCore Memory (AWS managed, eu-west-2) |
| Key | `thread_id` + `actor_id` |
| Content | Full LangGraph checkpoint (messages, tool results, state) |
| TTL | Permanent |
| Written by | LangGraph checkpointer (automatic, after each step) |
| Read by | LangGraph checkpointer (automatic, on session resume) |
| Purpose | Agent remembers previous conversations with the same user |

---

## 7. Tool Architecture

### Current (direct HTTP to K8s)

```
web_search      → HTTP GET  → SearXNG :8080
                   aggregates: Google, Bing, DuckDuckGo, Wikipedia, arXiv
                   all free, no API keys

fetch_and_store → HTTP POST → Crawl4AI :11235
                   renders JS, extracts clean markdown, semantic chunking
                → Bedrock Titan embed → Qdrant :6333 (store chunks)

search_memory   → Bedrock Titan embed → Qdrant :6333 (cosine search)
```

All traffic is K8s cluster-internal DNS — never leaves the VPC.

### Target (AgentCore Gateway with semantic discovery)

```
Startup:
  1. GET {gateway}/mcp  method: tools/list  (Cognito JWT)
     returns: [{ name, description, inputSchema }, ...]
  2. Bedrock Titan embeds each description → stored in pod RAM

Per turn:
  3. Embed user task with Bedrock Titan
  4. Cosine similarity → top-k tools (e.g. top 4 of 20)
  5. Only top-k schemas passed to create_deep_agent for this turn

Tool call:
  6. POST {gateway}/mcp  method: tools/call
     { name: "web_search", arguments: { query: "..." } }
     Authorization: Bearer {cognito_jwt}
  7. Gateway validates JWT scope: "https://tools.eaf.dev/invoke"
  8. Gateway routes to registered Lambda target
  9. Lambda (in VPC) calls K8s service via internal DNS
  10. Result back to agent
```

Adding a new tool in target state = register it in Gateway (Terraform).
No code change in the agent.

---

## 8. AgentCore Gateway Setup

### Provisioned (workloads/dev/agentcore-gateway.tf)

| Resource | Name | Status |
|----------|------|--------|
| Cognito User Pool | `eaf-dev-gateway` | ✅ Applied |
| Cognito User Pool Domain | `eaf-dev-gateway-{account_id}` | ✅ Applied |
| Cognito Resource Server | `https://tools.eaf.dev` | ✅ Applied |
| Cognito App Client | `eaf-agent` (client_credentials, 1h) | ✅ Applied |
| Secrets Manager | `eaf-dev/gateway/agent-client-creds` | ✅ Applied |
| IAM execution role | `eaf-dev-gateway-execution-role` | ✅ Applied |
| Security group | `eaf-dev-gateway-egress` (VPC only) | ✅ Applied |
| Gateway resource | `aws_bedrockagentcore_gateway` | ⏳ Pending provider |

`aws_bedrockagentcore_gateway` is not yet in hashicorp/aws ~5.x.
Block is commented out in `agentcore-gateway.tf`. All prerequisites deployed.
Uncomment and re-apply when provider support lands.

### Auth flow

```
1. Pod reads Secrets Manager → { client_id, client_secret, token_endpoint }
2. POST token_endpoint with client_credentials → JWT (1h, cached in pod RAM)
3. All MCP calls include: Authorization: Bearer {jwt}
4. Gateway validates JWT against Cognito User Pool
```

---

## 9. Where All Data Lives

| Data | Storage | Location | Scope | Written by |
|------|---------|----------|-------|------------|
| Conversation state | AgentCore Memory | AWS managed, eu-west-2 | Per thread | Checkpointer (auto) |
| Session web chunks | Qdrant | EKS `tools` ns | Per session | fetch_and_store |
| Workspace files | S3 | `eaf-dev-workspace-*` | Per agent, persistent | EAFBackend |
| Skills | Pod disk | `/app/skills/` (in image) | Global, read-only | Git → CI → image |
| Policies | Pod disk | `/app/policies/` | Global, read-only | Git → CI → image |
| Guardrail config | Pod disk | `/app/guardrails/` | Global, read-only | Git → CI → image |
| Tool schemas | AgentCore Gateway | AWS managed | Global | Terraform |
| Tool embeddings | Pod RAM | In-memory | Ephemeral | ToolRegistry at boot |
| Cognito tokens | Pod RAM | Cached | Per pod, 1h | auth/cognito.py |
| Client credentials | Secrets Manager | `eaf-dev/gateway/agent-client-creds` | Per env | Terraform |
| LLM traces | Langfuse | EKS `langfuse` ns | All sessions | LangChain callback |
| Scratch files | Graph state (RAM) | In-memory | Per session | StateBackend |

---

## 10. Build Order

1. **`EAFBackend`** — full S3 BackendProtocol (`agent/filesystem/eaf_backend.py`)
2. **`CompositeBackend` wiring** — update `brain.py` to use composite + EAFBackend
3. **`uv lock` regeneration** — run locally, commit `uv.lock` (unblocks all agent PRs)
4. **Lambda tool proxies** — one Lambda per tool, in VPC, calls K8s internal DNS
5. **Register tools in Gateway** — Terraform MCP targets once provider supports it
6. **`ToolRegistry → Gateway`** — swap local tools list for MCP discovery
7. **Delegation config** — sub-agent scoped tools + isolated EAFBackend instance

---

## 11. Key Constraints (non-negotiable)

| Constraint | Rule |
|------------|------|
| Data residency | All data stays in eu-west-2. No exceptions. |
| No manual resources | Everything through Git → PR → pipeline → Terraform |
| No paid APIs | All tools must be free / open source |
| Pipeline rule | Never create/destroy/apply through CLI scripts |
| No shell sandbox in prod | Use tool whitelist + IAM + gate instead |
| Obligation gate | Always runs outside model. Always fails closed. |
| Tool discovery | Semantic (Bedrock Titan). Never a hardcoded list. |
| Dependencies | uv.lock pins exact versions. Never edit manually. |
