---
title: "3.9 Data Source Contract: legislation.gov.uk Endpoints, Responses, and Storage"
type: section
tags: [section, retrieval, storage]
aliases: ["§3.9"]
source: .kiro/specs/enterprise-agent-framework/design.md
generated: 2026-08-03T21:21:18+00:00
---

# 3.9 Data Source Contract: legislation.gov.uk Endpoints, Responses, and Storage

Part of [[3-low-level-architecture|3. Low-Level Architecture]].

The concrete integration contract for the anchor use case. Everything here is drawn from the [official data documentation](https://legislation.github.io/data-documentation/); nothing is assumed.

#### 3.9.1 Endpoint inventory

Base: `https://www.legislation.gov.uk`. Format is chosen by suffix, so **all of these are one URI space with a format subresource** — content negotiation via `Accept` also works, but explicit suffixes are used so that requests are self-describing in logs.

| # | Purpose | URI template | Returns | Payload size |
| --- | --- | --- | --- | --- |
| 1 | **Resolve an identifier** | `/id?title={t}&type={ty}&year={y}&number={n}` | **`301`** to the canonical URI if unique; **`300 Multiple Choices`** with an XHTML `<ul>` of candidates if not | Tiny |
| 2 | **Table of contents** | `/{type}/{year}/{number}/contents/data.xml` | `<Contents>` tree of provision IDs | Small–medium |
| 3 | **ToC with text-match flags** | ToC URI carrying the `text=` parameter, `/data.xml` inserted before `?` | ToC where matching provisions carry `MatchText="true"`, and `<Contents>` carries `MatchTextEntries` — a space-separated list of matching provision IDs plus pseudo-IDs `note`, `signature`, `earlier-orders`, `introduction`, `schedules` | Small |
| 4 | **Whole item, point in time** | `/{type}/{year}/{number}[/{extent}]/{yyyy-mm-dd}/data.xml` | CLML XML | **Massive** — up to 10,000+ pages |
| 5 | **Single provision, point in time** | `/{type}/{year}/{number}/section/{n}/{yyyy-mm-dd}/data.xml` | CLML fragment | Small–medium |
| 6 | **Named document parts** | `…/introduction`, `…/note`, `…/signature`, `…/schedules`, `…/earlier-orders` | The corresponding CLML element | Varies; `schedules` is often huge |
| 7 | **Effects (the graph)** | `/changes[/affected/{ty}/{y}/{n}][/affecting/{ty}/{y}/{n}]/data.feed` | Atom; each `<entry>` carries a `<ukm:Effect>` | Small per page |
| 8 | **Listings / search** | `/{type}/{year}/{range}/data.feed?title=&text=&extent=&version=&sort=` | Atom list | Small per page |
| 9 | **Publication log (watermark)** | `/update[/{date}][/{content-type}]/data.feed?event=&format=&republished=` | Atom, publication/withdrawal events | Small; **fixed 20/page** |
| 10 | **New legislation** | `/new[/{type}]/{yyyy-mm-dd}/data.feed` | Atom | Small |
| 11 | **Metadata graph** | `…/data.rdf` | RDF/XML | Small |

**Alternative formats on any content URI:** `data.xml` (CLML), `data.akn` (Akoma Ntoso), `data.xht` / `data.htm` (XHTML snippet), `data.html` (HTML5), `data.pdf`, `data.feed` (Atom, feeds only).

**Three behaviours to code against explicitly, because each is a trap:**

- **Prefer the list page over `/search`.** A `/search` request always **redirects** to the equivalent list page, so hitting the list page directly saves one request against a shared budget. Two forms exist for the same query — path (`/uksi+nisr/2009/1-100?title="amendment"`) and query string (`/search?type=uksi&type=nisr&…`).
- **Default sort differs between HTML and Atom.** Atom defaults to `modified` descending, HTML to "basic". **Always specify `sort` explicitly** — an unspecified sort is a silent behaviour difference between what a developer sees in a browser and what the code receives.
- **Search applies stemming.** `dogs` matches `dog`, `protect` matches `protected`. Boolean `AND`/`OR` **must be capitalised** or they are treated as ordinary words. This shapes eval expectations: a text search is not a substring match, and tests written as though it were will fail for the wrong reason.

**`300 Multiple Choices` is a deterministic ambiguity signal, and that is worth exploiting.** When a title resolves to several items, the API says so with a status code and a candidate list. That means the **`ask` exit can be triggered by a fact rather than by model judgement** — the agent asks which Companies Act because the upstream told us there are several, not because it felt uncertain. Deterministic ambiguity detection is far more reliable than asking a model to introspect on its own confidence, and it is available for free here.

#### 3.9.2 The `<ukm:Effect>` payload — the fields we extract

Each effect entry carries the following, and every one of them is load-bearing for [[Property 34]] or [[Property 36]]:

| Field | Extracted as | Why |
| --- | --- | --- |
| Affected item + provision(s) | Edge target | Provision-level, not item-level |
| Affecting item + provision(s) | Edge source | |
| Items commenced in full or part | Commencement edges | |
| Effect type | Edge label — `words substituted`, `repealed`, `restricted`, `inserted`, `modified`, `applied` | Typed edges |
| In-force date(s) | **A set** of `(date, extent, purpose)` — not one date | An amendment may commence partly, repeatedly, per extent |
| Commencement authority | Edge to the provision that decides commencement | The multi-hop driver |
| Extent + territorial application | On **both** affecting and affected sides, which may differ | Wrong-extent answers are wrong answers |
| Applied / will-be-applied | Boolean pair | **[[Property 34]] clause 4** — unapplied in-force effects |
| Savings | Edges to qualifying provisions | Textually right, legally wrong without these |
| `EffectId` | Stable citation key, also `/id/effect/{id}` | Every edge is individually citable |

#### 3.9.3 What is stored, and where — one home per fact

The rule is **no fact has two systems of record**. Duplication across stores is how a graph and a table start disagreeing.

| Store | Holds | Key | Why here |
| --- | --- | --- | --- |
| **Neo4j** | **System of record for the effects graph.** `(:Item)`, `(:Provision)`, `(:Effect)` nodes; `AFFECTS`, `COMMENCED_BY`, `QUALIFIED_BY` edges with type, in-force set, extent, applied flags | Provision URI | Depth-limited traversal is the primary query and it is a graph query. Cypher in both environments ([[§4.1]].1) |
| **Postgres** | Item and version metadata; **fetch provenance (the three-state table for [[Property 36]])**; feed watermarks; the obligation register | Item URI, resource URI | Relational, transactional, and the provenance table needs constraints rather than convention |
| **pgvector** | **(a)** The tenant policy corpus — the primary and unambiguous case. **(b)** Provisions **already held**, for semantic recall within them | `(item_uri, provision_path, version_date)`; tenant-partitioned | Retrieval. **Chunked on provision boundaries, never character counts** — CLML nesting makes character chunking destroy meaning ([[ADR-015]]) |
| **Object store (T1)** | Raw CLML/AKN per `(item, version)`, content-addressed and immutable | Content digest | The offload target. A tool returns a `Reference` to this, never the bytes ([[P4]], [[Property 9]]) |
| **Redis** | **The shared upstream rate budget**; session manifests; negative-cache timers | Global budget key; session key | The 3,000-per-5-minutes limit is **per user, not per IP**, so the bucket must be central. A per-replica limiter is non-compliant by construction |

**The provenance table is the one that carries a correctness property, so its shape is specified rather than left to implementation:**

```pascal
STRUCTURE FetchProvenance                 // Postgres; enforces Property 36
  resource_uri: String                    // PRIMARY KEY — the exact URI fetched
  state: Enum{NEVER_FETCHED,              // implied by absence OR an explicit row
              FETCHED_WITH_RESULTS,
              FETCHED_CONFIRMED_EMPTY}    // "we asked; there is genuinely nothing"
  fetched_at: Timestamp?
  freshness_confirmed_at: Timestamp?      // last time the feed or a re-fetch confirmed it
  upstream_etag: String?                  // conditional requests save budget
  result_count: Integer?                  // 0 with FETCHED_CONFIRMED_EMPTY is meaningful
END STRUCTURE
```

`FETCHED_CONFIRMED_EMPTY` with `result_count = 0` is what licenses the sentence *"this provision has not been amended"*. Absence of a row licenses only *"we have not checked"*. Collapsing those two into an empty result set is the defect [[Property 36]] exists to prevent.

**Three question shapes, three mechanisms — and vectors own only one of them.** Recorded because conflating them is the most likely way this retrieval design gets built wrong:

| Question shape | Mechanism | Why not the others |
| --- | --- | --- |
| *"Which provisions contain the word `auditor`?"* | **Upstream `text=` search** (endpoint 3) — lexical, stemmed, authoritative, complete | Embeddings are weak at exact terms and identifiers. If the requirement is the word, match the word |
| *"What does our policy say about director liability?"* | **pgvector** — semantic similarity | No lexical overlap exists between how a user phrases a duty and how a policy document words it |
| *"What amended s.172, when, and is it in force?"* | **Neo4j effects graph** | Not a text question at all — a typed traversal with dates and extents |

**Discovery over public legislation goes upstream, not through our vector index**, and this is a deliberate constraint rather than an omission. Two reasons: upstream search is **complete and authoritative** while ours is **partial by construction** under lazy ingestion (§ anchor use case), so semantic search over our own copy would silently miss anything not yet fetched — reintroducing the [[Property 36]] failure through the retrieval path instead of the graph path. And upstream search costs one request against the rate budget rather than a full crawl to populate an index.

Our vector index therefore serves **semantic recall within material already held**, plus the tenant corpus, where no upstream search exists and indexing it ourselves is the only option.

**Why pgvector rather than a dedicated vector store.** The deciding argument is **filtered search in a single query**: retrieval here always carries hard predicates — `tenant_id`, `version_date`, `extent` — and in Postgres those are joins against the metadata tables in the same statement. A separate vector store forces either duplicating those predicates as synced metadata, or a fetch-top-K-then-filter pattern that can legitimately return nothing usable because the nearest twenty chunks were all the wrong tenant or the wrong version. Secondary arguments: a chunk and its provenance row **commit in one transaction**, and standard Postgres plus pgvector is **identical local and managed** ([[P16]]), whereas a managed-only vector service is a migration cliff needing its own ADR. The honest limit: pgvector concedes to dedicated engines above roughly tens of millions of vectors at high query rates, and HNSW index builds are slow and memory-hungry at that size — neither of which our lazily-populated corpus approaches.

#### 3.9.4 The tool surface — eight tools, prefix-masked ([[P3]])

| Tool | Endpoints used | Returns | Upstream cost |
| --- | --- | --- | --- |
| `leg_resolve_identifier` | 1 | Canonical URI, **or `AMBIGUOUS` with candidates** | 1 |
| `leg_search` | 8 | Compact result list + next-page cursor | 1/page |
| `leg_get_contents` | 2, 3 | Provision tree; with `text=`, the matching provision IDs | 1 |
| `leg_get_provision` | 5, 6 | Compact extract **plus a `Reference`** to the offloaded CLML | 1 |
| `leg_get_item` | 4 | **`Reference` only** — never inlined | 1 (large) |
| `leg_list_effects` | 7 | Effect edges as structured metadata | 1/page |
| `leg_traverse_amendments` | Neo4j + 7 on cache miss | Query-scoped subgraph **plus a completeness flag** | 0–N |
| `policy_search` | Internal corpus | Tenant-scoped chunks | 0 |

Plus `obligation_register_add` — the approval-gated write ([[§2.4]]), which touches no upstream API.

**`leg_get_contents` with a text match is the tool that makes this use case affordable**, and it deserves calling out. It returns *which provisions match* without downloading the item. So the sequence is: search → contents-with-match → fetch only the matching provisions. **The agent never downloads a 10,000-page Act to find out which three sections are relevant.** That is the same "cheap metadata first, targeted large fetch second" discipline as the amendment traversal, applied to text search.

#### 3.9.5 Rate budget as a first-class resource

The ceiling is 3,000 requests per 5 minutes **for the whole platform across all tenants**, with a recommended working rate closer to 1–2 requests per second. Consequences already recorded in the anchor use case, restated here as implementation requirements:

- A **central token bucket in Redis**, not per-replica.
- **Per-tenant fair-share** allocation under the global ceiling, so one tenant's deep traversal cannot starve others.
- **Conditional requests** using stored `upstream_etag` — a `304` costs a request but no parsing, and re-fetching unchanged effects is the most avoidable waste available.
- A **mandatory identifying `User-Agent`** with contact details, asserted at service startup. Failing startup is correct: an anonymous agent gets the platform blocked, so booting without it is worse than not booting.
- When the budget is exhausted, tools return a structured `RATE_BUDGET_EXHAUSTED` error and the agent **discloses a partial answer** ([[Property 36]] clause 4) rather than answering from whatever is cached.

---
