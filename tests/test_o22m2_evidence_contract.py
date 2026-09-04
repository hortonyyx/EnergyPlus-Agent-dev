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
    DebtObligationV1,
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
from src.agent.correction import evidence_contract
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

_ABSENT_CHANNELS = (
    "elevation_openings", "floor_levels", "dimensions", "room_roles",
)


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
            obligation=None,
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
            obligation=None,
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
            obligation=None,
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
            channel_status=[
                # rework-2 B-1: the green premise merges BOTH products' wall
                # claims, so its routing table must list both payload
                # sources.  (Before source closure nobody looked, and the
                # table silently claimed tiny alone while carrying
                # legacy_plan's claims -- B-1's shape, in a fixture.)
                (
                    s.model_copy(update={
                        "source_input_ids": ("tiny", "legacy_plan")
                    })
                    if s.channel == "walls"
                    else s
                )
                for s in a.bundle.channel_status
            ],
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
# Cross-review rework (2026-08-31) -- F-1 payload closure, F-2 single sourcing
# (verdict: ../verdict/2026-08-31_o22m2_crossreview_claude.md, findings F-1/F-2)
# =========================================================================== #
def _empty_artifact() -> CorrectionEvidenceBundleArtifactV1:
    """The reviewer's F-1 shape: a LEGAL as-drawn product whose face_lines
    and hypotheses are both empty, wired as walls=present.  Nothing in the
    OLD validator objects -- that is the hole, reproduced."""
    doc = {"schema": SCHEMA, "observations": {"face_lines": []},
           "declarations": {}, "hypotheses": {}}
    AsDrawnPlanV2.model_validate(doc)  # premise: empty IS a legal product
    raw = json.dumps(doc, indent=1).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    meta = SourceArtifactV1(
        input_id="empty_plan", source_contract_id=SOURCE_CONTRACT_AS_DRAWN,
        source_output_sha256=sha, view_type="plan", floor_ref="5f",
    )
    absent = (
        "plan_openings", "elevation_openings", "floor_levels",
        "dimensions", "room_roles",
    )
    debts = [EvidenceDebtV1(
        debt_id=f"debt_{ch}_empty", kind="missing_channel", channel=ch,
        description="channel not carried by this empty product",
        obligation=None,
    ) for ch in absent]
    return CorrectionEvidenceBundleArtifactV1(
        bundle=finalize_bundle(CorrectionEvidenceBundleV1(
            schema_version=BUNDLE_SCHEMA_VERSION,
            source_artifacts=[meta],
            channel_status=[
                ChannelStatusV1(channel="walls", state="present",
                                source_input_ids=("empty_plan",)),
                *(ChannelStatusV1(
                    channel=ch, state="absent",
                    covered_by_debt_ids=(f"debt_{ch}_empty",),
                ) for ch in absent),
            ],
            wall_claims=[], face_dispositions=[], opening_claims=[],
            evidence_debts=debts,
        )),
        frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=raw)],
    )


def test_f1_present_channel_requires_payload_or_an_explicit_debt(monkeypatch):
    """Cross-review F-1.  BEFORE: with the closure check neutered, the
    reviewer's shape validates on THIS tree (the hole was real, not
    transcribed).  AFTER: loud -- and the honest "wired, produced nothing"
    debt still passes, so the gate kills only the SILENT empty run."""
    art = _empty_artifact()
    # BEFORE: neuter the new check and the old validator waves it through
    monkeypatch.setattr(
        evidence_contract, "_assert_channel_payload_closure", lambda b: None
    )
    validate_evidence_bundle(art)
    monkeypatch.undo()

    # AFTER: loud, with the stable code and the offending channel named
    err = _expect_error(art, "PRESENT_CHANNEL_WITHOUT_PAYLOAD")
    assert err.context == {"channel": "walls"}

    # ⭐ the honest shape still passes (the gate's other direction)
    honest = art.model_copy(deep=True)
    honest.bundle.evidence_debts.append(EvidenceDebtV1(
        debt_id="debt_zero_walls", kind="zero_payload_channel",
        channel="walls", description="walls wired, produced nothing",
        obligation=None,
    ))
    validate_evidence_bundle(_refinalize(honest))

    # a zero-payload debt without a channel cannot keep the gate honest
    dangling = art.model_copy(deep=True)
    dangling.bundle.evidence_debts.append(EvidenceDebtV1(
        debt_id="debt_zero_none", kind="zero_payload_channel",
        description="no channel named",
        obligation=None,
    ))
    _expect_error(_refinalize(dangling), "ZERO_PAYLOAD_DEBT_WITHOUT_CHANNEL")

    # plan_openings, the second channel WITH payload members: present with
    # zero opening claims is loud the same way (tiny carries real payload
    # everywhere else, so the red can only come from the emptied channel)
    art2 = _tiny_artifact()
    art2.bundle.opening_claims = []
    err2 = _expect_error(_refinalize(art2), "PRESENT_CHANNEL_WITHOUT_PAYLOAD")
    assert err2.context == {"channel": "plan_openings"}

    # the three channels with NO payload member on this bundle can never
    # witness a present: declaring one present without a debt is loud too
    art3 = _tiny_artifact()
    art3.bundle.channel_status = [
        (
            c.model_copy(update={
                "state": "present",
                "source_input_ids": ("tiny",),
                "covered_by_debt_ids": (),
            })
            if c.channel == "elevation_openings" else c
        )
        for c in art3.bundle.channel_status
    ]
    err3 = _expect_error(_refinalize(art3), "PRESENT_CHANNEL_WITHOUT_PAYLOAD")
    assert err3.context == {"channel": "elevation_openings"}


