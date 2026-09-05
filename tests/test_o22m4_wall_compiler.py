"""②-2 module 4: the provisional wall compiler (2026-08-31).

Dispatch: ``AI_agent/logs/reviews/request/
2026-08-31_o22m4_wall_compiler_dispatch.md`` (eight acceptance items, two
of them carried by name from earlier cross-family reviews).

What is locked here, per acceptance item
----------------------------------------
1  paired-face tail fidelity in BOTH directions: a longer face's unshared
   stretch survives as a ``SingleFaceFragmentV1`` that still names the
   ORIGINAL claim (design §9.2's own test name), and equal coverage
   produces ZERO fragments -- one direction alone would let an
   unconditional shredder pass;
2  (in module 3's test file) the pin is flipped to point at this
   implementation;
3  ⭐ the ambiguous debt is CONSUMED: real sm24 (78/98 undecided) under
   ``strict`` blocks loudly with every debt named and the ratio measured
   independently from the product; under ``exploratory`` it continues with
   ``completion="degraded"`` and the undecided ratio on the record;
4  sm24's four solid bands compile to four walls, widths recomputed from
   the product's own ``edges_m`` -- no invented partner face;
5  the three thickness names stay separate, each with provenance
   (observation / declaration / match label); the pair node's cached
   ``spacing_m`` is never trusted -- mutate it and the compiled spacing
   does not move;
6  the midline is derived ONLY here: no centerline/midline field exists on
   the producer types or anywhere in the bundle, compilation derives real
   support lines, and it writes NOTHING back (bundle serialization,
   frozen bytes and the on-disk product all byte-identical after a
   compile; the module performs no file I/O at all);
7  (import probe here, git-diff half in the execution report) the compiler
   reaches neither the pipeline nor any judge module;
8  (run command in the execution report).

Plus the design §9.2 rows this module owns: unknown basis never auto
resolves (f9's real no-thickness shape AND the §5.2.1 thickness-bearing
shape), a structured centerline declaration is the one legal identity,
spacing+thickness survive to the IR the kernel will read, same bundle +
same decisions compile byte-identically, and the module-4 half of module
2's NF-4 #5 pin: a dangling UNSELECTED candidate dies in this compiler's
own full-graph walk.

Rework (2026-09-01, cross-review blocker 1): the ``single_face`` CHANNEL
now has fixtures of its own.  The review measured every ``_compile_*``
entry point over this file plus module 3's and found this one had ZERO
inventory -- a mutation removing the open item entirely survived 43 green
tests.  Locked here now: the real unpaired face (sm25_2f ``L012``) opens
an ``axis_offset_undetermined`` item with both offset families, a unique
thickness scale still requires a decision (design §6.1: even a candidate
that survives filtering unique needs an explicit decision / re-perception),
a source with NO scale opens with an empty candidate set, and the two
non-default ``counterface_state`` values compile through the same channel
with the same no-silent-axis behaviour.

Rework 2 (2026-09-01, cross-review F-1 + N-1): the unique-SCALE fixture
above measured a PROXY, not the target.  One thickness value still
enumerates both signs (``candidate count == 2``), so the reviewer's real
``len(candidates) == 1 => silent auto-execute`` mutation survived all 27
tests green.  Locked here now: a fixture whose product fact IS
``len(candidates) == 1`` (the REAL enumerator narrowed to one surviving
candidate -- the shape side-evidence / stricter filtering will produce),
asserting its own premise first and the item's openness second, plus one
lock per branch of ``why_not_auto_resolved`` so the decision packet can
never carry a story opposite to its own candidate set.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import subprocess
import sys
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel

from src.agent.correction import wall_compiler as wc
from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_plan,
    adapt_legacy_reading_view,
)
from src.agent.correction.evidence_contract import (
    BUNDLE_SCHEMA_VERSION,
    SOURCE_CONTRACT_AS_DRAWN,
    CorrectionEvidenceBundleArtifactV1,
    CorrectionEvidenceBundleV1,
    ChannelStatusV1,
    EvidenceContractError,
    EvidenceDebtV1,
    FaceDispositionV1,
    FrozenSourceV1,
    ObservationRefV1,
    ArtifactPointerV1,
    SingleFaceWallClaimV1,
    SourceArtifactV1,
    as_drawn_face_index,
    finalize_bundle,
    validate_evidence_bundle,
)
from src.agent.correction.window_sources import (
    canonical_json_bytes,
    source_locator,
)
from src.agent.reading.as_drawn.schema import SCHEMA, AsDrawnPlanV2

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_F9 = Path("tests/fixtures/f9_window_host_crash/0_reading/1f_view.json")


# ── shared helpers ─────────────────────────────────────────────────────────── #
def _raw_product(name: str) -> bytes:
    p = _PRODUCTS / name
    # ⛔ no exists()-and-skip: a vanished tracked fixture must be a red.
    assert p.is_file(), f"tracked as-drawn product missing: {p}"
    return p.read_bytes()


def _adapted(name: str, floor: str) -> CorrectionEvidenceBundleArtifactV1:
    return adapt_as_drawn_plan(
        _raw_product(name), input_id=name.removesuffix(".json"), floor_ref=floor
    )


def _adapt_doc(doc: dict, input_id: str, floor: str):
    raw = json.dumps(doc, indent=1).encode("utf-8")
    return adapt_as_drawn_plan(raw, input_id=input_id, floor_ref=floor)


def _expect_error(thunk, code: str, cls=wc.WallCompilerError):
    with pytest.raises(cls) as exc:
        thunk()
    assert exc.value.code == code, (
        f"expected {code}, got {exc.value.code}: {getattr(exc.value, 'context', '')}"
    )
    return exc.value


def _face(fid: str, axis: str, world_axis: str, col: int,
          runs_px: list, runs_m: list | None = None) -> dict:
    if runs_m is None:
        runs_m = [[lo / 10.0, hi / 10.0] for lo, hi in runs_px]
    return {
        "id": fid, "axis": axis, "constant_world_axis": world_axis,
        "pos_px": float(col), "pos_m": 0.01 * col,
        "support_cols_px": [col, col + 1], "edges_m": [0.0, 0.02],
        "support_width_m": 0.02, "runs_px": runs_px, "runs_m": runs_m,
        "gaps": [], "ink_coverage_per_run": [1.0] * len(runs_px),
        "covered_px": sum(hi - lo for lo, hi in runs_px),
        "support_px": sum(hi - lo for lo, hi in runs_px) + 1,
    }


def _pair_doc(runs_a_px: list, runs_b_px: list) -> dict:
    """F01/F02 selected as a pair (run lengths caller's choice), F03
    disposed non_wall.  Minimal honest as-drawn shape."""
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, runs_a_px),
            _face("F02", "col", "x", 112, runs_b_px),
            _face("F03", "row", "y", 200, [[5, 9]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [
                {"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                 "spacing_m": 0.12, "matched_declared_mm": [120],
                 "overlap_px": 30, "source": "selected"},
            ],
            "pair_candidates": [
                {"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                 "spacing_m": 0.12, "matched_declared_mm": [120],
                 "overlap_px": 30},
            ],
            "opening_candidates": [],
            "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {"F03": "a furniture edge"},
            "unpaired_wall_faces": {},
            "solid_band_walls": {},
            "ambiguous_face_lines": {},
        },
    }
    AsDrawnPlanV2.model_validate(doc)  # premise: this IS a legal product
    return doc


def _legacy_doc(strokes: list[dict]) -> dict:
    doc = {"image_label": "legacy plan", "strokes": strokes}
    return doc


def _adapt_legacy(strokes: list[dict], input_id="legacy_synth"):
    raw = json.dumps(_legacy_doc(strokes), indent=1).encode("utf-8")
    return adapt_legacy_reading_view(raw, input_id=input_id, floor_ref="1f")


_WALL_STROKE = {
    "id": "W01", "pen": "wall",
    "geometry": {"p1": [0.0, 0.0], "p2": [9.0, 0.0], "thickness_m": None},
    "note": "centreline (prose only -- ⛔ never parsed)",
}

IDENTITY_BAN_SET = {wc.IDENTITY_BAN}


def _walk_values(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_values(value)
    else:
        yield node


# =========================================================================== #
# Acceptance 1 -- tail fidelity, both directions (design §9.2's own name)
# =========================================================================== #
def test_paired_face_unshared_tail_survives_as_single_face_fragment():
    art = _adapt_doc(_pair_doc(runs_a_px=[[10, 100]], runs_b_px=[[10, 40]]),
                     "tail_unequal", "9f")
    validate_evidence_bundle(art)  # green premise
    comp = wc.compile_wall_ir(art)

    pairs = [w for w in comp.walls if w.claim_kind == "paired_faces"]
    assert len(pairs) == 1
    wall = pairs[0]
    # the double-face wall exists ONLY over the jointly covered stretch
    assert wall.double_face_intervals == ((1.0, 4.0),)
    # the unshared tail survives as a fragment STILL OWNED by the claim
    assert len(wall.unshared_tail_fragments) == 1
    frag = wall.unshared_tail_fragments[0]
    assert frag.source_claim_id == wall.source_claim_ids[0]
    assert frag.tail_of == "face_a"
    assert frag.face_ref.observation_id == "F01"
    assert frag.along_interval_m == (4.0, 10.0)
    # ⛔ neither drop (intersection) nor inflate (union): the wall's own
    # coverage is the union, the double-face part is the intersection
    assert wall.resolved_along_intervals == ((1.0, 10.0),)
    # the midline is the perpendicular midpoint of the two faces
    assert wall.resolved_centerline is not None
    assert wall.resolved_centerline.constant_pos_m == pytest.approx(
        (1.0 + 1.12) / 2.0
    )


def test_equal_coverage_produces_no_fragment():
    """The second direction: with nothing to cut, NO fragment of any kind
    may appear -- an unconditional shredder must fail here."""
    art = _adapt_doc(_pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]]),
                     "tail_equal", "9f")
    validate_evidence_bundle(art)
    comp = wc.compile_wall_ir(art)
    wall = next(w for w in comp.walls if w.claim_kind == "paired_faces")
    assert wall.unshared_tail_fragments == ()
    assert wall.double_face_intervals == ((1.0, 8.0),)
    assert wall.resolved_along_intervals == ((1.0, 8.0),)
    assert sum(len(w.unshared_tail_fragments) for w in comp.walls) == 0


# =========================================================================== #
# Acceptance 3 -- the ambiguous debt is consumed (both profile halves)
# =========================================================================== #
def test_sm24_strict_blocks_on_ambiguous_debt_and_names_every_one():
    art = _adapted("sm24_1f_v2.json", "1f")
    doc = json.loads(_raw_product("sm24_1f_v2.json"))
    hyp = doc["hypotheses"]

    # ⭐ premise measured INDEPENDENTLY from the product (not from the
    # compiler): every ambiguous face participates in the candidate graph,
    # with these exact counts.
    counts: dict[str, int] = {}
    for cand in hyp["pair_candidates"]:
        for side in ("face_a", "face_b"):
            counts[cand[side]] = counts.get(cand[side], 0) + 1
    ambiguous = set(hyp["ambiguous_face_lines"])
    total = len(doc["observations"]["face_lines"])
    assert len(ambiguous) == 78 and total == 98
    assert ambiguous <= set(counts)  # 78/78 in the graph (module 3's F-2)

    err = _expect_error(
        lambda: wc.compile_wall_ir(art, profile="strict"),
        "AMBIGUOUS_DEBT_BLOCKS_STRICT_PROFILE",
    )
    assert err.context["ambiguous_faces"] == 78
    assert err.context["disposed_face_lines"] == 98
    assert err.context["undecided_ratio"] == 78 / 98
    assert err.context["remedy"] == "wall_level_reperception"
    assert len(err.context["debt_ids"]) == 78
    # the per-face dependency analysis matches the independent recount
    reported = {
        entry["observation_id"]: entry["candidate_count"]
        for entry in err.context["participation"]
    }
    assert reported == {fid: counts[fid] for fid in ambiguous}


def test_sm24_exploratory_continues_and_reports_the_undecided_ratio():
    art = _adapted("sm24_1f_v2.json", "1f")
    comp = wc.compile_wall_ir(art, profile="exploratory")

    assert comp.completion == "degraded"  # ⛔ never "complete" past a debt
    assert comp.undecided is not None
    assert comp.undecided.disposed_face_lines == 98
    assert comp.undecided.ambiguous_face_lines == 78
    assert comp.undecided.undecided_ratio == 78 / 98
    assert comp.undecided.per_source[0].input_id == "sm24_1f_v2"
    # the debts ride along as residual, and the analysis names every face
    ambiguous_debt_ids = {
        d.debt_id for d in art.bundle.evidence_debts
        if d.kind == "ambiguous_face"
    }
    assert ambiguous_debt_ids <= set(comp.residual_debt_ids)
    assert len(comp.ambiguous_analysis) == 78
    assert all(a.candidate_participation > 0 for a in comp.ambiguous_analysis)
    assert all(a.topology_exposure == "candidate_graph"
               for a in comp.ambiguous_analysis)


# =========================================================================== #
# Acceptance 4 -- sm24's four solid bands: four walls, no fake faces
# =========================================================================== #
def test_sm24_four_solid_bands_become_walls_without_fake_faces():
    art = _adapted("sm24_1f_v2.json", "1f")
    doc = json.loads(_raw_product("sm24_1f_v2.json"))
    faces = {f["id"]: f for f in doc["observations"]["face_lines"]}
    expected_widths = {
        fid: node["edges_m"][1] - node["edges_m"][0]
        for fid, node in faces.items()
        if fid in doc["hypotheses"]["solid_band_walls"]
    }
    assert len(expected_widths) == 4  # premise: the product really has four

    comp = wc.compile_wall_ir(art, profile="exploratory")
    bands = [w for w in comp.walls if w.claim_kind == "solid_band"]
    assert len(bands) == 4
    assert len(comp.walls) == 12  # 8 paired + 4 bands, nothing else minted
    for wall in bands:
        oid = wall.source_refs[0].observation_id
        # ONE source ref: no partner face was invented for a band
        assert len(wall.source_refs) == 1
        assert wall.observed_face_spacing_m == pytest.approx(
            expected_widths[oid]
        )
        assert wall.observed_basis == "ink_band_edges"
        assert wall.resolved_centerline is not None
        assert wall.resolved_centerline.constant_pos_m == pytest.approx(
            sum(faces[oid]["edges_m"]) / 2.0
        )
        assert wall.output_basis == "wall_axis"


# =========================================================================== #
# Acceptance 5 -- the three thickness names, each with a source
# =========================================================================== #
def _wall_for_pair(comp, face_a: str, face_b: str):
    for w in comp.walls:
        if w.claim_kind != "paired_faces":
            continue
        ids = {r.observation_id for r in w.source_refs}
        if ids == {face_a, face_b}:
            return w
    raise AssertionError(f"no paired wall for {face_a}/{face_b}")


def test_three_thickness_names_separated_with_provenance():
    raw = _raw_product("sm25_1f_v2.json")
    doc = json.loads(raw)
    art = adapt_as_drawn_plan(raw, input_id="sm25_1f_v2", floor_ref="1f")
    faces = {f["id"]: f for f in doc["observations"]["face_lines"]}
    comp = wc.compile_wall_ir(art, profile="strict")

    pair0 = doc["hypotheses"]["pairs"][0]
    assert pair0["matched_declared_mm"] == [240]  # premise: label present
    wall = _wall_for_pair(comp, pair0["face_a"], pair0["face_b"])
    recomputed = abs(
        faces[pair0["face_b"]]["pos_m"] - faces[pair0["face_a"]]["pos_m"]
    )
    # name 1: the OBSERVED spacing, recomputed from the two face nodes
    assert wall.observed_face_spacing_m == recomputed
    # name 2: unresolved until a decision executes
    assert wall.resolved_thickness_m is None
    assert wall.thickness_resolution is None
    # the item enumerates keep-vs-snap with BOTH provenance families
    item = next(
        i for i in comp.open_items
        if i.scope_entity_ids == (wall.wall_id,)
        and i.kind == "thickness_resolution"
    )
    ops = {c.symbolic_operation for c in item.candidates}
    assert ops == {"KEEP_OBSERVED_WIDTH", "SNAP_TO_DECLARATION"}
    snaps = sorted(
        c.thickness_source.value_m for c in item.candidates
        if c.symbolic_operation == "SNAP_TO_DECLARATION"
    )
    assert snaps == [0.12, 0.24]  # sm25_1f declares 240 and 120
    assert {
        c.thickness_source.provenance for c in item.candidates
    } == {"observed_spacing", "declared_callout"}


def test_thickness_decision_produces_the_resolution_record():
    raw = _raw_product("sm25_1f_v2.json")
    doc = json.loads(raw)
    art = adapt_as_drawn_plan(raw, input_id="sm25_1f_v2", floor_ref="1f")
    faces = {f["id"]: f for f in doc["observations"]["face_lines"]}
    comp0 = wc.compile_wall_ir(art, profile="strict")
    pair0 = doc["hypotheses"]["pairs"][0]
    wall0 = _wall_for_pair(comp0, pair0["face_a"], pair0["face_b"])
    item = next(
        i for i in comp0.open_items
        if i.scope_entity_ids == (wall0.wall_id,)
        and i.kind == "thickness_resolution"
    )
    observed = wall0.observed_face_spacing_m

    # KEEP: resolved == observed, delta 0, source = the observation
    keep = next(
        c for c in item.candidates
        if c.symbolic_operation == "KEEP_OBSERVED_WIDTH"
    )
    comp_keep = wc.compile_wall_ir(
        art, profile="strict", decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=keep.candidate_id
        ),)
    )
    wall_keep = _wall_for_pair(comp_keep, pair0["face_a"], pair0["face_b"])
    assert wall_keep.resolved_thickness_m == observed
    assert wall_keep.observed_face_spacing_m == observed  # ⛔ not overwritten
    assert wall_keep.thickness_resolution is not None
    assert wall_keep.thickness_resolution.operation_id == "KEEP_OBSERVED_WIDTH"
    assert wall_keep.thickness_resolution.delta_m == 0.0
    # ⭐ preview and execution are two INDEPENDENT computations (candidate
    # construction vs. decision application); this equality is their
    # reconciliation lock -- a drift in either one alone goes red here
    assert wall_keep.thickness_resolution.delta_m == keep.preview_delta_m
    assert wall_keep.resolved_thickness_m == keep.preview_thickness_m
    assert wall_keep.thickness_resolution.decision_id == \
        f"fixed:{keep.candidate_id}"
    assert [s.provenance for s in wall_keep.thickness_resolution.source_values
            ] == ["observed_spacing"]

    # SNAP to the 240 declaration: resolved 0.24, delta measured, and the
    # matched label rides ALONG (it never supplied the value)
    snap = next(
        c for c in item.candidates
        if c.symbolic_operation == "SNAP_TO_DECLARATION"
        and c.thickness_source.value_m == 0.24
    )
    comp_snap = wc.compile_wall_ir(
        art, profile="strict", decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=snap.candidate_id
        ),)
    )
    wall_snap = _wall_for_pair(comp_snap, pair0["face_a"], pair0["face_b"])
    assert wall_snap.resolved_thickness_m == 0.24
    assert wall_snap.thickness_resolution.delta_m == 0.24 - observed
    assert wall_snap.thickness_resolution.delta_m == snap.preview_delta_m
    assert wall_snap.resolved_thickness_m == snap.preview_thickness_m
    provenances = [
        s.provenance for s in wall_snap.thickness_resolution.source_values
    ]
    assert provenances == ["declared_callout", "matched_label"]


def test_selected_pair_values_are_recomputed_not_cached():
    """Design §9.2 / §4.1: the pair node's cached ``spacing_m`` /
    ``overlap_px`` are never trusted -- corrupt them and the compiled wall
    does not move.

    ⭐ The premise is MEASURED, not assumed: this product really carries
    pairs whose cached ``spacing_m`` disagrees with the two faces' own
    ``pos_m`` (e.g. L005/L007: cache 0.238 vs recomputed 0.2379…), which is
    the empirical reason the design mandates recomputation.  If a future
    product regenerates with a fully consistent cache this premise goes red
    -- pick a different tracked fixture, do not delete the premise.
    """
    doc = json.loads(_raw_product("sm25_1f_v2.json"))
    faces = {f["id"]: f for f in doc["observations"]["face_lines"]}

    def _recomputed(pair):
        return abs(faces[pair["face_b"]]["pos_m"] - faces[pair["face_a"]]["pos_m"])

    victim = next(
        (i, p) for i, p in enumerate(doc["hypotheses"]["pairs"])
        if p["spacing_m"] != _recomputed(p)
    )
    expected = _recomputed(victim[1])

    corrupted = json.loads(_raw_product("sm25_1f_v2.json"))
    corrupted["hypotheses"]["pairs"][victim[0]]["spacing_m"] = 999.0
    corrupted["hypotheses"]["pairs"][victim[0]]["spacing_px"] = 999.0
    corrupted["hypotheses"]["pairs"][victim[0]]["overlap_px"] = -1
    AsDrawnPlanV2.model_validate(corrupted)  # still a legal product

    comp = wc.compile_wall_ir(_adapt_doc(corrupted, "cached_lie", "1f"),
                              profile="strict")
    wall = _wall_for_pair(comp, victim[1]["face_a"], victim[1]["face_b"])
    assert wall.observed_face_spacing_m == expected
    assert wall.observed_face_spacing_m != 999.0


def test_malformed_declared_callouts_are_loud():
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    doc["declarations"] = {"thickness_callouts_mm": "240"}
    AsDrawnPlanV2.model_validate(doc)  # declarations is Any at module 1
    art = _adapt_doc(doc, "bad_callouts", "9f")
    err = _expect_error(
        lambda: wc.compile_wall_ir(art), "DECLARED_CALLOUTS_MALFORMED",
        cls=EvidenceContractError,
    )
    assert err.context["input_id"] == "bad_callouts"


# =========================================================================== #
# Acceptance 6 -- the midline is derived ONLY here, and nothing is written back
# =========================================================================== #
def _model_classes(annotation) -> list[type]:
    origin = typing.get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return [annotation]
        return []
    out: list[type] = []
    for arg in typing.get_args(annotation):
        out.extend(_model_classes(arg))
    return out


def _nested_models(root: type) -> set[type]:
    seen: set[type] = set()
    stack = [root]
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        for field in cls.model_fields.values():
            stack.extend(_model_classes(field.annotation))
    return seen


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_keys(value)


def test_midline_derived_only_here_and_nothing_written_back():
    product_path = _PRODUCTS / "sm25_1f_v2.json"
    disk_before = product_path.read_bytes()

    # (a) no centerline/midline FIELD exists on the producer's own types
    for cls in _nested_models(AsDrawnPlanV2):
        for name in cls.model_fields:
            assert "centerline" not in name.lower()
            assert "midline" not in name.lower(), (cls.__name__, name)
    # ... and none anywhere in the bundle artifact's serialization
    art = adapt_as_drawn_plan(
        disk_before, input_id="sm25_1f_v2", floor_ref="1f"
    )
    for key in _walk_keys(art.model_dump(mode="json")):
        assert "centerline" not in key.lower()
        assert "midline" not in key.lower(), key

    bundle_before = canonical_json_bytes(art.bundle.model_dump(mode="json"))
    raw_before = art.frozen_sources[0].raw_bytes

    comp = wc.compile_wall_ir(art, profile="strict")
    # positive control: the compiler DID derive support lines -- this test
    # must not pass vacuously
    assert any(w.resolved_centerline is not None for w in comp.walls)
    midlines = {
        w.resolved_centerline.constant_pos_m
        for w in comp.walls
        if w.resolved_centerline is not None
    }
    # and none of the derived values leaked back into the bundle/source
    assert canonical_json_bytes(art.bundle.model_dump(mode="json")) == \
        bundle_before
    assert art.frozen_sources[0].raw_bytes == raw_before
    assert product_path.read_bytes() == disk_before
    values_in_bundle = {
        v for v in _walk_values(art.bundle.model_dump(mode="json"))
        if isinstance(v, float)
    }
    assert not (midlines & values_in_bundle)

    # the module performs no file I/O at all: refs resolve in frozen bytes
    source = Path(inspect.getsourcefile(wc)).read_text(encoding="utf-8")
    for forbidden in ("open(", "read_bytes", "Path(", "write_bytes"):
        assert forbidden not in source, forbidden


# =========================================================================== #
# Acceptance 7 -- zero wiring (behavioural half; git diff is in the report)
# =========================================================================== #
#: The module's ENTIRE non-stdlib import face: module 2's two corrections
#: modules plus the pydantic every contract model already uses.  Anything
#: outside this set is a new wiring edge and must fail the AST lock below
#: on purpose.
_COMPILER_IMPORT_ALLOWLIST = frozenset({
    "src.agent.correction.evidence_contract",
    "src.agent.correction.window_sources",
    "pydantic",
})


def _probe_modules(target: str) -> set[str]:
    probe = (
        "import sys; import " + target + "; "
        "print(sorted(m for m in sys.modules if "
        "m == 'src.agent.pipeline' or m.startswith('src.agent.judge')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0, result.stderr
    return set(ast.literal_eval(result.stdout.strip()))


def test_compiler_adds_no_pipeline_or_judge_edge_beyond_module_2():
    """Zero wiring, measured where it is actually decidable.

    ⚠️ Why not "judge absent from sys.modules"?  Because that quantity is
    structurally unreachable inside this package: importing ANY
    ``correction`` submodule first executes the package init chain, and the
    upstream ``window_sources`` (module 2's own dependency, closed and
    cross-reviewed) transitively imports ``execution.step_orchestrator``,
    which imports ``judge.verdict`` / ``judge.executor`` at module level.
    Measured: importing module 2's ``evidence_contract`` alone brings in
    exactly ``{judge, judge.executor, judge.retry, judge.verdict}``.  A lock
    on bare absence could never go green here -- it would be measuring the
    package's pre-existing substrate, not this module's wiring.

    What this module must actually prove is TWO stronger things:
    1. DIFFERENCE: the set of pipeline/judge modules reachable after
       importing THIS module equals the set reachable after importing
       module 2's contract alone -- this module adds zero of them;
    2. FACE: every non-stdlib import in the module's own source is on the
       allowlist above (AST walk, comments and strings included in the
       parse), so a future third import fails loudly here, at the diff.
    """
    baseline = _probe_modules("src.agent.correction.evidence_contract")
    assert baseline, "premise broke: module 2 no longer reaches judge/pipeline"
    mine = _probe_modules("src.agent.correction.wall_compiler")
    assert mine == baseline, (
        f"wall_compiler changed the reachable pipeline/judge set: "
        f"added={sorted(mine - baseline)} removed={sorted(baseline - mine)}"
    )

    tree = ast.parse(
        Path(inspect.getsourcefile(wc)).read_text(encoding="utf-8")
    )
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    external = {
        name for name in imported
        if not name.startswith("_") and name.split(".")[0] not in sys.stdlib_module_names
    }
    assert external <= _COMPILER_IMPORT_ALLOWLIST, (
        f"import face grew beyond module 2's: {sorted(external - _COMPILER_IMPORT_ALLOWLIST)}"
    )


# =========================================================================== #
# Unknown basis never yields a silent axis (design §9.2 / §5.2.1)
# =========================================================================== #
def test_unknown_basis_item_is_never_auto_resolved_f9_shape():
    """f9's REAL shape: no typed basis, no typed thickness, contradictory
    centreline/skin signals only in free notes.  Every trace stays
    axis-less, its item has ZERO candidates, and no auto action touches
    it."""
    art = adapt_legacy_reading_view(
        _F9.read_bytes(), input_id="f9_1f", floor_ref="1f"
    )
    comp = wc.compile_wall_ir(art, profile="strict")

    walls = [w for w in comp.walls if w.claim_kind == "legacy_wall_trace"]
    assert len(walls) == 10
    assert all(w.resolved_centerline is None for w in walls)  # no axis trace
    assert all(w.output_basis is None for w in walls)
    items = {i.scope_entity_ids[0]: i for i in comp.open_items}
    assert len(items) == 10
    for wall in walls:
        item = items[wall.wall_id]
        assert item.kind == "legacy_basis_unknown"
        assert item.candidates == ()  # no thickness scale exists
        assert IDENTITY_BAN_SET <= set(item.exclusions)
        # ⛔ no auto action may touch an open item's wall
        assert all(wall.wall_id not in a.scope_entity_ids
                   for a in comp.auto_actions)
        assert all(a.kind != "identity_axis_from_centerline_evidence"
                   for a in comp.auto_actions)
    # a decision on an empty candidate set is loud, never invented
    some_item = next(iter(comp.open_items))
    err = _expect_error(
        lambda: wc.compile_wall_ir(art, profile="strict", decisions=(
            wc.FixedDecisionV1(item_id=some_item.item_id,
                               candidate_id="cand_nonexistent"),)
        ),
        "UNKNOWN_DECISION_CANDIDATE",
    )
    assert err.context["available"] == []


def test_unknown_basis_with_thickness_still_never_silent_identity():
    """The §5.2.1 shape: typed ``thickness_m=0.239``, no typed basis, and a
    free note that SAYS centreline.  Identity is not among the candidates
    (it is unrepresentable), the item is never auto-closed, and only an
    explicit offset decision produces an axis."""
    strokes = [dict(_WALL_STROKE)]
    strokes[0]["geometry"] = {**strokes[0]["geometry"], "thickness_m": 0.239}
    art = _adapt_legacy(strokes, input_id="w01_shape")
    comp = wc.compile_wall_ir(art, profile="strict")

    wall = next(w for w in comp.walls if w.claim_kind == "legacy_wall_trace")
    assert wall.observed_basis == "unknown"
    assert wall.resolved_centerline is None
    item = next(i for i in comp.open_items
                if i.scope_entity_ids == (wall.wall_id,))
    assert item.kind == "legacy_basis_unknown"
    assert {c.symbolic_operation for c in item.candidates} == {
        "OFFSET_POSITIVE", "OFFSET_NEGATIVE"
    }  # ⭐ identity is not even expressible
    assert IDENTITY_BAN_SET <= set(item.exclusions)
    assert all(c.thickness_source.provenance == "declared_field"
               and c.thickness_source.value_m == 0.239
               for c in item.candidates)
    assert {c.preview_constant_pos_m for c in item.candidates} == {
        0.0 + 0.239 / 2, 0.0 - 0.239 / 2
    }

    # no auto path: compiling again without decisions changes nothing
    comp_again = wc.compile_wall_ir(art, profile="strict")
    assert next(w for w in comp_again.walls
                if w.wall_id == wall.wall_id).resolved_centerline is None
    assert any(i.item_id == item.item_id for i in comp_again.open_items)

    # the explicit decision -- the ONLY closer -- produces the offset axis
    positive = next(c for c in item.candidates
                    if c.symbolic_operation == "OFFSET_POSITIVE")
    decided = wc.compile_wall_ir(
        art, profile="strict",
        decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=positive.candidate_id
        ),),
    )
    wall_decided = next(w for w in decided.walls if w.wall_id == wall.wall_id)
    assert wall_decided.resolved_centerline is not None
    assert wall_decided.resolved_centerline.constant_pos_m == \
        0.0 + 0.239 / 2
    assert wall_decided.resolved_thickness_m == 0.239
    assert wall_decided.output_basis == "wall_axis"
    assert not any(i.item_id == item.item_id for i in decided.open_items)
    assert decided.applied_decisions[0].symbolic_operation == \
        "OFFSET_POSITIVE"


def test_structured_centerline_is_the_one_legal_identity():
    strokes = [{
        **_WALL_STROKE,
        "geometry": {"kind": "line", "p1": [1.0, 2.0], "p2": [1.0, 7.0],
                     "thickness_m": None, "basis": "centerline"},
    }]
    art = _adapt_legacy(strokes, input_id="centerline_declared")
    comp = wc.compile_wall_ir(art, profile="strict")

    wall = next(w for w in comp.walls if w.claim_kind == "legacy_wall_trace")
    assert wall.observed_basis == "centerline"
    assert wall.resolved_centerline is not None
    assert wall.resolved_centerline.constant_world_axis == "x"
    assert wall.resolved_centerline.constant_pos_m == 1.0
    assert wall.resolved_along_intervals == ((2.0, 7.0),)
    assert wall.output_basis == "wall_axis"
    # the identity is an AUTO action carrying the structured evidence ref
    actions = [a for a in comp.auto_actions
               if wall.wall_id in a.scope_entity_ids]
    assert [a.kind for a in actions] == \
        ["identity_axis_from_centerline_evidence"]
    pointers = {r.json_pointer for r in actions[0].source_refs}
    assert "/strokes/0/geometry/basis" in pointers
    # and it opened no item: evidence-backed identity needs no decision
    assert not any(i.scope_entity_ids == (wall.wall_id,)
                   for i in comp.open_items)


def test_legacy_outer_skin_stroke_does_not_become_axis_trace():
    """Design §9.2: f9's real outer-skin-in-prose traces keep no axis -- the
    prose is not evidence, and nothing else supplies a basis."""
    art = adapt_legacy_reading_view(
        _F9.read_bytes(), input_id="f9_1f", floor_ref="1f"
    )
    doc = json.loads(_F9.read_bytes())
    notes = [s.get("note") or "" for s in doc["strokes"]
             if s.get("pen") == "wall"]
    assert any("外皮" in n for n in notes)  # premise: the prose signal exists
    comp = wc.compile_wall_ir(art, profile="strict")
    assert all(w.resolved_centerline is None for w in comp.walls)


def test_non_orthogonal_legacy_trace_opens_an_item_instead_of_snapping():
    strokes = [{
        **_WALL_STROKE,
        "geometry": {"p1": [0.0, 0.0], "p2": [5.0, 5.0], "thickness_m": 0.2},
    }]
    art = _adapt_legacy(strokes, input_id="diagonal")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "legacy_wall_trace")
    assert wall.resolved_centerline is None
    item = next(i for i in comp.open_items
                if i.scope_entity_ids == (wall.wall_id,))
    assert item.kind == "legacy_trace_non_orthogonal"
    assert item.candidates == ()


def test_pair_whose_world_axes_disagree_is_loud():
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    doc["observations"]["face_lines"][1][
        "constant_world_axis"] = "y"  # same image axis, other world axis
    AsDrawnPlanV2.model_validate(doc)
    art = _adapt_doc(doc, "axes_disagree", "9f")
    _expect_error(
        lambda: wc.compile_wall_ir(art),
        "PAIR_CONSTANT_WORLD_AXIS_DISAGREE", cls=EvidenceContractError,
    )


# =========================================================================== #
# non_wall honoured vs ambiguous debt (design §9.2 row) + kernel-entry survival
# =========================================================================== #
def test_non_wall_is_auto_accounted_but_ambiguous_is_debt():
    art = _adapted("sm25_1f_v2.json", "1f")
    doc = json.loads(_raw_product("sm25_1f_v2.json"))
    expected_non_wall = len(doc["hypotheses"]["non_wall_face_lines"])
    assert expected_non_wall == 5  # premise: the product really has five

    comp = wc.compile_wall_ir(art, profile="strict")  # 0 ambiguous: passes
    honored = [a for a in comp.auto_actions
               if a.kind == "honor_non_wall_declaration"]
    assert len(honored) == expected_non_wall
    assert comp.undecided.ambiguous_face_lines == 0
    assert comp.undecided.undecided_ratio == 0.0
    # the contrast half: sm24's ambiguous faces are NOT auto-anything
    art24 = _adapted("sm24_1f_v2.json", "1f")
    _expect_error(
        lambda: wc.compile_wall_ir(art24, profile="strict"),
        "AMBIGUOUS_DEBT_BLOCKS_STRICT_PROFILE",
    )


def test_observed_spacing_and_resolved_thickness_survive_kernel_entry():
    """R-6's module-4 half: after a KEEP decision both names are on the wall
    IR the kernel will read -- the observation was not overwritten by the
    resolution."""
    art = _adapted("sm24_1f_v2.json", "1f")
    comp = wc.compile_wall_ir(art, profile="exploratory")
    band = next(w for w in comp.walls if w.claim_kind == "solid_band")
    item = next(i for i in comp.open_items
                if i.scope_entity_ids == (band.wall_id,))
    keep = next(c for c in item.candidates
                if c.symbolic_operation == "KEEP_OBSERVED_WIDTH")

    decided = wc.compile_wall_ir(
        art, profile="exploratory",
        decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=keep.candidate_id
        ),),
    )
    wall = next(w for w in decided.walls if w.wall_id == band.wall_id)
    observed = band.observed_face_spacing_m
    assert wall.observed_face_spacing_m == observed
    assert wall.resolved_thickness_m == observed
    assert wall.thickness_resolution is not None
    assert wall.thickness_resolution.operation_id == "KEEP_OBSERVED_WIDTH"
    assert wall.thickness_resolution.delta_m == 0.0


# =========================================================================== #
# Determinism (design §9.2 row)
# =========================================================================== #
def test_same_bundle_and_decisions_produce_byte_identical_resolved_artifact():
    art = _adapted("sm25_1f_v2.json", "1f")
    comp = wc.compile_wall_ir(art, profile="strict")
    # close one wall's thickness item so the artifact carries a decision
    wall = comp.walls[0]
    item = next(i for i in comp.open_items
                if i.scope_entity_ids == (wall.wall_id,))
    keep = next(c for c in item.candidates
                if c.symbolic_operation == "KEEP_OBSERVED_WIDTH")
    decisions = (wc.FixedDecisionV1(
        item_id=item.item_id, candidate_id=keep.candidate_id
    ),)

    first = wc.compile_wall_ir(art, profile="strict", decisions=decisions)
    second = wc.compile_wall_ir(art, profile="strict", decisions=decisions)
    assert first.content_sha256 == second.content_sha256
    assert canonical_json_bytes(first.model_dump(mode="json")) == \
        canonical_json_bytes(second.model_dump(mode="json"))
    # the decision actually landed
    assert not any(i.item_id == item.item_id for i in first.open_items)
    assert [d.symbolic_operation for d in first.applied_decisions] == \
        ["KEEP_OBSERVED_WIDTH"]


# =========================================================================== #
# Module 2's NF-4 #5 pin, module-4 half: the compiler's own full-graph walk
# =========================================================================== #
def _hand_built_artifact(doc: dict, input_id: str):
    """A bundle the ADAPTER would refuse (its candidate walk is module 3's),
    but module 2 validates fine -- exactly the shape only this compiler's
    own walk can catch."""
    raw = json.dumps(doc, indent=1).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    meta = SourceArtifactV1(
        input_id=input_id, source_contract_id=SOURCE_CONTRACT_AS_DRAWN,
        source_output_sha256=sha, view_type="plan", floor_ref="9f",
    )
    index = as_drawn_face_index(doc)

    def fref(fid: str) -> ObservationRefV1:
        base = f"/observations/face_lines/{index[fid][0]}"
        return ObservationRefV1(
            input_id=input_id, source_contract_id=SOURCE_CONTRACT_AS_DRAWN,
            source_output_sha256=sha, json_pointer=base, observation_id=fid,
            source_locator=source_locator(
                input_id=input_id, observation_id=fid, output_sha256=sha
            ),
            pixel_witness_pointers=(
                f"{base}/support_cols_px", f"{base}/runs_px",
                f"{base}/edges_m", f"{base}/gaps",
            ),
            evidence_resolution="pixel_backed",
        )

    def pointer(target: str) -> ArtifactPointerV1:
        return ArtifactPointerV1(
            input_id=input_id, source_contract_id=SOURCE_CONTRACT_AS_DRAWN,
            source_output_sha256=sha, json_pointer=target,
        )

    dispositions = [
        FaceDispositionV1(
            face_ref=fref(fid), status="non_wall",
            reason_ref=pointer(f"/hypotheses/non_wall_face_lines/{fid}"),
        )
        for fid in doc["hypotheses"]["non_wall_face_lines"]
    ]
    debts = [
        EvidenceDebtV1(
            debt_id=f"debt_missing_walls_{input_id}", kind="missing_channel",
            channel="walls", description="no positive claim",
            obligation=None,
        ),
        EvidenceDebtV1(
            debt_id=f"debt_missing_plan_openings_{input_id}",
            kind="missing_channel", channel="plan_openings",
            description="no opening candidate",
            obligation=None,
        ),
    ]
    channels = [
        ChannelStatusV1(
            channel="walls", state="absent",
            covered_by_debt_ids=(f"debt_missing_walls_{input_id}",),
        ),
        ChannelStatusV1(
            channel="plan_openings", state="absent",
            covered_by_debt_ids=(f"debt_missing_plan_openings_{input_id}",),
        ),
    ]
    for channel in (
        "elevation_openings", "floor_levels", "dimensions", "room_roles",
    ):
        debt_id = f"debt_{channel}_{input_id}"
        debts.append(EvidenceDebtV1(
            debt_id=debt_id, kind="missing_channel", channel=channel,
            description="not carried",
            obligation=None,
        ))
        channels.append(ChannelStatusV1(
            channel=channel, state="absent", covered_by_debt_ids=(debt_id,)
        ))
    bundle = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=BUNDLE_SCHEMA_VERSION,
        source_artifacts=[meta],
        channel_status=channels,
        wall_claims=[],
        face_dispositions=dispositions,
        opening_claims=[],
        evidence_debts=debts,
    ))
    return CorrectionEvidenceBundleArtifactV1(
        bundle=bundle,
        frozen_sources=[FrozenSourceV1(artifact=meta, raw_bytes=raw)],
    )


def test_unselected_dangling_candidate_is_caught_by_compiler_walk():
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    hyp = doc["hypotheses"]
    hyp["pairs"] = []  # explicit empty selection: a legal product
    hyp["pairs_status"] = "SELECTED"
    hyp["non_wall_face_lines"] = {"F01": "a", "F02": "b", "F03": "c"}
    hyp["pair_candidates"] = [
        {"face_a": "F01", "face_b": "L999", "spacing_px": 1.0,
         "spacing_m": 0.01, "matched_declared_mm": [], "overlap_px": 3},
    ]
    AsDrawnPlanV2.model_validate(doc)

    art = _hand_built_artifact(doc, "dangling_candidate")
    validate_evidence_bundle(art)  # premise: module 2's layer passes it
    err = _expect_error(
        lambda: wc.compile_wall_ir(art),
        "PAIR_CANDIDATE_REFERENCES_UNKNOWN_FACE", cls=EvidenceContractError,
    )
    assert err.context["observation_id"] == "L999"
    assert err.context["candidate_index"] == 0
    assert err.context["selected"] is False

    # control: the same bundle with a RESOLVING candidate compiles green --
    # the refusal is about the dangling reference, nothing else
    hyp["pair_candidates"][0]["face_b"] = "F02"
    control = _hand_built_artifact(doc, "dangling_candidate_control")
    comp = wc.compile_wall_ir(control, profile="strict")
    assert comp.walls == []
    honored = [a for a in comp.auto_actions
               if a.kind == "honor_non_wall_declaration"]
    assert len(honored) == 3


# =========================================================================== #
# Decision-fault teeth
# =========================================================================== #
def test_unknown_and_duplicate_decisions_are_loud():
    art = _adapt_doc(_pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]]),
                     "decision_faults", "9f")
    comp = wc.compile_wall_ir(art)
    item = comp.open_items[0]
    keep = next(c for c in item.candidates
                if c.symbolic_operation == "KEEP_OBSERVED_WIDTH")
    _expect_error(
        lambda: wc.compile_wall_ir(art, decisions=(
            wc.FixedDecisionV1(item_id="item_missing",
                               candidate_id=keep.candidate_id),)
        ),
        "UNKNOWN_DECISION_ITEM",
    )
    _expect_error(
        lambda: wc.compile_wall_ir(art, decisions=(
            wc.FixedDecisionV1(item_id=item.item_id,
                               candidate_id=keep.candidate_id),
            wc.FixedDecisionV1(item_id=item.item_id,
                               candidate_id=keep.candidate_id),
        )),
        "DUPLICATE_DECISION_FOR_ITEM",
    )


# =========================================================================== #
# Rework (2026-09-01, blocker 1): the single_face CHANNEL, measured
# =========================================================================== #
def _unpaired_face_doc(
    callouts: list[int] | None, *, with_counterface: bool = True
) -> dict:
    """One honest as-drawn product with ONE unpaired wall face (F04) and,
    optionally, one non-wall line (F05).  ``callouts`` is the drawing's own
    thickness declaration list, or ``None`` for a source carrying NO
    thickness scale at all."""
    faces = [_face("F04", "col", "x", 300, [[10, 90]])]
    non_wall: dict[str, str] = {}
    if with_counterface:
        faces.append(_face("F05", "row", "y", 200, [[5, 9]]))
        non_wall = {"F05": "a furniture edge"}
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": faces},
        "declarations": ({} if callouts is None
                         else {"thickness_callouts_mm": callouts}),
        "hypotheses": {
            "pairs": [], "pair_candidates": [], "opening_candidates": [],
            "opening_types": None, "pairs_status": "SELECTED",
            "non_wall_face_lines": non_wall,
            "unpaired_wall_faces": {
                "F04": ("IS a wall face; its counterface is not in the "
                        "observations")
            },
            "solid_band_walls": {}, "ambiguous_face_lines": {},
        },
    }
    AsDrawnPlanV2.model_validate(doc)  # premise: this IS a legal product
    return doc


def _assert_axis_item_open_not_silent(comp, wall):
    """The single_face invariant in one place: with no side/thickness basis
    an ``axis_offset_undetermined`` item is OPEN, identity is excluded, no
    axis / thickness / output basis is minted, and NO auto action the
    compiler took on its own touches the wall (design §4.1: the claim
    asserts neither side nor thickness; §5.2: no silent midline; §6.1: the
    open item is a state boundary only a decision closes)."""
    item = next(
        i for i in comp.open_items if i.scope_entity_ids == (wall.wall_id,)
    )
    assert item.kind == "axis_offset_undetermined"
    assert IDENTITY_BAN_SET <= set(item.exclusions)
    assert wall.resolved_centerline is None  # ⛔ no silent axis
    assert wall.output_basis is None
    assert wall.observed_face_spacing_m is None
    assert wall.resolved_thickness_m is None
    assert all(wall.wall_id not in a.scope_entity_ids
               for a in comp.auto_actions)
    return item


def test_single_face_real_l012_opens_axis_item_with_both_offset_families():
    """The REAL shape (sm25_2f): one unpaired wall face on a drawing that
    declares two thickness scales.  The channel must OPEN, enumerate both
    offset families over both scales, and leave the axis to an explicit
    decision -- the exact invariant a dropped ``return wall, [], []`` used
    to remove invisibly (cross-review M7: 43 green, zero hits)."""
    raw = _raw_product("sm25_2f_v2.json")
    doc = json.loads(raw)
    hyp = doc["hypotheses"]
    # premise, measured on the product: exactly one unpaired face, no
    # ambiguous debt (so strict can run), two declared scales
    assert list(hyp["unpaired_wall_faces"]) == ["L012"]
    assert not (hyp["ambiguous_face_lines"] or {})
    assert doc["declarations"]["thickness_callouts_mm"] == [240, 120]

    art = adapt_as_drawn_plan(raw, input_id="sm25_2f_v2", floor_ref="2f")
    sf_claims = [c for c in art.bundle.wall_claims if c.kind == "single_face"]
    assert [c.counterface_state for c in sf_claims] == [
        "not_in_observations"
    ]  # the adapter's mechanical translation of the unpaired bucket

    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    assert wall.observed_basis == "single_observed_face"
    item = _assert_axis_item_open_not_silent(comp, wall)
    assert comp.completion == "degraded"  # the open item is a real boundary

    # candidates: BOTH signs over BOTH declared scales, each preview anchored
    # on the face's own pos (re-read from the doc, not from the output)
    pos = next(f["pos_m"] for f in doc["observations"]["face_lines"]
               if f["id"] == "L012")
    got = {
        (c.symbolic_operation, c.thickness_source.value_m):
            c.preview_constant_pos_m
        for c in item.candidates
    }
    assert set(got) == {
        (op, value) for op in ("OFFSET_POSITIVE", "OFFSET_NEGATIVE")
        for value in (0.24, 0.12)
    }
    for (op, value), preview in got.items():
        sign = 1.0 if op == "OFFSET_POSITIVE" else -1.0
        assert preview == pytest.approx(pos + sign * value / 2.0)
    assert all(c.thickness_source.provenance == "declared_callout"
               for c in item.candidates)

    # the legal exit exists and is the ONLY closer: an explicit decision
    chosen = next(
        c for c in item.candidates
        if c.symbolic_operation == "OFFSET_POSITIVE"
        and c.thickness_source.value_m == 0.24
    )
    decided = wc.compile_wall_ir(
        art, profile="strict",
        decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=chosen.candidate_id
        ),),
    )
    wall_decided = next(
        w for w in decided.walls if w.wall_id == wall.wall_id
    )
    assert wall_decided.resolved_centerline is not None
    assert wall_decided.resolved_centerline.constant_pos_m == \
        pytest.approx(pos + 0.24 / 2.0)
    assert wall_decided.output_basis == "wall_axis"
    assert wall_decided.resolved_thickness_m == 0.24
    assert not any(i.item_id == item.item_id for i in decided.open_items)


def test_single_face_unique_thickness_scale_still_requires_a_decision():
    """Design §6.1's explicit rule: when every candidate shares ONE
    thickness scale -- the value is unique, only the sign is left, which is
    'filtered unique' pushed to the edge this compiler can see -- the
    compiler must NOT converge and must keep the item open; a silent
    'unique ⇒ auto-execute' leg is exactly the path this lock exists to
    keep red."""
    art = _adapt_doc(_unpaired_face_doc([200]),
                     "single_face_one_scale", "9f")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)

    # premise of THIS lock: one scale, two signs
    assert {c.thickness_source.value_m for c in item.candidates} == {0.2}
    assert {c.symbolic_operation for c in item.candidates} == {
        "OFFSET_POSITIVE", "OFFSET_NEGATIVE"
    }
    assert {c.preview_constant_pos_m for c in item.candidates} == \
        {3.0 + 0.1, 3.0 - 0.1}

    # and recompiling without a decision changes nothing: no auto path
    again = wc.compile_wall_ir(art, profile="strict")
    assert next(w for w in again.walls if w.wall_id == wall.wall_id
                ).resolved_centerline is None
    assert any(i.item_id == item.item_id for i in again.open_items)


def test_single_face_without_any_scale_opens_with_empty_candidates():
    """The no-scale leg: the source carries NO thickness scale at all.  The
    candidate set is empty and the item is STILL opened -- the legal exits
    the code itself names are an explicit decision, wall-level
    re-perception, or a degraded profile; a silent axis is not among them,
    and a decision against the empty set is loud rather than invented."""
    art = _adapt_doc(_unpaired_face_doc(None), "single_face_no_scale", "9f")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)
    assert item.candidates == ()

    err = _expect_error(
        lambda: wc.compile_wall_ir(
            art, profile="strict",
            decisions=(wc.FixedDecisionV1(
                item_id=item.item_id, candidate_id="cand_invented"
            ),),
        ),
        "UNKNOWN_DECISION_CANDIDATE",
    )
    assert err.context["available"] == []


def _rebound_single_face_claim(art, **updates):
    """Rebuild the adapter's own bundle with the single_face claim's
    counterface fields replaced.  The adapter only ever emits the mechanical
    default state, so the other two values are hand-bound here on top of a
    bundle the adapter itself produced (its channel/debt routing is reused
    verbatim, not hand-copied)."""
    old = art.bundle
    claim = next(c for c in old.wall_claims if c.kind == "single_face")
    data = claim.model_dump()
    data.update(updates)
    new_claim = SingleFaceWallClaimV1(**data)
    rebuilt = finalize_bundle(CorrectionEvidenceBundleV1(
        schema_version=old.schema_version,
        source_artifacts=old.source_artifacts,
        channel_status=old.channel_status,
        wall_claims=[new_claim],
        face_dispositions=old.face_dispositions,
        opening_claims=old.opening_claims,
        evidence_debts=old.evidence_debts,
    ))
    return art.model_copy(update={"bundle": rebuilt})


def test_single_face_observed_unclaimed_counterface_still_no_silent_axis():
    """counterface_state='observed_unclaimed': the other face IS observed
    but was consumed by a non_wall disposition (its node pointer and
    disposition travel on the claim).  That is MORE evidence about the
    counterface, yet still no side/thickness basis -- the channel behaves
    exactly like the default state."""
    art = _adapt_doc(
        _unpaired_face_doc(None, with_counterface=True),
        "single_face_unclaimed", "9f",
    )
    f05_ref = next(
        d.face_ref for d in art.bundle.face_dispositions
        if d.face_ref.observation_id == "F05"
    )
    rebound = _rebound_single_face_claim(
        art,
        counterface_state="observed_unclaimed",
        counterface_observation_ref=f05_ref.model_dump(),
        counterface_disposition_status="non_wall",
    )
    validate_evidence_bundle(rebound)  # green premise: still a legal bundle
    comp = wc.compile_wall_ir(rebound, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)
    assert item.candidates == ()  # no scale in this source either


def test_single_face_ink_present_unpromoted_witness_still_no_silent_axis():
    """counterface_state='ink_present_unpromoted' (sm25_2f L012's own prose
    story, hand-bound): the counterface's ink is on the drawing but was
    never promoted to a face line.  The layer's one hard property of a
    witness pointer is that it RESOLVES (the ink position has no structured
    slot yet -- the producer's own types pin that absence), and the channel
    behaves the same: evidence ABOUT the other side is not a side/thickness
    basis for this one."""
    art = _adapt_doc(
        _unpaired_face_doc(None, with_counterface=False),
        "single_face_ink", "9f",
    )
    rebound = _rebound_single_face_claim(
        art,
        counterface_state="ink_present_unpromoted",
        counterface_witness_pointers=("/observations/face_lines/0/runs_px",),
    )
    validate_evidence_bundle(rebound)  # witness resolves: green premise
    comp = wc.compile_wall_ir(rebound, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)
    assert item.candidates == ()


# =========================================================================== #
# Rework 2 (2026-09-01, F-1): the TARGET quantity -- genuinely ONE candidate
# =========================================================================== #
def test_single_face_genuinely_single_candidate_stays_open(monkeypatch):
    """F-1 (rework 2): the target quantity is ``len(candidates) == 1``,
    ⛔ NOT "one thickness value" -- one value still enumerates both signs,
    which is 2 candidates; the unique-scale lock above pinned that proxy and
    the reviewer's real ``len(candidates) == 1 => silent auto-execute``
    mutation survived it green.

    A legal as-drawn product cannot reach one candidate today (nothing in
    the evidence names the wall's side, so both signs are always
    enumerated) -- but the channel must stay safe for the day something
    upstream CAN filter to one (side evidence, a stricter enumerator).  This
    fixture narrows the REAL enumerator to one surviving candidate and
    compiles through the REAL entry point; the item must STILL be open --
    "filtered unique ⇒ execute" is module 5/6's adjudication, never a
    silent leg of this compiler (design §5.2 / §6.1).
    """
    real_enumerator = wc._offset_candidates

    def one_survivor(wall_id, anchor_pos_m, sources):
        # evidence degenerate to ONE enumerable offset: keep the real
        # enumerator's own first candidate verbatim (ids, preview, source
        # record all real) and drop its sibling
        return real_enumerator(wall_id, anchor_pos_m, sources)[:1]

    monkeypatch.setattr(wc, "_offset_candidates", one_survivor)

    art = _adapt_doc(_unpaired_face_doc([200]),
                     "single_face_one_survivor", "9f")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")

    # ⭐ the premise FIRST, measured on the product -- the target quantity
    # itself.  If this ever goes red the fixture has degenerated back into
    # a proxy (that is F-1's whole lesson), and the lock below it would be
    # measuring something else.
    opened = [i for i in comp.open_items
              if i.scope_entity_ids == (wall.wall_id,)]
    assert len(opened) == 1, (
        "the axis item vanished from open_items -- a silent auto-execute "
        "path closed it (F-1's mutation does exactly this)"
    )
    assert len(opened[0].candidates) == 1, (
        "fixture premise broke: candidate count != 1 -- one thickness "
        "value still enumerates both signs; this lock must measure the "
        "TARGET, not that proxy"
    )

    # THEN the invariant: filtered-unique does NOT converge.  No axis, no
    # thickness, no output basis, identity excluded, no auto action, and
    # the open item is a real state boundary.
    item = _assert_axis_item_open_not_silent(comp, wall)
    assert len(item.candidates) == 1
    sole = item.candidates[0]
    assert sole.symbolic_operation in ("OFFSET_POSITIVE", "OFFSET_NEGATIVE")
    assert sole.thickness_source is not None  # one REAL candidate, not a stub
    assert comp.completion == "degraded"

    # and the door is not welded shut: an explicit decision on that sole
    # candidate is still the one legal closer
    decided = wc.compile_wall_ir(
        art, profile="strict",
        decisions=(wc.FixedDecisionV1(
            item_id=item.item_id, candidate_id=sole.candidate_id
        ),),
    )
    wall_decided = next(
        w for w in decided.walls if w.wall_id == wall.wall_id
    )
    assert wall_decided.resolved_centerline is not None
    assert wall_decided.resolved_centerline.constant_pos_m == \
        sole.preview_constant_pos_m
    assert wall_decided.output_basis == "wall_axis"
    assert wall_decided.resolved_thickness_m == sole.thickness_source.value_m
    assert not any(i.item_id == item.item_id for i in decided.open_items)


# =========================================================================== #
# Rework 2 (2026-09-01, N-1): why_not_auto_resolved matches its OWN item
# =========================================================================== #
def test_single_face_why_not_names_enumerable_offsets_when_candidates_exist():
    """N-1 branch 1: with candidates enumerated, the item's explanation must
    say offsets ARE enumerable and must NOT claim an empty candidate set --
    the cross-review flipped the two branches and every test stayed green,
    i.e. the decision packet could carry a story opposite to its own facts."""
    art = _adapt_doc(_unpaired_face_doc([200]), "why_with_cands", "9f")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)

    assert len(item.candidates) > 0  # premise: THIS is the with-candidates branch
    assert "enumerable" in item.why_not_auto_resolved
    assert "candidate set is empty" not in item.why_not_auto_resolved


def test_single_face_why_not_names_the_empty_set_when_no_scale_exists():
    """N-1 branch 2: the empty-candidate item's explanation must claim the
    empty set and name the legal exits (decision / re-perception /
    degraded profile) -- the same flipped-branch mutation hands this item
    the enumerable-offsets story, which its own candidate set contradicts."""
    art = _adapt_doc(_unpaired_face_doc(None), "why_no_scale", "9f")
    comp = wc.compile_wall_ir(art, profile="strict")
    wall = next(w for w in comp.walls if w.claim_kind == "single_face")
    item = _assert_axis_item_open_not_silent(comp, wall)

    assert item.candidates == ()  # premise: THIS is the empty branch
    assert "candidate set is empty" in item.why_not_auto_resolved
    assert "re-perception" in item.why_not_auto_resolved
