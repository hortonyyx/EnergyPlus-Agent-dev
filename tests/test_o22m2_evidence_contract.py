"""②-2 module 2: the correction evidence contract, type layer (2026-08-30).

Dispatch: ``AI_agent/logs/reviews/request/
2026-08-30_o22m2_evidence_contract_dispatch.md`` (with its §六-§八 supplement:
four task items, nine acceptance items).

What lives here
---------------
``evidence_contract`` is the TYPE layer plus the validator for hard
invariants 1-8.  It wires nothing, adapts nothing, and this file never
touches the pipeline.  The bundle-FACTORY below (``_build_from_product`` /
``_build_from_tiny``) is a TEST FIXTURE FACTORY, ⛔ not module 3's adapter:

* its construction-time refusals are early failures, ⛔ not the load-bearing
  teeth -- the load-bearing teeth are ``validate_evidence_bundle``, and every
  corruption family below is ALSO driven through a validator-level mutation
  (or through ``as_drawn_face_index``, a production function the factory
  shares with the validator, so a factory refusal and a validator refusal
  are the same teeth, not two opinions);
* it never parses prose (dispatch ban #5): bucket reasons travel verbatim,
  and ``L012``'s sixth state is never derived -- only proven constructible.

Every "has teeth" test proves its own premise: the green side runs first
(the uncorrupted fixture validates), and where the corruption is a
module-1-era blind spot the test first asserts TODAY's producer type and
classifier still say yes to it, so a green can never be the always-green
kind ([[regression-case-must-prove-its-own-premise]],
[[gate-with-only-negative-assertions-is-unobservable]]).
"""
from __future__ import annotations

import hashlib
import json
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from src.agent.correction.evidence_contract import (
    BUNDLE_SCHEMA_VERSION,
    SOURCE_CONTRACT_AS_DRAWN,
    SOURCE_CONTRACT_LEGACY,
    ArtifactPointerV1,
    ChannelStatusV1,
    CorrectionEvidenceBundleArtifactV1,
    CorrectionEvidenceBundleV1,
    EvidenceContractError,
    EvidenceDebtV1,
    FaceDispositionV1,
    FrozenSourceV1,
    LegacyWallTraceClaimV1,
    ObservationRefV1,
    OpeningClaimV1,
    PairedFacesWallClaimV1,
    SingleFaceWallClaimV1,
    SolidBandWallClaimV1,
    SourceArtifactV1,
    WallClaimV1,
    as_drawn_face_index,
    finalize_bundle,
    validate_evidence_bundle,
    wall_claim_id,
)
from src.agent.correction.window_sources import (
    canonical_json_bytes,
    source_locator,
)
from src.agent.reading.as_drawn.schema import (
    SCHEMA,
    AsDrawnPlanV2,
    FaceLineV2,
    GapV2,
    InkProfileV2,
    PairCandidateV2,
)
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_PLAN,
    CONTRACT_READING_VIEW_LEGACY,
    CONTRACT_UNKNOWN,
    classify_vector_json,
)

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_TRACKED = ("sm25_1f_v2.json", "sm25_2f_v2.json", "sm24_1f_v2.json")

_ABSENT_CHANNELS = ("elevation_openings", "dimensions", "room_roles")


# =========================================================================== #
# The test fixture factory (⛔ not module 3's adapter -- see module docstring)
# =========================================================================== #
def _raw_product(name: str) -> bytes:
    p = _PRODUCTS / name
    # ⛔ never `if p.exists()` + skip: a vanished fixture must be a red
    # ([[absent-file-read-as-passing-check]]).
    assert p.is_file(), f"tracked as-drawn product missing: {p}"
    return p.read_bytes()


def _fref(input_id: str, contract: str, sha: str, pointer: str, oid: str,
          witnesses: tuple[str, ...],
          resolution: str = "pixel_backed") -> ObservationRefV1:
    return ObservationRefV1(
        input_id=input_id,
        source_contract_id=contract,
        source_output_sha256=sha,
        json_pointer=pointer,
        observation_id=oid,
        source_locator=source_locator(
            input_id=input_id, observation_id=oid, output_sha256=sha
        ),
        pixel_witness_pointers=witnesses,
        evidence_resolution=resolution,  # type: ignore[arg-type]
    )


def _pref(input_id: str, contract: str, sha: str, pointer: str) -> ArtifactPointerV1:
    return ArtifactPointerV1(
        input_id=input_id, source_contract_id=contract,
        source_output_sha256=sha, json_pointer=pointer,
    )


def _must_exist(idx: dict, fid: str, what: str) -> None:
    if fid not in idx:
        raise EvidenceContractError(
            f"{what}_REFERENCES_UNKNOWN_FACE", {"observation_id": fid}
        )


