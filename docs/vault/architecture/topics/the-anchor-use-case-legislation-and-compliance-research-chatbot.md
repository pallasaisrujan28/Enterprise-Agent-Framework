---
title: "The Anchor Use Case: Legislation and Compliance Research Chatbot"
type: topic
tags: [topic]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-01T13:52:07+00:00
---

# The Anchor Use Case: Legislation and Compliance Research Chatbot

Part of [[overview|Overview]].

Every capability in this document is justified against **one concrete scenario**, recorded here so that "is this feature needed" has an answer other than opinion. A design with no anchor use case produces infrastructure nobody asked for, and eval cases that measure nothing in particular.

**The scenario.** A compliance analyst holds a **conversation** with the platform: *"What are our director duties under the Companies Act? … and how did that change after the 2023 amendments? … does our internal delegation policy actually satisfy s.172?"* Multi-turn, each turn potentially pulling entire Acts and internal policy documents into play, and every answer required to cite the exact provision **and the version of it that was in force**.

**Three defining properties, and all three were chosen deliberately.**

1. **Tool outputs exceed the context window by design, on the first call.** Fetching a full Act is megabytes of structured XML. Not an edge case to degrade gracefully on — the normal case.
2. **The documents must be read whole, not merely searched.** "Does our policy satisfy this duty" is not a snippet-retrieval question. It requires the provision, its amendments, and the internal policy side by side.
3. **It is a chatbot.** Multi-turn conversation is what exercises session state, freshness, compaction across turns, cross-session memory, streaming, and the clarification exit — none of which a single-shot task touches.

