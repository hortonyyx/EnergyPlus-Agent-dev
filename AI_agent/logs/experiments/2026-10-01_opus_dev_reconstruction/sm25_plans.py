"""Developer's sm25 floor declarations (two different floors on one L-shaped footprint).

Anchors: measured outer wall lines (1F x 282/1437 px, y 1235/310 px; 2F x 241/1387 px,
y 1258/341 px; profiles 005-012). Walls on chain values: top 5000/4940/1120/3940/10000,
west 3940/2060/4000/4120/1940/3940, east 2000 x7 (1F) or 3940/2060/2000 x4/2060/3940 (2F),
bottom 5000/8000/7940/4060 (1F) or 5000/4090/3910/3910/4030/4060 (2F). The middle offices'
(1F) and meeting room's (2F) east wall is undimensioned: measured at x = 8.94 (= 5.00 + 3.94,
the office-column width). Door jambs are measured wall-line gaps (profiles 013-020).
z from the elevations' ground line; exterior door chains start 200/2100, so the ground floor
is 0.2 above it; storey line at 3600, roof at 7200.
"""
import json
from pathlib import Path

RUN = Path(__file__).resolve().parents[1] / "2026-10-01_opus_dev_sm25"
FOOT = [(0, 20), (15, 20), (15, 6), (25, 6), (25, 0), (5, 0), (5, 14), (0, 14)]


class Frame:
    def __init__(self, x0, x25, y0, y20):
        self.x0, self.y0, self.sx, self.sy = x0, y0, (x25 - x0) / 25.0, (y20 - y0) / 20.0
        self.x_anchors, self.y_anchors = [[x0, 0], [x25, 25]], [[y0, 0], [y20, 20]]

    def p(self, x, y):
        return [round(self.x0 + x * self.sx, 3), round(self.y0 + y * self.sy, 3)]


def build(f, floor_id, z_floor, height, walls, openings, seeds, basis, assumptions):
    return {"floor_id": floor_id, "z_floor": z_floor, "ceiling_height": height,
            "x_anchors": f.x_anchors, "y_anchors": f.y_anchors, "basis": basis,
            "footprint_pixels": [f.p(*q) for q in FOOT],
            "partitions": [{"id": i, "points": [f.p(*a), f.p(*b)], "source_refs": r} for i, a, b, r in walls],
            "openings": [{"id": i, "kind": k, "p1": f.p(*a), "p2": f.p(*b), "z": z, "source_refs": r}
                         for i, k, a, b, z, r in openings],
            "space_seeds": [{"id": i, "point": f.p(*q)} for i, q in seeds],
            "assumptions": assumptions, "unresolved": []}


