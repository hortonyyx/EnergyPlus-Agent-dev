"""Evaluate the finished sm25 F1 plan-reader probe offline."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
BRIDGE = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1b/scoring_bridge.py"
REFERENCE = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm25-L_anchor.json"
CASE, IMAGE = "sm25-L_anchor", "1f_view.png"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha(value: object, *, newline: bool = False) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                     allow_nan=False) + ("\n" if newline else "")
    return hashlib.sha256(raw.encode()).hexdigest()


def inside(path: Path, parent: Path) -> Path:
    path = path.resolve()
    try:
        path.relative_to(parent.resolve())
    except ValueError as error:
        raise ValueError(f"path escapes {parent}: {path}") from error
    return path


def import_bridge():
    spec = importlib.util.spec_from_file_location("plan_probe_scoring_bridge", BRIDGE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {BRIDGE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def diagnostic_trial(run: Path, original_sha: str):
    """Return a passed trial for review only; absence of submission still cannot pass."""
    found = []
    for receipt_path in sorted(run.glob("tasks/*/bim/trial_workspace/trial_receipts/trial_*.json")):
        receipt = load(receipt_path)
        workspace = receipt_path.parents[1]
        source = workspace / str(receipt.get("candidate")) / "source_model.json"
        image = workspace / "images" / IMAGE
        if (receipt.get("status") == "passed" and receipt.get("source_geometry_ready") is True
                and source.is_file() and sha(source) == receipt.get("candidate_source_sha256")
                and image.is_file() and sha(image) == original_sha):
            found.append((workspace, receipt_path, receipt, source))
    return found[-1] if found else (None, None, None, None)


def submitted_evidence(run: Path, result: dict[str, Any], submission_path: Path, original_sha: str):
    submission = load(submission_path)
    task_dir = submission_path.parents[1]
    record_path = task_dir / "reader_record.json"
    record = load(record_path)
    artifact_path = inside(run / record["artifact"]["path"], run)
    artifact = load(artifact_path)
    if not (record.get("status") == "completed" and record.get("role_id") == "plan_reader"
            and record.get("target") == "F1" and artifact == submission.get("artifact")):
        raise ValueError("submission differs from the completed F1 reader_record")
    if not (sha(artifact_path) == json_sha(artifact) == record["artifact"]["sha256"]
            and json_sha(artifact, newline=True) == submission.get("artifact_sha256")):
        raise ValueError("artifact hash differs from reader_record or submission")
    artifact_blob = inside(run / record["artifact"]["blob"]["uri"], run)
    record_blob = inside(run / record["record_blob"]["uri"], run)
    if artifact_blob.read_bytes() != artifact_path.read_bytes():
        raise ValueError("artifact differs from its immutable blob")
    if not (sha(record_blob) == record["record_blob"]["sha256"]
            and load(record_blob) == {key: value for key, value in record.items() if key != "record_blob"}):
        raise ValueError("reader_record differs from its immutable blob")

    validation = submission["validation"]
    if record.get("validation") != validation:
        raise ValueError("submission validation differs from reader_record")
    expected = {"path": record["artifact"]["path"], "artifact_sha256": record["artifact"]["sha256"],
                "record_blob_sha256": record["record_blob"]["sha256"],
                "plan_sha256": validation["plan_sha256"],
                "compiled_numeric_plan_sha256": validation["compiled_numeric_plan_sha256"],
                "candidate_source_sha256": validation["candidate_source_sha256"]}
    if result.get("accepted_artifact") != expected:
        raise ValueError("terminal accepted_artifact differs from durable reader evidence")

    workspace = submission_path.parent / "trial_workspace"
    receipt_path = inside(workspace / validation["receipt_file"], workspace)
    receipt = load(receipt_path)
    if not (validation.get("validation_passed") is True and receipt.get("status") == "passed"
            and receipt.get("source_geometry_ready") is True
            and sha(workspace / "images" / IMAGE) == original_sha):
        raise ValueError("submitted trial is not passed or its original image differs")
    if any(validation.get(key) != value for key, value in receipt.items()):
        raise ValueError("submission validation differs from the trial receipt")
    plan = inside(workspace / receipt["input_plan_file"], workspace)
    numeric = inside(workspace / receipt["compiled_numeric_plan_file"], workspace)
    source = inside(workspace / receipt["candidate"] / "source_model.json", workspace)
    if not (sha(plan) == receipt["plan_sha256"]
            and sha(numeric) == receipt["compiled_numeric_plan_sha256"]
            and sha(source) == receipt["candidate_source_sha256"]
            and load(numeric) == artifact["plan"]):
        raise ValueError("trial plan, numeric plan, source, or submitted plan hash mismatch")
    files = [submission_path, record_path, artifact_path, artifact_blob, record_blob,
             receipt_path, plan, numeric, source]
    return workspace, receipt_path, receipt, source, artifact_path, files


def semantic_gate(reference: dict[str, Any], conversion: dict[str, Any], scoring: dict[str, Any]):
    from shapely.geometry import LineString, Polygon

    floor = scoring["assigned_role_score"]["questions"][0]["raw"]["floors"][0]
    if any(key not in floor for key in ("exterior", "partitions", "rooms", "openings")):
        return {"status": "fail", "reason": "F1 semantic score is incomplete"}
    reference_floor = next(row for row in reference["plan_questions"] if row["floor_id"] == "F1")
    answer_floor = conversion["answer"]["plan_questions"][0]
    room_map = {row["candidate_id"]: row["reference_id"] for row in floor["rooms"].get("matches", [])
                if row.get("status") in {"pass", "minor"}}
    refs = {row["id"]: row for row in reference_floor["openings"]}
    answers = {row["id"]: row for row in answer_floor["openings"]}
    connections = []
    for match in floor["openings"].get("comparisons", []):
        ref, answer = refs[match["reference_id"]], answers[match["answer_id"]]
        mapped = [room_map.get(room) for room in answer["host_room_ids"]]
        span, cross = ref["span_m"], ref["cross_m"]
        line = LineString([(span[0], cross), (span[1], cross)] if ref["axis"] == "x"
                          else [(cross, span[0]), (cross, span[1])])
        tolerance = ref["tolerance_m"]["external_cross_m" if ref["exterior"] else "internal_cross_m"]
        reference_hosts = [room["id"] for room in reference_floor["rooms"]
                           if Polygon(room["polygon_m"]).boundary.distance(line) <= tolerance + 1e-9]
        passed = (None not in mapped and set(mapped) == set(reference_hosts)
                  and bool(answer["exterior"]) == bool(ref["exterior"]))
        connections.append({"reference_id": ref["id"], "candidate_id": answer["id"],
                            "mapped_candidate_hosts": mapped, "reference_hosts": reference_hosts,
                            "status": "pass" if passed else "fail"})
    components = {
        "rooms": floor["rooms"]["status"] in {"pass", "minor"},
        "walls": floor["exterior"]["status"] == floor["partitions"]["status"] == "pass",
        "openings": floor["openings"]["status"] == "pass",
        "connections": (len(connections) == len(refs) == len(answers)
                         and all(row["status"] == "pass" for row in connections)),
    }
    return {"status": "pass" if all(components.values()) else "fail", "components": components,
            "connection_comparisons": connections,
            "limits": ["Compilation/self-consistency alone is not acceptance.",
                       "Connections cover referenced doors/windows; elevations and unrepresented passage/open kinds are out of scope."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run, out = args.run.resolve(), args.out.resolve()
    if not run.is_dir() or out == run or run in out.parents:
        raise ValueError("--run must exist and fresh --out must be outside it")
    out.mkdir(parents=True, exist_ok=False)
    manifest, result = load(run / "probe_manifest.json"), load(run / "probe_result.json")
    if result.get("probe_status") not in {"passed", "failed"}:
        raise ValueError("probe_result has no terminal probe_status")
    task = manifest.get("task", {})
    if [task.get(key) for key in ("task_id", "role_id", "target", "image")] != [
        "plan_f1", "plan_reader", "F1", IMAGE,
    ]:
        raise ValueError("run is not the approved one-F1 probe")
    original = run / "original_input" / IMAGE
    if not original.is_file() or sha(original) != manifest.get("original_sha256"):
        raise ValueError("original differs from probe_manifest")

    submissions = sorted(run.glob("tasks/*/bim/reader_submission.json"))
    if len(submissions) > 1:
        raise ValueError("one-F1 probe has multiple submissions")
    submitted, evidence_error, files = bool(submissions), None, []
    if submitted:
        try:
            workspace, receipt_path, receipt, source, artifact_path, files = submitted_evidence(
                run, result, submissions[0], manifest["original_sha256"])
        except Exception as error:
            workspace = receipt_path = receipt = source = artifact_path = None
            evidence_error = f"{type(error).__name__}: {error}"
    else:
        workspace, receipt_path, receipt, source = diagnostic_trial(run, manifest["original_sha256"])
        artifact_path = None
        files = [path for path in (receipt_path, source) if path is not None]
    candidate_found = source is not None
    protected = list(dict.fromkeys([original, REFERENCE, run / "probe_manifest.json",
                                    run / "probe_result.json", *files]))
    before = {str(path): sha(path) for path in protected}
    role_evaluation, semantic = None, {"status": "not_scored"}
    visuals: dict[str, Any] = {"status": "not_generated"}

    if candidate_found and evidence_error is None:
        try:
            if submitted:
                bridge = import_bridge()
                conversion = bridge.convert_role_artifacts(
                    case=CASE, plan_artifact=artifact_path, plan_trial_source=source,
                    plan_trial_receipt=receipt_path, assigned_plan_floors=["F1"], assigned_elevation_facades=[])
                scored = bridge.score_scoped_answer(REFERENCE, conversion)
                scoring = {key: value for key, value in scored.items() if key != "complete_reference_score"}
                semantic = semantic_gate(load(REFERENCE), conversion, scoring)
                role_evaluation = {"conversion": conversion, "scoring": scoring, "source_semantics": semantic}
                write(out / "role_evaluation.json", role_evaluation)
            from scripts.dev.evaluate_run import display, overlays
            source_value = load(source)
            shown = overlays(workspace, source_value, out / "overlays")
            rendered = display(workspace, receipt["candidate"], source_value, out / "display")
            visuals = {"status": "generated", "viewer": str(out / "display/viewer.html"),
                       "plan_pngs": [str(out / "display" / name) for name in rendered["plans"]],
                       "original_overlays": [str(out / "overlays" / row["overlay"])
                                             for row in shown["plans"] if row.get("overlay")]}
        except Exception as error:
            evidence_error = f"{type(error).__name__}: {error}"

    after = {str(path): sha(path) for path in protected}
    hashes = {"algorithm": "sha256", "subjects": {"original": str(original),
              "candidate": str(source) if source else None, "reference": str(REFERENCE)},
              "files": {path: {"before": value, "after": after[path], "unchanged": value == after[path]}
                        for path, value in before.items()}, "all_unchanged": before == after}
    write(out / "hashes.json", hashes)
    assigned = (role_evaluation or {}).get("scoring", {}).get("assigned_role_score", {}).get("status", "not_scored")
    passed = bool(result["probe_status"] == "passed" and submitted and candidate_found
                  and evidence_error is None and assigned == semantic["status"] == "pass"
                  and hashes["all_unchanged"])
    status = ("pass" if passed else "no_submit_and_no_passed_candidate"
              if not submitted and not candidate_found else "no_submit" if not submitted
              else "no_passed_candidate" if not candidate_found else "fail")
    summary = {"schema_version": "plan_probe_offline_evaluation_v1", "run": str(run),
               "scope": {"assigned_plan_floors": ["F1"], "assigned_elevation_facades": []},
               "probe_status": result["probe_status"], "submission_present": submitted,
               "passed_trial_candidate_present": candidate_found,
               "candidate_use": "diagnostic_only" if candidate_found and not submitted else "submitted" if submitted else None,
               "acceptance": {"status": status, "passed": passed, "assigned_role_score": assigned,
                              "source_semantics": semantic["status"], "error": evidence_error},
               "visuals": visuals,
               "outputs": {"role_evaluation": str(out / "role_evaluation.json") if role_evaluation else None,
                           "hashes": str(out / "hashes.json")},
               "claims": {"submitted_by_evaluator": False, "whole_building_delivered": False,
                          "model_requests": 0, "complete_reference_score_used": False}}
    write(out / "summary.json", summary)
    print(json.dumps({"status": status, "passed": passed, "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
