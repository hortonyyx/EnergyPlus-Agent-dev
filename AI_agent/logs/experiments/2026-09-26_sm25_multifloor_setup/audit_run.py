"""Audit run50 only after generation finishes; never expose GT to the agent."""
from __future__ import annotations

from collections import Counter
import importlib
import json
from pathlib import Path
import tempfile

from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.opening_review import facade_inventory
from src.agent.geometry.plan_assembly import assemble_plan_proposals
from src.agent.geometry.plan_partition import compile_plan_partition


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-26_sm25_multifloor_claude_run50"
CASE = "sm25-L_anchor"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(run: Path, name: str) -> Path:
    path = (run / name).resolve()
    if not path.is_relative_to(run.resolve()):
        raise ValueError(f"record points outside run: {name}")
    return path


def verify_inputs(run: Path, frozen: dict, manifest: dict, *, cold: bool) -> dict:
    assert manifest["scope"] == frozen["scope"]
    assert manifest["provider"] == frozen["provider"] == "claude"
    assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
    assert not manifest["input_contents"]["building_declaration"]["included"]
    if cold:
        assert "plan_recovery" not in manifest
        assert "seed" not in manifest
        assert not (run / "resume_plan.json").exists()
        assert not manifest["input_contents"].get("saved_pixel_plan", {}).get("included", False)
    else:
        recovery = manifest["plan_recovery"]
        assert recovery["image"] == "1f_view.png"
        assert digest(run / "resume_plan.json") == frozen["seed_sha256"]
        assert recovery["raw_sha256"] == frozen["seed_sha256"]
        assert recovery["image_sha256"] == frozen["image_sha256"]["1f_view.png"]
    for image, sha in frozen["image_sha256"].items():
        assert digest(run / "images" / image) == sha
        assert manifest["images"][image]["sha256"] == sha
    implementation = {name: digest(ROOT / name) == sha
                      for name, sha in manifest["implementation_sha256"].items()}
    assert all(implementation.values()), f"implementation hash mismatch: {[k for k,v in implementation.items() if not v]}"
    return {"frozen_scope_match": True,
            "seed_sha256": None if cold else frozen["seed_sha256"],
            "six_image_sha256": frozen["image_sha256"],
            "implementation_sha256": manifest["implementation_sha256"]}


def replay_assemblies(run: Path, manifest: dict) -> list[dict]:
    """Recompile saved drafts from bound PNGs and replay every successful assembly."""
    rows = []
    for path in sorted((run / "plan_assemblies").glob("assembly_*.json")):
        record = load(path)
        assert record["operation"] == "namespace_ids_and_translate_z_only"
        items, floors = [], []
        for binding in record["floors"]:
            draft_id = binding["draft_id"]
            draft = _relative(run, f"plan_drafts/{draft_id}/plan.json")
            assert digest(draft) == binding["expected_plan_sha256"]
            image_name = binding["image"]
            image = _relative(run, f"images/{image_name}")
            assert digest(image) == binding["image_sha256"] == manifest["images"][image_name]["sha256"]
            with Image.open(image) as picture:
                proposal, compilation = compile_plan_partition(load(draft), image_size=picture.size,
                                                               image_name=image_name)
            assert compilation == binding["compilation"]
            plan = load(draft)
            assert binding["original_floor_id"] == plan["floor_id"]
            assert binding["original_z_floor"] == plan["z_floor"]
            assert binding["ceiling_height"] == plan["ceiling_height"]
            items.append({"proposal": proposal, "floor_id": binding["floor_id"],
                          "z_floor": binding["z_floor"], "source_ref": binding["evidence"]})
            floors.append({"draft_id": draft_id, "draft_sha256": digest(draft),
                           "image": image_name, "image_sha256": digest(image),
                           "floor_id": binding["floor_id"], "z_floor": binding["z_floor"]})
        replayed = assemble_plan_proposals(items)
        matches = []
        for candidate in sorted(run.glob("candidate_*")):
            source_path = candidate / "source_model.json"
            if not source_path.is_file():
                continue
            provenance = load(source_path)["generation"]["provenance"]
            assembly = provenance.get("plan_assembly", {})
            if assembly.get("file") == str(path.relative_to(run)):
                assert assembly["sha256"] == digest(path)
                assert replayed == load(candidate / "proposal.json")
                matches.append(candidate.name)
        rows.append({"file": str(path.relative_to(run)), "sha256": digest(path),
                     "floors": floors, "candidate_replay_matches": matches,
                     "unmatched_note": None if matches else "No saved successful source candidate for this assembly"})
    return rows


