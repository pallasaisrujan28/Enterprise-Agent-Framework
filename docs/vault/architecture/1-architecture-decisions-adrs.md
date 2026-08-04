---
title: "1. Architecture Decisions (ADRs)"
type: hub
tags: [hub]
aliases: ["§1"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-04T10:12:35+00:00
---

# 1. Architecture Decisions (ADRs)

Each decision follows the format: **Decision → Context → Rationale → Consequences → Alternatives considered**. These are the principles the platform commits to.

## In this section

- [[ADR-001-layered-architecture-instead-of-one-flat-langgraph-graph|ADR-001: Layered architecture instead of one flat LangGraph graph]]
- [[ADR-002-hierarchical-planner-executor-sub-agents-with-context-isolation|ADR-002: Hierarchical planner/executor sub-agents with context isolation]]
- [[ADR-002b-capability-extension-via-skills-with-progressive-disclosure|ADR-002b: Capability extension via Skills with progressive disclosure]]
- [[ADR-003-mcp-gateway-fronting-isolated-tool-server-pools|ADR-003: MCP gateway fronting isolated tool-server pools]]
- [[ADR-004-kv-cache-first-prompt-assembly|ADR-004: KV-cache-first prompt assembly]]
- [[ADR-005-tool-masking-logit-allowlist-instead-of-dynamic-add-remove|ADR-005: Tool masking (logit/allowlist) instead of dynamic add/remove]]
- [[ADR-006-restorable-compression-with-filesystem-object-store-as-external|ADR-006: Restorable compression with filesystem/object store as external memory]]
- [[ADR-006b-observation-variation-is-allowed-only-after-the-cache-breakpoint|ADR-006b: Observation variation is allowed only after the cache breakpoint]]
- [[ADR-006c-pre-compaction-memory-flush-let-the-agent-save-what-matters|ADR-006c: Pre-compaction memory flush — let the agent save what matters before you compact]]
- [[ADR-006d-silent-turns-agent-turns-whose-output-is-never-delivered|ADR-006d: Silent turns — agent turns whose output is never delivered]]
- [[ADR-007-hybrid-rag-graphrag-retrieval|ADR-007: Hybrid RAG + GraphRAG retrieval]]
- [[ADR-008-continuous-improvement-as-two-distinct-tracks-behaviour-tuning|ADR-008: Continuous improvement as two distinct tracks — behaviour tuning now, weight training later]]
- [[ADR-009-guardrail-pipeline-pii-strategy-delivered-in-two-stages|ADR-009: Guardrail pipeline + PII strategy, delivered in two stages]]
- [[ADR-010-multi-tenancy-and-a-three-check-authorization-model-split|ADR-010: Multi-tenancy, and a three-check authorization model split across two gateways]]
- [[ADR-011-one-provider-aws-bedrock-behind-a-model-proxy-task-routing-is-a|ADR-011: One provider (AWS Bedrock) behind a model proxy; task routing is a later config change]]
- [[ADR-012-one-agentic-loop-is-the-default-unit-declarative-graphs-require|ADR-012: One agentic loop is the default unit; declarative graphs require justification]]
- [[ADR-013-classification-is-one-bedrock-model-call-made-safe-by|ADR-013: Classification is one Bedrock model call, made safe by recoverability rather than accuracy]]
- [[ADR-014-prompt-and-policy-artifacts-are-versioned-immutable-and-canaried|ADR-014: Prompt and policy artifacts are versioned, immutable, and canaried]]
- [[ADR-015-terraform-owns-infrastructure-a-narrow-typed-config-owns-only|ADR-015: Terraform owns infrastructure; a narrow typed config owns only chunking and embeddings; everything else is code]]
- [[ADR-016-tiered-session-storage-sandbox-nvme-s3-express-one-zone-s3|ADR-016: Tiered session storage — sandbox NVMe, S3 Express One Zone, S3 Standard, Redis]]
- [[ADR-017-phased-delivery-one-thin-vertical-slice-then-widen|ADR-017: Phased delivery — one thin vertical slice, then widen]]
- [[ADR-018-kubernetes-is-the-eventual-deployment-target-not-yet-active|ADR-018: Kubernetes is the eventual deployment target (not yet active)]]
- [[ADR-019-local-first-development-on-docker-compose-cloud-deferred-behind|ADR-019: Local-first development on Docker Compose; cloud deferred behind an explicit checkpoint]]
- [[ADR-020-the-initial-aws-dependency-set-iam-bedrock-cognito-agentcore|ADR-020: The initial AWS dependency set — IAM, Bedrock, Cognito, AgentCore Gateway, and AgentCore Memory scoped to user preferences only]]
- [[ADR-021-tools-are-reached-only-through-the-mcp-gateway-and-tool|ADR-021: Tools are reached only through the MCP gateway, and tool selection is semantic search]]