def _cross_input_artifact(cross: str) -> CorrectionEvidenceBundleArtifactV1:
    """The reviewer's F-2/A3 shape: TWO legal products (planA 1f / planB 2f,
    same face ids, same axes), one paired_faces claim spanning them.  Every
    reference resolves, the hypothesis and candidate matches succeed, the
    axes agree -- structurally flawless, physically impossible.

    ``cross="face_b"``: the wall's two faces in two products ("cross-floor"
    wall).  ``cross="hypothesis"``: faces same-source, the hypothesis node
    in the other product -- proving the gate covers ALL refs, not just the
    two face refs."""
    doc_a = _tiny_doc()
    doc_b = _tiny_doc()
    doc_b["observations"]["face_lines"] = \
        doc_b["observations"]["face_lines"][:2]
    doc_b["hypotheses"]["non_wall_face_lines"] = {}
    doc_b["hypotheses"]["unpaired_wall_faces"] = {}
    doc_b["hypotheses"]["pair_candidates"] = \
        doc_b["hypotheses"]["pair_candidates"][:1]
    AsDrawnPlanV2.model_validate(doc_a)
    AsDrawnPlanV2.model_validate(doc_b)  # premise: both are legal products
    raw_a = json.dumps(doc_a, indent=1).encode("utf-8")
    raw_b = json.dumps(doc_b, indent=1).encode("utf-8")
    sha_a = hashlib.sha256(raw_a).hexdigest()
    sha_b = hashlib.sha256(raw_b).hexdigest()
    contract = SOURCE_CONTRACT_AS_DRAWN
    meta_a = SourceArtifactV1(
        input_id="planA", source_contract_id=contract,
        source_output_sha256=sha_a, view_type="plan", floor_ref="1f",
    )
    meta_b = SourceArtifactV1(
        input_id="planB", source_contract_id=contract,
        source_output_sha256=sha_b, view_type="plan", floor_ref="2f",
    )

    def fref(input_id: str, sha: str, i: int, fid: str) -> ObservationRefV1:
        base = f"/observations/face_lines/{i}"
        return _fref(input_id, contract, sha, base, fid,
                     (f"{base}/support_cols_px", f"{base}/runs_px",
                      f"{base}/edges_m", f"{base}/gaps"))

    if cross == "face_b":
        face_a = fref("planA", sha_a, 0, "F01")
        face_b = fref("planB", sha_b, 1, "F02")
        hyp = _pref("planA", contract, sha_a, "/hypotheses/pairs/0")
        a_f02_claimed, b_f02_claimed = False, True
    else:
        face_a = fref("planA", sha_a, 0, "F01")
        face_b = fref("planA", sha_a, 1, "F02")
        hyp = _pref("planB", contract, sha_b, "/hypotheses/pairs/0")
        a_f02_claimed, b_f02_claimed = True, False

    claim = PairedFacesWallClaimV1(
        claim_id="pending",
        hypothesis_ref=hyp,
        perception_source_ref=_pref("planA", contract, sha_a, "/hypotheses"),
        source_contract_id=contract,
        face_a_ref=face_a,
        face_b_ref=face_b,
        pair_candidate_ref=_pref(
            "planA", contract, sha_a, "/hypotheses/pair_candidates/0"
        ),
    )
    claim = claim.model_copy(update={"claim_id": wall_claim_id(claim)})

    def reason(input_id: str, sha: str) -> ArtifactPointerV1:
        pointer = ("/hypotheses/non_wall_face_lines/F03"
                   if input_id == "planA" else "/hypotheses")
        return _pref(input_id, contract, sha, pointer)

    def disp(ref: ObservationRefV1, claimed: bool) -> FaceDispositionV1:
        if claimed:
            return FaceDispositionV1(
                face_ref=ref, status="claimed_wall",
                consuming_claim_id=claim.claim_id,
            )
        return FaceDispositionV1(
            face_ref=ref, status="non_wall",
            reason_ref=reason(ref.input_id, ref.source_output_sha256),
        )

    dispositions = [
        disp(fref("planA", sha_a, 0, "F01"), True),
        disp(fref("planA", sha_a, 1, "F02"), a_f02_claimed),
        disp(fref("planA", sha_a, 2, "F03"), False),
        disp(fref("planA", sha_a, 3, "F04"), False),
        disp(fref("planB", sha_b, 0, "F01"), False),
        disp(fref("planB", sha_b, 1, "F02"), b_f02_claimed),
    ]
    absent = (
        "plan_openings", "elevation_openings", "floor_levels",
        "dimensions", "room_roles",
    )
    debts = [EvidenceDebtV1(
        debt_id=f"debt_{ch}_cross", kind="missing_channel", channel=ch,
        description="channel not carried by this probe bundle",
        obligation=None,
    ) for ch in absent]
    return CorrectionEvidenceBundleArtifactV1(
        bundle=finalize_bundle(CorrectionEvidenceBundleV1(
            schema_version=BUNDLE_SCHEMA_VERSION,
            source_artifacts=[meta_a, meta_b],
            channel_status=[
                ChannelStatusV1(channel="walls", state="present",
                                source_input_ids=("planA", "planB")),
                *(ChannelStatusV1(
                    channel=ch, state="absent",
                    covered_by_debt_ids=(f"debt_{ch}_cross",),
                ) for ch in absent),
            ],
            wall_claims=[claim],
            face_dispositions=dispositions,
            opening_claims=[],
            evidence_debts=debts,
        )),
        frozen_sources=[
            FrozenSourceV1(artifact=meta_a, raw_bytes=raw_a),
            FrozenSourceV1(artifact=meta_b, raw_bytes=raw_b),
        ],
    )


