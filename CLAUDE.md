# Claude Code — Agent Project Instructions

This file is read by Claude Code at the start of every session.
See `docs/ARCHITECTURE.md` for the full system design.

---

## Development workflow

### Run `make check` before every commit

Before committing any Python change, run:

```bash
make check     # ruff lint + ruff format check (~3 seconds)
```

If it fails, fix first:
```bash
make format    # auto-fix lint + format in place
```

Then verify it is clean:
```bash
make check     # must pass before git commit
```

Install the pre-push hook so this runs automatically:
```bash
make install-hooks
```

**Principle:** CI should never see a failure a local check would have caught.
A red PR blocks the branch, wastes pipeline time, and creates fix commits
that clutter the history. Run the check locally — it takes 3 seconds.

### One feature per branch — keep PRs small and reviewable

Each branch must contain exactly **one logical change**.
Aim for 1–3 files changed per PR.

**Good:**
- `feat(backends): add EAFBackend S3 implementation` — one new file
- `fix(mypy): ignore_missing_imports for third-party stubs` — one config change
- `feat(tools): web_search via SearXNG` — one tool file

**Not good:**
- Backend + brain + delegation + tools all in one PR
- New feature AND unrelated refactor in the same commit

A PR that touches more than 4 files is almost always more than one feature.
Split it. The goal: **a reviewer should understand the full change in 5 minutes.**

### Commit message format

```
<type>(<scope>): <short description>

<body if needed — why, not what>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`
Scope: the module changed (`brain`, `backends`, `tools`, `memory`, etc.)

---

## Architecture decisions (do not reverse without discussion)

### deepagents is the harness — LangGraph is underneath

We use `create_deep_agent` from deepagents (not `create_react_agent` from LangGraph directly).
deepagents provides skills, filesystem, task planning, sub-agents, HITL out of the box.
LangGraph StateGraph is the execution engine underneath — graph engineering, not loop engineering.

### Backend = storage. Sandbox = backend + execute(). Never confuse them.

`BackendProtocol` is the filesystem/storage interface.
`SandboxBackendProtocol` extends it with `execute()` (shell commands).
EAF uses `EAFBackend` (S3, no execute) — no shell sandbox in production.
The security boundary is IAM + K8s NetworkPolicy + tool whitelist.

### CompositeBackend routes by path prefix

```
/workspace  → EAFBackend (S3, persistent)
/skills     → FilesystemBackend (pod disk, read-only, baked in image)
default     → StateBackend (RAM, ephemeral scratch)
```

The agent uses paths. The routing is silent. Never change path conventions
without updating the CompositeBackend routes and the system prompt.

### Tools are discovered semantically — never hardcoded

`ToolRegistry` embeds tool descriptions with Bedrock Titan at startup.
Per turn: top-k most similar tools are selected via cosine similarity.
Never pass all tools to the model on every turn.
Adding a tool = add it to `brain.py`'s tools list (or Gateway later).

### Data residency is a hard requirement

All inference and data stays in eu-west-2 (London).
`ChatBedrockConverse` with `region_name="eu-west-2"` — no exceptions.
Qdrant, Langfuse, AgentCore Memory are all in eu-west-2.
No external sandbox services (Daytona, Modal) unless verified in eu-west-2.

### No stored credentials anywhere

Auth is IRSA — pod service account annotation → IAM role → temporary credentials.
No API keys, no access keys, no secrets in environment variables or code.
Cognito client credentials (for AgentCore Gateway) live in Secrets Manager only.

### Obligation gate runs outside the model — always

`gate.py` checks draft responses against skill obligations.
It runs after the model responds, not as a prompt instruction to the model.
It fails closed: an error inside the gate blocks delivery.
Never disable, bypass, or remove the gate to fix an error.

### Pipeline rule applies here too

No Python code is deployed from a terminal.
Every change goes through Git → PR → CI → merge.
The CI pipeline (`build-checks.sh`) runs: pip-audit → lint → format → mypy → tests.

---

## What lives where

| Code | Location |
|------|----------|
| Agent harness wiring | `agent/brain.py` |
| S3 workspace backend | `agent/backends/s3.py` |
| Sub-agent builders | `agent/delegation/` |
| Web search tool | `agent/tools/web_search.py` |
| Fetch + store tool | `agent/tools/fetch_and_store.py` |
| Session memory tool | `agent/tools/search_memory.py` |
| Semantic tool registry | `agent/registry.py` |
| Obligation gate | `agent/gate.py` |
| Bedrock guardrails | `agent/guardrails/bedrock.py` |
| Platform policies | `agent/policies/loader.py` |
| Cognito token manager | `agent/auth/cognito.py` |
| Session memory (Qdrant) | `agent/memory/working.py` |
| Cross-session memory | `agent/memory/checkpointer.py` |
| Context compaction | `agent/context/compaction.py` |
| Token budget | `agent/context/budget.py` |

| Config/Data | Location |
|-------------|----------|
| Agent config | `agents/core.yaml` |
| Skill definitions | `skills/*.md` |
| Platform policies | `policies/default.yaml` |
| Guardrail spec | `guardrails/content_safety.yaml` |
| K8s manifests | `k8s/` |
| Full architecture | `docs/ARCHITECTURE.md` |
