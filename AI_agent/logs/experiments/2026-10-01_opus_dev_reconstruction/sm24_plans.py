"""Developer's sm24 floor declaration (one storey), positions from the dimension chains.

Anchors: measured outer faces of the gray exterior walls (x 249/611 px, y 152/878 px).
Dividers on the centre values of the labelled chains (west 4060/2940/4940/8060, east
4060/1940/5940/3120/4940, south 4180/1640/4180). The corridor-to-SE-room step at y=3.44 is
not dimensioned: measured double line centred at y px 753 (3.44 m = 4.94 - 1.50).
Heights: z measured from the elevations' ground line (the chains' datum); the floor is
200 above it (every exterior door chain starts 200/2400), so z_floor = 0.2.
"""
import json
from pathlib import Path

RUN = Path(__file__).resolve().parents[1] / "2026-10-01_opus_dev_sm24"
X0, X1, Y0, Y1 = 249, 611, 878, 152          # px of x=0, x=10, y=0, y=20
SX, SY = (X1 - X0) / 10.0, (Y1 - Y0) / 20.0


def p(x, y):
    return [round(X0 + x * SX, 3), round(Y0 + y * SY, 3)]


def wall(wid, a, b, refs):
    return {"id": wid, "points": [p(*a), p(*b)], "source_refs": refs}


def opening(oid, kind, a, b, z, refs):
    return {"id": oid, "kind": kind, "p1": p(*a), "p2": p(*b), "z": z, "source_refs": refs}


