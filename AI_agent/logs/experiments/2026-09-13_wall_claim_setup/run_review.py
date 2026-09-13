"""Bounded repair of previous model claims using originals and raw measurements."""
import json
from pathlib import Path
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

OLD = ROOT / "AI_agent/logs/experiments/2026-09-13_sm24_plan_observation"
OUT = ROOT / "AI_agent/logs/experiments/2026-09-13_sm24_wall_claim_review"

INSTRUCTION = """Perform a bounded correction review of ONLY the two previous model
wall hypotheses below. They are hypotheses, not reliable observations. The raw
pixel_profile records from that observer are also supplied unchanged. Check
whether each record actually covers and supports either claim; do not convert
zero or disconnected support into proof of a continuous wall. A failed colour
test also does not prove that no physical wall exists: inspect the original,
choose more appropriate evidence, and explain any change of interpretation.
For each of the two claims, return retain/revise/reject/uncertain, short drawing
evidence, and corrected original-pixel wall intervals and gaps where you can
establish them. Distinguish physical partitions from furniture, door/window
symbols and dimensions. If the claimed wall does not exist, do not invent a
replacement merely to populate a field. Explain the local space continuity
affected by each decision; do not enumerate all rooms or read elevations.
Use the remaining_seconds feedback. Limit investigation to these hypotheses,
then return a concise JSON object (at most 600 words) with claims and unresolved.
An honest partial result is useful. No GT, correct geometry or room counts are
provided. Do not build BIM in this observation task.

PREVIOUS MODEL CLAIMS AND ORIGINAL TOOL RECORDS:
"""

if __name__ == "__main__":
    OUT.mkdir(exist_ok=False)
    (OUT / "images").mkdir()
    response = json.loads((OLD / "response.json").read_text())
    ledger = json.loads(re.search(r"```json\s*(.*?)\s*```", response["result"], re.S).group(1))
    # Mechanical scope selection by orientation/order, never evaluation answers.
    claims = [r for r in ledger["partition_walls"] if "VERTICAL" in r["id"]][:2]
    records = [json.loads(line) for line in (OLD / "detail_01/tools.jsonl").read_text().splitlines()]
    profiles = [r for r in records if r["action"] == "pixel_profile"]
    evidence = {"previous_claims": claims, "previous_profile_records": profiles}
    dump(OUT / "prior_evidence.json", evidence)
    dump(OUT / "prior_evidence_provenance.json", {
        "selection": "first two partition_walls whose ID contains VERTICAL, retaining order; all original pixel_profile rows",
        "response_path": str(OLD / "response.json"), "response_sha256": digest(OLD / "response.json"),
        "tools_path": str(OLD / "detail_01/tools.jsonl"), "tools_sha256": digest(OLD / "detail_01/tools.jsonl"),
        "contains_evaluation": False,
    })
    name = "1f_view.png"
    target = OUT / "images" / name
    shutil.copy2(ROOT / "case_tests/e2e_tests/sm24_anchor/case_data" / name, target)
    with Image.open(target) as image:
        size = list(image.size)
    dump(OUT / "inputs.json", {
        "images": {name: {"size": size, "sha256": digest(target)}},
        "input_mode": "developer_scoped_previous_observation_repair",
        "only_input": "original plan plus previous model hypotheses and raw tool records; no BIM, GT or evaluation",
        "implementation_sha256": {"scripts/tool_scripts/run_bim_agent.py": digest(ROOT / "scripts/tool_scripts/run_bim_agent.py")},
    })
    question = INSTRUCTION + json.dumps(evidence, ensure_ascii=False)
    child, input_sha = prepare_detail_observation(Toolkit(OUT), question, [name], "detail_01", timeout_seconds=240)
    source = {"run": "detail_01", "input_sha256": input_sha, "images": {name: digest(target)}}
    deadline = json.loads((child / "inputs.json").read_text())["deadline_epoch"]
    receipt = subscription(child, f"Images: {[name]}\nQuestion: {question}", model="sonnet", name="detail_01",
                           readonly=True, timeout=deadline-time.time(), log_run=OUT,
                           receipt_context={"observation_source": source})
    result = receipt.get("result", {})
    response = {"actual_model": receipt.get("actual_model"), "timed_out": receipt.get("timed_out", False),
                "completed": bool(result) and not result.get("is_error", False) and not receipt.get("timed_out", False)
                             and receipt.get("returncode") == 0,
                "result": result.get("result", "No completed answer"), "observation_source": source}
    dump(OUT / "response.json", response)
    print(json.dumps(response, ensure_ascii=False, indent=2))
