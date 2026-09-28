"""Summarize completed public evidence; no model calls or quality threshold changes."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import statistics

load = lambda path: json.loads(path.read_text())


def distribution(values):
    return dict(n=len(values), min=min(values), median=statistics.median(values), max=max(values)) if values else None


def summarize(run):
    receipt = load(run / "agent_receipt.json")
    assert receipt["returncode"] == 0 and not receipt["result"]["is_error"]
    report = load(run / "postrun_audit.json")
    audit = importlib.import_module("AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.audit")
    physical = importlib.import_module("AI_agent.logs.experiments.2026-09-28_behavior_resume.review_saved").physical
    actions = audit.calls(run / "agent_stream.jsonl.gz")
    original = report["original_openings"]
    multiplicity = Counter(sid for floor in original.get("floors", [])
        for ids in floor["space_identity_by_interior_point"].values() for sid in ids)
    ambiguous = {sid for sid, count in multiplicity.items() if count > 1}
    independent = [row for row in original.get("comparisons", []) if not (set(row["expected_hosts"]) & ambiguous)]
    partition = load(run / "evaluation/gt" / f'{report["candidate"]}_partition.json')["comparison"]
    versions, previous = [], None
    for path in sorted(run.glob("candidate_*/source_model.json")):
        source = load(path)
        current = physical(source)
        versions.append(dict(candidate=path.parent.name,
            counts={k: len(source[k]) for k in ("floors", "spaces", "openings", "connections")},
            physical_fields_changed=None if previous is None else [k for k in current if current[k] != previous[k]]))
        previous = current
    result = dict(run=run.name, arm=load(run / "experiment_condition.json")["arm"],
        completed=True, actual_model=receipt["actual_model"], effort=receipt["effort"],
        elapsed_seconds=report["elapsed_seconds"], estimated_usd_not_bill=report["estimated_usd_not_bill"],
        usage={key: receipt["result"].get("usage", {}).get(key) for key in
            ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")},
        counts=report["counts"], strict_partition_status=partition["status"],
        partition_finding_codes=dict(Counter(row["code"] for row in partition["findings"])),
        boundary_hausdorff_m=distribution([row["boundary_hausdorff_m"] for row in partition["matches"]]),
        original_positions=original.get("positions"), original_reference_count=original.get("reference_count"),
        original_hosts_raw=original.get("hosts"), original_connections_raw=original.get("door_connections"),
        ambiguous_space_ids=sorted(ambiguous),
        hosts_with_unique_room_identity=sum(row["host_match"] for row in independent),
        connections_with_unique_room_identity=sum(row["connection_match"] is True for row in independent),
        endpoint_error_m=distribution([row["max_endpoint_error_m"] for row in original.get("comparisons", [])]),
        perpendicular_error_m=distribution([row["perpendicular_error_m"] for row in original.get("comparisons", [])]),
        exterior_parameters_match=report["exterior_parameters_match"], height_mismatches=report["height_mismatches"],
        public_tool_counts=dict(Counter(row["tool"] for row in actions)),
        errors=[row for row in actions if row.get("is_error") or row.get("returned_error")],
        first_build_ordinal=next((row["ordinal"] for row in actions if row["tool"] == "build_plan_bim"), None),
        measurement_binding_files=[str(path.relative_to(run)) for path in sorted(run.glob("plan_drafts/*/measurement_bindings.json"))],
        source_versions=versions,
        limits=["Raw original host counts may hide merged reference rooms; unique-room counts exclude those correspondences.",
                "One sample per arm; descriptive method-package comparison, not stability or causal proof.",
                "Tool access, references, claims and confirmations do not establish drawing truth.",
                "Continuous errors supplement the unchanged strict scores; they do not replace object review."])
    (run / "comparison_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("errors", "source_versions", "height_mismatches", "limits")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    summarize(parser.parse_args().run.resolve())