def _bundle_from_as_drawn(doc: dict, raw: bytes, input_id: str,
                          floor: str) -> CorrectionEvidenceBundleArtifactV1:
    """Translate ONE as-drawn product into a bundle, mechanically.

    ⛔ No prose is parsed and no geometry value is copied.  Construction-time
    refusals here duplicate checks the validator owns -- see the module
    docstring for why that is not a second opinion.
    """
    sha = hashlib.sha256(raw).hexdigest()
    contract = SOURCE_CONTRACT_AS_DRAWN
    meta = SourceArtifactV1(
        input_id=input_id, source_contract_id=contract,
        source_output_sha256=sha, view_type="plan", floor_ref=floor,
    )
    idx = as_drawn_face_index(doc)  # duplicate ids die here, loudly

    def face_ref(fid: str) -> ObservationRefV1:
        _must_exist(idx, fid, "FACE")
        base = f"/observations/face_lines/{idx[fid][0]}"
        return _fref(input_id, contract, sha, f"{base}", fid,
                     (f"{base}/support_cols_px", f"{base}/runs_px",
                      f"{base}/edges_m", f"{base}/gaps"))

    hyp = doc["hypotheses"]
    claims: list[WallClaimV1] = []
    dispositions: list[FaceDispositionV1] = []
    debts: list[EvidenceDebtV1] = []
    openings: list[OpeningClaimV1] = []

    candidate_at: dict[frozenset, int] = {}
    for k, cand in enumerate(hyp.get("pair_candidates") or []):
        candidate_at.setdefault(frozenset((cand["face_a"], cand["face_b"])), k)
    for j, pair in enumerate(hyp.get("pairs") or []):
        _must_exist(idx, pair["face_a"], "SELECTED_PAIR")
        _must_exist(idx, pair["face_b"], "SELECTED_PAIR")
        key = frozenset((pair["face_a"], pair["face_b"]))
        k = candidate_at.get(key)
        if k is None:
            # design §4.3: a selected pair missing from the candidate graph
            # is reperception_required / an input error -- never a code
            # invented nearest-neighbour leg.
            raise EvidenceContractError(
                "SELECTED_PAIR_NOT_IN_CANDIDATE_GRAPH",
                {"pair_index": j, "faces": sorted(key)},
            )
        a, b = face_ref(pair["face_a"]), face_ref(pair["face_b"])
        claim = PairedFacesWallClaimV1(
            claim_id="pending",
            hypothesis_ref=_pref(input_id, contract, sha, f"/hypotheses/pairs/{j}"),
            perception_source_ref=_pref(input_id, contract, sha, "/hypotheses"),
            source_contract_id=contract,
            face_a_ref=a, face_b_ref=b,
            pair_candidate_ref=_pref(
                input_id, contract, sha, f"/hypotheses/pair_candidates/{k}"
            ),
        )
        claim = claim.model_copy(update={"claim_id": wall_claim_id(claim)})
        claims.append(claim)
        for ref in (a, b):
            dispositions.append(FaceDispositionV1(
                face_ref=ref, status="claimed_wall",
                consuming_claim_id=claim.claim_id,
            ))

    for bucket in ("solid_band_walls", "unpaired_wall_faces"):
        for fid, reason in (hyp.get(bucket) or {}).items():
            _must_exist(idx, fid, "BUCKET_KEY")
            ref = face_ref(fid)
            if bucket == "solid_band_walls":
                claim = SolidBandWallClaimV1(
                    claim_id="pending",
                    hypothesis_ref=_pref(
                        input_id, contract, sha, f"/hypotheses/solid_band_walls/{fid}"
                    ),
                    perception_source_ref=_pref(input_id, contract, sha, "/hypotheses"),
                    source_contract_id=contract,
                    band_face_ref=ref,
                )
            else:
                claim = SingleFaceWallClaimV1(
                    claim_id="pending",
                    hypothesis_ref=_pref(
                        input_id, contract, sha, f"/hypotheses/unpaired_wall_faces/{fid}"
                    ),
                    perception_source_ref=_pref(input_id, contract, sha, "/hypotheses"),
                    source_contract_id=contract,
                    face_ref=ref,
                    original_reason=reason,
                    # ⚠️ mechanical default.  L012's TRUE state is the sixth
                    # one, but deriving it from prose is module 3's job
                    # (dispatch ban #5) -- see the dedicated constructibility
                    # test below.
                    counterface_state="not_in_observations",
                )
            claim = claim.model_copy(update={"claim_id": wall_claim_id(claim)})
            claims.append(claim)
            dispositions.append(FaceDispositionV1(
                face_ref=ref, status="claimed_wall",
                consuming_claim_id=claim.claim_id,
            ))

    for fid in hyp.get("non_wall_face_lines") or {}:
        _must_exist(idx, fid, "BUCKET_KEY")
        dispositions.append(FaceDispositionV1(
            face_ref=face_ref(fid), status="non_wall",
            reason_ref=_pref(
                input_id, contract, sha, f"/hypotheses/non_wall_face_lines/{fid}"
            ),
        ))
    for n, fid in enumerate(hyp.get("ambiguous_face_lines") or {}):
        _must_exist(idx, fid, "BUCKET_KEY")
        ref = face_ref(fid)
        dispositions.append(FaceDispositionV1(
            face_ref=ref, status="ambiguous",
            reason_ref=_pref(
                input_id, contract, sha, f"/hypotheses/ambiguous_face_lines/{fid}"
            ),
        ))
        debts.append(EvidenceDebtV1(
            debt_id=f"debt_amb_{input_id}_{n}", kind="ambiguous_face",
            channel="walls", affected_refs=(ref,),
            description="reading abstained on this face line",
        ))

    for i, opening in enumerate(hyp.get("opening_candidates") or []):
        ref = _fref(
            input_id, contract, sha,
            f"/hypotheses/opening_candidates/{i}", opening["id"],
            (f"/hypotheses/opening_candidates/{i}/span_m",),
        )
        openings.append(OpeningClaimV1(opening_id=opening["id"], source_ref=ref))

    for channel in _ABSENT_CHANNELS:
        debts.append(EvidenceDebtV1(
            debt_id=f"debt_{channel}_{input_id}", kind="missing_channel",
            channel=channel,
            description="channel not carried by this prototype product",
        ))
    channels = [
        ChannelStatusV1(channel="walls", state="present",
                        source_input_ids=(input_id,)),
        ChannelStatusV1(channel="plan_openings", state="present",
                        source_input_ids=(input_id,)),
        *(
            ChannelStatusV1(
                channel=channel, state="absent",
                covered_by_debt_ids=(f"debt_{channel}_{input_id}",),
            )
            for channel in _ABSENT_CHANNELS
        ),
    ]
    bundle = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=BUNDLE_SCHEMA_VERSION,
        source_artifacts=[meta],
        channel_status=channels,
        wall_claims=claims,
        face_dispositions=dispositions,
        opening_claims=openings,
        evidence_debts=debts,
    ))
    return CorrectionEvidenceBundleArtifactV1(
        bundle=bundle,
        frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=raw)],
    )


def _built(name: str) -> CorrectionEvidenceBundleArtifactV1:
    raw = _raw_product(name)
    doc = json.loads(raw)
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_AS_DRAWN_PLAN, decision.reason
    input_id = name.removesuffix(".json")
    floor = "2f" if "2f" in name else "1f"
    return _bundle_from_as_drawn(doc, raw, input_id, floor)


# ── tiny hand-made fixtures (for teeth that need a shape the real products
#    cannot exhibit -- e.g. a same-axis third face for a mismatched pair) ──── #
def _gap() -> dict:
    return {
        "lo_px": 20, "hi_px": 24, "len_px": 4,
        "ink_by_family": {"F0": {"on_line": 2, "by_distance_px": {"2": 1},
                                  "span_ratio": 0.5, "nearest_px": 0}},
        "span_m": [1.1, 1.14], "len_m": 0.04,
    }


def _face(fid: str, axis: str, world_axis: str, col: int) -> dict:
    return {
        "id": fid, "axis": axis, "constant_world_axis": world_axis,
        "pos_px": float(col), "pos_m": 0.01 * col,
        "support_cols_px": [col, col + 1], "edges_m": [0.0, 0.02],
        "support_width_m": 0.02, "runs_px": [[10, 40]],
        "runs_m": [[1.0, 1.3]], "gaps": [_gap()],
        "ink_coverage_per_run": [1.0], "covered_px": 30, "support_px": 31,
    }


