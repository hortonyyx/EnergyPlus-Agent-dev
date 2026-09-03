"""WP-2--WP-4 fail-closed locks for the candidate-to-baseline path."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.judge import gt_promotion as promotion
from src.agent.judge import gt_raw_layer as raw_layer
from src.agent.judge import tarch_normalize as tn
from src.agent.judge import tarch_review_bundle as bundle_api
from src.agent.judge.gt import load_gt_document
from src.agent.judge.gt_promotion import promote_gt_v3
from src.agent.judge.gt_schema import canonical_gt_v3_bytes, compute_gt_v3_content_sha256
from src.agent.judge.tarch_converter_schema import (GT_SOURCES_ROOT,
                                                     TarchConversionRequestV1)


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
REQUEST = REPO / "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json"
ANNOTATIONS = REPO / "tests/fixtures/sm24_review/bundle_07_25/review_annotations.json"
RASTERS = REPO / "case_tests/e2e_tests/sm24_anchor/case_data"
FROZEN_GT = REPO / "tests/fixtures/sm24_review/bundle_07_25/gt/gt.json"


def _without_registered_provenance_stamps(document: dict) -> dict:
    """Remove only the registered code/DXF/manifest provenance hash chain."""
    answer = json.loads(json.dumps(document))
    answer.pop("content_sha256")
    for field in ("extractor_sha256", "validator_sha256", "vg_implementation_sha256",
                  "manifest_sha256"):
        answer["generator"].pop(field)
    for source in answer["sources"]:
        source.pop("content_sha256")
    return answer


def _copy_bundle(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _test_gt_root(tmp_path: Path) -> Path:
    root = tmp_path / "gt"
    root.mkdir(exist_ok=True)
    (root / promotion.TEST_GT_ROOT_MARKER).write_text("test fixture\n", encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def candidate_bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("promotion_candidate")
    source = root / "source.dxf"; source.write_bytes(SOURCE.read_bytes())
    request = TarchConversionRequestV1.model_validate_json(REQUEST.read_text(encoding="utf-8"))
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["zone_roles"]
    return bundle_api.build_review_bundle(source, request, output_dir=root / "bundle", raster_root=RASTERS,
                                          review_annotations=annotations)


@pytest.fixture()
def fresh_bundle(candidate_bundle, tmp_path):
    return _copy_bundle(candidate_bundle, tmp_path / "bundle")


def _index_bytes(root: Path) -> bytes:
    return (root / "review_index.json").read_bytes()


def _refresh_index_and_ack(root: Path) -> None:
    candidate = json.loads((root / "gt/gt.json").read_text())
    manifest = json.loads((root / "manifest.json").read_text())
    index = bundle_api.build_review_index(bundle_api._review_files(root), root=root,
                                          candidate_gt_sha256=candidate["content_sha256"],
                                          manifest_sha256=manifest["manifest_sha256"])
    (root / "review_index.json").write_text(json.dumps(index), encoding="utf-8")
    ack = json.loads((root / "review_ack.json").read_text()); ack["review_index_sha256"] = index["inventory_sha256"]
    (root / "review_ack.json").write_text(json.dumps(ack), encoding="utf-8")


def _write_index(root: Path, index: dict) -> None:
    (root / "review_index.json").write_text(json.dumps(index), encoding="utf-8")


def test_r2_1_inventory_formula_is_frozen(tmp_path):
    (tmp_path / "b.txt").write_bytes(b"b")
    (tmp_path / "a.txt").write_bytes(b"a")
    index = bundle_api.build_review_index([tmp_path / "b.txt", tmp_path / "a.txt"], root=tmp_path,
                                          candidate_gt_sha256="1" * 64, manifest_sha256="2" * 64)
    assert index["files"] == [
        {"path": "a.txt", "sha256": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"},
        {"path": "b.txt", "sha256": "3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d"},
    ]
    assert index["inventory_sha256"] == "f6338ab939fa6958f9b9ea4986971edb3d7843a93fc491d44da663bacba8bb8b"


@pytest.mark.parametrize("relative", ["gt/gt.json", "gt/renders/gt_plan.png", "opening_elevation_audit.json", "review_annotations.json"])
def test_r2_2_any_indexed_file_tamper_changes_inventory(fresh_bundle, relative):
    path = fresh_bundle / relative; path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ValueError, match="review_index_file_hash_mismatch"):
        bundle_api.validate_review_index(fresh_bundle)


@pytest.mark.parametrize("mutate", [lambda files: files[:-1], lambda files: files + [files[-1]]])
def test_r2_3_missing_or_extra_file_list_is_rejected(fresh_bundle, mutate):
    index = json.loads(_index_bytes(fresh_bundle)); index["files"] = mutate(index["files"])
    (fresh_bundle / "review_index.json").write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="review_index_inventory_mismatch"):
        bundle_api.validate_review_index(fresh_bundle)


def test_r2_4_input_file_order_does_not_change_inventory(tmp_path):
    files = []
    for name in ("c", "a", "b"):
        path = tmp_path / name; path.write_text(name); files.append(path)
    forward = bundle_api.build_review_index(files, root=tmp_path, candidate_gt_sha256="1" * 64, manifest_sha256="2" * 64)
    reverse = bundle_api.build_review_index(list(reversed(files)), root=tmp_path, candidate_gt_sha256="1" * 64, manifest_sha256="2" * 64)
    assert forward["inventory_sha256"] == reverse["inventory_sha256"]


def test_r2_5_neutering_sort_releases_r2_4(tmp_path, monkeypatch):
    files = []
    for name in ("c", "a", "b"):
        path = tmp_path / name; path.write_text(name); files.append(path)
    monkeypatch.setattr(bundle_api, "_sort_inventory_entries", lambda items: items)
    forward = bundle_api.build_review_index(files, root=tmp_path, candidate_gt_sha256="1" * 64, manifest_sha256="2" * 64)
    reverse = bundle_api.build_review_index(list(reversed(files)), root=tmp_path, candidate_gt_sha256="1" * 64, manifest_sha256="2" * 64)
    assert forward["inventory_sha256"] != reverse["inventory_sha256"]


def test_r2_6_two_bundles_have_identical_index(candidate_bundle, tmp_path):
    source = tmp_path / "source.dxf"; source.write_bytes(SOURCE.read_bytes())
    request = TarchConversionRequestV1.model_validate_json(REQUEST.read_text(encoding="utf-8"))
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["zone_roles"]
    second = bundle_api.build_review_bundle(source, request, output_dir=tmp_path / "second", raster_root=RASTERS,
                                            review_annotations=annotations)
    assert _index_bytes(candidate_bundle) == _index_bytes(second)


def test_sm24_rebuilt_gt_is_field_stable_except_registered_provenance_stamps(candidate_bundle):
    """Lock final GT fields, not only converter records and normalized DXF bytes."""
    rebuilt = json.loads((candidate_bundle / "gt/gt.json").read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN_GT.read_text(encoding="utf-8"))
    code_hash_fields = ("extractor_sha256", "validator_sha256", "vg_implementation_sha256")
    assert any(rebuilt["generator"][field] != frozen["generator"][field]
               for field in code_hash_fields)
    # The old signed bundle and current rebuild are known to carry different
    # normalized-DXF/manifest/content stamps as well as implementation hashes.
    # Every non-provenance field must nevertheless remain exactly equal.
    assert rebuilt["sources"][0]["content_sha256"] != frozen["sources"][0]["content_sha256"]
    assert rebuilt["generator"]["manifest_sha256"] != frozen["generator"]["manifest_sha256"]
    assert _without_registered_provenance_stamps(rebuilt) \
        == _without_registered_provenance_stamps(frozen)


def test_r3_1_signs_and_existing_verifier_accepts(fresh_bundle):
    ack = bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z",
                                        confirm_near_threshold=True)
    request = TarchConversionRequestV1.model_validate_json((fresh_bundle / "request.json").read_bytes())
    accepted, _ = tn._verify_human_review_ack(fresh_bundle, request, fresh_bundle / "source.dxf",
                                               fresh_bundle / "overlay_plan.svg")
    assert ack.near_threshold_confirmed and accepted


def test_r3_2_tampered_candidate_refuses_signature(fresh_bundle):
    path = fresh_bundle / "gt/gt.json"; path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ValueError, match="review_index_file_hash_mismatch"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_malformed_refuses_signature(fresh_bundle):
    (fresh_bundle / "review_index.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="review_index_invalid"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_schema_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["schema"] = "wrong"
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_schema_invalid"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_file_list_shape_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["files"] = {}
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_files_invalid"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_file_entry_shape_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["files"][0]["path"] = 3
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_files_invalid"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_unsorted_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["files"].reverse()
    index["inventory_sha256"] = bundle_api._canonical_inventory_sha256(index["files"])
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_files_unsorted"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_algorithm_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["inventory_algorithm"] = "wrong"
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_algorithm_invalid"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_index_file_set_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["files"] = index["files"][:-1]
    index["inventory_sha256"] = bundle_api._canonical_inventory_sha256(index["files"])
    _write_index(fresh_bundle, index)
    with pytest.raises(ValueError, match="review_index_file_set_mismatch"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


@pytest.mark.parametrize("relative", ["rogue_root.txt", "review/rogue_review.txt", "gt/rogue_gt.txt"])
def test_r3_directory_rogue_file_refuses_validation_and_promotion(ready_bundle, tmp_path, relative):
    rogue = ready_bundle / relative
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_text("unsigned reviewer bait\n", encoding="utf-8")
    with pytest.raises(ValueError, match="review_index_directory_file_set_mismatch"):
        bundle_api.validate_review_index(ready_bundle)
    with pytest.raises(ValueError, match="review_index_directory_file_set_mismatch"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    assert not (tmp_path / "gt/sm24_anchor").exists()


def test_r3_3_bad_inventory_refuses_signature(fresh_bundle):
    index = json.loads(_index_bytes(fresh_bundle)); index["inventory_sha256"] = "0" * 64
    (fresh_bundle / "review_index.json").write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="review_index_inventory_mismatch"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_source_hash_refuses_signature(fresh_bundle):
    source = fresh_bundle / "source.dxf"; source.write_bytes(source.read_bytes() + b"x")
    with pytest.raises(ValueError, match="review_bundle_source_hash_mismatch"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_4_near_threshold_requires_explicit_confirmation(fresh_bundle):
    with pytest.raises(ValueError, match="near_threshold_confirmation_required"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")
    assert bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z",
                                         confirm_near_threshold=True).near_threshold_confirmed


def test_r3_5_nonreview_red_gate_refuses_signature(fresh_bundle):
    report = json.loads((fresh_bundle / "conversion_report.json").read_text())
    next(gate for gate in report["gates"] if gate["id"] == "G1")["passed"] = False
    (fresh_bundle / "conversion_report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="nonreview_gate_failed"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z")


def test_r3_6_ack_never_overwritten(fresh_bundle):
    bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z",
                                  confirm_near_threshold=True)
    with pytest.raises(FileExistsError, match="review_ack_exists"):
        bundle_api.sign_review_bundle(fresh_bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z",
                                      confirm_near_threshold=True)


@pytest.fixture(scope="module")
def signed_rerun_bundle(candidate_bundle, tmp_path_factory):
    bundle = _copy_bundle(candidate_bundle, tmp_path_factory.mktemp("signed_rerun") / "bundle")
    bundle_api.sign_review_bundle(bundle, reviewer="terra", signed_at="2026-07-26T00:00:00Z",
                                  confirm_near_threshold=True)
    bundle_api.rerun_signed_review_bundle(bundle)
    return bundle


@pytest.fixture()
def ready_bundle(signed_rerun_bundle, tmp_path):
    return _copy_bundle(signed_rerun_bundle, tmp_path / "bundle")


def test_r4_1_full_chain_promotes_only_after_signed_rerun(ready_bundle, tmp_path):
    gt_root = _test_gt_root(tmp_path)
    assert load_gt_document("sm24_anchor", gt_dir=gt_root) is None
    result = promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=gt_root)
    assert result.destination == gt_root / "sm24_anchor"
    assert load_gt_document("sm24_anchor", gt_dir=gt_root).verification.status == "human_verified"


def test_r4_2_semantic_invariant(ready_bundle, tmp_path):
    promoted = promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    candidate = json.loads((ready_bundle / "gt/gt.json").read_text())
    verified = json.loads((promoted.destination / "gt.json").read_text())
    for document in (candidate, verified):
        document.pop("verification"); document.pop("content_sha256")
    assert candidate == verified


# --------------------------------------------------------------------------- #
# F-117 -- promotion is now the ONLY writer gt_sources/<case>/ needs
#
# Until now, promote_gt_v3 read request.json (for report.request_sha256) and
# source.dxf out of the bundle root but never wrote either anywhere durable --
# case_tests/test_baseline/gt_sources/<case>/ was populated by hand for the
# three existing cases, so the next promoted case would reproduce F-111 (the
# reproduction gate's signed-inputs resolver finds nothing).  ⛔ The lock below
# deliberately drives the REAL entry point (promote_gt_v3), not the private
# helper: F-116 already established that a helper-only test cannot see a
# search-root regression the way an end-to-end resolve can.
# --------------------------------------------------------------------------- #
def test_f117_a_signed_inputs_root_mirrors_the_production_constant():
    """Pure path arithmetic, no filesystem writes: for the real (default) gt_dir,
    the sibling-of-gt/ formula this module uses must equal the actual constant
    the reproduction gate reads from (tarch_converter_schema.GT_SOURCES_ROOT).
    If a future edit lets the two drift apart, promotion would keep writing
    signed inputs nobody's reproduction gate ever looks at again."""
    target_root = promotion._approved_target_root(Path(promotion.DEFAULT_GT_DIR))
    assert promotion._signed_inputs_root(target_root) == GT_SOURCES_ROOT.resolve()


