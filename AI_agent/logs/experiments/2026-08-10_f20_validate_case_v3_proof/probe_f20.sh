#!/usr/bin/env bash
# F-20 investigation — read-only, reproducible probe.
# Reproduces every measured fact in README.md. Never writes inside the repo;
# all scratch copies go to a throwaway tmp dir. Safe to re-run any time.
#
# Usage: bash probe_f20.sh   (run from anywhere; REPO is auto-detected below)

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SCRATCH="$(mktemp -d)"
echo "REPO=$REPO"
echo "SCRATCH=$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

cd "$REPO"

echo
echo "### 1. Founding-commit archaeology (Q1) ###"
echo "--- call site birth (802822f, 07-06): build_geometry(geom) -> build_geometry(geom, capability_profile=profile) ---"
git show 802822f -- src/agent/execution/validation_run.py | grep -A2 -B2 "build_geometry(geom"

echo "--- proof requirement birth (2885a84, 07-18): is_b5 and window_host_proof is None -> raise ---"
git show 2885a84 -- src/agent/geometry/build.py | grep -A3 "is_b5 and window_host_proof"

echo "--- 'never bind an approval to stale bytes' comment birth: git log -S ---"
git log -S"never bind an approval to stale" --oneline -- src/agent/execution/validation_run.py

echo "--- 'NOT the M0 audit manifest' comment birth: git log -S ---"
git log -S"NOT the M0 audit manifest" --oneline -- src/agent/execution/validation_run.py

echo "--- correction_geometry_snapped.json stage-root read: only ever touched by founding commit ---"
git log -S"correction_geometry_snapped.json" --oneline -- src/agent/execution/validation_run.py

echo
echo "### 2. F-20-A: validate_case never reads run_manifest.json (grep) ###"
grep -n "manifest\|RunManifest" src/agent/execution/validation_run.py

echo
echo "### 3. F-20-B: load_verified_accepted_correction production call sites ###"
echo "(excluding tests/ and backup/src_history/ snapshots)"
grep -rn "load_verified_accepted_correction(" --include="*.py" . | grep -v "/tests/" | grep -v "/backup/"

echo
echo "### 4. Stage-root mirroring is NOT complete for B5 artifacts (Q2) ###"
RUN="case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify"
echo "-- stage root 1_correction/ --"; ls "$RUN/1_correction/"
echo "-- attempts/001/ --"; ls "$RUN/1_correction/attempts/001/"
echo "-- sha256 mirror check (output.json / corrections.json) --"
sha256sum "$RUN/1_correction/correction_geometry_snapped.json" "$RUN/1_correction/attempts/001/output.json"
sha256sum "$RUN/1_correction/corrections.json" "$RUN/1_correction/attempts/001/audit.json"

echo
echo "### 5. F-20-D: manifest 1_correction record IS a B5 contract ###"
python3 -c "
import json
d = json.load(open('$RUN/_run/run_manifest.json'))
print(json.dumps(d['stages']['1_correction'], indent=2))
"

echo
echo "### 6. Reproduce the F-20 failure firsthand (read-only copy) ###"
# Copy the WHOLE case dir (not just the run) so case_dir=run_dir.parent resolves
# case_data/testdata_prompt.json correctly — validate_case needs it for the
# (unrelated) view-manifest / testdata checks; only 2_modelling/geometry_digest
# below is what F-20 is actually about.
cp -r case_tests/e2e_tests/sm21_anchor "$SCRATCH/sm21_anchor_copy"
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')
from src.agent.execution.validation_run import validate_case
from src.agent.execution.policy import RunPolicy
run_dir = Path('$SCRATCH/sm21_anchor_copy/run_2026-08-09_f18_e2e_verify')
policy = RunPolicy(capability_profile='orthogonal_polygon', require_ep=False)
res = validate_case(run_dir, policy=policy, write_reports=False)
print('blocked:', res.blocked)
print('geometry_digest:', res.geometry_digest)
for b in res.blocking_summary:
    print(' -', b)
"