def _tiny_doc() -> dict:
    """Four face lines, one selected pair, one non-wall, one lone face.

    F01/F02/F04 are same-axis (candidates exist for two of the three
    pairings), F03 is the other axis -- the shapes the real products cannot
    exhibit but the invariant-3 teeth need.
    """
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100),
            _face("F02", "col", "x", 112),
            _face("F03", "row", "y", 200),
            _face("F04", "col", "x", 130),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [{"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                        "spacing_m": 0.12, "matched_declared_mm": [120],
                        "overlap_px": 30, "source": "selected"}],
            "pair_candidates": [
                {"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                 "spacing_m": 0.12, "matched_declared_mm": [120],
                 "overlap_px": 30},
                {"face_a": "F01", "face_b": "F04", "spacing_px": 30.0,
                 "spacing_m": 0.30, "matched_declared_mm": [],
                 "overlap_px": 30},
            ],
            "opening_candidates": [{
                "id": "F01g0", "face_line": "F01", "gap_index": 0,
                "span_m": [1.1, 1.14], "len_m": 0.04, "len_px": 4,
                "ink_by_family": {"F0": {"on_line": 2, "by_distance_px": {"2": 1},
                                          "span_ratio": 0.5, "nearest_px": 0}},
            }],
            "opening_types": {"F01g0": "window"},
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {"F03": "a furniture edge on this dialect"},
            "unpaired_wall_faces": {"F04": "lone face, honest default state"},
            "solid_band_walls": {},
            "ambiguous_face_lines": {},
        },
    }
    AsDrawnPlanV2.model_validate(doc)  # premise: this IS a legal product
    return doc


def _tiny_artifact() -> CorrectionEvidenceBundleArtifactV1:
    raw = json.dumps(_tiny_doc(), indent=1).encode("utf-8")
    return _bundle_from_as_drawn(json.loads(raw), raw, "tiny", "9f")


def _legacy_raw() -> bytes:
    doc = {
        "image_label": "legacy plan",
        "strokes": [
            {"id": "W01", "pen": "wall",
             "geometry": {"p1": [0, 0], "p2": [100, 0], "thickness_m": None},
             "note": "outer skin line (prose only -- ⛔ never parsed)"},
            {"id": "D01", "pen": "door", "geometry": {}},
        ],
    }
    return json.dumps(doc, indent=1).encode("utf-8")


def _legacy_artifact() -> CorrectionEvidenceBundleArtifactV1:
    raw = _legacy_raw()
    sha = hashlib.sha256(raw).hexdigest()
    contract = SOURCE_CONTRACT_LEGACY
    meta = SourceArtifactV1(
        input_id="legacy_plan", source_contract_id=contract,
        source_output_sha256=sha, view_type="plan", floor_ref="8f",
    )
    trace = _fref("legacy_plan", contract, sha, "/strokes/0", "W01", (),
                  resolution="vector_only")
    claim = LegacyWallTraceClaimV1(
        claim_id="pending",
        hypothesis_ref=_pref("legacy_plan", contract, sha, "/strokes/0"),
        perception_source_ref=_pref("legacy_plan", contract, sha, ""),
        source_contract_id=contract,
        trace_ref=trace,
        source_basis="unknown",
    )
    claim = claim.model_copy(update={"claim_id": wall_claim_id(claim)})
    channels = [
        ChannelStatusV1(channel="walls", state="present",
                        source_input_ids=("legacy_plan",)),
        *(
            ChannelStatusV1(
                channel=channel, state="absent",
                covered_by_debt_ids=(f"debt_{channel}_legacy",),
            )
            for channel in ("plan_openings", *_ABSENT_CHANNELS)
        ),
    ]
    debts = [
        EvidenceDebtV1(
            debt_id=f"debt_{channel}_legacy", kind="missing_channel",
            channel=channel, description="legacy view carries no such channel",
        )
        for channel in ("plan_openings", *_ABSENT_CHANNELS)
    ]
    bundle = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=BUNDLE_SCHEMA_VERSION,
        source_artifacts=[meta],
        channel_status=channels,
        wall_claims=[claim],
        face_dispositions=[],
        opening_claims=[],
        evidence_debts=debts,
    ))
    return CorrectionEvidenceBundleArtifactV1(
        bundle=bundle,
        frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=raw)],
    )


# ── mutation helpers (validator-level teeth; each preserves everything the
#    mutation is NOT about, then re-finalizes so the hash gate stays green
#    and the failure can only come from the semantic gate under test) ──────── #
def _retag(ref: ObservationRefV1, **changes) -> ObservationRefV1:
    data = ref.model_dump()
    data.update(changes)
    data["source_locator"] = source_locator(
        input_id=data["input_id"],
        observation_id=data["observation_id"],
        output_sha256=data["source_output_sha256"],
    )
    return ObservationRefV1.model_validate(data)


def _refinalize(artifact: CorrectionEvidenceBundleArtifactV1
                ) -> CorrectionEvidenceBundleArtifactV1:
    art = artifact.model_copy(deep=True)
    art.bundle = finalize_bundle(art.bundle)
    return art


def _mutate_claim(artifact: CorrectionEvidenceBundleArtifactV1, claim_id: str,
                  transform) -> CorrectionEvidenceBundleArtifactV1:
    """Rewrite ONE claim and keep everything else coherent: the new claim gets
    its canonical id and the dispositions that consumed the old id are
    re-pointed, so the mutation changes ONLY the dimension under test."""
    art = artifact.model_copy(deep=True)
    claims, remap = [], {}
    for claim in art.bundle.wall_claims:
        if claim.claim_id == claim_id:
            new = transform(claim)
            new = new.model_copy(update={"claim_id": wall_claim_id(new)})
            remap[claim.claim_id] = new.claim_id
            claim = new
        claims.append(claim)
    art.bundle.wall_claims = claims
    if remap:
        art.bundle.face_dispositions = [
            (
                d.model_copy(update={
                    "consuming_claim_id": remap[d.consuming_claim_id]
                })
                if d.consuming_claim_id in remap else d
            )
            for d in art.bundle.face_dispositions
        ]
    return _refinalize(art)


def _mutate_opening_ref(artifact: CorrectionEvidenceBundleArtifactV1,
                        opening_id: str,
                        transform) -> CorrectionEvidenceBundleArtifactV1:
    art = artifact.model_copy(deep=True)
    art.bundle.opening_claims = [
        (transform(o) if o.opening_id == opening_id else o)
        for o in art.bundle.opening_claims
    ]
    return _refinalize(art)


def _first_claim_of_kind(artifact: CorrectionEvidenceBundleArtifactV1, kind: str):
    return next(c for c in artifact.bundle.wall_claims if c.kind == kind)


def _expect_error(artifact: CorrectionEvidenceBundleArtifactV1, code: str):
    with pytest.raises(EvidenceContractError) as exc:
        validate_evidence_bundle(artifact)
    assert exc.value.code == code, (
        f"expected {code}, got {exc.value.code}: {exc.value.context}"
    )
    return exc.value


