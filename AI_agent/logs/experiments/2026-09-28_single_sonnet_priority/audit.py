"""Read-only historical evidence; no model/network calls or BIM changes."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENTS = HERE.parent
BASELINE = "d4714173"


def main():
    rows = []
    for number in range(53, 59):
        matches = list(EXPERIMENTS.glob(f"*_run{number}"))
        assert len(matches) == 1, matches
        run = matches[0]
        receipt_path = run / "agent_receipt.json"
        summary_path = run / "summary.json"
        receipt = json.loads(receipt_path.read_text())
        summary = json.loads(summary_path.read_text())
        detail_requests = list(run.rglob("detail_*_request.json"))
        receipts = list(run.glob("*_receipt.json"))
        assert summary["agent_response_completed"] is True
        assert receipt["actual_model"] == "claude-sonnet-5"
        assert receipt["returncode"] == 0
        assert summary["subscription_invocations"] == 1
        assert len(receipts) == 1 and not detail_requests
        rows.append(dict(run=run.name, actual_model=receipt["actual_model"],
            effort=receipt["effort"], completed=True, subscription_invocations=1,
            detail_requests=0, receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            summary_sha256=hashlib.sha256(summary_path.read_bytes()).hexdigest()))
    restored = {}
    for name in ["scripts/tool_scripts/run_bim_agent.py", "src/agent/model_routes.py",
                 "src/agent/execution/chat_mcp.py"]:
        old = subprocess.check_output(["git", "show", f"{BASELINE}:{name}"], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        assert old == current, name
        restored[name] = hashlib.sha256(current).hexdigest()
    assert not (ROOT / "scripts/tool_scripts/bim_agent_api.py").exists()
    result = dict(historical_runs=rows, starting_commit=BASELINE,
        restored_production_sha256=restored, new_model_calls=0,
        limits="Single Sonnet plus deterministic tools; these receipts establish invocation composition, not universal quality or restored stability. Existing optional delegation and inactive role/API configuration remain available for later work.")
    (HERE / "evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(runs_checked=len(rows), all_single_sonnet=True,
                         production_files_restored=len(restored), new_model_calls=0)))


if __name__ == "__main__":
    main()
