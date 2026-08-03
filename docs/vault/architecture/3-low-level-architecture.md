---
title: "3. Low-Level Architecture"
type: hub
tags: [hub]
aliases: ["§3"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T14:18:45+00:00
---

# 3. Low-Level Architecture

This section defines **the data passed between components**, **how components interact**, and a **detailed end-to-end walkthrough of a single request**. Contracts are written as structured pseudocode; JSON-shaped payloads use deterministic key ordering ([[P2]]).

## In this section

- [[3-1-core-data-contracts|3.1 Core Data Contracts]]
- [[3-2-access-policies-user-authentication-agent-authentication-and|3.2 Access Policies: User Authentication, Agent Authentication, and Tool Authorization]]
- [[3-3-how-systems-interact|3.3 How Systems Interact]]
- [[3-4-end-to-end-walkthrough-of-a-single-request|3.4 End-to-End Walkthrough of a Single Request]]
- [[3-5-context-compaction-points-summary|3.5 Context Compaction Points (summary)]]
- [[3-6-document-sync-ingestion-config-and-the-retrieval-accuracy|3.6 Document Sync, Ingestion Config, and the Retrieval Accuracy Harness]]
- [[3-7-key-function-signatures|3.7 Key Function Signatures]]
- [[3-8-adding-and-evolving-tools|3.8 Adding and Evolving Tools]]
- [[3-9-data-source-contract-legislation-gov-uk-endpoints-responses-and|3.9 Data Source Contract: legislation.gov.uk Endpoints, Responses, and Storage]]