# =========================================================================== #
# Acceptance 1 -- the type vocabulary: 4 + 3 + THREE counterface states
# =========================================================================== #
def test_acceptance_1_type_vocabulary():
    kinds = {
        PairedFacesWallClaimV1: "paired_faces",
        SolidBandWallClaimV1: "solid_band",
        SingleFaceWallClaimV1: "single_face",
        LegacyWallTraceClaimV1: "legacy_wall_trace",
    }
    for model, kind in kinds.items():
        assert model.model_fields["kind"].default == kind
    statuses = set(typing.get_args(
        FaceDispositionV1.model_fields["status"].annotation
    ))
    assert statuses == {"claimed_wall", "non_wall", "ambiguous"}
    counterface = set(typing.get_args(
        SingleFaceWallClaimV1.model_fields["counterface_state"].annotation
    ))
    # ⭐ N-1: the design's two values were superseded -- the sixth real state
    # (ink present, never promoted: sm25 2F L012) must be a FIRST-CLASS value.
    assert counterface == {
        "not_in_observations", "observed_unclaimed", "ink_present_unpromoted",
    }
    # ... and the design's two-value spelling must no longer validate
    with pytest.raises(ValidationError):
        SingleFaceWallClaimV1.model_validate({
            "claim_id": "c", "kind": "single_face",
            "hypothesis_ref": _pref("i", "c", "0" * 64, "/h"),
            "perception_source_ref": _pref("i", "c", "0" * 64, "/h"),
            "source_contract_id": "c", "face_ref": _fref(
                "i", "c", "0" * 64, "/o", "F01", ("/o/runs_px",)
            ),
            "original_reason": "r",
            "counterface_state": "not_in_observations_ink_absent_checked",
        })


# =========================================================================== #
# Acceptance 2 -- the three REAL products each build and validate
# =========================================================================== #
@pytest.mark.parametrize("name", _TRACKED)
def test_acceptance_2_real_products_build_and_validate(name):
    art = _built(name)
    validate_evidence_bundle(art)  # the green premise every red test leans on
    doc = json.loads(_raw_product(name))
    hyp = doc["hypotheses"]
    bundle = art.bundle
    expected_claims = (
        len(hyp.get("pairs") or [])
        + len(hyp.get("solid_band_walls") or {})
        + len(hyp.get("unpaired_wall_faces") or {})
    )
    assert len(bundle.wall_claims) == expected_claims
    assert len(bundle.face_dispositions) == len(doc["observations"]["face_lines"])
    assert len(bundle.opening_claims) == len(hyp.get("opening_candidates") or [])
    # L012 (sm25 2F) lands on the MECHANICAL default today -- its true sixth
    # state is module 3's derivation, and dispatch acceptance #2 explicitly
    # excludes that derivation from THIS dispatch.
    if name == "sm25_2f_v2.json":
        lone = _first_claim_of_kind(art, "single_face")
        assert lone.counterface_state == "not_in_observations"
        assert lone.face_ref.observation_id == "L012"


def test_n1_the_sixth_state_is_constructible_with_a_witness():
    """⭐ N-1 acceptance half: the third counterface state EXISTS on the type
    and can be constructed -- pointing its witness at the node that carries
    the (prose) evidence.  ⛔ This is constructibility, NOT derivation: no
    prose is read to get here."""
    art = _tiny_artifact()
    validate_evidence_bundle(art)  # green premise
    lone = _first_claim_of_kind(art, "single_face")  # F04, on the tiny fixture
    assert lone.face_ref.observation_id == "F04"
    claim_id = lone.claim_id
    art2 = _mutate_claim(art, claim_id, lambda c: c.model_copy(update={
        "counterface_state": "ink_present_unpromoted",
        "counterface_witness_pointers": (
            "/hypotheses/unpaired_wall_faces/F04",
        ),
    }))
    # the mutated claim kept its canonical id (same refs, same kind)
    assert _first_claim_of_kind(art2, "single_face").claim_id == claim_id
    validate_evidence_bundle(art2)  # ⭐ constructible + valid

    # ⛔ without a witness the type itself refuses the sixth state
    with pytest.raises(ValidationError):
        SingleFaceWallClaimV1.model_validate({
            **json.loads(lone.model_dump_json()),
            "counterface_state": "ink_present_unpromoted",
            "counterface_witness_pointers": [],
        })
    # ⛔ and a witness that resolves nowhere dies in the validator
    art3 = _mutate_claim(art, claim_id, lambda c: c.model_copy(update={
        "counterface_state": "ink_present_unpromoted",
        "counterface_witness_pointers": (
            "/hypotheses/unpaired_wall_faces/NO_SUCH_NODE",
        ),
    }))
    _expect_error(art3, "COUNTERFACE_WITNESS_UNRESOLVED")


def test_observed_unclaimed_carries_the_counterfaces_disposition():
    """The second counterface state must travel WITH the observed-but-
    unclaimed node's pointer AND its disposition status (design §4.1)."""
    art = _tiny_artifact()
    lone = _first_claim_of_kind(art, "single_face")
    f03_ref = next(
        d.face_ref for d in art.bundle.face_dispositions
        if d.face_ref.observation_id == "F03"
    )
    art3 = _mutate_claim(art, lone.claim_id, lambda c: c.model_copy(update={
        "counterface_state": "observed_unclaimed",
        "counterface_observation_ref": f03_ref,
        "counterface_disposition_status": "non_wall",
    }))
    validate_evidence_bundle(art3)  # F03 IS disposed non_wall -- agrees

    art4 = _mutate_claim(art, lone.claim_id, lambda c: c.model_copy(update={
        "counterface_state": "observed_unclaimed",
        "counterface_observation_ref": f03_ref,
        "counterface_disposition_status": "ambiguous",  # ⛔ disagrees
    }))
    _expect_error(art4, "COUNTERFACE_DISPOSITION_DISAGREES")


# =========================================================================== #
# Invariant locks 1-8 (acceptance 3: green premise first, red after)
# =========================================================================== #
def test_inv1_every_ref_resolves_in_the_frozen_bytes():
    art = _tiny_artifact()
    validate_evidence_bundle(art)  # green premise

    pair = _first_claim_of_kind(art, "paired_faces")
    # a) ref names an id the pointed-at node does not carry
    art_a = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(c.face_b_ref, observation_id="F99"),
    }))
    _expect_error(art_a, "OBSERVATION_ID_MISMATCH")
    # b) ref names an input that was never frozen
    art_b = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(c.face_b_ref, input_id="never_frozen"),
    }))
    _expect_error(art_b, "UNKNOWN_INPUT_ID")
    # c) witness pointer resolves nowhere
    art_c = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(
            c.face_b_ref,
            pixel_witness_pointers=("/observations/face_lines/1/nope",),
        ),
    }))
    _expect_error(art_c, "WITNESS_POINTER_UNRESOLVED")
    # d) ref's sha is not the frozen source's sha (the carrier got swapped)
    other_sha = "e" * 64
    art_d = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(c.face_b_ref, source_output_sha256=other_sha),
    }))
    _expect_error(art_d, "REF_HASH_MISMATCH")
    # e) frozen bytes no longer hash to the declared sha
    art_e = art.model_copy(deep=True)
    art_e.frozen_sources[0].raw_bytes += b" "
    _expect_error(art_e, "SOURCE_HASH_MISMATCH")


