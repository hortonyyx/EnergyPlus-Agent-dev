"""C2 B-M §4/§8: strict generator — determinism, hash discipline, sm21/sm20
dual-fixture full mapping, generation-time hard gates, entry-identity
negatives, and the direction three-axis matrix.

`build_view_manifest` is a pure function of case_dir on disk; every test here
either points at the real checked-in sm20/sm21/sm24 anchors (read-only) or
builds a small synthetic case under tmp_path (for tamper/negative scenarios
that must never touch the real fixtures)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.claims import (
    ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS,
    PLAN_POTENTIALLY_OBSERVABLE_CLAIMS,
)
from src.agent.execution.manifest import hash_bytes, hash_file
from src.agent.execution.view_manifest import (
    VIEW_MANIFEST_NAME,
    build_view_manifest,
    provision_view_manifest,
    verify_view_manifest,
)

SM21 = Path("case_tests/e2e_tests/sm21_anchor")
SM20 = Path("case_tests/e2e_tests/sm20_anchor")
SM24 = Path("case_tests/e2e_tests/sm24_anchor")


def _tiny_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _write_case(root: Path, testdata: dict, images: dict[str, bytes] | None = None) -> Path:
    """A minimal synthetic case: `root/case_data/{images...,testdata_prompt.json}`.
    `images` maps basename -> bytes; any name referenced by `testdata` but not
    given a byte payload gets a default tiny PNG."""
    case_data = root / "case_data"
    case_data.mkdir(parents=True, exist_ok=True)
    referenced: set[str] = set()
    for item in testdata.get("Floor plans") or []:
        referenced.add(Path(item["path"]).name)
    for key in (
        "South view path of the building", "North view path of the building",
        "East view path of the building", "West view path of the building",
        "Path of the supplementary plan example drawing for the building",
    ):
        if key in testdata:
            referenced.add(Path(testdata[key]).name)
    images = dict(images or {})
    for name in referenced:
        images.setdefault(name, _tiny_png())
    for name, data in images.items():
        (case_data / name).write_bytes(data)
    (case_data / "testdata_prompt.json").write_text(json.dumps(testdata), encoding="utf-8")
    return root


def _sm21_style_testdata(**overrides) -> dict:
    base = {
        "TestName": "synth",
        "Floor plans": [
            {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 7, "dimensioned": True},
        ],
        "dimensioned_views": ["1f_view", "South_view"],
        "South view path of the building": "case_data/South_view.png",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# §8.1 determinism
# --------------------------------------------------------------------------- #
def test_deterministic_across_two_builds():
    m1 = build_view_manifest(SM21)
    m2 = build_view_manifest(SM21)
    assert m1.model_dump_json() == m2.model_dump_json()


def test_absolute_path_never_appears_in_manifest_text():
    m = build_view_manifest(SM21)
    text = m.model_dump_json()
    assert "/workspaces" not in text
    for e in m.entries:
        assert not e.source_image.startswith("/")


def test_image_byte_change_only_changes_that_entry_and_top_hash(tmp_path: Path):
    case_dir = tmp_path / "sm21_copy"
    import shutil

    shutil.copytree(SM21, case_dir)
    before = build_view_manifest(case_dir)

    img = case_dir / "case_data" / "South_view.png"
    data = bytearray(img.read_bytes())
    data[0] ^= 0xFF
    img.write_bytes(bytes(data))
    after = build_view_manifest(case_dir)

    assert after.content_sha256 != before.content_sha256
    before_by_id = {e.input_id: e for e in before.entries}
    after_by_id = {e.input_id: e for e in after.entries}
    for input_id in before_by_id:
        if input_id == "South_view":
            assert after_by_id[input_id].image_sha256 != before_by_id[input_id].image_sha256
        else:
            assert after_by_id[input_id].image_sha256 == before_by_id[input_id].image_sha256


def test_atomic_write_leaves_no_partial_file_on_crash(tmp_path: Path, monkeypatch):
    import src.agent.execution.view_manifest as vm

    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    def _boom(*_a, **_kw):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(vm.os, "replace", _boom)
    with pytest.raises(OSError):
        provision_view_manifest(case_dir, run_dir)

    final_path = run_dir / "_run" / VIEW_MANIFEST_NAME
    assert not final_path.exists()
    # no orphan temp file left behind either
    leftovers = list((run_dir / "_run").glob(f".{VIEW_MANIFEST_NAME}.*")) if (run_dir / "_run").exists() else []
    assert leftovers == []


def test_case_metadata_hash_chain(tmp_path: Path):
    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    m = build_view_manifest(case_dir)
    raw = (case_dir / "case_data" / "testdata_prompt.json").read_bytes()
    assert m.case_metadata_sha256 == hash_bytes(raw)


def test_provision_is_idempotent_and_verify_agrees(tmp_path: Path):
    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    first = provision_view_manifest(case_dir, run_dir)
    second = provision_view_manifest(case_dir, run_dir)
    assert first.content_sha256 == second.content_sha256
    result = verify_view_manifest(case_dir, run_dir)
    assert result.ok
    assert result.on_disk.content_sha256 == first.content_sha256


def test_provision_raises_on_mid_run_case_data_change(tmp_path: Path):
    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    provision_view_manifest(case_dir, run_dir)

    img = case_dir / "case_data" / "1f_view.png"
    img.write_bytes(_tiny_png() + b"\x00")
    with pytest.raises(ValueError, match="drift"):
        provision_view_manifest(case_dir, run_dir)


# --------------------------------------------------------------------------- #
# §8.3 sm21 + sm20 dual fixture full mapping
# --------------------------------------------------------------------------- #
def test_sm21_six_view_full_mapping():
    m = build_view_manifest(SM21)
    by_id = {e.input_id: e for e in m.entries}
    assert set(by_id) == {"1f_view", "2f_view", "East_view", "North_view", "South_view", "West_view"}

    plans = {"1f_view": 1, "2f_view": 2}
    for input_id, floor in plans.items():
        e = by_id[input_id]
        assert e.kind == "required_view"
        assert e.view_type == "plan"
        assert e.floor_ref == floor
        assert e.dimensioned is True
        assert e.expected_output_id == input_id
        assert e.direction_source == "standard_assumption"
        assert e.direction_semantics == "building_axis"
        assert e.semantics_source == "standard_assumption"
        assert e.building_view_direction is None
        assert e.declared_direction_token is None
        assert sorted(e.opening_evidence.potentially_observable_claims) == sorted(PLAN_POTENTIALLY_OBSERVABLE_CLAIMS)
        assert e.opening_evidence.negative_evidence_capable_claims == []

    elevations = {"South_view": "South", "North_view": "North", "East_view": "East", "West_view": "West"}
    for input_id, token in elevations.items():
        e = by_id[input_id]
        assert e.view_type == "elevation"
        assert e.declared_direction_token == token
        assert e.direction_source == "user"
        assert e.direction_semantics == "building_axis"
        assert e.semantics_source == "standard_assumption"
        assert e.building_view_direction == token
        assert e.dimensioned is True
        assert e.expected_output_id == input_id
        assert sorted(e.opening_evidence.potentially_observable_claims) == sorted(ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS)

    # entries are canonically sorted by input_id
    assert [e.input_id for e in m.entries] == sorted(by_id)


def test_sm20_supplementary_plan_typed_required_view():
    m = build_view_manifest(SM20)
    by_id = {e.input_id: e for e in m.entries}
    assert set(by_id) == {
        "1f_view", "2f_view", "3f_view", "East_view", "North_view", "South_view", "West_view", "supp_plan",
    }
    supp = by_id["supp_plan"]
    assert supp.kind == "required_view"
    assert supp.view_type == "detail"
    assert supp.expected_output_id == "supp_plan_view"
    assert supp.floor_ref is None
    assert supp.dimensioned is False  # sm20 declares no dimensioned_views at all
    # sm20 declares no dimensioned_views key -> every entry defaults False
    assert all(e.dimensioned is False for e in m.entries)


def test_sm24_single_floor_no_supplementary():
    m = build_view_manifest(SM24)
    by_id = {e.input_id: e for e in m.entries}
    assert set(by_id) == {"1f_view", "East_view", "North_view", "South_view", "West_view"}
    assert by_id["1f_view"].floor_ref == 1


# --------------------------------------------------------------------------- #
# §8.4 generation-time hard gates
# --------------------------------------------------------------------------- #
def test_declared_path_not_exists_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    (case_dir / "case_data").mkdir(parents=True)
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps({"Floor plans": [{"floor": 1, "path": "case_data/missing.png", "thermal_zones": 1}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not exist"):
        build_view_manifest(case_dir)


def test_declared_path_symlink_escape_raises(tmp_path: Path):
    outside = tmp_path / "outside.png"
    outside.write_bytes(_tiny_png())
    case_dir = tmp_path / "case"
    (case_dir / "case_data").mkdir(parents=True)
    (case_dir / "case_data" / "escape.png").symlink_to(outside)
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps({"Floor plans": [{"floor": 1, "path": "case_data/escape.png", "thermal_zones": 1}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escapes case input root"):
        build_view_manifest(case_dir)


def test_two_elevation_keys_sharing_one_image_raises_on_input_id(tmp_path: Path):
    """Two distinct elevation-direction metadata keys (`North view path...` /
    `South view path...`) pointing at the *same* declared image collide on
    input_id (both normalize to the same basename) before the (currently
    unreachable, given the fixed 4-key North/South/East/West scheme —
    duplicate *direction tokens* would require two keys to carry the same
    token, which the metadata schema doesn't allow) direction-duplication
    guard would ever see two different tokens."""
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata()
    testdata["North view path of the building"] = "case_data/South_view.png"  # same file, distinct key
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="duplicate input_id"):
        build_view_manifest(case_dir)


def test_duplicate_floor_ref_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(**{
        "Floor plans": [
            {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 7},
            {"floor": 1, "path": "case_data/1f_view_b.png", "thermal_zones": 7},
        ],
    })
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="duplicate floor_ref"):
        build_view_manifest(case_dir)


def test_duplicate_input_id_same_basename_two_roles_raises(tmp_path: Path):
    """Entry-identity negative: the same declared basename reachable through
    two different metadata roles (a Floor plans entry and an elevation key
    both pointing at the identical file) collapses to the same input_id."""
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata()
    testdata["South view path of the building"] = "case_data/1f_view.png"
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="duplicate input_id"):
        build_view_manifest(case_dir)


def test_expected_output_id_conflict_without_input_id_conflict_raises(tmp_path: Path):
    """Entry-identity negative: two *different* input_ids whose mapping rule
    (`_expected_output_id`) collides on the same expected_output_id — a Floor
    plans entry literally named `supp_plan_view.png` vs the supplementary key's
    `supp_plan.png` both resolve to expected_output_id=`supp_plan_view`."""
    case_dir = tmp_path / "case"
    testdata = {
        "Floor plans": [
            {"floor": 1, "path": "case_data/supp_plan_view.png", "thermal_zones": 1},
        ],
        "Path of the supplementary plan example drawing for the building": "case_data/supp_plan.png",
    }
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="duplicate expected_output_id"):
        build_view_manifest(case_dir)


def test_view_kind_partial_override_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(views={"1f_view": {"view_kind": "partial"}})
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="partial views not supported"):
        build_view_manifest(case_dir)


def test_dimensioned_contradiction_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(**{
        "Floor plans": [
            {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 7, "dimensioned": False},
        ],
        "dimensioned_views": ["1f_view"],
    })
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="dimensioned contradiction"):
        build_view_manifest(case_dir)


def test_unclassified_image_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    (case_dir / "case_data" / "mystery.png").write_bytes(_tiny_png())
    with pytest.raises(ValueError, match="unclassified image"):
        build_view_manifest(case_dir)


def test_derived_working_copy_positive_and_negative(tmp_path: Path):
    case_dir = tmp_path / "case"
    _write_case(case_dir, _sm21_style_testdata())
    parent_bytes = (case_dir / "case_data" / "1f_view.png").read_bytes()
    (case_dir / "case_data" / "1f_view_source.png").write_bytes(parent_bytes)
    m = build_view_manifest(case_dir)
    excluded = {e.input_id: e for e in m.excluded_entries()}
    assert "1f_view_source" in excluded
    assert excluded["1f_view_source"].excluded_reason == "derived_working_copy"
    assert excluded["1f_view_source"].parent_input_id == "1f_view"
    assert excluded["1f_view_source"].image_sha256 == hash_file(case_dir / "case_data" / "1f_view.png")

    # negative: byte mismatch against the claimed parent
    (case_dir / "case_data" / "1f_view_source.png").write_bytes(parent_bytes + b"\x00")
    with pytest.raises(ValueError, match="byte mismatch"):
        build_view_manifest(case_dir)


def test_bad_or_missing_metadata_raises(tmp_path: Path):
    case_dir = tmp_path / "case_missing"
    (case_dir / "case_data").mkdir(parents=True)
    with pytest.raises(ValueError, match="no case metadata found"):
        build_view_manifest(case_dir)

    case_dir2 = tmp_path / "case_bad_json"
    (case_dir2 / "case_data").mkdir(parents=True)
    (case_dir2 / "case_data" / "testdata_prompt.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        build_view_manifest(case_dir2)

    case_dir3 = tmp_path / "case_non_dict"
    (case_dir3 / "case_data").mkdir(parents=True)
    (case_dir3 / "case_data" / "testdata_prompt.json").write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        build_view_manifest(case_dir3)


# --------------------------------------------------------------------------- #
# §8.6 direction three-axis matrix
# --------------------------------------------------------------------------- #
def test_true_azimuth_via_views_overlay(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(views={
        "South_view": {"direction_semantics": "true_azimuth", "azimuth_deg": 123.4},
    })
    _write_case(case_dir, testdata)
    m = build_view_manifest(case_dir)
    e = m.entry_by_input_id("South_view")
    assert e.direction_semantics == "true_azimuth"
    assert e.azimuth_deg == 123.4
    assert e.building_view_direction is None
    assert e.semantics_source == "case_metadata"
    assert e.direction_source == "user"  # independent axis, unaffected by the semantics override


def test_unknown_direction_semantics_via_views_overlay(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(views={"South_view": {"direction_semantics": "unknown"}})
    _write_case(case_dir, testdata)
    m = build_view_manifest(case_dir)
    e = m.entry_by_input_id("South_view")
    assert e.direction_semantics == "unknown"
    assert e.azimuth_deg is None
    assert e.building_view_direction is None


def test_true_azimuth_override_missing_angle_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(views={"South_view": {"direction_semantics": "true_azimuth"}})
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="azimuth_deg"):
        build_view_manifest(case_dir)


def test_true_azimuth_override_out_of_range_raises(tmp_path: Path):
    case_dir = tmp_path / "case"
    testdata = _sm21_style_testdata(views={
        "South_view": {"direction_semantics": "true_azimuth", "azimuth_deg": 360.0},
    })
    _write_case(case_dir, testdata)
    with pytest.raises(ValueError, match="azimuth_deg"):
        build_view_manifest(case_dir)


# --------------------------------------------------------------------------- #
# §8 claim-vocabulary lock on real generated output (plan vs elevation split)
# --------------------------------------------------------------------------- #
def test_plan_and_elevation_claim_sets_are_disjoint_where_expected():
    m = build_view_manifest(SM21)
    plan = m.entry_by_input_id("1f_view")
    elevation = m.entry_by_input_id("South_view")
    assert "host" in plan.opening_evidence.potentially_observable_claims
    assert "host" not in elevation.opening_evidence.potentially_observable_claims
    assert "sill" in elevation.opening_evidence.potentially_observable_claims
    assert "sill" not in plan.opening_evidence.potentially_observable_claims
    assert "existence" in plan.opening_evidence.potentially_observable_claims
    assert "existence" in elevation.opening_evidence.potentially_observable_claims
