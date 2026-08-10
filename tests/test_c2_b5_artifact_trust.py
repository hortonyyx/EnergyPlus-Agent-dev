"""B5 Phase-D trust-root, accepted-chain, E4, and fail-closed locks."""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from test_c2_b5_parent_and_verts import _bundle

from src.agent.correction.orientation import (
    OrientationEvidenceSetV1,
    OrientationRunConfigV1,
    build_orientation_resolution_input,
    finalize_orientation_enrichment,
    verify_orientation_resolution,
)
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.manifest import (
    RunInputs,
    RunManifest,
    RunManifestV2,
    StageRecordV2,
    hash_bytes,
    hash_text,
    new_run_id,
)
from src.agent.execution.correction_audit import load_reportable_correction_audit
from src.agent.execution.policy import RunPolicy, ValidationScope
from src.agent.execution.run_policy_freeze import provision_run_policy
from src.agent.execution.stage_runner import StageRunner
from src.agent.execution.step_orchestrator import approve_geometry
from src.agent.execution.validation_run import validate_case
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import (
    building_geometry_json,
    geometry_specs_markdown,
    serialize_geometry,
)
from src.agent.output_coordinates import (
    load_verified_accepted_correction,
    verify_integrated_gate1_correction,
)
from src.agent.state import IntakeOutput
from src.validator.checks.correction import check_correction
from src.validator.checks.kernel import check_kernel
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus
from src.validator.data_model import BuildingSchema, SiteLocationSchema


def _report() -> CheckReport:
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    report.add_pass("phase_d.fixture", CheckLayer.INVARIANT)
    return report


def _accepted(tmp_path: Path, *, include_elevation: bool = False, include_window: bool = True):
    bundle = _bundle(tmp_path, include_elevation=include_elevation, include_window=include_window)
    marker = bundle.verified
    manifest = RunManifestV2(
        case="phase-d",
        run_id=new_run_id(),
        run_inputs=RunInputs(
            view_manifest_sha256=marker.inputs.view_manifest.content_sha256,
        ),
    )
    meta = tmp_path / "_run"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "view_manifest.json").write_bytes(marker.raw_view_manifest_bytes)
    reading_dir = tmp_path / "0_reading"
    reading_dir.mkdir(parents=True, exist_ok=True)
    for input_id, raw in marker.raw_reading_artifacts:
        identity = next(row for row in marker.inputs.reading_artifacts if row.input_id == input_id)
        (reading_dir / f"{identity.expected_output_id}.json").write_bytes(raw)
    StageRunner(tmp_path, manifest).record(
        stage="1_correction",
        stage_dir=tmp_path / "1_correction",
        output_obj=bundle.result,
        report=_report(),
    )
    manifest.save(tmp_path)
    record = manifest.accepted("1_correction")
    attempt = tmp_path / "1_correction" / "attempts" / f"{record.accepted_attempt:03d}"
    return bundle, manifest, record, attempt


def _accept_file_mutation(record, path: Path, artifact_key: str) -> None:
    digest = hash_bytes(path.read_bytes())
    record.artifact_hashes[artifact_key] = digest
    if artifact_key == "output":
        record.output_hash = digest


def _rebuild_self_consistent_writer_result(result, *, geom, audit_payload):
    """Re-sign a caller-forged candidate through the public B5 identity APIs."""
    from src.agent.correction.artifact_serialization import (
        serialize_correction_output,
        serialize_feature_states,
    )
    from src.agent.correction.config import load_core_tolerances
    from src.agent.correction.feature_state import FeatureStatesArtifactV1
    from src.agent.correction.finalize import PreparedCandidateIdentity
    from src.agent.correction.window_host import derive_window_evidence_ledger

    output_bytes = serialize_correction_output(geom)
    output_sha256 = hashlib.sha256(output_bytes).hexdigest()
    feature_states = FeatureStatesArtifactV1(
        output_sha256=output_sha256,
        claims=result.feature_state_claims,
    )
    feature_states_bytes = serialize_feature_states(feature_states)
    prepared = PreparedCandidateIdentity(
        output_bytes=output_bytes,
        output_sha256=output_sha256,
        feature_states_bytes=feature_states_bytes,
        feature_states_sha256=hashlib.sha256(feature_states_bytes).hexdigest(),
    )
    evidence = derive_window_evidence_ledger(
        geom,
        host_claims=result.window_host_claims,
        verified_inputs=result.verified_window_resolver_inputs,
        candidate_identity=prepared,
        tolerances=load_core_tolerances(),
    )
    return dataclasses.replace(
        result,
        geom=geom,
        audit_payload=audit_payload,
        prepared_candidate_identity=prepared,
        window_evidence_ledger=evidence,
    )


def _forge_both_window_audit_copies(result, mutate_rows):
    geom_corrections = json.loads(json.dumps(result.geom.corrections))
    audit_payload = json.loads(json.dumps(result.audit_payload))
    mutate_rows(geom_corrections)
    mutate_rows(audit_payload["corrections"])
    geom = result.geom.model_copy(update={"corrections": geom_corrections})
    return _rebuild_self_consistent_writer_result(
        result,
        geom=geom,
        audit_payload=audit_payload,
    )


def test_d1_writer_emits_exact_six_artifacts_and_loader_issues_build_proof(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    assert record.artifact_contract == "correction_b5_v1"
    assert set(record.artifact_hashes) == {
        "output", "checks", "audit", "feature_states",
        "window_resolver_inputs", "window_hosts",
    }
    assert {path.name for path in attempt.iterdir()} == {
        "output.json", "checks.json", "audit.json", "feature_states.json",
        "window_resolver_inputs.json", "window_hosts.json",
    }
    verified = load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)
    assert verified.window_host_proof is not None
    built = build_geometry(
        bundle.result.geom,
        capability_profile="orthogonal_polygon",
        window_host_proof=verified.window_host_proof,
    )
    assert len(built.windows) == 1


