"""W#3 (wallhunt 2026-09-08b / dispatch 2026-09-08c S-A) — the as_drawn
leg's writer-side chain replay.

WHAT THIS FILE LOCKS:

1. ``StageRunner.record`` ACCEPTS a genuine as_drawn-chain candidate: the
   B5 replay dispatches BY LEG on the candidate's own ``chain_provenance``
   carrier, re-drives the whole chain from the marker's frozen bytes
   (compilations + embedded products) and the shared gauntlet passes
   field-for-field.  The attempt files ``chain_provenance.json`` alongside
   the six B5 artifacts.
2. The replay has TEETH, one named red per tamper class (the F-22
   BLOCKER-1 threat model, transposed to this leg — a caller that forges
   a self-consistent candidate dies at the byte anchors, not at shapes):
   * ``chain_replay_compilation_hash_drift`` — compilation bytes whose body
     no longer match their own ``content_sha256``;
   * ``chain_replay_source_bytes_drift`` — the marker's embedded plan bytes
     are not the bytes the provenance row froze;
   * ``chain_replay_compilation_unbound`` — the compilation was not minted
     from THIS plan product's evidence bundle;
   * ``chain_replay_producer_drift`` — the chain replayed from the frozen
     compilations assembles a different producer than the marker carries
     (the leg's answer to sol's forged-candidate reproduction).
3. OMISSION is loud: an as_drawn geometry minted WITHOUT the carrier routes
   to the legacy replay and reds ``writer_core_projection_drift`` by
   construction — ⛔ never a silent leg skip.
4. ``judge.correction_score`` pairs stamp and proof PER LEG: a chain
   product carrying a legacy proof (or vice versa) is declared but NOT
   trusted, ⛔ no cross-leg mixing.

The happy path is driven through the REAL production chain (elevation
ladder → per-floor evidence chains on the real sm25 as-drawn products,
``fixed_responses`` only for the model beat) → snap → assembly →
``finalize_as_drawn_chain_geometry`` with the frozen compilations →
``StageRunner.record`` — ⛔ zero mocked geometry, so the replay's
byte-compare anchors are exercised against genuine chain bytes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tool_scripts"))

from run_stage import _w1_cross_check_elevation_ladders  # noqa: E402

from src.agent.correction.chain_provenance import (  # noqa: E402
    AsDrawnChainProvenanceV1,
    build_chain_provenance,
)
from src.agent.correction.config import load_core_tolerances  # noqa: E402
from src.agent.correction.finalize import (  # noqa: E402
    FinalizeResult,
    finalize_as_drawn_chain_geometry,
)
from src.agent.correction.parse import correction_target  # noqa: E402
from src.agent.correction.window_sources import (  # noqa: E402
    build_verified_window_inputs_as_drawn,
)
from src.agent.execution.manifest import (  # noqa: E402
    RunInputs,
    RunManifestV2,
    new_run_id,
)
from src.agent.execution.stage_runner import StageRunner  # noqa: E402
from src.agent.execution.view_manifest import ViewManifest  # noqa: E402
from src.agent.pipeline import MultiFloorPlanRun, run_multifloor_correction  # noqa: E402
from src.validator.checks.schema import CheckLayer, CheckReport  # noqa: E402

_AS_DRAWN_OUT = (
    REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_LEGACY_RUN = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_t1_probe2"
_MANIFEST_SRC = _LEGACY_RUN / "_run" / "view_manifest.json"

# manifest input_id -> as_drawn product file in the 08-23 prototype dir
_AS_DRAWN_PRODUCTS = {
    "1f_view": "sm25_1f_v2.json",
    "2f_view": "sm25_2f_v2.json",
    "East_view": "sm25_east_as_drawn.json",
    "North_view": "sm25_north_as_drawn.json",
    "South_view": "sm25_south_as_drawn.json",
    "West_view": "sm25_west_as_drawn.json",
}


def _stage_as_drawn_run(tmp_path: Path) -> Path:
    """Same staging shape as ``test_w1_flow_routing``: manifest + the six
    as_drawn products under their manifest expected_output_id names."""
    run_dir = tmp_path / "run_w3"
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True)
    (run_dir / "_run").mkdir(parents=True)
    (run_dir / "_run" / "view_manifest.json").write_bytes(_MANIFEST_SRC.read_bytes())
    for input_id, name in _AS_DRAWN_PRODUCTS.items():
        (rdir / f"{input_id}.json").write_bytes(
            (_AS_DRAWN_OUT / name).read_bytes()
        )
    return run_dir


def _fixed_responses(rdir: Path, product_filename: str):
    """The deterministic model beat (the ``test_o22m7`` shape): round 0
    selects every open item's FIRST candidate, round 1 accepts."""
    from src.agent.correction.decision_executor import (
        FixedDecisionV1,
        build_decision_packet,
        compile_wall_ir,
        decision_hash,
    )
    from src.agent.correction.decision_schema import (
        CorrectionDecisionResponseV1,
        ItemDecisionV1,
    )
    from src.agent.correction.evidence_adapters import adapt_as_drawn_plan

    stem = Path(product_filename).stem
    raw = (rdir / product_filename).read_bytes()
    artifact = adapt_as_drawn_plan(
        raw, input_id=stem, floor_ref=stem.removesuffix("_view"), view_type="plan"
    )
    packet0 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"), bundle=artifact, round_index=0
    )
    picks = tuple(
        (item.item_id, item.candidates[0].candidate_id)
        for item in packet0.open_items
    )
    select = CorrectionDecisionResponseV1(
        packet_hash=packet0.packet_hash,
        item_decisions=tuple(
            ItemDecisionV1(
                item_id=item_id,
                action="select_candidate",
                candidate_id=candidate_id,
                reason_code="WIRED_LOCK",
            )
            for item_id, candidate_id in picks
        ),
        whole_building_review={"verdict": "accept"},
    )
    packet1 = build_decision_packet(
        compile_wall_ir(
            artifact,
            profile="exploratory",
            decisions=tuple(
                FixedDecisionV1(item_id=i, candidate_id=c) for i, c in picks
            ),
        ),
        bundle=artifact,
        round_index=1,
        previous_decision_hashes=(decision_hash(select),),
    )
    accept = CorrectionDecisionResponseV1(
        packet_hash=packet1.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    return [select, accept]


@dataclass
class _ChainBundle:
    result: FinalizeResult
    run_dir: Path
    manifest: RunManifestV2
    record: object
    attempt: Path


def _chain_bundle(tmp_path: Path) -> _ChainBundle:
    """Drive the REAL chain (fixed model beat) and archive it once."""
    run_dir = _stage_as_drawn_run(tmp_path)
    rdir = run_dir / "0_reading"
    manifest = ViewManifest.model_validate_json(
        (run_dir / "_run" / "view_manifest.json").read_text("utf-8")
    )
    entries = manifest.required_entries()
    plan_entries = sorted(
        (e for e in entries if e.view_type == "plan"), key=lambda e: e.floor_ref
    )
    elevation_entries = [e for e in entries if e.view_type == "elevation"]
    elevation_evidence = _w1_cross_check_elevation_ladders(
        elevation_entries, rdir
    )
    s1 = run_dir / "1_correction"
    plan_runs = [
        MultiFloorPlanRun(
            vector_dir=rdir,
            product_filename=f"{e.expected_output_id}.json",
            out_dir=s1 / f"floor_{e.floor_ref}",
            profile="exploratory",
            fixed_responses=_fixed_responses(
                rdir, f"{e.expected_output_id}.json"
            ),
        )
        for e in plan_entries
    ]
    geom = run_multifloor_correction(
        elevation_evidence,
        plan_runs,
        snap_ledger_path=s1 / "footprint_snap_ledger.json",
        evidence_debt_path=s1 / "evidence_debt.json",
    )
    from src.agent.correction.as_drawn_windows import populate_as_drawn_windows
    from src.agent.correction.facade_visibility import VisibilityTolerances

    tol = load_core_tolerances()
    geom, account = populate_as_drawn_windows(
        geom,
        raw_view_manifest_bytes=(run_dir / "_run" / "view_manifest.json").read_bytes(),
        raw_reading_artifacts={
            entry.input_id: (rdir / f"{entry.expected_output_id}.json").read_bytes()
            for entry in entries
        },
        visibility_tolerances=VisibilityTolerances(
            depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
            endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m,
        ),
    )
    assert account.windows_built == len(geom.windows) == 31
    marker = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=(
            run_dir / "_run" / "view_manifest.json"
        ).read_bytes(),
        raw_reading_artifacts={
            entry.input_id: (rdir / f"{entry.expected_output_id}.json").read_bytes()
            for entry in entries
        },
    )
    provenance = build_chain_provenance([
        {
            "input_id": entry.input_id,
            "product_filename": f"{entry.expected_output_id}.json",
            "floor_ref": f"{entry.floor_ref}f",
            "compilation_bytes": (
                s1 / f"floor_{entry.floor_ref}" / "evidence_chain_compilation.json"
            ).read_bytes(),
            "source_bytes_sha256": hashlib.sha256(
                (rdir / f"{entry.expected_output_id}.json").read_bytes()
            ).hexdigest(),
        }
        for entry in plan_entries
    ])
    result = finalize_as_drawn_chain_geometry(
        geom,
        verified_window_inputs=marker,
        target=correction_target("orthogonal_polygon"),
        chain_provenance=provenance,
    )

    run_manifest = RunManifestV2(
        case="w3-lock",
        run_id=new_run_id(),
        run_inputs=RunInputs(
            view_manifest_sha256=marker.inputs.view_manifest.content_sha256,
        ),
    )
    meta = run_dir / "_run"
    (meta / "view_manifest.json").write_bytes(marker.raw_view_manifest_bytes)
    for input_id, raw in marker.raw_reading_artifacts:
        identity = next(
            row for row in marker.inputs.reading_artifacts if row.input_id == input_id
        )
        (rdir / f"{identity.expected_output_id}.json").write_bytes(raw)
    report = CheckReport(
        stage="1_correction", capability_profile="orthogonal_polygon"
    )
    report.add_pass("w3.fixture", CheckLayer.INVARIANT)
    StageRunner(run_dir, run_manifest).record(
        stage="1_correction",
        stage_dir=s1,
        output_obj=result,
        report=report,
    )
    run_manifest.save(run_dir)
    record = run_manifest.accepted("1_correction")
    attempt = s1 / "attempts" / f"{record.accepted_attempt:03d}"
    return _ChainBundle(result, run_dir, run_manifest, record, attempt)


