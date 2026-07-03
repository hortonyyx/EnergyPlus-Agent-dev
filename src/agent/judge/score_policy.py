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

EXTRA_MINOR_MAX = 2
WINDOW_MINOR_RATIO = 0.80


def reading_score_criteria(
    scores: Mapping[str, FloorScore],
    *,
    wall_tol_m: float = DEFAULT_WALL_TOL_M,
    window_centre_tol_m: float = DEFAULT_WIN_CENTRE_TOL_M,
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
