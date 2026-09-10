"""Read-only evidence inventory; no model, solver, GT, or artifact mutation."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_view(doc):
    strokes = doc.get("strokes", [])
    return {
        "image_kind": doc.get("image_kind"),
        "scale_origin": doc.get("scale_origin"),
        "calibration_note": doc.get("calibration_note"),
        "pens": dict(Counter(s.get("pen") for s in strokes)),
        "dimension_count": len(doc.get("dimensions", [])),
        "walls": [{k: s.get(k) for k in ("id", "geometry", "dimension_refs", "note")}
                  for s in strokes if s.get("pen") == "wall"],
        "explicit_door_strokes": [s for s in strokes if s.get("pen") in {"door", "opening", "passage"}],
        "door_mentions_in_stroke_notes": [s.get("id") for s in strokes
                                           if any(t in s.get("note", "").lower()
                                                  for t in ("door", "门"))],
        "uncaptured": doc.get("uncaptured"),
    }


def inventory():
    fixtures = json.loads((REPO / "case_tests/test_baseline/reading_fixtures.json").read_text())
    records = []
    for fixture in fixtures["fixtures"]:
        run = REPO / fixture["run"]
        files = sorted((run / "0_reading").glob("*_view.json"))
        records.append({
            "id": fixture["id"], "run": fixture["run"],
            "historical_label": fixture["label"], "historical_score": fixture["score"],
            "view_files": [{"path": str(p.relative_to(REPO)), "sha256": digest(p)} for p in files],
            "view_set_sha256": hashlib.sha256(b"".join(
                p.name.encode() + b"\0" + p.read_bytes() + b"\0" for p in files)).hexdigest() if files else None,
            "cv_sidecar_files_present": len(list((run / "0_reading" / "cv_evidence").rglob("*.json"))),
            "note": "Sidecar count is retained files under cv_evidence, not total tool calls or completeness.",
        })
    groups = defaultdict(list)
    for p in sorted((REPO / "case_tests/e2e_tests").glob("*/run*/0_reading/1f_view.json")):
        groups[digest(p)].append(str(p.relative_to(REPO)))
    selected = {}
    for name, path in {
        "sm21_0707_1f": "case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/1f_view.json",
        "sm24_0707_1f": "case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json",
        "sm21_0820_S1_1f": "case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/0_reading/1f_view.json",
    }.items():
        p = REPO / path
        selected[name] = {"path": path, "sha256": digest(p), **summarize_view(json.loads(p.read_text()))}
    path = "AI_agent/logs/experiments/2026-09-09_automatic_source_sm21_run01/run/0_reading/attempts/001/output.json"
    p = REPO / path
    selected["sm21_0909_1f"] = {"path": path, "json_pointer": "/views/1f_view", "sha256": digest(p),
                                 **summarize_view(json.loads(p.read_text())["views"]["1f_view"])}
    path = "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json"
    p = REPO / path
    doc = json.loads(p.read_text())
    selected["sm25_as_drawn_2f"] = {
        "path": path, "sha256": digest(p), "schema": doc["schema"], "ledger": doc["ledger"],
        "hypotheses_sources": {k: doc["hypotheses"].get(k) for k in
                               ("perception_source", "opening_types_source", "pairs_status")},
        "family_roles_source": doc["hypotheses"]["family_roles"].get("source"),
    }
    path = "case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/1_correction/correction_raw.txt"
    p = REPO / path
    doc = json.loads(p.read_text())
    selected["sm24_0624_raw_correction"] = {
        "path": path, "sha256": digest(p),
        "floors": [{"name": f["name"], "cell_count": len(f["cells"]),
                    "cell_ids": [c["id"] for c in f["cells"]]} for f in doc["floors"]],
        "note": "The raw correction response already contains the 11 cells, before downstream surface generation.",
    }
    path = "case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/0_reading/attempts/001/score_vs_gt.json"
    p = REPO / path
    doc = json.loads(p.read_text())
    selected["sm21_S1_saved_score"] = {
        "path": path, "sha256": digest(p), "scorer_schema": doc.get("scorer_schema"),
        "tolerances": doc.get("tolerances"),
        "plans": {k: {field: v.get(field) for field in ("wall_hits", "wall_total", "max_wall_offset_m", "boundary")}
                  for k, v in doc["scores"].items() if isinstance(v, dict) and "wall_hits" in v},
        "note": "Current saved sidecar inspection, not a fresh score or proof of the exact scorer used at the original run date.",
    }
    return {
        "scope": "Repository HEAD 5a37eb71 historical products; current scan is not an independent generation or new quality score.",
        "fixtures": records,
        "first_floor_byte_duplicates": {
            "scope": "case_tests/e2e_tests/*/run*/0_reading/1f_view.json only; identical first floor does not prove all six views identical",
            "file_count": sum(map(len, groups.values())), "unique_sha256_count": len(groups),
            "duplicate_groups": [{"sha256": h, "paths": ps} for h, ps in groups.items() if len(ps) > 1],
        },
        "selected_products": selected,
    }


if __name__ == "__main__":
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))
