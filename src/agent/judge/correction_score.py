"""Correction-stage gt scorer.

Judge-side adapter for accepted ``CorrectedGeometry`` attempt outputs.  It
extracts the same wall/window primitives used by ``reading_score`` and reuses
the shared gt derivation + matchers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from src.agent.correction import deterministic as deterministic_module
from src.agent.correction.cell_geometry import cell_bbox, cell_polygon
from src.agent.correction.schema import CorrectedGeometry

from .reading_score import (
    DEFAULT_COMPLETE_EPS_M,
    DEFAULT_EXTENT_TOL_M,
    DEFAULT_POSITION_TOL_M,
    DEFAULT_WALL_TOL_M,
    DEFAULT_WIN_CENTRE_TOL_M,
    FloorScore,
    WallSegment,
    _dedupe,
    _dedupe_segments,
    _match_lines,
    _match_wall_segments,
    _match_window_segments,
    derive_gt_walls,
    derive_gt_wall_segments,
    derive_gt_windows,
    match_boundary,
)
from .elevation_score import (
    DEFAULT_ELEVATION_ALONG_TOL_M,
    DEFAULT_FLOOR_LINE_TOL_M,
    DEFAULT_OVERLAP_ACCEPT,
    DEFAULT_OVERLAP_COMPLETE,
    DEFAULT_HEAD_TOL_M,
    DEFAULT_SILL_TOL_M,
    DEFAULT_WIDTH_TOL_M,
    ElevationScoreResult,
    score_correction_elevation_windows,
)

_BOUNDARY_EPS_M = 0.30

# ---------------------------------------------------------------------------
# Single declared judge-side output convention — RUNTIME ENFORCED (F-22
# BLOCKER-1 fix, 2026-08-11 sol cross-review + user-ratified correction).
#
# This is the ONE place that states which physical frame a 1_correction
# product's coordinates are TRUSTED to be expressed in, for scoring against
# gt without a frame conversion —
#   * exterior envelope (footprint / floor.footprint) == the wall's OUTER
#     FACE.  This is the same face gt's `footprint.W_m`/`D_m` are measured
#     to (gt also separately records `wall_thickness_m`, purely as metadata
#     for that outer-skin dimension — not as a hint that judge-side geometry
#     needs converting).
#   * interior partition walls == the wall CENTRELINE.  This is the same
#     line gt's `zones[].rect_m` edges sit on (see `derive_gt_wall_segments`
#     in reading_score.py — an interior gt wall's declared extent already
#     runs edge-to-edge of the outer footprint, i.e. touches the outer skin
#     at its ends, not an inset centerline point).
#
# Before 2026-08-09 (F-17) a 1_correction product's exterior envelope was
# expressed at the wall CENTRELINE, so this scorer used to convert it
# outward by half `wall_thickness_m` before comparing to gt (see git history
# of `_boundary_centerline_to_outer` / `_expand_boundary_span`, removed
# earlier in F-22). F-17 fixed the deterministic core's envelope transform
# so a schema-v3 (`orthogonal_polygon`) product's own footprint is now
# already expressed at the outer face — i.e. that ONE profile already
# matches this declared convention with no transform needed.
#
# ⛔ NARROWED SCOPE (sol BLOCKER-1, 2026-08-11): the first cut of this fix
# treated EVERY schema version as already-outer-skin unconditionally. Real
# measurement on this repo's own historical runs proved that false: schema
# v1/v2 (`rectangular`, which is the CLI's DEFAULT capability_profile) has
# NEVER been verified to share this frame, and real v1/v2 artifacts on disk
# sit at inconsistent, unregistered offsets (measured examples: exactly
# [0,0] some runs, [-0.1,-0.1] others, [-0.22,-0.23] on a third — no fixed
# relationship to gt's outer skin at all). Directly comparing those against
# gt "because there's only one convention now" reproduced a NEW variant of
# the same double-expansion-era bug (an asymmetric miss on 2 of 4 boundary
# sides, and dropped interior-wall hits, purely from betting on an unproven
# frame) — see `AI_agent/logs/reviews/verdict/2026-08-11_f22_f9s0s1_crossreview_sol.md`
# BLOCKER-1 for the reproduction. The user-ratified correction is: trust
# schema v3 (`orthogonal_polygon`) ONLY; everything else is explicitly
# rejected (not guessed) — see `_is_trusted_output_convention` below, which
# every extraction site calls and which every caller must treat as
# authoritative. This is NOT a second conversion branch (the user's "single
# output convention, no switch" instruction from the original F-22 dispatch
# still holds) — untrusted inputs get NO conversion of any kind, they get
# refused.
#
# ⛔⛔ STILL NARROWER (sol re-review 2026-08-12, BLOCKER-1 remained OPEN after
# the narrowing above): `schema_version == "3"` alone is NOT proof of
# `outer_skin_exterior_centerline_interior` either. A bug fix to the core's
# transform logic (F-17, 2026-08-09) does not bump `schema_version` — by
# design, this project's own convention is "fixing a bug never changes the
# version number" — so the SAME `schema_version == "3"` spans real,
# byte-identical-looking runs both BEFORE and AFTER that fix
# (`run_2026-08-09_f17_e2e_verify`, pre-fix, footprint `[0.12,14.88]`, vs.
# `run_2026-08-11_continuous_e2e`, post-fix, footprint `[0,15]` — same
# `capability_profile`, same declared config). Trusting on schema alone
# scored the pre-fix run five-for-five `pass`, 0.12 m off on every side, with
# zero refusal evidence. The fix is a SEPARATE, unconditional identity the
# deterministic core itself stamps on every v3 completion regardless of
# whether anything changed (`DeterministicCoreStampV1`,
# `src/agent/correction/schema.py`; written by
# `deterministic.apply_deterministic_core`, see that function's v3 branch) —
# `schema_version` states WHAT SHAPE a product claims to be; the stamp states
# WHICH REVISION OF THE CORE actually produced it. Both are now required.
#
# `CORRECTION_OUTPUT_CONVENTION` is the ONE declaration of the identity
# currently trusted; `_is_trusted_output_convention()` is the ONE runtime
# read of it (now joined by `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION`
# for the post-transform half of that identity — referenced via the module,
# not `from ... import`, so a test that mutates
# `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION` is read live, the
# same "single declared source, no drift" discipline `CORRECTION_OUTPUT_CONVENTION`
# already uses). Self-test (required by sol, and locked by
# `tests/test_judge_batch_b.py::test_output_convention_declaration_mutation_changes_scoring_behavior`):
# mutate this constant's VALUE and rerun scoring on a real, otherwise-valid
# schema-v3 product — the result MUST change (boundary/wall-extent scoring
# must stop trusting it), proving the declaration is load-bearing and not
# decorative. The same self-test discipline now also applies to the stamp
# version (`tests/test_f22_blocker1_core_stamp.py`).
#
# This constant is the seam for a future second convention (the deferred
# "标注/墙厚/出模" work item): a second named identity would be added, and
# `_is_trusted_output_convention` — the only reader — is the only place that
# would need to grow a branch. Nothing else in this module may assume a
# frame on its own.
_TRUSTED_SCHEMA_V3_IDENTITY = "outer_skin_exterior_centerline_interior"
CORRECTION_OUTPUT_CONVENTION = _TRUSTED_SCHEMA_V3_IDENTITY


def _is_trusted_output_convention(geom: CorrectedGeometry) -> bool:
    """Runtime identity check — the ONLY gate that may treat a product's
    coordinates as directly comparable to gt without a frame conversion.

    Three independent facts must ALL hold, none a proxy for another:

    1. `schema_version == "3"` — the wire shape claims `orthogonal_polygon`.
    2. `CORRECTION_OUTPUT_CONVENTION == _TRUSTED_SCHEMA_V3_IDENTITY` — this
       module's own declared identity has not been tampered with.
    3. The product's `deterministic_core_stamp.version` (F-22 BLOCKER-1,
       2026-08-12) exactly equals `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION`
       — the deterministic core (whose only verified-safe revision is the
       CURRENT one; see that constant's docstring) actually ran to
       completion on THIS artifact. Only `apply_deterministic_core` ever
       writes this field, unconditionally, on every v3 completion — whether
       or not it found anything to move (F-22 BLOCKER-1 §3: a *conditional*
       "did an envelope transform record get written" signal cannot tell
       "the core never ran" apart from "the core ran and had nothing to
       do", because a drawing already annotated at the outer skin also
       leaves no transform record).

    (1) alone used to be treated as sufficient — that was BLOCKER-1's bug:
    the SAME `schema_version == "3"` spans a real run from before the F-17
    transform fix and a real run from after it, with no version bump between
    them, so schema alone cannot distinguish a pre-fix product from a
    post-fix one. (3) is what actually distinguishes them: a pre-fix run
    predates this stamp's existence entirely, so its `deterministic_core_stamp`
    is unconditionally `None` — missing, not merely mismatched — and is
    refused exactly like an unrecognized version would be, with no
    historical whitelist (user-ratified 2026-08-12: this applies even to
    runs produced AFTER the F-17 fix landed but before this stamp did, e.g.
    `run_2026-08-11_continuous_e2e` — they need a rerun to regain a score;
    that is the intended enforcement, not a gap).

    Returns False for everything else, INCLUDING a mutated/unrecognized
    `CORRECTION_OUTPUT_CONVENTION` value or stamp version — there is no
    fallback interpretation; untrusted means untrusted.
    """
    stamp = getattr(geom, "deterministic_core_stamp", None)
    stamp_version = getattr(stamp, "version", None)
    return (
        getattr(geom, "schema_version", None) == "3"
        and CORRECTION_OUTPUT_CONVENTION == _TRUSTED_SCHEMA_V3_IDENTITY
        and stamp_version == deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION
    )


@dataclass
class CorrectionScoreResult:
    scores: dict[str, FloorScore]
    evidence: list[dict] = field(default_factory=list)
    floor_map: dict[str, str] = field(default_factory=dict)
    elevation: ElevationScoreResult | None = None
    # F-22 BLOCKER-1: explicit schema/profile provenance for the boundary /
    # interior-wall-extent convention this scoring run assumed — written
    # unconditionally (both trusted and untrusted cases) so the sidecar
    # always states what was assumed, not just when it refuses. `identity`
    # is `CORRECTION_OUTPUT_CONVENTION` when trusted, else None.
    output_convention: dict = field(default_factory=dict)


def _floor_number(name: str) -> int | None:
    m = re.search(r"(?<!\d)(\d+)(?!\d)", name or "")
    return int(m.group(1)) if m else None


def _map_floors(geom: CorrectedGeometry, gt: dict) -> tuple[dict[str, str], list[dict]]:
    gt_floors = list(gt.get("floors", []))
    gt_by_name = {str(f.get("name")): f for f in gt_floors}
    used: set[str] = set()
    mapping: dict[str, str] = {}
    evidence: list[dict] = []

    # 1. exact name
    for fl in geom.floors:
        if fl.name in gt_by_name:
            mapping[fl.name] = fl.name
            used.add(fl.name)

    # 2. numeric floor ordinal: F1 / 1F / Floor 1 -> gt floor #1
    for fl in geom.floors:
        if fl.name in mapping:
            continue
        n = _floor_number(fl.name)
        if n is None:
            continue
        idx = n - 1
        if 0 <= idx < len(gt_floors):
            candidate = str(gt_floors[idx].get("name"))
            if candidate not in used:
                mapping[fl.name] = candidate
                used.add(candidate)

    # 3. z-floor first, then list order for any remaining unique slot.
    remaining_gt = [f for f in gt_floors if str(f.get("name")) not in used]
    for fl in sorted((f for f in geom.floors if f.name not in mapping), key=lambda f: f.z_floor):
        z_matches = [
            f for f in remaining_gt
            if f.get("z_floor") is not None and abs(float(f["z_floor"]) - float(fl.z_floor)) <= 0.45
        ]
        chosen = z_matches[0] if z_matches else (remaining_gt[0] if remaining_gt else None)
        if chosen is None:
            evidence.append(
                {
                    "type": "unmatched_floor",
                    "floor": fl.name,
                    "z_floor": fl.z_floor,
                    "reason": "no remaining gt floor",
                }
            )
            continue
        gt_name = str(chosen.get("name"))
        mapping[fl.name] = gt_name
        used.add(gt_name)
        remaining_gt = [f for f in remaining_gt if str(f.get("name")) != gt_name]

    for fl in geom.floors:
        if fl.name not in mapping:
            evidence.append(
                {
                    "type": "unmatched_floor",
                    "floor": fl.name,
                    "z_floor": fl.z_floor,
                    "reason": "could not map by exact name, ordinal, z_floor, or order",
                }
            )
    return mapping, evidence


def _extract_correction_wall_segments(
    floor,
    W: float,
    D: float,
    *,
    geom: CorrectedGeometry,
) -> tuple[list[WallSegment], list[WallSegment]]:
    """Interior wall extents, per CORRECTION_OUTPUT_CONVENTION (module docstring).

    Gated on `_is_trusted_output_convention(geom)` (F-22 BLOCKER-1): when
    trusted, a product's interior wall extents are read verbatim from its
    cell polygons — no centerline<->outer-skin conversion — because the
    product footprint is already at the outer face (post-F-17) and gt's own
    interior wall truth extents (`derive_gt_wall_segments`) already run
    edge-to-edge of the outer footprint. When NOT trusted, returns no
    segments at all rather than guess: comparing an unverified frame's wall
    extents directly against gt's outer-skin-anchored truth reproduces the
    same class of asymmetric-miss bug the boundary side had (sol BLOCKER-1
    reproduction: legacy real runs showed a registration offset become a
    lopsided N/E "miss" once compared without a trusted, uniform frame).
    """
    if not _is_trusted_output_convention(geom):
        return [], []
    vx: list[WallSegment] = []
    hy: list[WallSegment] = []
    for cell in floor.cells:
        try:
            coords = list(cell_polygon(cell).exterior.coords)
        except ValueError:
            continue
        for a, b in zip(coords, coords[1:]):
            x0, y0 = float(a[0]), float(a[1])
            x1, y1 = float(b[0]), float(b[1])
            if abs(x0 - x1) <= 1e-6:
                x = round(x0, 2)
                if _BOUNDARY_EPS_M < x0 < W - _BOUNDARY_EPS_M:
                    lo, hi = sorted((y0, y1))
                    vx.append(WallSegment("v", x, round(lo, 2), round(hi, 2)))
            elif abs(y0 - y1) <= 1e-6:
                y = round(y0, 2)
                if _BOUNDARY_EPS_M < y0 < D - _BOUNDARY_EPS_M:
                    lo, hi = sorted((x0, x1))
                    hy.append(WallSegment("h", y, round(lo, 2), round(hi, 2)))
    return _dedupe_segments(vx), _dedupe_segments(hy)


def _extract_correction_walls(
    floor, W: float, D: float, *, geom: CorrectedGeometry
) -> tuple[list[float], list[float]]:
    vx, hy = _extract_correction_wall_segments(floor, W, D, geom=geom)
    return [s.coord for s in vx], [s.coord for s in hy]


def _valid_pair(vals) -> tuple[float, float] | None:
    if vals is None or len(vals) != 2:
        return None
    try:
        a, b = float(vals[0]), float(vals[1])
    except (TypeError, ValueError):
        return None
    return min(a, b), max(a, b)


def _floor_cells_bbox(floor) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xs: list[float] = []
    ys: list[float] = []
    for cell in floor.cells:
        try:
            minx, miny, maxx, maxy = cell_bbox(cell)
        except ValueError:
            continue
        xs.extend([minx, maxx])
        ys.extend([miny, maxy])
    if not xs or not ys:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys))


def _fallback_footprint_from_raw_cells(data: dict) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xs: list[float] = []
    ys: list[float] = []
    for floor in data.get("floors") or []:
        for cell in floor.get("cells") or []:
            x = cell.get("x") or []
            y = cell.get("y") or []
            if len(x) == 2:
                xs.extend([float(x[0]), float(x[1])])
            if len(y) == 2:
                ys.extend([float(y[0]), float(y[1])])
    if not xs or not ys:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys))


def _normalise_raw_geom_for_scoring(data: dict) -> dict:
    fx = _valid_pair(data.get("footprint_x"))
    fy = _valid_pair(data.get("footprint_y"))
    if fx is not None and fy is not None:
        return data
    bbox = _fallback_footprint_from_raw_cells(data)
    if bbox is None:
        return data
    out = dict(data)
    if fx is None:
        out["footprint_x"] = [bbox[0][0], bbox[0][1]]
    if fy is None:
        out["footprint_y"] = [bbox[1][0], bbox[1][1]]
    return out


def _extract_correction_boundary(
    geom: CorrectedGeometry,
    floor,
) -> dict[str, float] | None:
    """Exterior envelope boundary, per CORRECTION_OUTPUT_CONVENTION (module docstring).

    Gated on `_is_trusted_output_convention(geom)` (F-22 BLOCKER-1). When
    trusted, read verbatim from the product's own footprint — no
    centerline<->outer-skin conversion — because the product footprint is
    already at the outer face (post-F-17) and gt's `footprint.W_m`/`D_m` are
    also outer-skin. When NOT trusted, returns None (the existing "no data"
    representation `FloorScore.boundary` already carries — see its
    docstring) rather than guess a conversion: `score_correction_geometry`
    additionally records an explicit, visible `unsupported_output_convention`
    evidence entry for the floor so this reads as an active refusal, not a
    silent pass (a None boundary contributes 0/0 to `boundary_hits()`, which
    on its own would look identical to "nothing to grade" — the evidence
    entry is what makes `score_evidence_completeness` surface as severe).
    """
    if not _is_trusted_output_convention(geom):
        return None
    from src.agent.correction.footprint import footprint_bbox
    try:
        fx, fy = footprint_bbox(geom, floor)
    except ValueError:
        bbox = _floor_cells_bbox(floor)
        if bbox is None:
            return None
        fx, fy = bbox
    return {"S": fy[0], "N": fy[1], "W": fx[0], "E": fx[1]}


def _gt_floor_for_label(label: str, gt: dict, floor_map: dict[str, str]) -> str | None:
    if label in floor_map:
        return floor_map[label]
    gt_floors = list(gt.get("floors", []))
    gt_names = {str(f.get("name")) for f in gt_floors}
    if label in gt_names:
        return label
    n = _floor_number(label)
    if n is not None and 0 <= n - 1 < len(gt_floors):
        return str(gt_floors[n - 1].get("name"))
    return None


def _extract_correction_windows(
    geom: CorrectedGeometry,
    gt_floor_name: str,
    gt: dict,
    floor_map: dict[str, str],
) -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {"N": [], "S": [], "E": [], "W": []}
    facade_code = {"North": "N", "South": "S", "East": "E", "West": "W"}
    for win in geom.windows:
        if _gt_floor_for_label(win.floor, gt, floor_map) != gt_floor_name:
            continue
        code = facade_code.get(win.facade)
        if not code or len(win.span) != 2:
            continue
        out[code].append((round(min(win.span), 2), round(max(win.span), 2)))
    return out


def score_correction_geometry(
    geom_data: CorrectedGeometry | dict,
    gt: dict,
    *,
    wall_tol: float = DEFAULT_WALL_TOL_M,
    win_tol: float = DEFAULT_WIN_CENTRE_TOL_M,
    position_tol: float | None = None,
    extent_tol: float = DEFAULT_EXTENT_TOL_M,
    complete_eps: float = DEFAULT_COMPLETE_EPS_M,
    elevation_along_tol_m: float = DEFAULT_ELEVATION_ALONG_TOL_M,
    sill_tol_m: float = DEFAULT_SILL_TOL_M,
    head_tol_m: float = DEFAULT_HEAD_TOL_M,
    width_tol_m: float = DEFAULT_WIDTH_TOL_M,
    overlap_accept: float = DEFAULT_OVERLAP_ACCEPT,
    overlap_complete: float = DEFAULT_OVERLAP_COMPLETE,
    floor_line_tol_m: float = DEFAULT_FLOOR_LINE_TOL_M,
) -> CorrectionScoreResult:
    from src.agent.correction.parse import ensure_corrected_geometry
    geom = ensure_corrected_geometry(
        geom_data if isinstance(geom_data, CorrectedGeometry)
        else _normalise_raw_geom_for_scoring(geom_data)
    )
    fp = gt["footprint"]
    W, D = float(fp["W_m"]), float(fp["D_m"])
    gt_floor_by_name = {str(f["name"]): f for f in gt.get("floors", [])}
    floor_map, evidence = _map_floors(geom, gt)
    scores: dict[str, FloorScore] = {}

    # F-22 BLOCKER-1: identity is a property of the whole product (schema
    # version), not per-floor, so compute the trust decision once and record
    # it unconditionally — this is the sidecar-visible provenance the
    # user-ratified fix requires (§3 point 3), independent of whether any
    # floor ends up flagged.
    trusted = _is_trusted_output_convention(geom)
    output_convention = {
        "schema_version": getattr(geom, "schema_version", None),
        "trusted": trusted,
        "identity": CORRECTION_OUTPUT_CONVENTION if trusted else None,
    }
    if not trusted:
        # F-22 BLOCKER-1 (2026-08-12): give the SPECIFIC reason, not a generic
        # one — `_is_trusted_output_convention` now checks three independent
        # facts (schema_version / CORRECTION_OUTPUT_CONVENTION / the core
        # stamp's version) and a message that only ever names "schema_version"
        # would misdiagnose the exact case this fix exists for: a real
        # schema-v3 product that fails ONLY because it predates the
        # unconditional stamp (`deterministic_core_stamp` is unconditionally
        # `None` on any artifact produced before this fix, or by a producer
        # that isn't `apply_deterministic_core`) — "schema_version does not
        # qualify" would be false for that product; its schema_version is
        # exactly "3".
        stamp = getattr(geom, "deterministic_core_stamp", None)
        stamp_version = getattr(stamp, "version", None)
        schema_ok = getattr(geom, "schema_version", None) == "3"
        if not schema_ok:
            core_stamp_reason = (
                f"schema_version {getattr(geom, 'schema_version', None)!r} is not "
                f"the trusted schema-v3/orthogonal_polygon shape"
            )
        elif stamp is None:
            core_stamp_reason = (
                "schema_version is v3, but deterministic_core_stamp is absent — "
                "this artifact predates the unconditional core stamp (F-22 "
                "BLOCKER-1) or was never produced by apply_deterministic_core; "
                "a v3 schema shape alone does not prove the current, verified "
                "deterministic core actually ran on it"
            )
        elif stamp_version != deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION:
            core_stamp_reason = (
                f"schema_version is v3 and a deterministic_core_stamp is "
                f"present, but its version {stamp_version!r} does not match "
                f"the currently trusted core version "
                f"{deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION!r} — "
                f"either a stale core revision or an unrecognized/forged value"
            )
        else:
            core_stamp_reason = "CORRECTION_OUTPUT_CONVENTION declaration mismatch"
        evidence.append(
            {
                "type": "unsupported_output_convention",
                "schema_version": getattr(geom, "schema_version", None),
                "reason": (
                    "boundary and interior-wall-extent scoring require a "
                    "trusted schema-v3/orthogonal_polygon post-transform "
                    "product identity (F-22 BLOCKER-1); this product does "
                    f"not qualify ({core_stamp_reason}), so boundary was left "
                    "unscored (no_data) and no interior wall segments were "
                    "extracted, rather than guessing a frame conversion"
                ),
            }
        )

    for fl in geom.floors:
        gt_name = floor_map.get(fl.name)
        if gt_name is None:
            continue
        gt_floor = gt_floor_by_name.get(gt_name)
        if gt_floor is None:
            evidence.append(
                {"type": "unmatched_floor", "floor": fl.name, "mapped_gt_floor": gt_name}
            )
            continue
        position_tol = wall_tol if position_tol is None else position_tol
        gvx, ghy = derive_gt_wall_segments(gt_floor["zones"], W, D)
        gwin = derive_gt_windows(gt, gt_name)
        rvx, rhy = _extract_correction_wall_segments(fl, W, D, geom=geom)
        rwin = _extract_correction_windows(geom, gt_name, gt, floor_map)
        rbnd = _extract_correction_boundary(geom, fl)

        sc = FloorScore(floor=gt_name)
        sc.vwalls, sc.extra_vwalls = _match_wall_segments(
            rvx,
            gvx,
            position_tol=position_tol,
            extent_tol=extent_tol,
            complete_eps=complete_eps,
        )
        sc.hwalls, sc.extra_hwalls = _match_wall_segments(
            rhy,
            ghy,
            position_tol=position_tol,
            extent_tol=extent_tol,
            complete_eps=complete_eps,
        )
        sc.boundary = match_boundary(rbnd, W, D, wall_tol, complete_eps=complete_eps)
        for facade in ("N", "S", "E", "W"):
            ms, extra = _match_window_segments(
                facade,
                rwin[facade],
                gwin[facade],
                extent_tol=extent_tol,
                complete_eps=complete_eps,
            )
            sc.windows[facade] = ms
            sc.extra_windows[facade] = extra
        scores[fl.name] = sc

    window_floor_names = {w.floor for w in geom.windows}
    known_floor_names = {f.name for f in geom.floors}
    for floor_name in sorted(window_floor_names - known_floor_names):
        if _gt_floor_for_label(floor_name, gt, floor_map) is not None:
            continue
        evidence.append(
            {
                "type": "unmatched_window_floor",
                "floor": floor_name,
                "reason": "window floor not present in CorrectedGeometry.floors",
            }
        )
    elevation_evidence: list[dict] = []
    elevation = score_correction_elevation_windows(
        geom,
        gt,
        floor_map=floor_map,
        evidence=elevation_evidence,
        elevation_along_tol_m=elevation_along_tol_m,
        sill_tol_m=sill_tol_m,
        head_tol_m=head_tol_m,
        width_tol_m=width_tol_m,
        overlap_accept=overlap_accept,
        overlap_complete=overlap_complete,
        floor_line_tol_m=floor_line_tol_m,
    )
    return CorrectionScoreResult(
        scores=scores,
        evidence=evidence,
        floor_map=floor_map,
        elevation=elevation,
        output_convention=output_convention,
    )
