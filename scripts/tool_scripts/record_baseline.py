"""Record a case as a self-contained baseline: baseline.json + RUN_REPORT.md.

The new (2026-06-16) baseline scheme: a clean anchor case carries its own machine
score-card (baseline.json) + a human report with an eyeball checklist
(RUN_REPORT.md). This tool runs the deterministic gate① over the on-disk case
(validate_case), rolls it up (summarize_gates), folds in the model config
(llm.yaml) + EP end-state, and writes both files into the case dir.

It does NOT run the pipeline or any LLM — it records an already-produced run. The
judge② verdicts (the Agent's, in <stage>/attempts/NNN/judge.json) are summarized
if present. Timestamp/orchestrator are passed in (no Date.now in tooling here).

Usage:
    python scripts/tool_scripts/record_baseline.py <case> \
        --base-dir case_tests/e2e_tests --date 2026-06-16 --orchestrator opus-4.8
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.agent.execution import load_state, summarize_gates, validate_case
from src.agent.execution.policy import RunPolicy
from src.agent.judge.verdict import StageVerdict


def _models_from_llm_yaml(case_dir: Path) -> dict:
    """Best-effort read of the per-case model config (which model per stage)."""
    p = case_dir / "llm.yaml"
    if not p.exists():
        return {}
    try:
        from omegaconf import OmegaConf

        cfg = OmegaConf.to_container(OmegaConf.load(p), resolve=False)
    except Exception:  # noqa: BLE001 — config read is best-effort metadata
        return {}
    out = {}
    for key in ("intake_correction", "intake_mep", "default"):
        sec = cfg.get(key) if isinstance(cfg, dict) else None
        if isinstance(sec, dict) and sec.get("model_name"):
            out[key] = sec["model_name"]
    return out


def _ep_end(case_dir: Path) -> dict | None:
    run = case_dir / "EP" / "EP_run"
    if not (run / "eplusout.end").exists():
        return None
    from src.runner.runner import read_ep_end

    end = read_ep_end(run)
    if end is None:
        return None
    return {"completed": end["completed"], "severe": end["severe"],
            "warnings": end["warnings"]}


def _geometry_counts(case_dir: Path) -> dict:
    bg = case_dir / "2_modelling" / "building_geometry.json"
    if not bg.exists():
        return {}
    d = json.loads(bg.read_text())
    return {"zones": len(d.get("zones", [])),
            "surfaces": len(d.get("surfaces", [])),
            "windows": len(d.get("windows", []))}


def _draws_and_verdicts(case_dir: Path) -> tuple[dict, list]:
    """Count append-only attempts per stage + collect judge verdict summaries."""
    draws: dict[str, int] = {}
    verdicts: list[dict] = []
    for stage in ("0_reading", "1_correction", "2_modelling", "3_split_pairing",
                  "4_mep", "5_intakeoutput"):
        adir = case_dir / stage / "attempts"
        if not adir.exists():
            continue
        attempts = [p for p in adir.iterdir() if p.is_dir() and p.name.isdigit()]
        draws[stage] = len(attempts)
        for ap in sorted(attempts):
            jf = ap / "judge.json"
            if jf.exists():
                try:
                    v = json.loads(jf.read_text())
                    blocking = _verdict_blocking(v)
                except Exception:  # noqa: BLE001 — best-effort verdict metadata
                    pass
                else:
                    verdicts.append({"stage": stage, "attempt": int(ap.name),
                                     "blocking": blocking,
                                     "root_stage": v.get("root_stage")})
    return draws, verdicts


def _verdict_blocking(v: dict) -> bool:
    return StageVerdict.model_validate(v).blocking


_AUDIT_KINDS = ("corrections", "conflicts", "unsupported")
_CORRECTION_ROW_KEYS = (
    "id",
    "rule_id",
    "target",
    "source_ids",
    "original_value",
    "resolved_value",
    "delta",
    "changes_topology",
)
_CORRECTION_ROW_CAP = 20


def _empty_corrections_summary(
    sidecar_path: str,
    *,
    present: bool,
    parse_status: str,
    parse_error: str | None = None,
) -> dict:
    summary = {
        "sidecar_path": sidecar_path,
        "present": present,
        "parse_status": parse_status,
        "counts": {kind: 0 for kind in _AUDIT_KINDS},
        "by_rule_id": {},
        "by_stage": {},
        "corrections": {"total": 0, "shown": 0, "cap": _CORRECTION_ROW_CAP, "rows": []},
        "conflicts": [],
        "unsupported": [],
    }
    if parse_error:
        summary["parse_error"] = parse_error
    return summary


def _as_list(obj) -> list:
    return obj if isinstance(obj, list) else []


def _string_count_value(entry: dict, key: str) -> str | None:
    value = entry.get(key)
    if value is None or value == "":
        return None
    return str(value)


def _count_audit_fields(entries: list) -> tuple[dict, dict]:
    by_rule_id: Counter[str] = Counter()
    by_stage: Counter[str] = Counter()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rule_id = _string_count_value(entry, "rule_id")
        stage = _string_count_value(entry, "stage")
        if rule_id:
            by_rule_id[rule_id] += 1
        if stage:
            by_stage[stage] += 1
    return dict(sorted(by_rule_id.items())), dict(sorted(by_stage.items()))


def _summarize_correction_rows(corrections: list, cap: int = _CORRECTION_ROW_CAP) -> dict:
    rows = []
    for entry in corrections[:cap]:
        if isinstance(entry, dict):
            row = {key: entry.get(key) for key in _CORRECTION_ROW_KEYS if key in entry}
        else:
            row = {"value": entry}
        rows.append(row)
    return {"total": len(corrections), "shown": len(rows), "cap": cap, "rows": rows}


def _corrections_summary(run_dir: Path) -> dict:
    """Best-effort read of 1_correction/corrections.json for attribution reporting.

    The sidecar is intentionally heterogeneous: LLM A0 entries are rich dicts,
    deterministic-core entries are narrower, and legacy/bad entries should not make
    baseline recording fail.
    """
    sidecar = run_dir / "1_correction" / "corrections.json"
    rel = sidecar.relative_to(run_dir).as_posix()
    if not sidecar.exists():
        return _empty_corrections_summary(rel, present=False, parse_status="missing")
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — attribution sidecar is best-effort metadata
        return _empty_corrections_summary(
            rel, present=True, parse_status="malformed_json", parse_error=str(e))
    if not isinstance(data, dict):
        return _empty_corrections_summary(
            rel, present=True, parse_status="invalid_shape",
            parse_error="root JSON value is not an object")

    corrections = _as_list(data.get("corrections", []))
    conflicts = _as_list(data.get("conflicts", []))
    unsupported = _as_list(data.get("unsupported", []))
    by_rule_id, by_stage = _count_audit_fields(corrections + conflicts + unsupported)
    return {
        "sidecar_path": rel,
        "present": True,
        "parse_status": "ok",
        "counts": {
            "corrections": len(corrections),
            "conflicts": len(conflicts),
            "unsupported": len(unsupported),
        },
        "by_rule_id": by_rule_id,
        "by_stage": by_stage,
        "corrections": _summarize_correction_rows(corrections),
        "conflicts": conflicts,
        "unsupported": unsupported,
    }


def _eyeball_checklist(
    case_dir: Path, summary: dict, counts: dict, corrections_summary: dict | None = None
) -> list[str]:
    """The 🔍 L-肉眼 list: perceptual items deterministic + judge can't fully
    settle. Always-on items + one per surfaced flag."""
    items = [
        "每层填色区图 `1_correction/*_zones.png` vs 原平面图 —— 房间无错并/错分/缺失/多出"
        "（尤其走廊是否被切断，sm20 那类坑）",
        "立面窗位图 `1_correction/*_elev.png` vs 原立面 —— 窗落在对的立面/楼层/位置",
        "3D 几何 `manual_review/geometry_viewer.html`（浏览器打开：orbit / 半透明 / 截面 / 爆炸 / 量距）"
        " —— 整体体量 + 内部分区 + 窗在对的立面，确认无误后 `approve-geometry`",
    ]
    for f in summary.get("flags", []):
        items.append(
            f"flag [{f['stage']}::{f['check']}] —— {f['message']}（对应渲染件人工核一眼）")
    if corrections_summary:
        c = corrections_summary.get("counts", {})
        conflicts = c.get("conflicts", 0)
        unsupported = c.get("unsupported", 0)
        if conflicts or unsupported:
            items.append(
                "audit-derived [corrections_summary] —— "
                f"`corrections.json` 有 {conflicts} conflicts / {unsupported} unsupported，"
                "人核看错↔改错归因")
    return items


def record_baseline(run_dir: Path, *, date: str, orchestrator: str,
                    require_ep: bool = False) -> dict:
    """Record a self-contained RUN (``<case>/run_<note>/``) as a baseline. The
    case (materials) is the run's parent; products + llm.yaml live in the run."""
    run_dir = Path(run_dir)
    case = run_dir.parent.name
    res = validate_case(run_dir, policy=RunPolicy(require_ep=require_ep),
                        write_reports=True)
    summary = summarize_gates(res.reports)
    counts = _geometry_counts(run_dir)
    draws, verdicts = _draws_and_verdicts(run_dir)
    state = load_state(run_dir)  # stepwise orchestration ledger (stop_reason etc.)
    corr_summary = _corrections_summary(run_dir)
    baseline = {
        "case": case,
        "run": run_dir.name,
        "recorded": date,
        "orchestrator": orchestrator,
        "models": _models_from_llm_yaml(run_dir),
        "geometry": counts,
        "geometry_digest": res.geometry_digest,
        "geometry_approved": res.geometry_approved,
        "gates": summary["gates"],
        "flags": summary["flags"],
        "blocking": summary["blocking"],
        "judge_verdicts": verdicts,
        "draws": draws,
        "orchestration": state.get("stages", {}),
        "stop_reason": state.get("stop_reason"),
        "ep": _ep_end(run_dir),
        "corrections_summary": corr_summary,
        "blocked": res.blocked,
    }
    (run_dir / "baseline.json").write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "RUN_REPORT.md").write_text(
        _render_report(
            baseline, _eyeball_checklist(run_dir, summary, counts, corr_summary)),
        encoding="utf-8")
    return baseline


