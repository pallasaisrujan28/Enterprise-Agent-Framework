# Git Workflow and CI/CD

Binding rules for branching, committing, and shipping.

## Never Work On Main

`main` is protected. It is never committed to directly, and it is never pushed to directly.

Every change starts on a **feature branch named after the feature**:

```
feature/<feature-name>      # new capability
fix/<short-description>     # bug fix
chore/<short-description>   # tooling, deps, config
docs/<short-description>    # documentation only
refactor/<short-description>
```

Use kebab-case matching the spec feature name where one exists, so a branch traces back to its spec:

```
feature/mcp-gateway-tool-catalog
feature/skill-registry
fix/prefix-hash-cardinality
```

## The Loop

1. **Branch** from an up-to-date `main` using the naming convention above.
2. **Implement** the feature, with tests.
3. **Update documentation in the same branch.** A feature that changes behaviour described in the design document updates that document before the PR opens. This is not optional and not a follow-up ticket.
4. **Commit** in logical units with conventional-commit messages.
5. **Push** the branch with upstream tracking: `git push -u origin feature/<name>`.
6. **Open a pull request** into `main`.
7. **CI must pass.** All blocking gates green.
8. **Approval required.** `main` merges only on explicit review approval. No self-merge without approval, no bypassing the gate.

## Commit Messages

Conventional commits:

```
feat(skills): add skill index to stable prefix
fix(prompt): restore deterministic tool ordering
test(retry): cover failure-loop detection at threshold
docs(design): record Kubernetes deployment decision
chore(deps): pin langgraph to exact version
```

Rules:
- Subject under 72 characters, imperative mood.
- Body explains **why**, not what the diff already shows.
- One logical change per commit. Do not bundle a refactor with a behaviour change — it makes review and bisection harder.
- Never commit secrets, `.env` files, or credential stores. Stage specific files rather than `git add .` so nothing unrelated slips in.

## Destructive Operations

Force push, `reset --hard`, `clean -f`, and branch deletion require explicit human confirmation. Never rewrite published history on a shared branch. Prefer new commits over `--amend` on anything already pushed.

## CI/CD — Grows With the Codebase

**We are local-first. There is no cloud deployment yet.** The pipeline starts deliberately small and gains gates only as the things those gates protect come into existence. A gate for a component that does not exist is noise that trains people to ignore CI.

### Stage 0 — current state: the only three gates

Runs on every pull request. Nothing else is wired up yet.

1. **Lint and format** — `ruff check` and `ruff format --check`
2. **Vulnerability scan** — dependency audit (`pip-audit` or `uv`-native), container image scan (`trivy`), and secret scanning (`gitleaks` or `detect-secrets`)
3. Nothing more.

No deployment step. No cloud credentials in CI. There is nowhere to deploy to yet, and adding a deploy job that targets nothing is how a pipeline rots.

### Gate growth path — each gate arrives with the thing it protects

Add a gate when the component it guards exists, not before:

| Gate | Added when |
| --- | --- |
| Type checking (`mypy --strict`) | The first typed module lands |
| Unit and contract tests | The first data contract exists |
| Integration tests against a real local LangGraph server | The first agent loop runs end to end |
| Skill validation and skill eval cases | The skill registry exists |
| Policy tests (OPA fixtures) | The policy engine is wired in |
| Ingestion config validation | The knowledge layer exists |
| Behavioural eval subset (`deepeval`) | There is behaviour worth asserting on |
| Retrieval accuracy gate | A retrieval strategy exists to regress |
| Cost and cache budget gate | Prompt assembly and token accounting exist |
| `terraform validate` | Infrastructure code exists — which is post-cloud-decision |

### Cloud pipelines — not yet, and gated by an explicit decision

Dev and prod deployment pipelines, staging, canary, and automatic rollback are **future state**. They are designed in the spec but not built. They arrive only after a **cloud readiness checkpoint** concludes that the move is justified — reviewed after every three features (see the spec's phased delivery plan).

Do not build them speculatively. Building a canary pipeline before there is a cluster to canary into is wasted work that then has to be maintained through every subsequent design change.

When that checkpoint does say yes, the pipeline gains: build and sign images, push to a registry, deploy to dev on merge, and a separate prod pipeline that is **approval-only** — staging, full eval suite, red team, **manual approval gate**, canary at limited traffic, automatic rollback on degradation. Rollback is a pointer change, never a rebuild.

## Pull Requests

- Title under 70 characters. Detail goes in the description.
- Description covers: what changed, why, how it was tested, alternatives considered and why they lost, and any documentation updated.
- Link the spec or ADR the change implements.
- Note explicitly if a change touches authorization, tenancy, PII, or the prompt stable prefix. Those get closer review because their failure modes are silent.
