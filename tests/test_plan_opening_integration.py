"""Source openings survive the real correction writer and completeness gate."""
from __future__ import annotations

import copy
import dataclasses

import pytest

from scripts.tool_scripts.diagnose_reading_openings import record_candidate
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.schema import CorrectedGeometry
from src.agent.correction.window_host import derive_window_evidence_ledger, recompute_window_host_claims
from src.validator.checks.correction import check_correction


def _payload():
    return {
        "schema_version": "3", "footprint_x": [0, 8], "footprint_y": [0, 4],
        "floors": [{"id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
                    "footprint": {"vertices": [[0, 0], [8, 0], [8, 4], [0, 4]]},
                    "cells": [{"id": "room", "x": [0, 8], "y": [0, 4]}]}],
        "openings": [{"id": "entrance", "kind": "door", "space_id": "room", "other_space_id": None,
                      "p1": [1, 0], "p2": [2, 0], "z": [0, 2.1], "state": "open",
                      "source_refs": ["fixture:entrance"]}],
    }


@pytest.mark.parametrize("change", ["move", "close", "remove"])
def test_writer_rejects_changed_opening_even_when_candidate_sidecars_are_consistent(tmp_path, change):
    from b5_test_helpers import finalize_empty_window_v3

    original = finalize_empty_window_v3(_payload(), vector_dir=tmp_path)
    payload = copy.deepcopy(_payload())
    if change == "move":
        payload["openings"][0].update(p1=[2, 0], p2=[3, 0])
    elif change == "close":
        payload["openings"][0]["state"] = "closed"
    else:
        payload["openings"] = []
    changed = finalize_empty_window_v3(payload, vector_dir=tmp_path)
    marker = original.verified_window_resolver_inputs
    tol = load_core_tolerances()
    claims = recompute_window_host_claims(changed.geom, verified_inputs=marker, tolerances=tol)
    evidence = derive_window_evidence_ledger(
        changed.geom, host_claims=claims, verified_inputs=marker,
        candidate_identity=changed.prepared_candidate_identity, tolerances=tol,
    )
    forged = dataclasses.replace(changed, verified_window_resolver_inputs=marker,
                                 window_host_claims=claims, window_evidence_ledger=evidence)
    with pytest.raises(ValueError, match="writer_core_projection_drift"):
        record_candidate(tmp_path / "changed", forged)


def test_known_unbuilt_plan_opening_blocks_even_exploratory_correction():
    raw = _payload()
    raw["schema_version"] = "2"
    geom = CorrectedGeometry.model_validate(raw)
    geom.unsupported.append({"kind": "as_drawn_opening_unbuilt", "input_id": "plan",
                             "observation_ids": ["door-2"], "reason": "no_complete_host"})
    report = check_correction(geom, capability_profile="orthogonal_polygon", run_profile="exploratory")
    assert any(row.check_id == "correction.plan_opening_completeness" for row in report.blocking())


def test_opening_recipe_changes_replay_hash_without_changing_historical_recipe_bytes():
    from pathlib import Path
    from src.agent.correction.chain_provenance import (
        AsDrawnChainProvenanceV1, PlanWallOpeningPolicyV1, build_chain_provenance,
    )

    path = Path("case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/1_correction/attempts/001/chain_provenance.json")
    old = AsDrawnChainProvenanceV1.model_validate_json(path.read_bytes())
    rows = [{"input_id": r.input_id, "product_filename": r.product_filename, "floor_ref": r.floor_ref,
             "compilation_bytes": r.compilation_bytes, "source_bytes_sha256": r.source_bytes_sha256}
            for r in old.floors]
    rebuilt = build_chain_provenance(rows)
    assert rebuilt.model_dump(mode="json") == old.model_dump(mode="json")
    assert "wall_opening_policy" not in rebuilt.model_dump(mode="json")
    fresh = build_chain_provenance(rows, wall_opening_policy=PlanWallOpeningPolicyV1())
    taller = build_chain_provenance(rows, wall_opening_policy=PlanWallOpeningPolicyV1(assumed_height_m=2.2))
    assert len({old.replay_input_hash, fresh.replay_input_hash, taller.replay_input_hash}) == 3
    assert len({old.content_sha256, fresh.content_sha256, taller.content_sha256}) == 3