def test_f2_claim_refs_must_share_one_input_id(monkeypatch):
    """Cross-review F-2.  Green premise first: a same-source claim on the
    tiny fixture (and all three real products, in test_acceptance_2) still
    validates.  BEFORE: with the single-sourcing check neutered, BOTH
    cross-input variants validate on THIS tree.  AFTER: loud, with the two
    offending input ids named."""
    validate_evidence_bundle(_tiny_artifact())  # same-source premise

    for cross in ("face_b", "hypothesis"):
        art = _cross_input_artifact(cross)
        # BEFORE: neuter the new check and the old validator waves it
        # through -- every dereference, hypothesis match, candidate match
        # and axis check above it genuinely succeeds.
        monkeypatch.setattr(
            evidence_contract, "_assert_claim_refs_single_sourced",
            lambda c: None,
        )
        validate_evidence_bundle(art)
        monkeypatch.undo()

        err = _expect_error(art, "CLAIM_REFS_SPAN_MULTIPLE_INPUTS")
        assert err.context["input_ids"] == ["planA", "planB"], err.context


# =========================================================================== #
# Rework-2 (2026-08-31) -- B-1 source closure, B-2 payloadless present
# (verdict: ../verdict/2026-08-31_o22m2_rework_crossreview_gpt.md, B-1/B-2:
#  F-1 asked whether a present channel has payload AT ALL, never WHERE the
#  payload came from; and the zero-payload pass was open to three channels
#  that have no payload member to witness a present with.)
# =========================================================================== #
def _merge_empty_plan(
    art: CorrectionEvidenceBundleArtifactV1,
) -> CorrectionEvidenceBundleArtifactV1:
    """Freeze the legal empty product ALONGSIDE tiny's payload -- the
    reviewer's B-1 staging: the routing table can now lie in both
    directions (payload from an undeclared source; a declared source with
    no payload)."""
    merged = art.model_copy(deep=True)
    src = _empty_artifact().frozen_sources[0]
    merged.frozen_sources.append(src)
    merged.bundle.source_artifacts.append(src.artifact)
    return merged


def _set_channel_sources(
    art: CorrectionEvidenceBundleArtifactV1,
    channel: str,
    input_ids: tuple[str, ...],
) -> CorrectionEvidenceBundleArtifactV1:
    art.bundle.channel_status = [
        (
            s.model_copy(update={"source_input_ids": input_ids})
            if s.channel == channel
            else s
        )
        for s in art.bundle.channel_status
    ]
    return art


def _zero_payload_debt(
    debt_id: str, channel: str, scoped_to: tuple[ArtifactPointerV1, ...] = ()
) -> EvidenceDebtV1:
    return EvidenceDebtV1(
        debt_id=debt_id,
        kind="zero_payload_channel",
        channel=channel,
        affected_refs=scoped_to,
        description="wired, produced nothing this run",
        obligation=None,
    )


