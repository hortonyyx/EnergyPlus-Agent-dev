import json, ezdxf
from types import SimpleNamespace
from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import OpeningCarrierRuleV1
from src.agent.judge.gt_manifest import ClipBoxDxf

WIN_BLOCK = "$EWDLib$00000533"
DOOR_BLOCK = "$EWDLib$00000621"
WIN_SHA = "7800eb81a1dd440de462f13b89590cfaba3a8830952e3002b7f08e5aabe8592d"
DOOR_SHA = "2fa970a627d297431c28aa7d85ba4fef3db2bfb848aa988d99541056e4c466ad"
# 洞口 = 外框；其余为窗扇/门扇/把手等非结构细节
WIN_OUTLINE = {"316", "317", "319", "31B"}
DOOR_OUTLINE = {"35E", "35F", "360", "361"}
WIN_ALL = ["314","315","316","317","318","319","31A","31B"]
DOOR_ALL = ["34E","34F","350","351","352","353","354","355","356","357","358",
            "359","35A","35B","35C","35D","35E","35F","360","361","362"]

rules = [
    OpeningCarrierRuleV1.model_validate({
        "carrier_id": "sm25.window.polyline",
        "opening_kind": "window",
        "match": {"entity_type": "LWPOLYLINE", "layers": ["E_WINDOW"]},
        "outline": {"kind": "closed_polyline_rect"},
    }),
    OpeningCarrierRuleV1.model_validate({
        "carrier_id": "sm25.window.block",
        "opening_kind": "window",
        "match": {"entity_type": "INSERT", "layers": ["E_WINDOW"],
                  "block_name_exact": WIN_BLOCK, "block_definition_sha256": WIN_SHA},
        "outline": {"kind": "block_entity_rect",
                    "block_entity_roles": [
                        {"entity_handle": h,
                         "role": "structural_outline" if h in WIN_OUTLINE else "nonstructural_detail"}
                        for h in WIN_ALL]},
    }),
    OpeningCarrierRuleV1.model_validate({
        "carrier_id": "sm25.door.block",
        "opening_kind": "door",
        "match": {"entity_type": "INSERT", "layers": ["E_WINDOW"],
                  "block_name_exact": DOOR_BLOCK, "block_definition_sha256": DOOR_SHA},
        "outline": {"kind": "block_entity_rect",
                    "block_entity_roles": [
                        {"entity_handle": h,
                         "role": "structural_outline" if h in DOOR_OUTLINE else "nonstructural_detail"}
                        for h in DOOR_ALL]},
        "module_union_strategy": "touching_rect_union",
        "module_union_min_gap_m": 0.5,
    }),
]
print("schema OK: %d rules" % len(rules))

doc = ezdxf.readfile("case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf")
msp = doc.modelspace()
FRAMES = {"West_view":"382","South_view":"384","North_view":"386","East_view":"388"}
boxes = {}
for e in msp:
    if e.dxf.layer == "edge" and e.dxftype() == "LWPOLYLINE":
        pts=[tuple(p)[:2] for p in e.get_points()]
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        boxes[e.dxf.handle]=ClipBoxDxf(xmin=min(xs),ymin=min(ys),xmax=max(xs),ymax=max(ys))
tols = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=0.001, topo_area_m2=0.001)

total_w = total_d = 0
for vid, handle in FRAMES.items():
    view = SimpleNamespace(id=vid, clip_box_dxf=boxes[handle])
    carriers, diags = tn._resolve_opening_carriers(view, rules, msp, tols)
    doors, ddiags = tn._merge_door_carriers(
        [c for c in carriers if c[1] == "door"], rules, tols, vid)
    wins = [c for c in carriers if c[1] == "window"]
    audit = tn._audit_opening_carrier_consumption(view, rules, [], msp, carriers)
    total_w += len(wins); total_d += len(doors)
    print(f"{vid:11s} {len(wins):2d} 窗  {len(doors)} 门   解析诊断 {len(diags)}  合并诊断 {len(ddiags)}  台账剩余诊断 {len(audit)}")
    for d in list(diags)+list(ddiags)+list(audit):
        print("      !!", d.code, d.entity_handles)
    for d in doors:
        print("      门 handles:", d[3], "rect w=%.1f h=%.1f" % (d[2][2]-d[2][0], d[2][3]-d[2][1]))
print(f"TOTAL {total_w} 窗 {total_d} 门")
