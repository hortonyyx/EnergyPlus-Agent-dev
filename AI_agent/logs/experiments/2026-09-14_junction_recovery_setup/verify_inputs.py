"""Verify the actual originals, recovery seed and unfiltered observation input."""
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
    run = parser.parse_args().run.resolve()
    assert (run / "summary.json").exists(), "Wait for generation to finish"
    setup = Path(__file__).resolve().parent
    frozen = json.loads((setup / "frozen_inputs.json").read_text())
    manifest = json.loads((run / "inputs.json").read_text())
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data"
    seed = Path(frozen["seed_proposal"]["file"])
    observation = Path(frozen["prior_observation"]["file"])
    stream = run / "agent_stream.jsonl"
    opener = open
    if not stream.exists():
        stream = stream.with_suffix(".jsonl.gz")
        opener = gzip.open
    calls, inputs_received, seed_received = {}, [], []
    with opener(stream, "rt") as handle:
        for line in handle:
            event = json.loads(line)
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls[block["id"]] = block
                if block.get("type") != "tool_result" or block.get("is_error"):
                    continue
                call = calls.get(block.get("tool_use_id"), {})
                name = call.get("name", "").split("__")[-1]
                if name not in {"inputs", "inspect_candidate"}:
                    continue
                for content in block.get("content", []):
                    if content.get("type") != "text":
                        continue
                    record = json.loads(content["text"])
                    if name == "inputs":
                        inputs_received.append(record)
                    elif call.get("input", {}).get("candidate", "seed") == "seed":
                        seed_received.append(record)
    scope = (setup / "scope.md").read_text()
    checks = {
        "five_originals_exact": len(manifest["images"]) == 5 and all(
            digest(run / "images" / name) == digest(original / name) == row["sha256"]
            for name, row in manifest["images"].items()),
        "original_declaration_exact": (run / "building_input.json").read_bytes()
            == (original / "testdata_prompt.json").read_bytes(),
        "scope_matches_frozen": manifest["scope"] == scope
            and digest(setup / "scope.md") == frozen["scope_sha256"],
        "observation_included_verbatim": observation.read_text() in scope
            and digest(observation) == frozen["prior_observation"]["sha256"],
        "all_old_profiles_included_verbatim": all(Path(name).read_text() in scope
            and digest(Path(name)) == sha for name, sha in frozen["prior_profiles"].items()),
        "seed_digest_matches_original": manifest["seed"]["proposal_sha256"]
            == digest(seed) == frozen["seed_proposal"]["sha256"],
        "seed_saved_without_content_change": json.loads((run / "seed/proposal.json").read_text())
            == json.loads(seed.read_text()),
        "model_received_exact_scope_and_declaration": bool(inputs_received) and all(
            r["scope"] == scope and r["building_input"] == manifest["building_input"]
            and r["images"] == manifest["images"] for r in inputs_received),
        "model_inspected_original_seed": bool(seed_received) and all(
            r["proposal"] == json.loads(seed.read_text()) for r in seed_received),
    }
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    report = {"checks": checks, "all_checks_passed": all(checks.values()),
        "inputs_response_count": len(inputs_received), "seed_inspection_count": len(seed_received),
        "action_counts": dict(Counter(r["action"] for r in rows)),
        "limits": "Assisted recovery: developer-selected local scope, prior seed and complete unfiltered old observation/profiles. No evaluation data or corrected geometry supplied. Input transport does not certify correct decisions."}
    dump(run / "input_execution_audit.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()
