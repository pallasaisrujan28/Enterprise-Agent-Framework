"""The architecture, as data — shape, position, and what is actually true.

WHY POSITION IS DECLARED HERE RATHER THAN COMPUTED
The first version refused to carry layout, on the principle that a hand-placed
diagram drifts from the code. One grid layout later the result was twenty-five
boxes in five columns: an inventory, not an architecture. It said what existed
and nothing about how a request moves.

A useful architecture diagram follows the flow of one request, and that flow is
a design decision rather than something derivable from a node list. So each node
declares a `col` and `row`. The anti-drift property is kept differently: the node
set, the edges and the statuses are still data, still probed, and still pinned by
tests, so a component cannot appear without a status and a reason, and an edge
cannot point at a node that no longer exists.

THE DIAGRAM SHOWS THE SHAPE, THE TABLE SHOWS THE INVENTORY. Sub-concerns that
would clutter the chart — the secrets resolver, the model proxy — live in a
node's `detail` and in the table, not as boxes of their own.

BANDS OWN DISJOINT ROW RANGES. A band is drawn as the bounding box of its
members, so two bands whose rows interleave produce overlapping rectangles and a
label struck through by someone else's boxes. That is not a styling preference;
it is what the first attempt actually did.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

# built    — implemented and exercised by a test or a verified run
# partial  — implemented but does not yet do its whole job
# missing  — declared in the design, no implementation
# broken   — implemented and verified NOT to work
Status = Literal["built", "partial", "missing", "broken"]

# How a status was arrived at. Rendered, so a green box can be distrusted when
# nothing actually checked it.
Evidence = Literal["probed", "claimed"]

Shape = Literal["box", "diamond"]


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    # One short line under the label, inside the box. A few words.
    caption: str
    group: str
    col: int
    row: int
    status: Status
    # The full truth, for the table and the click panel. Not length-limited.
    detail: str
    shape: Shape = "box"
    # A heavier border. Reserved for the loop, which is what every reader looks
    # for first.
    emphasis: bool = False
    evidence: Evidence = "claimed"
    probe_import: str | None = None
    probe_env: str | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    # Rendered on the line. An unlabelled arrow makes the reader guess.
    label: str = ""
    kind: Literal["solid", "dashed"] = "solid"


@dataclass(frozen=True)
class Band:
    """A dashed container drawn around every node that names it."""

    id: str
    label: str
    note: str = ""


BANDS: tuple[Band, ...] = (
    Band("harness", "HARNESS", "the turn inside is ephemeral"),
    Band("tooling", "TOOL PATH", "how a tool is chosen, narrowed, then run"),
    Band("memory", "MEMORY", "what survives the turn"),
    Band("ops", "EVAL / OPS", "the offline improvement loop"),
)

# col/row are grid slots, not pixels. The renderer owns spacing.
NODES: tuple[Node, ...] = (
    # ── HARNESS, rows 0-1: the request flow, left to right ─────────────────────
    Node(
        "channel",
        "Channel",
        "cli · web",
        "harness",
        0,
        0,
        "partial",
        "This dashboard and `agent dashboard` exist. No chat endpoint yet "
        "(KAN-9) and no API for real traffic. A channel must only move text — it "
        "never touches memory, so adding one cannot break recall.",
        evidence="probed",
    ),
    Node(
        "working",
        "Working memory",
        "assembled per turn",
        "harness",
        1,
        0,
        "partial",
        "Rebuilt from scratch every turn: persona, the time, memory context and "
        "chat history. The bounded history window is not implemented, so context "
        "grows with the conversation instead of staying flat.",
    ),
    Node(
        "agent",
        "LLM agent",
        "reason",
        "harness",
        2,
        0,
        "partial",
        "gpt-oss-120b on Bedrock, verified invocable. Not yet behind the model "
        "proxy seam (KAN-11), and credentials are read straight from the "
        "environment rather than through a resolver (KAN-10).",
        emphasis=True,
        probe_import="boto3",
    ),
    Node(
        "obligation",
        "Obligation gate",
        "fails closed",
        "harness",
        3,
        0,
        "built",
        "agent/gate.py. Runs OUTSIDE the model, so the model cannot reason its "
        "way to a pass or be talked past it. Fails closed. Observe-mode "
        "violations record without blocking, so an obligation can be tuned "
        "against real traffic before it enforces. It checks the Draft's fields — "
        "including which tools were called — rather than substring-matching "
        "prose.",
        evidence="probed",
        probe_import="agent.gate",
    ),
    Node(
        "reply",
        "Reply",
        "back to you",
        "harness",
        4,
        0,
        "partial",
        "Returned to whatever called it. No streaming, and no single respond() "
        "function owns a turn — so there is nowhere for tracing, consolidation "
        "or the retrieval gate to hang.",
    ),
    Node(
        "retrieval",
        "Retrieval gate",
        "MISSING · always on",
        "harness",
        1,
        1,
        "missing",
        "Memory is injected on EVERY turn unconditionally. That costs latency "
        "and biases answers with facts the turn never needed. A cheap-model "
        "judge breaks even above a 4% skip rate. Its decision must be traced: we "
        "watched waku's gate fail open on a 403 and report 'retrieve', spending "
        "1742 tokens to answer 17x3. KAN-16.",
        shape="diamond",
    ),
    Node(
        "tools",
        "Tool surface",
        "what the model sees",
        "harness",
        2,
        1,
        "partial",
        "The schemas actually put in front of the model this turn. web_search "
        "via self-hosted SearXNG and web_fetch via trafilatura both work and "
        "need no API key.",
        emphasis=True,
    ),
    # ── TOOL PATH, rows 2-3 ────────────────────────────────────────────────────
    # Its own lane because "which tools does the model even see, and where does
    # the call run" is decided three times over and was invisible on the chart.
    Node(
        "tool_declared",
        "Declared tools",
        "skill names them",
        "tooling",
        0,
        2,
        "built",
        "A skill names the tools its procedure needs. Three jobs: every name "
        "must resolve in the pinned catalog, so a skill referencing a deleted "
        "tool fails at LOAD rather than mid-conversation; it cross-checks the "
        "semantic ranking, because a ranking can be wrong silently; and in "
        "`declared` mode it IS the selector, which cannot be wrong because it is "
        "a lookup. required_scopes must be a SUBSET of the agent's grants — a "
        "skill can narrow access, never widen it.",
        evidence="probed",
        probe_import="agent.skills_engine",
    ),
    Node(
        "tool_select",
        "Tool selection",
        "top-k · Titan",
        "tooling",
        1,
        2,
        "partial",
        "agent/registry.py ranks tools by embedding similarity to the task and "
        "passes only the top-k, instead of every schema. Two modes: LOCAL uses "
        "Python tool functions; GATEWAY discovers them from AgentCore Gateway's "
        "MCP ListTools at startup, so adding a tool needs no deploy and every "
        "call is audited. Gateway mode is written but unverified.",
        evidence="probed",
        probe_import="agent.registry",
    ),
    Node(
        "tool_mask",
        "Tool masking",
        "MISSING · ADR-005",
        "tooling",
        2,
        2,
        "missing",
        "ADR-005 chose masking — constraining which of a stable tool list is "
        "callable — over adding and removing tools between turns. Removing a "
        "tool mutates the prompt prefix, and prefix mutation destroys the "
        "KV-cache hit rate the whole context design is built around. Not "
        "implemented, so today the selected set simply becomes the schema list.",
    ),
    Node(
        "executor",
        "Shell / sandbox",
        "root · BROKEN",
        "tooling",
        3,
        2,
        "broken",
        "Where a tool call actually runs. Currently as root in the same pod that "
        "holds every credential — its own docstring says 'unrestricted local "
        "shell command execution'. Per-session directories separate accidents, "
        "not actors: one `cd ..` reaches another session, and the Pod Identity "
        "token, POSTGRES_PASSWORD and NEO4J_AUTH are all readable. KAN-19.",
    ),
    Node(
        "mcp",
        "MCP tool pools",
        "MISSING",
        "tooling",
        4,
        2,
        "missing",
        "ADR-003 and ADR-021 both decided tools are reached through an MCP "
        "gateway fronting ISOLATED pools — one namespace per tool domain, so a "
        "leaking tool cannot reach unrelated services. Zero MCP servers are "
        "connected. It is also the cheapest way to add capability: a server in "
        "config beats a hand-written tool function.",
    ),
    Node(
        "tool_result",
        "Result",
        "text, not an exception",
        "tooling",
        2,
        3,
        "partial",
        "What the model observes. A failing tool should come back as text it can "
        "read and retry — 'Error running X: ...' — not as an exception that ends "
        "the turn. Ours still raise. LangGraph ships ToolErrorMiddleware and we "
        "have not wired it.",
    ),
    # ── MEMORY, rows 4-5: four pillars ────────────────────────────────────────
    Node(
        "procedural",
        "Procedural",
        "skills",
        "memory",
        0,
        4,
        "partial",
        "skills_engine loads and validates skill files, refusing any whose "
        "obligations cannot be enforced. Progressive disclosure is designed — "
        "the index line is always resident, the body only on trigger. Never "
        "observed firing in a real run.",
        evidence="probed",
        probe_import="agent.skills_engine",
    ),
    Node(
        "semantic",
        "Semantic",
        "facts · Graphiti",
        "memory",
        1,
        4,
        "broken",
        "Graphiti on Neo4j. Grows correctly: 7 entities and 6 facts from 3 "
        "sentences. Self-correction fired in only 3 of 6 runs — and recall does "
        "NOT exclude expired facts, so a retracted fact still reaches the model. "
        "The generated Cypher returns valid_at, invalid_at and expired_at and "
        "filters on none of them. KAN-15.",
        probe_import="graphiti_core",
    ),
    Node(
        "episodic",
        "Episodic",
        "episodes · summaries",
        "memory",
        2,
        4,
        "built",
        "Graphiti episodes plus generated community summaries. The summaries "
        "were the most accurate part of the whole test — it fused four episodes "
        "including a contradiction correctly.",
        probe_import="graphiti_core",
    ),
    Node(
        "doc",
        "Self-editing doc",
        "AGENTS.md",
        "memory",
        3,
        4,
        "built",
        "The agent writes it, Postgres persists it, and a fresh session with no "
        "shared history recalled it with ZERO tool calls. The one thing we have "
        "that waku does not attempt.",
    ),
    Node(
        "consolidation",
        "Consolidation",
        "MISSING · nothing distils",
        "memory",
        1,
        5,
        "missing",
        "No batched pass, so either every exchange is written or none is. "
        "Batching every N exchanges gives a summariser enough context to be "
        "worth running, and it should fail SAFE — leave the log unconsolidated "
        "rather than write a bad summary into durable memory.",
    ),
    # ── EVAL / OPS, rows 6-7 ──────────────────────────────────────────────────
    # Along the bottom rather than as a sixth column: as a column it ran off the
    # right edge of the card and was simply invisible.
    #
    # Trace and the ledger are STACKED rather than in line with eval. Four boxes
    # in a row meant the trace->eval arrow had to hop over the ledger, which
    # reads as a connection to the box it passes. Stacked, they are what they
    # actually are: two independent records feeding one scorer.
    Node(
        "trace",
        "Trace",
        "MISSING",
        "ops",
        0,
        6,
        "missing",
        "One record per turn, carrying gate decisions, tool calls and timings. "
        "The Postgres checkpointer already holds most of one and has never been "
        "read. KAN-17.",
    ),
    Node(
        "ledger",
        "Usage ledger",
        "MISSING",
        "ops",
        0,
        7,
        "missing",
        "One append per model call, tokens as ground truth and cost derived. "
        "Total spend on this project is unknown, which is why 'did gpt-oss beat "
        "Nova' is unanswerable. KAN-17.",
    ),
    Node(
        "evals",
        "Eval",
        "deterministic + judge",
        "ops",
        1,
        6,
        "missing",
        "Two suites that never mix: deterministic asks 'did the right tool fire' "
        "and scores 0 or 1; the judge asks 'was the answer good' and scores a "
        "percentage. Neither exists.",
    ),
    Node(
        "release",
        "Release gate",
        "MISSING",
        "ops",
        2,
        6,
        "missing",
        "100% of deterministic plus a threshold on the judge. Requires both suites first.",
    ),
)

EDGES: tuple[Edge, ...] = (
    # the request
    Edge("channel", "working", "one message"),
    Edge("working", "agent"),
    Edge("agent", "obligation", "draft"),
    Edge("obligation", "reply", "pass or refuse"),
    Edge("reply", "channel", "same channel", "dashed"),
    # how a tool gets picked
    Edge("working", "tool_select", "the task", "dashed"),
    Edge("procedural", "tool_declared", "from the skill", "dashed"),
    Edge("tool_declared", "tool_select", "cross-check"),
    Edge("tool_select", "tool_mask", "top-k"),
    Edge("tool_mask", "tools", "callable set"),
    # how it gets executed
    Edge("agent", "tools", "emits a call"),
    Edge("tools", "executor", "run it"),
    Edge("executor", "mcp", "should route", "dashed"),
    Edge("executor", "tool_result"),
    Edge("tool_result", "agent", "observe"),
    # memory
    Edge("working", "retrieval", "every turn", "dashed"),
    Edge("retrieval", "semantic", "only if needed", "dashed"),
    Edge("retrieval", "episodic", "only if needed", "dashed"),
    Edge("retrieval", "doc", "only if needed", "dashed"),
    Edge("retrieval", "procedural", "on match", "dashed"),
    Edge("reply", "consolidation", "save the exchange", "dashed"),
    Edge("consolidation", "semantic", "distil"),
    # ops
    Edge("reply", "trace", "each turn", "dashed"),
    Edge("agent", "ledger", "each call", "dashed"),
    Edge("trace", "evals"),
    Edge("ledger", "evals"),
    Edge("evals", "release"),
    Edge("release", "working", "improved prompt", "dashed"),
)


def _probe(node: Node) -> tuple[Status, Evidence]:
    """Check a node's claim where checking is possible.

    Only ever DOWNGRADES. A node claiming "built" whose dependency is missing
    becomes "missing"; a node claiming "missing" is never promoted, because the
    presence of a library says nothing about whether we wired it up.
    """
    if node.probe_import is None and node.probe_env is None:
        return node.status, node.evidence

    if node.probe_import is not None:
        try:
            found = importlib.util.find_spec(node.probe_import) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            return "missing", "probed"

    if node.probe_env is not None and not os.environ.get(node.probe_env):
        return "missing", "probed"

    return node.status, "probed"


def counts(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Headline numbers. Honest arithmetic, not a score."""
    tally: dict[str, int] = {"built": 0, "partial": 0, "missing": 0, "broken": 0}
    for node in nodes:
        tally[node["status"]] = tally.get(node["status"], 0) + 1
    return tally


def describe() -> dict[str, Any]:
    """The payload the dashboard renders. Pinned by test/test_topology.py."""
    nodes: list[dict[str, Any]] = []
    for node in NODES:
        status, evidence = _probe(node)
        payload = asdict(node)
        payload.pop("probe_import")
        payload.pop("probe_env")
        payload["status"] = status
        payload["evidence"] = evidence
        nodes.append(payload)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "bands": [asdict(band) for band in BANDS],
        "nodes": nodes,
        "edges": [asdict(edge) for edge in EDGES],
        "counts": counts(nodes),
    }
