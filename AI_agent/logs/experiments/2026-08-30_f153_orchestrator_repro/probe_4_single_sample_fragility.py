"""F-153 形态 A 的脆弱度量化：出口射线只采 mid_along 一个点。"""
import json
from pathlib import Path
from shapely.geometry import Point
from src.agent.judge.as_measured import (AsMeasuredViewV1, _boundary_footprint,
                                         _boundary_wall_region)

FACTS = Path("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json")
LO, HI, EXIT_CONST = 46400, 53600, 161201

doc = json.loads(FACTS.read_text(encoding="utf-8"))
for vid in ("plan-F1", "plan-F2"):
    view = AsMeasuredViewV1.model_validate(
        next(v for v in doc["views"] if v["view_id"] == vid))
    _boundary_footprint(view)
    wall_region = _boundary_wall_region(view)
    xs = list(range(LO, HI + 1, 10))          # 1 mm 步长
    bad = [x for x in xs if wall_region.covers(Point(x, EXIT_CONST))]
    mid = (LO + HI) // 2
    print(f"{vid}: span x[{LO},{HI}] 采样 {len(xs)} 点，落在墙体并集内 = {len(bad)}"
          f" ({len(bad)/len(xs):.1%})；生产代码只采 mid_along={mid} ⇒ "
          f"{'判死' if mid in bad else '判活'}；中毒区间 x=[{bad[0]},{bad[-1]}]")