def _empty_plan_pointer() -> ArtifactPointerV1:
    meta = _empty_artifact().frozen_sources[0].artifact
    return ArtifactPointerV1(
        input_id=meta.input_id,
        source_contract_id=meta.source_contract_id,
        source_output_sha256=meta.source_output_sha256,
        json_pointer="",
    )


def test_b1_payload_must_come_from_the_channels_declared_source(monkeypatch):
    """Rework-2 B-1, forward.  BEFORE (source closure neutered): declaring
    the walls -- or plan_openings -- channel's source as the empty product
    while the payload still all comes from tiny VALIDATES (F-1 is honestly
    satisfied: the channel DOES carry payload).  AFTER: loud, with both the
    real and the declared routing named.  The other direction: the three
    real products and the untouched fixtures stay green."""
    for channel in ("walls", "plan_openings"):
        art = _set_channel_sources(
            _merge_empty_plan(_tiny_artifact()), channel, ("empty_plan",)
        )
        # BEFORE: neuter the new closure and the tree-of-record waves it
        # through -- the red can only come from the gate under test
        monkeypatch.setattr(
            evidence_contract,
            "_assert_channel_source_closure",
            lambda b, f: None,
        )
        validate_evidence_bundle(_refinalize(art.model_copy(deep=True)))
        monkeypatch.undo()

        # AFTER: loud
        err = _expect_error(
            _refinalize(art.model_copy(deep=True)),
            "PAYLOAD_FROM_UNDECLARED_SOURCE",
        )
        assert err.context["channel"] == channel
        assert err.context["payload_input_ids"] == ["tiny"]
        assert err.context["declared_input_ids"] == ["empty_plan"]

    # the other direction: honest single-source routing still passes (the
    # three real products, the tiny fixture, the legacy fixture)
    for name in _TRACKED:
        validate_evidence_bundle(_built(name))
    validate_evidence_bundle(_tiny_artifact())
    validate_evidence_bundle(_legacy_artifact())


def test_b1_declared_source_without_payload_needs_a_scoped_debt(monkeypatch):
    """Rework-2 B-1, reverse.  The channel DOES carry payload (all of it
    from tiny) while the table also lists the empty product.  BEFORE: that
    validates with no debt at all.  AFTER: each payload-free declared
    source must be excused by a ``zero_payload_channel`` debt SCOPED to it
    via ``affected_refs`` -- ⛔ a channel-granularity debt does NOT count
    (its statement "this channel produced nothing" is false while tiny
    produced), and the scoped debt must name the frozen source by its real
    identity, so the excuse cannot be minted against a made-up one."""
    base = _set_channel_sources(
        _merge_empty_plan(_tiny_artifact()), "walls", ("empty_plan", "tiny")
    )

    # BEFORE: neuter the new closure and the tree-of-record waves it through
    monkeypatch.setattr(
        evidence_contract, "_assert_channel_source_closure", lambda b, f: None
    )
    validate_evidence_bundle(_refinalize(base.model_copy(deep=True)))
    monkeypatch.undo()

    # AFTER, no debt: loud, with the payload-free source named
    err = _expect_error(
        _refinalize(base.model_copy(deep=True)),
        "CHANNEL_SOURCE_WITHOUT_PAYLOAD_OR_SCOPED_DEBT",
    )
    assert err.context == {"channel": "walls", "input_ids": ["empty_plan"]}

    # a channel-granularity debt still does not excuse it
    global_debt = base.model_copy(deep=True)
    global_debt.bundle.evidence_debts.append(
        _zero_payload_debt("debt_zero_walls", "walls")
    )
    _expect_error(
        _refinalize(global_debt),
        "CHANNEL_SOURCE_WITHOUT_PAYLOAD_OR_SCOPED_DEBT",
    )

    # the scoped debt does: it names the empty source by its frozen identity
    scoped = base.model_copy(deep=True)
    scoped.bundle.evidence_debts.append(_zero_payload_debt(
        "debt_zero_walls_empty", "walls", scoped_to=(_empty_plan_pointer(),)
    ))
    validate_evidence_bundle(_refinalize(scoped))

    # and the excuse cannot be forged: the ref must carry the frozen
    # source's real hash, not just its input_id
    forged = base.model_copy(deep=True)
    forged.bundle.evidence_debts.append(_zero_payload_debt(
        "debt_zero_walls_forged",
        "walls",
        scoped_to=(
            _empty_plan_pointer().model_copy(
                update={"source_output_sha256": "0" * 64}
            ),
        ),
    ))
    _expect_error(
        _refinalize(forged), "SCOPED_ZERO_PAYLOAD_DEBT_REF_UNKNOWN"
    )