def test_inv2_every_face_line_has_exactly_one_disposition():
    art = _tiny_artifact()
    validate_evidence_bundle(art)  # green premise

    # a) a disposition outside the face-line domain (dangling bucket key,
    #    NF-4 #2's validator-level teeth: the ref resolves because an
    #    opening candidate node also carries an id -- but it is no face line)
    art_a = art.model_copy(deep=True)
    art_a.bundle.face_dispositions.append(FaceDispositionV1(
        face_ref=_fref(
            "tiny", SOURCE_CONTRACT_AS_DRAWN,
            art.bundle.source_artifacts[0].source_output_sha256,
            "/hypotheses/opening_candidates/0", "F01g0",
            ("/hypotheses/opening_candidates/0/span_m",),
        ),
        status="non_wall",
        reason_ref=_pref(
            "tiny", SOURCE_CONTRACT_AS_DRAWN,
            art.bundle.source_artifacts[0].source_output_sha256,
            "/hypotheses/non_wall_face_lines/F03",
        ),
    ))
    _expect_error(_refinalize(art_a), "DISPOSITION_REFERENCES_UNKNOWN_FACE")

    # b) a face line with no disposition at all (the direction the legacy
    #    union check silently absorbed)
    art_b = art.model_copy(deep=True)
    art_b.bundle.face_dispositions = [
        d for d in art_b.bundle.face_dispositions
        if d.face_ref.observation_id != "F03"
    ]
    _expect_error(_refinalize(art_b), "FACE_WITHOUT_DISPOSITION")

    # c) the same face disposed twice
    art_c = art.model_copy(deep=True)
    dup = next(d for d in art_c.bundle.face_dispositions
               if d.face_ref.observation_id == "F03")
    art_c.bundle.face_dispositions.append(dup.model_copy(deep=True))
    _expect_error(_refinalize(art_c), "DUPLICATE_DISPOSITION")

    # d) a disposition sold to a claim that never consumed that face (the
    #    reachable shape of "sold to two claims": making two claims share a
    #    face while BOTH stay hypothesis-consistent is unconstructible --
    #    the producer's buckets partition faces, which is exactly why the
    #    ledger-vs-refs closure has to be checked, not assumed)
    lone = _first_claim_of_kind(art, "single_face")
    pair = _first_claim_of_kind(art, "paired_faces")
    art_d = art.model_copy(deep=True)
    art_d.bundle.face_dispositions = [
        (
            d.model_copy(update={"consuming_claim_id": lone.claim_id})
            if d.face_ref.observation_id == "F01" else d
        )
        for d in art_d.bundle.face_dispositions
    ]
    _expect_error(_refinalize(art_d), "FACE_SOLD_TO_TWO_CLAIMS")

    # e) a claim consuming a face that reading disposed non_wall
    art_e = art.model_copy(deep=True)
    f03_disp = next(d for d in art_e.bundle.face_dispositions
                    if d.face_ref.observation_id == "F03")
    art_e.bundle.face_dispositions = [
        (d.model_copy(update={
            "status": "claimed_wall",
            "consuming_claim_id": lone.claim_id,
            "reason_ref": None,
        }) if d is f03_disp else d)
        for d in art_e.bundle.face_dispositions
    ]
    # F03 is now claimed by the lone claim but NOT referenced by it:
    _expect_error(_refinalize(art_e), "CLAIMED_FACE_WITH_NO_CLAIM")

    # f) an ambiguous abstention without an evidence debt is a silent hole
    art_f = art.model_copy(deep=True)
    f03_disp = next(d for d in art_f.bundle.face_dispositions
                    if d.face_ref.observation_id == "F03")
    art_f.bundle.face_dispositions = [
        (d.model_copy(update={
            "status": "ambiguous",
            "consuming_claim_id": None,
        }) if d is f03_disp else d)
        for d in art_f.bundle.face_dispositions
    ]
    _expect_error(_refinalize(art_f), "AMBIGUOUS_WITHOUT_EVIDENCE_DEBT")


def test_inv3_paired_faces_consistency():
    art = _tiny_artifact()
    validate_evidence_bundle(art)  # green premise
    pair = _first_claim_of_kind(art, "paired_faces")

    # a) self-pairing
    art_a = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": c.face_a_ref,
    }))
    _expect_error(art_a, "PAIR_SELF_REFERENTIAL")

    # b) the two faces on different axes (tiny has F03 on the other axis;
    #    the real products cannot exhibit this shape at all)
    art_b = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(
            c.face_b_ref,
            json_pointer="/observations/face_lines/2",
            observation_id="F03",
        ),
    }))
    _expect_error(art_b, "PAIR_AXES_DISAGREE")

    # c) hypothesis node does not carry this pair's faces (NF-4 #1's
    #    validator-level teeth: a dangling face_b in the SOURCE makes the
    #    hypothesis node disagree with the claim's refs)
    art_c = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "face_b_ref": _retag(
            c.face_b_ref,
            json_pointer="/observations/face_lines/3",
            observation_id="F04",
        ),
    }))
    _expect_error(art_c, "PAIR_HYPOTHESIS_MISMATCH")

    # d) selected pair not backed by the candidate graph (design §4.3)
    art_d = _mutate_claim(art, pair.claim_id, lambda c: c.model_copy(update={
        "pair_candidate_ref": _pref(
            c.pair_candidate_ref.input_id,
            c.pair_candidate_ref.source_contract_id,
            c.pair_candidate_ref.source_output_sha256,
            "/hypotheses/pair_candidates/1",  # the (F01,F04) candidate
        ),
    }))
    _expect_error(art_d, "SELECTED_PAIR_NOT_IN_CANDIDATE_GRAPH")


