"""Run the chart's geometry check inside the normal pytest gate.

test_topology.py pins the data behind the diagram. This pins the diagram: that no
line is routed through a box it has nothing to do with, that no two labels land
on each other, and that nothing falls outside the canvas. Those were real
defects, and none of them is visible to a test that only looks at the payload.

The check itself is JavaScript because the renderer is JavaScript — reimplementing
the layout in Python to assert against would be testing a second implementation,
not the one that ships. It needs node and no packages. Where node is absent the
test SKIPS rather than fails: the geometry is still checked wherever node exists,
including CI, and a missing toolchain is not a defect in the chart.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agent.dashboard import topology

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / "test" / "chart_geometry.mjs"
RENDERER = REPO / "agent" / "dashboard" / "static" / "js" / "diagram.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_rendered_chart_is_geometrically_sound(tmp_path: Path) -> None:
    payload = tmp_path / "topology.json"
    payload.write_text(json.dumps(topology.describe()))

    result = subprocess.run(  # noqa: S603 — fixed argv, no shell, paths are ours
        [str(shutil.which("node")), str(CHECKER), str(RENDERER), str(payload)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, (
        "the architecture chart has layout defects:\n" + result.stderr.strip()
    )
