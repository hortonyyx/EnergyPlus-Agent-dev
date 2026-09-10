#!/usr/bin/env python3
"""Build the sm25 presentation-only 3D BIM viewer.

The authoritative 2026-09-09 source BIM is never changed.  This builder makes
one local copy for the research-report demo and records one manual display aid:
the two face-line observations of one 2F door are intersected to a single,
two-space host interval. It uses the existing deterministic source-view
projection and HTML viewer, so walls are actually cut at all windows and doors.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "AI_agent/logs/experiments/2026-09-09_source_bim_run04/sm25/source_model.json"

sys.path.insert(0, str(ROOT))

from src.agent.geometry.source_bim import source_view_geometry  # noqa: E402
from src.agent.geometry.source_model import _digest  # noqa: E402
from scripts.tool_scripts.render_geometry_viewer import build_viewer_html  # noqa: E402


MANUAL_DOOR_ID = "showcase_manual:2f-door-L029g3-L030g2"
MANUAL_HOSTS = [
    "space/2f-c000/wall/8",
    "space/2f-c006/wall/0",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon_area(vertices: list[list[float]]) -> float:
    """Planar polygon area in 3D, using Newell's formula."""
    nx = ny = nz = 0.0
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx * nx + ny * ny + nz * nz) ** 0.5 / 2.0