def floor1():
    f = Frame(282, 1437, 1235, 310)
    top, west, east, bot = ("1f_view.png top chains 5000/4940/1120/3940/10000 and 2240/2400/720/2400/2540/600/4100/300/8000/1700",
                            "1f_view.png west chains 3940/2060/4000/4120/1940/3940 and 4660/1340/1840/1800/720/1800/2740/800/4300",
                            "1f_view.png east chains 2000 x7 + 6000 and 740/900/720/900/1480/900/720/900/1480/900/720/900/1100/900/740/3860/1600/540",
                            "1f_view.png bottom chains 5000/8000/7940/4060 and 5000/3640/4000/720/4000/3580/4060")
    walls = [("P_MR12", (5, 16.06), (5, 20), [top]), ("P_top", (0, 16.06), (9.94, 16.06), [west]),
             ("P_corTop", (9.94, 16.06), (9.94, 20), [top]), ("P_col", (11.06, 20), (11.06, 6), [top, east]),
             ("P_LMn", (5, 14), (8.94, 14), [west]), ("P_LMe", (8.94, 14), (8.94, 5.88),
              ["1f_view.png: undimensioned divider measured at x 8.94 (5.00+3.94)"]),
             ("P_LMm", (5, 10), (8.94, 10), [west]), ("P_LMs", (5, 5.88), (8.94, 5.88), [west]),
             ("P_colS", (11.06, 6), (15, 6), [east + ": office row ends at the 6000 line"]),
             ("P_MRn", (5, 3.94), (20.94, 3.94), [west, bot]), ("P_MR34", (13, 0), (13, 3.94), [bot]),
             ("P_MRe", (20.94, 0), (20.94, 3.94), [bot])]
    walls += [(f"P_off{y}", (11.06, y), (15, y), [east + f": office divider at {y}"]) for y in (18, 16, 14, 12, 10, 8)]
    n12, nbig = "North_view.png chain 1000/1600/1000: 1.0-2.6", "North_view.png chain 1000/2200/400: 1.0-3.2"
    e12, w12, s18 = ("East_view.png chain 1000/1600/1000: 1.0-2.6", "West_view.png middle chain 1000/1600/1000: 1.0-2.6",
                     "South_view.png chain 1000/1800/800: 1.0-2.8")
    door = "West_view.png door chain 200/2100/1300: 0.2-2.3"
    gap = "measured wall-line gap (view_pixel_profile)"
    o = [("W_N1", "window", (2.24, 20), (4.64, 20), [1.0, 2.6], [top, n12]),
         ("W_N2", "window", (5.36, 20), (7.76, 20), [1.0, 2.6], [top, n12]),
         ("W_N3", "window", (10.30, 20), (10.90, 20), [1.0, 2.6], [top, n12]),
         ("W_BN", "window", (15.30, 6), (23.30, 6), [1.0, 3.2], [top, nbig]),
         ("W_W1", "window", (5, 10.36), (5, 12.16), [1.0, 2.6], [west, w12]),
         ("W_W2", "window", (5, 7.84), (5, 9.64), [1.0, 2.6], [west, w12]),
         ("W_S1", "window", (8.64, 0), (12.64, 0), [1.0, 2.8], [bot, s18]),
         ("W_S2", "window", (13.36, 0), (17.36, 0), [1.0, 2.8], [bot, s18]),
         ("D_W1", "door", (0, 14.54), (0, 15.34), [0.2, 2.3], [west, door]),
         ("D_W2", "door", (5, 4.30), (5, 5.10), [0.2, 2.3], [west, door]),
         ("D_E", "door", (25, 0.54), (25, 2.14), [0.2, 2.3],
          [east, "East_view.png double door: no height chain; drawn frame about 0.18-2.28 m against the 3600 storey line, read as the 200/2100 door type"])]
    for i, (a, b) in enumerate(((18.36, 19.26), (16.74, 17.64), (14.36, 15.26), (12.74, 13.64), (10.36, 11.26), (8.74, 9.64), (6.74, 7.64)), 1):
        o.append((f"W_E{i}", "window", (15, a), (15, b), [1.0, 2.6], [east, e12]))
    inner = [("D_MR1", (3.82, 16.06), (4.66, 16.06)), ("D_MR2", (5.35, 16.06), (6.17, 16.06)),
             ("D_LM1", (8.94, 10.34), (8.94, 11.17)), ("D_LM2", (8.94, 8.82), (8.94, 9.64)),
             ("D_MR3", (11.04, 3.94), (12.64, 3.94)), ("D_MR4", (13.35, 3.94), (14.98, 3.94))]
    inner += [(f"D_O{i}", (11.06, a), (11.06, b)) for i, (a, b) in enumerate(
        ((18.34, 19.17), (16.82, 17.64), (14.34, 15.15), (12.82, 13.64), (10.32, 11.17), (8.82, 9.64), (6.82, 7.63)), 1)]
    o += [(i, "door", a, b, [0.2, 2.3], [gap, "height assumed equal to the exterior doors (2.1 m above the floor)"]) for i, a, b in inner]
    seeds = [("MR1", (2.5, 18)), ("MR2", (7.5, 18)), ("COR", (10.5, 12)), ("LM1", (7, 12)), ("LM2", (7, 8)),
             ("MR3", (9, 2)), ("MR4", (17, 2))] + [(f"O{i}", (13, y)) for i, y in enumerate((19, 17, 15, 13, 11, 9, 7), 1)]
    basis = ("Anchors: outer wall lines by view_pixel_profile (x 282/1437 px, y 1235/310 px) matched to 25000/20000. "
             "Perimeter on outer faces (L outline with the 0-5 m step at y 14 and the wing below y 6); dividers on "
             "chain centre values; positions are chain values mapped to pixels. z from the ground line; floor 0.2.")
    return build(f, "F1", 0.2, 3.4, walls, o, seeds, basis, [
        "World z = 0 at the elevations' ground line; the ground floor is 0.2 m above it (exterior door chains 200/2100).",
        "The 1F east wall of the middle offices is undimensioned and measured at x = 8.94 m.",
        "The bottom-corridor north wall is kept on the 6.0 m line east of the corridor so it meets the outer face; west of it the chain gives 5.88 m.",
        "Interior door heights assumed equal to the exterior door type (2.1 m above the floor).",
        "Door jambs from measured wall gaps rounded to 10 mm."])