echo
echo "### 7. Q3 attack-surface test: tamper a non-geometric field at stage root only ###"
python3 -c "
import json
p = '$SCRATCH/sm21_anchor_copy/run_2026-08-09_f18_e2e_verify/1_correction/correction_geometry_snapped.json'
d = json.load(open(p))
d['windows'][0]['room'] = 'room_TAMPERED_by_probe'
json.dump(d, open(p, 'w'))
"
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')
from src.agent.execution.validation_run import validate_case
from src.agent.execution.policy import RunPolicy
run_dir = Path('$SCRATCH/sm21_anchor_copy/run_2026-08-09_f18_e2e_verify')
policy = RunPolicy(capability_profile='orthogonal_polygon', require_ep=False)
res = validate_case(run_dir, policy=policy, write_reports=False)
crep = res.reports.get('1_correction')
print('Stage-root-only tamper (room field) — 1_correction check results:')
for r in crep.results:
    print(' ', r.check_id, r.status)
print('=> if all PASS/NOT_APPLICABLE except the pre-existing missing-proof FAIL, the tamper is INVISIBLE to today/Option-2 stage-root reading.')
"

echo
echo "### 8. Q3 attack-surface test: same tamper caught by Option 1 (manifest-hash-bound loader) ###"
rm -rf "$SCRATCH/run_copy2"; cp -r "$RUN" "$SCRATCH/run_copy2"
python3 -c "
import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from src.agent.output_coordinates import load_verified_accepted_correction
from src.agent.execution.manifest import load_run_manifest
run_dir = Path('$SCRATCH/run_copy2')
manifest = load_run_manifest(run_dir)
attempt_out = run_dir / '1_correction' / 'attempts' / '001' / 'output.json'
d = json.loads(attempt_out.read_text())
d['windows'][0]['room'] = 'room_TAMPERED_attempt'
attempt_out.write_text(json.dumps(d))
try:
    load_verified_accepted_correction(run_dir=run_dir, manifest=manifest)
    print('UNEXPECTED: load succeeded after attempt tamper')
except Exception as e:
    print('EXPECTED: load FAILED —', type(e).__name__, '-', e)
"

echo
echo "### 9. Q3 legacy blast-radius: golden anchors with NO run_manifest.json at all ###"
for d in case_tests/e2e_tests/*/run_*; do
  if [ -d "$d" ] && [ ! -f "$d/_run/run_manifest.json" ]; then
    echo "NO MANIFEST: $d"
  fi
done
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')
from src.agent.execution.manifest import load_run_manifest
m = load_run_manifest(Path('case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline'))
print('load_run_manifest on sm20 golden anchor ->', m)
print('=> any fix that unconditionally requires a manifest to resolve window_host_proof')
print('   would need an explicit legacy/no-manifest fallback, or it breaks this golden anchor.')
"

echo
echo "### 10. Q5: v3/B5 coverage count across every test file that calls validate_case ###"
for f in tests/test_validation_run_baseline.py tests/test_run_stage_flow.py tests/test_check_parity.py tests/test_reading_ruler_r1_batchB.py tests/test_run_pipeline_self_checks.py; do
  echo "--- $f ---"
  echo -n "validate_case( calls: "; grep -c "validate_case(" "$f"
  echo -n "schema_version==3 / '\"3\"' hits: "; grep -c 'schema_version.*3\|"3"' "$f" || true
  echo -n "correction_b5_v1 / B5 contract hits: "; grep -c -i "correction_b5\|b5_v1" "$f" || true
done

echo
echo "### 11. Q6: replay blast radius — real snapped geometry through the raw producer-draw gate ###"
python3 -c "
import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from src.agent.correction.parse import parse_correction_draw, correction_target
payload = json.loads(Path('$RUN/1_correction/correction_geometry_snapped.json').read_text())
target = correction_target('orthogonal_polygon')
try:
    parse_correction_draw(payload, target)
    print('UNEXPECTED: parse_correction_draw accepted the real artifact as-is')
except Exception as e:
    print('EXPECTED: parse_correction_draw rejects the real artifact as-is —', type(e).__name__, ':', e)
"
python3 -c "
import sys
sys.path.insert(0, '.')
from src.agent.correction.schema import nested_draw_forbidden_fields, nested_draw_derived_fields, CorrectedGeometryV3
print('FORBIDDEN fields (must be stripped for front-door replay):', nested_draw_forbidden_fields(CorrectedGeometryV3))
print('DERIVED fields (must be stripped for front-door replay):', nested_draw_derived_fields(CorrectedGeometryV3))
"

echo
echo "### 12. Q6: fixture size ###"
du -sh "$RUN"
du -sh "$RUN"/* 2>/dev/null

echo
echo "DONE."