# ── lock 1: the happy path genuinely archives ──────────────────────────────── #
def test_record_accepts_a_genuine_as_drawn_chain_candidate(tmp_path: Path):
    """The B5 writer dispatches BY LEG on the provenance carrier and the
    chain replay passes the shared gauntlet on genuine chain bytes."""
    bundle = _chain_bundle(tmp_path)
    output = json.loads((bundle.attempt / "output.json").read_bytes())
    assert len(output["windows"]) == 31
    floors = {floor["id"]: floor["name"] for floor in output["floors"]}
    assert all(w["floor"] == floors[w["floor_id"]] for w in output["windows"])
    # The public replay also works with its default tolerance argument.
    from src.agent.correction.chain_replay import replay_as_drawn_chain

    replayed = replay_as_drawn_chain(
        bundle.result.verified_window_resolver_inputs,
        bundle.result.chain_provenance,
        target=correction_target("orthogonal_polygon"),
    )
    assert replayed.prepared_candidate_identity == bundle.result.prepared_candidate_identity
    # the carrier itself is filed alongside the six B5 artifacts
    assert (bundle.attempt / "chain_provenance.json").exists()
    filed = AsDrawnChainProvenanceV1.model_validate_json(
        (bundle.attempt / "chain_provenance.json").read_text("utf-8")
    )
    assert filed == bundle.result.chain_provenance
    assert "chain_provenance" in bundle.record.artifact_hashes
    # the accepted geometry stamps THIS leg's kernel version, ⛔ never "1"
    from src.agent.correction.deterministic import AS_DRAWN_CHAIN_STAMP_VERSION

    stamp = bundle.result.geom.deterministic_core_stamp
    assert stamp is not None and stamp.version == AS_DRAWN_CHAIN_STAMP_VERSION
    # and the proof binds to the frozen compilation bytes, not the producer
    proof = json.loads(
        (bundle.attempt / "deterministic_core_proof.json").read_text("utf-8")
    )
    assert proof["core_version"] == AS_DRAWN_CHAIN_STAMP_VERSION
    assert proof["input_hash"] == bundle.result.chain_provenance.replay_input_hash