def test_b2_a_channel_without_payload_carrier_can_never_be_present(monkeypatch):
    """Rework-2 B-2.  BEFORE: dimensions=present + zero_payload_channel(
    dimensions) VALIDATES -- the pass was open to a channel with no payload
    member, which can never witness a present.  AFTER: that debt itself is
    refused (and a present with no debt at all keeps F-1's original code).
    The other direction: walls=present + zero_payload_channel(walls) on a
    genuine whole-channel zero run STAYS GREEN -- that exit belongs to the
    channels this layer can actually check."""
    art = _tiny_artifact()
    art.bundle.channel_status = [
        (
            s.model_copy(update={
                "state": "present",
                "source_input_ids": ("tiny",),
                "covered_by_debt_ids": (),
            })
            if s.channel == "dimensions"
            else s
        )
        for s in art.bundle.channel_status
    ]
    art.bundle.evidence_debts.append(
        _zero_payload_debt("debt_zero_dimensions", "dimensions")
    )

    # BEFORE: neuter the payload-closure gate (where B-2's fix lives) and
    # the tree-of-record waves it through
    monkeypatch.setattr(
        evidence_contract, "_assert_channel_payload_closure", lambda b: None
    )
    validate_evidence_bundle(_refinalize(art.model_copy(deep=True)))
    monkeypatch.undo()

    # AFTER: the pass no longer exists for a payloadless channel
    _expect_error(
        _refinalize(art.model_copy(deep=True)),
        "ZERO_PAYLOAD_DEBT_WITHOUT_PAYLOAD_CARRIER",
    )

    # and with no debt at all, present is still impossible there (F-1's
    # original code, unchanged -- the debt gate did not replace it)
    naked = _tiny_artifact()
    naked.bundle.channel_status = [
        (
            s.model_copy(update={
                "state": "present",
                "source_input_ids": ("tiny",),
                "covered_by_debt_ids": (),
            })
            if s.channel == "dimensions"
            else s
        )
        for s in naked.bundle.channel_status
    ]
    err = _expect_error(_refinalize(naked), "PRESENT_CHANNEL_WITHOUT_PAYLOAD")
    assert err.context == {"channel": "dimensions"}

    # the other direction: the genuine whole-channel zero run keeps its
    # exit (walls CAN carry payload, and this run carried none)
    honest = _empty_artifact()
    honest.bundle.evidence_debts.append(
        _zero_payload_debt("debt_zero_walls", "walls")
    )
    validate_evidence_bundle(_refinalize(honest))


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


def test_as_drawn_plan_is_adapt_not_consumed():
    """⭐ FLIPPED (module 7 wiring, 2026-09-02) from ``test_as_drawn_is_
    still_not_consumed`` -- the flip this pin's own docstring said must be
    on-purpose.  The adapter is registered: disposition ``ADAPT``, which
    still means ⛔ NOT consumed (adapting and pasting are disjoint wires)
    and ⛔ never an offender -- the ledger contract this module's bundles
    rely on is unchanged where it touches us."""
    from src.agent.reading.vector_contract import CONTRACTS, Disposition

    spec = next(s for s in CONTRACTS
                if s.contract_id == CONTRACT_AS_DRAWN_PLAN)
    assert spec.disposition is Disposition.ADAPT


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


# =========================================================================== #
# Rework-3 (2026-09-01) -- ``absent`` while the payload rides along
# (dispatch: ../request/2026-09-01_o22m2_absent_with_payload_dispatch.md)
#
# ⭐ Every fixture below builds the TARGET QUANTITY directly and then WITNESSES
#   it before asserting any behaviour: "this row says absent" and "this bundle
#   really carries N positive claims for that channel" are both measured off
#   the bundle, by this file's own arithmetic, ⛔ never by asking the module
#   under test whether it thinks there is payload.  A fixture that only sets up
#   a condition which USUALLY produces the target quantity is what let 27 locks
#   go green over a live defect elsewhere this week.
# =========================================================================== #
def _row(bundle, channel: str):
    """The declared row for ``channel``, or None -- read off the bundle."""
    return next((c for c in bundle.channel_status if c.channel == channel), None)


def _measured_walls_payload(bundle) -> int:
    """This file's OWN count of positive walls payload in the bundle.

    ⛔ Does not call ``evidence_contract``: a fixture that measures with the
    instrument under test cannot witness anything.  A wall claim is a
    positive walls product by definition; a ``claimed_wall`` ledger row is
    the ledger asserting the walls leg consumed that face."""
    return len(bundle.wall_claims) + len(
        [d for d in bundle.face_dispositions if d.status == "claimed_wall"]
    )


def _measured_openings_payload(bundle) -> int:
    return len(bundle.opening_claims)


_R3_MEASURE = {
    "walls": _measured_walls_payload,
    "plan_openings": _measured_openings_payload,
}