def _audit_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _render_corrections_audit(summary: dict) -> list[str]:
    lines = ["", "## 校正审计（看错↔改错归因）"]
    path = summary.get("sidecar_path", "1_correction/corrections.json")
    status = summary.get("parse_status", "unknown")
    if not summary.get("present"):
        lines += ["", f"- （无 corrections.json）`{path}`"]
        return lines
    if status != "ok":
        msg = summary.get("parse_error", "")
        lines += ["", f"- `corrections.json` 读取状态: {status}" + (f" — {msg}" if msg else "")]
        return lines

    counts = summary.get("counts", {})
    conflicts = summary.get("conflicts", [])
    unsupported = summary.get("unsupported", [])
    corrections = summary.get("corrections", {})
    rows = corrections.get("rows", [])

    if conflicts:
        lines += ["", "### conflicts[]"]
        lines += [f"- {_audit_json(entry)}" for entry in conflicts]
    if unsupported:
        lines += ["", "### unsupported[]"]
        lines += [f"- {_audit_json(entry)}" for entry in unsupported]
    if rows:
        lines += ["", f"### corrections[]（显示 {corrections.get('shown', len(rows))}/"
                  f"{corrections.get('total', len(rows))}，cap={corrections.get('cap', '?')}）"]
        lines += [f"- {_audit_json(row)}" for row in rows]
    elif not (conflicts or unsupported):
        lines += ["", "- `corrections.json` 存在，但 audit 为空。"]

    lines += [
        "",
        "### count summary",
        f"- sidecar: `{path}` ({status})",
        "- counts: "
        f"corrections={counts.get('corrections', 0)}, "
        f"conflicts={counts.get('conflicts', 0)}, "
        f"unsupported={counts.get('unsupported', 0)}",
        f"- by_rule_id: {_audit_json(summary.get('by_rule_id', {}))}",
        f"- by_stage: {_audit_json(summary.get('by_stage', {}))}",
    ]
    return lines


