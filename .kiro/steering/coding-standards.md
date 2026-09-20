# Coding Standards

Binding rules for all code in this repository. These are not suggestions.

## Non-Negotiable Working Principles

These four rules override convenience, deadline pressure, and the desire to look productive.

### 1. No mocks, no placeholders, no imaginary code

- **Never** write a stub, `pass`, `TODO`, `NotImplementedError`, or a fake return value and present it as working. If a function is not implemented, say so explicitly in the response.
- **Never** invent an API, method, parameter, or config key. If you are not certain a symbol exists, verify it against the installed package or official docs before using it.
- **Never** fabricate example output, benchmark numbers, or metrics. Run it or label it clearly as illustrative.
- Mocks are permitted **only** inside tests, and only for genuine external boundaries (a third-party HTTP API, a paid model call). Never mock our own components to make a test pass — that tests the mock.
- A feature is "done" when it runs and its tests pass, not when the structure exists.

### 2. Research before implementing

- If the correct approach is not known, **research it first**: official documentation, the installed source, then reputable secondary sources.
- Prefer official docs over blog posts. Prefer reading the installed package source over guessing at its behaviour.
- When a decision rests on external information, cite the source in the PR description or a code comment.
- Never guess at library semantics that a two-minute check would settle.

### 3. Evaluate alternatives before committing to a design

For any non-trivial decision — a new dependency, a data model, a control-flow change, a storage choice — identify **at least two viable approaches**, state the tradeoffs, and record why the chosen one wins. A single unexamined option is not a decision, it is a default.

Record it in the PR description for ordinary changes, or as an ADR in the design document when it constrains future work.

### 4. Ask when confused

If a requirement is ambiguous, contradictory, or under-specified, **ask**. Do not pick an interpretation and build on it silently. A clarifying question costs minutes; a wrong assumption discovered after implementation costs days. This applies especially to: intended behaviour at edge cases, which of two conflicting requirements wins, and anything touching tenant data or access control.

## Language and Tooling

- **Python** is the implementation language. Target the version pinned in `pyproject.toml`.
- **uv** for dependency and environment management. `uv sync --frozen` in CI.
- **ruff** for lint and format. **mypy** in strict mode. Both are blocking in CI.
- **pydantic** for all data contracts crossing a component boundary.
- Dependencies are **pinned to exact versions**. No floating ranges, no `^`, no `*`. A floating version silently changes tool schemas and prompt content between deploys.

## Where Ideas Come From vs What Builds Them

Two different repos play two different roles, and confusing them is how this codebase grew a second harness.

> **waku-agent is a source of CONCEPTS. deepagents is the tool that BUILDS them.**
>
> Read waku to understand *what* to build and *why* — its retrieval gate, its triage split, its two-model tiering, its fail-open discipline. Never copy *how* it builds them. waku hand-rolls its harness because it is a teaching repo with no harness dependency; we have deepagents, and the whole point of this project is to learn it.

So the workflow for any waku idea is fixed:

1. **Understand the concept** from waku — the problem it solves, the failure it prevents.
2. **Find the deepagents component** that provides it. Check the pinned version's source, not memory.
3. **Build it with that component.**
4. **Only if deepagents genuinely has nothing** for it, write custom code — and say so in the PR.

### waku concept → deepagents component

The mapping as it stands. Verify against the pinned version before relying on a row; this is a map, not a contract.