def test_tamper_16_writer_rejects_caller_tampered_record_digest_before_attempt_exists(
    tmp_path: Path,
):
    bundle = _bundle(tmp_path)
    original = bundle.result.window_host_claims
    fake_row = original.resolutions[0].model_copy(
        update={"resolution_sha256": "0" * 64},
    )
    fake_claims = original.model_copy(
        update={"resolutions": (fake_row,)},
    )
    forged = dataclasses.replace(bundle.result, window_host_claims=fake_claims)
    manifest = RunManifestV2(
        case="writer-tamper", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="writer_window_host_claims_drift"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=forged, report=_report(),
        )
    assert not (tmp_path / "1_correction" / "attempts").exists()


def test_tamper_17_finalize_symbol_patch_produces_fake_claims_but_writer_uses_true_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    import src.agent.correction.finalize as finalize_module
    from src.agent.correction.finalize import finalize_correction_draw
    from src.agent.correction.parse import correction_target
    from src.agent.correction.schema import CorrectedGeometryV3
    from src.agent.correction.window_host import resolve_window_hosts as true_resolve

    bundle = _bundle(tmp_path)

    class FinalizeOnlyForgedClaims:
        """Behave truthfully for the commit recheck, then expose a fake digest."""

        def __init__(self, genuine):
            self.genuine = genuine
            fake_row = genuine.resolutions[0].model_copy(
                update={"resolution_sha256": "0" * 64},
            )
            self.fake = genuine.model_copy(update={"resolutions": (fake_row,)})
            self.resolution_reads = 0

        def __eq__(self, _other):
            return not self.resolution_reads

        def __ne__(self, _other):
            return bool(self.resolution_reads)

        @property
        def resolutions(self):
            self.resolution_reads += 1
            return (
                self.genuine.resolutions
                if self.resolution_reads == 1
                else self.fake.resolutions
            )

        def __getattr__(self, name):
            return getattr(self.fake if self.resolution_reads else self.genuine, name)

    def patched_finalize_resolver(*args, **kwargs):
        return FinalizeOnlyForgedClaims(true_resolve(*args, **kwargs))

    monkeypatch.setattr(
        finalize_module, "resolve_window_hosts", patched_finalize_resolver
    )
    forged = finalize_correction_draw(
        CorrectedGeometryV3.model_validate_json(
            bundle.verified.producer_draw_canonical_bytes
        ),
        vector_dir=tmp_path,
        verified_window_inputs=bundle.verified,
        target=correction_target("orthogonal_polygon"),
    )
    assert forged.window_host_claims.resolutions[0].resolution_sha256 == "0" * 64
    manifest = RunManifestV2(
        case="dual-probe", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="writer_window_host_claims_drift"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=forged, report=_report(),
        )


def test_d1_writer_rejects_v3_with_all_b5_fields_missing_even_zero_window(
    tmp_path: Path,
):
    bundle = _bundle(tmp_path, include_window=False)
    stripped = dataclasses.replace(
        bundle.result,
        window_host_claims=None,
        window_evidence_ledger=None,
        verified_window_resolver_inputs=None,
        prepared_candidate_identity=None,
    )
    manifest = RunManifestV2(
        case="no-v3-b2-backdoor", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="all four B5 trust-root fields"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=stripped, report=_report(),
        )
    assert manifest.accepted("1_correction") is None


def test_d2_accepted_loader_rejects_v3_record_downgraded_to_b2_without_proof(
    tmp_path: Path,
):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    record.artifact_contract = "correction_b2_v1"
    for key, filename in (
        ("window_resolver_inputs", "window_resolver_inputs.json"),
        ("window_hosts", "window_hosts.json"),
    ):
        record.artifact_hashes.pop(key)
        (attempt / filename).unlink()

    with pytest.raises(ValueError, match="v3 B5 proof requirement"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("original_room_id", "forged-room"),
        ("original_span", {"lo": 0.5, "hi": 3.0}),
    ],
)
def test_d1_writer_rejects_caller_tampered_original_audit_replay_fields(
    tmp_path: Path, field: str, value,
):
    bundle = _bundle(tmp_path)
    audit = json.loads(json.dumps(bundle.result.audit_payload))
    row = next(
        item for item in audit["corrections"]
        if item.get("kind") == "window_host_resolution"
    )
    row[field] = value
    forged = dataclasses.replace(bundle.result, audit_payload=audit)
    manifest = RunManifestV2(
        case="audit-replay", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="writer_audit_output_drift"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=forged, report=_report(),
        )
    assert not (tmp_path / "1_correction" / "attempts").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("original_room_id", "forged-room"),
        ("original_span", {"lo": 0.5, "hi": 3.0}),
    ],
)
def test_d1_writer_replay_rejects_self_consistent_original_field_forgery(
    tmp_path: Path, field: str, value,
):
    bundle = _bundle(tmp_path)

    def mutate(rows):
        row = next(
            item for item in rows
            if item.get("kind") == "window_host_resolution"
        )
        row[field] = value

    forged = _forge_both_window_audit_copies(bundle.result, mutate)
    manifest = RunManifestV2(
        case="audit-replay-self-consistent", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="writer_window_audit_replay_drift"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=forged, report=_report(),
        )
    assert not (tmp_path / "1_correction" / "attempts").exists()


def test_d1_writer_totality_rejects_self_consistent_missing_audit_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    import src.agent.correction.window_host as window_host_module

    bundle = _bundle(tmp_path)

    def mutate(rows):
        index = next(
            index for index, item in enumerate(rows)
            if item.get("kind") == "window_host_resolution"
        )
        rows.pop(index)

    forged = _forge_both_window_audit_copies(bundle.result, mutate)
    # The production recompute helper independently checks audit totality too.
    # Pin it to the already verified genuine claims so this probe reaches and
    # uniquely locks StageRunner's own writer_window_audit_totality_drift gate.
    monkeypatch.setattr(
        window_host_module,
        "recompute_window_host_claims",
        lambda *_args, **_kwargs: bundle.result.window_host_claims,
    )
    manifest = RunManifestV2(
        case="audit-totality-self-consistent", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256=bundle.manifest.content_sha256),
    )
    with pytest.raises(ValueError, match="writer_window_audit_totality_drift"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=forged, report=_report(),
        )
    assert not (tmp_path / "1_correction" / "attempts").exists()


