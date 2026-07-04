"""Map gt scorer results into machine-readable judge evidence.

These suggestions are evidence for gate②, not an automatic verdict.  They are
kept out of ``StageVerdict`` on purpose: the judge still owns the authoritative
checklist decision.
"""

from __future__ import annotations

from collections.abc import Mapping

from .reading_score import (
    DEFAULT_WALL_TOL_M,
    DEFAULT_WIN_CENTRE_TOL_M,
    FloorScore,
)
from .elevation_score import (
    DEFAULT_ELEVATION_ALONG_TOL_M,
    DEFAULT_OVERLAP_ACCEPT,
    DEFAULT_OVERLAP_COMPLETE,
    DEFAULT_HEAD_TOL_M,
    DEFAULT_SILL_TOL_M,
    DEFAULT_WIDTH_TOL_M,
    ElevationScoreResult,
)

EXTRA_MINOR_MAX = 2
WINDOW_MINOR_RATIO = 0.80


def reading_score_criteria(
    scores: Mapping[str, FloorScore],
    *,
    wall_tol_m: float = DEFAULT_WALL_TOL_M,
    window_centre_tol_m: float = DEFAULT_WIN_CENTRE_TOL_M,
    elevation=None,
    elevation_along_tol_m: float = DEFAULT_ELEVATION_ALONG_TOL_M,
    sill_tol_m: float = DEFAULT_SILL_TOL_M,
    head_tol_m: float = DEFAULT_HEAD_TOL_M,
    width_tol_m: float = DEFAULT_WIDTH_TOL_M,
    overlap_accept: float = DEFAULT_OVERLAP_ACCEPT,
    overlap_complete: float = DEFAULT_OVERLAP_COMPLETE,
    extra_evidence: list[dict] | None = None,
) -> list[dict]:
    """Return suggested criterion evidence derived from FloorScore objects."""
    total_wall_hits = total_walls = total_windows_hit = total_windows = 0
    total_boundary_hits = total_boundary = 0
    extra_walls = extra_windows = 0
    no_data_boundary_floors = 0
    max_wall_offset = 0.0
    floors: list[dict] = []

    for key, score in scores.items():
        wh, wt = score.wall_hits()
        winh, wint = score.window_hits()
        bh, bt = score.boundary_hits()
        ew = len(score.extra_vwalls) + len(score.extra_hwalls)
        exwin = sum(len(v) for v in score.extra_windows.values())
        wall_status_counts = _status_counts(score.vwalls + score.hwalls + score.extra_vwalls + score.extra_hwalls)
        window_status_counts = _status_counts(
            [m for matches in score.windows.values() for m in matches]
            + [m for matches in score.extra_windows.values() for m in matches]
        )
        total_wall_hits += wh
        total_walls += wt
        total_windows_hit += winh
        total_windows += wint
        total_boundary_hits += bh
        total_boundary += bt
        if score.boundary is None:
            no_data_boundary_floors += 1
        extra_walls += ew
        extra_windows += exwin
        max_wall_offset = max(max_wall_offset, score.max_wall_offset())
        floors.append(
            {
                "key": key,
                "floor": score.floor,
                "wall_hits": wh,
                "wall_total": wt,
                "boundary_hits": bh,
                "boundary_total": bt,
                "boundary_no_data": score.boundary is None,
                "window_hits": winh,
                "window_total": wint,
                "extra_walls": ew,
                "extra_windows": exwin,
                "wall_status_counts": wall_status_counts,
                "window_status_counts": window_status_counts,
                "max_wall_offset_m": score.max_wall_offset(),
            }
        )

    missed_walls = max(0, total_walls - total_wall_hits)
    missed_boundary = max(0, total_boundary - total_boundary_hits)
    missed_windows = max(0, total_windows - total_windows_hit)
    window_ratio = 1.0 if total_windows == 0 else total_windows_hit / total_windows

    if missed_walls:
        wall_status = "severe"
    elif extra_walls:
        wall_status = "minor" if extra_walls <= EXTRA_MINOR_MAX else "severe"
    else:
        wall_status = "pass"

    boundary_status = "severe" if missed_boundary else "pass"

    if total_windows == 0 or missed_windows == 0:
        window_status = "pass"
    elif window_ratio >= WINDOW_MINOR_RATIO:
        window_status = "minor"
    else:
        window_status = "severe"

    oversplit_count = extra_walls
    if oversplit_count == 0:
        oversplit_status = "pass"
    elif oversplit_count <= EXTRA_MINOR_MAX:
        oversplit_status = "minor"
    else:
        oversplit_status = "severe"

    criteria = [
        {
            "criterion": "walls_complete",
            "suggested_status": wall_status,
            "evidence": (
                f"wall_hits={total_wall_hits}/{total_walls}; "
                f"missed={missed_walls}; extra={extra_walls}; "
                f"max_offset_m={round(max_wall_offset, 3)}; "
                f"wall_tol_m={wall_tol_m}"
            ),
            "floors": floors,
        },
        {
            "criterion": "windows_placed",
            "suggested_status": window_status,
            "evidence": (
                f"window_hits={total_windows_hit}/{total_windows}; "
                f"missed={missed_windows}; extra={extra_windows}; "
                f"hit_ratio={round(window_ratio, 3)}; "
                f"centre_tol_m={window_centre_tol_m}"
            ),
            "floors": floors,
        },
        {
            "criterion": "boundary_complete",
            "suggested_status": boundary_status,
            "evidence": (
                f"boundary_hits={total_boundary_hits}/{total_boundary}; "
                f"missed={missed_boundary}; "
                f"no_data_floors={no_data_boundary_floors}; "
                f"wall_tol_m={wall_tol_m}"
            ),
            "floors": floors,
        },
        {
            "criterion": "no_oversplit",
            "suggested_status": oversplit_status,
            "evidence": (
                f"extra_vwalls+extra_hwalls={oversplit_count}; "
                f"minor_threshold={EXTRA_MINOR_MAX}"
            ),
            "floors": floors,
        },
    ]
    if elevation is not None:
        criteria.append(
            elevation_windows_placed_criterion(
                elevation,
                elevation_along_tol_m=elevation_along_tol_m,
                sill_tol_m=sill_tol_m,
                head_tol_m=head_tol_m,
                width_tol_m=width_tol_m,
                overlap_accept=overlap_accept,
                overlap_complete=overlap_complete,
            )
        )
    if extra_evidence:
        criteria.append(
            {
                "criterion": "score_evidence_completeness",
                "suggested_status": "severe",
                "evidence": "some correction floors/windows could not be matched to gt floors",
                "details": extra_evidence,
            }
        )
    return criteria


