"""Verify a completed standalone BIM run, including imported seed provenance.

Reuses the earlier input, deterministic replay, returned-image and usage checks.
GT is never read. Source drawings and semantic fidelity need separate review.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


OLD = Path(__file__).resolve().parent.parent / "2026-09-20_sm24_method_transfer_run01" / "verify_run.py"
SPEC = importlib.util.spec_from_file_location("sm24_original_run_verify", OLD)
assert SPEC and SPEC.loader
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)
load = HELPERS.load
sha = HELPERS.sha
REPO = Path(__file__).resolve().parents[4]


def plan_provenance(run: Path, manifest: dict, original_dir: Path | None) -> dict:
    plan = manifest.get("plan_recovery")
    if not plan:
        return {"applicable": False, "pass": True}
    source = Path(plan.get("source_path", "")) if plan.get("source_path") else None
    frozen_name = plan.get("frozen_path")
    frozen = run / frozen_name if isinstance(frozen_name, str) else None
    image_name = plan.get("image")
    image_info = manifest.get("images", {}).get(image_name) if isinstance(image_name, str) else None
    run_image = run / "images" / image_name if image_info else None
    original_image = original_dir / image_name if original_dir and image_info else None
    source_bytes = source.read_bytes() if source and source.is_file() else None
    frozen_bytes = frozen.read_bytes() if frozen and frozen.is_file() else None
    checks = {
        "input_mode_is_saved_plan_recovery": manifest.get("input_mode") == "saved_plan_recovery",
        "source_plan_present": source_bytes is not None,
        "frozen_plan_present": frozen_bytes is not None,
        "source_and_frozen_plan_bytes_identical": source_bytes is not None and
            frozen_bytes is not None and source_bytes == frozen_bytes,
        "source_plan_hash_matches_manifest": source_bytes is not None and
            hashlib.sha256(source_bytes).hexdigest() == plan.get("raw_sha256"),
        "frozen_plan_hash_matches_manifest": frozen_bytes is not None and
            hashlib.sha256(frozen_bytes).hexdigest() == plan.get("raw_sha256"),
        "source_plan_size_matches_manifest": source_bytes is not None and
            len(source_bytes) == plan.get("raw_size_bytes"),
        "frozen_plan_size_matches_manifest": frozen_bytes is not None and
            len(frozen_bytes) == plan.get("raw_size_bytes"),
        "bound_image_admitted": image_info is not None,
        "bound_image_hash_matches_inventory": image_info is not None and
            plan.get("image_sha256") == image_info.get("sha256"),
        "frozen_bound_image_matches_manifest": run_image is not None and
            run_image.is_file() and sha(run_image) == plan.get("image_sha256"),
    }
    if original_dir is not None:
        checks["original_bound_image_matches_manifest"] = (original_image is not None and
            original_image.is_file() and sha(original_image) == plan.get("image_sha256"))
    if frozen_bytes is not None:
        try:
            parsed = json.loads(frozen_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        checks["frozen_declaration_matches_manifest"] = (
            isinstance(parsed, dict) and parsed == plan.get("declaration"))
    else:
        checks["frozen_declaration_matches_manifest"] = False
    return {"applicable": True, "pass": all(checks.values()),
            "source_path": str(source) if source else None,
            "frozen_path": str(frozen.relative_to(run)) if frozen else None,
            "image": image_name, "checks": checks}


def implementation_checks(manifest: dict) -> dict:
    expected = manifest.get("implementation_sha256")
    rows = []
    if isinstance(expected, dict):
        for name, digest in sorted(expected.items()):
            relative = Path(name)
            safe = not relative.is_absolute() and ".." not in relative.parts
            path = REPO / relative if safe else None
            actual = sha(path) if path and path.is_file() else None
            rows.append({"file": name, "expected_sha256": digest, "actual_sha256": actual,
                         "exists": actual is not None, "matches_current_file": actual == digest})
    return {"recorded_count": len(rows), "pass": bool(rows) and
            all(row["matches_current_file"] for row in rows), "files": rows,
            "note": "A mismatch means this run used another code snapshot; replay against current code must be interpreted accordingly."}


def seed_provenance(run: Path, manifest: dict) -> dict:
    seed = manifest.get("seed")
    if not seed:
        return {"applicable": False, "pass": True}
    folder = run / "seed"
    prior = Path(seed.get("source", "")) if seed.get("source") else None
    proposal_path = folder / "proposal.json"
    prior_proposal = prior / "proposal.json" if prior else None
    prior_source = prior / "source_model.json" if prior else None
    prior_display = prior / "display_geometry.json" if prior else None
    checks = {
        "manifest_mode_is_import": seed.get("mode") == "previous_generated_proposal_recovery",
        "manifest_candidate_is_seed": seed.get("candidate") == "seed",
        "seed_proposal_present": proposal_path.is_file(),
        "prior_proposal_present": bool(prior_proposal and prior_proposal.is_file()),
        "prior_source_present": bool(prior_source and prior_source.is_file()),
        "prior_display_present": bool(prior_display and prior_display.is_file()),
    }
    checks["manifest_proposal_hash_matches_seed"] = (
        checks["seed_proposal_present"] and sha(proposal_path) == seed.get("proposal_sha256"))
    checks["prior_proposal_bytes_identical"] = (
        checks["seed_proposal_present"] and checks["prior_proposal_present"] and
        proposal_path.read_bytes() == prior_proposal.read_bytes())
    report_path, source_path, display_path = (folder / name for name in
                                              ("report.json", "source_model.json", "display_geometry.json"))
    checks["seed_report_present"] = report_path.is_file()
    checks["seed_source_present"] = source_path.is_file()
    checks["seed_display_present"] = display_path.is_file()
    if all(checks[key] for key in ("seed_report_present", "seed_source_present")):
        report, source = load(report_path), load(source_path)
        checks["report_provenance_matches_manifest_seed"] = report.get("provenance") == seed
        checks["source_provenance_matches_manifest_seed"] = (
            source.get("generation", {}).get("provenance") == seed)
        checks["seed_proposal_hash_matches_report"] = (
            checks["seed_proposal_present"] and sha(proposal_path) == report.get("proposal_sha256"))
    else:
        source = None
        for key in ("report_provenance_matches_manifest_seed", "source_provenance_matches_manifest_seed",
                    "seed_proposal_hash_matches_report"):
            checks[key] = False
    same_geometry = {}
    if source and checks["prior_source_present"]:
        previous = load(prior_source)
        for key in ("spaces", "boundaries", "openings", "connections", "floors",
                    "opening_hosts", "boundary_relations", "coordinate_system", "validation"):
            same_geometry[key] = key in source and key in previous and source[key] == previous[key]
        checks["source_geometry_sha256_identical"] = (
            source.get("source_geometry_sha256") is not None and
            source.get("source_geometry_sha256") == previous.get("source_geometry_sha256"))
    else:
        same_geometry = {key: False for key in
                         ("spaces", "boundaries", "openings", "connections", "floors",
                          "opening_hosts", "boundary_relations", "coordinate_system", "validation")}
        checks["source_geometry_sha256_identical"] = False
    checks["all_source_geometry_fields_identical"] = all(same_geometry.values())
    if checks["seed_display_present"] and checks["prior_display_present"]:
        actual, previous = load(display_path), load(prior_display)
        display_keys = (actual.keys() | previous.keys()) - {"source_model"}
        checks["display_geometry_identical_except_embedded_source_provenance"] = all(
            actual.get(key) == previous.get(key) for key in display_keys)
    else:
        checks["display_geometry_identical_except_embedded_source_provenance"] = False
    return {"applicable": True, "pass": all(checks.values()),
            "prior_candidate": str(prior) if prior else None,
            "checks": checks, "geometry_field_checks": same_geometry,
            "note": "Full source/display bytes may differ because this run regenerates provenance; the imported proposal bytes and geometric content are checked separately."}


def candidate_provenance(run: Path, candidate: str, manifest: dict) -> dict:
    if candidate == "seed":
        return {"mode": "seed_import", "pass": manifest.get("seed", {}).get("candidate") == "seed",
                "note": "The complete imported seed lineage is checked in seed_provenance."}
    folder = run / candidate
    report = load(folder / "report.json")
    source = load(folder / "source_model.json")
    provenance = report.get("provenance")
    checks = {"report_provenance_present": isinstance(provenance, dict) and bool(provenance),
              "source_provenance_matches_report":
                  source.get("generation", {}).get("provenance") == provenance,
              "run_manifest_hash_matches_provenance":
                  isinstance(provenance, dict) and
                  provenance.get("input_manifest_sha256") == sha(run / "inputs.json")}
    if isinstance(provenance, dict) and provenance.get("parent_candidate"):
        parent = run / provenance["parent_candidate"] / "proposal.json"
        checks["parent_proposal_present"] = parent.is_file()
        checks["parent_proposal_hash_matches_provenance"] = (
            parent.is_file() and sha(parent) == provenance.get("parent_proposal_sha256"))
    if isinstance(provenance, dict) and provenance.get("plan_input"):
        plan = provenance["plan_input"]
        saved = run / plan.get("plan_file", "")
        checks["plan_present"] = saved.is_file()
        checks["plan_hash_matches_provenance"] = saved.is_file() and sha(saved) == plan.get("plan_sha256")
    return {"mode": "candidate_generation", "pass": all(checks.values()), "checks": checks}


def verify(run: Path, original_dir: Path | None) -> dict:
    if not (run / "summary.json").is_file() or not (run / "agent_receipt.json").is_file():
        raise ValueError("run must be complete: summary.json and agent_receipt.json required")
    summary, manifest = load(run / "summary.json"), load(run / "inputs.json")
    candidate = (summary.get("delivery") or {}).get("candidate")
    inputs = HELPERS.input_checks(run, manifest, original_dir)
    seed = seed_provenance(run, manifest)
    plan = plan_provenance(run, manifest, original_dir)
    implementation = implementation_checks(manifest)
    transport = HELPERS.image_transport(run)
    usage = HELPERS.model_usage(run, summary)
    if candidate:
        replay = HELPERS.replay(run, candidate, manifest)
        origin = candidate_provenance(run, candidate, manifest)
    else:
        replay, origin = None, {"mode": "no_delivery", "pass": False}
    replay_keys = ("proposal_hash_matches_report", "source_hash_matches_report",
                   "replay_source_ready", "source_bytes_identical", "display_bytes_identical",
                   "report_counts_match_source")
    checks = {
        "candidate_delivered": bool(candidate),
        "all_frozen_inputs_match": bool(inputs) and all(
            row.get("frozen_matches") and row.get("size_matches", True) and
            row.get("original_matches", True) for row in inputs),
        "seed_import_lineage_valid": seed["pass"],
        "saved_plan_lineage_valid": plan["pass"],
        "implementation_matches_run_snapshot": implementation["pass"],
        "delivered_candidate_origin_valid": origin["pass"],
        "deterministic_replay_valid": bool(replay) and all(replay.get(key) is True for key in replay_keys),
        "saved_image_transport_valid": transport.get("stream_present") is True and
            bool(transport.get("comparisons")) and
            all(row.get("pixels_match") is True for row in transport["comparisons"]),
        "receipt_count_matches_summary": usage.get("receipt_count_matches_summary") is True,
        "reported_partial_cost_matches_summary": usage.get("reported_partial_cost_matches_summary") is True,
    }
    return {"schema_version": "completed_bim_run_verification_v1", "run": str(run),
            "candidate": candidate, "pass": all(checks.values()), "checks": checks,
            "input_checks": inputs, "seed_provenance": seed,
            "plan_provenance": plan, "implementation": implementation,
            "candidate_provenance": origin, "replay": replay,
            "image_transport": transport, "model_usage": usage,
            "limits": ["This proves saved inputs, source/display replay and selected returned-image transport, not drawing fidelity.",
                       "Ordinary view_image crops without a saved rendered counterpart are counted as unpaired, not pixel-verified.",
                       "A seed import is a recovery run; its source hash changes with provenance even when geometric content is identical."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--original-dir", type=Path, help="Original case_data for input-byte comparison")
    parser.add_argument("--out", type=Path, help="New report; default RUN/verification.json")
    args = parser.parse_args()
    run = args.run.resolve()
    result = verify(run, args.original_dir.resolve() if args.original_dir else None)
    out = (args.out or run / "verification.json").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"pass": result["pass"], "candidate": result["candidate"],
                      "report": str(out),
                      "saved_images_compared": len(result["image_transport"]["comparisons"])},
                     ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
