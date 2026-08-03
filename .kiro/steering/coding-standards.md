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

## LangGraph Discipline

LangGraph is the execution substrate. Use it as designed rather than building a parallel abstraction over it.

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