**The data source is real, public, and free.** [legislation.gov.uk](https://www.legislation.gov.uk/) is operated by The National Archives with a **RESTful API using content negotiation**, giving access to the statute book *at various levels and for various times*. The base content format is **CLML XML**, with **Akoma Ntoso** available by appending `/data.akn`, plus HTML fragments and RDF. URIs are structured and predictable — `/{type}/{year}/{number}[/{section}]`. Official documentation is published at [legislation/data-documentation](https://github.com/legislation/data-documentation).

**Why this beats the alternatives considered.** Two earlier anchors were written and retired: a support-desk entitlement triage case (**too small a payload** — it left the entire external-memory and compaction stack unexercised) and a cloud cost investigation case (**good on payload size, but the data only becomes interesting as our own bill grows, and it needed credentialed access**). Legislation wins on four counts:

| Advantage | Detail |
| --- | --- |
| **Massive from request one** | No account to grow, no spend to accumulate, no credentials. A single Act is enormous immediately |
| **Zero privacy surface** | Public legislation under open licence. **No PII of any kind**, so [[ADR-009]]'s regulated-data precondition is satisfied without contortion rather than by careful avoidance |
| **A genuine graph, not a contrived one** | Legislation is a citation and amendment network: an Act is amended by Statutory Instruments, each with commencement dates, some **prospective** ("changes that may be brought into force at a future date"). Answering "as at date X" is inherently multi-hop. This makes **GraphRAG ([[ADR-007]]) justified rather than aspirational** |
| **Groundedness is deterministically checkable** | A cited provision either exists and says that, or it does not. Eval cases become hard assertions instead of judgement calls — the single biggest weakness of most agent evaluation |

**What it exercises, claim by claim:**

| Architectural claim | What this use case makes real |
| --- | --- |
| **External memory over lossy summarization** ([[P4]], [[ADR-006]], [[ADR-016]]) | **Load-bearing on turn one.** An Act cannot be inlined, so offload to T1 with a restorable `Reference` is the only path by which the request completes. [[Property 9]] stops being a nicety |
| **Level-3 skill scripts at zero context cost** ([[ADR-002b]]) | The strongest possible case for scripts over prose. Parsing CLML, resolving an amendment chain, extracting a provision at a date — all exact work, done by a script the model never reads |
| **Chunking as the one configurable surface** ([[ADR-015]]) | **CLML and Akoma Ntoso are deeply nested, and character-count chunking destroys provision boundaries.** Chunking must follow the document's own structure. This is the concrete justification for chunking being configurable while everything else is code |
| **Mid-turn precheck** ([[ADR-006]] rule 6) | Fires constantly: a document lands and the prompt no longer fits before the next call |
| **Compaction tiers + memory flush** ([[ADR-006c]]) | A long research conversation accumulates conclusions across many turns. This is the long-horizon behaviour the design has so far only reasoned about |
| **Cross-session user memory** ([[ADR-020]]) | "I always work in the Scottish jurisdiction, cite OSCR guidance" is a durable user preference, which is exactly what `USER_PREFERENCE` is good at and what nothing else in the design covers |
| **The three freshness timestamps** ([[§2.10]], [[Property 31]]) | A chatbot has idle sessions, resumed sessions, and background activity. The distinction between real interaction and system events becomes observable rather than theoretical |
| **Streaming vs output rails** | A chatbot must feel responsive while answers are still guardrail-checked. The buffered-answers, streamed-progress tension is forced into the open |
| **The `ask` exit** ([[§2.2]]) | **Legislative answers are date-dependent and jurisdiction-dependent.** "What does s.172 say" has no single correct answer without a date and a jurisdiction. A correct agent asks; a plausible-sounding one guesses |
| **Fan-out via sub-graph as a tool** ([[§2.12]].1) | "Check each of the fourteen SIs that amended this Act" is natural fan-out, and the parent branch grows large enough that the **fork size cap actually triggers** ([[Property 30]]) |
| **Delegated user RBAC** ([[Property 32]]) | Public legislation is public — but the **tenant's internal policy corpus is not.** HR policy, board papers, and finance procedures are reachable by different roles. Same agent, same `search_policy` tool, different corpora per user |
| **HITL approval** ([[§2.4]]) | The write action is **publishing an entry to the tenant's obligation register** — a real compliance artifact that a firm does not let an agent write unreviewed |
| **`REROUTE`** ([[ADR-013]]) | A question about case law or about HMRC practice is not a statute question and belongs elsewhere |
| **Multi-tenancy** ([[ADR-010]]) | Several client organisations, each with their own internal policy corpus, their own jurisdiction defaults, and their own identity provider |

#### The data source in detail, and the constraints it imposes

Collected from the official [data documentation](https://legislation.github.io/data-documentation/), because several of these facts change the design rather than merely informing it.

**Scale, from the authoritative source.** The site holds **over 300,000 documents**, with "often many hundreds of ways users can view (sections of) each one" — and, decisively for this design, **some individual documents contain more than 10,000 pages worth of text** ([fair use policy](https://legislation.github.io/data-documentation/fair-use.html)). That is the offload justification stated by the publisher, not estimated by us.

**URI scheme.** Predictable and constructable, which means most lookups need no search step:

```
https://www.legislation.gov.uk/{type}/{year}/{number}[/{section}][/{authority}][/{extent}][/{version}]
https://www.legislation.gov.uk/id/{type}/{year}/{number}[/{section}]     # abstract identifier
https://www.legislation.gov.uk/id?title={title}                          # when the number is unknown
https://www.legislation.gov.uk/eur/2019/2013/2021-03-01/data.xml         # POINT IN TIME as a path segment
```

**The point-in-time date is part of the URI.** This is the single most useful fact for this use case: a revised version "as at" a date is directly addressable. So a citation can be a URI that **pins the version**, temporal answers are cacheable by construction, and [[Property 34]] below is implementable rather than aspirational.

**Formats** ([overview](https://legislation.github.io/data-documentation/formats/overview.html)):

| Format | Suffix | Use here |
| --- | --- | --- |
| **CLML** — Crown Legislation Markup Language, against a published [schema](https://www.legislation.gov.uk/schema/legislation.xsd) | `data.xml` | Primary ingestion format. A published schema means a **Level-3 script can parse it deterministically** rather than a model interpreting it |
| **Akoma Ntoso** | `data.akn` | Alternative, less complex; the international standard |
| XHTML snippet / HTML5 | `data.htm`, `data.xht` / `data.html` | Not used for ingestion — presentational |
| PDF | `data.pdf` | Only where XML does not exist |
| **Atom** (feeds only) | `data.feed` | Listings, search results, effects, and the Publication Log |
| RDF/XML | `data.rdf` | Metadata graph |

**Fair use, which is a hard constraint and not a courtesy.** Four rules, each with a design consequence:

| Rule | Consequence for us |
| --- | --- |
| **3,000 requests per 5 minutes**, and **the limit applies to the user, not the IP address** — multiple IPs collectively exceeding it still counts as exceeding it | **This is a single global budget shared across every tenant.** A per-replica rate limiter is not merely insufficient, it is non-compliant: scaling out pods multiplies IPs against one shared allowance. Requires a **centrally shared token bucket** plus **per-tenant fair-share allocation**, or one tenant's research session starves all others. This is exactly the "rate limits in two places" argument in [[§3.2]].4, with a third place added: a shared *upstream* budget |
| A **`User-Agent` identifying the bot with contact details** is mandatory; **anonymous user agents are grounds for blocking** | A compliance value in tool-pool configuration, asserted at startup. A deploy that drops it does not degrade — it gets the platform blocked |
| **`robots.txt` must be followed**, including `crawl-delay`; absent one, roughly 10 requests per 5–10 seconds | The conservative rate is ~1–2 req/s, far below the ceiling. Design for the *recommended* rate, not the limit |
| For bulk or one-off crawls, **use the feeds instead of crawling**, and contact them first | Backfill is a planned operation, not something to attempt casually |

**The Publication Log is the ingestion watermark, and this is a strong fit rather than a coincidence.** The [Publication Log](https://legislation.github.io/data-documentation/api/publication-log.html) is an Atom feed with one entry per publication, republication, or withdrawal, covering legislation, associated documents, Impact Assessments, and **changes to legislation (effects)**. It is filterable by date path segment, content type, document type, year, and number, and by query parameters including `event`, `format`, `language`, and `republished`.

That maps **directly** onto `sync_documents(config, since)` in [[§3.6]].1: the feed *is* the `since` source, so the incremental sync design already has the right shape. Three traps in it, though:

1. **Pagination is fixed at 20 entries per page.** Combined with a ~1–2 req/s recommended rate, catch-up throughput is bounded. Incremental sync is comfortable; initial backfill is not, and must be planned.
2. **The `published` field may be absent** for resources first published before 5 July 2023, and `Republished: false` means only "not previously published on or after 5 July 2023." **A watermark keyed on `published` will silently skip older material.** Use `updated`.
3. **Effects are only ever "published", never "withdrawn" — but a publication of changes may delete existing effects.** So an idempotent upsert-on-publish sync **leaves deleted effects behind**, and stale amendments are the worst possible defect in this domain: they produce a confidently wrong legal answer. A changes publication must be treated as a **replace-set for that item**, not an upsert. This is [[Property 35]].

**Two further shape facts that affect configuration.** Welsh legislation is **dual-language** (`en`/`cy`), with titles that can carry both languages in one XHTML element — so the corpus is multilingual and the embedding choice must cope. And CLML and Akoma Ntoso are **deeply nested**: character-count chunking severs provisions from their context, which is why chunking must follow the document's own structural boundaries ([[ADR-015]]).

**Unverified, to check before [[Phase 3]].** A [community MCP server for legislation.gov.uk](https://lobehub.com/mcp/legislation-legislation-mcp-ts) appears to exist. If it is maintained and its provenance is sound, registering it as an AgentCore Gateway target is cheaper than writing our own tools — but it must be assessed for whether it honours the fair-use rules above, since a third-party server that crawls carelessly gets **our** user agent blocked.

#### The amendment graph is published data, not something we infer

**The question this answers:** bills are amended over decades — can we build a metadata graph and have the agent traverse it, then go and read only the documents that matter?

**Yes, and the important part is that we do not have to extract it.** legislation.gov.uk publishes an **[effects](https://legislation.github.io/data-documentation/model/effects.html)** model: when a provision amends another, editors record it as a structured effect. Each effect carries:

| Field | Why it matters here |
| --- | --- |
| **Effect type** | `inserted`, `words substituted`, `repealed`, `applied`, `modified` — a typed edge, not a generic "related to" |
| **Affecting provisions** / **Affected provisions** | The edge endpoints, at **provision** level rather than whole-Act level |
| **In force dates** | An amendment may come **wholly into force once, or partly into force many times** for specific geographic extents or purposes. So the edge is not a single date — it is a set of date-and-scope pairs |
| **Commencement authority** | The provision that determines *when* it commences, which is frequently a different instrument. This is why the graph is genuinely multi-hop |
| **Savings** | Provisions that qualify the effect's meaning, usually preserving prior meaning in some contexts. An answer that ignores savings can be textually right and legally wrong |
| **Extent and territorial application** | Of the affecting *and* the affected provision, **which may differ** |
| **Applied / requires-applied status** | See the trap below. Also tracked separately for Welsh text |
| **Effect ID and URI** | `/id/effect/{id}`, with `EffectId` on `<Effect>` and `<UnappliedEffect>` elements — so every edge is individually addressable and citable |

Effects are retrievable as Atom, including pairwise: `/changes/affected/{affected}/affecting/{affecting}/data.feed`.

**The consequence for [[ADR-007]], stated sharply: where an authoritative graph exists, LLM extraction is a downgrade.** GraphRAG's entity-and-relationship extraction earns its place on corpora that have no published structure. Using it to *infer* amendment edges that the publisher already states would replace citable editorial fact with model output — in a domain where a hallucinated repeal is the worst thing the system could produce. So the platform runs **two graph layers with different provenance and different trust**:

| Layer | Source | Edges are | Used for |
| --- | --- | --- | --- |
| **Legislative graph** | Published effects data | **Authoritative.** Ingested, never inferred | Amendment chains, commencement, point-in-time reconstruction |
| **Tenant policy graph** | The tenant's internal policy corpus | **Inferred** by LLM extraction ([[ADR-007]]), because no published graph exists | Linking internal obligations to the provisions they implement |

**Ingestion strategy: lazy on first query, then stored permanently and kept fresh.** Three options were considered and the middle one wins on the rate limit alone:

| Strategy | Verdict |
| --- | --- |
| **Eager full ingest** — pull the whole effects graph up front | **Rejected.** Over 300,000 documents against a shared ~1–2 req/s recommended rate is a multi-day backfill before anything works at all, and the publisher explicitly asks to be contacted before large one-off crawls. It also front-loads work for a statute book that real questions barely touch |
| **Lazy on first query, stored permanently, kept fresh** | **Chosen.** The graph grows along the paths real questions take. Time-to-first-value is immediate, and the effects API is queryable *per affected item* (`/changes/affected/{item}/data.feed`), so inbound amendment edges for a provision are directly retrievable without having crawled whatever amended it |
| **Pure per-query fetch, nothing stored** | **Rejected.** Amendment data changes rarely and is consulted repeatedly; re-fetching it burns the shared rate budget on data that was already correct, and makes every conversation pay a latency tax the second user does not need to pay |

**What "stored permanently" must mean here, because the naive version is unsafe.** Effects can be **retracted** by a later publication ([[Property 35]]), so permanent storage without ongoing freshness is permanently *wrong* storage. Three requirements:

1. **Three-state provenance per item**, not two. Every item is `never_fetched`, `fetched_with_effects`, or `fetched_and_confirmed_empty` — with a timestamp. Collapsing the last two into "no rows" is the defect described in [[Property 36]].
2. **Feed-driven invalidation for held items.** The Publication Log `changes` feed is watched, and any entry for an item we hold triggers a replace-set refresh. Volume is low, so the whole feed can be watched and irrelevant entries discarded.
3. **A staleness bound as a backstop.** If freshness for an item has not been confirmed within a defined window, it is stale — refresh before answering, or disclose. A missed poll must not turn into silently outdated law.

**How a query then runs — stored graph, on-the-fly projection, targeted fetch:**

1. **Resolve the seed** provision from the question.
2. **Depth-limited expansion** over the stored effects graph, filtered to the as-at date and extent — producing a small subgraph of *metadata only*. A frontier node that is `never_fetched` triggers a fetch **within the shared rate budget**.
3. **If the budget or depth limit stops the traversal, the answer says so.** A truncated traversal presented as complete is the worst outcome available here ([[Property 36]]).
4. **Fetch text for just the provisions the traversal identified**, at their point-in-time URIs, offloading each to T1 with a `Reference` ([[P4]]).
5. Answer from those, citing version-pinned URIs and the effect IDs relied on.

The ordering is what makes 10,000-page documents tractable: **the agent never scans documents to discover amendments** — it traverses cheap metadata to decide which few documents are worth reading. Large payloads are pulled deliberately and narrowly, not speculatively.

**The cost of choosing lazy, stated plainly.** Coverage becomes a function of query history rather than a known quantity, so "have we got everything about this Act" has no answer from the schema alone — it has to be asked of the provenance records. That is the price of not doing a multi-day backfill, and [[Property 36]] is what stops it becoming a correctness problem rather than merely an operational one.

**Prior art — the answer to "has anyone proved this".** Yes, and on all three of the pieces this design depends on:

- **The pattern of a depth-limited subgraph around a seed Act is published and validated.** [Computational and Graph-Theoretic Analysis of Legislative Networks](https://www.mdpi.com/2078-2489/17/2/161/xml) builds focal legislative citation networks using exactly this depth-limited expansion, and reports a reason for it we would not otherwise have anticipated: it **avoids the global hub dominance** that swamps whole-corpus analysis. Widely-referenced Acts otherwise drown the signal, so seed-and-expand is not just cheaper, it is more informative.
- **Graph RAG adapted to legal norms with temporal versioning is an established approach.** [Graph RAG for Legal Norms: A Hierarchical, Temporal and Deterministic Approach](https://arxiv.org/abs/2505.00039) targets precisely this problem — hierarchical structure, dense cross-references, and continuous evolution through temporal versions — and concludes that the temporal dynamism **demands a deterministic representation of the law at a given point in time**. That is an independent statement of [[Property 34]].
- **Point-in-time reconstruction from an event-centric amendment graph has been demonstrated end to end.** [An LRMoo-Based, Component-Level, Event-Centric Approach to Legal Knowledge Graphs](https://arxiv.org/html/2506.07853) formalizes amendments as events and demonstrates **exact reconstruction of any part of a legal text as it existed on a specific date**, using the Brazilian Constitution.
- Broader network-analytic work over statutes across time and jurisdictions ([Measuring Law Over Time](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2021.658463/full)) and large-scale automatic citation-graph extraction at the scale of hundreds of millions of documents ([Ukrainian court decisions](https://arxiv.org/html/2605.15362v1)) establish that both the modelling and the scale are tractable.

> Sources were paraphrased; content was rephrased for compliance with licensing restrictions.

**The trap that this research does not save us from, and it is the sharpest one in the whole use case.** An effect carries an **"applied" / "requires applied"** status — meaning **an amendment can be in force but not yet applied to the published text**, which is why `<UnappliedEffect>` exists as a distinct element. Two consequences:

1. **The point-in-time text is not guaranteed to be the law as at that date.** Fetching `/2021-03-01/data.xml` gives the text as editorially revised, which may omit in-force amendments still awaiting application.
2. **Therefore a version-pinned citation is necessary but not sufficient.** An answer must also disclose outstanding unapplied effects for the provisions it relied on. Silence here produces the exact failure this domain punishes hardest: a fluent, correctly-cited, version-pinned answer that is nonetheless not the current law. This is clause 4 of [[Property 34]].

Also note that the effects data deliberately **does not contain the amending text**, nor machine-readable instructions for applying it — it links to the amending provision so that a human can work it out. So the graph is for **navigation and disclosure**, never for synthesising amended text ourselves. Reconstructing provision text by applying effects with a model would be inventing law, and it is out of scope by design.

#### Actors and the permission matrix

The read/act asymmetry is the load-bearing part. Cognito groups map to `UserPrincipal.roles`, which resolve to `data_scopes` in the tenant policy bundle ([[ADR-020]]).

| User | Cognito group | Read cost data | Act on resources | Proves |
| --- | --- | --- | --- | --- |
| `alice.finops` | `finops-analyst` | **All** linked accounts | **Nothing** — read-only by role | [[Property 32]] clause 3 in its most realistic form: the agent holds the remediation tool, this user does not hold the scope. Broad read plus zero write is the single most common real enterprise shape |
| `bob.owner` | `platform-owner` | Only their own accounts | Yes, **with approval**, within a cost ceiling | Happy path, and the approval gate on a financially committing action |
| `carol.other-tenant` | `tenant-b-analyst` | Only tenant B | No | [[Property 1]] with a genuinely valid token |
| `svc.nightly` | `service-principal` | Read only | No | [[Property 32]] clause 2 — no human behind the turn, explicit service principal rather than a null |

Note that `alice` has **wider read access and less write access** than `bob`. Access is not a single scalar level, so an implementation that collapses roles into a rank will pass a naive test and fail this one.

#### Tool inventory — real third-party systems, not stand-ins

**No stubbed services and no invented domain model.** The tools call real third-party APIs over the network, against accounts we own. This is a stronger choice than a seeded local database, and the reason is not idealism: a local stand-in cannot produce OAuth token expiry, real rate-limit responses, cursor pagination, provider-specific error taxonomies, idempotency semantics, partial failures, or latency variance — and those are the conditions the circuit breakers ([[ADR-003]]), retry scoping ([[§2.13]]), and the secrets resolver seam ([[ADR-019]]) exist to handle. Building against a stand-in means designing against conditions that do not occur.

| Tool | Real system behind it | Kind |
| --- | --- | --- |
| `billing_get_subscription` | **Stripe** — `Customer`, `Subscription`, `Price`, `Product` | Read |
| `billing_list_entitlements` | **Stripe** — [Active Entitlements API](https://docs.stripe.com/billing/entitlements) | Read |
| `entitlement_set_feature` | **Stripe** — attach/detach a [`product_feature`](https://docs.stripe.com/api/product-feature/attach) | **Write**, approval-gated |
| `ticket_get` / `ticket_add_note` | **A real issue tracker** (GitHub Issues, or Jira Service Management) | Read / Write |
| `search_policy` | Our corpus, ingested from **real published vendor pricing, plan, and terms pages** | Read |

**Stripe Billing Entitlements is not an analogue of this use case — it *is* this use case.** Features are created in Stripe, attached to products, and a customer subscribing to a product is entitled to that product's features. So "does this customer's plan include CSV export?" is a real API question with a real answer, and "enable it" is a real mutation. The domain model does not have to be invented, which also means we are not designing against a model of our own construction that flatters our assumptions.

Stripe **test mode is the real API** — same endpoints, same objects, same error semantics, same idempotency behaviour, with `sk_test_` credentials. That is the right level of real: genuine integration surface, no real money moving.

`entitlement_set_feature` must genuinely mutate the Stripe account. If the write is a no-op, neither the approval gate nor the Tier-1 denial proves anything — the test would pass against a system that silently does nothing.

#### Data provenance: what is real, and the one thing that cannot be

Being precise about this matters, because "use real data" and "use real systems" are different requests and only one of them is fully satisfiable.

| Layer | Provenance | Real? |
| --- | --- | --- |
| **APIs and integration surface** | Live Stripe and a live issue tracker, over the network, with real credentials | **Real** |
| **Plan and policy documents** | Real published pricing, plan-comparison, and terms pages from actual SaaS vendors, ingested through the real sync pipeline | **Real** — and genuinely ambiguous, which is the point |
| **Ticket text** | Real user-written issues from public trackers | **Real** — real typos, real wrong terminology, real multi-question tickets |
| **Customer and subscription records** | Created by us, in **our own** real Stripe account | Real objects in a real system; the *businesses* they describe are ours |

**The one thing that cannot be real is another company's customer list**, and that is a legal and privacy limit rather than a technical one. We have no tenant yet, so there is no production customer data we are entitled to hold — and [[ADR-009]]'s binding precondition forbids regulated PII in the platform before [[Phase 6]] regardless. Anyone reading this as a shortcut should note that using a real business's customer records here would be the single fastest way to turn a design decision into a compliance incident.

**Why real published policy documents matter more than the account records.** The hardest part of this use case is not looking up a subscription — it is deciding what a plan document actually entitles a customer to. Real pricing pages hedge, use inconsistent feature names between the comparison table and the terms, and leave cases genuinely uncovered. That ambiguity is what makes the `ask` exit necessary rather than decorative, and it is exactly what an invented policy document would have smoothed away.

**The account records still need specific shapes**, and they are created in Stripe rather than seeded into a table:

| Shape to create in Stripe | Exists to test |
| --- | --- |
| Customer on a product **with** the feature attached, provisioning not reflected | The in-plan defect path — enable it |
| Customer on a product **without** the feature | The upgrade path — do not enable, explain |
| Customer whose eligibility turns on **the policy document, not the API** | The conditional path |
| A case the published policy leaves **genuinely uncovered** | The `ask` exit |
| Two tenants with **different product catalogs and different vendor policy wording** | Tenant isolation, and why plan normalization cannot be hardcoded |
| A customer with a long subscription and invoice history | Offload to T1 and reference-based context ([[P4]]) |

Contact details on these customers are synthetic (`example.com`) — real systems do not require real people.

#### The cost of real integrations, and how CI survives it

This is the honest tradeoff, and it needs a decision rather than discovery:

- **Evals become network-dependent and non-deterministic.** Running every pull request against live Stripe and a live tracker makes CI slow, flaky, dependent on third-party uptime, and rate-limited.
- **The resolution: record once, replay in CI, and run live on a schedule.** Real interactions are captured and replayed deterministically in the per-PR gates; a scheduled job runs the same suite against the live APIs and fails loudly when reality has drifted from the recordings.
- **A recorded real response is not a mock**, and the distinction is worth holding onto: a mock encodes what we *assumed* the API returns, while a recording contains what it *did* return, including the fields and error shapes we did not anticipate. But recordings do go stale, which is precisely what the scheduled live run exists to catch — without it, replay quietly becomes a mock with extra steps.
- **Secrets, rate limits, and egress allowlists become real on day one.** This is a benefit rather than a cost: the secrets resolver seam, the per-pool egress allowlist, and the circuit breakers get exercised from the first feature instead of being designed on paper and validated after the cloud move.

#### The first skill

`entitlement_discrepancy_triage` — the first capability added to the platform, and it is added **as a skill, with no platform code**:

> Read the ticket. Identify the customer and the feature in question; if either is ambiguous, **ask**. Look up the subscription and current entitlements. Retrieve the plan policy for that plan. Decide between: in-plan defect, requires upgrade, trial-eligible, or out of scope for entitlement triage. State the policy clause relied upon. If a change is warranted and permitted, propose it for approval. Write a resolution note recording plan, entitlement state, decision, and the clause.

Deterministic sub-steps belong in a **Level-3 script** rather than prose — comparing an entitlement list against a plan's feature list is exact work, and a script does it at zero context cost and cannot be half-followed by a model.

#### Eval cases — the definition of done

These are the skill's own eval cases, and it cannot be promoted without passing them ([[ADR-002b]], [[§5.5]]):

1. **Correct classification** across all four decision paths.
2. **Groundedness** — the cited clause actually supports the decision. A confident answer citing an unrelated clause is a failure, not a partial credit.
3. **Tier-1 denial** — `bob.narrow` triggers no entitlement write, and the denial arrives from the gateway rather than from the model declining.
4. **Approval enforced** — `alice.broad`'s billing-relevant change suspends for approval and applies **only** after it, with the database unchanged in the interim.
5. **Ambiguity is asked about, not guessed at** — the silent-policy fixture produces a question.
6. **Cross-tenant containment** — `carol.other-tenant` cannot read tenant A, with a valid token.
7. **Resolution note completeness** — plan, entitlement state, decision, clause. Deterministically checkable.

#### What this use case does not cover

Recorded because the gap should not be discovered later. Support tickets are **short**, so this scenario leaves the long-horizon machinery — full compaction tiers, the pre-compaction memory flush, silent turns, sub-graph delegation — **largely unexercised**. It also does not stress multi-hop graph traversal, since policy lookup is mostly single-hop.

That is an argument for a **second** use case, not against this one. A **quarterly account review** — one task spanning dozens of customers, accumulating findings — is the natural counterpart and would exercise exactly what this misses. The short case goes first because [[Phase 1]]'s purpose is a complete vertical slice through every layer, and a short task reaches the end of the slice soonest. The honest consequence: the compaction design in [[ADR-006]] remains a hypothesis for longer than the rest of the platform, which [[§7.11]] already records as the cost of deferred validation.
---
