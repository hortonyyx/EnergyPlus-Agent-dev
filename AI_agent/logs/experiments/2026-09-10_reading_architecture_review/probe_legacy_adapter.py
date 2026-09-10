"""Diagnose existing legacy adaptation without LLMs or source edits.

Run from the repository root: python -m AI_agent.logs.experiments.
2026-09-10_reading_architecture_review.probe_legacy_adapter
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from src.agent.correction.evidence_adapters import adapt_legacy_reading_view
from src.agent.correction.wall_compiler import compile_wall_ir

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
SOURCES = (
    "case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/1f_view.json",
    "case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/0_reading/1f_view.json",
    "case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json",
)


def probe():
    results = []
    for relative in SOURCES:
        path = REPO / relative
        raw = path.read_bytes()
        artifact = adapt_legacy_reading_view(raw, input_id="1f_view", floor_ref="1", view_type="plan")
        compiled = compile_wall_ir(artifact, profile="exploratory")
        results.append({
            "path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
            "wall_claims": len(artifact.bundle.wall_claims),
            "source_basis_counts": dict(Counter(w.source_basis for w in artifact.bundle.wall_claims)),
            "opening_claims": len(artifact.bundle.opening_claims),
            "debts": [d.model_dump(mode="json") for d in artifact.bundle.evidence_debts],
            "compiled_walls": len(compiled.walls),
            "resolved_centerlines": sum(w.resolved_centerline is not None for w in compiled.walls),
            "open_item_kinds": dict(Counter(i.kind for i in compiled.open_items)),
            "open_items_with_candidates": sum(bool(i.candidates) for i in compiled.open_items),
            "completion": compiled.completion,
            "source_unchanged": path.read_bytes() == raw,
        })
    return {
        "scope": "Read-only adapt_legacy_reading_view -> compile_wall_ir; no model, GT, solver, injected decisions, or source edits. This is interface diagnosis, not case generation.",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
