---
title: "References"
type: hub
tags: [hub]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# References

- [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache economics, tool masking over mutation, restorable compression, goal recitation, keeping errors in context, observation variation, context isolation, harness-quality test.
- [Anthropic prompt caching documentation](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — prefix-match caching, cache breakpoints, cost and time-to-first-token effects, cache-write premium.
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/) — LLM-extracted entity/relationship graphs and community summaries for global and multi-hop queries.
- [GEPA: Reflective Prompt Evolution](https://arxiv.org/abs/2507.19457) and [DSPy](https://dspy.ai/) — Track B optimization; reported gains over GRPO and MIPROv2 with far fewer rollouts.
- [Agent Lightning](https://www.microsoft.com/en-us/research/project/agent-lightning/) — adding RL to an existing LangChain/LangGraph/AutoGen stack without rewriting it.
- [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/latest/index.html) — Colang policies, input/output/retrieval rails, PII and jailbreak catalog.
- [Microsoft Presidio](https://microsoft.github.io/presidio/) — PII detection and redaction before model egress.
- [LangSmith](https://docs.smith.langchain.com/) — tracing, datasets encoding expected retrieved documents and expected agent steps, CI integration.
- [DeepEval](https://deepeval.com/docs/getting-started) — pytest-native LLM regression testing as a CI gate.
- [LangGraph](https://langchain-ai.github.io/langgraph/), [AutoGen](https://microsoft.github.io/autogen/stable/), [Google ADK](https://google.github.io/adk-docs/), [A2A protocol](https://a2a-protocol.org/) — prior art for declarative agent execution graphs.

**Context engineering and compaction**

- [Context Engineering for AI Agents: Lessons from Building Manus](https://www.manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) and a [third-party summary](https://tianpan.co/blog/2026-03-02-context-engineering-lessons-from-manus) — the primary source for [[P1]]–[[P6]], tool masking, restorable compression, goal recitation, keeping errors in context, and the roughly one-third-of-actions-on-bookkeeping finding that motivates a dedicated planner ([[ADR-002]]).
- [Prompt caching for long-horizon agentic tasks](https://arxiv.org/html/2601.06007v1) — evaluations reporting large API cost reductions and time-to-first-token improvements from correct prefix caching; the empirical basis for treating KV-cache hit rate as the north-star cost metric ([[ADR-004]]).
- [Context compaction](https://arxiv.org/html/2602.22402v1) and [structurally lossless trimming](https://arxiv.org/html/2510.00615v1) — the compaction tiers and the reported reductions cited in [[ADR-006]], including agent-decided ("active") compaction and ACON-style compression.
- [OpenClaw session management and compaction internals](https://github.com/openclaw/openclaw/blob/main/docs/reference/session-management-compaction.md) — **primary source for the compaction mechanics corrected in this revision**: compaction as an appended entry carrying a summary plus a cut point and a pre-compaction token count; the transcript as a **tree** of `id`/`parentId` entries, which is what makes forking native for sub-graph spawn and scope-2 re-attempt; the rule that a chunk boundary must never separate an assistant tool call from its result, and that aborted or errored call blocks may split freely; the **pre-compaction memory flush** as a silent agentic turn on a soft threshold below the compaction threshold, once per cycle, cheap-model routable, skipped on a read-only workspace ([[ADR-006c]]); **silent turns** via a sentinel suppressed on both the buffered and streaming paths ([[ADR-006d]]); the **mid-turn precheck that raises a structured signal** for the outer run loop rather than compacting inline; overflow recovery that recognizes an error family, forwards the provider's reported attempted token count, falls back to a minimally over-budget synthetic count, and preserves the session mapping; a **pluggable summarization provider with automatic built-in fallback** while genuine aborts are re-thrown; the **three freshness timestamps** and the rule that system events must not extend idle-expiry freshness; the **fork constraints** (refused during an active parent run, fresh token counters for the child) and the ~100K-token cap that forces isolated child context regardless of any complexity flag; and the honest framing that the context-token counter is a runtime estimate rather than a guarantee. **Its state topology is deliberately NOT adopted — see [[§7.12]].**

**Gateway, tooling, and platform topology**

- [Enterprise MCP architecture](https://markaicode.com/architecture/enterprise-mcp-architecture/) and [what an MCP gateway is](https://konghq.com/blog/learning-center/what-is-a-mcp-gateway) — the layered gateway → orchestrator → domain-isolated pool topology, per-pool circuit breakers, registry watching, mTLS between tiers, and per-tenant limits enforced in the orchestrator rather than only at the edge ([[ADR-003]], [[ADR-010]]).
- [OpenClaw architecture](https://extuitive.com/articles/how-does-openclaw-work) — gateway control plane, session runtime, and **extensible skills** as a reference point for the control-plane/runtime split and the shape of capability extension. This is the prior art behind [[ADR-002b]]: skills as loadable, attachable capability units distinct from tools. Read alongside **[[§7.12]]**, which records that the single-Gateway-owns-all-session-state topology is correct for a self-hosted single-user assistant and wrong for a multi-tenant platform.
- [Anthropic Agent Skills — progressive disclosure loading system](https://anthropics-skills.mintlify.app/spec/loading-system) — **primary source for the three-level skill model in [[ADR-002b]]**: Level 1 metadata always resident in the prefix, Level 2 `SKILL.md` body loaded on trigger with a target under roughly 500 lines, Level 3 bundled `scripts/`, `references/`, and `assets/` loaded on demand and unlimited in size. It supplies the finding that **bundled scripts execute without being read into context** — zero context cost, unlike reference documents which cost tokens when read — and the concrete token budgets (≈100 tokens of metadata per skill; ~5,000 tokens of index for 50 skills against ~50,000 if loaded eagerly; ~10,000 with one skill active) that the per-agent skill-count ceiling and [[Property 25]] are now derived from. Also the authoring guidance adopted here: prefer a script over prose for deterministic work, and state trigger conditions explicitly in the description, since the description is all the model sees at selection time.

**Knowledge layer**

- [Microsoft GraphRAG documentation](https://microsoft.github.io/graphrag/) and the [GraphRAG research announcement](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/) — entity/relationship extraction, community summaries, and why multi-hop and global-corpus questions need more than vector similarity ([[ADR-007]]).
- [Haystack 2.x pipeline serialization](https://docs.haystack.deepset.ai/docs/serialization) — the components-plus-named-connections format an earlier draft of [[§3.6]] was modeled on. **Retained as a rejected alternative, not as a dependency:** [[ADR-015]] now records why full pipeline-as-YAML was dropped in favour of Terraform for infrastructure, code for pipelines and retrieval, and a narrow typed config for chunking and embeddings.

**Improvement layer**

- [GEPA: reflective prompt evolution](https://arxiv.org/html/2507.19457v1) — the reported margins over GRPO and MIPROv2 with far fewer rollouts, and the natural-language-reflection thesis behind RL Phase A.
- [Agent RL framework landscape](https://www.turingpost.com/p/agent-rl-training-tools) — the survey behind the framework comparison table in [[ADR-008]].
- [VerlTool: RLVR for multi-turn tool use](https://arxiv.org/abs/2509.01055) — verifiable-reward design over tool trajectories, the reference for RL Phase C reward construction.
- [`docs/vault/architecture/agent-tuning-loop.md`](../../../docs/vault/architecture/agent-tuning-loop.md) — the externally-provided agent auto-tuning reference diagram and the full analysis of what it gets right, the three gaps, and the two constraints. Folded into **ADR-008a**.

**Guardrails, evaluation, and CI**

- [NeMo Guardrails PII detection catalog](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/pii-detection) — PII rails across input, output, and retrieval flows ([[ADR-009]]).
- [DeepEval regression testing in CI/CD](https://deepeval.com/guides/guides-regression-testing-in-cicd) — pytest-native quality gates ([[§5.4]]).
- [LangSmith CI/CD pipeline example](https://docs.langchain.com/langsmith/cicd-pipeline-example) — eval runs wired into pull-request pipelines ([[§5.5]]).

**Framing and skepticism**

- [Graph engineering guide](https://www.aibuilderclub.com/blog/graph-engineering-guide-2026) — the cumulative prompt → context → harness → loop → graph stack and the "who decides the path" discriminator ([[ADR-012]]). Read alongside [[§7.2]], which records that the term originated on X in mid-2026, is **not** a Karpathy-authored essay, describes mechanics that predate the label, and was publicly questioned by LangGraph's own creator as to whether it names anything new.

> Content was rephrased for compliance with licensing restrictions. This applies to the two primary sources added in this revision as well — the Agent Skills loading-system specification ([[ADR-002b]]) and the OpenClaw session-management and compaction documentation ([[ADR-006]], [[ADR-006c]], [[ADR-006d]], [[§2.10]], [[§3.1]].11, [[§7.12]]) — both of which are cited inline at the point of use and carry a rephrasing note there. Reported figures are attributed to the sources above; no pricing or benchmark numbers beyond those sources are asserted here.
>
> **Unverified in this session:** the specifics of how commercial providers implement internal model-selection routing could not be checked (web search was unavailable). [[ADR-013]] describes only the publicly discussed *general* pattern — a lightweight routing model in front of a family of models, trained on usage and preference signals — and flags it as requiring verification before it is relied upon. No claims about any specific provider's internals are made anywhere in this document.
