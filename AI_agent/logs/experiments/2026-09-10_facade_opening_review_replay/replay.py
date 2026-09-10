"""Replay saved sm24 opening observations with manually declared facade scopes.

This writes only the requested receipt and never changes the source run.
Run from a repository checkout, for example:

python AI_agent/logs/experiments/2026-09-10_facade_opening_review_replay/replay.py \
  --run AI_agent/logs/experiments/2026-09-10_partial_inference_sm24_run01 \
  --out AI_agent/logs/experiments/2026-09-10_facade_opening_review_replay/replay_results.json
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.agent.geometry.bim_delivery import summarize_delivery
from src.agent.geometry.opening_review import review_openings


_FACADES = ("South", "North", "North", "South", "East", "East", "West")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True, help="saved partial-inference run directory")
    parser.add_argument("--out", type=Path, required=True, help="new diagnostic receipt path")
    args = parser.parse_args()
    source = json.loads((args.run / "candidate_01/source_model.json").read_text())
    saved = [json.loads(path.read_text()) for path in sorted((args.run / "opening_reviews").glob("review_*.json"))]
    if len(saved) != len(_FACADES):
        raise ValueError("expected the seven saved sm24 exterior observations")
    images = {row["image"]["name"]: {"size": row["image"]["size"], "sha256": row["image"]["sha256"]}
              for row in saved}
    reports = []
    for saved_review, facade in zip(saved, _FACADES):
        observation = copy.deepcopy(saved_review["observations"])
        observation["facade"] = facade  # Explicit diagnostic declaration, never inferred from the filename.
        report = review_openings(source, observation, images)
        report["review_file"] = saved_review["review_file"]
        reports.append(report)
    empty_west_door = {
        "floor_id": "F1", "kind": "door", "facade": "West", "image": "West_view.png",
        "coverage": "complete", "marks": [],
    }
    report = review_openings(source, empty_west_door, images)
    report["review_file"] = "diagnostic/west-door-empty.json"
    reports.append(report)
    delivery = summarize_delivery(source, reports)
    receipt = {
        "schema_version": "facade_opening_review_replay_v1",
        "diagnostic": "manual facade scope declaration over immutable saved observations",
        "source_model_sha256": source["source_model_sha256"],
        "reports": [{key: report[key] for key in
                     ("review_file", "review_scope", "model_opening_ids", "matched_opening_ids", "findings", "conclusion")}
                    for report in reports],
        "opening_review_scopes": delivery["opening_review_scopes"],
        "facade_review_scopes": delivery["facade_review_scopes"],
        "drawing_fidelity": delivery["drawing_fidelity"],
    }
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
