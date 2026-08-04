---
title: "ADR-021: Tools are reached only through the MCP gateway, and tool selection is semantic search"
type: adr
tags: [adr, tools]
aliases: ["ADR-021"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-04T10:12:35+00:00
---

# ADR-021: Tools are reached only through the MCP gateway, and tool selection is semantic search

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Three parts, and the first is the one that matters architecturally.

1. **Every tool is behind the AgentCore MCP gateway from the first tool.** No in-process tool functions, ever — not even for convenience during early development. This is what makes everything else a configuration change rather than a rewrite.
2. **Tool selection is [semantic search](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-semantic-search.html)**, enabled on the gateway at creation. The agent calls `x_amz_bedrock_agentcore_search` with a natural-language query and receives the relevant tool specs, which are then injected into `toolConfig` for the following turn.
3. **The mode is a per-agent field**, `tool_selection: semantic | declared`, so a narrow agent can be switched to declared selection without touching code.

**Context.** The alternative — carrying every tool definition statically in the cached prefix — is what Waku does (`ToolRegistry.schemas()` returns all of them) and what Hermes does today, with their stated reason being that *every model tool ships on every API call*, hence a deliberately brutal bar on adding one.

That approach has a measured ceiling. At roughly 50 tools (~8K tokens) most models hold 84–95% tool-selection accuracy; at ~200 tools (~32K tokens) accuracy falls to **41–83% depending on model**. A published study reports a **99.6% reduction in tool-related tokens at a 97.1% hit rate for K=3** over 121 tools. So a large static catalog is not merely expensive, it makes the model measurably worse at choosing. Hermes has an open issue moving toward hybrid tool search for exactly this reason.

**Rationale, and the honest shape of the trade.** Search returns invocable tool specs, so **provider-side schema validation is preserved** — the model still emits a validated tool call, it just learns the schema one turn earlier. That was the open question and it resolves in favour of search.

The cost is specific and it lands on [[P1]]: **injecting tool specs mid-conversation changes `toolConfig`, which is part of the cached prefix, so every search invalidates the cache.** A conversation that searches once pays one cache break; one that searches repeatedly pays repeatedly.

| Approach | Baseline prefix | Cache behaviour | Selection accuracy at scale |
| --- | --- | --- | --- |
| **Declared** (rule states `required_tools`) | All of the agent's tools, ~150 tokens each | Never breaks | Perfect — it is a lookup, not a ranking |
| **Semantic search** | One tool | **Breaks on every search** | Degrades gracefully; the only viable option past ~50 tools |

**At our current scale declared selection would measure better.** An eight-tool agent is ~1,200 cached tokens that never break, against a search round trip plus a guaranteed cache miss. Semantic search is chosen anyway, deliberately, to avoid a migration at the point where the catalog grows — and because a per-agent switch means the narrow case can be reverted with config if the measurements say so.

**Consequences.**
- (+) **No migration when the catalog grows.** The gateway, the search path, and the injection mechanism are exercised from day one rather than retrofitted at the point of pain.
- (+) The baseline prefix stays tiny regardless of how many tools exist across the platform.
- (+) Schema validation survives, because search hands back real specs.
- (−) **Cache hit rate takes a measurable hit, and [[P1]] is the north-star metric.** The mitigation is to instrument it in the first slice, so the cost is observed rather than argued about.
- (−) An extra round trip per search, on the user's critical path.
- (−) A ranking step is a new failure mode: a search that returns the wrong three tools produces a wrong answer with no error. `required_tools` in the rule file is the cross-check — a rule that names its tools makes a bad ranking detectable.
- (−) **Diagnostic ambiguity while the platform is young.** With one tool and a search step, a misbehaving agent has two candidate causes instead of one. Accepted knowingly.

**Alternatives considered.**
- **Static catalog, all tools in the prefix** — rejected on the accuracy data above, and because it forces the Hermes discipline of refusing tools to protect the prefix, which pushes capability into skills whether or not that is the right home for it.
- **Declared selection from `required_tools`, no search** — genuinely competitive today and still the recommended mode for a narrow agent. Rejected as the *default* to avoid building only the path that stops working at scale.
- **Lazy per-tool schema fetch without semantic ranking** — rejected. It pays the same cache cost as search while giving up the ranking that makes a large catalog navigable.
- **Threshold-triggered switch, declared until 25 tools** — rejected in favour of exercising the eventual path from the start, accepting a worse measurement now for a cheaper path later.

> **Note on tech choices.** **Kubernetes remains a decided constraint rather than a substitutable default** ([[ADR-018]]) — but it is the **eventual** target and is **not yet active** ([[ADR-019]]). The current runtime is Docker Compose. Everything else named later (Envoy, OPA, Redis, LiteLLM-style proxy, Neo4j, OpenSearch/pgvector, LangSmith, DeepEval, GitHub Actions, and the specific autoscaling components in [[§5.7]]) is a **reasonable, model-agnostic default** rather than a hard requirement — and each one now carries a recorded selection rationale and tradeoff in [[§4.1]] rather than appearing as an unexplained product name. The ADRs above constrain the *shape* of the system; substitutable products may be swapped if they satisfy the same principles.
---
