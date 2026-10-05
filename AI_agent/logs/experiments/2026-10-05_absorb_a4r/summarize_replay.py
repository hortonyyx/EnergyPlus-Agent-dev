"""Validate all replay evidence and aggregate the five offline variants."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    verification = json.loads((HERE / "archive_verification.json").read_bytes())
    wire_audit = json.loads((HERE / "wire_canonical_audit.json").read_bytes())
    assert wire_audit["requests"] == 207 and wire_audit["all_actual_wire_bytes_equal_canonical_bytes"]
    runs = [json.loads((HERE / "replay" / (r["run"] + ".json")).read_bytes())
            for r in verification["runs"]]
    assert sum(r["requests"] for r in runs) == 207
    for run in runs:
        assert run["variants"][0]["baseline_wire_identical"]
        baseline = run["variants"][0]["steps"]
        for variant in run["variants"]:
            assert variant["key_state_preserved"] and variant["context_limit_exceeded_requests"] == 0
            assert all(a["state_sha256"] == b["state_sha256"] and b["projected_state_preserved"]
                       and b["protected_messages_preserved"] >= 2
                       for a, b in zip(baseline, variant["steps"], strict=True))
    variants = []
    for i in range(5):
        rows = [r["variants"][i] for r in runs]
        value = {k: rows[0][k] for k in ("threshold", "ratio")}
        value.update({k: sum(r[k] for r in rows) for k in (
            "compactions", "estimated_uncached_input", "compaction_refill_estimate",
            "input_estimate_total", "removed_messages", "removed_images")})
        value["runs"] = [{k: row[k] for k in (
            "compactions", "estimated_uncached_input", "compaction_refill_estimate",
            "removed_messages", "removed_images", "removed_categories", "max_wire_reservation_tokens")}
            | {"run": run["run"]} for run, row in zip(runs, rows, strict=True)]
        variants.append(value)
    for value in variants:
        value["estimated_miss_change_percent"] = round(
            (value["estimated_uncached_input"] / variants[0]["estimated_uncached_input"] - 1) * 100, 3)
    report = {"model_requests": 0, "historical_requests": 207, "projected_requests": 1035,
        "baseline_requests_identical": 207, "all_key_state_and_pins_preserved": True,
        "all_sent_machine_states_identical_to_recorded_state": True,
        "context_limit_violations": 0, "variants": variants, "defaults_changed": False,
        "decision": "Keep 150000/0.60. Lower retention is promising in an ideal-prefix estimate "
                    "but removes additional recent reasoning/results; these fixed responses cannot "
                    "establish building-quality retention or actual provider-cache savings.",
        "evidence_sha256": {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted((HERE / "replay").glob("*.json"))}}
    (HERE / "compaction_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("historical_requests", "projected_requests", "defaults_changed")}))


if __name__ == "__main__":
    main()