def _declare_absent(art, channel: str, debt_id: str | None = None):
    """Flip ONE channel's declaration to ``absent`` + a ``missing_channel``
    debt, changing nothing else -- the payload stays exactly where it was."""
    debt_id = debt_id or f"debt_r3_{channel}"
    out = art.model_copy(deep=True)
    out.bundle.evidence_debts = sorted(
        [*out.bundle.evidence_debts, EvidenceDebtV1(
            debt_id=debt_id, kind="missing_channel", channel=channel,
            description="declared absent by this fixture",
            obligation=None,
        )],
        key=lambda d: d.debt_id,
    )
    out.bundle.channel_status = [
        (
            ChannelStatusV1(channel=channel, state="absent",
                            covered_by_debt_ids=(debt_id,))
            if c.channel == channel else c
        )
        for c in out.bundle.channel_status
    ]
    return _refinalize(out)


def _all_non_wall_doc() -> dict:
    """A LEGAL as-drawn product whose every face line is declared non-wall.

    ⭐ This is not a hypothetical: it is the shape module 3's approved
    adapter emits (it declares walls ``present`` only when a positive claim
    exists) and module 4's compiler consumes.  Its ledger is FULL -- one
    disposition per face line, as invariant 2 demands -- while the walls leg
    produced nothing at all."""
    doc = _tiny_doc()
    hyp = doc["hypotheses"]
    hyp["pairs"] = []
    hyp["pairs_status"] = "SELECTED"
    hyp["unpaired_wall_faces"] = {}
    hyp["non_wall_face_lines"] = {
        f["id"]: "furniture edge on this dialect"
        for f in doc["observations"]["face_lines"]
    }
    AsDrawnPlanV2.model_validate(doc)  # premise: this IS a legal product
    return doc


def _all_non_wall_artifact():
    doc = _all_non_wall_doc()
    raw = json.dumps(doc, indent=1).encode("utf-8")
    art = _bundle_from_as_drawn(json.loads(raw), raw, "all_non_wall", "7f")
    # the factory hard-codes walls=present; module 3's adapter would declare
    # absent here, which is what this fixture needs.
    return _declare_absent(art, "walls", "debt_missing_walls_all_non_wall")


def test_r3_absent_channel_may_not_carry_its_payload(monkeypatch):
    """Rework-3, the dispatch's §一.  Declaring a channel ``absent`` used to
    make BOTH earlier closures step aside (each opened with
    ``if status.state != "present": continue``), so two wall claims / four
    dispositions / an opening claim travelled in a bundle that said the
    channel carried nothing.

    BEFORE (reconciliation neutered): the tree-of-record waves it through --
    the hole is reproduced HERE, ⛔ not transcribed from the dispatch.
    AFTER: loud, naming the channel and which members carried the payload.
    """
    for channel in ("walls", "plan_openings"):
        art = _declare_absent(_tiny_artifact(), channel)
        bundle = art.bundle

        # ── witness the target quantity, both halves, before asserting ──
        row = _row(bundle, channel)
        assert row is not None and row.state == "absent", (
            f"fixture failed to declare {channel} absent: {row}"
        )
        carried = _R3_MEASURE[channel](bundle)
        assert carried > 0, (
            f"fixture carries no {channel} payload -- it would be testing "
            f"nothing (measured {carried})"
        )

        # BEFORE
        monkeypatch.setattr(
            evidence_contract, "_assert_channel_payload_closure", lambda b: None
        )
        validate_evidence_bundle(art)
        monkeypatch.undo()

        # AFTER
        err = _expect_error(art, "CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD")
        assert err.context["channel"] == channel
        assert err.context["state"] == "absent"
        assert err.context["payload_row_count"] == carried

    # the two §一 readings, pinned as numbers so a fixture that quietly
    # empties itself cannot make this test pass by carrying nothing
    tiny = _tiny_artifact().bundle
    assert (len(tiny.wall_claims), len(tiny.face_dispositions),
            len(tiny.opening_claims)) == (2, 4, 1)


