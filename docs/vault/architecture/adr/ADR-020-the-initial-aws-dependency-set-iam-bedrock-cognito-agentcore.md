---
title: "ADR-020: The initial AWS dependency set — IAM, Bedrock, Cognito, AgentCore Gateway, and AgentCore Memory scoped to user preferences only"
type: adr
tags: [adr]
aliases: ["ADR-020"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-04T10:12:35+00:00
---

# ADR-020: The initial AWS dependency set — IAM, Bedrock, Cognito, AgentCore Gateway, and AgentCore Memory scoped to user preferences only

Part of [[1-architecture-decisions-adrs|1. Architecture Decisions (ADRs)]].

**Decision.** Five real AWS services are consumed from local development. The set is closed until an ADR reopens it ([[ADR-019]]).

| Service | Role | Scope |
| --- | --- | --- |
| **IAM roles** | Identity and permission boundary for everything below | Full. Least-privilege roles per component from day one |
| **Bedrock** | All model calls | Full ([[ADR-011]]) |
| **Cognito** | The **one** identity provider — issues the user JWT that L1 validates *and* that AgentCore Gateway accepts as inbound auth | Full, with seeded test users and groups |
| **AgentCore Gateway** | The MCP tool boundary — inbound auth, outbound auth, endpoint-to-MCP-tool exposure | Adopted, replacing the self-built gateway in [[ADR-003]] |
| **AgentCore Memory** | Cross-session user memory | **`USER_PREFERENCE` strategy only.** Not short-term, not summarization, not semantic |

**Explicitly excluded, and why each exclusion is load-bearing:**

| Excluded | Reason |
| --- | --- |
| **EKS, ECR** | These are cloud *deployment*. Standing them up cancels [[ADR-019]] and retires the [[§8]] checkpoint before one feature ships. Deferred to the checkpoint, unmodified |
| **AgentCore Runtime** | It hosts and drives the agent, which takes **prompt assembly** out of our hands. [[P1]], [[P2]] and [[ADR-004]] are the platform's cost model; a managed runtime that owns the prefix repeals them. This is the "managed agent platform" already rejected in [[ADR-018]], and the rejection stands |
| **AgentCore Memory short-term** | It would replace the compaction, restorability, and prefix-preservation machinery that [[ADR-006]], [[ADR-006c]] and [[ADR-016]] exist to provide. See the strategy analysis below |
| **Gateway "no authorization" mode** | The Gateway supports an unauthenticated mode [for development and testing](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html). **Forbidden in every environment, including local.** A dev-only auth bypass is precisely the thing that survives into production, and we would be testing a path we never intend to ship |

#### Why Cognito, and what the seeded users are for

Cognito is the single identity provider for **both** boundaries in [[ADR-010]]: L1 validates the end-user JWT, and AgentCore Gateway accepts the same issuer as [inbound JWT auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html) via a discovery URL with allowed audience and allowed client IDs. One issuer, two consumers, one set of claims — so the `UserPrincipal` that L1 establishes is the same identity the Gateway authorizes against, rather than two identity models that have to be reconciled.

**The seeded users are a correctness fixture, not convenience.** [[Property 32]] says effective access is the *intersection* of agent grant and user scopes, and that the decision cache is keyed on the user. Neither clause can be tested with a single user, and neither can be tested honestly with hand-built fixture tokens — a fixture proves the checking code runs, not that it runs against real claims. The minimum useful set:

| Test user | Cognito group | Exists to prove |
| --- | --- | --- |
| `alice.broad` | `analyst-full` | The happy path: agent grant and user scope both allow |
| `bob.narrow` | `analyst-restricted` | **Intersection**: the same agent, the same tool, denied because the *user* lacks the data scope ([[Property 32]] clause 3) |
| `carol.other-tenant` | `tenant-b-analyst` | Cross-tenant containment ([[Property 1]]) with a genuinely valid token |
| `svc.scheduler` | `service-principal` | A turn with no human behind it carries an explicit service principal, not a null ([[Property 32]] clause 2) |

Cognito **groups map to `UserPrincipal.roles`**, and roles resolve to `data_scopes` in the tenant policy bundle. The `alice`/`bob` pair against one agent is the confused-deputy test, and the `alice`-then-`bob` sequence against a warm decision cache is clause 4.

#### Tenant identity: one federated issuer, not one gateway per tenant

**The question this answers:** a tenant has their own identity provider — possibly a custom server-side API or an internal microservice — and wants the platform to accept *their* auth. How?

**What the Gateway accepts.** Inbound JWT auth is configured with a **discovery URL** (`.well-known/openid-configuration`), plus allowed audience, allowed client IDs, allowed scopes, and optional [custom claim validation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/inbound-jwt-authorizer.html). It trusts an **issuer**, not a product, so any conformant OIDC provider works. Three requirements a tenant's own server must meet:

| Requirement | Fails when |
| --- | --- |
| Publishes an OIDC discovery document **and a JWKS endpoint** | The gateway verifies signatures by fetching public keys; without JWKS there is nothing to verify against |
| Issues **JWTs**, not opaque tokens | A bespoke API returning a random session string cannot be used as inbound auth at all |
| The discovery URL is **publicly reachable by AWS** | **This is the one that bites.** An internal microservice in a private VPC or behind a VPN fails even when it is perfectly OIDC-compliant, because a managed AWS service cannot reach it — and in enterprise, internal IdPs usually are private |

**Decision: federate tenant IdPs behind one Cognito user pool; do not run one gateway per tenant.**

The authorizer is configured **per gateway with a single discovery URL**. Taken naively, "each tenant brings their own IdP" therefore implies one gateway per tenant, which multiplies gateway resources, target registration, tool-catalog wiring, quota, and cost — and fragments the single tool chokepoint that [[ADR-003]] and [[ADR-010]] both assume. Cognito user pools [federate external SAML 2.0 and OIDC providers](https://docs.aws.amazon.com/en_us/cognito/latest/developerguide/cognito-user-pools-identity-federation.html), acting as a bridge and applying **attribute-mapping rules** so downstream systems standardize on one token shape.

That buys four things at once:

1. **One issuer toward the Gateway** — one gateway, one authorizer, one claim shape, regardless of how many tenant IdPs exist.
2. **Claim normalization where it belongs.** Attribute mapping converts each tenant's claim names into the canonical `UserPrincipal` ([[§3.1]]). Without this, every tenant's claim shape leaks into policy evaluation, and [[Property 32]]'s roles → `data_scopes` resolution would need per-tenant parsing code.
3. **A path for private IdPs.** With **SAML** federation the assertion travels through the *user's browser* to the Cognito ACS endpoint, so AWS never needs to reach the tenant's internal IdP — which is the only clean answer to requirement 3 above. **Unverified detail:** that this holds with an uploaded metadata document rather than a metadata URL. Confirm before promising it to a tenant with a private IdP.
4. **Tenant onboarding stays configuration.** Adding a tenant IdP is a Cognito federation entry plus an attribute mapping, not a new gateway and not a code change ([[P12]], [[P16]]).

**When a tenant's auth is genuinely custom** — opaque tokens, no OIDC surface at all — something must translate, and there are only two honest options:

- **The tenant exposes an OIDC surface** and federates normally. Preferred; the work sits with the party that owns the identity.
- **We run a token-exchange broker at L1**: validate their token against their API, then mint a token from an issuer the Gateway trusts. Workable, and the cost must be stated plainly rather than discovered: **the broker becomes a trusted issuer, so compromising it compromises every tenant behind it**, and we would be asserting an identity we did not authenticate ourselves. It needs its own threat model and its own ADR before it ships.

**One more unverified gotcha, recorded because it would surface late.** A secondary source reports that Cognito works as the *server-side* issuer for the Gateway but not for the **client** side of the MCP OAuth flow, because Cognito is an OIDC identity provider rather than an MCP-compliant authorization server — the workaround being an API Gateway façade in front of it. If the goal is for arbitrary third-party MCP clients to connect, **verify this before committing**, because it changes the client story rather than the server story.

#### AgentCore Memory: the strategies, and why only one is adopted

Long-term memory runs [extraction strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/long-term-memory.html) over raw session events and keeps **only the extracted insights rather than the raw conversation**. Triggered when events are written to short-term memory. Assessed one at a time:

| Strategy | What it produces | Verdict |
| --- | --- | --- |
| **`USER_PREFERENCE`** | Durable per-user preferences across sessions | **Adopt.** This fills a genuine gap — the platform has session working memory and an enterprise corpus, and *nothing* that remembers a user between sessions. Lossy extraction is entirely appropriate for "prefers metric units, wants terse answers" |
| **`SUMMARIZATION`** | Session summaries | **Reject.** This is the direct collision. [[P4]] requires that everything removed from context keeps a `Reference` back to the original; this keeps insights and discards the raw. It also duplicates [[ADR-006]]'s anchored summary while being *less* recoverable |
| **`SEMANTIC`** | Facts extracted from conversation, semantic search | **Reject for now.** It builds a second knowledge corpus out of chat transcripts, which is a lower-quality corpus than the ingested one and splits retrieval across two systems — against [[P11]]. Revisit only if a use case wants conversational facts specifically |
| **`EPISODIC`** | Past interaction episodes | **Defer.** Plausibly useful, no use case demanding it yet |
| **Built-in with overrides** | Your own prompt appended, and your own model choice, for the extraction and consolidation steps | **Use, on `USER_PREFERENCE`.** Two reasons: route extraction to a **cheap model** rather than paying conversation-model rates for background housekeeping (the same argument as [[ADR-006c]]), and **constrain what may be extracted** so preferences cannot absorb PII |

**Three findings that constrain how this is wired, all of which matter more than the strategy choice.**

**1 — Tenant isolation is not expressible as a namespace variable.** Namespaces are hierarchical paths, and the documented template placeholders are `{actorId}`, `{sessionId}`, and `{memoryStrategyId}`. There is **no tenant placeholder.** So [[Property 1]] has to be bought some other way, and the two options are not equivalent:

- **One Memory resource per tenant** — a hard resource boundary, isolation by construction, and an IAM-enforceable one. **Recommended.** Open question: the per-account resource quota, which needs checking before we rely on it at tenant scale.
- **Encode the tenant into `actorId`** (`"{tenant_id}:{user_subject}"`) — one resource, but isolation now rests on string-construction discipline in every call site. One malformed `actorId` cross-contaminates tenants, and the failure is silent. Rejected as the default.

**2 — Events written to managed memory must be post-redaction.** Extraction reads raw conversation events, so anything written there is both persisted in a managed store *and* fed to a model. [[Property 10]] (no raw PII crosses the provider boundary) and [[Property 11]] (PII tokenized in every persisted surface) both apply. **Redaction happens before the write, never after** — and since [[ADR-009]]'s self-hosted PII stack is [[Phase 6]], the regulated-data precondition covers this surface too. This is [[Property 33]].

**3 — Extraction is model work we do not see.** The extraction and consolidation steps consume tokens on our account that never pass through our model proxy, so they are **invisible to the [[§5.6]] token ledger and to the KV-cache accounting**. Cost per task will understate reality by whatever memory extraction costs. Fix: attribute it from billing rather than from the ledger, and record the gap rather than discovering it as a variance.

**Consequences.**
- (+) The three hardest parts of a tool boundary — inbound auth, outbound auth on behalf of a user, and endpoint-to-MCP exposure — are bought rather than built, and the Gateway's on-behalf-of model **matches** the identity design in [[ADR-010]] rather than fighting it.
- (+) Cross-session user memory arrives without building a second storage tier for it.
- (+) One identity provider, real tokens, and a test-user matrix that makes [[Property 32]] genuinely testable instead of fixture-testable.
- (−) **[[ADR-003]]'s per-pool containment is weakened.** Per-pool circuit breakers, per-pool network policy, and domain-pool isolation were ours; a managed gateway supplies its own isolation model instead. This is a real reduction in blast-radius control and is accepted deliberately.
- (−) **A second memory system exists**, with a different durability model from ours. The boundary must stay sharp: **within-session working memory is ours and restorable; cross-session user preference is AgentCore's and lossy.** Blurring that line reintroduces the summarization collision through the back door.
- (−) **Local development now needs an AWS account with five services, and none of it works offline.** The dependency set is closed for exactly this reason.
- (−) AgentCore is a young service surface. Several details here — resource quotas, and whether extraction cost is attributable per tenant — are **recorded as unverified and must be confirmed before [[Phase 2]]**.

**Alternatives considered.**
- **Build our own gateway per [[ADR-003]] as originally designed** — still the stronger containment story, and rejected only on effort: inbound/outbound OAuth on behalf of an end user is a large amount of security-critical code to own before a single feature ships. If the containment loss proves to matter, [[ADR-003]] is restorable — the tool interface is unchanged either way.
- **Adopt all AgentCore Memory strategies** — rejected. `SUMMARIZATION` contradicts [[P4]] outright, and `SEMANTIC` splits retrieval against [[P11]]. Taking the whole product because part of it is useful is how the summarization collision would enter unnoticed.
- **Keycloak in a container instead of Cognito** — genuinely viable and cheaper, and rejected for a specific reason: the Gateway needs a discovery URL it can reach, and a local container is not reachable from a managed AWS service. Local dev would then use a different IdP from every other environment, which is exactly the local/cloud divergence [[P16]] exists to prevent.
- **One gateway per tenant, each trusting that tenant's own IdP directly** — rejected. It removes the need for federation, and it pays for that with N gateways to provision, N target registrations, N tool-catalog wirings, and a quota ceiling on tenant count — while fragmenting the single tool chokepoint [[ADR-003]] and [[ADR-010]] are built around. Federating behind one issuer keeps tenant onboarding a configuration change.
- **Passing each tenant's raw claims straight through to policy evaluation** — rejected. Without Cognito's attribute mapping normalizing claims into one `UserPrincipal` shape, every tenant's claim naming leaks into the authorization path, and [[Property 32]] would need per-tenant claim-parsing code. That is a per-tenant code path in the security-critical layer, which is the worst place to have one.
- **Fixture JWTs instead of real Cognito users** — rejected. It tests that our validation code runs, not that it validates real claims, and claim-shape mismatches are a classic integration failure.
