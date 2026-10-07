"""Write index.html: the three-case comparison table with links to plan images, overlays, viewers and scores.

Usage: python summary.py   (reads metrics_<run>.json, evaluation_<run>.json and each run's posthoc_* folders;
runs not yet scored show as pending). No model calls.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNS = ROOT / "AI_agent/archive/local_backup/cmp3"
LINK = "../../../archive/local_backup/cmp3"
CASES = [("sm24", "sm24：一层，8 间"), ("sm21", "sm21：两层，14 间"), ("sm25", "sm25：两层，29 间")]
MODES = [("single", "单模型"), ("role", "分工模式")]

# Findings read from the overlays, plan images and score details (Opus, 10-07).
NOTES = {
    "sm24_single": "无实质错误。门窗 19/21 在 5 cm 内。",
    "sm24_role": "无实质错误。房间边界 6 处、门 4 处在 10–30 cm 档。",
    "sm21_role": "无实质错误。门窗全部在 5 cm 内；房间边界 7 处在 10–30 cm 档。开局 5 次请求被 GLM 以并发超限拒绝；"
                 "协调员收尾约 21 分钟，含一次西立面返工。",
    "sm21_single": "无实质错误。门窗 24/29 在 5 cm 内。",
    "sm25_single": "二层东段约 10 m×2 m 的走廊漏建（被当成室外）：南侧 3 扇门因此成了外门，庭院一侧的一扇长窗被拆成 6 扇"
                   "（多出 5 扇）。房间边界表里另两处“>30 cm”（一层 roomA、二层会议室）实为一条 13 cm 宽、5 m 长的墙缝"
                   "分给了房间而不是走廊，实际属 10–30 cm 档。一层两扇外门底标高按 0 m 建，图上为 0.2 m。"
                   "用了 62/64 个候选，130 分钟。",
    "sm25_role": "一层上方第二间会议室少一道墙、并进了走廊，走廊西段反而多加一道隔墙、成了单独的“未知”空间；二层两道墙之间"
                 "留下一条约 12 cm 宽的缝被当成一个房间（30 间对参考 29 间）。7 处门窗“挂错墙／连错房间”都是这两处划分的"
                 "连带结果，门窗本身位置准（无 >30 cm）；外墙门窗高度 34 扇全部在 5 cm 内。房间边界表里另三处“>30 cm”为细长缝，"
                 "实属 10–30 cm 档。一层平面读图员开头被 GLM 连拒 6 次停掉，第 52 分钟才重派，关键路径因此多出约 50 分钟；"
                 "122.6 分钟。",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def tiers(row):
    return " / ".join(str(row[k]) for k in ("<=5cm", "5-10cm", "10-30cm", ">30cm"))


def links(name, metrics):
    run = RUNS / name
    shown = load(run / "posthoc_overlays/index.json") or {}
    display = load(run / "posthoc_display/index.json") or {}
    base = f"{LINK}/{name}"
    parts = []
    plans = [f'<a href="{base}/posthoc_display/{p}">{html.escape(Path(p).stem.removeprefix("plan_"))}</a>'
             for p in display.get("plans", [])]
    if plans:
        parts.append("平面图 " + " ".join(plans))
    overlay = [f'<a href="{base}/posthoc_overlays/{p["overlay"]}">{html.escape(p.get("floor", p["floor_id"]))}</a>'
               for p in shown.get("plans", []) if "overlay" in p]
    overlay += [f'<a href="{base}/posthoc_overlays/{e["overlay"]}">{e["facade"][0]}</a>'
                for e in shown.get("elevations", []) if "overlay" in e]
    if overlay:
        parts.append("回叠图 " + " ".join(overlay))
    if display.get("viewer"):
        parts.append(f'<a href="{base}/posthoc_display/viewer.html">BIM 查看页</a>')
    parts.append(f'<a href="evaluation/{name}/index.html">评分报告</a>')
    return "<br>".join(parts)


def row(case, mode, label):
    name = f"{case}_{mode}"
    metrics = load(HERE / f"metrics_{name}.json")
    if metrics is None:
        return f'<tr><td>{label}</td><td colspan="7" class="pending">运行中或待评分</td></tr>'
    spaces = metrics["spaces_reference_candidate_matched"]
    openings, heights = metrics["openings"], metrics["heights"]
    substantive = metrics["substantive_findings"]
    tokens = metrics["tokens_reported"]
    flag = "bad" if substantive else "ok"
    return (f'<tr><td>{label}</td>'
            f'<td class="num">{metrics["minutes"]:.1f}</td>'
            f'<td class="num">{metrics["requests"]}<br><span class="sub">{tokens / 1e6:.2f}M token</span></td>'
            f'<td>{spaces[2]}/{spaces[0]}<br><span class="sub">边界 {tiers(metrics["tiers_room_boundary"])}</span></td>'
            f'<td>{openings["matched"]}/{openings["reference_count"]}<br>'
            f'<span class="sub">沿墙 {tiers(metrics["tiers_opening_along_wall"])}</span></td>'
            f'<td>{heights["matched"]}/{heights["expected"]}<br><span class="sub">{tiers(metrics["tiers_exterior_height"])}</span></td>'
            f'<td class="{flag}">{len(substantive) if substantive else "无"}<br><span class="sub">{html.escape(NOTES.get(name, ""))}</span></td>'
            f'<td class="links">{links(name, metrics)}</td></tr>')


def gallery(name):
    run = RUNS / name
    shown = load(run / "posthoc_overlays/index.json")
    display = load(run / "posthoc_display/index.json")
    if not shown or not display:
        return ""
    base = f"{LINK}/{name}"
    images = [(f"{base}/posthoc_display/{p}", "平面图 " + Path(p).stem.removeprefix("plan_")) for p in display["plans"]]
    images += [(f"{base}/posthoc_overlays/{p['overlay']}", "平面回叠 " + p.get("floor", p["floor_id"]))
               for p in shown["plans"] if "overlay" in p]
    images += [(f"{base}/posthoc_overlays/{e['overlay']}", "立面回叠 " + e["facade"])
               for e in shown["elevations"] if "overlay" in e]
    cells = "".join(f'<figure><a href="{src}"><img loading="lazy" src="{src}" alt="{html.escape(cap)}"></a>'
                    f'<figcaption>{html.escape(cap)}</figcaption></figure>' for src, cap in images)
    return (f'<details><summary>{name} · 交付 {display["candidate"]}</summary>'
            f'<div class="grid">{cells}</div></details>')


def main():
    rows, galleries = [], []
    for case, title in CASES:
        rows.append(f'<tr class="case"><td colspan="8">{title}</td></tr>')
        for mode, label in MODES:
            rows.append(row(case, mode, label))
            galleries.append(gallery(f"{case}_{mode}"))
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>三案对照 10-07</title>
<style>
:root {{ --bg:#fbfbf9; --fg:#1d1d1b; --muted:#6b6b66; --line:#deded8; --ok:#1f7a3f; --bad:#b3261e; --case:#efefe9; --link:#2456a6; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#181817; --fg:#e8e8e3; --muted:#a3a39b; --line:#3a3a36; --ok:#6cc58b; --bad:#f08a80; --case:#262624; --link:#8db4f2; }} }}
:root[data-theme="dark"] {{ --bg:#181817; --fg:#e8e8e3; --muted:#a3a39b; --line:#3a3a36; --ok:#6cc58b; --bad:#f08a80; --case:#262624; --link:#8db4f2; }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.55 system-ui, "Microsoft YaHei", sans-serif; margin:0 auto; max-width:1280px; padding:24px 16px 64px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} p {{ margin:6px 0; }} .meta, .sub {{ color:var(--muted); }} .sub {{ font-size:12.5px; }}
a {{ color:var(--link); }} .wrap {{ overflow-x:auto; margin:16px 0; }}
table {{ border-collapse:collapse; width:100%; min-width:980px; }}
th, td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ font-size:13px; color:var(--muted); font-weight:600; }}
tr.case td {{ background:var(--case); font-weight:600; }}
td.num {{ font-variant-numeric:tabular-nums; white-space:nowrap; }} td.ok {{ color:var(--ok); }} td.bad {{ color:var(--bad); }}
td.ok .sub, td.bad .sub {{ color:var(--muted); }} td.links {{ white-space:nowrap; font-size:13.5px; }} .pending {{ color:var(--muted); }}
details {{ border-top:1px solid var(--line); padding:10px 0; }} summary {{ cursor:pointer; font-weight:600; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:12px; margin-top:10px; }}
figure {{ margin:0; }} figure img {{ width:100%; border:1px solid var(--line); background:#000; }} figcaption {{ font-size:12.5px; color:var(--muted); }}
</style></head><body>
<h1>三案对照：单模型 vs 分工模式（10-07）</h1>
<p class="meta">GLM 订阅 glm-5.3-flash · medium · Agent 版本 t1-20261007-d1i.1 · 六次依次运行（错开派发）· 每次上限 3 小时、400 次请求、3000 万 token</p>
<p>精度三档（10-07 定）：≤5 cm 好；5–10 cm 可以；10–30 cm 不作为主要提升点；&gt;30 cm 需专门处理。表中四个数依次是这四档的个数。
“实质错误”指房间多、少、拆、并，门窗多、少，或门窗换了所在墙、连接的房间。</p>
<div class="wrap"><table>
<thead><tr><th>模式</th><th>用时（分）</th><th>请求</th><th>房间（对上/参考）</th><th>门窗（对上/参考）</th><th>外墙门窗高度</th><th>实质错误</th><th>产物</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="sub">平面图和 BIM 查看页按现行命名规则（bim_names_v3）从交付稿重出，几何不变；回叠图在运行结束后用该次运行自己登记的标定画出，模型没看过这些图。
回叠图上的小字是模型自己用的内部编号（按 10-07 约定，回叠图不加公开名）。房间边界的档位按边界最大偏离算，一条细长缝会按其长度计入，&gt;30 cm 的行已逐一看过并在备注里说明。</p>
{''.join(galleries)}
</body></html>
"""
    (HERE / "index.html").write_text(page, encoding="utf-8", newline="\n")
    print(HERE / "index.html")


if __name__ == "__main__":
    main()
