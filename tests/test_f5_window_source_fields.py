"""F-5 locks: window-source field names pinned to the product contract.

BLOCKER fixed here — ``window_sources._window_strokes`` read ``x_range`` /
``y_range`` / ``z_range``, but the product contract (``schema.py:36`` Stroke.geometry
doc "rect: x_range_m/y_range_m"; ``guide.md:175,360`` "Elevation window strokes use
geometry.kind=rect + x_range_m / y_range_m") is ``x_range_m`` / ``y_range_m`` and
elevations have **no** ``z_range`` field. So any compliant windowed reading product
hit ``source_identity_invalid`` at 1_correction; the test fixtures had copied the
wrong spelling, so the whole repo stayed green while every real product died.

These locks pin the consumer to the contract's single source of truth and prove
real compliant products now flow:

* real-product lock — a real 07-07 sm21 window stroke (verbatim geometry values)
  yields non-empty intervals on BOTH channels, and elevation ``local_z_interval``
  is non-None (the sill/head evidence in ``y_range_m`` finally enters the chain —
  pre-F-5 it was always None because ``z_range`` does not exist);
* four-cell on real-scale payloads — {plan, elevation} x {compliant, field-missing};
  compliant products yield intervals, missing required fields fail-closed;
* structural lock — the consumer reads ONLY the contract field names (mechanically
  derived below), the stale spellings are gone from the consumer and the B5
  fixtures, and the contract source still declares the metric names.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.agent.correction import window_sources
from src.agent.correction.window_sources import (
    ElevationSourceWindowV1,
    PlanSourceWindowV1,
    WindowResolverInputError,
    _window_strokes,
)
from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry

H = "0" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]

# The product contract's SINGLE source of truth for window-rect geometry field
# names — mechanically derived from schema.py:36 ("rect: x_range_m/y_range_m")
# and guide.md:175,360 ("x_range_m / y_range_m"). The real-product fixtures below
# build geometry FROM this tuple (zip), never hand-copying the strings; the
# consumer reads exactly these names.
CONTRACT_RECT_FIELDS = ("x_range_m", "y_range_m")
# Stale spellings the BLOCKER lived on — must stay absent from consumer + fixtures.
_STALE_KEYS = re.compile(r'"(?:x|y|z)_range"\s*:')


def _entry(view_type: str) -> RequiredViewEntry:
    claims = (["existence", "host", "along", "width"] if view_type == "plan"
              else ["existence", "along", "width", "sill", "head", "appearance"])
    kwargs = dict(
        input_id=view_type, source_image=f"case_data/{view_type}.png", image_sha256=H,
        view_type=view_type, direction_source="standard_assumption",
        direction_semantics="building_axis", semantics_source="case_metadata",
        dimensioned=True, expected_output_id=view_type,
        opening_evidence=OpeningEvidence(potentially_observable_claims=claims),
    )
    if view_type == "plan":
        kwargs["floor_ref"] = 1
    else:
        kwargs["declared_direction_token"] = "South"
        kwargs["building_view_direction"] = "South"
    return RequiredViewEntry(**kwargs)


def _artifact(image_kind: str, strokes) -> bytes:
    return json.dumps(
        {"image_kind": image_kind, "strokes": list(strokes), "uncaptured": []},
        separators=(",", ":"),
    ).encode("utf-8")


def _rect(values: tuple[tuple[float, float], tuple[float, float]]) -> dict:
    """Build a contract rect geometry from the single-source field tuple."""
    return {"kind": "rect", **dict(zip(CONTRACT_RECT_FIELDS, values))}


def _real_plan_window() -> dict:
    # 07-07 sm21 product 1f_view S11 — verbatim geometry values.
    return {"id": "S11", "pen": "window", "geometry": _rect(([1.24, 3.64], [7.76, 8.0]))}


def _real_elevation_window() -> dict:
    # 07-07 sm21 product East_view S3 — verbatim geometry values; [4.0, 5.8] is
    # the sill->head vertical span that pre-F-5 never entered the chain.
    return {"id": "S3", "pen": "window", "geometry": _rect(([3.4, 4.6], [4.0, 5.8]))}


# =========================================================================== #
# Real-product lock — a compliant product flows on both channels (摘掉 F-5a 即红)
# =========================================================================== #
def test_plan_compliant_product_yields_world_intervals():
    """Real plan window (x_range_m/y_range_m) yields world intervals equal to the
    geometry. Neuter F-5a (read x_range again) ⇒ _interval(None) ⇒ fail-closed ⇒ red."""
    rows = list(_window_strokes(_artifact("plan", [_real_plan_window()]), _entry("plan")))
    assert len(rows) == 1
    assert isinstance(rows[0], PlanSourceWindowV1)
    assert (rows[0].world_x_interval.lo, rows[0].world_x_interval.hi) == (1.24, 3.64)
    assert (rows[0].world_y_interval.lo, rows[0].world_y_interval.hi) == (7.76, 8.0)


def test_elevation_compliant_product_yields_along_and_z_intervals():
    """Real elevation window yields the along-facade interval AND the vertical
    (sill/head) interval — the latter from y_range_m, which pre-F-5 was always None
    because z_range is not a contract field. Neuter F-5a ⇒ either interval reds."""
    rows = list(_window_strokes(_artifact("elevation", [_real_elevation_window()]), _entry("elevation")))
    assert len(rows) == 1
    assert isinstance(rows[0], ElevationSourceWindowV1)
    assert (rows[0].local_along_interval.lo, rows[0].local_along_interval.hi) == (3.4, 4.6)
    # The whole point of F-5a on the elevation branch: sill/head evidence enters.
    assert rows[0].local_z_interval is not None
    assert (rows[0].local_z_interval.lo, rows[0].local_z_interval.hi) == (4.0, 5.8)


# =========================================================================== #
# Four-cell — {plan, elevation} x {compliant, field-missing}; bad fails closed
# =========================================================================== #
@pytest.mark.parametrize("missing", ["x_range_m", "y_range_m"])
def test_plan_missing_required_field_fails_closed(missing):
    base = _real_plan_window()
    base["geometry"] = {k: v for k, v in base["geometry"].items() if k != missing}
    with pytest.raises(WindowResolverInputError, match="source_identity_invalid"):
        list(_window_strokes(_artifact("plan", [base]), _entry("plan")))


def test_elevation_missing_along_field_fails_closed():
    base = _real_elevation_window()
    base["geometry"] = {k: v for k, v in base["geometry"].items() if k != "x_range_m"}
    with pytest.raises(WindowResolverInputError, match="source_identity_invalid"):
        list(_window_strokes(_artifact("elevation", [base]), _entry("elevation")))


# =========================================================================== #
# Structural lock — consumer + fixtures pinned to the contract single source
# =========================================================================== #
def test_consumer_reads_only_contract_field_names():
    """The consumer source must read the contract field names and not the stale
    spellings. Catches any revert of F-5a."""
    src = Path(window_sources.__file__).read_text(encoding="utf-8")
    assert 'geometry.get("x_range_m")' in src
    assert 'geometry.get("y_range_m")' in src
    for stale in (
        'geometry.get("x_range")', 'geometry.get("y_range")', 'geometry.get("z_range")',
        'field="x_range"', 'field="y_range"', 'field="z_range"',
    ):
        assert stale not in src, f"stale spelling returned to the consumer: {stale}"


@pytest.mark.parametrize("rel", [
    "tests/test_c2_b5_host_resolution.py",
    "tests/test_c2_b5_source_routing.py",
    "tests/test_c2_b5_parent_and_verts.py",
    "tests/test_c2_b2b_envelope_transform.py",
    "tests/test_f5_window_source_fields.py",
])
def test_no_stale_geometry_field_spellings_in_fixtures(rel):
    """No window-geometry dict key in the B5 fixtures (or this lock file) may use
    the stale non-metric spellings — they must all use the contract's _m names."""
    offenders = []
    for i, line in enumerate((REPO_ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
        if _STALE_KEYS.search(line):
            offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, "stale geometry field spellings:\n" + "\n".join(offenders)


def test_contract_source_still_declares_metric_field_names():
    """The product contract (schema.py Stroke.geometry doc) still declares the
    metric field names — the single source the consumer + fixtures are pinned to.
    Catches a contract-side revert that would silently orphan the consumer."""
    schema_src = (REPO_ROOT / "src" / "agent" / "reading" / "schema.py").read_text(encoding="utf-8")
    assert "x_range_m" in schema_src and "y_range_m" in schema_src
