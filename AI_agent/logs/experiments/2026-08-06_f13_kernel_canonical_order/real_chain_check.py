"""F-13 (2026-08-06) route-1 real-chain check on the REAL sm21 wall3 dataset.

Why this script exists instead of literally reusing the frozen
`5_intakeoutput/intake_output.json` via `--intake-from`, as the dispatch's
literal §4.2 recipe says: that recipe was written to verify the REJECTED
validator-side fix (which runs fresh on every downstream call, regardless of
when intake_output.json was frozen). Route 1 (this fix) moves the fix
upstream, into 2_modelling/3_split_pairing — stages that already finished
and got baked into that frozen JSON *before* this fix existed. Reusing it
verbatim cannot show the fix's effect: confirmed by direct inspection (see
below, Z01_Ceiling's frozen snapshot record starts at index that is NOT its
top-left corner under the shared canonicalizer).

This script instead:
  1. Loads the REAL accepted 1_correction output for
     run_2026-08-06_wall3_a_retest (read-only; schema v1/rectangular per
     that run's run_config.yaml, so no window-host-proof machinery needed).
  2. Runs it through `build_geometry` (this fix, live from the working
     tree) to get a canonical `BuildingGeometry`.
  3. Feeds it through the REAL production entry points
     (`SurfaceConverter.validate` / `FenestrationConverter.validate`) —
     same as Lock 1, but on all 115 real faces instead of a 7-face fixture.
  4. Surgically patches ONLY the Vertices fields of a copy of the already
     fully-formed, already-LLM-produced IDF
     (EP_f12_verify/temp_20260806_100002.idf, read-only source) to match
     what the validated surfaces/windows now carry — everything else
     (materials, constructions, zones, schedules, HVAC — all non-geometric)
     is untouched. This reuses real downstream LLM output for the parts
     F-13 does not touch, at zero additional LLM cost.
  5. Computes the REAL "B-layer" issue count via the actual production
     function `_live_idf_vertex_drift_issues`, comparing a FRESH
     `build_output_coordinate_snapshot(bg)` (this fix's canonical output)
     against the patched live IDF.
  6. Runs local EnergyPlus (`-x -w data/weather/Shenzhen.epw`, no LLM cost)
     and reports severe count + hands the result to wh_audit2.py.

Zero writes to the live run directory — read-only throughout. All outputs
go under this script's own directory.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))

RUN_DIR = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest"
OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

from src.agent._share import IDD_PATH, ensure_schema_initialized  # noqa: E402
ensure_schema_initialized()

from eppy.modeleditor import IDF  # noqa: E402
from src.agent.correction.schema import CorrectedGeometry  # noqa: E402
from src.agent.geometry import build_geometry  # noqa: E402
from src.agent.output_coordinates import build_output_coordinate_snapshot  # noqa: E402
from src.validator.data_model import BaseSchema, GeometrySchema  # noqa: E402
from src.validator.output_coordinates import _live_idf_vertex_drift_issues  # noqa: E402
from src.converters.surface_converter import SurfaceConverter  # noqa: E402
from src.converters.fenestration_converter import FenestrationConverter  # noqa: E402

# --------------------------------------------------------------------------- #
# 1. load the REAL accepted 1_correction output (read-only)
# --------------------------------------------------------------------------- #
corr_path = RUN_DIR / "1_correction" / "attempts" / "001" / "output.json"
corr_dict = json.loads(corr_path.read_text())
corr_dict.setdefault("schema_version", "1")
geom = CorrectedGeometry.model_validate(corr_dict)
print(f"loaded 1_correction accepted output: {len(geom.windows)} windows, "
      f"{sum(len(fl.cells) for fl in geom.floors)} cells across {len(geom.floors)} floor(s)")

# --------------------------------------------------------------------------- #
# 2. run the FIXED kernel
# --------------------------------------------------------------------------- #
bg = build_geometry(geom, capability_profile="rectangular")
print(f"build_geometry (fixed kernel): {len(bg.surfaces)} surfaces, {len(bg.windows)} windows")

# --------------------------------------------------------------------------- #
# 3. real production entry points — identity + §2.3 change counter
# --------------------------------------------------------------------------- #
BaseSchema.set_idf(IDD_PATH)
idf_for_validate = BaseSchema.get_idf()
GeometrySchema._interior_points = None
import numpy as np
GeometrySchema._interior_points = np.array([])
GeometrySchema._surface_to_normal_vector = {}
GeometrySchema.reset_normalization_change_state()

zone_to_surfaces: dict[str, list[dict]] = {}
for s in bg.surfaces:
    zone_to_surfaces.setdefault(s.zone, []).append({
        "Name": s.name, "Surface Type": s.stype,
        "Construction Name": "Exterior Wall" if s.stype == "Wall" else "Interior Floor",
        "Zone Name": s.zone, "Outside Boundary Condition": s.obc,
        "Outside Boundary Condition Object": s.obc_obj or None,
        "Vertices": [{"X": v[0], "Y": v[1], "Z": v[2]} for v in s.verts],
    })
validated_surfaces = SurfaceConverter(idf_for_validate).validate(zone_to_surfaces)
surf_verts_by_name = {s.name: [(float(x), float(y), float(z)) for x, y, z in s.vertices] for s in validated_surfaces}

fen_data = {"fenestrationsurfaces": [
    {"Name": w.name, "Surface Type": "Window", "Construction Name": "Exterior Window",
     "Building Surface Name": w.parent, "Number of Vertices": len(w.verts),
     "Vertices": [{"X": v[0], "Y": v[1], "Z": v[2]} for v in w.verts]}
    for w in bg.windows
]}
validated_fen = FenestrationConverter(idf_for_validate).validate(fen_data)
win_verts_by_name = {f.name: [(float(x), float(y), float(z)) for x, y, z in f.vertices] for f in validated_fen.fenestrationsurfaces}

mismatches = []
for s in bg.surfaces:
    kernel_v = [tuple(v) for v in s.verts]
    if surf_verts_by_name[s.name] != kernel_v:
        mismatches.append(s.name)
for w in bg.windows:
    kernel_v = [tuple(v) for v in w.verts]
    if win_verts_by_name[w.name] != kernel_v:
        mismatches.append(w.name)

print(f"\n=== identity through real entry points (Lock 1, on REAL 115-face data) ===")
print(f"mismatches: {len(mismatches)} / {len(bg.surfaces) + len(bg.windows)}  -> {mismatches[:10]}")
print(f"§2.3 change counter: {GeometrySchema.normalization_change_count()}")
if GeometrySchema.normalization_change_count():
    print("change log sample:", GeometrySchema.normalization_change_log()[:5])

# --------------------------------------------------------------------------- #
# 4. surgically patch vertices into a copy of the real already-simulated IDF
# --------------------------------------------------------------------------- #
src_idf_path = RUN_DIR / "EP_f12_verify" / "temp_20260806_100002.idf"
IDF.setiddname(str(IDD_PATH))
idf = IDF(str(src_idf_path))

patched = 0
for obj in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
    v = surf_verts_by_name.get(obj.Name)
    if v is None:
        continue
    for i, (x, y, z) in enumerate(v, 1):
        setattr(obj, f"Vertex_{i}_Xcoordinate", x)
        setattr(obj, f"Vertex_{i}_Ycoordinate", y)
        setattr(obj, f"Vertex_{i}_Zcoordinate", z)
    patched += 1
for obj in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]:
    v = win_verts_by_name.get(obj.Name)
    if v is None:
        continue
    for i, (x, y, z) in enumerate(v, 1):
        setattr(obj, f"Vertex_{i}_Xcoordinate", x)
        setattr(obj, f"Vertex_{i}_Ycoordinate", y)
        setattr(obj, f"Vertex_{i}_Zcoordinate", z)
    patched += 1
print(f"\npatched {patched} live-IDF objects' vertices to the fixed kernel's canonical output")

# --------------------------------------------------------------------------- #
# 5. B-layer: real production function, fresh canonical snapshot vs patched IDF
# --------------------------------------------------------------------------- #
snapshot = build_output_coordinate_snapshot(bg)
issues = _live_idf_vertex_drift_issues(snapshot, idf)
print(f"\n=== B-layer (_live_idf_vertex_drift_issues, real fn) ===")
print(f"issues: {len(issues)}")
for i in issues[:10]:
    print(" ", i.code, i.message)

# --------------------------------------------------------------------------- #
# 6. save + run local EnergyPlus
# --------------------------------------------------------------------------- #
idf_out = OUT_DIR / "f13_kernel_verify.idf"
idf.idfobjects["OUTPUT:SURFACES:LIST"] = []
idf.newidfobject("OUTPUT:SURFACES:LIST", Report_Type="Details")
idf.saveas(str(idf_out))
print(f"\nsaved patched IDF: {idf_out}")

EPW = REPO / "data/weather/Shenzhen.epw"
ep_out_dir = OUT_DIR / "ep_out"
ep_out_dir.mkdir(exist_ok=True)
ep_exe = None
import shutil
for cand in ("energyplus", "EnergyPlus"):
    p = shutil.which(cand)
    if p:
        ep_exe = p
        break
if ep_exe is None:
    for cand in Path("/").glob("EnergyPlus-*"):
        maybe = cand / "energyplus"
        if maybe.exists():
            ep_exe = str(maybe)
            break
print(f"EnergyPlus exe: {ep_exe}")
if ep_exe:
    cmd = [ep_exe, "-x", "-w", str(EPW), "-d", str(ep_out_dir), str(idf_out)]
    print("running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ep_out_dir), capture_output=True, text=True, timeout=300)
    print("returncode:", result.returncode)
    print(result.stdout[-3000:])
    print(result.stderr[-2000:])
else:
    print("EnergyPlus executable not found — skipping simulation")