def test_inv4_claimed_ids_exist_and_witnesses_are_complete():
    art = _built("sm24_1f_v2.json")
    validate_evidence_bundle(art)  # green premise (4 real solid bands)
    band = _first_claim_of_kind(art, "solid_band")

    # a) a solid band without the required pixel witnesses
    art_a = _mutate_claim(art, band.claim_id, lambda c: c.model_copy(update={
        "band_face_ref": _retag(
            c.band_face_ref,
            pixel_witness_pointers=tuple(
                p for p in c.band_face_ref.pixel_witness_pointers
                if not p.endswith("/runs_px")
            ),
        ),
    }))
    _expect_error(art_a, "SOLID_BAND_WITNESS_INCOMPLETE")

    # b) the hypothesis pointer lands on a bucket entry whose key is a
    #    DIFFERENT face than the claim's
    art_b = _mutate_claim(art, band.claim_id, lambda c: c.model_copy(update={
        "hypothesis_ref": _pref(
            c.hypothesis_ref.input_id,
            c.hypothesis_ref.source_contract_id,
            c.hypothesis_ref.source_output_sha256,
            "/hypotheses/unpaired_wall_faces/NOPE",
        ),
    }))
    _expect_error(art_b, "POINTER_UNRESOLVED")

    # c) a bucket key that exists but is not the claimed face
    raw = _raw_product("sm24_1f_v2.json")
    other_face = next(iter(
        json.loads(raw)["hypotheses"]["ambiguous_face_lines"]
    ))
    art_c = _mutate_claim(art, band.claim_id, lambda c: c.model_copy(update={
        "hypothesis_ref": _pref(
            c.hypothesis_ref.input_id,
            c.hypothesis_ref.source_contract_id,
            c.hypothesis_ref.source_output_sha256,
            f"/hypotheses/ambiguous_face_lines/{other_face}",
        ),
    }))
    _expect_error(art_c, "BUCKET_KEY_IS_NOT_THE_CLAIMED_FACE")


def test_inv5_one_source_per_semantic_slot():
    a = _tiny_artifact()      # view_type=plan, floor 9f
    b = _legacy_artifact()    # view_type=plan, floor 8f
    art = CorrectionEvidenceBundleArtifactV1(
        bundle=finalize_bundle(CorrectionEvidenceBundleV1(
            schema_version=BUNDLE_SCHEMA_VERSION,
            source_artifacts=[
                *a.bundle.source_artifacts,
                *b.bundle.source_artifacts,
            ],
            channel_status=a.bundle.channel_status,
            wall_claims=[*a.bundle.wall_claims, *b.bundle.wall_claims],
            face_dispositions=a.bundle.face_dispositions,
            opening_claims=a.bundle.opening_claims,
            evidence_debts=[
                *a.bundle.evidence_debts, *b.bundle.evidence_debts
            ],
        )),
        frozen_sources=[*a.frozen_sources, *b.frozen_sources],
    )
    validate_evidence_bundle(art)  # different floors coexist: green premise

    clash = b.frozen_sources[0].artifact.model_copy(
        update={"input_id": "legacy_plan_again", "floor_ref": "9f"}
    )
    raw = b.frozen_sources[0].raw_bytes
    sha = b.bundle.source_artifacts[0].source_output_sha256
    legacy_claim = b.bundle.wall_claims[0]
    retagged = []
    for claim in b.bundle.wall_claims:
        claim = claim.model_copy(update={
            "trace_ref": _retag(claim.trace_ref, input_id=clash.input_id),
            "hypothesis_ref": _pref(
                clash.input_id, SOURCE_CONTRACT_LEGACY, sha,
                claim.hypothesis_ref.json_pointer,
            ),
            "perception_source_ref": _pref(
                clash.input_id, SOURCE_CONTRACT_LEGACY, sha, "",
            ),
        })
        claim = claim.model_copy(update={"claim_id": wall_claim_id(claim)})
        retagged.append(claim)
    art2 = CorrectionEvidenceBundleArtifactV1(
        bundle=finalize_bundle(CorrectionEvidenceBundleV1(
            schema_version=BUNDLE_SCHEMA_VERSION,
            source_artifacts=[
                *a.bundle.source_artifacts, clash,
            ],
            channel_status=a.bundle.channel_status,
            wall_claims=[*a.bundle.wall_claims, *retagged],
            face_dispositions=a.bundle.face_dispositions,
            opening_claims=a.bundle.opening_claims,
            evidence_debts=a.bundle.evidence_debts,
        )),
        frozen_sources=[
            *a.frozen_sources,
            FrozenSourceV1(artifact=clash, raw_bytes=raw),
        ],
    )
    assert legacy_claim.claim_id != retagged[0].claim_id
    _expect_error(art2, "DUPLICATE_SEMANTIC_INPUT")


def test_inv6_one_file_matching_two_contracts_is_loud():
    raw = _legacy_raw()
    hybrid = json.loads(raw)
    hybrid.update(_tiny_doc())  # carries BOTH a strokes list and the as-drawn
    # ... declaration. Premise: every detector runs and the classifier calls
    # it AMBIGUOUS (⛔ never resolved by declaration order).
    decision = classify_vector_json(hybrid)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert "AMBIGUOUS" in (decision.reason or "")

    hybrid_bytes = json.dumps(hybrid, indent=1).encode("utf-8")
    sha = hashlib.sha256(hybrid_bytes).hexdigest()
    contract = SOURCE_CONTRACT_AS_DRAWN
    meta = SourceArtifactV1(
        input_id="hybrid", source_contract_id=contract,
        source_output_sha256=sha, view_type="plan", floor_ref="7f",
    )
    bundle = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=BUNDLE_SCHEMA_VERSION,
        source_artifacts=[meta],
        channel_status=[
            ChannelStatusV1(channel="walls", state="present",
                            source_input_ids=("hybrid",)),
        ],
        wall_claims=[], face_dispositions=[], opening_claims=[],
        evidence_debts=[],
    ))
    _expect_error(
        CorrectionEvidenceBundleArtifactV1(
            bundle=bundle,
            frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=hybrid_bytes)],
        ),
        "AMBIGUOUS_CONTRACT_MATCH",
    )


def test_inv7_declared_but_malformed_never_falls_back_to_legacy():
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["observations"]["face_lines"][0]["runs_px"] = "0-100"  # module-1 corruption
    # premise: today's producer type refuses it (that is module 1's teeth)
    with pytest.raises(ValidationError):
        AsDrawnPlanV2.model_validate(doc)
    raw = json.dumps(doc, indent=1).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    meta = SourceArtifactV1(
        input_id="malformed", source_contract_id=SOURCE_CONTRACT_AS_DRAWN,
        source_output_sha256=sha, view_type="plan", floor_ref="6f",
    )
    bundle = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=BUNDLE_SCHEMA_VERSION,
        source_artifacts=[meta],
        channel_status=[ChannelStatusV1(
            channel="walls", state="present", source_input_ids=("malformed",),
        )],
        wall_claims=[], face_dispositions=[], opening_claims=[],
        evidence_debts=[],
    ))
    _expect_error(
        CorrectionEvidenceBundleArtifactV1(
            bundle=bundle,
            frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=raw)],
        ),
        "MALFORMED_DECLARED_CONTRACT",
    )


