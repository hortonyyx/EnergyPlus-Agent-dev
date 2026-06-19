"""Tests for the offline interactive 3D geometry viewer generator (backlog #3).

The rendered result needs a browser to confirm visually (headless container); these
tests assert the generated HTML is self-contained + offline + carries the geometry
and all controls, and that the app script parses (node --check, when node exists)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_geometry_viewer as rgv  # noqa: E402

_GEO = {
    "zones": ["Z1", "Z2"],
    "surfaces": [
        {"name": "w1", "zone": "Z1", "type": "Wall", "obc": "Outdoors",
         "verts": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]},
        {"name": "w2", "zone": "Z2", "type": "Wall", "obc": "Surface",
         "verts": [[0, 0, 3], [4, 0, 3], [4, 0, 6], [0, 0, 6]]},
    ],
    "windows": [
        {"name": "win1", "parent": "w1", "verts": [[1, 0, 1], [3, 0, 1], [3, 0, 2], [1, 0, 2]]},
    ],
}


def test_viewer_is_offline_and_self_contained():
    html = rgv.build_viewer_html(_GEO, title="t")
    assert "unpkg.com" not in html and "cdn.jsdelivr" not in html  # offline
    assert "Three.js Authors" in html                              # three inlined
    assert "OrbitControls" in html                                 # orbit inlined
    assert "window.GEO = " in html                                 # geometry embedded


def test_viewer_embeds_geometry_verbatim():
    html = rgv.build_viewer_html(_GEO, title="t")
    start = html.index("window.GEO = ") + len("window.GEO = ")
    end = html.index(";</script>", start)
    geo = json.loads(html[start:end])
    assert len(geo["surfaces"]) == 2 and len(geo["windows"]) == 1 and geo["zones"] == ["Z1", "Z2"]
    # OBC metadata preserved (needed for colour-by-OBC)
    assert {s["obc"] for s in geo["surfaces"]} == {"Outdoors", "Surface"}


def test_viewer_has_all_controls():
    html = rgv.build_viewer_html(_GEO, title="t")
    for ctrl in ('id="opacity"', 'id="explode"', 'id="explodeMode"', 'id="measure"', 'id="savePng"',
                 'id="colorBy"', 'id="floorSel"', 'id="showWin"', 'id="showEdges"',
                 'id="hud"', 'id="meas"', 'section cuts', 'select by'):
        assert ctrl in html, f"missing control: {ctrl}"


def test_geometry_cannot_break_out_of_script():
    """High (review 2026-06-19): a string in the geometry containing </script>
    must not close the inline <script> — it must be escaped to \\u003c."""
    evil = {"zones": ["</script><img src=x onerror=alert(1)>"],
            "surfaces": [{"name": "n", "zone": "z", "type": "Wall", "obc": "Outdoors",
                          "verts": [[0, 0, 0], [1, 0, 0], [1, 0, 1]]}],
            "windows": []}
    html = rgv.build_viewer_html(evil, title="t")
    # exactly the 4 legitimate <script> blocks, none injected by the data
    assert html.count("<script>") == 4 and html.count("</script>") == 4
    assert "\\u003c/script\\u003e" in html  # the evil close-tag was escaped


def test_title_is_html_escaped():
    html = rgv.build_viewer_html(_GEO, title="<b>&x")
    assert "&lt;b&gt;&amp;x" in html                       # title escaped
    assert "Geometry inspection — <b>&x" not in html       # raw title not injected


def test_app_js_parses_with_node(tmp_path):
    """If node is available, the app script must parse (catches JS syntax errors I
    cannot catch by running the browser headless)."""
    node = shutil.which("node")
    if not node:
        return  # node not present in this environment — skip
    js = tmp_path / "app_check.js"
    js.write_text(rgv.app_js(), encoding="utf-8")
    r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, f"node --check failed:\n{r.stderr}"
