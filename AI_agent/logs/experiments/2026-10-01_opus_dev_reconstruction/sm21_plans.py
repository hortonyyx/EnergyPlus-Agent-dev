"""Developer's sm21 floor declarations: positions from the drawings' dimension chains.

Calibration anchors are the measured outer faces of the gray exterior walls (pixel
profiles in this run); every wall and opening is then placed at its labelled
dimension value and converted to original pixels with the same anchors, so the
compiled metres equal the dimensions instead of inheriting ink-measurement noise.
Interior door jambs are the measured wall-line gaps (0.9 m, 300 mm off the divider
face), snapped to 10 mm. Heights were read per facade before drafting.
"""
import json
from pathlib import Path

RUN = Path(__file__).resolve().parents[1] / "2026-10-01_opus_dev_sm21"


class Frame:
    def __init__(self, x0, x15, y0, y8):
        self.x0, self.y0 = x0, y0
        self.sx, self.sy = (x15 - x0) / 15.0, (y8 - y0) / 8.0
        self.x_anchors, self.y_anchors = [[x0, 0], [x15, 15]], [[y0, 0], [y8, 8]]

    def p(self, x, y):
        return [round(self.x0 + x * self.sx, 3), round(self.y0 + y * self.sy, 3)]


def opening(frame, oid, kind, a, b, z, refs):
    return {"id": oid, "kind": kind, "p1": frame.p(*a), "p2": frame.p(*b), "z": z, "source_refs": refs}


def wall(frame, wid, a, b, refs):
    return {"id": wid, "points": [frame.p(*a), frame.p(*b)], "source_refs": refs}


