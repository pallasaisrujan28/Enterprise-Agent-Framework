"""Pin the topology payload so the chart cannot silently drift.

The dashboard renders whatever `describe()` returns. Without these tests a
renamed node id would break an edge, and the picture would quietly lose a line
rather than fail — which is the exact failure mode a data-driven diagram exists
to prevent.
"""

from __future__ import annotations

import pytest

from agent.dashboard import topology

VALID_STATUSES = {"built", "partial", "missing", "broken"}
VALID_EVIDENCE = {"probed", "claimed"}
VALID_EDGE_KINDS = {"solid", "dashed"}


@pytest.fixture
def payload() -> dict:
    return topology.describe()


def test_payload_has_the_keys_the_frontend_reads(payload: dict) -> None:
    # js/views.js and js/diagram.js read exactly these.
    assert set(payload) == {"generated_at", "groups", "nodes", "edges", "counts"}


def test_probe_fields_are_not_exposed(payload: dict) -> None:
    """`probe_import` and `probe_env` are internal.

    They name importable modules and environment variables, which is
    information about the host rather than about the architecture, so they are
    stripped before the payload leaves the process.
    """
    for node in payload["nodes"]:
        assert "probe_import" not in node
        assert "probe_env" not in node


def test_every_node_declares_a_valid_status_and_evidence(payload: dict) -> None:
    for node in payload["nodes"]:
        assert node["status"] in VALID_STATUSES, node
        assert node["evidence"] in VALID_EVIDENCE, node


def test_every_node_explains_itself(payload: dict) -> None:
    """A status with no reason is how the previous diagrams went stale."""
    for node in payload["nodes"]:
        assert node["detail"].strip(), f"{node['id']} has a status but no detail"


def test_node_ids_are_unique(payload: dict) -> None:
    ids = [node["id"] for node in payload["nodes"]]
    assert len(ids) == len(set(ids))


def test_every_node_belongs_to_a_declared_group(payload: dict) -> None:
    groups = {group["id"] for group in payload["groups"]}
    for node in payload["nodes"]:
        assert node["group"] in groups, f"{node['id']} is in unknown group {node['group']}"


def test_every_edge_connects_two_real_nodes(payload: dict) -> None:
    """The renderer skips an edge whose endpoints it cannot find.

    That is the right behaviour at runtime — a missing line beats a crash — and
    it is precisely why it has to fail here instead.
    """
    ids = {node["id"] for node in payload["nodes"]}
    for edge in payload["edges"]:
        assert edge["src"] in ids, f"edge from unknown node {edge['src']}"
        assert edge["dst"] in ids, f"edge to unknown node {edge['dst']}"
        assert edge["kind"] in VALID_EDGE_KINDS


def test_counts_match_the_nodes(payload: dict) -> None:
    assert sum(payload["counts"].values()) == len(payload["nodes"])


def test_probing_only_downgrades() -> None:
    """A node whose dependency is absent must not be reported as built.

    Probing never promotes: an installed library says nothing about whether we
    wired it up, so a claim of "missing" stays missing even when the import
    succeeds.
    """
    node = topology.Node(
        id="fake",
        label="Fake",
        group="ops",
        status="built",
        detail="claims to be built",
        probe_import="a_module_that_does_not_exist_anywhere",
    )
    status, evidence = topology._probe(node)
    assert status == "missing"
    assert evidence == "probed"

    claimed_missing = topology.Node(
        id="fake2",
        label="Fake2",
        group="ops",
        status="missing",
        detail="claims to be missing",
        probe_import="json",
    )
    status, _ = topology._probe(claimed_missing)
    assert status == "missing"


def test_known_broken_components_are_reported_as_broken(payload: dict) -> None:
    """Two things are verified NOT to work and must not drift to a softer status.

    - the shell runs as root in the pod holding every credential (KAN-19)
    - Graphiti recall returns facts it has already expired (KAN-15)
    """
    by_id = {node["id"]: node for node in payload["nodes"]}
    assert by_id["shell"]["status"] == "broken"
    if by_id["mem_facts"]["status"] != "missing":  # graphiti not installed here
        assert by_id["mem_facts"]["status"] == "broken"