def plan():
    west = "1f_view.png west chains 540/1500/2380/1200/1740/1500/1220/1500/3080/4800/540 and 4060/2940/4940/8060"
    east = "1f_view.png east chains 540/1500/2380/1200/740/4800/1540/1600/5700 and 4060/1940/5940/3120/4940"
    north = "1f_view.png north chain 540/1600/2520/4800/540"
    south = "1f_view.png south chains 540/1500/2500/900/2520/1500/540 and 4180/1640/4180"
    gaps = "1f_view.png wall-line gaps by view_pixel_profile (profiles 005-007), snapped to 10 mm"
    walls = [
        wall("P_lobby", (0, 15.94), (10, 15.94), [west, east + ": lobby wall at 20-4.06"]),
        wall("P_corW", (4.18, 15.94), (4.18, 0), [south + ": corridor west wall at 4.18"]),
        wall("P_corE_up", (5.82, 15.94), (5.82, 8.06), [south + ": corridor east wall at 5.82", "open to the east hall below 8.06"]),
        wall("P_corE_low", (5.82, 4.94), (5.82, 3.44), [south, "SE room west wall above the step"]),
        wall("P_step", (4.18, 3.44), (5.82, 3.44), ["1f_view.png: undimensioned double line centred at y px 753 (3.44 m = 4940-1500)"]),
        wall("P_W13", (0, 13.0), (4.18, 13.0), [west + ": 20-4.06-2.94"]),
        wall("P_W806", (0, 8.06), (4.18, 8.06), [west + ": 8060 from the south"]),
        wall("P_E14", (5.82, 14.0), (10, 14.0), [east + ": 20-4.06-1.94"]),
        wall("P_E806", (5.82, 8.06), (10, 8.06), [east + ": 4.94+3.12"]),
        wall("P_E494", (5.82, 4.94), (10, 4.94), [east + ": 4940 from the south"]),
    ]
    n_el, s_el = "North_view.png", "South_view.png"
    e_el, w_el = "East_view.png", "West_view.png"
    big = "chain 1000/2400/1100 from the ground line: 1.0-3.4"
    small = "chain 1000/1800/1700 from the ground line: 1.0-2.8"
    door = "chain 200/2400/1900 from the ground line: 0.2-2.6"
    openings = [
        opening("D_N", "door", (0.54, 20), (2.14, 20), [0.2, 2.6], [north, f"{n_el} {door}"]),
        opening("W_N", "window", (4.66, 20), (9.46, 20), [1.0, 3.4], [north, f"{n_el} {big}"]),
        opening("W_S1", "window", (0.54, 0), (2.04, 0), [1.0, 2.8], [south, f"{s_el} {small}"]),
        opening("D_S", "door", (4.54, 0), (5.44, 0), [0.2, 2.6], [south, f"{s_el} {door}"]),
        opening("W_S2", "window", (7.96, 0), (9.46, 0), [1.0, 2.8], [south, f"{s_el} {small}"]),
        opening("W_E1", "window", (10, 17.96), (10, 19.46), [1.0, 2.8], [east, f"{e_el} {small}"]),
        opening("W_E2", "window", (10, 14.38), (10, 15.58), [1.0, 2.8], [east, f"{e_el} {small}"]),
        opening("W_E3", "window", (10, 8.84), (10, 13.64), [1.0, 3.4], [east, f"{e_el} {big}"]),
        opening("D_E", "door", (10, 5.70), (10, 7.30), [0.2, 2.6], [east, f"{e_el} {door}"]),
        opening("W_W1", "window", (0, 17.96), (0, 19.46), [1.0, 2.8], [west, f"{w_el} {small}"]),
        opening("W_W2", "window", (0, 14.38), (0, 15.58), [1.0, 2.8], [west, f"{w_el} {small}"]),
        opening("W_W3", "window", (0, 11.14), (0, 12.64), [1.0, 2.8], [west, f"{w_el} {small}"]),
        opening("W_W4", "window", (0, 8.42), (0, 9.92), [1.0, 2.8], [west, f"{w_el} {small}"]),
        opening("W_W5", "window", (0, 0.54), (0, 5.34), [1.0, 3.4], [west, f"{w_el} {big}"]),
    ]
    inner = [("D_lobby", (4.38, 15.94), (5.62, 15.94)), ("D_WA", (4.18, 13.39), (4.18, 14.29)),
             ("D_WB", (4.18, 11.77), (4.18, 12.67)), ("D_WC", (4.18, 6.81), (4.18, 7.71)),
             ("D_EA", (5.82, 14.39), (5.82, 15.29)), ("D_EB", (5.82, 12.76), (5.82, 13.66)),
             ("D_SE", (8.58, 4.94), (9.48, 4.94))]
    for oid, a, b in inner:
        openings.append(opening(oid, "door", a, b, [0.2, 2.3],
                                [gaps, "height assumed 2.1 m above the 0.2 m floor: no drawing dimensions interior doors"]))
    seeds = [{"id": sid, "point": p(*pt)} for sid, pt in (
        ("LOBBY", (3.0, 18.0)), ("R_WA", (2.0, 14.5)), ("R_WB", (2.0, 10.5)), ("R_WC", (2.0, 4.0)),
        ("COR", (5.0, 11.0)), ("R_EA", (8.0, 15.0)), ("R_EB", (8.0, 11.0)), ("R_SE", (8.0, 2.0)))]
    return {"floor_id": "F1", "z_floor": 0.2, "ceiling_height": 4.3,
            "x_anchors": [[X0, 0], [X1, 10]], "y_anchors": [[Y0, 0], [Y1, 20]],
            "basis": ("Anchors: outer faces of the gray exterior walls by view_pixel_profile (x 249/611 px, profile_001; "
                      "y 152/878 px, profiles 002/003) matched to the 10000/20000 overall dimensions. Perimeter on outer "
                      "faces, dividers on chain centre values mapped to pixels. z from the elevations' ground line; the "
                      "floor is 200 above it (door chains 200/2400/1900); roof line at 4500, so storey height 4.3 m."),
            "footprint_pixels": [p(0, 0), p(10, 0), p(10, 20), p(0, 20)],
            "partitions": walls, "openings": openings, "space_seeds": seeds,
            "assumptions": ["World z = 0 at the elevations' ground line; the ground floor is 0.2 m above it, so z_floor = 0.2 "
                            "(if z = 0 were taken at the floor instead, every z here would be 0.2 lower).",
                            "Interior door heights 2.1 m above the floor: no drawing dimensions them.",
                            "Corridor/SE-room step wall at y = 3.44 m is measured (not dimensioned).",
                            "Interior door jambs from measured wall gaps snapped to 10 mm."],
            "unresolved": []}


if __name__ == "__main__":
    out = RUN / "dev_inputs"
    out.mkdir(exist_ok=True)
    data = plan()
    (out / "plan_f1.json").write_text(json.dumps(data, ensure_ascii=False))
    req = [{"tool": "build_plan_bim", "arguments": {"image": "1f_view.png", "plan_json": json.dumps(data, ensure_ascii=False)}}]
    (out / "req_build.json").write_text(json.dumps(req, ensure_ascii=False))
    print(len(data["partitions"]), "dividers", len(data["openings"]), "openings", len(data["space_seeds"]), "seeds")