def replay_final(run: Path, candidate: str) -> tuple[dict, dict, dict]:
    folder = _relative(run, candidate)
    source = load(folder / "source_model.json")
    proposal = load(folder / "proposal.json")
    display = load(folder / "display_geometry.json")
    with tempfile.TemporaryDirectory(prefix="sm25-multifloor-source-replay-") as tmp:
        exported = Path(tmp) / "candidate"
        report = export_source_proposal(proposal, exported,
                                        provenance=source["generation"]["provenance"])
        assert report["source_model_sha256"] == source["source_model_sha256"]
        assert load(exported / "source_model.json") == source
        assert load(exported / "display_geometry.json") == display
    return source, proposal, display


def first_floor_xy(run: Path, source: dict) -> dict:
    """Compare final F1 XY with the supplied saved plan; height is excluded."""
    seed = load(run / "resume_plan.json")
    image_name = "1f_view.png"
    with Image.open(run / "images" / image_name) as picture:
        try:
            original, _ = compile_plan_partition(seed, image_size=picture.size, image_name=image_name)
        except (ValueError, TypeError) as error:
            return {"status": "not_evaluated", "reason": f"saved F1 draft did not compile: {error}"}
    original_geom = original["geometry"]
    original_floor = original_geom["floors"][0]
    actual_floor = next((floor for floor in source["floors"] if floor["id"] == "F1"), None)
    if actual_floor is None:
        return {"status": "different", "reason": "final source has no F1 floor"}
    old_cells = {cell["id"]: Polygon(cell["polygon"]) for cell in original_floor["cells"]}
    actual_cells = {row["id"].split(":", 1)[1]: Polygon(row["polygon"])
                    for row in source["spaces"] if row["floor_id"] == "F1" and row["id"].startswith("F1:")}
    missing = sorted(old_cells.keys() - actual_cells.keys())
    added = sorted(actual_cells.keys() - old_cells.keys())
    changed = sorted(key for key in old_cells.keys() & actual_cells.keys()
                     if not old_cells[key].equals(actual_cells[key]))
    old_openings = {row["id"]: row for row in original_geom["windows"] + original_geom["openings"]}
    actual_openings = {row["id"].split(":", 1)[1]: row for row in source["openings"]
                       if row["id"].startswith("F1:")}
    missing_openings = sorted(old_openings.keys() - actual_openings.keys())
    added_openings = sorted(actual_openings.keys() - old_openings.keys())
    moved_openings = []
    for oid in sorted(old_openings.keys() & actual_openings.keys()):
        original_line = LineString([old_openings[oid]["p1"], old_openings[oid]["p2"]])
        xy = list(dict.fromkeys(tuple(vertex[:2]) for vertex in actual_openings[oid]["vertices"]))
        if len(xy) != 2 or not original_line.equals(LineString(xy)):
            moved_openings.append(oid)
    return {"status": "same_xy" if not any((missing, added, changed, missing_openings,
                                             added_openings, moved_openings)) else "different",
            "height_excluded": True, "original_floor_id": original_floor["name"],
            "missing_spaces": missing, "added_spaces": added, "moved_spaces": changed,
            "missing_openings": missing_openings, "added_openings": added_openings,
            "moved_openings": moved_openings}


def _source_exterior_facade(source: dict, opening: dict) -> tuple[str | None, str | None]:
    """Classify the actual exposed floor edge under an aperture, not its ID."""
    if not opening["exterior"]:
        return None, "interior_opening"
    spaces = {row["id"]: row for row in source["spaces"]}
    boundaries = {row["id"]: row for row in source["boundaries"]}
    host = boundaries.get(opening["host_boundary_id"])
    if host is None or host["geometry_type"] != "wall" or host["space_id"] not in opening["space_ids"]:
        return None, "source_host_boundary_invalid"
    floor_id = spaces[host["space_id"]]["floor_id"]
    floor = next((row for row in source["floors"] if row["id"] == floor_id), None)
    if floor is None:
        return None, "source_floor_missing"
    xy = list(dict.fromkeys(tuple(vertex[:2]) for vertex in opening["vertices"]))
    if len(xy) != 2:
        return None, "opening_plan_segment_invalid"
    line = LineString(xy)
    wall_line = LineString([host["vertices"][0][:2], host["vertices"][1][:2]])
    if not wall_line.covers(line):
        return None, "opening_not_on_declared_host"
    ring = list(orient(Polygon(floor["footprint"]), sign=1).exterior.coords)
    edges = [(a, b) for a, b in zip(ring, ring[1:]) if LineString([a, b]).covers(line)]
    if len(edges) != 1:
        return None, "opening_not_on_one_exposed_floor_edge"
    a, b = edges[0]
    normal = (b[1] - a[1], a[0] - b[0])  # CCW polygon has its exterior on the right.
    if normal[0] > 0 and normal[1] == 0:
        return "East", None
    if normal[0] < 0 and normal[1] == 0:
        return "West", None
    if normal[1] > 0 and normal[0] == 0:
        return "North", None
    if normal[1] < 0 and normal[0] == 0:
        return "South", None
    return None, "exposed_floor_edge_not_cardinal"


