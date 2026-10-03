"""Side-by-side behaviour/quality/cost table from records/<run>/summary.json (offline).

Quality figures come from each run's saved independent evaluation, cited per row; behaviour,
time and usage come from the behaviour records written by record.py.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (label, run directory, period, quality: rooms one-to-one / positions / hosts / connections /
# exterior heights within 5 cm / strict partition, source of the quality figures)
RUNS = [
    ("run57", "2026-09-26_sm21_whole_building_claude_run57", "好结果", "通过 / 29 / 29 / 14 / 17/17 / minor", "instruction_fix README 表"),
    ("run58", "2026-09-27_sm21_whole_building_repeat_claude_run58", "好结果", "通过 / 29 / 29 / 14 / 17/17 / minor", "instruction_fix README 表"),
    ("run93", "2026-09-29_sm21_aligned_prompt_run93", "退步期", "通过 / 18 / 29 / 14 / 15/17 / minor", "instruction_fix README 表"),
    ("run94", "2026-09-29_sm21_instruction_refactor_run94", "退步期", "三间合一 / 13 / 29 / 14 / 9/13+4未配 / severe", "instruction_fix README 表"),
    ("run98", "2026-09-30_sm21_instruction_fix_run98", "修复包", "通过 / 29 / 29 / 14 / 16/17 / severe", "run98 fix_evaluation.json"),
    ("run99", "2026-09-30_sm21_instruction_fix_run99", "修复包", "通过 / 28 / 29 / 14 / 9/17 / severe", "run99 fix_evaluation.json"),
    ("run100", "2026-09-30_sm24_instruction_fix_run100", "修复包 sm24", "走廊并入东侧会议室 / 14/21 / 18 / 7 / 14/14 / severe", "run100 cross_case_evaluation.json"),
    ("GLM", "2026-09-30_sm21_instruction_fix_glm_trial01", "修复包(GLM)", "通过 / 27 / 29 / 14 / 17/17 / severe", "glm_flash_trial README"),
    ("run55", "2026-09-26_sm24_whole_building_claude_run55", "好结果 sm24", "通过 / 20/21 / 21 / 10 / 14/14 / severe", "cross_case_historical_checks.json"),
    ("run56", "2026-09-26_sm24_whole_building_repeat_claude_run56", "好结果 sm24", "通过 / 21/21 / 21 / 10 / 14/14 / severe", "cross_case_historical_checks.json"),
    ("run53", "2026-09-26_sm25_height_cold_claude_run53", "好结果 sm25", "通过 / 61/61 / 61 / 30 / 34/34 / severe", "cross_case_historical_checks.json"),
    ("run54", "2026-09-26_sm25_height_repeat_claude_run54", "好结果 sm25", "通过 / 53/61 / 61 / 30 / 34/34 / severe", "cross_case_historical_checks.json"),
]
EXTRA = []  # appended at run time for runs recorded later, e.g. run100/run101


def row(label, name, period, quality, source):
    path = HERE / "records" / name / "summary.json"
    if not path.exists():
        return None
    s = json.loads(path.read_text())
    if s.get("schema_version") == "bim.behaviour.v2":
        # Old archives keep their historical names; newly regenerated records
        # use the shared schema, without rewriting old evidence to invent values.
        s = dict(s, first_build_s=s["first_build_attempt_s"],
                 calls_before_first_build=s["calls_before_first_build_attempt"],
                 full_views_before_first_build=s["full_views_before_first_build_attempt"],
                 crops_before_first_build=s["crops_before_first_build_attempt"],
                 pixel_tools_before_first_build=s["pixel_tools_before_first_build_attempt"],
                 claims=s["height_provenance_claims"], cross_facade_claims=s["cross_facade_height_claims"])
    usage = next(iter(s["model_usage"].values()), {}) if s["model_usage"] else {}
    window = s["five_hour_window"]
    overlays = sum(s["elevation_overlays_by_facade"].values())
    return dict(
        label=label, period=period, quality=quality, quality_source=source, model=s["model"],
        elapsed_s=round(s["elapsed_seconds"] or 0), first_build_s=round(s["first_build_s"] or 0),
        turns=s["turns"], tool_calls=s["tool_calls"], tool_errors=f"{s['tool_errors']}/{s.get('domain_failures', '未计')}/{s.get('usable_source_drafts', '未计')}",
        before_first_build=f"{s['calls_before_first_build']}（全图{s['full_views_before_first_build']}/局部{s['crops_before_first_build']}/像素{s['pixel_tools_before_first_build']}）",
        elevation_check=f"叠图{overlays}（{','.join(f'{k[0].upper()}{v}' for k, v in sorted(s['elevation_overlays_by_facade'].items()) if k)}）/立面局部{sum(s['elevation_crops_by_facade'].values())}",
        claims=f"{len(s['claims'])}（跨立面套用{s['cross_facade_claims']}）",
        output_tokens=usage.get("outputTokens"), thinking_tokens=usage.get("thinkingTokens"),
        cache_read_tokens=usage.get("cacheReadInputTokens"), cost_usd_cli=round(s["cost_usd_cli"], 2) if s["cost_usd_cli"] is not None else None,
        five_hour_used=round(window[1] - window[0], 2) if window else None)


COLUMNS = [("label", "运行"), ("period", "时期"), ("quality", "房间对应/位置/宿主/连接/外高/严格分区"),
           ("elapsed_s", "总时长s"), ("first_build_s", "首建尝试s"), ("turns", "轮数"), ("tool_calls", "工具调用"),
           ("tool_errors", "调用报错/领域未成功/可用源稿"), ("before_first_build", "首稿前调用"), ("elevation_check", "立面核对"),
           ("claims", "高度依据"), ("output_tokens", "输出token"), ("thinking_tokens", "思考token"),
           ("cache_read_tokens", "缓存读取"), ("cost_usd_cli", "CLI估价$"), ("five_hour_used", "5h窗口占用")]


def main():
    rows = [r for r in (row(*spec) for spec in RUNS + EXTRA) if r]
    lines = ["| " + " | ".join(title for _, title in COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(str(r[key]) for key, _ in COLUMNS) + " |" for r in rows]
    (HERE / "compare.md").write_text("\n".join(lines) + "\n\n质量来源：" + "；".join(
        f"{r['label']}={r['quality_source']}" for r in rows) + "。CLI 估价非账单；5h 窗口占用为运行首末读数之差，可能含同时段其他会话用量。\n")
    (HERE / "compare.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
