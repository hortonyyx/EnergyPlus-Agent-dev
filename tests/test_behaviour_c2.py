"""The same behaviour measures for both transports, including domain failures."""
import gzip
import json
from pathlib import Path

from src.agent.runtime_behaviour import load_behaviour, tool_result_data, write_behaviour_report


def test_metadata_survives_time_tail_and_transport_wrappers():
    data = {"name": "North.png", "display_scale_actual": [2, 2], "original_size": [900, 600]}
    text = json.dumps(data) + '\n已用 40 分钟；剩余 60 分钟。'
    forms = [text, {"content": [{"type": "text", "text": text}]},
             {"structuredContent": data, "content": [{"type": "text", "text": text}]},
             {"tool_message": {"content": json.dumps({"content": [{"type": "text", "text": text}]})}}]
    assert all(tool_result_data(value) == data for value in forms)
    truncated = '{"candidate":"candidate_04","source_geometry_ready":true,"evidence":['
    assert tool_result_data(truncated) == {"candidate": "candidate_04", "source_geometry_ready": True,
                                          "_partial_json": True}


def test_saved_claims_domain_outcomes_and_unanswered_calls_are_not_conflated(tmp_path):
    run = tmp_path / "run"
    (run / "claims").mkdir(parents=True)
    claim = {"candidate": "candidate_01", "objects": [{"kind": "window", "id": "W1"}],
             "values": {"z": [1, 2]}, "reason": "own chain"}
    saved = {"id": "claim_0001", "claim": claim, "sources": [{"image": "West.png"}],
             "resolved_values": {"z": [1, 2]}}
    (run / "claims/claim_0001.json").write_text(json.dumps(saved))
    steps = []
    def add(tool, data, *, error=False, args=None):
        steps.append(dict(index=len(steps)+1, t_call=len(steps), tool=tool, arguments=args or {},
                          result_text=json.dumps(data)+'\n剩余 1 分钟。', is_error=error,
                          model_text_before="", thinking_tokens_before=0))
    add("view_image", {"name": "West.png", "display_scale_actual": [2, 2]}, args={"name": "West.png"})
    add("build_plan_bim", {"status": "error", "source_geometry_ready": False})
    add("revise_plan_bim", {"candidate": "candidate_01", "source_geometry_ready": True})
    add("record_claim", {"id": "claim_0001", "sources": [{"image": "wrong-return.png"}]},
        args={"claim_json": json.dumps(claim)})
    add("revise_bim", {"status": "error"}, error=True)
    add("build_bim", {"candidate": "candidate_02", "source_geometry_ready": False})
    (run / "candidate_02").mkdir()
    (run / "candidate_02/report.json").write_text('{"source_geometry_ready": false}')
    # Reading a failed candidate is a successful inspection, not another failed build.
    add("inspect_candidate", {"candidate": "candidate_02", "report": {"source_geometry_ready": False}})
    record = dict(run="fixture", receipt={}, invocations=[dict(invocation=1, stream="archive", steps=steps)])
    archive = tmp_path / "record.json.gz"
    with gzip.open(archive, "wt") as stream:
        json.dump(record, stream)
    loaded = load_behaviour(archive, source_root=run)
    summary = loaded["summary"]
    assert (summary["call_errors"], summary["domain_failures"], summary["usable_source_drafts"]) == (1, 2, 1)
    assert summary["first_build_attempt_s"] == 1 and summary["first_draft_s"] == 2
    assert summary["full_views_before_first_build_attempt"] == 1
    assert summary["height_provenance_claims"][0]["sources"] == ["West.png"]
    assert summary["height_provenance_claims"][0]["evidence_capture"] == "saved_claim_file"
    assert summary["claims_from_saved_files"] == 1
    assert '剩余 1 分钟' in loaded["invocations"][0]["steps"][0]["result_text"]
    out = tmp_path / "reports"
    write_behaviour_report(archive, out, source_root=run)
    assert "调用报错 | 领域未成功 | 可用源稿" in (out/"timeline.md").read_text()