@pytest.mark.parametrize(
    ("case", "mutate", "error_match"),
    [
        ("output_segment_ref", lambda data: data["windows"][0].__setitem__("facade_segment_id", "forged"), "unknown facade_segment_id"),
        ("output_room", lambda data: data["windows"][0].__setitem__("room", "forged"), "feature-state sidecar does not bind the accepted output bytes"),
        ("output_span", lambda data: data["windows"][0].__setitem__("span", [0.5, 2.5]), "feature-state sidecar does not bind the accepted output bytes"),
        ("segment_p1", lambda data: data["facade_segments"][0].__setitem__("p1", [0.25, 0.0]), "facade segment must be non-zero and axis-aligned"),
        ("segment_p2", lambda data: data["facade_segments"][0].__setitem__("p2", [3.75, 0.0]), "facade segment must be non-zero and axis-aligned"),
        ("segment_normal", lambda data: data["facade_segments"][0].__setitem__("outward_normal", [1, 0]), "facade segment normal must be unit and perpendicular"),
        ("segment_visible", lambda data: data["facade_segments"][0].__setitem__("visible_intervals", []), "feature-state sidecar does not bind the accepted output bytes"),
        ("segment_fingerprint", lambda data: data["facade_segments"][0].__setitem__("source_footprint_fingerprint", "0" * 64), "source_footprint_fingerprint does not match floor footprint"),
    ],
)
def test_tamper_01_to_04_output_fields_fail_closed(
    tmp_path: Path, case: str, mutate, error_match: str,
):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    path = attempt / "output.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _accept_file_mutation(record, path, "output")
    with pytest.raises(ValueError, match=error_match):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