def _render_report(b: dict, eyeball: list[str]) -> str:
    g = b["geometry"]
    ep = b["ep"]
    stop = b.get("stop_reason")
    if b["blocked"] or stop:
        verdict = f"❌ STOPPED ({stop})" if stop else "❌ BLOCKED"
    else:
        verdict = "✅ clean"
    lines = [
        f"# {b['case']} / {b.get('run','')} 跑批反馈 "
        f"({b['recorded']}, orchestrator={b['orchestrator']})",
        "",
        f"**结论**: {verdict}"
        + (f" / EP {'Completed' if ep and ep['completed'] else 'NOT completed'}, "
           f"{ep['severe']} severe, {ep['warnings']} warn" if ep else " / EP 未跑")
        + (f" / {g.get('zones','?')}区·{g.get('surfaces','?')}面·{g.get('windows','?')}窗"
           if g else ""),
        "",
        f"**模型**: {b['models'] or '(未读到 llm.yaml)'}",
        "",
        "## 逐段 gate①",
        "",
        "| 段 | pass | flag | block | n/a |",
        "|---|---|---|---|---|",
    ]
    for stage, agg in b["gates"].items():
        lines.append(f"| {stage} | {agg['pass']} | {agg['flag']} | {agg['block']} | {agg['na']} |")
    if b.get("orchestration"):
        lines += ["", "## 逐段编排状态（judge-in-the-loop）", "",
                  "| 段 | status | 抽样 |", "|---|---|---|"]
        for stage, st in b["orchestration"].items():
            lines.append(f"| {stage} | {st.get('status','?')} | {st.get('attempts_used','?')} |")
    if b["draws"]:
        lines += ["", f"**抽样次数（attempts/ 落盘）**: {b['draws']}"]
    if b["judge_verdicts"]:
        nblk = sum(1 for v in b["judge_verdicts"] if v.get("blocking"))
        lines += ["", f"**judge② verdicts**: {len(b['judge_verdicts'])} 条"
                  f"（{nblk} 条 blocking；见各 attempts/NNN/judge.json）"]
    if b["blocking"]:
        lines += ["", "## ⛔ blocking"]
        lines += [f"- [{x['stage']}::{x['check']}] {x['message']}" for x in b["blocking"]]
    if b["flags"]:
        lines += ["", "## ⚠️ flags（不阻塞、供归因）"]
        lines += [f"- [{x['stage']}::{x['check']}] {x['message']}" for x in b["flags"]]
    lines += _render_corrections_audit(b.get("corrections_summary", {}))
    lines += ["", "## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）"]
    lines += [f"{i+1}. {it}" for i, it in enumerate(eyeball)]
    lines += ["", f"_附: baseline.json / 各 <stage>_checks.json / geometry_digest={b['geometry_digest']}_"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", help="case name under <base-dir>/")
    ap.add_argument("run", help="run folder name under <case>/ (e.g. run_2026-06-16_opus)")
    ap.add_argument("--base-dir", default="case_tests/e2e_tests")
    ap.add_argument("--date", required=True, help="ISO date of the run (no Date.now in tooling)")
    ap.add_argument("--orchestrator", required=True, help="main Agent model id, e.g. opus-4.8")
    ap.add_argument("--require-ep", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.base_dir) / args.case / args.run
    b = record_baseline(run_dir, date=args.date, orchestrator=args.orchestrator,
                        require_ep=args.require_ep)
    print(f"wrote {run_dir/'baseline.json'} + RUN_REPORT.md  (blocked={b['blocked']})")


if __name__ == "__main__":
    main()