def _opening_diagnostic(source: dict, gt, partition: dict) -> dict:
    """Diagnostic GT opening pairing with the existing judge's declared tolerances.

    This is not the full typed B4b claim score: source proposals do not contain
    the correction V3 facade-segment identities or view evidence that it needs.
    """
    from src.agent.judge.gt_schema import GroundTruthV3
    from src.agent.judge.score_config import load_judge_score_config

    if not isinstance(gt, GroundTruthV3):
        return {"status": "not_evaluated", "reason": "typed GT opening diagnostic requires v3"}
    config = load_judge_score_config(ROOT / "src/configs/judge_score.yaml")
    classifications = facade_inventory(source)["opening_classifications"]
    floor_map = partition.get("floor_mapping", {})
    segments = {s.id: s for floor in gt.floors for s in floor.boundary_segments}
    room_matches = {row["candidate_id"]: row
                    for row in partition.get("comparison", {}).get("matches", [])}
    built = []
    old_classifier_disagreements = []
    source_unclassified = []
    for opening in source["openings"]:
        classification = classifications[opening["id"]]
        facade, reason = _source_exterior_facade(source, opening)
        if opening["exterior"] and facade != classification.get("facade"):
            old_classifier_disagreements.append({
                "opening_id": opening["id"], "source_exposed_edge_facade": facade,
                "old_facade_inventory_facade": classification.get("facade"),
                "old_facade_inventory_reason": classification.get("reason"),
                "source_exposed_edge_reason": reason,
            })
        if opening["exterior"] and facade is None:
            source_unclassified.append({"opening_id": opening["id"], "reason": reason})
        if facade is None:
            continue
        axis = 0 if facade in {"North", "South"} else 1
        vertices = opening["vertices"]
        built.append({"id": opening["id"], "kind": opening["kind"],
                      "floor_id": floor_map.get(classification["floor_id"]),
                      "facade": facade,
                      "along": [min(v[axis] for v in vertices), max(v[axis] for v in vertices)],
                      "z": [min(v[2] for v in vertices), max(v[2] for v in vertices)],
                      "host_ids": opening["space_ids"], "exterior": opening["exterior"]})
    targets = [{"id": item.id, "kind": item.kind, "floor_id": item.floor_id,
                "facade": segments[item.boundary_segment_id].facade_family,
                "along": [item.world_along_interval.lo, item.world_along_interval.hi],
                "z": None if item.z_interval is None else [item.z_interval.lo, item.z_interval.hi],
                "host_zone_id": item.host_zone_id}
               for item in gt.openings]
    matched, used_built, used_gt = [], set(), set()
    for key in sorted({(row["floor_id"], row["kind"], row["facade"]) for row in targets}):
        refs = [row for row in targets if (row["floor_id"], row["kind"], row["facade"]) == key]
        cands = [row for row in built if (row["floor_id"], row["kind"], row["facade"]) == key]
        if not refs or not cands:
            continue
        costs = []
        for ref in refs:
            costs.append([])
            for cand in cands:
                a, b = ref["along"], cand["along"]
                centre = abs((a[0] + a[1] - b[0] - b[1]) / 2)
                overlap = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
                costs[-1].append((centre + abs((a[1]-a[0])-(b[1]-b[0]))) if
                                 overlap > 0 and centre <= config.opening_match_center_tol_m else 1e6)
        for i, j in zip(*linear_sum_assignment(costs)):
            if costs[i][j] >= 1e6:
                continue
            ref, cand = refs[i], cands[j]
            used_gt.add(ref["id"]); used_built.add(cand["id"])
            along_delta = max(abs(ref["along"][k] - cand["along"][k]) for k in (0, 1))
            width_delta = abs((ref["along"][1]-ref["along"][0]) - (cand["along"][1]-cand["along"][0]))
            z_delta = None if ref["z"] is None else [abs(ref["z"][k] - cand["z"][k]) for k in (0, 1)]
            host = None if ref["host_zone_id"] is None else [
                room_matches[sid]["reference_id"] if sid in room_matches else None
                for sid in cand["host_ids"]]
            host_partition_status = None if host is None else [
                room_matches[sid]["status"] if sid in room_matches else "unmatched"
                for sid in cand["host_ids"]]
            matched.append({"reference_id": ref["id"], "opening_id": cand["id"],
                            "floor_id": key[0], "facade": key[2], "kind": key[1],
                            "reference_along_m": ref["along"], "candidate_along_m": cand["along"],
                            "reference_z_m": ref["z"], "candidate_z_m": cand["z"],
                            "max_along_endpoint_delta_m": along_delta, "width_delta_m": width_delta,
                            "z_endpoint_delta_m": z_delta,
                            "along_within_judge_tolerance": along_delta <= config.along_claim_tol_m,
                            "width_within_judge_tolerance": width_delta <= config.width_claim_tol_m,
                            "z_within_judge_tolerance": None if z_delta is None else
                                z_delta[0] <= config.sill_claim_tol_m and z_delta[1] <= config.head_claim_tol_m,
                            "host_zone_match": None if host is None else host == [ref["host_zone_id"]],
                            "host_mapping": host, "host_partition_status": host_partition_status})
    internal = [row for row in source["openings"] if not row["exterior"]]
    return {"mode": "typed_gt_exterior_opening_diagnostic_not_full_B4b_score",
            "judge_config_sha256": digest(ROOT / "src/configs/judge_score.yaml"),
            "tolerances_m": {"match_center": config.opening_match_center_tol_m,
                             "along": config.along_claim_tol_m, "width": config.width_claim_tol_m,
                             "sill": config.sill_claim_tol_m, "head": config.head_claim_tol_m},
            "matched": matched,
            "unmatched_reference": sorted(row["id"] for row in targets if row["id"] not in used_gt),
            "unmatched_built_exterior": sorted(row["id"] for row in built if row["id"] not in used_built),
            "old_classifier_disagreements": old_classifier_disagreements,
            "source_exposed_edge_unclassified": source_unclassified,
            "unclassified_source_openings": [row for row in classifications.values()
                                             if row.get("reason") not in {None, "not_exterior"}],
            "internal_openings_not_in_exterior_GT": [row["id"] for row in internal],
            "limits": ["GT exterior opening comparison does not verify internal door locations or missing internal doors.",
                       "Nearest paired openings are diagnostics; full judge B4b view evidence and segment binding are unavailable for geometry-v2 proposals."]}


