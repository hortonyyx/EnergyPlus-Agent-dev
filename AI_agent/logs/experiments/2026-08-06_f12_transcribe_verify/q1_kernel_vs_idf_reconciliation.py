"""F-12 ad-hoc inspection: reproduce the exact output-coordinate gate issues
against the saved temp IDF from the real-chain verification run, using the
REAL validator (src/validator/output_coordinates.py), not a hand-rolled
reimplementation.

Not a test — throwaway diagnostic, run from /tmp per project convention.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspaces/EnergyPlus-Agent-dev")

from eppy.modeleditor import IDF

IDF.setiddname("/EnergyPlus-25.1.0-68a4a7c774-Linux-Ubuntu22.04-x86_64/Energy+.idd")

RUN_DIR = Path(
    "/workspaces/EnergyPlus-Agent-dev/case_tests/e2e_tests/sm21_anchor/"
    "run_2026-08-06_wall3_a_retest"
)
IDF_PATH = RUN_DIR / "EP_f12_verify" / "temp_20260806_100002.idf"
SNAPSHOT_PATH = RUN_DIR / "5_intakeoutput" / "output_coordinate_snapshot.json"

from src.agent.output_coordinates import OutputCoordinateSnapshotV1
from src.validator.output_coordinates import _live_idf_vertex_drift_issues, _idf_vertices

snapshot = OutputCoordinateSnapshotV1.model_validate_json(SNAPSHOT_PATH.read_text())
print(f"snapshot records: {len(snapshot.records)}")
by_type = Counter(r.object_type for r in snapshot.records)
print("snapshot by object_type:", dict(by_type))

idf = IDF(str(IDF_PATH))
issues = _live_idf_vertex_drift_issues(snapshot, idf)
print(f"\nlive-IDF vertex-drift issues: {len(issues)}")

code_counts = Counter(i.code for i in issues)
print("by code:", dict(code_counts))

# classify by message shape
missing = [i for i in issues if "missing from the live IDF" in i.message]
host_changed = [i for i in issues if "host changed" in i.message]
vert_diff = [i for i in issues if "vertices differ" in i.message]
print(f"missing-from-idf: {len(missing)}")
print(f"host-changed: {len(host_changed)}")
print(f"vertices-differ: {len(vert_diff)}")

win_related = [i for i in issues if "_Win" in i.message]
wall_related = [i for i in issues if "_Win" not in i.message]
print(f"\nissues mentioning a window name (_Win): {len(win_related)}")
print(f"issues NOT mentioning a window name (walls/floors/roofs/ceilings): {len(wall_related)}")

print("\n--- sample of first 10 issues (full detail) ---")
for i in issues[:10]:
    print(f"[{i.code}] {i.message}")
    if i.detail:
        print("   detail:", i.detail[:500])

print("\n--- all vertices-differ issue names ---")
import re
names = []
for i in vert_diff:
    m = re.match(r"live IDF '([^']+)' vertices differ", i.message)
    if m:
        names.append(m.group(1))
print(f"count={len(names)}")
print(names)

print("\n--- deep-dive on one window: Z01_W3_Win1 ---")
win_issue = [i for i in vert_diff if "Z01_W3_Win1" in i.message]
if win_issue:
    d = json.loads(win_issue[0].detail)
    print("snapshot:", d.get("snapshot"))
    print("actual:  ", d.get("actual"))

print("\n--- deep-dive on one wall: Z01_Ceiling ---")
wall_issue = [i for i in vert_diff if i.message.startswith("live IDF 'Z01_Ceiling'")]
if wall_issue:
    d = json.loads(wall_issue[0].detail)
    print("snapshot:", d.get("snapshot"))
    print("actual:  ", d.get("actual"))

print("\n--- rotation check across ALL vert_diff: is actual a cyclic rotation of snapshot (same set, same order, diff start)? ---")
def is_rotation(a, b):
    if len(a) != len(b):
        return False
    a2 = a + a
    for k in range(len(a)):
        if tuple(a2[k:k+len(b)]) == tuple(b):
            return True
    return False

rotation_count = 0
reversed_rotation_count = 0
other_count = 0
for i in vert_diff:
    d = json.loads(i.detail)
    snap = [tuple(v) for v in d.get("snapshot", [])]
    act = [tuple(v) for v in d.get("actual", [])]
    if set(snap) != set(act):
        other_count += 1
        continue
    if is_rotation(snap, act):
        rotation_count += 1
    elif is_rotation(snap, list(reversed(act))):
        reversed_rotation_count += 1
    else:
        other_count += 1

print(f"same-vertex-set + rotation only: {rotation_count}")
print(f"same-vertex-set + reversed rotation (winding flip): {reversed_rotation_count}")
print(f"different vertex set entirely (real coordinate diff): {other_count}")

print("\n--- Q1 layered accounting: kernel snapshot vs final live IDF ---")
all_names = {r.name: r.object_type for r in snapshot.records}
drifted_names = set(names)
exact_match_names = sorted(set(all_names) - drifted_names)
print(f"total matched by name: {len(all_names)}")
print(f"exact match (0 diff): {len(exact_match_names)}")
print(f"cyclic rotation (same winding, diff start): {rotation_count}")
print(f"winding flip (reversed): {reversed_rotation_count}")
print(f"real coordinate diff: {other_count}")
print(f"missing from IDF: {len(missing)}")
print("exact-match names:", exact_match_names)
