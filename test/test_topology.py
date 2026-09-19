"""Pin the topology payload so the chart cannot silently drift.

The dashboard renders whatever `describe()` returns. Without these tests a
renamed node id would break an edge and the picture would quietly lose a line
rather than fail — the exact failure a data-driven diagram exists to prevent.

Position is declared rather than computed (see the module docstring in
topology.py), which adds one failure mode a grid layout did not have: two nodes
can be given the same slot and silently overlap. That is tested here.
"""

from __future__ import annotations

import pytest

from agent.dashboard import topology

VALID_STATUSES = {"built", "partial", "missing", "broken"}
VALID_EVIDENCE = {"probed", "claimed"}
VALID_EDGE_KINDS = {"solid", "dashed"}
VALID_SHAPES = {"box", "diamond"}


@pytest.fixture
def payload() -> dict:
    return topology.describe()


def test_payload_has_the_keys_the_frontend_reads(payload: dict) -> None:
    # js/views.js and js/diagram.js read exactly these.
    assert set(payload) == {"generated_at", "bands", "nodes", "edges", "counts"}


def test_probe_fields_are_not_exposed(payload: dict) -> None:
    """`probe_import` and `probe_env` are internal.

    They name importable modules and environment variables — information about
    the host rather than the architecture — so they are stripped before the
    payload leaves the process.
    """
    for node in payload["nodes"]:
        assert "probe_import" not in node
        assert "probe_env" not in node


def test_every_node_declares_a_valid_status_shape_and_evidence(payload: dict) -> None:
    for node in payload["nodes"]:
        assert node["status"] in VALID_STATUSES, node
        assert node["evidence"] in VALID_EVIDENCE, node
        assert node["shape"] in VALID_SHAPES, node


def test_every_node_explains_itself(payload: dict) -> None:
    """A status with no reason is how the previous diagrams went stale."""
    for node in payload["nodes"]:
        assert node["detail"].strip(), f"{node['id']} has a status but no detail"
        assert node["caption"].strip(), f"{node['id']} has no caption for its box"


def test_captions_fit_in_a_box(payload: dict) -> None:
    """The renderer truncates, so an over-long caption is a silent tidiness bug.

    Caught here instead, because nobody reviews a chart for ellipses.
    """
    for node in payload["nodes"]:
        assert len(node["caption"]) <= 30, f"{node['id']} caption will be truncated"
        assert len(node["label"]) <= 24, f"{node['id']} label will be truncated"


def test_node_ids_are_unique(payload: dict) -> None:
    ids = [node["id"] for node in payload["nodes"]]
    assert len(ids) == len(set(ids))


def test_no_two_nodes_share_a_grid_slot(payload: dict) -> None:
    """Declared positions can collide; computed ones could not.

    Two nodes in the same (col, row) render exactly on top of each other, and
    the chart looks merely odd rather than broken.
    """
    seen: dict[tuple[int, int], str] = {}
    for node in payload["nodes"]:
        slot = (node["col"], node["row"])
        assert slot not in seen, f"{node['id']} overlaps {seen[slot]} at {slot}"
        seen[slot] = node["id"]


def test_every_node_belongs_to_a_declared_band(payload: dict) -> None:
    bands = {band["id"] for band in payload["bands"]}
    for node in payload["nodes"]:
        assert node["group"] in bands, f"{node['id']} is in unknown band {node['group']}"


def test_bands_own_disjoint_rows(payload: dict) -> None:
    """One row, one band.

    A band is drawn as the bounding box of its members, so two bands sharing a
    row produce overlapping rectangles and a label struck through by someone
    else's boxes. js/diagram.js also derives the band of a row in order to space
    rows apart, and that mapping is only well-defined if this holds.
    """
    owner: dict[int, str] = {}
    for node in payload["nodes"]:
        existing = owner.setdefault(node["row"], node["group"])
        assert existing == node["group"], (
            f"row {node['row']} is claimed by both {existing} and {node['group']} "
            f"(via {node['id']})"
        )


def test_edge_labels_fit_the_space_they_are_drawn_in(payload: dict) -> None:
    """The renderer truncates an edge label past 18 characters.

    18 monospace characters is also about as wide as the column gap, which is
    what the label has to sit in. Longer labels were clipped by the boxes on
    either side.
    """
    for edge in payload["edges"]:
        assert len(edge["label"]) <= 18, (
            f"{edge['src']}->{edge['dst']} label {edge['label']!r} will be truncated"
        )


def test_every_edge_connects_two_real_nodes(payload: dict) -> None:
    """The renderer skips an edge whose endpoints it cannot find.

    That is right at runtime — a missing line beats a crash — and precisely why
    it has to fail here instead.
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
    claims_built = topology.Node(
        id="fake",
        label="Fake",
        caption="pretend",
        group="ops",
        col=0,
        row=0,
        status="built",
        detail="claims to be built",
        probe_import="a_module_that_does_not_exist_anywhere",
    )
    status, evidence = topology._probe(claims_built)
    assert status == "missing"
    assert evidence == "probed"

    claims_missing = topology.Node(
        id="fake2",
        label="Fake2",
        caption="pretend",
        group="ops",
        col=0,
        row=0,
        status="missing",
        detail="claims to be missing",
        probe_import="json",
    )
    status, _ = topology._probe(claims_missing)
    assert status == "missing"


def test_known_broken_components_are_reported_as_broken(payload: dict) -> None:
    """Two things are verified NOT to work and must not drift to a softer status.

    - the shell runs as root in the pod holding every credential (KAN-19)
    - Graphiti recall returns facts it has already expired (KAN-15)
    """
    by_id = {node["id"]: node for node in payload["nodes"]}
    assert by_id["executor"]["status"] == "broken"
    # graphiti_core is not installed in this repo yet, so the probe downgrades
    # "broken" to "missing". Either is honest; "built" never is.
    assert by_id["semantic"]["status"] in {"broken", "missing"}


def test_the_flow_reaches_a_reply(payload: dict) -> None:
    """The chart is meant to read as one request, so the path must be connected.

    Walks forward from the channel and asserts the reply is reachable. A broken
    flow is the one defect a reader would not spot, because a chart with a gap
    still looks like a chart.
    """
    forward: dict[str, list[str]] = {}
    for edge in payload["edges"]:
        forward.setdefault(edge["src"], []).append(edge["dst"])

    seen: set[str] = set()
    queue = ["channel"]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(forward.get(current, []))

    assert "reply" in seen, "no path from channel to reply"
    assert "semantic" in seen, "memory is not reachable from the flow"
    assert "evals" in seen, "the ops loop is not reachable from the flow"