def floor1():
    f = Frame(426, 1815, 1087, 347)
    corridor_n, corridor_s = 5.0, 3.0
    chain_n = "1f_view.png north chain 1240/2400/1300/120/1240/2400/1240/120/1300/2400/1240 = 15000"
    chain_s = "1f_view.png south chain 540/900/2000/1200/360/1300/2400/1300/1360/2400/1240 = 15000"
    chain_w = "1f_view.png west chain 3000/250/1500/250/3000 = 8000"
    chain_e = "1f_view.png east chain 2940/120/340/1200/340/120/2940 = 8000"
    gaps = "1f_view.png corridor wall-line gaps measured by view_pixel_profile (profile_006/007), 0.9 m wide, 300 mm off divider faces"
    walls = [
        wall(f, "P_cor_N", (0, corridor_n), (15, corridor_n), [chain_w, chain_e + ": 120 mm corridor wall centred at y=5.0"]),
        wall(f, "P_cor_S", (0, corridor_s), (15, corridor_s), [chain_w, chain_e + ": 120 mm corridor wall centred at y=3.0"]),
        wall(f, "P_N5", (5, corridor_n), (5, 8), [chain_n + ": 120 mm divider centred at x=5.0"]),
        wall(f, "P_N10", (10, corridor_n), (10, 8), [chain_n + ": 120 mm divider centred at x=10.0"]),
        wall(f, "P_S5", (5, 0), (5, corridor_s), [chain_s + ": divider at x=5.0 (4640+360)"]),
        wall(f, "P_S10", (10, 0), (10, corridor_s), [chain_s + ": divider at x=10.0 (8700+1300)"]),
    ]
    north = "North_view.png 1F chain 1000/1600/400 from the ground: z 1.0-2.6"
    south_big = "South_view.png 1F right chain 1000/1600/400: z 1.0-2.6"
    south_small = "South_view.png 1F left chain 1500/600/900 from the ground: small window z 1.5-2.1"
    openings = [
        opening(f, "W_N1", "window", (1.24, 8), (3.64, 8), [1.0, 2.6], [chain_n, north]),
        opening(f, "W_N2", "window", (6.30, 8), (8.70, 8), [1.0, 2.6], [chain_n, north]),
        opening(f, "W_N3", "window", (11.36, 8), (13.76, 8), [1.0, 2.6], [chain_n, north]),
        opening(f, "D_S", "door", (0.54, 0), (1.44, 0), [0.0, 2.1],
                [chain_s, "South_view.png door head level with the small window head: 1500+600 = 2100"]),
        opening(f, "W_S1", "window", (3.44, 0), (4.64, 0), [1.5, 2.1], [chain_s, south_small]),
        opening(f, "W_S2", "window", (6.30, 0), (8.70, 0), [1.0, 2.6], [chain_s, south_big]),
        opening(f, "W_S3", "window", (11.36, 0), (13.76, 0), [1.0, 2.6], [chain_s, south_big]),
        opening(f, "W_E", "window", (15, 3.40), (15, 4.60), [1.0, 2.8],
                [chain_e, "East_view.png 1F chain 1000/1800/200: z 1.0-2.8"]),
        opening(f, "D_W", "door", (0, 3.25), (0, 4.75), [0.0, 2.1],
                [chain_w, "West_view.png double door: no height dimension; drawn head at about 2.1 m by the 3000 storey scale"]),
    ]
    for row, y in (("N", corridor_n), ("S", corridor_s)):
        for label, (a, b) in zip(("1", "2", "3"), ((3.74, 4.64), (5.36, 6.26), (10.36, 11.26))):
            openings.append(opening(f, f"D_{row}{label}", "door", (a, y), (b, y), [0.0, 2.1],
                                    [gaps, "height assumed 2.1 m: no drawing dimensions interior doors"]))
    seeds = [{"id": sid, "point": f.p(*pt)} for sid, pt in (
        ("R_N1", (2.5, 6.5)), ("R_N2", (7.5, 6.5)), ("R_N3", (12.5, 6.5)), ("COR", (7.5, 4.0)),
        ("R_S1", (2.5, 1.5)), ("R_S2", (7.5, 1.5)), ("R_S3", (12.5, 1.5)))]
    return {"floor_id": "F1", "z_floor": 0, "ceiling_height": 3.0,
            "x_anchors": f.x_anchors, "y_anchors": f.y_anchors,
            "basis": ("Anchors: outer faces of the gray exterior walls measured with view_pixel_profile "
                      "(x 426/1815 px, profile_001; y 347/1087 px, profiles 003/002) matched to the 15000/8000 "
                      "overall dimensions whose extension lines reach those faces. Perimeter on outer faces; "
                      "120 mm dividers on their centre planes from the labelled chains; all positions are the "
                      "chain values mapped back to pixels. Storey 3000 from the elevations."),
            "footprint_pixels": [f.p(0, 0), f.p(15, 0), f.p(15, 8), f.p(0, 8)],
            "partitions": walls, "openings": openings, "space_seeds": seeds,
            "assumptions": ["Interior door heights 2.1 m: no drawing dimensions them.",
                            "West double-door head 2.1 m read from the drawn door against the 3000 storey line on West_view.png; not dimensioned.",
                            "Interior door jambs from measured wall gaps snapped to 10 mm."],
            "unresolved": []}