def floor2():
    f = Frame(241, 1387, 1258, 341)
    top, west, east, bot = ("2f_view.png top chains 5000/4940/1120/3940/10000 and 2240/2400/720/2400/2540/600/4100/300/8000/1700",
                            "2f_view.png west chains 3940/2060/4000/4120/1940/3940 and 6000/1840/4320/2380/1200/4260",
                            "2f_view.png east chains 3940/2060/2000 x4/2060/3940 and 4740/900/720/900/1480/900/720/900/1100/900/740/6000",
                            "2f_view.png bottom chains 5000/4090/3910/3910/4030/4060 and 5000/1930/1800/720/1800/3500/1800/720/1800/2230/1800/1900")
    walls = [("P_AB", (5, 16.06), (5, 20), [top]), ("P_top", (0, 16.06), (15, 16.06), [west, east]),
             ("P_BC", (9.94, 16.06), (9.94, 20), [top]), ("P_col", (11.06, 16.06), (11.06, 6), [top]),
             ("P_colS", (11.06, 6), (15, 6), [east]),
             ("P_MTn", (5, 14), (8.94, 14), [west]), ("P_MTe", (8.94, 14), (8.94, 5.88),
              ["2f_view.png: undimensioned meeting-room wall measured at x 8.94 (5.00+3.94)"]),
             ("P_MTs", (5, 5.88), (8.94, 5.88), [west]), ("P_offN", (5, 3.94), (25, 3.94), [west, east])]
    walls += [(f"P_off{y}", (11.06, y), (15, y), [east + f": office divider at {y}"]) for y in (14, 12, 10, 8)]
    walls += [(f"P_bo{x}", (x, 0), (x, 3.94), [bot + f": office divider at {x}"]) for x in (9.09, 13.0, 16.91, 20.94)]
    n16, nbig = "North_view.png chain 1000/1600/1000 above 3600: 4.6-6.2", "North_view.png chain 1000/2200/400 above 3600: 4.6-6.8"
    e16, s16 = "East_view.png chain 1000/1600/1000 above 3600: 4.6-6.2", "South_view.png chain 1000/1600/1000 above 3600: 4.6-6.2"
    w22, w16 = "West_view.png chain 1000/2200/400 above 3600: 4.6-6.8", "West_view.png chain 1000/1600/1000 above 3600: 4.6-6.2"
    gap = "measured wall-line gap (view_pixel_profile)"
    o = [("W_N1", "window", (2.24, 20), (4.64, 20), [4.6, 6.2], [top, n16]),
         ("W_N2", "window", (5.36, 20), (7.76, 20), [4.6, 6.2], [top, n16]),
         ("W_N3", "window", (10.30, 20), (10.90, 20), [4.6, 6.2], [top, n16]),
         ("W_BN", "window", (15.30, 6), (23.30, 6), [4.6, 6.8], [top, nbig]),
         ("W_W1", "window", (5, 7.84), (5, 12.16), [4.6, 6.8], [west, w22]),
         ("W_W2", "window", (5, 4.26), (5, 5.46), [4.6, 6.2], [west, w16])]
    for i, (a, b) in enumerate(((14.36, 15.26), (12.74, 13.64), (10.36, 11.26), (8.74, 9.64), (6.74, 7.64)), 1):
        o.append((f"W_E{i}", "window", (15, a), (15, b), [4.6, 6.2], [east, e16]))
    for i, (a, b) in enumerate(((6.93, 8.73), (9.45, 11.25), (14.75, 16.55), (17.27, 19.07), (21.30, 23.10)), 1):
        o.append((f"W_S{i}", "window", (a, 0), (b, 0), [4.6, 6.2], [bot, s16]))
    inner = [("D_A", (3.85, 16.06), (4.66, 16.06)), ("D_B", (5.37, 16.06), (6.18, 16.06)), ("D_C", (10.11, 16.06), (10.92, 16.06)),
             ("D_MT", (8.94, 12.07), (8.94, 13.69))]
    inner += [(f"D_O{i}", (11.06, a), (11.06, b)) for i, (a, b) in enumerate(
        ((14.33, 15.17), (12.81, 13.63), (10.33, 11.16), (8.80, 9.65), (6.82, 7.63)), 1)]
    inner += [(f"D_S{i}", (a, 3.94), (b, 3.94)) for i, (a, b) in enumerate(
        ((7.94, 8.76), (9.43, 10.29), (15.74, 16.59), (17.28, 18.11), (21.29, 22.13)), 1)]
    o += [(i, "door", a, b, [3.6, 5.7], [gap, "height assumed 2.1 m above the 3.6 m floor"]) for i, a, b in inner]
    seeds = [("A", (2.5, 18)), ("B", (7.5, 18)), ("C", (12.5, 18)), ("COR", (10, 10)), ("MT", (7, 10))]
    seeds += [(f"O{i}", (13, y)) for i, y in enumerate((15, 13, 11, 9, 7), 1)]
    seeds += [(f"S{i}", (x, 2)) for i, x in enumerate((7, 11, 15, 19, 23), 1)]
    basis = ("Anchors: outer wall lines by view_pixel_profile (x 241/1387 px, y 1258/341 px) matched to 25000/20000; same "
             "origin and axes as F1. Dividers on chain centre values mapped to pixels. Floor at the 3600 storey line, roof 7200.")
    return build(f, "F2", 3.6, 3.6, walls, o, seeds, basis, [
        "The 2F meeting-room east wall is undimensioned and measured at x = 8.94 m.",
        "Interior door heights assumed 2.1 m above the floor.",
        "Door jambs from measured wall gaps rounded to 10 mm."])


if __name__ == "__main__":
    out = RUN / "dev_inputs"
    out.mkdir(exist_ok=True)
    req = []
    for name, plan, image in (("plan_f1.json", floor1(), "1f_view.png"), ("plan_f2.json", floor2(), "2f_view.png")):
        (out / name).write_text(json.dumps(plan, ensure_ascii=False))
        req.append({"tool": "build_plan_bim", "arguments": {"image": image, "plan_json": json.dumps(plan, ensure_ascii=False)}})
        print(name, len(plan["partitions"]), "dividers", len(plan["openings"]), "openings", len(plan["space_seeds"]), "seeds")
    (out / "req_build.json").write_text(json.dumps(req, ensure_ascii=False))