def elevation_windows_placed_criterion(
    elevation,
    *,
    elevation_along_tol_m: float = DEFAULT_ELEVATION_ALONG_TOL_M,
    sill_tol_m: float = DEFAULT_SILL_TOL_M,
    head_tol_m: float = DEFAULT_HEAD_TOL_M,
    width_tol_m: float = DEFAULT_WIDTH_TOL_M,
    overlap_accept: float = DEFAULT_OVERLAP_ACCEPT,
    overlap_complete: float = DEFAULT_OVERLAP_COMPLETE,
) -> dict:
    """Advisory status from elevation section only.

    Misses, z-drifts, extras, and no-data facade/floor cells all count against
    accurate elevation placement.  This remains score evidence only and is never
    a ``StageVerdict`` field.
    """

    if isinstance(elevation, ElevationScoreResult):
        summary = elevation.summary()
        floors = []
        for facade, by_floor in elevation.scores.items():
            for floor, score in by_floor.items():
                placed, gt_total = score.placed_hits()
                matched, _ = score.matched_hits()
                complete = sum(1 for m in score.matches if m.status == "complete")
                within = sum(1 for m in score.matches if m.status == "within_tol")
                floors.append(
                    {
                        "facade": facade,
                        "floor": floor,
                        "orientation": score.orientation,
                        "no_data": score.no_data,
                        "gt_count": score.gt_count,
                        "read_count": score.read_count,
                        "matched_total": matched,
                        "placed_hit_total": placed,
                        "complete_total": complete,
                        "within_tol_total": within,
                        "miss_total": sum(1 for m in score.matches if m.status == "miss"),
                        "extra_total": len(score.extras),
                    }
                )
    else:
        summary = dict(elevation.get("summary", {})) if isinstance(elevation, Mapping) else {}
        floors = []
        if isinstance(elevation, Mapping):
            for facade, facade_data in (elevation.get("facades") or {}).items():
                for floor, score in (facade_data.get("floors") or {}).items():
                    matches = score.get("matches") or []
                    floors.append(
                        {
                            "facade": facade,
                            "floor": floor,
                            "orientation": score.get("orientation"),
                            "no_data": bool(score.get("no_data")),
                            "gt_count": int(score.get("gt_count", 0)),
                            "read_count": int(score.get("read_count", 0)),
                            "matched_total": int(score.get("matched_total", 0)),
                            "placed_hit_total": int(score.get("placed_hit_total", 0)),
                            "complete_total": int(score.get("complete_total", 0)),
                            "within_tol_total": int(score.get("within_tol_total", 0)),
                            "miss_total": sum(1 for m in matches if m.get("status") == "miss"),
                            "extra_total": len(score.get("extras") or []),
                        }
                    )

    gt_total = int(summary.get("gt_total", 0))
    complete = int(summary.get("complete_total", summary.get("placed_hit_total", 0)))
    within = int(summary.get("within_tol_total", 0))
    placed = complete + within
    misses = int(summary.get("miss_total", 0))
    extras = int(summary.get("extra_total", 0))
    no_data = int(summary.get("no_data_floor_facades", 0))
    failures = max(0, gt_total - placed) + extras + no_data
    ratio = 1.0 if gt_total == 0 else placed / gt_total

    if failures == 0:
        status = "pass"
    elif ratio >= WINDOW_MINOR_RATIO and no_data == 0:
        status = "minor"
    else:
        status = "severe"

    return {
        "criterion": "elevation_windows_placed",
        "suggested_status": status,
        "evidence": (
            f"elevation_placed={placed}/{gt_total}; "
            f"complete={complete}; within_tol={within}; missed={misses}; extra={extras}; "
            f"no_data_floor_facades={no_data}; hit_ratio={round(ratio, 3)}; "
            f"along_tol_m={elevation_along_tol_m}; sill_tol_m={sill_tol_m}; "
            f"head_tol_m={head_tol_m}; width_tol_m={width_tol_m}; "
            f"overlap_accept={overlap_accept}; overlap_complete={overlap_complete}"
        ),
        "floors": floors,
    }


def _status_counts(records: list[object]) -> dict[str, int]:
    out = {"complete": 0, "within_tol": 0, "miss": 0, "extra": 0}
    for record in records:
        status = getattr(record, "status", None)
        if status in out:
            out[status] += 1
    return out