def test_r3_honest_absent_channels_are_not_killed():
    """The other direction (dispatch acceptance 2): every genuinely empty
    ``absent`` channel must STILL pass.  Only doing the half above would
    turn every honest absence red.

    ⭐ The load-bearing case is the last one: a full disposition ledger with
    zero wall claims.  The ledger is a function of the SOURCE PRODUCT
    (invariant 2 mandates a row per face line), ⛔ not of the walls leg, so
    reading "the ledger is non-empty" as "the walls channel produced" would
    kill module 3's honest output and module 4's fixture.
    """
    # the channels this plan-family fixture cannot carry.  B3 (2026-09-03)
    # gave elevation_openings and floor_levels payload members, so for THEM
    # "absent with an empty member list" is now the measured truth the
    # closure gate checks; dimensions/room_roles stay payloadless (B-2).
    tiny = _tiny_artifact()
    for channel in (
        "dimensions", "room_roles", "elevation_openings", "floor_levels",
    ):
        row = _row(tiny.bundle, channel)
        assert row is not None and row.state == "absent", row
    validate_evidence_bundle(tiny)          # whole artifact
    evidence_contract._assert_channel_payload_closure(tiny.bundle)  # this gate

    # walls truly empty: the reviewer's F-1 product, declared absent
    empty = _declare_absent(_empty_artifact(), "walls", "debt_walls_zero_run")
    assert _row(empty.bundle, "walls").state == "absent"
    assert _measured_walls_payload(empty.bundle) == 0
    validate_evidence_bundle(empty)
    evidence_contract._assert_channel_payload_closure(empty.bundle)

    # ⭐ walls absent + a FULL non-wall ledger (module 3's real output shape)
    ledger = _all_non_wall_artifact()
    assert _row(ledger.bundle, "walls").state == "absent"
    assert _measured_walls_payload(ledger.bundle) == 0
    assert len(ledger.bundle.wall_claims) == 0
    assert len(ledger.bundle.face_dispositions) == 4, (
        "the ledger must be FULL -- that is the whole point of this case"
    )
    validate_evidence_bundle(ledger)
    evidence_contract._assert_channel_payload_closure(ledger.bundle)


def test_r3_zero_payload_channel_exit_survives():
    """Dispatch acceptance 3: ``walls=present`` + an explicit
    ``zero_payload_channel`` debt -- the honest "wired, produced nothing this
    run" -- must still pass after the reconciliation became two-directional.
    """
    art = _empty_artifact()
    art.bundle.evidence_debts.append(EvidenceDebtV1(
        debt_id="debt_zero_walls", kind="zero_payload_channel",
        channel="walls", description="walls wired, produced nothing",
        obligation=None,
    ))
    art = _refinalize(art)
    assert _row(art.bundle, "walls").state == "present"
    assert _measured_walls_payload(art.bundle) == 0
    assert any(d.kind == "zero_payload_channel" and d.channel == "walls"
               for d in art.bundle.evidence_debts)
    validate_evidence_bundle(art)
    evidence_contract._assert_channel_payload_closure(art.bundle)


def test_r3_a_deleted_channel_row_is_not_a_third_state(monkeypatch):
    """⭐ Dispatch acceptance 5, same-shape input #1 -- ⛔ not one of §一's.

    If the reconciliation walked the DECLARED ROWS, the identical payload
    would leave by deleting the row instead of flipping its value: the
    carrier swaps from the VALUE of ``state`` to the EXISTENCE of ``state``
    ([[gate-measures-right-but-carrier-gets-swapped]]).  So the loop walks
    the channel domain and an undeclared channel is loud."""
    art = _tiny_artifact().model_copy(deep=True)
    art.bundle.channel_status = [
        c for c in art.bundle.channel_status if c.channel != "walls"
    ]
    art = _refinalize(art)

    # witness: the row is really gone AND the payload is really still here
    assert _row(art.bundle, "walls") is None
    carried = _measured_walls_payload(art.bundle)
    assert carried > 0, "no walls payload left -- the fixture proves nothing"

    monkeypatch.setattr(
        evidence_contract, "_assert_channel_payload_closure", lambda b: None
    )
    validate_evidence_bundle(art)  # BEFORE: an undeclared channel was free
    monkeypatch.undo()

    err = _expect_error(art, "CHANNEL_STATUS_MISSING")
    assert err.context["channel"] == "walls"

    # green anchor for THIS gate: declaring the row again (truthfully) passes
    restored = _tiny_artifact()
    assert _row(restored.bundle, "walls").state == "present"
    evidence_contract._assert_channel_payload_closure(restored.bundle)


def test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload(monkeypatch):
    """⭐ Dispatch acceptance 5, same-shape input #2 -- ⛔ not one of §一's.

    A third carrier: WHICH ROWS COUNT.  On a non-as-drawn source the
    claim<->disposition closure cannot see a ``claimed_wall`` ledger row
    (its ``face_index`` is empty), so a bundle can declare walls ``absent``,
    carry ZERO wall claims, and still assert through the ledger that a face
    was consumed by a wall.  Reading walls payload as "wall_claims only"
    would let exactly this through.
    """
    art = _legacy_artifact().model_copy(deep=True)
    bundle = art.bundle
    claim = bundle.wall_claims[0]
    trace = claim.trace_ref
    bundle.wall_claims = []
    bundle.face_dispositions = [FaceDispositionV1(
        face_ref=trace, status="claimed_wall",
        consuming_claim_id=claim.claim_id,
    )]
    art = _declare_absent(_refinalize(art), "walls", "debt_walls_legacy_absent")
    bundle = art.bundle

    # witness both halves of the target quantity
    assert _row(bundle, "walls").state == "absent"
    assert len(bundle.wall_claims) == 0, "the claim list must be empty here"
    assert _measured_walls_payload(bundle) == 1, (
        "the ledger must carry exactly the one claimed_wall row under test"
    )

    monkeypatch.setattr(
        evidence_contract, "_assert_channel_payload_closure", lambda b: None
    )
    validate_evidence_bundle(art)  # BEFORE: this shape was accepted
    monkeypatch.undo()

    err = _expect_error(art, "CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD")
    assert err.context["channel"] == "walls"
    assert err.context["payload_rows"] == ["face_dispositions"]