def audit(run: Path = RUN) -> dict:
    run = run.resolve()
    if not (run / "summary.json").is_file():
        raise RuntimeError("generation must finish before audit or GT access")
    manifest, summary = load(run / "inputs.json"), load(run / "summary.json")
    cold = "plan_recovery" not in manifest
    frozen_path = (HERE.parent / "2026-09-26_sm25_multifloor_cold_setup" / "frozen_method.json"
                   if cold else HERE / "frozen_method.json")
    frozen = load(frozen_path)
    assert frozen["mode"] == ("original_images_only_whole_building_cold_start" if cold
                              else "saved_F1_plan_extension_to_two_floors")
    binding = verify_inputs(run, frozen, manifest, cold=cold)
    delivery = load(run / "delivery.json")
    receipt = load(run / "agent_receipt.json")
    assert receipt["actual_model"].startswith("claude-sonnet-")
    assert summary["delivery"]["candidate"] == delivery["candidate"]
    source, proposal, _ = replay_final(run, delivery["candidate"])
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    assemblies = replay_assemblies(run, manifest)
    f1_xy = ({"status": "not_applicable", "reason": "No saved F1 draft supplied"}
             if cold else first_floor_xy(run, source))

    # GT is loaded only after the completion gate and all input/replay checks.
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import gt_path, load_gt_document
    evaluation_path = run / "evaluation"
    if (evaluation_path / "summary.json").is_file():
        evaluation = load(evaluation_path / "summary.json")
    else:
        evaluation = evaluate(run, CASE, modelling_task="reconstruction",
            reference_scope=("Six original sm25 PNGs only; whole-building cold start. GT withheld from generation."
                             if cold else "Six original sm25 PNGs plus saved run48 F1 pixel declaration; two-floor extension, not a whole-building cold start. GT withheld from generation."),
            out=evaluation_path)
    partition = load(evaluation_path / f"{delivery['candidate']}_partition.json")
    gt = load_gt_document(CASE)
    openings = _opening_diagnostic(source, gt, partition)
    dump(evaluation_path / "final_opening_diagnostic.json", openings)
    strict = partition["comparison"]
    identity_codes = {"source_space_split", "source_spaces_merged", "missing_source_space",
                      "extra_source_space", "floor_assignment_changed", "candidate_spaces_overlap"}
    identity_findings = [row for row in strict["findings"] if row["code"] in identity_codes]
    internal_line_findings = [row for row in partition["topology_findings"]
                              if row["code"] == "internal_partition_boundary_changed"]
    floor_rows = []
    for floor in source["floors"]:
        mapped = partition["floor_mapping"].get(floor["id"])
        reference = next((row for row in gt.floors if row.id == mapped), None)
        floor_rows.append({"source_floor_id": floor["id"], "reference_floor_id": mapped,
                           "source_z_floor_m": floor["z_floor"], "source_height_m": floor["height"],
                           "reference_z_floor_m": None if reference is None else reference.z_floor_m,
                           "reference_height_m": None if reference is None else reference.ceiling_height_m,
                           "source_space_count": sum(s["floor_id"] == floor["id"] for s in source["spaces"]),
                           "reference_space_count": None if reference is None else len(reference.zones),
                           "strict_partition_findings": [row for row in strict["findings"]
                               if row.get("floor_id") == mapped or any(match.get("candidate_floor_id") == floor["id"]
                                   for match in [row.get("match", {})])],
                           "topology_findings": [row for row in partition["topology_findings"]
                               if row.get("floor_id") == mapped or any(match.get("candidate_floor_id") == floor["id"]
                                   for match in [row.get("match", {})])]})
    dump(evaluation_path / "final_floor_diagnostic.json", floor_rows)
    actions = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    result = {"mode": ("original_image_only_whole_building_post_generation_audit" if cold
                       else "saved_F1_draft_extension_post_generation_audit"),
              "candidate": delivery["candidate"], "selection_origin": delivery["selection_origin"],
              "actual_model": receipt["actual_model"], "generation_status": delivery["generation_status"],
              "input_and_implementation_binding": binding,
              "source_display_replay_exact": True, "assemblies_replayed": assemblies,
              "original_F1_xy": f1_xy,
              "source_validation": source["validation"],
              "counts": {name: len(source[name]) for name in
                         ("floors", "spaces", "openings", "connections", "unbuilt_openings", "unsupported")},
              "opening_kinds": dict(Counter(row["kind"] for row in source["openings"])),
              "tools": dict(Counter(row["action"] for row in actions)),
              "independent_GT_sha256": digest(gt_path(CASE)),
              "strict_partition_status": strict["status"],
              "strict_partition_findings": strict["findings"],
              "topology_status": partition["status"],
              "topology_findings": partition["topology_findings"],
              "space_correspondence": {"reference_count": strict["reference_count"],
                                       "candidate_count": strict["candidate_count"],
                                       "matched_count": strict["matched_count"],
                                       "split_merge_or_missing_findings": identity_findings},
              "internal_line_difference_findings": internal_line_findings,
              "topology_interpretation": "Strict 2 cm boundary and internal-line differences are retained. "
                  "A line offset is not by itself proof of an extra or missing room; explicit "
                  "split/merge/missing-room findings are reported separately.",
              "floor_diagnostic_file": "evaluation/final_floor_diagnostic.json",
              "opening_diagnostic_file": "evaluation/final_opening_diagnostic.json",
              "evaluation_summary_file": "evaluation/summary.json",
              "evaluation_candidates": [row["candidate"] for row in evaluation["candidates"]],
              "overall_fidelity": "not_automatically_decided",
              "limits": (["No saved plan or BIM supplied; this is a whole-building cold-start run."] if cold else
                         ["Saved run48 F1 draft was supplied; this is not whole-building cold start."]) + [
                         "GT and existing tolerance comparison are independent post-generation diagnostics, not source-image proof.",
                         "Exterior GT openings do not certify internal door completeness or source height evidence."]}
    # Preserve actual image transport evidence and archive the completed stream.
    finalizer = importlib.import_module("AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run")
    finalizer.finalize(run)
    result["transported_image_count"] = load(run / "transport_audit.json")["image_count"]
    result["stream_lossless_archive_verified"] = load(run / "stream_archive.json")["lossless_verified"]
    dump(run / "postrun_audit.json", result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    print(json.dumps(audit(args.run), ensure_ascii=False, indent=2))