# ── lock 2: the replay's byte anchors have teeth ───────────────────────────── #
def _retampered_result(
    bundle: _ChainBundle, *, provenance: AsDrawnChainProvenanceV1
) -> FinalizeResult:
    """Re-present the SAME candidate with a swapped carrier (the rest of
    the result is untouched — the carrier is the only moved part)."""
    import dataclasses

    return dataclasses.replace(bundle.result, chain_provenance=provenance)


def _record_refuses(tmp_path: Path, result: FinalizeResult, needle: str) -> None:
    run_dir = tmp_path / "tamper_run"
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True)
    (run_dir / "_run").mkdir(parents=True)
    marker = result.verified_window_resolver_inputs
    manifest = RunManifestV2(
        case="w3-tamper",
        run_id=new_run_id(),
        run_inputs=RunInputs(
            view_manifest_sha256=marker.inputs.view_manifest.content_sha256,
        ),
    )
    (run_dir / "_run" / "view_manifest.json").write_bytes(
        marker.raw_view_manifest_bytes
    )
    for input_id, raw in marker.raw_reading_artifacts:
        identity = next(
            row for row in marker.inputs.reading_artifacts if row.input_id == input_id
        )
        (rdir / f"{identity.expected_output_id}.json").write_bytes(raw)
    report = CheckReport(
        stage="1_correction", capability_profile="orthogonal_polygon"
    )
    report.add_pass("w3.fixture", CheckLayer.INVARIANT)
    with pytest.raises(ValueError, match=needle):
        StageRunner(run_dir, manifest).record(
            stage="1_correction",
            stage_dir=run_dir / "1_correction",
            output_obj=result,
            report=report,
        )