def validate_manual_door(original: dict, model: dict, before: dict, after: dict, door: dict) -> dict:
    """Check the local presentation assist before HTML is written.

    This is intentionally independent of the original failed opening-account
    status. It proves that the manual door fits both whole wall faces, has two
    reciprocal hosts, does not overlap another opening, and caused a real cut
    of the expected area in the deterministic display projection.
    """
    eps = 1e-7
    assert len(door["space_ids"]) == len(MANUAL_HOSTS) == 2
    boundaries = {b["id"]: b for b in model["boundaries"]}
    assert {boundaries[h]["space_id"] for h in MANUAL_HOSTS} == set(door["space_ids"])
    assert any(set(relation["boundary_ids"]) == set(MANUAL_HOSTS)
               for relation in model["boundary_relations"])

    x0, x1 = door["vertices"][0][0], door["vertices"][1][0]
    z0, z1 = door["vertices"][0][2], door["vertices"][2][2]
    assert x0 < x1 and z0 < z1
    for host in MANUAL_HOSTS:
        wall = boundaries[host]["vertices"]
        a, b = wall[0], wall[1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length_sq = dx * dx + dy * dy
        assert length_sq > eps and all(abs((v[0] - a[0]) * dy - (v[1] - a[1]) * dx) < eps for v in door["vertices"])
        ts = [((v[0] - a[0]) * dx + (v[1] - a[1]) * dy) / length_sq for v in door["vertices"]]
        assert min(ts) >= -eps and max(ts) <= 1 + eps
        wall_z = [v[2] for v in wall]
        assert min(wall_z) - eps <= z0 < z1 <= max(wall_z) + eps
        for opening in original["openings"]:
            if host not in original["opening_hosts"][opening["id"]]:
                continue
            xs = [v[0] for v in opening["vertices"]]
            zs = [v[2] for v in opening["vertices"]]
            overlap_x = min(x1, max(xs)) - max(x0, min(xs))
            overlap_z = min(z1, max(zs)) - max(z0, min(zs))
            assert not (overlap_x > eps and overlap_z > eps), (host, opening["id"])

    display_openings = [o for o in after["openings"] if o["source_opening_id"] == door["id"]]
    assert len(display_openings) == 2
    names = {o["name"] for o in display_openings}
    assert all(o["partner"] in names and o["partner"] != o["name"] for o in display_openings)
    expected_cut_area = (x1 - x0) * (z1 - z0)
    cut_areas = {}
    for host in MANUAL_HOSTS:
        old_area = sum(polygon_area(part["verts"]) for part in before["display_surface_parts"][host])
        new_area = sum(polygon_area(part["verts"]) for part in after["display_surface_parts"][host])
        cut_areas[host] = old_area - new_area
        assert abs(cut_areas[host] - expected_cut_area) < 1e-6
    return {"door_interval_m": [x0, x1], "door_area_m2": expected_cut_area, "cut_areas_m2": cut_areas}


def main() -> None:
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    model = json.loads(json.dumps(original))

    # L029 and L030 are the two 120-mm wall-face lines at y=16.1251 / 16.0051 m.
    # Their gaps are one door seen on those two faces. The overlap (not the
    # union) is the 0.8067-m clear interval that wholly fits the existing
    # 2f-c000 ↔ 2f-c006 common boundary; it agrees with the single cyan swing
    # arc in the local original plan. This avoids inventing a third connection.
    door = {
        "id": MANUAL_DOOR_ID,
        "kind": "door",
        "host_boundary_id": "space/2f-c006/wall/0",
        "space_ids": ["2f-c000", "2f-c006"],
        "exterior": False,
        "vertices": [
            [10.1219, 16.0646, 3.6],
            [10.9286, 16.0646, 3.6],
            [10.9286, 16.0646, 5.7],
            [10.1219, 16.0646, 5.7],
        ],
        "connectivity": "unknown",
        "source_refs": ["manual_showcase:2f_view:L029g3", "manual_showcase:2f_view:L030g2"],
        "assumptions": [
            "Presentation-only manual interpretation: L029g3 and L030g2 are the two wall-face observations of one door, not two doors.",
            "The doorway interval is the overlap of the two observed face gaps (0.8067 m), so it lies fully on the existing 2f-c000 ↔ 2f-c006 shared wall.",
            "Door height is the existing sm25 interior-door convention (2.10 m); it is not newly measured from an elevation.",
        ],
    }
    model["openings"].append(door)
    model["opening_hosts"][MANUAL_DOOR_ID] = MANUAL_HOSTS
    model["connections"].append({
        "opening_id": MANUAL_DOOR_ID,
        "kind": "door",
        "space_ids": door["space_ids"],
        "exterior": False,
        "state": "unknown",
        "presentation_only": True,
    })
    model["showcase_metadata"] = {
        "kind": "research_report_presentation_assist",
        "original_source_model": str(SOURCE.relative_to(ROOT)),
        "original_source_model_sha256": sha256(SOURCE),
        "original_validation_status": original["validation"]["status"],
        "original_unbuilt_observations": original["unsupported"],
        "manual_changes": [{
            "change": "add one 2F two-space doorway to the display copy",
            "opening_id": MANUAL_DOOR_ID,
            "observation_ids": ["L029g3", "L030g2"],
            "counts_before": {"spaces": 29, "windows": 31, "doors": 29},
            "counts_after": {"spaces": 29, "windows": 31, "doors": 30},
            "status": "presentation-only; not an automatic reconstruction result",
        }],
    }
    # Preserve the original severe validation and unresolved observations in the
    # showcase source. The new local proof below validates only this display aid.
    model.pop("source_model_sha256", None)
    model["source_model_sha256"] = _digest(model)

    before = source_view_geometry(original)
    display = source_view_geometry(model)
    manual_geometry_proof = validate_manual_door(original, model, before, display, door)
    model["showcase_metadata"]["manual_geometry_proof"] = manual_geometry_proof
    # The proof is metadata too, so recompute the source digest then regenerate.
    model.pop("source_model_sha256", None)
    model["source_model_sha256"] = _digest(model)
    display = source_view_geometry(model)
    html = build_viewer_html(display, title="sm25 · 演示修订版（29 空间 / 31 窗 / 30 门）")

    (OUT / "showcase_model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "display_geometry.json").write_text(json.dumps(display, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "sm25_showcase.html").write_text(html, encoding="utf-8")
    manifest = {
        "kind": "sm25_research_report_showcase",
        "offline": True,
        "outputs": {
            "viewer": "sm25_showcase.html",
            "presentation_model": "showcase_model.json",
            "display_projection": "display_geometry.json",
        },
        "counts": {"spaces": 29, "windows": 31, "doors": 30, "manual_doors": 1},
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "manual_interpretation": "L029g3 + L030g2 are two wall-face observations of one 0.8067-m, two-space doorway; not a product success metric.",
        "manual_geometry_proof": manual_geometry_proof,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
