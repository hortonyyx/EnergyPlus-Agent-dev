"""Reuse unchanged evaluation references after run58 completes."""
import importlib
import json

from .run_repeat import BASE, HERE, RUN
from scripts.tool_scripts.run_bim_agent import digest, dump


def main():
    assert (RUN / "summary.json").is_file(), "Wait for generation to finish"
    audit = importlib.import_module(
        "AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_run")
    audit.RUN, audit.HERE = RUN, HERE
    audit.main()
    original = importlib.import_module(
        "AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    original.audit(RUN)
    transport = importlib.import_module(
        "AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_transport")
    transport.audit(RUN)
    load = lambda p: json.loads(p.read_text())
    before, after = load(BASE / "inputs.json"), load(RUN / "inputs.json")
    assert before["scope"] == after["scope"]
    assert before["images"] == after["images"]
    assert before["implementation_sha256"] == after["implementation_sha256"]
    request_before, request_after = load(BASE / "agent_request.json"), load(RUN / "agent_request.json")
    assert request_before["system_prompt"] == request_after["system_prompt"]
    for key in ("provider", "requested_model", "effort", "timeout_seconds"):
        assert request_before[key] == request_after[key]
    reports = []
    for run in (BASE, RUN):
        delivery = load(run / "delivery.json")
        source = load(run / delivery["candidate"] / "source_model.json")
        proposal = load(run / delivery["candidate"] / "proposal.json")
        reports.append({
            "run": run.name, "candidate": delivery["candidate"],
            "postrun": load(run / "postrun_audit.json"),
            "original_openings": load(run / "evaluation/original_openings.json"),
            "source_model_sha256": source["source_model_sha256"],
            "assumptions": proposal.get("assumptions", []),
            "unresolved": proposal.get("unresolved", []),
        })
    dump(HERE / "comparison.json", {
        "same_six_images_scope_system_prompt_implementation_and_run_settings": True,
        "evaluation_original_reference_sha256": digest(original.HERE / "original_reference.json"),
        "runs": reports,
        "limits": ["Two independent runs on this case; not general stability.",
                   "Evaluation references and previous results were excluded from generation.",
                   "No human acceptance or downstream simulation verification."],
    })


if __name__ == "__main__":
    main()