def test_tampered_compilation_body_is_refused(tmp_path: Path):
    """A re-signed carrier whose compilation body was edited (``content_
    sha256`` kept stale on purpose — the canonical-hash anchor's own
    failure mode) dies at ``chain_replay_compilation_hash_drift``."""
    bundle = _chain_bundle(tmp_path)
    original = bundle.result.chain_provenance
    first = original.floors[0]
    doc = json.loads(first.compilation_bytes.decode("utf-8"))
    doc["completion"] = "complete" if doc.get("completion") != "complete" else "degraded"
    tampered_bytes = json.dumps(doc, indent=2).encode("utf-8")
    tampered = build_chain_provenance([
        {
            "input_id": first.input_id,
            "product_filename": first.product_filename,
            "floor_ref": first.floor_ref,
            "compilation_bytes": tampered_bytes,  # body changed...
            "source_bytes_sha256": first.source_bytes_sha256,
        },
        *[{
            "input_id": row.input_id,
            "product_filename": row.product_filename,
            "floor_ref": row.floor_ref,
            "compilation_bytes": row.compilation_bytes,
            "source_bytes_sha256": row.source_bytes_sha256,
        } for row in original.floors[1:]],
    ])
    _record_refuses(
        tmp_path,
        _retampered_result(bundle, provenance=tampered),
        "chain_replay_compilation_hash_drift",
    )


