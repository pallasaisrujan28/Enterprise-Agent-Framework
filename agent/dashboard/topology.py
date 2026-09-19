"""The architecture, as data — so the diagram cannot lie about what exists.

A hand-drawn architecture picture is wrong the first time anything changes, and
nobody notices because a picture has no tests. So the shape is declared here, in
one place, and the dashboard renders whatever this module returns.

The shape is DECLARED; the status is PROBED. That split is deliberate and it is
the honest limit of this approach. We cannot introspect a component that has not
been written, so `Node.status` is not inferred from the code — it is a claim,
checked at runtime wherever a check is actually possible (can this package be
imported, is this connection string configured). Where no check is possible the
status is stated as a claim and labelled as one.

The alternative — a status field with no probe at all — is how a diagram ends up
showing five green boxes for components that were deleted a month ago.
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

# How a status was arrived at. Rendered in the UI so a green box can be
# distrusted when nothing checked it.
Evidence = Literal["probed", "claimed"]


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    group: str
    status: Status
    detail: str
    evidence: Evidence = "claimed"
    # The import that, if present, means this component's dependency is installed.
    # Nodes with one get status "missing" automatically when it is absent.
    probe_import: str | None = None
    # An environment variable that must be set for this component to be reachable.
    probe_env: str | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    label: str = ""
    # solid   — a call that happens on every relevant turn
    # dashed  — conditional, or an observation path
    kind: Literal["solid", "dashed"] = "solid"


@dataclass(frozen=True)
class Group:
    id: str
    label: str
    note: str = ""


GROUPS: tuple[Group, ...] = (
    Group("channel", "CHANNEL", "moves text, touches nothing else"),
    Group("orchestrator", "ORCHESTRATOR", "holds memory, judgement and credentials"),
    Group("memory", "MEMORY", "what survives a turn"),
    Group("executor", "EXECUTOR", "holds tools, holds no secrets"),
    Group("ops", "EVAL / OPS", "nothing is measurable without this"),
)

# Reasons recorded inline rather than in a design document, because a status that
# outlives its justification is how the previous diagrams went stale.
NODES: tuple[Node, ...] = (
    # ── channel ────────────────────────────────────────────────────────────────
    Node(
        "http",
        "HTTP API",
        "channel",
        "partial",
        "This dashboard serves /api/topology. No chat endpoint yet (KAN-9).",
        evidence="probed",
    ),
    Node(
        "webui",
        "Web UI",
        "channel",
        "partial",
        "Overview renders. Chat view is not implemented.",
        evidence="probed",
    ),
    Node(
        "cli",
        "CLI",
        "channel",
        "partial",
        "`agent dashboard` works. No interactive chat loop yet.",
        evidence="probed",
    ),
    # ── orchestrator ───────────────────────────────────────────────────────────
    Node(
        "respond",
        "respond()",
        "orchestrator",
        "missing",
        "No single function owns a turn yet. KAN-14.",
    ),
    Node(
        "loop",
        "Agent loop",
        "orchestrator",
        "partial",
        "deepagents drives it in the lab prototype; not yet migrated here. KAN-14.",
        probe_import="deepagents",
    ),
    Node(
        "modelproxy",
        "Model proxy",
        "orchestrator",
        "missing",
        "ADR-011 seam. Bedrock calls are not yet behind an interface. KAN-11.",
        probe_import="boto3",
    ),
    Node(
        "secrets",
        "Secrets resolver",
        "orchestrator",
        "missing",
        "ADR-019's sixth seam. Credentials are still read from os.environ. KAN-10.",
    ),
    Node(
        "gate_retrieval",
        "Retrieval gate",
        "orchestrator",
        "missing",
        "Memory is injected on every turn unconditionally. Break-even skip rate "
        "is about 4 percent, so this pays for itself. KAN-16.",
    ),
    Node(
        "gate_obligation",
        "Obligation gate",
        "orchestrator",
        "built",
        "agent/gate.py — runs outside the model, fails closed, observe mode does not block.",
        evidence="probed",
        probe_import="agent.gate",
    ),
    Node(
        "registry",
        "Tool registry",
        "orchestrator",
        "partial",
        "agent/registry.py — semantic top-k selection, plus AgentCore Gateway "
        "MCP discovery. Gateway mode unverified.",
        evidence="probed",
        probe_import="agent.registry",
    ),
    # ── memory ─────────────────────────────────────────────────────────────────
    Node(
        "mem_working",
        "Working memory",
        "memory",
        "partial",
        "LangGraph state in the prototype. Bounded window not implemented.",
    ),
    Node(
        "mem_doc",
        "Self-editing document",
        "memory",
        "built",
        "/memory/AGENTS.md in the Postgres store. Verified: a fresh session "
        "recalled it with zero tool calls.",
    ),
    Node(
        "mem_skills",
        "Skills (procedural)",
        "memory",
        "partial",
        "skills_engine loads and validates them. Never observed firing in a run.",
        evidence="probed",
        probe_import="agent.skills_engine",
    ),
    Node(
        "mem_facts",
        "Semantic facts",
        "memory",
        "broken",
        "Graphiti on Neo4j. Grows correctly. Self-correction fired in 3 of 6 "
        "runs. Recall does NOT exclude expired facts. KAN-15.",
        probe_import="graphiti_core",
    ),
    Node(
        "mem_episodes",
        "Episodes + communities",
        "memory",
        "built",
        "Graphiti episodes with generated community summaries.",
        probe_import="graphiti_core",
    ),
    Node(
        "mem_scratch",
        "Session scratch",
        "memory",
        "partial",
        "Per-session directory on a volume. Separates accidents, not actors.",
    ),
    Node(
        "consolidation",
        "Consolidation",
        "memory",
        "missing",
        "No batched 'every N exchanges' pass. Nothing decides what is worth keeping.",
    ),
    # ── executor ───────────────────────────────────────────────────────────────
    Node(
        "shell",
        "Shell / code interpreter",
        "executor",
        "broken",
        "Runs as root in the same pod that holds every credential. Its own "
        "docstring says 'unrestricted'. KAN-19.",
    ),
    Node(
        "tools_web",
        "web_search · web_fetch",
        "executor",
        "built",
        "SearXNG self-hosted plus trafilatura, with r.jina.ai as fallback. Both keyless.",
    ),
    Node(
        "mcp",
        "MCP tool pools",
        "executor",
        "missing",
        "ADR-003 and ADR-021. Zero MCP servers connected. KAN-19.",
    ),
    Node(
        "hitl",
        "Human in the loop",
        "executor",
        "built",
        "approve / edit / reject on web_search. 6 of 6 checks passed.",
    ),
    # ── ops ────────────────────────────────────────────────────────────────────
    Node(
        "trace",
        "Trace",
        "ops",
        "missing",
        "No trace. The Postgres checkpointer holds most of one and has never been read. KAN-17.",
    ),
    Node(
        "ledger",
        "Usage ledger",
        "ops",
        "missing",
        "Total token spend on this project is unknown. KAN-17.",
    ),
    Node(
        "evals",
        "Evals",
        "ops",
        "missing",
        "Deterministic and judge suites, kept separate. Neither exists.",
    ),
    Node(
        "release",
        "Release gate",
        "ops",
        "missing",
        "Requires both eval suites first.",
    ),
)

EDGES: tuple[Edge, ...] = (
    Edge("cli", "respond"),
    Edge("http", "respond"),
    Edge("webui", "http"),
    Edge("respond", "loop", "assemble then run"),
    Edge("loop", "modelproxy", "one call per iteration"),
    Edge("modelproxy", "secrets", "resolve credentials", "dashed"),
    Edge("loop", "registry", "which tools"),
    Edge("loop", "shell", "execute"),
    Edge("loop", "tools_web"),
    Edge("tools_web", "hitl", "approval before search", "dashed"),
    Edge("registry", "mcp", "discover", "dashed"),
    Edge("respond", "gate_retrieval", "every turn", "dashed"),
    Edge("gate_retrieval", "mem_facts", "only if needed", "dashed"),
    Edge("gate_retrieval", "mem_doc", "only if needed", "dashed"),
    Edge("gate_retrieval", "mem_episodes", "only if needed", "dashed"),
    Edge("mem_skills", "mem_working", "on match", "dashed"),
    Edge("mem_working", "loop"),
    Edge("loop", "gate_obligation", "check the draft"),
    Edge("gate_obligation", "respond", "pass or refuse"),
    Edge("respond", "consolidation", "after N exchanges", "dashed"),
    Edge("consolidation", "mem_facts", "distil"),
    Edge("consolidation", "mem_episodes", "distil"),
    Edge("shell", "mem_scratch"),
    Edge("loop", "trace", "every event", "dashed"),
    Edge("modelproxy", "ledger", "every call", "dashed"),
    Edge("trace", "evals"),
    Edge("ledger", "evals"),
    Edge("evals", "release"),
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
    """Headline numbers for the overview. Honest arithmetic, not a score."""
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
        "groups": [asdict(group) for group in GROUPS],
        "nodes": nodes,
        "edges": [asdict(edge) for edge in EDGES],
        "counts": counts(nodes),
    }
