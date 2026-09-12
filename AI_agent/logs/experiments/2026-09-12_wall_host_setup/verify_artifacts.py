"""Verify frozen inputs, wall evidence and physical object changes after generation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.wall_reference import resolve_wall_references, convert_wall_dimensions
from src.agent.geometry.source_model import _digest

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()
run = args.run.resolve()
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert (run / "summary.json").is_file(), "wait for generator completion"
manifest = read(run / "inputs.json")
checks = {"implementation:"+p: sha(ROOT / p) == h for p,h in manifest["implementation_sha256"].items()}
checks.update({"image:"+p: sha(run / "images" / p) == v["sha256"] for p,v in manifest["images"].items()})
baseline_path = run / "seed/source_model.json"
if not baseline_path.is_file():
    baseline_path = next(iter(sorted(run.glob("candidate_*/source_model.json"))), None)
assert baseline_path is not None, "No built source candidate to verify"
seed = read(baseline_path)
rows = []
for directory in sorted(run.glob("candidate_*")):
    if not (directory / "source_model.json").exists():
        continue
    source = read(directory / "source_model.json")
    proposal = read(directory / "proposal.json")
    walls = resolve_wall_references(source, proposal.get("wall_references", []))
    dimensions = convert_wall_dimensions(walls, proposal.get("wall_dimensions", []))
    verified = {"source_digest": _digest({k:v for k,v in source.items() if k != "source_model_sha256"}) == source["source_model_sha256"]}
    if "wall_references" in source:
        verified.update(wall_replay=walls == source["wall_references"], dimension_replay=dimensions == source["wall_dimension_report"])
    changed = {}
    for field in ("spaces", "boundaries", "openings", "connections"):
        before = {r.get("id", r.get("opening_id")):r for r in seed[field]}
        after = {r.get("id", r.get("opening_id")):r for r in source[field]}
        changed[field] = {"added": sorted(after.keys()-before.keys()), "removed": sorted(before.keys()-after.keys()),
                          "changed": sorted(k for k in before.keys() & after.keys() if before[k] != after[k])}
    rows.append({"candidate":directory.name,"checks":verified,"changes_from_baseline":changed,
                 "spaces":len(source["spaces"]), "openings":dict(Counter(r["kind"] for r in source["openings"])),
                 "wall_reference_count":len(walls), "dimension_count":len(dimensions["dimensions"]),
                 "dimension_statuses":[d["status"] for d in dimensions["dimensions"]]})
report = {"baseline":str(baseline_path.relative_to(run)),"input_checks":checks,"candidates":rows,"scope":"execution and persistence; no drawing fidelity verdict"}
(run / "artifact_verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
assert all(checks.values()) and all(all(r["checks"].values()) for r in rows), report
print(json.dumps(report,ensure_ascii=False,indent=2))
