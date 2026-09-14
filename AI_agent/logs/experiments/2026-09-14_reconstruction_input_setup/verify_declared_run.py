"""Verify declaration transport and input provenance after the real model run ends."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    assert (run / "summary.json").exists(), "Wait for generation to finish"
    manifest = json.loads((run / "inputs.json").read_text())
    supplied = manifest["building_input"]
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data/testdata_prompt.json"
    stream = run / "agent_stream.jsonl"
    opener = open
    if not stream.exists():
        stream = stream.with_suffix(".jsonl.gz")
        opener = gzip.open
    calls, inputs_received = {}, []
    with opener(stream, "rt") as handle:
        for line in handle:
            event = json.loads(line)
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls[block["id"]] = block
                if block.get("type") != "tool_result":
                    continue
                call = calls.get(block.get("tool_use_id"), {})
                if call.get("name", "").split("__")[-1] != "inputs" or block.get("is_error"):
                    continue
                for content in block.get("content", []):
                    if content.get("type") == "text":
                        inputs_received.append(json.loads(content["text"]))
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    provenance = []
    for path in sorted(run.glob("candidate_*/source_model.json")):
        report = json.loads((path.parent / "report.json").read_text())
        source = json.loads(path.read_text())
        provenance.append({
            "candidate": path.parent.name,
            "report_binds_declared_manifest": report["provenance"]["input_manifest_sha256"] == digest(run / "inputs.json"),
            "source_binds_same_provenance": source.get("generation", {}).get("provenance") == report["provenance"],
            "source_provenance": source.get("generation", {}).get("provenance", {}),
        })
    checks = {
        "original_json_bytes_preserved": original.read_bytes() == (run / "building_input.json").read_bytes(),
        "original_json_digest_preserved": digest(original) == supplied["raw_sha256"],
        "model_received_full_declaration": bool(inputs_received) and all(
            received["building_input"] == supplied for received in inputs_received),
        "model_received_exact_image_inventory": bool(inputs_received) and all(
            received["images"] == manifest["images"] for received in inputs_received),
        "no_seed_supplied": not (run / "seed").exists() and not manifest["input_contents"]["saved_generated_proposal"]["included"],
        "all_saved_candidates_bind_input_manifest": bool(provenance) and all(
            row["report_binds_declared_manifest"] and row["source_binds_same_provenance"] for row in provenance),
    }
    report = {"checks": checks, "all_checks_passed": all(checks.values()),
        "input_response_count": len(inputs_received), "candidate_provenance": provenance,
        "action_counts": dict(Counter(row["action"] for row in rows)),
        "viewed_originals": sorted({row["data"]["name"] for row in rows if row["action"] == "view_image"}),
        "limits": "Actual runtime transport and saved input provenance. Includes the original thermal_zones declaration; no prior contour-probe response or seed supplied. Does not certify correct use of declarations or drawing fidelity."}
    dump(run / "declaration_execution_audit.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert all(value for key, value in checks.items() if key != "all_saved_candidates_bind_input_manifest")
    assert not provenance or checks["all_saved_candidates_bind_input_manifest"]


if __name__ == "__main__":
    main()
