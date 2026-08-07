"""F-9 root fix (2026-08-07 dispatch): the correction LLM's `source_ids`
citations for the North/West (mirrored, `_BASE_SIGN=-1`) elevation channel
kept swapping a window with its mirror twin — the real crash fixture
(`tests/fixtures/f9_window_host_crash/`, a byte-for-byte trim of
`run_2026-08-05_f7_verify_sonnet`) shows exactly this: all four
`source_geometry_mismatch` conflicts are a window citing the OTHER window's
elevation stroke (see the dispatch's A1 table). `_BASE_SIGN` and the
North/West sign convention are user-ratified (2026-08-05) and are NOT touched
here (A2).

B-1 (dispatch, verified before this fix landed): the real transform is
``world = along_origin + sign * local``, with ``along_origin = lo if sign>0
else hi``. Under this project's world-coordinate invariant (origin = the
overall bounding box's SW corner) and the current single-shared-footprint
architecture, ``lo == 0`` for every facade family's along-axis, so
``along_origin`` collapses to ``{0, W}`` where ``W`` is that facade's OWN
along-axis overall dimension — already present in the reading artifact's own
dimension chain, independent of any correction draw. So the mirror flip can
be pre-applied at catalog-build time (before a draw exists), removing the
model's need to mentally apply it.

This file locks that fix at the unit level (`derive_observation_reference_catalog`
/ `format_observation_reference_catalog` in `window_sources.py`) with
HAND-COMPUTED interval constants (not re-derived through the function under
test) — never a self-referential comparison of the implementation's own
output to itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.window_sources import (
    ObservationReferenceCatalogEntry,
    derive_observation_reference_catalog,
    format_observation_reference_catalog,
)
from src.agent.execution.view_manifest import ViewManifest

_FIXTURE = Path("tests/fixtures/f9_window_host_crash")


def _load_fixture_catalog() -> tuple[ObservationReferenceCatalogEntry, ...]:
    raw_manifest = (_FIXTURE / "_run" / "view_manifest.json").read_bytes()
    manifest = ViewManifest.model_validate_json(raw_manifest)
    reading_dir = _FIXTURE / "0_reading"
    raw_readings = {
        entry.input_id: (reading_dir / f"{entry.expected_output_id}.json").read_bytes()
        for entry in manifest.required_entries()
    }
    return derive_observation_reference_catalog(
        raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=raw_readings,
    )


# =========================================================================== #
# Lock A — hand-computed interval math (B-1). North's own overall width is
# 15.0m (dimension D1/D7, role=overall, axis=x, both value_m=15.0, read
# directly off the fixture's North_view.json). North's base sign is -1
# (unmirrored: `facade.mirrored == "false"`, `local_x_positive` defaults to
# left-to-right). So the reduction is `world = 15.0 - local` for every North
# stroke. Hand-computed by hand from the fixture's own `x_range_m` values —
# NOT by calling the function under test a second time:
#   S5 local [1.24, 3.64]   -> world [15.0-3.64,  15.0-1.24]  = [11.36, 13.76]
#   S7 local [11.36, 13.76] -> world [15.0-13.76, 15.0-11.36] = [1.24, 3.64]
#   S3 local [1.95, 5.55]   -> world [15.0-5.55,  15.0-1.95]  = [9.45, 13.05]
#   S4 local [9.45, 13.05]  -> world [15.0-13.05, 15.0-9.45]  = [1.95, 5.55]
# =========================================================================== #
def test_f9_advisory_world_hint_matches_hand_computed_mirror_flip():
    entries = _load_fixture_catalog()
    by_ref = {entry.reference: entry.approx_world_along_interval for entry in entries}

    assert by_ref["North_view/S5"] == pytest.approx((11.36, 13.76), abs=1e-6)
    assert by_ref["North_view/S7"] == pytest.approx((1.24, 3.64), abs=1e-6)
    assert by_ref["North_view/S3"] == pytest.approx((9.45, 13.05), abs=1e-6)
    assert by_ref["North_view/S4"] == pytest.approx((1.95, 5.55), abs=1e-6)


# =========================================================================== #
# Lock B — the mirrored-facade lock the dispatch requires by name: each North
# window's OWN plan-declared span (read from the fixture's crashing
# `correction_geometry.json` — its `span` field came from the PLAN reading,
# which the dispatch's A1 confirms was correct; only the elevation citation
# was swapped) must overlap the SELF elevation stroke's advisory hint, and
# must NOT overlap the mirror twin's — the exact swap the crashing draw made.
# =========================================================================== #
_OWN_PLAN_SPAN = {
    "W-F1-N-1": (1.24, 3.64),
    "W-F1-N-3": (11.36, 13.76),
    "W-F2-N-1": (1.95, 5.55),
    "W-F2-N-2": (9.45, 13.05),
}


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def test_f9_own_plan_span_matches_fixture_crashing_draw():
    """Sanity anchor: the hand-picked `_OWN_PLAN_SPAN` constants above are
    not invented — they are exactly what the real crashing draw wrote as
    each window's own `span` (independently re-read from the fixture file,
    not from the catalog under test)."""
    payload = json.loads((_FIXTURE / "1_correction" / "correction_geometry.json").read_text(encoding="utf-8"))
    spans = {w["id"]: tuple(w["span"]) for w in payload["windows"] if w["id"] in _OWN_PLAN_SPAN}
    assert spans == _OWN_PLAN_SPAN


@pytest.mark.parametrize(
    "window_id,self_ref,mirror_twin_ref",
    [
        ("W-F1-N-1", "North_view/S7", "North_view/S5"),
        ("W-F1-N-3", "North_view/S5", "North_view/S7"),
        ("W-F2-N-1", "North_view/S4", "North_view/S3"),
        ("W-F2-N-2", "North_view/S3", "North_view/S4"),
    ],
)
def test_f9_north_window_pairs_to_self_not_mirror_twin(window_id, self_ref, mirror_twin_ref):
    entries = _load_fixture_catalog()
    by_ref = {entry.reference: entry.approx_world_along_interval for entry in entries}
    own_span = _OWN_PLAN_SPAN[window_id]

    self_hint = by_ref[self_ref]
    mirror_hint = by_ref[mirror_twin_ref]
    assert self_hint is not None and mirror_hint is not None

    self_overlap = _overlap(own_span, self_hint)
    mirror_overlap = _overlap(own_span, mirror_hint)
    # The window's own 2.4m-wide span must be (near-)fully covered by the
    # self stroke's hint and have ZERO overlap with the mirror twin's hint —
    # the crashing draw cited the mirror twin (zero overlap with its own span,
    # which is exactly why `source_geometry_mismatch` fired).
    assert self_overlap > 2.0, (window_id, self_ref, self_hint, own_span)
    assert mirror_overlap == 0.0, (window_id, mirror_twin_ref, mirror_hint, own_span)


# =========================================================================== #
# Lock C — wiring: the hint must actually reach the formatted prompt text
# (not just live in the dataclass), since that text is what
# `pipeline.py::_build_correction_prompt` actually inserts into the LLM
# prompt (F-7's existing `test_f7_build_observation_reference_catalog_from_run_reads_real_run_layout`
# already locks that `build_observation_reference_catalog_from_run` calls
# through to this same `format_observation_reference_catalog` text).
# =========================================================================== #
def test_f9_formatted_catalog_text_carries_the_self_hint_numbers():
    entries = _load_fixture_catalog()
    text = format_observation_reference_catalog(entries)
    line = next(line for line in text.splitlines() if line.startswith("- North_view/S7"))
    assert "1.24" in line and "3.64" in line
    line = next(line for line in text.splitlines() if line.startswith("- North_view/S5"))
    assert "11.4" in line and "13.8" in line  # %.3g rounding of 11.36/13.76
