"""B1 acceptance helper: the two-directional gt reconciliation (4b/⑥).

This is TEST-side tooling, ⛔ never production code: the gt iron rule says
``gt.json`` is readable only by the gate② judge and humans — the bridge and
gate① never import this.  The acceptance table (dispatch §五 4b) pins the
two-directional definition as NON-NEGOTIABLE:

    ① counts equal
    ② every gt zone is matched ONE-TO-ONE onto a face (nearest-centroid,
       each face at most one zone), centroid distance ≤ bound
    ③ every face is matched to a zone too — an ownerless face is RED

⛔⛔ The one-directional (gt→face) version was MEASURED to be fully GREEN
on the S3 injection (every zone matched some face, max d = 0.067 m): the
reconciliation the bridge's failures are handed to is only as good as ③.

The bound is DERIVED from the matched pairs' measured distribution
(dispatch §五 bottom): ``K × baseline all-matched max distance`` with
K = 5 — the number comes from the data, the program is fixed.  Area
difference is a readout only, ⛔ never a gate (midline < outer-skin is a
systematic one-sided bias, design §六之四).
"""

from __future__ import annotations

from dataclasses import dataclass, field

BOUND_MULTIPLIER = 5
"""K in ``bound = K × baseline max pair distance`` (v6 cross-review N-2:
K∈[2,10] judged identically on the measured attacks — red distances
≥ 2.06 m vs bounds 0.21–1.07 m — and 5 is what round 4 measured with)."""


def centroid(ring: list[list[float]] | tuple[tuple[float, float], ...]):
    """The GEOMETRIC centroid (area-weighted), not the vertex mean.

    Measured on real F1 the two differ by up to 1.28 m on the L-shaped
    99.93 m² zone — the vertex mean is not a centroid on non-convex rings,
    and a bound derived from it (5 × 1.28 = 6.4 m) would swallow every
    attack this reconciliation exists to catch (the S3-A2 attacks sit at
    1.08–2.31 m).  The cross-review's probe measured the clean baseline at
    max 0.107 m on the same data — that reading is only reproducible with
    the area-weighted centroid.
    """
    from shapely.geometry import Polygon

    c = Polygon(ring).centroid
    return c.x, c.y


def _ring_area(ring) -> float:
    n = len(ring)
    return abs(
        sum(
            ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
            for i in range(n)
        )
        / 2.0
    )


@dataclass
class ReconcilePair:
    zone_id: str
    face_index: int
    centroid_distance_m: float
    area_readout_m2: tuple[float, float]  # (face, zone) — readout, never gate


@dataclass
class ReconcileReport:
    n_faces: int
    n_zones: int
    pairs: list[ReconcilePair] = field(default_factory=list)
    counts_ok: bool = True
    unmatched_zones: list[str] = field(default_factory=list)
    ownerless_faces: list[int] = field(default_factory=list)

    @property
    def green(self) -> bool:
        return (
            self.counts_ok
            and not self.unmatched_zones
            and not self.ownerless_faces
        )

    @property
    def max_pair_distance(self) -> float:
        return max((p.centroid_distance_m for p in self.pairs), default=0.0)

    def failures(self) -> list[str]:
        out = []
        if not self.counts_ok:
            out.append(
                f"① counts: bridge {self.n_faces} faces vs gt {self.n_zones} zones"
            )
        if self.unmatched_zones:
            out.append(
                f"② zones unmatched (no face within bound): "
                f"{sorted(self.unmatched_zones)}"
            )
        if self.ownerless_faces:
            out.append(f"③ ownerless faces: {sorted(self.ownerless_faces)}")
        return out


def reconcile_faces_vs_zones(
    faces: list,
    zones: list[tuple[str, list[list[float]]]],
    *,
    bound_m: float,
) -> ReconcileReport:
    """The three-clause two-directional reconciliation (4b, non-negotiable).

    Matching is nearest-centroid one-to-one, greedy by ascending distance
    (each face at most one zone, each zone at most one face) — on the
    inputs this acceptance runs, any sane one-to-one rule judges
    identically (attack red distances sit far above the bound).
    """
    report = ReconcileReport(n_faces=len(faces), n_zones=len(zones))
    report.counts_ok = len(faces) == len(zones)
    pairs_all = []
    for zid, zring in zones:
        zc = centroid(zring)
        for fi, fring in enumerate(faces):
            fc = centroid(fring)
            d = ((zc[0] - fc[0]) ** 2 + (zc[1] - fc[1]) ** 2) ** 0.5
            pairs_all.append((d, zid, fi, _ring_area(fring), _ring_area(zring)))
    pairs_all.sort(key=lambda t: t[0])
    used_faces: set[int] = set()
    for d, zid, fi, fa, za in pairs_all:
        if zid in {p.zone_id for p in report.pairs} or fi in used_faces:
            continue
        if d > bound_m:
            continue  # too far even though unmatched: not a pair
        report.pairs.append(
            ReconcilePair(
                zone_id=zid,
                face_index=fi,
                centroid_distance_m=d,
                area_readout_m2=(fa, za),
            )
        )
        used_faces.add(fi)
    matched_zones = {p.zone_id for p in report.pairs}
    report.unmatched_zones = sorted(z for z, _ in zones if z not in matched_zones)
    report.ownerless_faces = sorted(
        set(range(len(faces))) - used_faces
    )
    return report


def bound_from_baseline(report: ReconcileReport) -> float:
    """``K × baseline all-matched max pair distance`` — the derived bound.

    The baseline report must itself be green (an unmatchable baseline has
    no distribution to derive from — that is a red acceptance, not a
    zero-width bound).
    """
    if not report.pairs or not report.green:
        raise ValueError(
            "baseline reconciliation is not green; refusing to derive a "
            f"bound from it: {report.failures()}"
        )
    return BOUND_MULTIPLIER * report.max_pair_distance


def load_gt_zones(gt_path, floor_id: str) -> list[tuple[str, list[list[float]]]]:
    import json

    data = json.loads(open(gt_path, encoding="utf-8").read())
    for floor in data["floors"]:
        if floor["id"] == floor_id:
            return [
                (z["id"], z["polygon"]["exterior"]["vertices"])
                for z in floor["zones"]
            ]
    raise KeyError(f"floor {floor_id} not in {gt_path}")
