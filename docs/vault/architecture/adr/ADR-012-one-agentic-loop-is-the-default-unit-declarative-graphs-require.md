---
title: "ADR-012: One agentic loop is the default unit; declarative graphs require justification"
type: adr
tags: [adr, graph]
aliases: ["ADR-012"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:43:44+00:00
---

# ADR-012: One agentic loop is the default unit; declarative graphs require justification

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** The default implementation of any capability is **a single agentic loop** — an agent with a goal, a quality bar, a small toolset, and permission to choose its own route. A declarative execution graph is introduced only when a specific forcing function applies, and each new node must be justified against the list below in the PR that adds it.

**Context.** The existing system models every agent as a node in one flat LangGraph graph with central orchestrators routing between them, and it stops scaling as node count and classification branches grow. This is the single most important correction in this design; [[§6]] covers the migration in detail.

**Rationale.** The real discriminator between a loop and a graph is **who decides the path** — the agent, or you. A loop is a graph with one node. Choosing a graph means choosing to declare valid paths and the checks between them, which is worth it only when you actually need that declaration. Legitimate forcing functions:

1. Genuinely distinct specialties that need different system prompts.
2. A different model or toolset per step (cheap classifier vs frontier reasoner).
3. Fan-out/fan-in over independent subtasks.
4. Routing that must be **auditable** (regulated decisions, approval chains).
5. Failure isolation, where one step's blast radius must not reach another.
6. A dedicated **read-only reviewer** node that cannot mutate state.

If none of these apply, the node should be collapsed into the loop. Prior art for when a graph *is* warranted: [LangGraph `StateGraph`](https://langchain-ai.github.io/langgraph/), [AutoGen `GraphFlow`](https://microsoft.github.io/autogen/stable/), [Google ADK](https://google.github.io/adk-docs/), and the [A2A protocol](https://a2a-protocol.org/) for cross-agent interop.

**Apply the ladder before applying this list.** The forcing functions above answer "does this need a graph?" — but that is the *third* question, not the first. [[§2.12]] defines the mechanical decision ladder (**skill → tool → sub-graph**) that a reviewer applies in order. Most requests that arrive framed as "we need another node" are a skill (a procedure over existing tools, [[ADR-002b]]) or at most a tool ([[§3.8]]). A sub-graph is reached only when one of the six forcing functions genuinely applies, and when it is reached it is **invoked by the parent as a tool** with its own isolated context and its own stable prefix — so the parent's graph still does not grow ([[§2.12]]).

**Consequences.**
- (+) Router prompts stay small because the orchestrator routes to a handful of sub-agent *types*, not to every classification branch.
- (+) Fewer, stronger loops means fewer context handoffs and fewer cache-busting prefix variants.
- (−) Requires review discipline; "add a node" is the path of least resistance and must be actively resisted.
- (−) Some existing classification nodes will be deleted, which is migration work with behavioural risk ([[§6.3]]).

**Alternatives considered.** Keep expanding the flat graph — rejected, this is the reported failure mode. Go fully graph-free with one mega-agent — rejected, it violates [[P3]] (toolset size) and [[P5]] (context isolation) and gives up the auditable routing that enterprise tenants require.
