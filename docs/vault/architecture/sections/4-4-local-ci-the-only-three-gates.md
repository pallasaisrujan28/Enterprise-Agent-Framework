---
title: "4.4 Local CI — the only three gates"
type: section
tags: [section, local-first]
aliases: ["§4.4"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# 4.4 Local CI — the only three gates

Part of [[4-service-selection-and-local-first-development|4. Service Selection and Local-First Development]].

**Lint/format, vulnerability scanning, nothing else.** Concretely:

| Gate | Tooling |
| --- | --- |
| **Lint and format** | `ruff check` and `ruff format --check` |
| **Dependency audit** | `pip-audit` (or the `uv`-native audit) |
| **Container image scan** | `trivy` |
| **Secret scanning** | `gitleaks` |

**No deploy job.** There is nowhere to deploy, and a deploy job targeting nothing rots — it accumulates configuration that nobody exercises and then fails for unrelated reasons at the exact moment it is first needed. The full future-state pipeline is designed in [[§5.5]] and stays unbuilt.

The principle behind the smallness, stated so it does not read as laziness: **a gate for a component that does not exist trains people to ignore CI.** A red build that everybody knows is meaningless is worse than no build, because it teaches the team that red is normal.

#### 4.4.1 The gate-growth table — each gate arrives with the thing it protects

| Gate | Trigger that earns it |
| --- | --- |
| Type checking (`mypy --strict`) | The **first typed module** lands |
| Unit and contract tests | The **first data contract** exists ([[§3.1]]) |
| Integration tests against a real local LangGraph server | The **first agent loop runs end to end** |
| Skill validation + skill eval cases | The **skill registry exists** ([[ADR-002b]]) |
| Policy tests (OPA fixtures) | **OPA is wired in** ([[§3.2]]) |
| Ingestion config validation | The **knowledge layer exists** ([[§3.6]].2) |
| Behavioural eval subset (`deepeval`) | There is **behaviour worth asserting on** |
| Retrieval accuracy gate | A **retrieval strategy exists to regress** ([[§3.6]].4) |
| Cost and cache budget gate | **Prompt assembly and token accounting exist** ([[§3.1]].4) |
| `terraform validate` | **Infrastructure code exists** — which is **post-cloud-decision** only |

The growth path is maintained alongside the branching rules in `.kiro/steering/git-workflow.md`; this table is the design-side view of it.

#### 4.4.2 The actual Stage-0 workflow

```yaml
# .github/workflows/ci.yml — the whole pipeline, deliberately
name: ci
on: [pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen             # pinned deps, nothing floats
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  vulnerability-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run pip-audit                       # dependency vulnerabilities
      - uses: aquasecurity/trivy-action@master      # container image scan
        with:
          scan-type: fs
          severity: HIGH,CRITICAL
          exit-code: "1"
      - uses: gitleaks/gitleaks-action@v2           # secret scanning
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# No deploy job. No cloud credentials. Nowhere to deploy to yet (ADR-019).
```
---
