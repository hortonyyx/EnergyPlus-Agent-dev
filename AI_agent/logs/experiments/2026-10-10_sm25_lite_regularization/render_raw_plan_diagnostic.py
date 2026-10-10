"""Read-only source rendering: no compiler, alignment, repair, GT, or model calls."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\EnergyPlus-Agent-worktrees\lite-sm25-run-20261010")
RUN = ROOT / "AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1"
PLAN = RUN / "tasks/c1c3b11072b0cc1a10539ba75831d98e96c9275f8d8498eeb15cff1977aa386d/bim/trial_workspace/trial_receipts/trial_005_plan.json"
SOURCE = ROOT / "case_tests/e2e_tests/sm25-L_anchor/case_data/1f_view.png"
OUT = Path(__file__).resolve().parent
raw = PLAN.read_bytes()
plan = json.loads(raw)
original = Image.open(SOURCE).convert("RGBA")
layer = Image.new("RGBA", original.size)
draw = ImageDraw.Draw(layer)
font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
small = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)

footprint = [tuple(p) for p in plan["footprint_pixels"]]
draw.line(footprint + [footprint[0]], fill=(255, 196, 60, 230), width=4)
for wall in plan["partitions"]:
    draw.line([tuple(p) for p in wall["points"]], fill=(80, 150, 255, 210), width=4)
for opening in plan["openings"]:
    p1, p2 = tuple(opening["p1"]), tuple(opening["p2"])
    color = (255, 80, 160, 240) if opening["kind"] == "door" else (75, 245, 160, 230)
    if opening["id"] == "D6":
        color = (255, 40, 40, 255)
    draw.line([p1, p2], fill=color, width=7)
    if opening["kind"] == "door":
        x, y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        draw.text((x + 7, y - 26), opening["id"], font=small, fill=color, stroke_width=2, stroke_fill=(0, 0, 0, 255))
for seed in plan["space_seeds"]:
    x, y = seed["point"]
    draw.ellipse((x-5, y-5, x+5, y+5), fill=(255, 255, 255, 230))
overlay = Image.alpha_composite(original, layer).convert("RGB")
canvas = Image.new("RGB", (original.width + 640, original.height), (24, 28, 37))
canvas.paste(overlay, (0, 0))
d = ImageDraw.Draw(canvas)
x = original.width + 24
y = 30
lines = [
    "F1 trial_005 / pre-assembly",
    "未通过编译的原始声明，不是 BIM 结果",
    "原图与声明坐标 1:1 叠加，未对齐或修复",
    "黄色：footprint；蓝色：partition",
    "粉色：door；绿色：window；白点：seed",
    "红色 D6：一个开口跨过会议室隔墙",
    "原图实际是两组独立双扇门",
    "15 门 / 15 窗 / 14 seeds（非已验证空间）",
    "F2 首批未产生完整平面稿",
    "本轮 dev 辅助调度；非盲测",
    "原始 plan 文件 SHA256：",
]
digest = hashlib.sha256(raw).hexdigest()
lines += [digest[:32], digest[32:]]
for line in lines:
    d.text((x, y), line, fill=(238, 241, 247), font=font)
    y += 39
d.text((x, 590), "D6 区域原图（仅裁切放大，不改变证据）", font=font, fill="white")
crop = (750, 1000, 1020, 1120)
canvas.paste(original.crop(crop).convert("RGB").resize((540, 240)), (x, 630))
d.text((x, 900), "同区域原始声明叠图", font=font, fill="white")
canvas.paste(overlay.crop(crop).resize((540, 240)), (x, 940))
d.text((x, 1220), "原图门组约 x793–866 / x900–973，y1053", font=small, fill="white")
d.text((x, 1250), "声明 D6 x860–960，y1053；未经任何修正", font=small, fill="white")
target = OUT / "F1_trial005_raw_declarations_NOT_BIM.png"
canvas.save(target)
manifest = {
    "stage": "pre-assembly / failed trial / raw declarations, NOT BIM",
    "plan": str(PLAN), "plan_file_sha256": digest,
    "source_image": str(SOURCE), "source_image_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "output": target.name, "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "method": "Pillow: original image at (0,0), 1:1 declared pixel coordinates; RGBA lines and seed points only; sidebar includes exact region crop enlarged 2x. No coordinate changes, geometry compilation, GT, or model calls.",
}
(OUT / "F1_trial005_raw_declarations_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False, indent=2))