| waku concept | Build it with |
| --- | --- |
| The agent loop (`run_loop`) | `create_deep_agent` |
| Skills, progressive disclosure | `middleware.SkillsMiddleware` — via `create_deep_agent(skills=[...])` |
| Consolidation / summarising history | `middleware.SummarizationMiddleware` |
| Long-term / semantic memory | `middleware.MemoryMiddleware` + `backends.StoreBackend` |
| Sub-agent delegation (`delegate_task`) | `middleware.SubAgentMiddleware`, `AsyncSubAgentMiddleware` |
| Tool tiers, restricting what is callable | `create_deep_agent(tools=...)`, `FilesystemPermission` |
| Shell / sandboxed execution | `backends.LocalShellBackend`, `backends.LangSmithSandbox` |
| File and workspace tools | `middleware.FilesystemMiddleware` + `backends.CompositeBackend` |
| Two-model tiering (`model` + `small_model`) | `agent/model.py` — `get_model()` / `get_fast_model()` |
| Provider quirks and per-model conventions | `profiles.ProviderProfile`, `profiles.HarnessProfile` |
| Human-in-the-loop approval | `HumanInTheLoopMiddleware` via `create_deep_agent(interrupt_on=...)` |
| Judge-scored evaluation | `middleware.RubricMiddleware` |
| Per-turn tracing / the observer | LangGraph `.stream(stream_mode=...)`, `backends.langsmith` |
| Web search / page fetch (waku's `search_web`) | no deepagents component — a config-selected backend: `search_backend.py` (ddgs / SearXNG), `fetch_backend.py` (trafilatura / Firecrawl) |
| Durable threads | `create_deep_agent(checkpointer=...)` |

### waku concepts with no deepagents component — custom is correct here

Write these ourselves, and the PR should reference this list rather than re-arguing it:

- **The obligation gate.** `SkillsMiddleware` discloses skills to the model; nothing in deepagents enforces obligations *outside* it. Our whole premise is that the model cannot talk its way past them. Implemented as an `AgentMiddleware` so it plugs into the harness rather than wrapping it.
- **The retrieval gate** (a cheap model deciding *whether* to retrieve). `MemoryMiddleware` retrieves; it does not decide against retrieving. A `before_model` or `wrap_model_call` hook is the place for it.
- **The usage ledger.** Token counts come from `usage_metadata`; nothing upstream keeps an append-only spend record.
- **Channels and the dashboard.** The HTTP surface and the UI are ours by definition.

**Fail open or closed deliberately, and say which.** waku's gates fail *open* — a broken gate costs latency, never capability — because they protect tokens. Ours protect *delivery*, so an obligation check that cannot run must not silently pass. Copy the discipline of naming the direction; do not copy the direction itself.

## Use The Harness — deepagents First, Custom Last

**deepagents is the harness. Before writing any function or component, check whether deepagents already provides it, and use that instead.** This is the first question on every change, not a later refactor. Custom code is written only when the capability genuinely does not exist upstream.

Search order, and stop at the first hit:

1. **deepagents** — `create_deep_agent`, its middleware, its backends, its profiles
2. **langchain / langgraph** — the substrate underneath it (see LangGraph Discipline below)
3. **the standard library**
4. **custom code** — only after 1–3 are ruled out, and the ADR or PR says which one was missing and why

### What deepagents already provides

Checked against the pinned version rather than remembered. Re-check with `python -c "import deepagents; print(dir(deepagents))"` when the pin moves — this list is a map, not a contract.

| Need | Use this, do not rebuild it |
| --- | --- |
| The agent loop | `create_deep_agent` |
| Skills in the prompt, progressive disclosure | `middleware.SkillsMiddleware` |
| Context compaction / summarisation | `middleware.SummarizationMiddleware` |
| Long-term memory | `middleware.MemoryMiddleware` |
| Sub-agents and delegation | `middleware.SubAgentMiddleware`, `AsyncSubAgentMiddleware` |
| File tools | `middleware.FilesystemMiddleware`, `FilesystemPermission` |
| Scored evaluation | `middleware.RubricMiddleware` |
| Prompt caching | `middleware._prompt_caching` (applied by the harness) |
| Dangling tool calls | `middleware.patch_tool_calls` |
| State / store / filesystem / S3 backing | `backends.StateBackend`, `StoreBackend`, `FilesystemBackend`, `CompositeBackend` |
| Shell and sandboxed execution | `backends.LocalShellBackend`, `backends.LangSmithSandbox` |
| Per-model prompt and tool conventions | `profiles.HarnessProfile`, `register_harness_profile` |
| Per-provider quirks | `profiles.ProviderProfile`, `register_provider_profile` |

Models reach the agent through **`langchain_aws.ChatBedrockConverse`**, constructed in `agent/model.py`. Do not write a provider client, a streaming wrapper, or a message-shape adapter.

### The test for writing custom code

Answer in the PR description, in one sentence: **which upstream component did you look for, and what specifically does it not do?**

"It was easier to write my own" is not an answer. Neither is "the upstream one is more complicated than I need" — configuration is cheaper than a second implementation, and a second implementation is a thing to maintain, test and keep in step forever.

A legitimate answer looks like the **obligation gate** (`agent/gate.py`, `agent/skills_engine/obligations.py`): `SkillsMiddleware` loads skills and discloses them to the model, but nothing in deepagents enforces obligations *outside* the model, and the whole premise of this platform is that the model cannot talk its way past them. There is no upstream component for that, so it is ours. That is the bar.

### What this rule cost when it was not followed

A second harness was written before this rule existed and has since been deleted. It is recorded here because the shape of the mistake is worth recognising, not because the code still exists:

| Deleted | Duplicated |
| --- | --- |
| `agent/models/` — a `ChatModel` protocol, a Bedrock adapter, an echo adapter | `ChatBedrockConverse` and `profiles.ProviderProfile` |
| `agent/turn.py` — a turn loop, skill router, prompt assembly, history window | `create_deep_agent`, `SkillsMiddleware`, `SummarizationMiddleware`, the checkpointer |
| `agent/config.py` — a config and secrets seam | `agent/model.py` plus the boto3 credential chain |
| `agent/middleware/content.py` — tool-result offload | `SummarizationMiddleware` |

Every one of them worked. That is what made them expensive: two implementations of the same concern, both maintained, drifting apart, with two doors into the system carrying different protections. The obligation gate was wired into one and not the other.

**The one part that survived is the part with no upstream equivalent** — the gate itself, now `agent/middleware/obligations.py`, an `AgentMiddleware` that plugs into the harness rather than replacing it.

## LangGraph Discipline

LangGraph is the execution substrate **beneath deepagents**. Reach for it when deepagents has no component for the need — not before. Then use it as designed rather than building a parallel abstraction over it.

- **Use real LangGraph primitives**: `StateGraph`, typed state schemas, nodes, conditional edges, `Send` for fan-out, `Command` for control flow, checkpointers for durability, and interrupts for human-in-the-loop. Do not hand-roll equivalents.
- **Do not invent LangGraph APIs.** If unsure whether a primitive exists or how it behaves, check the installed version's source or docs. LangGraph's API has moved across versions; verify against the pinned version, not memory.
- **One graph per sub-agent.** Graphs stay small. A graph that is becoming the whole platform is a design violation — see the extension ladder in the design document (skill, then tool, then sub-graph).
- **State schemas are explicit and typed.** No untyped dict state. State is the contract between nodes.
- **Use the checkpointer for durability**, not custom persistence. Session state belongs in the configured store, never in process memory.
- **Interrupts are the HITL mechanism.** Do not build a bespoke approval queue when `interrupt` covers it.
- New capability is added as a **skill** or a **tool**, not as a new node, unless a forcing function from the design document genuinely applies.

## Data Contracts

- Every message crossing a component boundary is a pydantic model defined in the design document. Do not pass bare dicts between layers.
- **Deterministic serialization is mandatory.** JSON key ordering must be stable and explicit. Non-deterministic key ordering silently destroys KV-cache hit rate, which is the platform's primary cost metric. This is a correctness requirement, not a style preference.
- Never mutate anything that contributes to a prompt's stable prefix. Prefix mutation is a defect even when the output looks fine.

## Error Handling

- No bare `except:` and no `except Exception:` without re-raising or logging with full context.
- Errors carry structured context: what was attempted, with what inputs (PII-safe), and what the caller should do.
- Never swallow an exception to make a flow look successful.
- Distinguish transient from permanent failures explicitly; they get different retry treatment per the design document's error taxonomy.
- Fail closed on anything involving authorization, tenancy, or PII. Availability never trades against isolation.

## Security

- **Never** hardcode a credential, token, key, or connection string. Use secret references resolved at runtime.
- **Never** log a secret, a raw PII value, or a full prompt containing tenant data.
- `tenant_id` is read **only** from a verified token claim, never from a request body or query parameter.
- Every storage access is scoped to the tenant partition. A missing partition filter is a cross-tenant data leak, not a bug.
- Validate and constrain any model-authored input before it reaches a shell, a query, or a filesystem path.

## Testing

- **pytest** for unit and integration. **hypothesis** for the correctness properties in the design document. **deepeval** for agent behavioural assertions.
- A test that asserts nothing is not a test. A test that only asserts "no exception raised" is rarely a test.
- Deterministic gates (prefix stability, policy evaluation, PII egress, tenant isolation) must never depend on an LLM call. They cannot be allowed to flake.
- Agent evaluation asserts on the **trajectory** — tool sequence, retrieved documents, side effects, cost envelope — not just the final string.
- **Eval sets must include injected failures.** A suite of only happy paths overstates real behaviour, because recovery is a large share of production agent work.
- Clean up temporary files and test artifacts.

## Documentation

- Update the design document in the **same pull request** as the change that invalidates it. Documentation drift is treated as a defect, not a chore.
- Docstrings explain *why* and state pre/post-conditions. Skip docstrings that restate the signature.
- Comment the non-obvious: an invariant being maintained, a subtle ordering requirement, a workaround and its cause.
- When a decision is reversed, update the ADR and record why rather than deleting the history.

## Code Organization

- Small, single-purpose modules. If a file needs an index to navigate, split it.
- Dependencies point inward: gateway and orchestrator may depend on contracts; contracts depend on nothing.
- No circular imports.
- Prefer explicit composition over inheritance and over metaprogramming. Cleverness has a maintenance cost that outlives its author.
