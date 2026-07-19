"""B5 Phase-D legacy semantic and version-gated byte locks."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import re

import pytest

from src.agent.correction.artifact_serialization import serialize_correction_output
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import CorrectionTarget, correction_target
from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import (
    building_geometry_json,
    geometry_specs_markdown,
    serialize_geometry,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "c2_b5_legacy_window_byte_sha256.json"


def _payload(version: str, *, shifted: bool = False, extra: dict | None = None):
    lo = 0.004 if shifted else 0.0
    hi_x = 4.004 if shifted else 4.0
    hi_y = 3.004 if shifted else 3.0
    cell = {"id": "A", "x": [lo, hi_x], "y": [lo, hi_y]}
    if version == "2":
        cell["polygon"] = [[lo, lo], [hi_x, lo], [hi_x, hi_y], [lo, hi_y]]
    window = {
        "id": "W1", "floor": "F1", "facade": "South",
        "span": [-0.006, 1.0] if shifted else [1.0, 2.0],
        "z": [1.0, 2.0], "room": "A",
    }
    window.update(extra or {})
    return {
        "schema_version": version,
        "footprint_x": [0.0, 4.0], "footprint_y": [0.0, 3.0],
        "floors": [{
            "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "cells": [cell],
        }],
        "windows": [window],
    }


def _target(version: str):
    return (
        correction_target("rectangular")
        if version == "1"
        else CorrectionTarget("2", CorrectedGeometry, "orthogonal_polygon")
    )


def _chain(version: str, tmp_path: Path, *, payload=None, tol=None):
    result = finalize_correction_draw(
        payload or _payload(version),
        vector_dir=tmp_path,
        target=_target(version),
        tol=tol,
    )
    bg = build_geometry(
        result.geom,
        capability_profile="rectangular" if version == "1" else "orthogonal_polygon",
    )
    zone, surface, fenestration, _used = serialize_geometry(
        bg, geometry_contract="legacy",
    )
    return result, bg, {
        "output": serialize_correction_output(result.geom),
        "build": building_geometry_json(bg, geometry_contract="legacy").encode("utf-8"),
        "spec": geometry_specs_markdown(
            zone, surface, fenestration, geometry_contract="legacy",
        ).encode("utf-8"),
        "audit": json.dumps(
            result.audit_payload, indent=2, ensure_ascii=False,
        ).encode("utf-8"),
    }


@pytest.mark.parametrize("version", ["1", "2"])
def test_d4_legacy_full_chain_semantics_and_nit4_frozen_window_bytes(
    version: str, tmp_path: Path,
):
    expected = json.loads(_FIXTURE.read_text(encoding="utf-8"))[f"v{version}"]
    result, bg, artifacts = _chain(version, tmp_path)
    assert result.window_host_claims is None
    assert result.window_evidence_ledger is None
    assert result.verified_window_resolver_inputs is None
    assert result.prepared_candidate_identity is None
    assert bg.geometry_contract == "legacy"
    assert len(bg.windows) == 1
    assert {
        key: hashlib.sha256(value).hexdigest() for key, value in artifacts.items()
    } == expected


@pytest.mark.parametrize("version", ["1", "2"])
def test_d4_window_pass_stays_after_structural_snap(version: str, tmp_path: Path):
    result = finalize_correction_draw(
        _payload(version, shifted=True),
        vector_dir=tmp_path,
        target=_target(version),
    )
    assert result.geom.floors[0].cells[0].x == [0.0, 4.0]
    assert result.geom.windows[0].span == [0.0, 1.0]


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize(
    "extra",
    [
        {"facade_segment_id": "looks-valid"},
        {"facade_segment_id": 17, "host_resolution_sha256": "fake"},
    ],
)
def test_d4_legacy_ignores_v3_only_window_extras(
    version: str, extra: dict, tmp_path: Path,
):
    base, base_bg, base_artifacts = _chain(version, tmp_path / "base")
    changed, changed_bg, changed_artifacts = _chain(
        version, tmp_path / "changed", payload=_payload(version, extra=extra),
    )
    assert changed_bg == base_bg
    assert changed_artifacts == base_artifacts


@pytest.mark.parametrize("version", ["1", "2"])
def test_d4_window_clamp_false_retains_legacy_switch_semantics(version: str, tmp_path: Path):
    tol = dataclasses.replace(load_core_tolerances(), window_clamp_to_parent=False)
    result = finalize_correction_draw(
        _payload(version, shifted=True),
        vector_dir=tmp_path,
        target=_target(version),
        tol=tol,
    )
    assert result.geom.windows[0].span == [-0.01, 1.0]


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize(
    ("case", "room", "message"),
    [
        ("missing_room", None, "window W1: room 'None' not found; skipped"),
        ("no_parent", "NO_SUCH_ROOM", "window W1: room 'NO_SUCH_ROOM' not found; skipped"),
    ],
)
def test_d4_missing_room_and_no_parent_keep_legacy_failure_and_note_semantics(
    version: str, case: str, room: str | None, message: str, tmp_path: Path,
):
    payload = _payload(version)
    if case == "missing_room":
        payload["windows"][0].pop("room")
    else:
        payload["windows"][0]["room"] = room
    finalized = finalize_correction_draw(
        payload,
        vector_dir=tmp_path,
        target=_target(version),
    )
    assert finalized.geom.windows[0].room == room
    with pytest.raises(
        ValueError,
        match=re.escape(f"window attachment lost 1 of 1 window(s): {message}"),
    ):
        build_geometry(
            finalized.geom,
            capability_profile=(
                "rectangular" if version == "1" else "orthogonal_polygon"
            ),
        )


@pytest.mark.parametrize("version", ["1", "2"])
def test_d4_legacy_integrated_and_stepwise_full_chain_are_semantically_equal(
    version: str, tmp_path: Path,
):
    payload = _payload(version)
    integrated_result, integrated_bg, integrated_artifacts = _chain(
        version, tmp_path / "integrated", payload=payload,
    )
    parsed = CorrectedGeometry.model_validate(payload)
    stepwise_result, stepwise_bg, stepwise_artifacts = _chain(
        version, tmp_path / "stepwise", payload=parsed,
    )
    assert integrated_result.geom == stepwise_result.geom
    assert integrated_result.window_host_claims is stepwise_result.window_host_claims is None
    assert integrated_result.window_evidence_ledger is stepwise_result.window_evidence_ledger is None
    assert integrated_result.prepared_candidate_identity is stepwise_result.prepared_candidate_identity is None
    assert integrated_bg == stepwise_bg
    assert integrated_artifacts == stepwise_artifacts