def test_f117_b_real_promotion_populates_gt_sources_and_the_gate_resolves_it(ready_bundle, tmp_path):
    """The actual lock: promote through promote_gt_v3, then ask the real
    reproduction-gate resolvers (gt_raw_layer.find_signed_request /
    find_signed_source_dxf / verify_raw_layer_reproduction) to find what
    promotion just wrote -- with NOTHING hand-placed.  ⛔ Not a helper test."""
    gt_root = _test_gt_root(tmp_path)
    sources_root = gt_root.parent / "gt_sources"
    assert not sources_root.exists()  # nothing hand-placed for this fresh case

    result = promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=gt_root)

    ack = json.loads((result.destination / "review" / "review_ack.json").read_text())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", sources_root)
    try:
        request = raw_layer.find_signed_request("sm24_anchor", ack["request_sha256"])
        assert request is not None, "promotion wrote request.json but the gate cannot resolve it"
        assert raw_layer.compute_request_sha256(request) == ack["request_sha256"]

        dxf = raw_layer.find_signed_source_dxf("sm24_anchor", ack["source_dxf_sha256"])
        assert dxf is not None, "promotion wrote source.dxf but the gate cannot resolve it"

        verdict = raw_layer.verify_raw_layer_reproduction("sm24_anchor", gt_dir=gt_root)
        assert verdict.status == "reproduced", verdict.detail
    finally:
        monkeypatch.undo()