def test_inv8_canonical_order_and_content_hash():
    art = _tiny_artifact()
    validate_evidence_bundle(art)  # green premise

    # a) tampered content with a stale hash (view_manifest_sha256 feeds no
    #    semantic gate, so only the hash gate can catch this change)
    art_a = art.model_copy(deep=True)
    art_a.bundle.view_manifest_sha256 = "f" * 64
    _expect_error(art_a, "CONTENT_HASH_MISMATCH")

    # b) right hash, wrong order (the ordering half, named precisely): the
    #    canonical hash is computed over the SORTED form, so unsorted input
    #    keeps a matching hash -- only the order check can name it
    art_b = _refinalize(art)
    art_b.bundle.wall_claims = list(reversed(art_b.bundle.wall_claims))
    with pytest.raises(EvidenceContractError) as exc:
        validate_evidence_bundle(art_b)
    assert exc.value.code == "WALL_CLAIMS_UNORDERED"
    # ⭐ and finalize launders order -- that is its job, not a hole
    validate_evidence_bundle(
        CorrectionEvidenceBundleArtifactV1(
            bundle=finalize_bundle(art_b.bundle),
            frozen_sources=art.frozen_sources,
        )
    )

    # c) an unfinalized bundle (content_sha256=None) never validates
    art_c = art.model_copy(deep=True)
    art_c.bundle.content_sha256 = None
    _expect_error(art_c, "BUNDLE_NOT_FINALIZED")

    # d) a claim wearing another claim's id
    claims = art.bundle.wall_claims
    art_d = art.model_copy(deep=True)
    art_d.bundle.wall_claims[0] = art_d.bundle.wall_claims[0].model_copy(
        update={"claim_id": claims[-1].claim_id}
    )
    _expect_error(_refinalize(art_d), "CLAIM_ID_NOT_CANONICAL")


# =========================================================================== #
# Acceptance 5 (determinism) -- invariant 8's byte-level face
# =========================================================================== #
@pytest.mark.parametrize("name", _TRACKED)
def test_acceptance_5_same_bytes_twice_is_byte_identical(name):
    first, second = _built(name), _built(name)
    assert first.bundle.content_sha256 == second.bundle.content_sha256
    assert (
        canonical_json_bytes(first.bundle.model_dump(mode="json"))
        == canonical_json_bytes(second.bundle.model_dump(mode="json"))
    )


def test_acceptance_5_any_byte_change_moves_the_hash():
    name = "sm25_2f_v2.json"
    raw = _raw_product(name)
    art = _built(name)
    # same parsed content, different bytes (whitespace only)
    rewritten = json.dumps(json.loads(raw), indent=3).encode("utf-8")
    assert rewritten != raw
    doc = json.loads(rewritten)
    art2 = _bundle_from_as_drawn(doc, rewritten, "sm25_2f_v2", "2f")
    assert art2.bundle.content_sha256 != art.bundle.content_sha256, (
        "the hash must anchor in the BYTES, not in the parsed structure -- "
        "otherwise a re-serialized source would silently keep the old identity"
    )
    validate_evidence_bundle(art2)


# =========================================================================== #
# Acceptance 4 -- no copied geometry values on any wall claim (mechanical)
# =========================================================================== #
def _producer_value_field_names() -> set[str]:
    """The forbidden-name set, derived from the PRODUCER's own types (module
    1) -- so a value field added there tomorrow tightens this lock for free,
    instead of a hand-maintained list drifting out of date."""
    def _reduce(annotation):
        """Strip Annotated wrappers (``PixelInterval`` is an annotated list)."""
        while typing.get_origin(annotation) is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
        return annotation

    def _is_number_tree(annotation) -> bool:
        """A scalar number, or a list/tuple of them to any depth (``runs_px``
        is a list of pixel intervals, i.e. a number tree, ⛔ not a scalar)."""
        annotation = _reduce(annotation)
        if annotation in (float, int):
            return True
        origin = typing.get_origin(annotation)
        if origin in (list, tuple):
            args = typing.get_args(annotation)
            return bool(args) and _is_number_tree(args[0])
        return False

    names: set[str] = set()
    for model in (FaceLineV2, GapV2, PairCandidateV2, InkProfileV2):
        for field_name, field in model.model_fields.items():
            if _is_number_tree(field.annotation):
                names.add(field_name)
    return names


def _walk_claim_fields(model, seen: set[str] = frozenset()) -> set[str]:
    """Every field name on a claim model, recursing into nested claim models
    (⛔ the union members themselves, not the base class)."""
    found: set[str] = set()
    for field_name, field in model.model_fields.items():
        found.add(field_name)
        annotation = field.annotation
        if typing.get_origin(annotation) is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
        inner: list = list(typing.get_args(annotation))
        for candidate in [annotation, *inner]:
            if (
                isinstance(candidate, type)
                and issubclass(candidate, BaseModel)
                and candidate not in seen
            ):
                found |= _walk_claim_fields(candidate, seen | {candidate})
    return found


def test_acceptance_4_no_geometry_value_fields_on_wall_claims():
    forbidden = _producer_value_field_names()
    # spot-check the derivation itself, so a silently-empty set cannot pass
    assert {"pos_m", "edges_m", "runs_m", "runs_px", "spacing_m",
            "spacing_px", "len_m", "overlap_px"} <= forbidden
    for model in (PairedFacesWallClaimV1, SolidBandWallClaimV1,
                  SingleFaceWallClaimV1, LegacyWallTraceClaimV1):
        fields = _walk_claim_fields(model)
        assert not (fields & forbidden), (
            f"{model.__name__} carries copied geometry values: "
            f"{sorted(fields & forbidden)}"
        )
    # ⭐ spacing_m in particular is NOT carried even as an audit cache: with
    # no reader there is nothing to prove unread (dispatch acceptance #4's
    # alternative -- keep it AND prove recomputation -- was not taken).


# =========================================================================== #
# Acceptance 8 -- NF-4's five corruptions: before/after readings
# =========================================================================== #
def _today_says_yes(doc: dict) -> None:
    """The 'before' half of every NF-4 reading: today's producer type and
    classifier still accept the corrupted product."""
    AsDrawnPlanV2.model_validate(doc)
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_AS_DRAWN_PLAN


def _built_from_doc(doc: dict, input_id: str, floor: str,
                    ) -> CorrectionEvidenceBundleArtifactV1:
    raw = json.dumps(doc, indent=1).encode("utf-8")
    return _bundle_from_as_drawn(doc, raw, input_id, floor)