def test_r3_every_payload_bearing_bundle_field_is_declared():
    """The map is a DECLARATION, so it must be reconciled against the bundle
    type -- otherwise a future payload member is silently unwatched and
    ``absent`` becomes free again for it
    ([[declare-the-dialect-plus-consumption-ledger]]).

    ⛔ This is a rule, not a snapshot of today's names: every list-valued
    field of the bundle must be EITHER mapped to a channel OR listed as
    bookkeeping with a reason.  Adding a field to either side is a
    deliberate act; adding one to neither is red."""
    not_payload = {
        "source_artifacts": "the frozen-source identity table, not a channel product",
        "channel_status": "the routing table being reconciled -- not its own payload",
        "evidence_debts": "the known-missing ledger; a debt is the excuse, not the payload",
    }
    list_fields = {
        name for name, f in CorrectionEvidenceBundleV1.model_fields.items()
        if typing.get_origin(f.annotation) is list
    }
    assert list_fields, "no list-valued bundle fields found -- introspection broke"
    mapped = {
        member
        for members in evidence_contract.CHANNEL_PAYLOAD_MEMBERS.values()
        for member in members
    }
    assert mapped <= list_fields, (
        f"the map names fields the bundle does not have: {sorted(mapped - list_fields)}"
    )
    unaccounted = list_fields - mapped - set(not_payload)
    assert not unaccounted, (
        "bundle field(s) neither mapped to a channel nor declared "
        f"bookkeeping: {sorted(unaccounted)}"
    )
    assert not (mapped & set(not_payload)), "a field cannot be both"
    # every declared channel key is a real channel
    assert set(evidence_contract.CHANNEL_PAYLOAD_MEMBERS) <= set(
        evidence_contract.CHANNELS
    )


def test_r3_a_mapped_member_without_a_source_rule_is_loud(monkeypatch):
    """Extending the map without teaching the source closure where that
    member's identity lives must be LOUD, ⛔ not a silently empty source set
    (a silently empty set would make B-1's forward check vacuous for it)."""
    monkeypatch.setattr(
        evidence_contract,
        "CHANNEL_PAYLOAD_MEMBERS",
        {**evidence_contract.CHANNEL_PAYLOAD_MEMBERS,
         "walls": ("wall_claims", "face_dispositions", "source_artifacts")},
    )
    art = _tiny_artifact()
    assert art.bundle.source_artifacts, "fixture must carry the new member"
    _expect_error(art, "PAYLOAD_MEMBER_WITHOUT_SOURCE_RULE")


def test_obligation_is_a_closed_enum_not_a_free_string():
    """Dispatch 2026-09-04e T4-a, acceptance #1: ``obligation`` is a
    CLOSED Literal enum, ⛔ not a free string.  Undefined values (a typo
    of the real one, an arbitrary string, a non-string) are refused by
    the schema; the field is REQUIRED (T2 -- a producer cannot skip the
    decision); the one defined value plus ``None`` is the whole domain,
    and that domain is exactly what today's producers mint (acceptance
    #5 -- no unused slots)."""
    # the whole domain, read off the type itself (a rule, ⛔ not a
    # transcript of one run's values)
    assert set(typing.get_args(DebtObligationV1)) == {
        "elevation_chain_spans_whole_building"
    }
    base = dict(
        debt_id="debt_probe", kind="other_known_missing", description="d"
    )
    # a one-character typo of the real value -- the shape a free string
    # would wave through
    with pytest.raises(ValidationError):
        EvidenceDebtV1(**base, obligation="elevation_chain_spans_whole_buildings")
    # an arbitrary free string
    with pytest.raises(ValidationError):
        EvidenceDebtV1(**base, obligation="owner_b4")
    # a non-string
    with pytest.raises(ValidationError):
        EvidenceDebtV1(**base, obligation=1)
    # required: the mint must DECIDE (enum value or None), not skip
    with pytest.raises(ValidationError):
        EvidenceDebtV1(**base)
    # the two legal shapes
    assert (
        EvidenceDebtV1(
            **base, obligation="elevation_chain_spans_whole_building"
        ).obligation
        == "elevation_chain_spans_whole_building"
    )
    assert EvidenceDebtV1(**base, obligation=None).obligation is None