def test_f117_c_signed_inputs_write_failure_rolls_back_the_answer_too(ready_bundle, tmp_path, monkeypatch):
    """Atomicity: gt/<case> and gt_sources/<case>/ land as one unit. A failure
    writing the new sources copy must not leave the sibling answer behind
    half-promoted -- the exact "half-finished state" the dispatch warned against."""
    gt_root = _test_gt_root(tmp_path)
    real_copy = promotion.shutil.copyfile

    def fail_on_source_dxf_copy(src, dst):
        # "source.dxf" is never a copy DESTINATION anywhere in promote_gt_v3
        # except inside _promote_signed_inputs -- the gt/<case> loops above it
        # copy renders/*.png and five differently-named review/ files.
        if Path(dst).name == "source.dxf":
            raise RuntimeError("injected sources copy failure")
        return real_copy(src, dst)

    monkeypatch.setattr(promotion.shutil, "copyfile", fail_on_source_dxf_copy)
    with pytest.raises(RuntimeError, match="injected sources copy failure"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=gt_root)
    assert not (gt_root / "sm24_anchor").exists(), "the gt/<case> answer must not survive a sources-write failure"
    assert not (gt_root.parent / "gt_sources" / "sm24_anchor").exists()


def test_r4_3_production_path_rejects_pure_geometry_mutation(ready_bundle, tmp_path, monkeypatch):
    original = promotion._verified_document
    def mutate(candidate, ack):
        verified = original(candidate, ack)
        floor = verified.floors[0]
        segments = list(floor.boundary_segments)
        segments[0] = segments[0].model_copy(update={"wall_thickness_m": 0.25})
        floors = list(verified.floors)
        floors[0] = floor.model_copy(update={"boundary_segments": segments})
        return verified.model_copy(update={"floors": floors})
    monkeypatch.setattr(promotion, "_verified_document", mutate)
    with pytest.raises(ValueError, match="semantic_invariant_failed"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    assert not (tmp_path / "gt/sm24_anchor").exists()


def test_r4_4_missing_ack_refuses(ready_bundle, tmp_path):
    (ready_bundle / "review_ack.json").unlink()
    with pytest.raises(ValueError, match="promotion_ack_missing"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_5_bad_ack_index_refuses(ready_bundle, tmp_path):
    ack = json.loads((ready_bundle / "review_ack.json").read_text()); ack["review_index_sha256"] = "0" * 64
    (ready_bundle / "review_ack.json").write_text(json.dumps(ack), encoding="utf-8")
    with pytest.raises(ValueError, match="ack_index_mismatch"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_ack_verification_refuses(ready_bundle, tmp_path):
    ack = json.loads((ready_bundle / "review_ack.json").read_text()); ack["source_dxf_sha256"] = "0" * 64
    (ready_bundle / "review_ack.json").write_text(json.dumps(ack), encoding="utf-8")
    with pytest.raises(ValueError, match="ack_verification_failed"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


@pytest.mark.parametrize("relative", ["gt/gt.json", "gt/renders/gt_plan.png"])
def test_r4_6_indexed_tamper_refuses(ready_bundle, tmp_path, relative):
    path = ready_bundle / relative; path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ValueError, match="review_index_file_hash_mismatch"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_7_nonpass_report_refuses(ready_bundle, tmp_path):
    report = json.loads((ready_bundle / "conversion_report.json").read_text()); report["status"] = "BLOCKED"
    (ready_bundle / "conversion_report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="report_not_all_green"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_8_already_verified_candidate_refuses(ready_bundle, tmp_path):
    candidate = promotion.load_gt_file(ready_bundle / "gt/gt.json", allow_legacy=False)
    verification = candidate.verification.model_copy(update={"status": "human_verified", "reviewer_id": "terra",
                                                              "reviewed_on": "2026-07-26",
                                                              "methods": ["dxf_topology_roundtrip", "direct_gt_render",
                                                                          "overlay_on_original_drawing", "human_source_comparison"]})
    changed = candidate.model_copy(update={"verification": verification, "content_sha256": "0" * 64})
    changed = changed.model_copy(update={"content_sha256": compute_gt_v3_content_sha256(changed)})
    (ready_bundle / "gt/gt.json").write_bytes(canonical_gt_v3_bytes(changed)); _refresh_index_and_ack(ready_bundle)
    with pytest.raises(ValueError, match="candidate_status_invalid"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_9_bad_candidate_content_hash_refuses(ready_bundle, tmp_path):
    candidate = promotion.load_gt_file(ready_bundle / "gt/gt.json", allow_legacy=False)
    bad_hash = candidate.model_copy(update={"content_sha256": "0" * 64})
    index = json.loads(_index_bytes(ready_bundle)); index["candidate_gt_sha256"] = bad_hash.content_sha256
    _write_index(ready_bundle, index)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(promotion, "load_gt_file", lambda *args, **kwargs: bad_hash)
    try:
        with pytest.raises(ValueError, match="candidate_content_hash_mismatch"):
            promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    finally:
        monkeypatch.undo()


def test_r4_10_case_mismatch_refuses(ready_bundle, tmp_path):
    candidate = promotion.load_gt_file(ready_bundle / "gt/gt.json", allow_legacy=False)
    changed = candidate.model_copy(update={"case": "different_case", "content_sha256": "0" * 64})
    changed = changed.model_copy(update={"content_sha256": compute_gt_v3_content_sha256(changed)})
    (ready_bundle / "gt/gt.json").write_bytes(canonical_gt_v3_bytes(changed)); _refresh_index_and_ack(ready_bundle)
    with pytest.raises(ValueError, match="candidate_identity_mismatch"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))


def test_r4_11_existing_target_is_untouched(ready_bundle, tmp_path):
    root = _test_gt_root(tmp_path)
    target = root / "sm24_anchor"; target.mkdir(parents=True); (target / "keep").write_bytes(b"keep")
    with pytest.raises(FileExistsError, match="promotion_target_exists"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=root)
    assert (target / "keep").read_bytes() == b"keep"


def test_r4_unprotected_target_root_refuses(ready_bundle, tmp_path):
    root = tmp_path / "not-a-gt-root"; root.mkdir()
    with pytest.raises(ValueError, match="promotion_gt_dir_unprotected"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=root)


def test_r4_12_atomic_write_failure_leaves_no_target(ready_bundle, tmp_path, monkeypatch):
    real_copy = promotion.shutil.copyfile
    calls = 0
    def fail_second_copy(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected copy failure")
        return real_copy(*args, **kwargs)
    monkeypatch.setattr(promotion.shutil, "copyfile", fail_second_copy)
    with pytest.raises(RuntimeError, match="injected copy failure"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    assert not (tmp_path / "gt/sm24_anchor").exists()


def test_r4_13_postwrite_selfcheck_is_bound(ready_bundle, tmp_path, monkeypatch):
    monkeypatch.setattr(promotion, "load_gt_document", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="postwrite_selfcheck_failed"):
        promote_gt_v3(ready_bundle, case="sm24_anchor", gt_dir=_test_gt_root(tmp_path))
    assert not (tmp_path / "gt/sm24_anchor").exists()


# R3-7 / R4-14: every fail-closed precondition is source-neutered in an isolated
# mirror.  The child runs this whole module but excludes this marker, so it cannot
# recursively invoke more mutation children.
MUTANTS = {
    "promote_target_root_protected": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_gt_dir_unprotected")', "return root"),
    "index_parseable": ("src/agent/judge/tarch_review_bundle.py",
        'raise ValueError("review_index_invalid") from exc', "return {}"),
    "index_schema": ("src/agent/judge/tarch_review_bundle.py",
        'if index.get("schema") != REVIEW_INDEX_SCHEMA:\n        raise ValueError("review_index_schema_invalid")',
        'if False:\n        raise ValueError("review_index_schema_invalid")'),
    "index_file_list_shape": ("src/agent/judge/tarch_review_bundle.py",
        'if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):\n        raise ValueError("review_index_files_invalid")',
        'if False:\n        raise ValueError("review_index_files_invalid")'),
    "index_file_entry_shape": ("src/agent/judge/tarch_review_bundle.py",
        'if not isinstance(path, str) or not isinstance(digest, str):\n            raise ValueError("review_index_files_invalid")',
        'if False:\n            raise ValueError("review_index_files_invalid")'),
    "index_file_bytes": ("src/agent/judge/tarch_review_bundle.py",
        'if not candidate.is_relative_to(root) or not candidate.is_file() or _sha256(candidate) != digest:\n            raise ValueError("review_index_file_hash_mismatch")',
        'if False:\n            raise ValueError("review_index_file_hash_mismatch")'),
    "index_sorted": ("src/agent/judge/tarch_review_bundle.py",
        'if normalized != sorted(normalized, key=lambda item: item["path"]):\n        raise ValueError("review_index_files_unsorted")',
        'if False:\n        raise ValueError("review_index_files_unsorted")'),
    "index_algorithm": ("src/agent/judge/tarch_review_bundle.py",
        'if index.get("inventory_algorithm") != INVENTORY_ALGORITHM:\n        raise ValueError("review_index_algorithm_invalid")',
        'if False:\n        raise ValueError("review_index_algorithm_invalid")'),
    "index_inventory_hash": ("src/agent/judge/tarch_review_bundle.py",
        'if index.get("inventory_sha256") != _canonical_inventory_sha256(normalized):\n        raise ValueError("review_index_inventory_mismatch")',
        'if False:\n        raise ValueError("review_index_inventory_mismatch")'),
    "index_file_set": ("src/agent/judge/tarch_review_bundle.py",
        'if listed != expected:\n        raise ValueError("review_index_file_set_mismatch")',
        'if False:\n        raise ValueError("review_index_file_set_mismatch")'),
    "index_directory_file_set": ("src/agent/judge/tarch_review_bundle.py",
        'if not actual_files <= allowed_files | {\n        path for path in actual_files\n        if path.split("/", 1)[0] in _RUNTIME_BUNDLE_DIRECTORIES\n    }:\n        raise ValueError("review_index_directory_file_set_mismatch")',
        'if False:\n        raise ValueError("review_index_directory_file_set_mismatch")'),
    "sign_ack_not_exists": ("src/agent/judge/tarch_review_bundle.py",
        'raise FileExistsError("review_ack_exists")', "pass"),
    "sign_source_hash": ("src/agent/judge/tarch_review_bundle.py",
        'if not source.is_file() or _sha256(source) != request.source_dxf_sha256:\n        raise ValueError("review_bundle_source_hash_mismatch")',
        'if False:\n        raise ValueError("review_bundle_source_hash_mismatch")'),
    "sign_eight_review_gates": ("src/agent/judge/tarch_review_bundle.py",
        'if set(gates) != {f"G{i}" for i in range(1, 11)} or any(not gates[f"G{i}"].passed for i in range(1, 11) if i not in {6, 10}):\n        raise ValueError("review_bundle_nonreview_gate_failed")',
        'if False:\n        raise ValueError("review_bundle_nonreview_gate_failed")'),
    "sign_near_threshold_confirmation": ("src/agent/judge/tarch_review_bundle.py",
        'if near_faces and not confirm_near_threshold:\n        raise ValueError(f"review_bundle_near_threshold_confirmation_required:{near_faces}")',
        'if False:\n        raise ValueError(f"review_bundle_near_threshold_confirmation_required:{near_faces}")'),
    "promote_target_not_exists": ("src/agent/judge/gt_promotion.py",
        'raise FileExistsError("promotion_target_exists")', "pass"),
    "promote_report_all_green": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_report_not_all_green")', "pass"),
    "promote_ack_exists": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_ack_missing")', "pass"),
    "promote_ack_index": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_ack_index_mismatch")', "pass"),
    "promote_ack_verifies": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_ack_verification_failed")', "pass"),
    "promote_candidate_status": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_candidate_status_invalid")', "pass"),
    "promote_candidate_identity": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_candidate_identity_mismatch")', "pass"),
    "promote_candidate_content_hash": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_candidate_content_hash_mismatch")', "pass"),
    "promote_semantic_invariant": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_semantic_invariant_failed")', "pass"),
    "promote_postwrite_selfcheck": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_postwrite_selfcheck_failed")', "pass"),
}


def _mirror_repo(tmp_path: Path) -> Path:
    mirror = tmp_path / "repo"
    mirror.mkdir()
    for relative in ("src", "scripts", "tests"):
        shutil.copytree(REPO / relative, mirror / relative, ignore=shutil.ignore_patterns("__pycache__"))
    # This module's fixed sm24 fixtures are deliberately copied read-only; no
    # baseline asset is ever mutated in the source checkout. The review-request
    # fixtures (REQUEST / ANNOTATIONS) live under tests/fixtures/ and therefore
    # ride along with the tests/ copytree above, so the mirror finds them at the
    # same REPO-relative path the module references.
    for relative in (
        "case_tests/test_baseline/gt_sources/sm24_anchor",
        "case_tests/e2e_tests/sm24_anchor/case_data",
    ):
        shutil.copytree(REPO / relative, mirror / relative, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO / "pyproject.toml", mirror / "pyproject.toml")
    # pyproject addopts pins `-p ep_no_billed_gate` (the F-158 egress gate, a
    # repo-root plugin); the child pytest below reads that pyproject, so the
    # plugin module must exist in the mirror or the child fails to start.
    shutil.copy2(REPO / "ep_no_billed_gate.py", mirror / "ep_no_billed_gate.py")
    return mirror


def _apply_mutation(repo: Path, relative: str, original: str, replacement: str) -> None:
    path = repo / relative
    text = path.read_text(encoding="utf-8")
    assert text.count(original) == 1, f"mutation_not_hit_exactly_once:{relative}:{original!r}"
    path.write_text(text.replace(original, replacement, 1), encoding="utf-8")


def _failed_test_names(output: str) -> set[str]:
    return set(re.findall(r"^FAILED (tests/test_gt_promotion_path.py::[^\s]+)", output, flags=re.MULTILINE))


@pytest.mark.mutation
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_precondition_is_one_to_one_bound(mutant, tmp_path):
    repo = _mirror_repo(tmp_path)
    _apply_mutation(repo, *MUTANTS[mutant])
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-n0",
                          "-m", "not mutation", "tests/test_gt_promotion_path.py"],
                         cwd=repo, capture_output=True, text=True)
    failed = _failed_test_names(out.stdout + out.stderr)
    assert failed == EXPECTED[mutant], (mutant, sorted(failed), (out.stdout + out.stderr)[-4000:])


_NODE = "tests/test_gt_promotion_path.py::"
EXPECTED: dict[str, set[str]] = {
    "index_algorithm": {_NODE + "test_r3_index_algorithm_refuses_signature"},
    "index_file_bytes": {
        _NODE + "test_r2_2_any_indexed_file_tamper_changes_inventory[gt/gt.json]",
        _NODE + "test_r2_2_any_indexed_file_tamper_changes_inventory[gt/renders/gt_plan.png]",
        _NODE + "test_r2_2_any_indexed_file_tamper_changes_inventory[opening_elevation_audit.json]",
        _NODE + "test_r2_2_any_indexed_file_tamper_changes_inventory[review_annotations.json]",
        _NODE + "test_r3_2_tampered_candidate_refuses_signature",
        _NODE + "test_r4_6_indexed_tamper_refuses[gt/gt.json]",
        _NODE + "test_r4_6_indexed_tamper_refuses[gt/renders/gt_plan.png]",
    },
    "index_file_entry_shape": {_NODE + "test_r3_index_file_entry_shape_refuses_signature"},
    "index_file_list_shape": {_NODE + "test_r3_index_file_list_shape_refuses_signature"},
    "index_file_set": {_NODE + "test_r3_index_file_set_refuses_signature"},
    "index_directory_file_set": {
        _NODE + "test_r3_directory_rogue_file_refuses_validation_and_promotion[rogue_root.txt]",
        _NODE + "test_r3_directory_rogue_file_refuses_validation_and_promotion[review/rogue_review.txt]",
        _NODE + "test_r3_directory_rogue_file_refuses_validation_and_promotion[gt/rogue_gt.txt]",
    },
    "index_inventory_hash": {
        _NODE + "test_r2_3_missing_or_extra_file_list_is_rejected[<lambda>0]",
        _NODE + "test_r2_3_missing_or_extra_file_list_is_rejected[<lambda>1]",
        _NODE + "test_r3_3_bad_inventory_refuses_signature",
    },
    "index_parseable": {_NODE + "test_r3_index_malformed_refuses_signature"},
    "index_schema": {_NODE + "test_r3_index_schema_refuses_signature"},
    "index_sorted": {_NODE + "test_r3_index_unsorted_refuses_signature"},
    "promote_ack_exists": {_NODE + "test_r4_4_missing_ack_refuses"},
    "promote_ack_index": {_NODE + "test_r4_5_bad_ack_index_refuses"},
    "promote_ack_verifies": {_NODE + "test_r4_ack_verification_refuses"},
    "promote_candidate_content_hash": {_NODE + "test_r4_9_bad_candidate_content_hash_refuses"},
    "promote_candidate_identity": {_NODE + "test_r4_10_case_mismatch_refuses"},
    "promote_candidate_status": {_NODE + "test_r4_8_already_verified_candidate_refuses"},
    "promote_postwrite_selfcheck": {_NODE + "test_r4_13_postwrite_selfcheck_is_bound"},
    "promote_report_all_green": {_NODE + "test_r4_7_nonpass_report_refuses"},
    "promote_semantic_invariant": {_NODE + "test_r4_3_production_path_rejects_pure_geometry_mutation"},
    "promote_target_not_exists": {_NODE + "test_r4_11_existing_target_is_untouched"},
    "promote_target_root_protected": {_NODE + "test_r4_unprotected_target_root_refuses"},
    "sign_ack_not_exists": {_NODE + "test_r3_6_ack_never_overwritten"},
    "sign_eight_review_gates": {_NODE + "test_r3_5_nonreview_red_gate_refuses_signature"},
    "sign_near_threshold_confirmation": {_NODE + "test_r3_4_near_threshold_requires_explicit_confirmation"},
    "sign_source_hash": {_NODE + "test_r3_source_hash_refuses_signature"},
}