@pytest.mark.parametrize(
    ("case", "path", "value", "error_match"),
    [
        ("record_endpoint", ("claims", "resolutions", 0, "clamped_plan_endpoints_p1_to_p2", 0, "x"), 9.0, "resolution_sha256 does not match canonical host resolution"),
        ("record_vertex", ("claims", "resolutions", 0, "clamped_vertices", 0, "x"), 9.0, "resolution_sha256 does not match canonical host resolution"),
        ("record_t", ("claims", "resolutions", 0, "segment_parameter_interval", "lo"), 0.1, "resolution_sha256 does not match canonical host resolution"),
        ("record_digest", ("claims", "resolutions", 0, "resolution_sha256"), "0" * 64, "resolution_sha256 does not match canonical host resolution"),
        ("aggregate_digest", ("claims", "aggregate_sha256"), "0" * 64, "aggregate_sha256 does not match ordered resolution hashes"),
        ("artifact_output", ("output_sha256",), "0" * 64, "window-host artifact output identity mismatch"),
    ],
)
def test_tamper_05_to_10_host_artifact_fields_fail_closed(
    tmp_path: Path, case: str, path: tuple, value, error_match: str,
):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    artifact_path = attempt / "window_hosts.json"
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    cursor = data
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    artifact_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _accept_file_mutation(record, artifact_path, "window_hosts")
    with pytest.raises(ValueError, match=error_match):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_tamper_11_raw_reading_hash_change_is_rejected(tmp_path: Path):
    _bundle_obj, manifest, _record, _attempt = _accepted(tmp_path)
    reading = tmp_path / "0_reading" / "plan.json"
    reading.write_bytes(reading.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source_catalog|reading_artifacts|source_identity"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def _resign_resolver_artifact(record, path: Path, mutate) -> None:
    from src.agent.correction.window_sources import canonical_sha256

    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    inner = data["inputs"]
    inner["content_sha256"] = canonical_sha256({
        key: value for key, value in inner.items() if key != "content_sha256"
    })
    data["content_sha256"] = canonical_sha256({
        key: value for key, value in data.items() if key != "content_sha256"
    })
    path.write_text(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    _accept_file_mutation(record, path, "window_resolver_inputs")


def test_tamper_11_source_locator_is_independently_rejected(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    path = attempt / "window_resolver_inputs.json"
    _resign_resolver_artifact(
        record, path,
        lambda data: data["inputs"]["source_windows"][0].__setitem__(
            "source_locator", "src:" + "0" * 64
        ),
    )
    with pytest.raises(ValueError, match="source_identity|source_locator|resolver"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_tamper_11_manifest_hash_is_independently_rejected(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    path = attempt / "window_resolver_inputs.json"
    _resign_resolver_artifact(
        record, path,
        lambda data: data["inputs"]["view_manifest"].__setitem__(
            "content_sha256", "0" * 64
        ),
    )
    with pytest.raises(ValueError, match="manifest|source_identity|artifact"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_tamper_11_direction_fact_is_independently_rejected(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(
        tmp_path, include_elevation=True
    )
    path = attempt / "window_resolver_inputs.json"
    _resign_resolver_artifact(
        record, path,
        lambda data: data["inputs"]["elevation_direction_facts"][0].__setitem__(
            "mirrored", True
        ),
    )
    with pytest.raises(ValueError, match="direction|resolver|source_identity"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_d2_integrated_reauthenticates_embedded_raw_sources_without_signature_drift(
    tmp_path: Path,
):
    from src.agent.correction.feature_state import FeatureStatesArtifactV1
    from src.agent.correction.window_sources import (
        canonical_sha256,
        serialize_window_resolver_inputs_artifact,
    )

    bundle = _bundle(tmp_path)
    signature = inspect.signature(verify_integrated_gate1_correction)
    assert tuple(signature.parameters) == (
        "raw_output_bytes",
        "correction_report",
        "feature_states",
        "raw_window_resolver_inputs_bytes",
        "raw_window_hosts_bytes",
    )
    resolver = json.loads(
        serialize_window_resolver_inputs_artifact(bundle.verified).decode("utf-8")
    )
    feature_states = FeatureStatesArtifactV1.model_validate_json(
        bundle.result.prepared_candidate_identity.feature_states_bytes
    )
    with pytest.raises(ValueError, match="complete B5 resolver/host proof bundle"):
        verify_integrated_gate1_correction(
            raw_output_bytes=bundle.result.prepared_candidate_identity.output_bytes,
            correction_report=_report(),
            feature_states=feature_states,
        )
    resolver["raw_reading_artifacts"][0]["raw_bytes"] += " "
    resolver["content_sha256"] = canonical_sha256({
        key: value for key, value in resolver.items() if key != "content_sha256"
    })
    tampered_resolver = json.dumps(
        resolver, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="source|reading|resolver"):
        verify_integrated_gate1_correction(
            raw_output_bytes=bundle.result.prepared_candidate_identity.output_bytes,
            correction_report=_report(),
            feature_states=feature_states,
            raw_window_resolver_inputs_bytes=tampered_resolver,
            raw_window_hosts_bytes=bundle.artifact.model_dump_json(indent=2).encode("utf-8"),
        )


def test_tamper_12_stage_record_artifact_hash_is_rejected(tmp_path: Path):
    _bundle_obj, manifest, record, _attempt = _accepted(tmp_path)
    record.artifact_hashes["window_hosts"] = "0" * 64
    with pytest.raises(ValueError, match="artifact_hashes"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_tamper_13_self_consistent_output_sha_still_fails_relation_gate(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    from src.agent.correction.window_sources import canonical_sha256

    output = attempt / "output.json"
    data = json.loads(output.read_text(encoding="utf-8"))
    data["windows"][0]["room"] = "forged-room"
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _accept_file_mutation(record, output, "output")

    # Attacker also repairs every ordinary artifact SHA/content hash.  The
    # independent room/segment/source recomputation must still reject.
    states_path = attempt / "feature_states.json"
    states = json.loads(states_path.read_text(encoding="utf-8"))
    states["output_sha256"] = record.output_hash
    states_path.write_text(json.dumps(states, indent=2), encoding="utf-8")
    _accept_file_mutation(record, states_path, "feature_states")

    hosts_path = attempt / "window_hosts.json"
    hosts = json.loads(hosts_path.read_text(encoding="utf-8"))
    hosts["output_sha256"] = record.output_hash
    evidence = hosts["evidence"]
    evidence["output_sha256"] = record.output_hash
    evidence["feature_states_sha256"] = record.artifact_hashes["feature_states"]
    evidence["content_sha256"] = canonical_sha256({
        key: value for key, value in evidence.items() if key != "content_sha256"
    })
    hosts["content_sha256"] = canonical_sha256({
        key: value for key, value in hosts.items() if key != "content_sha256"
    })
    hosts_path.write_text(json.dumps(hosts, indent=2), encoding="utf-8")
    _accept_file_mutation(record, hosts_path, "window_hosts")
    with pytest.raises(ValueError, match="resolver_output_tampered|host|room"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


@pytest.mark.parametrize(
    ("artifact_key", "filename"),
    [
        ("output", "output.json"),
        ("checks", "checks.json"),
        ("audit", "audit.json"),
        ("feature_states", "feature_states.json"),
        ("window_resolver_inputs", "window_resolver_inputs.json"),
        ("window_hosts", "window_hosts.json"),
    ],
)
def test_tamper_14_each_missing_six_artifact_is_rejected(
    tmp_path: Path, artifact_key: str, filename: str,
):
    _bundle_obj, manifest, _record, attempt = _accepted(tmp_path)
    (attempt / filename).unlink()
    with pytest.raises(ValueError, match="missing|hash|output.json"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def _orientation_result(base):
    resolution_input, evidence_bytes = build_orientation_resolution_input(
        base_correction_sha256=base.ref.output_sha256,
        evidence_set=OrientationEvidenceSetV1(),
        completion_mode="prior_fill",
    )
    resolution_bytes = resolution_input.model_dump_json(indent=2).encode("utf-8")
    config_bytes = OrientationRunConfigV1(
        completion_mode="prior_fill",
    ).model_dump_json(indent=2).encode("utf-8")
    verified_resolution = verify_orientation_resolution(
        raw_resolution_input_bytes=resolution_bytes,
        raw_evidence_set_bytes=evidence_bytes,
        raw_run_config_bytes=config_bytes,
    )
    return finalize_orientation_enrichment(base, verified_resolution)


def test_tamper_15_orientation_cannot_reuse_base_window_hosts_bytes(tmp_path: Path):
    _bundle_obj, manifest, _record, _attempt = _accepted(tmp_path)
    base = load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)
    base_hosts = base.raw_window_hosts_bytes
    enriched = _orientation_result(base)
    StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj=enriched, report=_report(),
    )
    record = manifest.accepted("1_correction")
    attempt = tmp_path / "1_correction" / "attempts" / f"{record.accepted_attempt:03d}"
    hosts_path = attempt / "window_hosts.json"
    hosts_path.write_bytes(base_hosts)
    _accept_file_mutation(record, hosts_path, "window_hosts")
    with pytest.raises(ValueError, match="output|bind"):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_d3_orientation_enrichment_rejects_changed_host_relationship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    import src.agent.correction.window_host as window_host_module
    from src.agent.correction.window_host import (
        WindowHostClaimsV1,
        WindowHostResolutionV1,
        WindowHostsArtifactV1,
    )
    from src.agent.correction.window_sources import canonical_sha256

    _bundle_obj, manifest, _record, _attempt = _accepted(tmp_path)
    base = load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)
    base_hosts = WindowHostsArtifactV1.model_validate_json(
        base.raw_window_hosts_bytes
    )
    resolution_data = base_hosts.claims.resolutions[0].model_dump()
    resolution_data["room_id"] = "forged-room"
    resolution_data["resolution_sha256"] = canonical_sha256({
        key: value
        for key, value in resolution_data.items()
        if key != "resolution_sha256"
    })
    forged_resolution = WindowHostResolutionV1.model_validate(resolution_data)
    claims_data = base_hosts.claims.model_dump()
    claims_data["resolutions"] = (forged_resolution.model_dump(),)
    claims_data["aggregate_sha256"] = canonical_sha256(
        [forged_resolution.resolution_sha256]
    )
    forged_claims = WindowHostClaimsV1.model_validate(claims_data)
    assert forged_claims != base_hosts.claims

    true_recompute = window_host_module.recompute_window_host_claims
    call_count = 0

    def recompute_then_forge(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # The proof-consumption boundary must still authenticate the base.
            return true_recompute(*args, **kwargs)
        return forged_claims

    monkeypatch.setattr(
        window_host_module,
        "recompute_window_host_claims",
        recompute_then_forge,
    )
    with pytest.raises(ValueError, match="changed the host relationship"):
        _orientation_result(base)
    assert call_count == 2


def test_tamper_18_loader_parse_exception_never_returns_accepted_marker(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    output = attempt / "output.json"
    output.write_bytes(b"{")
    _accept_file_mutation(record, output, "output")
    with pytest.raises(ValueError):
        load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)


def test_tamper_19_parent_internal_exception_never_returns_build_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    import src.agent.geometry.modelling as modelling

    bundle, manifest, _record, _attempt = _accepted(tmp_path)
    verified = load_verified_accepted_correction(run_dir=tmp_path, manifest=manifest)

    def explode(**_kwargs):
        raise RuntimeError("parent resolver injected failure")

    monkeypatch.setattr(modelling, "_v3_parent_candidates", explode)
    with pytest.raises(RuntimeError, match="injected failure"):
        build_geometry(
            bundle.result.geom,
            capability_profile="orthogonal_polygon",
            window_host_proof=verified.window_host_proof,
        )


def test_source_scan_has_no_broad_exception_fail_open_in_trust_boundaries():
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "src/agent/correction/window_host.py",
        "src/agent/execution/stage_runner.py",
        "src/agent/output_coordinates.py",
        "src/agent/geometry/build.py",
        "src/agent/geometry/modelling.py",
        "src/agent/correction/window_sources.py",
        "src/agent/correction/orientation.py",
    ):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"), filename=rel)
        broad_handlers = [
            handler.lineno
            for handler in ast.walk(tree)
            if isinstance(handler, ast.ExceptHandler)
            and handler.type is not None
            and any(
                isinstance(node, ast.Name)
                and node.id in {"Exception", "BaseException"}
                for node in ast.walk(handler.type)
            )
        ]
        assert broad_handlers == [], (
            f"{rel} contains broad Exception/BaseException handlers at "
            f"lines {broad_handlers}"
        )


def test_d3_report_reads_manifest_accepted_host_and_evidence_not_root_copy(tmp_path: Path):
    _bundle_obj, _manifest, _record, _attempt = _accepted(tmp_path)
    root_copy = tmp_path / "1_correction" / "corrections.json"
    root_copy.write_text('{"corrections":[{"kind":"forged-root"}]}', encoding="utf-8")
    reportable = load_reportable_correction_audit(tmp_path)
    assert reportable is not None
    assert reportable.path.name == "audit.json"
    assert reportable.window_host_rows[0]["branch"] == "plan"
    assert reportable.window_host_rows[0]["clamped_span"] == {"lo": 1.0, "hi": 3.0}
    assert reportable.window_host_rows[0]["corroboration_status"] == "uncorroborated"


def test_d3_report_blocks_bad_audit_resolution_hash(tmp_path: Path):
    _bundle_obj, manifest, record, attempt = _accepted(tmp_path)
    audit_path = attempt / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    row = next(item for item in audit["corrections"] if item.get("kind") == "window_host_resolution")
    row["resolution_sha256"] = "0" * 64
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    _accept_file_mutation(record, audit_path, "audit")
    manifest.save(tmp_path)
    with pytest.raises(ValueError, match="resolution hash mismatch"):
        load_reportable_correction_audit(tmp_path)


def test_d3_report_reads_typed_conflict_reason_from_rejected_attempt_only(
    tmp_path: Path,
):
    _bundle_obj, _manifest, _record, _attempt = _accepted(tmp_path)
    rejected = tmp_path / "1_correction" / "attempts" / "002"
    rejected.mkdir()
    report = CheckReport(
        stage="1_correction", capability_profile="orthogonal_polygon"
    )
    report.add_fail(
        "correction.window_host_resolution",
        CheckLayer.INVARIANT,
        "typed host conflict",
    )
    (rejected / "checks.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    conflict = {
        "kind": "window_host_conflict",
        "conflict_schema_version": "1",
        "window_id": "w1",
        "floor_id": "f1",
        "branch": "plan",
        "reason_code": "cross_segment_boundary",
        "raw_span": {"lo": 1.0, "hi": 3.0},
        "source_input_ids": ["plan"],
        "candidate_segment_ids": [],
        "candidate_room_ids": [],
        "crossed_segment_ids": ["seg-a", "seg-b"],
        "trusted_negative": [],
        "upstream_error_code": None,
        "failed_gate_id": "correction.window_host_resolution",
        "fallback_action": "needs_input_no_geometry_commit",
        "blocking": True,
    }
    (rejected / "audit.json").write_text(
        json.dumps({"corrections": [], "conflicts": [conflict], "unsupported": []}, indent=2),
        encoding="utf-8",
    )
    # A forged root mirror must neither supply nor override rejected evidence.
    (tmp_path / "1_correction" / "corrections.json").write_text(
        json.dumps({"conflicts": [{"reason_code": "forged-root"}]}),
        encoding="utf-8",
    )
    reportable = load_reportable_correction_audit(tmp_path)
    assert reportable.rejected_window_host_conflicts == ({
        "attempt": 2,
        "window_id": "w1",
        "reason_code": "cross_segment_boundary",
        "branch": "plan",
        "failed_gate_id": "correction.window_host_resolution",
        "fallback_action": "needs_input_no_geometry_commit",
        "upstream_error_code": None,
        "audit_path": "1_correction/attempts/002/audit.json",
    },)


# ---------------------------------------------------------------------------
# F-20: validate_case must thread the V2 accepted-attempt trust root (loaded
# via load_verified_accepted_correction, the same function 7 production call
# sites already use) into all three geometry-consumer sites — check_correction
# / build_geometry / check_kernel — instead of rebuilding from the untrusted
# stage-root convenience copy without any window_host_proof at all. Design
# authority: AI_agent/proposals/f20_validate_case_v3_proof_design.md §4 (L1-L8).
# ---------------------------------------------------------------------------

_TRUST_CHECK_ID = "correction.accepted_artifact_trust"


def _write_canonical_2_3(run_dir: Path, bg) -> None:
    """F-5 discipline: never hand-write 2/3 fixture artifacts — always go
    through the exact canonical serializers validate_case's own S2/S3
    on-disk-consistency checks compare against."""
    zone_specs, surface_specs, fen_specs, _used = serialize_geometry(bg)
    (run_dir / "2_modelling").mkdir(parents=True, exist_ok=True)
    (run_dir / "2_modelling" / "building_geometry.json").write_text(
        building_geometry_json(bg), encoding="utf-8",
    )
    (run_dir / "3_split_pairing").mkdir(parents=True, exist_ok=True)
    (run_dir / "3_split_pairing" / "geometry_specs.md").write_text(
        geometry_specs_markdown(zone_specs, surface_specs, fen_specs), encoding="utf-8",
    )


def _trust_row(report: CheckReport):
    return next(r for r in report.results if r.check_id == _TRUST_CHECK_ID)


def _minimal_intake_output() -> IntakeOutput:
    return IntakeOutput(
        building=BuildingSchema(name="F20Probe"),
        site_location=SiteLocationSchema(
            name="F20", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0,
        ),
        zone_specs="n/a", material_specs="n/a", schedule_specs="n/a",
        construction_specs="n/a", surface_specs="n/a", fenestration_specs="n/a",
        hvac_specs="n/a", people_specs="n/a", lights_specs="n/a",
    )


def _assert_direct_no_proof_entry_points_still_fail(bundle) -> None:
    """§4 shared self-proving precondition for every F-20 lock below: prove
    that, absent the fix, the three DIRECT no-proof entry points still refuse
    this exact geometry (a pre-existing v3/B5 contract that F-20 must not
    touch) — so a later PASS through validate_case proves the fix threads a
    real accepted-attempt proof through, not that this precondition quietly
    stopped applying."""
    with pytest.raises(ValueError, match="v3 build requires VerifiedWindowHostProof"):
        build_geometry(bundle.result.geom, capability_profile="orthogonal_polygon")

    crep = check_correction(bundle.result.geom, capability_profile="orthogonal_polygon")
    host_row = next(r for r in crep.results if r.check_id == "correction.window_host_resolution")
    assert host_row.status == CheckStatus.FAIL

    krep = check_kernel(bundle.bg, capability_profile="orthogonal_polygon")
    host_row = next(r for r in krep.results if r.check_id == "kernel.window_parent_binding")
    assert host_row.status == CheckStatus.FAIL


def _legacy_geom() -> CorrectedGeometry:
    return CorrectedGeometry.model_validate({
        "footprint_x": [0.0, 4.0],
        "footprint_y": [0.0, 4.0],
        "floors": [{
            "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "cells": [{"id": "C1", "role": "office", "x": [0.0, 4.0], "y": [0.0, 4.0]}],
        }],
        "windows": [], "conflicts": [], "corrections": [], "unsupported": [],
    })


def _write_legacy_stage_root(run_dir: Path):
    """A pre-B5 (schema v1) correction geometry read straight off the
    stage-root convenience copy — the audit path F-20 must leave untouched
    for runs with no manifest / a grandfathered V1 manifest."""
    geom = _legacy_geom()
    stage_dir = run_dir / "1_correction"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "correction_geometry_snapped.json").write_text(
        geom.model_dump_json(), encoding="utf-8",
    )
    bg = build_geometry(geom, capability_profile="rectangular")
    _write_canonical_2_3(run_dir, bg)
    return geom, bg


@pytest.mark.parametrize("include_window", [True, False], ids=["with-window", "zero-window"])
def test_f20_l1_v3_accepted_proof_reaches_validate_case(tmp_path: Path, include_window: bool):
    bundle, manifest, record, attempt = _accepted(tmp_path, include_window=include_window)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    res = validate_case(tmp_path, policy=policy)

    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.PASS
    assert res.reports["1_correction"].passed, res.reports["1_correction"].blocking()
    host_row = next(
        r for r in res.reports["1_correction"].results
        if r.check_id == "correction.window_host_resolution"
    )
    assert host_row.status == CheckStatus.PASS
    assert res.reports["2_modelling"].passed, res.reports["2_modelling"].blocking()
    kernel_host_row = next(
        r for r in res.reports["2_modelling"].results
        if r.check_id == "kernel.window_parent_binding"
    )
    assert kernel_host_row.status == CheckStatus.PASS
    assert res.geometry_digest is not None

    provision_run_policy(tmp_path, run_profile="exploratory", capability_profile="orthogonal_polygon")
    appr = approve_geometry(tmp_path, actor="f20-lock", timestamp="2026-08-10T00:00:00Z")
    assert appr is not None
    assert appr.digest == res.geometry_digest

    # Scope-conservation tail (§2.5): break the upstream trust chain so a
    # full validate would now hard-reject, then prove --intake-from's early
    # return still never reaches the resolver at all — it only ever produces
    # the 5_intakeoutput report, digest stays None.
    (attempt / "output.json").write_bytes((attempt / "output.json").read_bytes() + b" ")
    broken = validate_case(tmp_path, policy=policy)
    assert not broken.reports["1_correction"].passed

    (tmp_path / "5_intakeoutput").mkdir(parents=True, exist_ok=True)
    (tmp_path / "5_intakeoutput" / "intake_output.json").write_text(
        _minimal_intake_output().model_dump_json(), encoding="utf-8",
    )
    downstream = validate_case(
        tmp_path, policy=RunPolicy(validation_scope=ValidationScope.DOWNSTREAM_ONLY),
    )
    assert set(downstream.reports) == {"5_intakeoutput"}
    assert downstream.geometry_digest is None


def test_f20_l2_tampered_accepted_output_is_fail_closed_no_stage_root_fallback(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None

    stage_root = tmp_path / "1_correction" / "correction_geometry_snapped.json"
    stage_root_before = stage_root.read_bytes()
    output_path = attempt / "output.json"
    output_path.write_bytes(output_path.read_bytes() + b" ")

    res = validate_case(tmp_path, policy=policy)
    assert stage_root.read_bytes() == stage_root_before  # only the accepted attempt was mutated

    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.FAIL
    assert res.geometry_digest is None
    # Must not fall into the generic "kernel build failed" bucket, and must
    # not fall back to the still-clean stage-root convenience copy.
    assert "2_modelling" not in res.reports


def test_f20_l3_missing_six_artifact_file_is_fail_closed(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    assert set(record.artifact_hashes) == {
        "output", "checks", "audit", "feature_states",
        "window_resolver_inputs", "window_hosts",
    }
    assert {p.name for p in attempt.iterdir()} == {
        "output.json", "checks.json", "audit.json", "feature_states.json",
        "window_resolver_inputs.json", "window_hosts.json",
    }
    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None

    (attempt / "window_hosts.json").unlink()
    res = validate_case(tmp_path, policy=policy)
    assert _trust_row(res.reports["1_correction"]).status == CheckStatus.FAIL
    assert res.geometry_digest is None
    assert "2_modelling" not in res.reports


def test_f20_l4_v3_downgraded_to_non_b5_contract_is_fail_closed(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    output_schema = json.loads((attempt / "output.json").read_text())["schema_version"]
    assert str(output_schema) == "3"
    assert record.artifact_contract == "correction_b5_v1"
    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None

    record.artifact_contract = "correction_b2_v1"
    for key, filename in (
        ("window_resolver_inputs", "window_resolver_inputs.json"),
        ("window_hosts", "window_hosts.json"),
    ):
        record.artifact_hashes.pop(key)
        (attempt / filename).unlink()
    manifest.save(tmp_path)

    res = validate_case(tmp_path, policy=policy)
    assert _trust_row(res.reports["1_correction"]).status == CheckStatus.FAIL
    assert res.geometry_digest is None


def test_f20_l5_stage_root_convenience_copy_tamper_does_not_affect_v2_authority(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    stage_root = tmp_path / "1_correction" / "correction_geometry_snapped.json"
    accepted_output = attempt / "output.json"
    assert stage_root.read_bytes() == accepted_output.read_bytes()

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None
    accepted_hash_before = record.output_hash

    stage_root_data = json.loads(stage_root.read_text())
    stage_root_data["windows"][0]["room"] = "forged-room"
    stage_root.write_text(json.dumps(stage_root_data, indent=2), encoding="utf-8")

    res = validate_case(tmp_path, policy=policy)
    assert stage_root.read_bytes() != accepted_output.read_bytes()  # only stage-root changed
    assert record.output_hash == accepted_hash_before  # accepted manifest hash untouched

    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.PASS  # V2 authority is unaffected by the tampered copy
    assert res.geometry_digest == clean.geometry_digest  # identical rebuild — copy was never consulted


def test_f20_l6_legacy_no_manifest_and_v1_manifest_continue_to_be_auditable(tmp_path: Path):
    # --- half 1: the V2/v3 positive path, paired per the design so this lock
    # is red (pre-fix) on the real F-20 defect, not merely on a formality ---
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    v2_res = validate_case(tmp_path, policy=RunPolicy(capability_profile="orthogonal_polygon"))
    assert _trust_row(v2_res.reports["1_correction"]).status == CheckStatus.PASS
    assert v2_res.geometry_digest is not None

    # --- half 2a: no manifest at all — the pre-F-20 behaviour must be
    # unchanged: this already passes today, and must keep passing. ---
    no_manifest_dir = tmp_path / "no_manifest"
    _write_legacy_stage_root(no_manifest_dir)
    assert not (no_manifest_dir / "_run" / "run_manifest.json").exists()
    res_a = validate_case(no_manifest_dir)
    trust_a = _trust_row(res_a.reports["1_correction"])
    assert trust_a.status == CheckStatus.NOT_APPLICABLE
    assert res_a.reports["2_modelling"].passed
    assert res_a.geometry_digest is not None
    # validate_case is read-only: it must never write/upgrade a manifest.
    assert not (no_manifest_dir / "_run" / "run_manifest.json").exists()
    res_a2 = validate_case(no_manifest_dir)
    assert res_a2.geometry_digest == res_a.geometry_digest  # stable across repeat runs

    # --- half 2b: a legit, grandfathered V1 manifest present ---
    v1_dir = tmp_path / "v1_manifest"
    _write_legacy_stage_root(v1_dir)
    v1_manifest = RunManifest(case="v1-legacy")
    assert v1_manifest.manifest_version == "1"
    v1_manifest.save(v1_dir)
    res_b = validate_case(v1_dir)
    trust_b = _trust_row(res_b.reports["1_correction"])
    assert trust_b.status == CheckStatus.NOT_APPLICABLE
    assert res_b.reports["2_modelling"].passed
    assert res_b.geometry_digest is not None
    on_disk_after = json.loads((v1_dir / "_run" / "run_manifest.json").read_text())
    assert on_disk_after["manifest_version"] == "1"  # never silently upgraded to V2


def test_f20_l7_v3_geometry_under_legacy_manifest_state_is_fail_closed(tmp_path: Path):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None

    manifest_path = tmp_path / "_run" / "run_manifest.json"
    assert json.loads(manifest_path.read_text())["manifest_version"] == "2"
    manifest_path.unlink()  # no manifest at all — the v3 stage-root geometry stays put
    res_no_manifest = validate_case(tmp_path, policy=policy)
    trust_no_manifest = _trust_row(res_no_manifest.reports["1_correction"])
    assert trust_no_manifest.status == CheckStatus.FAIL
    assert res_no_manifest.geometry_digest is None

    v1 = RunManifest(case="v1-with-v3-geometry")
    v1.save(tmp_path)
    res_v1 = validate_case(tmp_path, policy=policy)
    trust_v1 = _trust_row(res_v1.reports["1_correction"])
    assert trust_v1.status == CheckStatus.FAIL
    assert res_v1.geometry_digest is None


def test_f20_l8_unknown_resolver_exception_is_error_not_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    import src.agent.execution.validation_run as validation_run_module

    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS

    call_count = 0

    def sentinel(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("f20-l8-sentinel-unexpected-failure")

    monkeypatch.setattr(validation_run_module, "load_verified_accepted_correction", sentinel)
    res = validate_case(tmp_path, policy=policy)
    assert call_count == 1  # exactly once — neither skipped nor called redundantly

    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.ERROR
    assert res.geometry_digest is None
    assert "2_modelling" not in res.reports


@pytest.mark.parametrize(
    ("mutate", "case_id"),
    [
        (lambda p: p.write_text("{not valid json", encoding="utf-8"), "invalid-json"),
        (
            lambda p: p.write_text(
                json.dumps({"manifest_version": "99", "case": "x"}), encoding="utf-8",
            ),
            "unknown-version",
        ),
    ],
    ids=["invalid-json", "unknown-version"],
)
def test_f20_nit1_unparseable_manifest_is_fail_closed_not_treated_as_no_manifest(
    tmp_path: Path, mutate, case_id: str,
):
    bundle, manifest, record, attempt = _accepted(tmp_path)
    _assert_direct_no_proof_entry_points_still_fail(bundle)
    _write_canonical_2_3(tmp_path, bundle.bg)
    policy = RunPolicy(capability_profile="orthogonal_polygon")

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS

    manifest_path = tmp_path / "_run" / "run_manifest.json"
    mutate(manifest_path)

    res = validate_case(tmp_path, policy=policy)
    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.FAIL
    # ⛔ must not be silently absorbed into "no manifest" (fail-open onto the
    # untrusted stage-root convenience copy).
    assert trust.status != CheckStatus.NOT_APPLICABLE
    assert res.geometry_digest is None


def _write_legacy_v2_accepted(tmp_path: Path):
    """A legacy-SCHEMA correction accepted under a genuine V2 manifest
    (``base_v2`` contract, no B5 fields at all).

    This exists solely to isolate the "manifest present but unreadable" code
    path from a masking effect discovered during F-20 neuter review: the
    v3-schema fixture ``_accepted()`` uses for
    ``test_f20_nit1_unparseable_manifest_is_fail_closed_not_treated_as_no_manifest``
    still comes out FAIL after a manifest-corrupted-treated-as-no-manifest
    regression, because ``_resolve_legacy_stage_root`` independently refuses
    any v3 stage-root geometry regardless of *why* it ended up on the legacy
    path. That second check has no opinion on a LEGACY-schema geometry, so
    only a legacy-schema fixture can prove the manifest-unreadable branch
    itself — not a neighbour — is what produces FAIL here."""
    geom = _legacy_geom()
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir(parents=True, exist_ok=True)
    output_text = geom.model_dump_json()
    (stage_dir / "correction_geometry_snapped.json").write_text(output_text, encoding="utf-8")
    attempt = stage_dir / "attempts" / "001"
    attempt.mkdir(parents=True, exist_ok=True)
    (attempt / "output.json").write_text(output_text, encoding="utf-8")
    checks_report = CheckReport(stage="1_correction", capability_profile="rectangular")
    checks_report.add_pass("phase_d.fixture", CheckLayer.INVARIANT)
    checks_text = checks_report.model_dump_json(indent=2)
    (attempt / "checks.json").write_text(checks_text, encoding="utf-8")
    output_hash = hash_text(output_text)
    manifest = RunManifestV2(
        case="legacy-v2", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256="a" * 64),
    )
    manifest.accept(StageRecordV2(
        stage="1_correction", accepted_attempt=1, output_hash=output_hash,
        artifact_contract="base_v2",
        artifact_hashes={"output": output_hash, "checks": hash_text(checks_text)},
    ))
    manifest.save(tmp_path)
    bg = build_geometry(geom, capability_profile="rectangular")
    _write_canonical_2_3(tmp_path, bg)
    return geom, bg, manifest


def test_f20_nit1_legacy_schema_manifest_unreadable_is_fail_closed_not_masked(
    tmp_path: Path,
):
    """Same NIT-1 property as the test above, but on a LEGACY-schema accepted
    correction — this is the variant that actually isolates the
    manifest-unreadable branch (see ``_write_legacy_v2_accepted``'s
    docstring)."""
    _geom, _bg, _manifest = _write_legacy_v2_accepted(tmp_path)
    policy = RunPolicy(capability_profile="rectangular")

    clean = validate_case(tmp_path, policy=policy)
    assert _trust_row(clean.reports["1_correction"]).status == CheckStatus.PASS
    assert clean.geometry_digest is not None

    manifest_path = tmp_path / "_run" / "run_manifest.json"
    manifest_path.write_text("{not valid json", encoding="utf-8")

    res = validate_case(tmp_path, policy=policy)
    trust = _trust_row(res.reports["1_correction"])
    assert trust.status == CheckStatus.FAIL
    assert trust.status != CheckStatus.NOT_APPLICABLE
    assert res.geometry_digest is None
