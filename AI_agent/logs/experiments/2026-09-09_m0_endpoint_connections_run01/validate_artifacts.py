"""Check saved viewer wall cutouts and source counts; no browser/model calls."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union


def validate():
    run = Path(__file__).resolve().parent
    html = (run / "viewer.html").read_text()
    match = re.search(r"window\.GEO\s*=\s*", html)
    geo, _ = json.JSONDecoder().raw_decode(html[match.end():])
    surfaces = {s["name"]: s for s in geo["surfaces"]}
    errors = []
    for parent, parts in geo["visible_wall_parts"].items():
        surface = surfaces[parent]
        axis = max((0, 1), key=lambda i: max(p[i] for p in surface["verts"]) - min(p[i] for p in surface["verts"]))
        def ring(verts):
            return [(p[axis], p[2]) for p in verts]
        full = Polygon(ring(surface["verts"]))
        holes = unary_union([Polygon(ring(o["verts"])) for o in geo["openings"] if o["parent"] == parent])
        visible = unary_union([Polygon(ring(p["verts"]), [ring(h) for h in p.get("holes", [])]) for p in parts])
        errors.append(visible.symmetric_difference(full.difference(holes)).area)
        assert visible.intersection(holes).area < 1e-9
    assert max(errors) < 1e-9
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    with tempfile.TemporaryDirectory() as temp:
        for index, script in enumerate(scripts):
            path = Path(temp) / f"script{index}.js"
            path.write_text(script)
            subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)
    report = json.loads((run / "report.json").read_text())
    account = json.loads((run / "endpoint_connections.json").read_text())
    assert len(geo["source_model"]["spaces"]) == report["building"]["spaces"] == 32
    assert len(geo["windows"]) == 31
    old_model = json.loads((run.parent / "2026-09-09_m0_reading_openings_run01/2_modelling/building_geometry.json").read_text())
    def window_vertices(model):
        return sorted(tuple(sorted(tuple(v) for v in w["verts"])) for w in model["windows"])
    assert window_vertices(old_model) == window_vertices(geo)
    assert len(geo["source_model"]["openings"]) == 61  # 31 windows + 30 doors/passages
    assert len(geo["openings"]) == 57
    assert not report["correction"]["accepted"]
    assert report["building"]["source_mapping"]["status"] == "pass"
    old_second = account["historical_recipe"]["floors"][1]
    new_second = account["floors"][1]
    assert [old_second[k] for k in ("spaces_before_frame", "spaces_after_frame", "spaces_after_alignment")] == [16, 15, 11]
    assert [new_second[k] for k in ("spaces_before_frame", "spaces_after_frame", "spaces_after_alignment")] == [16, 16, 16]
    result = {"status": "pass", "source_spaces": 32, "windows": 31,
              "source_doors_and_passages": 30, "derived_openings": 57,
              "window_world_vertices_unchanged": True,
              "cut_parent_faces": len(errors), "max_wall_difference_area_error_m2": max(errors),
              "visible_walls_cover_no_opening_area": True,
              "viewer_inline_scripts_syntax_checked": len(scripts),
              "historical_second_floor_counts": [16, 15, 11],
              "new_second_floor_counts": [16, 16, 16],
              "not_evaluated": ["browser WebGL rendering and interaction", "whole-drawing partition fidelity"]}
    (run / "artifact_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
