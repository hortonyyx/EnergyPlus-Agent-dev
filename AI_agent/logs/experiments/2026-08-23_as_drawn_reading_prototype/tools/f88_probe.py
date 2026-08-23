"""F-88 diagnostic: does the converter's LENGTH-based jamb-cap rule move gt's zones?

⛔ READ-ONLY.  It monkeypatches the cap identification IN MEMORY, in a copy of the
run, and compares the resulting zone polygons with the SIGNED gt.json.  It edits
neither ``src/`` nor gt.

Why ask: the cap rule calls any short cross-section stroke within the wall
thickness range a jamb cap.  sm25's corridor wall carries 7 doors in a row, so the
REAL face fragments between them (0.36 m) fall in that range.  Measured on the
signed answer's own conversion report: 60 of 84 thickness-evidence entries are
> 0.25 m (0.30 / 0.36 / 0.296 / 0.356 ...) while the drawing declares only
240 / 120 -- and the code only keeps a junction-scale thickness event when a cap
band "proves" it.  So a false cap can turn a T-junction artefact into a thickness
event, which moves a zone edge.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from src.agent.judge import tarch_normalize as TN  # noqa: E402
from src.agent.judge.gt_manifest import load_gt_tooling_config  # noqa: E402
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1  # noqa: E402

GT_CFG = REPO / "src/configs/judge_gt.yaml"
VG_CFG = REPO / "src/configs/correction.yaml"


STATS = {"before": 0, "after": 0, "calls": 0}


def _geometric_cap_filter(collect, t_max_native: float):
    """Keep only caps that really span BETWEEN two long strokes of the other axis."""
    long_x, long_y = set(), set()
    for _h, x0, y0, x1, y1 in collect.wall_lines:
        if x0 == x1 and abs(y1 - y0) > t_max_native:
            long_x.add(round(x0, 4))
        elif y0 == y1 and abs(x1 - x0) > t_max_native:
            long_y.add(round(y0, 4))

    def near(v, s):
        return any(abs(v - c) <= 20.0 for c in s)     # 20 native units = 20 mm

    STATS["calls"] += 1
    STATS["before"] += sum(len(v) for v in collect.caps_v.values()) + \
                       sum(len(v) for v in collect.caps_h.values())
    for const, spans in list(collect.caps_v.items()):
        keep = {sp for sp in spans if near(sp[0], long_y) and near(sp[1], long_y)}
        collect.caps_v[const] = keep
    for const, spans in list(collect.caps_h.items()):
        keep = {sp for sp in spans if near(sp[0], long_x) and near(sp[1], long_x)}
        collect.caps_h[const] = keep
    STATS["after"] += sum(len(v) for v in collect.caps_v.values()) + \
                      sum(len(v) for v in collect.caps_h.values())
    return collect


def main(case: str, dxf: str, request_path: str) -> int:
    request = TarchConversionRequestV1.model_validate_json(Path(request_path).read_text())
    tooling = load_gt_tooling_config(GT_CFG, VG_CFG)
    t_max_native = max(float(t) for t in request.wall_thickness_range_m) / float(request.metres_per_unit)

    out = {}
    original = TN._collect_walls
    for variant in ("as_shipped", "geometric_caps"):
        if variant == "geometric_caps":
            def patched(*a, **k):
                return _geometric_cap_filter(original(*a, **k), t_max_native)
            TN._collect_walls = patched
        else:
            TN._collect_walls = original
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / Path(dxf).name
            shutil.copy2(dxf, staged)
            work = Path(tmp) / "work"
            res = TN.run_tarch_conversion(staged, request, tooling, work)
            plans = getattr(res, "plan_results", None) or [res]
            zones = []
            for pl in plans:
                for z in getattr(pl, "zones", []) or []:
                    poly = getattr(z, "polygon", None)
                    if poly is None:
                        poly = getattr(z, "vertices", None)
                    coords = []
                    if poly is not None:
                        try:
                            coords = list(poly.exterior.coords)     # shapely Polygon
                        except AttributeError:
                            coords = list(poly)
                    zones.append({"name": str(getattr(z, "name", getattr(z, "zone_id", "?"))),
                                  "polygon": [[round(float(x), 4), round(float(y), 4)]
                                              for x, y in coords]})
            out[variant] = {"zones": sorted(zones, key=lambda z: z["name"])}
    TN._collect_walls = original

    a, b = out["as_shipped"], out["geometric_caps"]
    same = a["zones"] == b["zones"]
    diffs = []
    for za, zb in zip(a["zones"], b["zones"]):
        if za != zb:
            diffs.append({"zone": za["name"], "as_shipped": za["polygon"][:6],
                          "geometric_caps": zb["polygon"][:6]})
    report = {"case": case,
              # ⛔ proof the patch actually ran and actually removed caps -- without
              # this, "identical zones" is indistinguishable from "patch never fired"
              "patch_calls": STATS["calls"],
              "caps_before_filter": STATS["before"], "caps_after_filter": STATS["after"],
              "caps_removed": STATS["before"] - STATS["after"],
              "zones": len(a["zones"]),
              "zone_polygons_identical": same, "zones_that_moved": len(diffs),
              "examples": diffs[:4]}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