def test_nf4_1_dangling_pair_face_b():
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["hypotheses"]["pairs"][0]["face_b"] = "L999"
    _today_says_yes(doc)  # BEFORE: passes (measured by the module-1 review)

    with pytest.raises(EvidenceContractError) as exc:
        _built_from_doc(doc, "nf4_1", "2f")
    assert exc.value.code == "SELECTED_PAIR_REFERENCES_UNKNOWN_FACE"
    # AFTER (validator-level teeth): test_inv3c drives the same corruption
    # family through PAIR_HYPOTHESIS_MISMATCH on a constructed bundle.


def test_nf4_2_dangling_bucket_key():
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["hypotheses"]["non_wall_face_lines"]["L999"] = "invented reason"
    _today_says_yes(doc)  # BEFORE: passes

    with pytest.raises(EvidenceContractError) as exc:
        _built_from_doc(doc, "nf4_2", "2f")
    assert exc.value.code == "BUCKET_KEY_REFERENCES_UNKNOWN_FACE"
    # AFTER (validator-level teeth): test_inv2a drives the same family
    # through DISPOSITION_REFERENCES_UNKNOWN_FACE.


def test_nf4_3_duplicate_face_id():
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["observations"]["face_lines"][1]["id"] = \
        doc["observations"]["face_lines"][0]["id"]
    _today_says_yes(doc)  # BEFORE: passes

    # AFTER: the shared production index refuses to build -- "resolves
    # uniquely" (invariant 1) is this function's job, and the bundle factory
    # calls the same function the validator calls.
    with pytest.raises(EvidenceContractError) as exc:
        as_drawn_face_index(doc)
    assert exc.value.code == "DUPLICATE_OBSERVATION_ID"


def test_nf4_4_opening_gap_index_out_of_range():
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["hypotheses"]["opening_candidates"][0]["gap_index"] = 99
    _today_says_yes(doc)  # BEFORE: passes

    # ⭐ This one the bundle factory does NOT check (it trusts openings
    # mechanically), so the bundle CONSTRUCTS -- and the validator is what
    # goes loud: the index is a dangling reference into the face's gaps.
    art = _built_from_doc(doc, "nf4_4", "2f")
    _expect_error(art, "OPENING_GAP_INDEX_OUT_OF_RANGE")

    # the same corruption on the tiny fixture (a different product shape)
    # is loud the same way
    tiny_doc = _tiny_doc()
    tiny_doc["hypotheses"]["opening_candidates"][0]["gap_index"] = 7
    _today_says_yes(tiny_doc)
    _expect_error(
        _built_from_doc(tiny_doc, "nf4_4b", "9f"),
        "OPENING_GAP_INDEX_OUT_OF_RANGE",
    )


def test_nf4_5_unselected_dangling_candidate_passes_today_module3_4_pinned():
    """PIN (dispatch task 4 / acceptance 9).  A dangling ``pair_candidates``
    entry that NO selected pair references passes this layer TODAY, on
    purpose: the bundle references selected pairs only (design §4.3 -- the
    candidate graph is a review aid, not wall claims), so an unselected
    dangling candidate is invisible here.

    Ownership: module 3 (``correction/evidence_adapters.py`` -- the adapter
    walks the candidate graph and must dereference ``face_b`` there) and
    module 4 (``correction/wall_compiler.py`` -- it recomputes the candidate
    graph from the observations and must refuse faces that do not exist).
    ⛔ Do not let this stay a silent gap between the two documents.
    """
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    selected = {
        frozenset((p["face_a"], p["face_b"]))
        for p in doc["hypotheses"]["pairs"]
    }
    unselected = next(
        c for c in doc["hypotheses"]["pair_candidates"]
        if frozenset((c["face_a"], c["face_b"])) not in selected
    )
    unselected["face_b"] = "L999"
    _today_says_yes(doc)  # BEFORE: passes

    art = _built_from_doc(doc, "nf4_5", "2f")
    validate_evidence_bundle(art)  # ⭐ PIN: passes TODAY, by design
    # ... and note the boundary honestly: the same corruption on a SELECTED
    # candidate is loud (nf4_1 / inv3), so the pin covers exactly the
    # unselected mass of the candidate graph.


# =========================================================================== #
# Acceptance 6/7 -- this dispatch wires nothing (behavioural face of it)
# =========================================================================== #
def test_the_type_layer_imports_no_pipeline():
    """⛔ Behavioural half of acceptance 6 (the diff half is the execution
    report's reading): a clean interpreter that imports ONLY the type layer
    must never reach the pipeline.  This is permanent -- the type layer is
    never allowed to grow an orchestration import."""
    import subprocess
    import sys

    probe = (
        "import sys; import src.agent.correction.evidence_contract; "
        "print(any(m == 'src.agent.pipeline' for m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_as_drawn_is_still_not_consumed():
    """The one-line gate from the wiring survey is untouched BY THIS DISPATCH.
    ⚠️ Like module 1's identical lock, this pin flips the day module 7
    registers the adapter -- that flip must be an on-purpose change."""
    from src.agent.reading.vector_contract import CONTRACTS, Disposition

    spec = next(s for s in CONTRACTS
                if s.contract_id == CONTRACT_AS_DRAWN_PLAN)
    assert spec.disposition is Disposition.KNOWN_NOT_CONSUMED


# =========================================================================== #
# Legacy wall-trace claims: the type works, basis evidence is structural
# =========================================================================== #
def test_legacy_wall_trace_unknown_basis_is_the_honest_default():
    art = _legacy_artifact()
    validate_evidence_bundle(art)
    claim = _first_claim_of_kind(art, "legacy_wall_trace")
    assert claim.source_basis == "unknown"
    assert claim.basis_evidence_ref is None


def test_legacy_non_unknown_basis_requires_structured_evidence():
    art = _legacy_artifact()
    sha = art.bundle.source_artifacts[0].source_output_sha256
    # ⛔ the type refuses a non-unknown basis without a structured pointer --
    # free-text notes never satisfy this gate (design §4.1 / §8.3)
    with pytest.raises(ValidationError):
        LegacyWallTraceClaimV1.model_validate({
            **json.loads(json.dumps(
                _first_claim_of_kind(art, "legacy_wall_trace").model_dump(
                    mode="json"
                )
            )),
            "source_basis": "centerline",
        })
    # ... and WITH a structural pointer it validates AND validates end to end
    claim = _first_claim_of_kind(art, "legacy_wall_trace")
    upgraded = claim.model_copy(update={
        "source_basis": "centerline",
        "basis_evidence_ref": _pref(
            "legacy_plan", SOURCE_CONTRACT_LEGACY, sha, "/strokes/0/geometry"
        ),
    })
    upgraded = upgraded.model_copy(update={"claim_id": wall_claim_id(upgraded)})
    art2 = art.model_copy(deep=True)
    art2.bundle.wall_claims = [upgraded]
    validate_evidence_bundle(_refinalize(art2))
