"""Production-builder-backed B5 fixtures for historical zero-window tests."""
from __future__ import annotations

import json
from pathlib import Path

from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import (
    correction_target,
    ensure_corrected_geometry,
    parse_correction_draw,
)
from src.agent.correction.window_sources import build_verified_window_resolver_inputs
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import (
    OpeningEvidence,
    RequiredViewEntry,
    ViewManifest,
)


def empty_window_verified_inputs(geom_or_payload, *, capability_profile="orthogonal_polygon"):
    target = correction_target(capability_profile)
    producer = (
        parse_correction_draw(geom_or_payload, target)
        if isinstance(geom_or_payload, dict)
        else ensure_corrected_geometry(geom_or_payload)
    )
    if producer.schema_version != "3" or producer.windows:
        raise ValueError("empty_window_verified_inputs is only for zero-window v3 fixtures")
    entries = []
    readings = {}
    for rank, floor in enumerate(
        sorted(producer.floors, key=lambda row: row.z_floor), start=1
    ):
        input_id = f"plan-{rank}"
        expected_output_id = f"plan_{rank}_view"
        entries.append(RequiredViewEntry(
            input_id=input_id,
            source_image=f"case_data/{input_id}.png",
            image_sha256="a" * 64,
            view_type="plan",
            floor_ref=rank,
            declared_direction_token=None,
            direction_source="standard_assumption",
            direction_semantics="building_axis",
            semantics_source="case_metadata",
            building_view_direction=None,
            dimensioned=True,
            expected_output_id=expected_output_id,
            opening_evidence=OpeningEvidence(
                potentially_observable_claims=["existence", "host", "along", "width"],
            ),
        ))
        readings[input_id] = json.dumps({
            "image_kind": "plan", "strokes": [], "uncaptured": [],
        }, separators=(",", ":")).encode("utf-8")
    payload = {
        "view_manifest_schema_version": "1",
        "claims_vocab_version": "1",
        "generator_version": "1",
        "completeness_ruleset_version": "1",
        "case_id": "b5-zero-window-history",
        "case_metadata_sha256": "b" * 64,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    return build_verified_window_resolver_inputs(
        producer_draw=producer,
        raw_view_manifest_bytes=manifest.model_dump_json().encode("utf-8"),
        raw_reading_artifacts=readings,
        elevation_direction_facts=(),
    )


def finalize_empty_window_v3(
    geom_or_payload,
    *,
    vector_dir: Path,
    capability_profile="orthogonal_polygon",
):
    target = correction_target(capability_profile)
    marker = empty_window_verified_inputs(
        geom_or_payload, capability_profile=capability_profile
    )
    return finalize_correction_draw(
        geom_or_payload,
        vector_dir=vector_dir,
        verified_window_inputs=marker,
        target=target,
    )


__all__ = ["empty_window_verified_inputs", "finalize_empty_window_v3"]