def test_tampered_source_bytes_are_refused(tmp_path: Path):
    """The provenance row's frozen ``source_bytes_sha256`` re-pointed at the
    OTHER floor's bytes (the sha256 cross-check's own failure mode — the
    marker itself stays genuine and resolver-verified, only the carrier's
    frozen anchor is wrong) dies at ``chain_replay_source_bytes_drift``."""
    bundle = _chain_bundle(tmp_path)
    original = bundle.result.chain_provenance
    first, second = original.floors[0], original.floors[1]
    tampered = build_chain_provenance([
        {
            "input_id": first.input_id,
            "product_filename": first.product_filename,
            "floor_ref": first.floor_ref,
            "compilation_bytes": first.compilation_bytes,
            "source_bytes_sha256": second.source_bytes_sha256,  # wrong anchor
        },
        {
            "input_id": second.input_id,
            "product_filename": second.product_filename,
            "floor_ref": second.floor_ref,
            "compilation_bytes": second.compilation_bytes,
            "source_bytes_sha256": second.source_bytes_sha256,
        },
    ])
    _record_refuses(
        tmp_path,
        _retampered_result(bundle, provenance=tampered),
        "chain_replay_source_bytes_drift",
    )


def test_unbound_compilation_is_refused(tmp_path: Path):
    """A compilation minted from a DIFFERENT plan product's bundle (the
    ``bundle_content_sha256`` binding's failure mode) dies at
    ``chain_replay_compilation_unbound`` — reachable by re-adapting the
    OTHER floor's bytes under this floor's stem, which mints a bundle
    identity that does not match this floor's frozen compilation."""
    bundle = _chain_bundle(tmp_path)
    original = bundle.result.chain_provenance
    rdir = bundle.run_dir / "0_reading"
    first, second = original.floors[0], original.floors[1]
    # Re-compile the OTHER floor's product under the FIRST floor's name:
    # a genuine, canonical compilation — but bound to a different bundle.
    from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
    from src.agent.correction.decision_executor import compile_wall_ir

    raw = (rdir / second.product_filename).read_bytes()
    artifact = adapt_as_drawn_plan(
        raw,
        input_id=Path(first.product_filename).stem,
        floor_ref=first.floor_ref,
        view_type="plan",
    )
    foreign = compile_wall_ir(artifact, profile="exploratory")
    tampered = build_chain_provenance([
        {
            "input_id": first.input_id,
            "product_filename": first.product_filename,
            "floor_ref": first.floor_ref,
            "compilation_bytes": foreign.model_dump_json(indent=2).encode("utf-8"),
            "source_bytes_sha256": first.source_bytes_sha256,
        },
        {
            "input_id": second.input_id,
            "product_filename": second.product_filename,
            "floor_ref": second.floor_ref,
            "compilation_bytes": second.compilation_bytes,
            "source_bytes_sha256": second.source_bytes_sha256,
        },
    ])
    _record_refuses(
        tmp_path,
        _retampered_result(bundle, provenance=tampered),
        "chain_replay_compilation_unbound",
    )


