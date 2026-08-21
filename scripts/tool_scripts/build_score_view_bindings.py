#!/usr/bin/env python3
"""Build the judge-owned ``_run/judge_score_bindings.json`` for a v3 case.

⭐ 2026-08-21：此前**全仓没有任何生成器** —— sm24 那份是手工产的，于是 sm25（第二个 v3
答案）一跑判卷就撞上「required judge sidecar(s) are missing ⇒ v3 scoring layer was skipped」，
**权威判卷被静默跳过**。本工具把这条路补成确定性的：每个字段都从 gt + run 的
``view_manifest.json`` 推导，⛔ 不手抄、不猜。

平面绑定已完整支持。⚠️ 立面绑定尚未实现（需要 frame transform / along_origin / 镜像约定），
遇到时**响亮报错**而不是静默产出半份文件。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agent.execution.view_manifest import ViewManifest
from src.agent.judge.score_schema import (JudgeScoreViewBindingsV1, hash_model_without,
                                          load_score_gt_identity)


def build(run_dir: Path, gt_file: Path, input_ids: set[str] | None) -> JudgeScoreViewBindingsV1:
    base = ViewManifest.model_validate_json((run_dir / "_run" / "view_manifest.json").read_text(encoding="utf-8"))
    identity, gt = load_score_gt_identity(gt_file)
    if gt is None:
        raise SystemExit("gt is not a scorable c2 v3 document")

    gt_views = {view.id: view for source in gt.sources for view in source.views}
    plan_view_for_floor: dict[str, list[str]] = {}
    for view_id, view in sorted(gt_views.items()):
        # GT plan views carry ``floor_ids`` (a list with exactly one entry), not ``floor_id``.
        floor_ids = list(getattr(view, "floor_ids", ()) or ())
        if view.kind == "plan":
            if len(floor_ids) != 1:
                raise SystemExit(f"plan view {view_id!r} must name exactly one floor, got {floor_ids}")
            plan_view_for_floor.setdefault(floor_ids[0], []).append(view_id)

    required = [entry for entry in base.required_entries() if entry.view_type in {"plan", "elevation"}]
    if input_ids is not None:
        required = [entry for entry in required if entry.input_id in input_ids]
        missing = input_ids - {entry.input_id for entry in required}
        if missing:
            raise SystemExit(f"input ids not required by the view manifest: {sorted(missing)}")

    bindings = []
    for entry in required:
        if entry.view_type != "plan":
            raise SystemExit(
                f"{entry.input_id}: elevation bindings are not derivable yet "
                "(frame transform / along_origin / mirror convention) — build them for the "
                "elevation batch, ⛔ do not hand-author a partial file")
        floor_id = _floor_for_plan(entry.input_id, plan_view_for_floor, gt)
        bindings.append({"kind": "plan", "input_id": entry.input_id, "floor_id": floor_id,
                         "gt_source_view_ids": tuple(plan_view_for_floor[floor_id])})

    payload = {"schema_version": "1", "case_id": base.case_id,
               "gt_content_sha256": identity.content_sha256,
               "case_metadata_sha256": base.case_metadata_sha256,
               "base_view_manifest_sha256": base.content_sha256,
               "bindings": tuple(bindings), "content_sha256": "0" * 64}
    draft = JudgeScoreViewBindingsV1.model_construct(**payload)
    payload["content_sha256"] = hash_model_without(draft, "content_sha256")
    return JudgeScoreViewBindingsV1.model_validate(payload)


def _floor_for_plan(input_id: str, plan_view_for_floor: dict[str, list[str]], gt) -> str:
    """Bind a plan input to its GT floor by the drawing's own floor ordering.

    The manifest's plan entries and the GT's floors are both in declaration order,
    so the n-th plan input is the n-th floor.  Any mismatch in count is a hard error
    rather than a guess.
    """
    floors = [floor.id for floor in gt.floors if floor.id in plan_view_for_floor]
    plans = sorted(plan_view_for_floor)
    if len(floors) != len(plans):
        raise SystemExit("gt floors and gt plan views do not correspond one-to-one")
    if input_id not in _PLAN_INPUT_ORDER:
        raise SystemExit(f"cannot bind plan input {input_id!r} to a floor; extend _PLAN_INPUT_ORDER")
    index = _PLAN_INPUT_ORDER[input_id]
    if index >= len(floors):
        raise SystemExit(f"plan input {input_id!r} has no matching gt floor")
    return floors[index]


#: 平面输入名 → 楼层序号。天正/本项目约定：``1f_view`` = 第 1 层，依此类推。
_PLAN_INPUT_ORDER = {f"{n}f_view": n - 1 for n in range(1, 21)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--input-ids", nargs="*", default=None,
                    help="restrict to these inputs (default: every required plan/elevation entry)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    result = build(args.run_dir, args.gt, set(args.input_ids) if args.input_ids else None)
    out = args.out or (args.run_dir / "_run" / "judge_score_bindings.json")
    out.write_text(json.dumps(result.model_dump(mode="json"), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "content_sha256": result.content_sha256,
                      "bindings": [b.input_id for b in result.bindings]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
