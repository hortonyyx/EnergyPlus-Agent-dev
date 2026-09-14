"""Audit profile references in one completed local observation and render them.

This script performs only mechanical provenance and coverage checks.  It does
not decide whether an assessment is visually or semantically correct, and it
does not create or modify BIM geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from PIL import Image


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_observation(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, object]] = []
    for start, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, length = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        candidates.append((start, start + length, value))
    maximal = [
        row for row in candidates
        if not any(other[0] <= row[0] and row[1] <= other[1] and other != row
                   for other in candidates)
    ]
    if len(maximal) != 1 or not isinstance(maximal[0][2], dict):
        raise ValueError(
            f"observation.md must contain one top-level JSON object; found {len(maximal)}"
        )
    return maximal[0][2]


def _profile_name(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        return None
    parts = list(path.parts)
    if parts and parts[0] == "detail_01":
        parts.pop(0)
    if len(parts) != 2 or parts[0] != "pixel_profiles" or not parts[1].endswith(".json"):
        return None
    return "/".join(parts)


def _line(axis: object, peak: object, interval: object) -> list[list[float]] | None:
    if axis not in {"x", "y"}:
        return None
    if (isinstance(peak, bool) or not isinstance(peak, (int, float))
            or not math.isfinite(float(peak))):
        return None
    if (not isinstance(interval, list) or len(interval) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(float(value)) for value in interval)):
        return None
    lo, hi = float(interval[0]), float(interval[1])
    if lo > hi:
        return None
    peak = float(peak)
    return [[peak, lo], [peak, hi]] if axis == "x" else [[lo, peak], [hi, peak]]


def _url(from_dir: Path, target: Path) -> str:
    return quote(os.path.relpath(target, from_dir).replace(os.sep, "/"), safe="/")


def audit(run: Path, out: Path) -> dict:
    run = run.resolve()
    out = out.resolve()
    detail = run / "detail_01"
    observation_path = run / "observation.md"
    observation = _load_observation(observation_path)
    inputs = json.loads((detail / "inputs.json").read_text(encoding="utf-8"))
    image_name = observation.get("image")
    if not isinstance(image_name, str) or not image_name:
        raise ValueError("observation.image must be a nonempty string")
    if PurePosixPath(image_name).name != image_name or image_name not in inputs.get("images", {}):
        raise ValueError("observation.image must be an exact filename from detail_01/inputs.json")
    image_path = detail / "images" / image_name
    if not image_path.is_file():
        raise ValueError(f"observation image is absent from detail_01/images: {image_name}")
    image_sha = _sha256(image_path)
    with Image.open(image_path) as source_image:
        image_size = list(source_image.size)

    profile_issues: list[dict] = []
    input_image = inputs.get("images", {}).get(image_name, {})
    if input_image.get("sha256") != image_sha:
        profile_issues.append({
            "profile_record": None,
            "reason": "detail input manifest image hash does not match actual original image",
            "declared": input_image.get("sha256"), "actual": image_sha,
        })
    if input_image.get("size") != image_size:
        profile_issues.append({
            "profile_record": None,
            "reason": "detail input manifest image size does not match actual original image",
            "declared": input_image.get("size"), "actual": image_size,
        })

    profiles: dict[str, dict] = {}
    inventory: dict[tuple[str, str], dict] = {}
    profile_rows = []
    for path in sorted((detail / "pixel_profiles").glob("*.json")):
        canonical = path.relative_to(detail).as_posix()
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            profile_issues.append({"profile_record": canonical, "reason": f"cannot read JSON: {error}"})
            continue
        if not isinstance(record, dict):
            profile_issues.append({"profile_record": canonical, "reason": "profile JSON is not an object"})
            continue
        profiles[canonical] = record
        declared_name = _profile_name(record.get("profile_record"))
        if declared_name != canonical:
            profile_issues.append({
                "profile_record": canonical,
                "reason": "record profile_record does not identify its actual file",
                "declared": record.get("profile_record"),
            })
        if record.get("name") != image_name:
            profile_issues.append({
                "profile_record": canonical, "reason": "profile names a different original image",
                "declared": record.get("name"), "observation_image": image_name,
            })
        if record.get("image_sha256") != image_sha:
            profile_issues.append({
                "profile_record": canonical, "reason": "profile original-image hash mismatch",
                "declared": record.get("image_sha256"), "actual": image_sha,
            })
        candidates = record.get("candidates")
        if not isinstance(candidates, list):
            profile_issues.append({"profile_record": canonical, "reason": "candidates is not a list"})
            candidates = []
        for candidate_index, candidate in enumerate(candidates):
            candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
            if not isinstance(candidate_id, str) or not candidate_id:
                profile_issues.append({
                    "profile_record": canonical,
                    "reason": f"candidate[{candidate_index}] has no valid id",
                })
                continue
            key = (canonical, candidate_id)
            if key in inventory:
                profile_issues.append({
                    "profile_record": canonical, "candidate_id": candidate_id,
                    "reason": "duplicate candidate id in profile",
                })
                continue
            intervals = candidate.get("support_intervals_at_peak")
            if not isinstance(intervals, list):
                profile_issues.append({
                    "profile_record": canonical, "candidate_id": candidate_id,
                    "reason": "support_intervals_at_peak is not a list",
                })
                intervals = []
            inventory[key] = {
                "profile_record": canonical, "candidate_id": candidate_id,
                "axis": record.get("axis"), "peak": candidate.get("peak"),
                "intervals": intervals,
            }
        profile_rows.append({
            "profile_record": canonical,
            "record_sha256": _sha256(path),
            "declared_profile_record": record.get("profile_record"),
            "image_sha256": record.get("image_sha256"),
            "image_hash_matches_actual": record.get("image_sha256") == image_sha,
            "axis": record.get("axis"),
            "candidate_count": len(candidates),
            "profile_image": record.get("profile_image"),
        })

    assessments = observation.get("assessments")
    if not isinstance(assessments, list):
        raise ValueError("observation.assessments must be a list")
    bad_references: list[dict] = []
    support_by_assessment = []
    candidate_coverage: dict[tuple[str, str], list[dict]] = {key: [] for key in inventory}
    interval_coverage: dict[tuple[str, str, int], list[dict]] = {}
    for assessment_index, assessment in enumerate(assessments):
        assessment_id = (assessment.get("id") if isinstance(assessment, dict) else None)
        if not isinstance(assessment_id, str) or not assessment_id:
            assessment_id = f"assessment[{assessment_index}]"
        supports = []
        refs = assessment.get("refs") if isinstance(assessment, dict) else None
        if not isinstance(refs, list):
            bad_references.append({
                "assessment_id": assessment_id, "ref_index": None,
                "reference": refs, "reasons": ["refs must be a list"],
            })
            refs = []
        for ref_index, ref in enumerate(refs):
            reasons = []
            if not isinstance(ref, dict):
                bad_references.append({
                    "assessment_id": assessment_id, "ref_index": ref_index,
                    "reference": ref, "reasons": ["reference must be an object"],
                })
                continue
            canonical = _profile_name(ref.get("profile_record"))
            if canonical is None:
                reasons.append("profile_record is not detail_01/pixel_profiles/*.json")
            elif canonical not in profiles:
                reasons.append("profile_record does not exist in this run")
            elif _profile_name(profiles[canonical].get("profile_record")) != canonical:
                reasons.append("profile_record points to a file whose self-declared profile_record differs")
            candidate_id = ref.get("candidate_id")
            key = None
            if not isinstance(candidate_id, str) or not candidate_id:
                reasons.append("candidate_id must be a nonempty string")
                candidate = None
            else:
                key = (canonical, candidate_id)
                candidate = inventory.get(key)
            if candidate is None and canonical in profiles and isinstance(candidate_id, str):
                reasons.append("candidate_id does not exist in the referenced profile")
            raw_indices = ref.get("interval_indices")
            if not isinstance(raw_indices, list) or not raw_indices:
                reasons.append("interval_indices must be a nonempty list")
                raw_indices = []
            elif any(isinstance(index, bool) or not isinstance(index, int) for index in raw_indices):
                reasons.append("interval_indices entries must be integers")
            duplicate_indices = sorted({index for index in raw_indices if raw_indices.count(index) > 1
                                        and isinstance(index, int) and not isinstance(index, bool)})
            if duplicate_indices:
                reasons.append(f"interval_indices repeats {duplicate_indices}")
            valid_indices = []
            if candidate is not None:
                for index in raw_indices:
                    if isinstance(index, bool) or not isinstance(index, int):
                        continue
                    if index < 0 or index >= len(candidate["intervals"]):
                        reasons.append(f"interval index {index} is outside available range")
                        continue
                    actual_line = _line(candidate["axis"], candidate["peak"],
                                        candidate["intervals"][index])
                    if actual_line is None:
                        reasons.append(f"interval index {index} or its peak/axis is malformed")
                        continue
                    valid_indices.append(index)
                    support = {
                        "profile_record": canonical, "candidate_id": candidate_id,
                        "interval_index": index, "axis": candidate["axis"],
                        "peak": candidate["peak"],
                        "support_interval_at_peak": candidate["intervals"][index],
                        "line_original_pixels": actual_line,
                    }
                    supports.append(support)
                    interval_coverage.setdefault((canonical, candidate_id, index), []).append({
                        "assessment_id": assessment_id, "ref_index": ref_index,
                    })
                if valid_indices:
                    candidate_coverage[key].append({
                        "assessment_id": assessment_id, "ref_index": ref_index,
                        "interval_indices": valid_indices,
                    })
            if reasons:
                bad_references.append({
                    "assessment_id": assessment_id, "ref_index": ref_index,
                    "reference": ref, "reasons": list(dict.fromkeys(reasons)),
                })
        support_by_assessment.append({
            "assessment_index": assessment_index, "assessment_id": assessment_id,
            "support_lines": supports,
        })

    uncovered_candidates = [
        {**inventory[key], "available_interval_indices": list(range(len(inventory[key]["intervals"])))}
        for key, coverage in candidate_coverage.items() if not coverage
    ]
    duplicate_candidates = [
        {"profile_record": key[0], "candidate_id": key[1], "references": coverage}
        for key, coverage in candidate_coverage.items() if len(coverage) > 1
    ]
    uncovered_intervals = []
    for key, candidate in inventory.items():
        for index, interval in enumerate(candidate["intervals"]):
            if (key[0], key[1], index) not in interval_coverage:
                uncovered_intervals.append({
                    "profile_record": key[0], "candidate_id": key[1],
                    "interval_index": index, "support_interval_at_peak": interval,
                })
    duplicate_intervals = [
        {"profile_record": key[0], "candidate_id": key[1], "interval_index": key[2],
         "references": coverage}
        for key, coverage in interval_coverage.items() if len(coverage) > 1
    ]

    audit_data = {
        "schema_version": "profile_reference_audit_v1",
        "mode": "mechanical_reference_audit_only",
        "run": str(run),
        "observation_file": str(observation_path),
        "observation_sha256": _sha256(observation_path),
        "semantic_or_visual_fidelity_judgment": "not_performed",
        "source_bim": False,
        "automatic_wall_certification": False,
        "original_image": {
            "name": image_name, "file": str(image_path), "sha256": image_sha,
            "size": image_size, "detail_manifest_sha256": input_image.get("sha256"),
        },
        "scope_box_from_observation": observation.get("scope_box"),
        "profiles": profile_rows,
        "counts": {
            "profiles": len(profile_rows), "candidates": len(inventory),
            "assessments": len(assessments),
            "resolved_support_line_references": sum(
                len(row["support_lines"]) for row in support_by_assessment),
            "uncovered_candidates": len(uncovered_candidates),
            "uncovered_intervals": len(uncovered_intervals),
            "duplicate_candidate_coverage": len(duplicate_candidates),
            "duplicate_interval_coverage": len(duplicate_intervals),
            "bad_references": len(bad_references),
            "profile_or_image_issues": len(profile_issues),
        },
        "uncovered_candidates": uncovered_candidates,
        "uncovered_intervals": uncovered_intervals,
        "duplicate_candidate_coverage": duplicate_candidates,
        "duplicate_interval_coverage": duplicate_intervals,
        "bad_references": bad_references,
        "profile_or_image_issues": profile_issues,
        "assessment_support": support_by_assessment,
        "limitations": [
            "Coverage means only that an answer cited an existing measured candidate/interval.",
            "No object, relation, gap explanation, wall identity, room division, or drawing fidelity was automatically accepted.",
            "Every SVG segment is one actual support_intervals_at_peak interval; disjoint intervals are not connected.",
            "The script does not join walls, repair coordinates, infer missing supports, or create source geometry.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "observation.json").write_text(
        json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "reference_audit.json").write_text(
        json.dumps(audit_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_html(out, run, observation_path, image_path, image_size, observation,
                profile_rows, audit_data)
    return audit_data


def _write_html(
    out: Path,
    run: Path,
    observation_path: Path,
    image_path: Path,
    image_size: list[int],
    observation: dict,
    profiles: list[dict],
    audit_data: dict,
) -> None:
    palette = ["#e60049", "#0bb4ff", "#50e991", "#e6d800", "#9b19f5",
               "#ffa300", "#dc0ab4", "#b3d4ff", "#00bfa0", "#f46a4e"]
    support_by_index = {
        row["assessment_index"]: row["support_lines"]
        for row in audit_data["assessment_support"]
    }
    buttons = []
    svg_groups = []
    table_rows = []
    assessments = observation["assessments"]
    for index, assessment in enumerate(assessments):
        assessment = assessment if isinstance(assessment, dict) else {}
        assessment_id = str(assessment.get("id", f"assessment[{index}]"))
        color = palette[index % len(palette)]
        group_id = f"assessment-{index}"
        buttons.append(
            f'<button class="active" data-target="{group_id}" '
            f'style="--c:{color}">{html.escape(assessment_id)}</button>')
        lines = []
        reference_text = []
        for support in support_by_index.get(index, []):
            (x1, y1), (x2, y2) = support["line_original_pixels"]
            lines.append(
                f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
                f'stroke="{color}" stroke-width="5" vector-effect="non-scaling-stroke" '
                f'stroke-linecap="butt"><title>{html.escape(assessment_id)} · '
                f'{html.escape(support["profile_record"])} / '
                f'{html.escape(support["candidate_id"])} / interval '
                f'{support["interval_index"]}</title></line>')
            reference_text.append(
                f'{support["profile_record"]} {support["candidate_id"]}'
                f'[{support["interval_index"]}]={support["support_interval_at_peak"]}')
        svg_groups.append(f'<g id="{group_id}">{"".join(lines)}</g>')
        table_rows.append(
            f'<tr data-target="{group_id}"><td><span class="swatch" '
            f'style="background:{color}"></span>{html.escape(assessment_id)}</td>'
            f'<td>{html.escape(str(assessment.get("object", "")))}</td>'
            f'<td>{html.escape(str(assessment.get("relation", "")))}</td>'
            f'<td>{html.escape(str(assessment.get("evidence", "")))}</td>'
            f'<td>{html.escape(str(assessment.get("gaps", "")))}</td>'
            f'<td>{html.escape("; ".join(reference_text) or "无可解析支持线")}</td></tr>')
    scope = observation.get("scope_box")
    scope_rect = ""
    if (isinstance(scope, list) and len(scope) == 4
            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    for value in scope)):
        x0, y0, x1, y1 = scope
        scope_rect = (f'<rect x="{x0:g}" y="{y0:g}" width="{x1-x0:g}" height="{y1-y0:g}" '
                      'fill="none" stroke="#111" stroke-width="2" stroke-dasharray="8 6" '
                      'vector-effect="non-scaling-stroke"><title>observation scope_box</title></rect>')
    preview_links = []
    for row in profiles[:2]:
        profile_image = row.get("profile_image")
        if isinstance(profile_image, str):
            target = run / "detail_01" / profile_image
            preview_links.append(
                f'<a href="{_url(out, target)}">{html.escape(Path(profile_image).name)}</a>')
    counts = audit_data["counts"]
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Profile 引用审计</title>
<style>
body{{font:15px/1.55 system-ui,sans-serif;max-width:1500px;margin:24px auto;padding:0 18px;color:#202124}}
.notice{{background:#fff3cd;border:1px solid #e5c365;padding:12px}} .stage{{position:relative;width:min(100%,790px)}}
.stage img{{display:block;width:100%;height:auto}} .stage svg{{position:absolute;inset:0;width:100%;height:100%}}
.controls{{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}} button{{border:2px solid var(--c);background:white;padding:5px 9px;cursor:pointer}}
button.active{{background:var(--c);color:#111}} table{{border-collapse:collapse;width:100%;margin-top:18px}}
th,td{{border:1px solid #bbb;padding:7px;vertical-align:top;text-align:left}} th{{position:sticky;top:0;background:#f4f4f4}}
.swatch{{display:inline-block;width:10px;height:10px;margin-right:6px}} code{{white-space:nowrap}}
</style></head><body>
<h1>候选观察的 profile 引用审计</h1>
<p class="notice"><strong>只读机械审计：</strong>此页只确认答复是否引用了本 run 中真实存在的 profile、C## 和原始支持区间。它不是 BIM，不自动认证任何墙、空间关系、缺口解释或图纸保真度。</p>
<p>候选 {counts['candidates']}；未覆盖候选 {counts['uncovered_candidates']}；未覆盖区间 {counts['uncovered_intervals']}；重复候选覆盖 {counts['duplicate_candidate_coverage']}；重复区间覆盖 {counts['duplicate_interval_coverage']}；坏引用 {counts['bad_references']}；profile/原图问题 {counts['profile_or_image_issues']}。</p>
<p><a href="reference_audit.json">完整引用审计 JSON</a> · <a href="observation.json">提取的原答 JSON</a> · <a href="{_url(out, observation_path)}">原答复</a> · {' · '.join(preview_links)}</p>
<p>每条彩线都是 profile 在 peak 位置记录的一段实际 support interval。断开的区间始终是独立 SVG line，没有连接或补齐。</p>
<div class="controls"><button id="show-all">全部显示</button><button id="hide-all">全部隐藏</button>{''.join(buttons)}</div>
<div class="stage"><img src="{_url(out, image_path)}" alt="原始平面图"><svg viewBox="0 0 {image_size[0]} {image_size[1]}" preserveAspectRatio="none">{scope_rect}{''.join(svg_groups)}</svg></div>
<table><thead><tr><th>assessment</th><th>object（原答复）</th><th>relation（原答复）</th><th>evidence（原答复）</th><th>gaps（原答复）</th><th>实际引用支持</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table>
<script>
const toggle=(button,on)=>{{document.getElementById(button.dataset.target).style.display=on?'':'none';button.classList.toggle('active',on)}};
document.querySelectorAll('button[data-target]').forEach(button=>button.onclick=()=>toggle(button,!button.classList.contains('active')));
document.querySelectorAll('tr[data-target]').forEach(row=>row.onclick=()=>{{const button=document.querySelector(`button[data-target="${{row.dataset.target}}"]`);toggle(button,!button.classList.contains('active'))}});
document.getElementById('show-all').onclick=()=>document.querySelectorAll('button[data-target]').forEach(button=>toggle(button,true));
document.getElementById('hide-all').onclick=()=>document.querySelectorAll('button[data-target]').forEach(button=>toggle(button,false));
</script></body></html>'''
    (out / "index.html").write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed observation run")
    parser.add_argument("--out", type=Path,
                        help="output directory (default: the observation run itself)")
    args = parser.parse_args()
    result = audit(args.run, args.out or args.run)
    print(json.dumps(result["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