def test_tampered_producer_bytes_are_refused(tmp_path: Path):
    """A SELF-CONSISTENT forged marker (sol's F-22 BLOCKER-1 shape): the
    tampered producer is re-built through the marker's own public
    constructor, so every identity field the resolver re-derives agrees
    with the tampered bytes and the marker passes its own rebuild gate —
    only the writer's chain replay, re-assembling the producer from the
    FROZEN compilations, can see the swap (``chain_replay_producer_drift``)."""
    bundle = _chain_bundle(tmp_path)
    marker = bundle.result.verified_window_resolver_inputs
    from src.agent.correction.schema import CorrectedGeometryV3
    from src.agent.correction.window_sources import (
        build_verified_window_inputs_as_drawn,
    )

    base = CorrectedGeometryV3.model_validate_json(
        marker.producer_draw_canonical_bytes.decode("utf-8")
    )
    tampered_producer = base.model_copy(
        update={
            "footprint_x": [
                float(base.footprint_x[0]),
                float(base.footprint_x[1]) + 0.5,
            ]
        }
    )
    tampered_marker = build_verified_window_inputs_as_drawn(
        producer_draw=tampered_producer,
        raw_view_manifest_bytes=marker.raw_view_manifest_bytes,
        raw_reading_artifacts=dict(marker.raw_reading_artifacts),
    )
    # and RE-FINALIZE the whole candidate from the tampered marker, so the
    # claims / feature states / output identity are all re-derived from the
    # forged producer and every earlier gauntlet gate passes — the ONLY
    # witness left that can see the swap is the chain replay itself.
    tampered_result = finalize_as_drawn_chain_geometry(
        tampered_producer,
        verified_window_inputs=tampered_marker,
        target=correction_target("orthogonal_polygon"),
        chain_provenance=bundle.result.chain_provenance,
    )
    _record_refuses(tmp_path, tampered_result, "chain_replay_producer_drift")


# ── lock 3: omission is loud, ⛔ never a silent leg skip ────────────────────── #
def test_chain_geometry_without_the_carrier_reds_on_the_legacy_replay(
    tmp_path: Path,
):
    """The same genuine chain geometry re-presented WITHOUT the provenance
    carrier routes to the legacy replay and dies at the unchanged
    ``writer_core_projection_drift`` — the omission is loud."""
    bundle = _chain_bundle(tmp_path)
    import dataclasses

    stripped = dataclasses.replace(bundle.result, chain_provenance=None)
    _record_refuses(tmp_path, stripped, "writer_core_projection_drift")


# ── lock 4: the judge pairs stamp and proof PER LEG ────────────────────────── #
def test_cross_leg_stamp_proof_pairs_are_not_trusted(tmp_path: Path):
    """``judge.correction_score`` trusts a stamp/proof PAIR under either
    leg's version — and refuses the MIXED pairs: a chain product carrying
    a legacy proof (and vice versa) is declared but untrusted."""
    from src.agent.correction.deterministic import (
        AS_DRAWN_CHAIN_STAMP_VERSION,
        DETERMINISTIC_CORE_STAMP_VERSION,
        DeterministicCoreProofV1,
        core_owned_projection_v1,
    )
    from src.agent.execution.manifest import hash_obj
    from src.agent.judge import correction_score

    bundle = _chain_bundle(tmp_path)
    geom = bundle.result.geom
    projection_hash = hash_obj(core_owned_projection_v1(geom))

    def _proof(version: str) -> DeterministicCoreProofV1:
        return DeterministicCoreProofV1(
            core_version=version,
            input_hash="0" * 64,
            core_projection_hash=projection_hash,
        )

    # the PAIRED proofs are trusted on this genuine chain product...
    assert correction_score._is_trusted_output_convention(
        geom, core_proof=_proof(AS_DRAWN_CHAIN_STAMP_VERSION)
    )
    # ...and the MIXED pairs are both refused
    assert not correction_score._is_trusted_output_convention(
        geom, core_proof=_proof(DETERMINISTIC_CORE_STAMP_VERSION)
    )
    legacy_like = geom.model_copy(
        update={
            "deterministic_core_stamp": geom.deterministic_core_stamp.model_copy(
                update={"version": DETERMINISTIC_CORE_STAMP_VERSION}
            )
        }
    )
    assert not correction_score._is_trusted_output_convention(
        legacy_like, core_proof=_proof(AS_DRAWN_CHAIN_STAMP_VERSION)
    )
    assert correction_score._is_trusted_output_convention(
        legacy_like, core_proof=_proof(DETERMINISTIC_CORE_STAMP_VERSION)
    )
