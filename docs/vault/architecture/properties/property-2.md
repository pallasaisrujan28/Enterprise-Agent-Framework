---
title: "Property 2: Authorization independent of masking"
type: property
tags: [property]
aliases: ["Property 2"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-07-31T18:38:27+00:00
---

# Property 2: Authorization independent of masking

Part of [[correctness-properties|Correctness Properties]].

For all executed tool calls `c`: `authorize(c)` returned `Allow` or `AllowWithObligation` under the `policy_version` recorded on `c`. A call that the mask permitted but policy denies is still rejected, because enforcement at the MCP gateway does not consult the mask.
