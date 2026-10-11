"""Optional historical delivery review snapshots."""
import json
from tests.archive_paths import archive_path
from src.agent.geometry.bim_delivery import summarize_delivery
from tests.test_bim_delivery import _scope
RUN06 = archive_path("AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run06")
def _json(relative):
    return json.loads((RUN06 / relative).read_text(encoding="utf-8"))


def test_run06_candidate02_reports_two_follow_up_reviews_and_unreviewed_windows():
    source = _json("candidate_02/source_model.json")
    reviews = [_json("opening_reviews/review_001.json"), _json("opening_reviews/review_002.json")]

    summary = summarize_delivery(source, reviews)

    assert summary["source_validation"] == source["validation"]
    assert summary["counts"] == {"spaces": 14, "boundaries": 84, "openings": 28,
                                 "connections": 14, "unbuilt_openings": 0, "unsupported": 0}
    assert summary["generation"]["unresolved"] == source["generation"]["unresolved"]
    assert [row["review_ref"] for row in summary["current_reviews"]] == [
        "opening_reviews/review_001.json", "opening_reviews/review_002.json"]
    assert summary["stale_reviews"] == []
    assert _scope(summary, "F1", "door")["review_status"] == "observations_require_follow_up"
    assert _scope(summary, "F2", "door")["review_status"] == "observations_require_follow_up"
    assert _scope(summary, "F1", "window")["review_status"] == "not_reviewed"
    assert summary["drawing_fidelity"] == "not_evaluated"


def test_run06_candidate03_does_not_inherit_candidate02_reviews_after_notes_change():
    source = _json("candidate_03/source_model.json")
    reviews = [_json("opening_reviews/review_001.json"), _json("opening_reviews/review_002.json")]

    summary = summarize_delivery(source, reviews)

    assert summary["current_reviews"] == []
    assert [row["stale_reason"] for row in summary["stale_reviews"]] == [
        "source_model_sha256_mismatch", "source_model_sha256_mismatch"]
    assert all(row["review_status"] == "not_reviewed" for row in summary["opening_review_scopes"])