def floor2():
    f = Frame(428, 1813, 1072, 333)
    corridor_n, corridor_s = 5.0, 3.0
    chain_n = "2f_view.png north chain 1950/3600/1889/120/1891/3600/1950 = 15000"
    chain_s = "2f_view.png south chain 2190/1200/360/360/1200/2190 twice = 15000"
    chain_w = "2f_view.png west chain 3000/400/1200/400/3000 = 8000"
    chain_e = "2f_view.png east chain 2940/120/340/1200/340/120/2940 = 8000"
    gaps = "2f_view.png corridor wall-line gaps measured by view_pixel_profile (profile_015/016), 0.9 m wide, 300 mm off divider faces"
    walls = [
        wall(f, "P_cor_N", (0, corridor_n), (15, corridor_n), [chain_w, chain_e + ": corridor wall centred at y=5.0"]),
        wall(f, "P_cor_S", (0, corridor_s), (15, corridor_s), [chain_w, chain_e + ": corridor wall centred at y=3.0"]),
        wall(f, "P_N7", (7.5, corridor_n), (7.5, 8), [chain_n + ": 120 mm divider centred at x=7.5"]),
        wall(f, "P_S3", (3.75, 0), (3.75, corridor_s), [chain_s + ": divider at x=3.75"]),
        wall(f, "P_S7", (7.5, 0), (7.5, corridor_s), [chain_s + ": divider at x=7.5"]),
        wall(f, "P_S11", (11.25, 0), (11.25, corridor_s), [chain_s + ": divider at x=11.25"]),
    ]
    upper = "{0}_view.png 2F chain 1000/1800/800 from the 3000 floor line: z 4.0-5.8"
    openings = [
        opening(f, "W_N1", "window", (1.95, 8), (5.55, 8), [4.0, 5.8], [chain_n, upper.format("North")]),
        opening(f, "W_N2", "window", (9.45, 8), (13.05, 8), [4.0, 5.8], [chain_n, upper.format("North")]),
    ]
    for label, (a, b) in zip("1234", ((2.19, 3.39), (4.11, 5.31), (9.69, 10.89), (11.61, 12.81))):
        openings.append(opening(f, f"W_S{label}", "window", (a, 0), (b, 0), [4.0, 5.8], [chain_s, upper.format("South")]))
    openings += [
        opening(f, "W_E", "window", (15, 3.40), (15, 4.60), [4.0, 5.8], [chain_e, upper.format("East")]),
        opening(f, "W_W", "window", (0, 3.40), (0, 4.60), [4.0, 5.8], [chain_w, upper.format("West")]),
    ]
    doors = [("D_N1", (6.24, 7.14), corridor_n), ("D_N2", (7.86, 8.76), corridor_n),
             ("D_S1", (2.49, 3.39), corridor_s), ("D_S2", (4.11, 5.01), corridor_s),
             ("D_S3", (9.99, 10.89), corridor_s), ("D_S4", (11.61, 12.51), corridor_s)]
    for did, (a, b), y in doors:
        openings.append(opening(f, did, "door", (a, y), (b, y), [3.0, 5.1],
                                [gaps, "height assumed 2.1 m above the 3.0 m floor: no drawing dimensions interior doors"]))
    seeds = [{"id": sid, "point": f.p(*pt)} for sid, pt in (
        ("R_N1", (3.75, 6.5)), ("R_N2", (11.25, 6.5)), ("COR", (7.5, 4.0)),
        ("R_S1", (1.9, 1.5)), ("R_S2", (5.6, 1.5)), ("R_S3", (9.4, 1.5)), ("R_S4", (13.1, 1.5)))]
    return {"floor_id": "F2", "z_floor": 3.0, "ceiling_height": 3.6,
            "x_anchors": f.x_anchors, "y_anchors": f.y_anchors,
            "basis": ("Anchors: outer faces of the gray exterior walls measured with view_pixel_profile "
                      "(x 428/1813 px, profile_010; y 333/1072 px, profiles 011/012) matched to 15000/8000. "
                      "Same origin and axes as F1. Dividers on centre planes from the labelled chains; "
                      "positions are chain values mapped to pixels. Floor at 3.0 m, storey 3600 from the elevations; "
                      "opening z are absolute."),
            "footprint_pixels": [f.p(0, 0), f.p(15, 0), f.p(15, 8), f.p(0, 8)],
            "partitions": walls, "openings": openings, "space_seeds": seeds,
            "assumptions": ["Interior door heights 2.1 m above floor: no drawing dimensions them.",
                            "Interior door jambs from measured wall gaps snapped to 10 mm."],
            "unresolved": []}


if __name__ == "__main__":
    out = RUN / "dev_inputs"
    out.mkdir(exist_ok=True)
    for name, plan in (("plan_f1.json", floor1()), ("plan_f2.json", floor2())):
        (out / name).write_text(json.dumps(plan, ensure_ascii=False))
        print(name, len(plan["partitions"]), "dividers", len(plan["openings"]), "openings", len(plan["space_seeds"]), "seeds")
