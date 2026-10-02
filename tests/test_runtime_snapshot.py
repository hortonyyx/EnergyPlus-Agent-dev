"""Saved-source snapshot extraction, including a real BIM mutation counterexample."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.contracts import (
    BuildingObjectRef,
    FeatureDisposition,
    NormalizationProposal,
    ToleranceDecision,
)
from src.agent.runtime_snapshot import SnapshotDimensionSource, snapshot_source_bim


ROOT = Path(__file__).resolve().parents[1]
REAL_SOURCE = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/candidate_04/source_model.json"
)


def _internal_digest(source: dict) -> str:
    payload = dict(source)
    payload.pop("source_model_sha256", None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _write_source(path: Path, source: dict) -> None:
    source["source_model_sha256"] = _internal_digest(source)
    path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n")


def _unique_host_opening(source: dict) -> tuple[dict, dict]:
    counts: dict[str, int] = {}
    for opening in source["openings"]:
        host_id = opening["host_boundary_id"]
        counts[host_id] = counts.get(host_id, 0) + 1
    opening = next(
        row for row in source["openings"] if counts[row["host_boundary_id"]] == 1
    )
    boundary = next(
        row for row in source["boundaries"] if row["id"] == opening["host_boundary_id"]
    )
    return opening, boundary


def _translate_wall_and_optionally_opening(
    boundary: dict, opening: dict, *, move_opening: bool
) -> None:
    a, b = boundary["vertices"][:2]
    axis = 0 if abs(a[0] - b[0]) < abs(a[1] - b[1]) else 1
    for vertex in boundary["vertices"]:
        vertex[axis] += 0.05
    if move_opening:
        for vertex in opening["vertices"]:
            vertex[axis] += 0.05


def test_snapshot_reads_real_saved_bim_and_copies_selected_dimensions():
    source = json.loads(REAL_SOURCE.read_text())
    boundary_index = next(
        index
        for index, row in enumerate(source["boundaries"])
        if row["geometry_type"] == "wall"
    )
    boundary = source["boundaries"][boundary_index]
    selector = SnapshotDimensionSource(
        object_ref=BuildingObjectRef(kind="boundary", id=boundary["id"]),
        field_path="/vertices/0/0",
        source_pointer=f"/boundaries/{boundary_index}/vertices/0/0",
    )
    snapshot = snapshot_source_bim(
        REAL_SOURCE, model_version_id="sm25:saved", dimensions=(selector,)
    )
    assert snapshot.artifact_sha256 == hashlib.sha256(REAL_SOURCE.read_bytes()).hexdigest()
    assert len(snapshot.semantics.floor_ids) == 2
    assert len(snapshot.semantics.room_ids) == 29
    assert len(snapshot.semantics.openings) == len(source["openings"])
    assert snapshot.dimensions[0].value_m == boundary["vertices"][0][0]


def test_stale_absolute_opening_is_rejected_after_saved_host_moves(tmp_path):
    source = json.loads(REAL_SOURCE.read_text())
    opening, boundary = _unique_host_opening(source)
    opening_id = opening["id"]
    _translate_wall_and_optionally_opening(boundary, opening, move_opening=False)
    mutated = tmp_path / "stale-opening-source-model.json"
    _write_source(mutated, source)
    with pytest.raises(ValueError, match="do not lie on the saved host wall"):
        snapshot_source_bim(mutated, model_version_id="sm25:stale")
    assert opening_id in mutated.read_text()


def test_real_boundary_move_recomputes_opening_and_normalization_guard_detects_it(tmp_path):
    before = snapshot_source_bim(REAL_SOURCE, model_version_id="sm25:before")
    source = json.loads(REAL_SOURCE.read_text())
    opening, boundary = _unique_host_opening(source)
    opening_id = opening["id"]
    old = next(row for row in before.semantics.openings if row.opening_id == opening_id)
    _translate_wall_and_optionally_opening(boundary, opening, move_opening=True)
    mutated = tmp_path / "moved-host-and-opening-source-model.json"
    _write_source(mutated, source)
    after = snapshot_source_bim(mutated, model_version_id="sm25:after")
    new = next(row for row in after.semantics.openings if row.opening_id == opening_id)
    assert (new.p1, new.p2) != (old.p1, old.p2)

    with pytest.raises(ValidationError, match="changed walls, rooms, opening"):
        NormalizationProposal(
            proposal_id="regularisation:counterexample",
            check_ids=("check:geometry",),
            tolerance=ToleranceDecision(
                origin="tool_default",
                value=0.06,
                unit="m",
                source_id="runtime-snapshot-test",
                reason="test-only upper limit",
            ),
            features=(
                FeatureDisposition(
                    feature_id="feature:wall-shift",
                    classification="genuine_offset",
                    decision="preserve",
                    reason="a host and its opening moved, so this is not dimension-only",
                ),
            ),
            edits=(),
            before=before,
            after=after,
        )


def test_snapshot_rejects_bad_internal_hash_and_unsupported_saved_format(tmp_path):
    source = json.loads(REAL_SOURCE.read_text())
    source["spaces"][0]["height"] += 0.1
    bad_hash = tmp_path / "bad-hash.json"
    bad_hash.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="internal content hash"):
        snapshot_source_bim(bad_hash, model_version_id="bad")

    unsupported = tmp_path / "unknown.json"
    unsupported.write_text(json.dumps({"schema_version": "future_bim_v9"}))
    with pytest.raises(ValueError, match="source_bim_v1/v2"):
        snapshot_source_bim(unsupported, model_version_id="future")
