"""逐栋校验：GLB 能否通过 mesh_observation 的门槛，并渲染预览。"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/workspaces/EnergyPlus-Agent-dev")
from src.agent.geometry.mesh_observation import MeshObservation

HERE = Path(__file__).parent
OUT = HERE / "single_buildings"
man = json.loads((OUT / "manifest.json").read_text())
results = []
for rec in man["buildings"]:
    bid = rec["building_id"]
    d = OUT / bid
    entry = dict(building_id=bid, district=rec["district"], axis1=rec["axis1_complexity"],
                 axis2=rec["axis2_type"], axis3=rec["axis3_quality"])
    try:
        obs = MeshObservation(d / "input.glb")
        desc = obs.describe()
        b = desc["bounds"]
        lo, hi = np.array(b[0], float), np.array(b[1], float)
        c, ext = (lo + hi) / 2, hi - lo
        # 斜视角：方位 -35°、仰角 25°，与既有单体预览一致，不依赖各栋局部轴朝向
        import math
        r = float(max(ext)) * 3.0
        az, el = math.radians(-35.0), math.radians(25.0)
        eye = [float(c[0]) + r * math.cos(el) * math.sin(az),
               float(c[1]) - r * math.cos(el) * math.cos(az),
               float(c[2]) + r * math.sin(el)]
        span = float(max(ext)) * 1.35
        obs.render(d / "view", eye=eye, target=[float(c[0]), float(c[1]), float(c[2])],
                   width_m=span, height_m=span, width_px=760, height_px=760)
        entry.update(mesh_observation="pass", faces=desc["face_count"],
                     extents_m=[round(float(v), 2) for v in ext],
                     texture_px=rec["texture_px"], texture_px_per_m=rec["texture_px_per_m"],
                     glb_bytes=rec["glb_bytes"], transferred_bytes=rec["transferred_bytes"])
    except Exception as exc:  # noqa: BLE001
        entry.update(mesh_observation="fail", error=f"{type(exc).__name__}: {exc}")
    results.append(entry)
    print(f"{bid}  {entry['mesh_observation']:5s}  {entry.get('extents_m','')}  "
          f"{entry.get('texture_px_per_m','')} px/m")
ok = sum(1 for r in results if r["mesh_observation"] == "pass")
(OUT / "verification.json").write_text(json.dumps(
    dict(checked=len(results), passed=ok, results=results), ensure_ascii=False, indent=1))
print(f"\n通过 {ok}/{len(results)}")
