"""Q1 rule selection and audit presentation for saved plan operations.

Only the trusted run manifest may select the historical replay policy. A plan
submitted by a model cannot opt out of the rules for a new operation.
"""
from __future__ import annotations

import copy
import hashlib
import json


CURRENT_RULE = "plan_regularization_v1"
LEGACY_RULE = "legacy"


def selected_rule(manifest):
    rule = manifest.get("plan_regularization_rule", CURRENT_RULE)
    if rule not in {CURRENT_RULE, LEGACY_RULE}:
        raise ValueError(f"unknown plan_regularization_rule: {rule!r}")
    return rule


def reject_source_proposal(toolkit, proposal):
    """Prepare a source-only hard-rule refusal before allocating a candidate.

    The caller is Toolkit.build. This helper never edits a source or the input
    proposal. Ordinary malformed inputs still use the exporter's existing error
    path; only a successfully constructed source is checked here.
    """
    if selected_rule(toolkit.manifest) == LEGACY_RULE:
        return None
    from src.agent.execution.source_proposal import _validate_proposal
    from src.agent.correction.schema import FootprintRing
    from src.agent.geometry.source_bim import build_source_bim
    from src.agent.geometry.building_precision import precision_report
    from src.agent.geometry.input_scale import check_geometry_scale
    from src.agent.execution.source_proposal import ensure_corrected_geometry

    try:
        geometry, _, _, enclosure = _validate_proposal(proposal)
        geom = ensure_corrected_geometry(copy.deepcopy(geometry))
        for floor in geom.floors:
            footprint = getattr(floor, "footprint", None)
            if isinstance(footprint, dict):
                floor.footprint = FootprintRing.model_validate(footprint)
        check_geometry_scale(geom.model_dump(mode="json"))
        source = build_source_bim(geom, capability_profile="orthogonal_polygon",
                                 enclosure_declaration=enclosure)
    except (ValueError, TypeError, KeyError):
        return None
    report = precision_report(source)
    if not report["items"]:
        return None
    folder = toolkit.run / "geometry_rejections"
    folder.mkdir(exist_ok=True)
    attempt = folder / f"attempt_{len(list(folder.glob('attempt_*'))) + 1:03d}"
    attempt.mkdir(exist_ok=False)
    full = {"rule_version": CURRENT_RULE, "status": "rejected", "changes": [],
            "rejections": report["items"], "hard_constraints": report}
    reference = save_report(attempt, full, toolkit.run)
    (attempt / "proposal.json").write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"status": "error", "source_geometry_ready": False,
            "error_stage": "source_hard_constraints",
            "error": "Source geometry violates the 0.30 m alignment or 0.60 m room-width rules; repair the listed objects before saving.",
            "regularization": reference, "remaining_seconds": toolkit.remaining_seconds()}


def report_sections(report):
    yield report
    for floor_id, floor_report in report.get("floor_reports", {}).items():
        for section in report_sections(floor_report):
            # Assembly may namespace/rename a floor from its original draft.
            yield {**section, "floor_id": floor_id,
                   "changes": [{**row, "floor_id": floor_id}
                               for row in section.get("changes", [])]}


def summary(report):
    sections = list(report_sections(report))
    changes = [row for section in sections for row in section.get("changes", [])]
    rejected = [row for section in sections for row in section.get("rejections", [])
                if row.get("type") != "floor_regularization_rejected"]
    attempted = [row for section in sections for row in section.get("attempted_changes", [])]
    if report.get("status") in {"rejected", "error"}:
        # A floor may have succeeded inside a rejected assembly. None of its
        # edits are delivered by that rejected top-level operation.
        attempted.extend(changes)
        changes = []
    distances = []
    for row in changes:
        for key in ("movement_m", "distance_m", "displacement_m", "delta_m"):
            value = row.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                distances.append(abs(value))
    return {
        "rule_version": report.get("rule_version", CURRENT_RULE),
        "status": report.get("status", "rejected" if rejected else "passed"),
        "moved_count": len(changes),
        "removed_strip_seed_count": sum(len(row.get("removed_space_seeds", [])) for row in changes),
        "merged_opening_count": sum(len(row.get("removed_opening_ids", [])) for row in changes),
        "attempted_change_count": len(attempted),
        "max_movement_m": max(distances, default=0.0),
        "rejected_count": len(rejected),
        "rejections": [
            {**{key: value for key, value in row.items()
                if key not in {"report", "before", "after", "hard_constraints", "attempted_changes",
                               "before_relationships", "after_relationships", "changed_legitimate_separations"}},
             **({"protected_separation_conflicts": len(row["changed_legitimate_separations"])}
                if row.get("changed_legitimate_separations") else {})}
            for row in rejected],
    }


def save_report(folder, report, run):
    path = folder / "regularization.json"
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return {"file": path.relative_to(run).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(), **summary(report)}


def compact_plan_input(record):
    compact = copy.deepcopy(record)
    if isinstance(compact.get("regularization"), dict):
        compact["regularization"] = summary(compact["regularization"])
    return compact


def source_reports(source):
    provenance = source.get("generation", {}).get("provenance", {})
    reports = []
    for name in ("plan_input", "plan_assembly"):
        report = provenance.get(name, {}).get("regularization")
        if isinstance(report, dict):
            reports.append(report)
    return reports


def collect_candidate_report(toolkit, candidate, source):
    """Keep the audit through later height/use edits without changing source BIM."""
    reports, seen = source_reports(source), {candidate}
    provenance = source.get("generation", {}).get("provenance", {})
    parent = provenance.get("parent_candidate")
    while not reports and parent and parent not in seen:
        seen.add(parent)
        path = toolkit.candidate_path(parent)
        sidecar = path / "regularization_report.json"
        if sidecar.is_file():
            inherited = json.loads(sidecar.read_text(encoding="utf-8"))
            reports = inherited.get("reports", [])
            break
        parent_source = json.loads((path / "source_model.json").read_text(encoding="utf-8"))
        reports = source_reports(parent_source)
        parent = parent_source.get("generation", {}).get("provenance", {}).get("parent_candidate")
    if not reports:
        return None
    result = {"rule_version": CURRENT_RULE, "reports": reports,
              "source_model_sha256": source.get("source_model_sha256"),
              "meaning": "Recorded geometric regularisation; original drawing fidelity remains unevaluated."}
    path = toolkit.candidate_path(candidate) / "regularization_report.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result
