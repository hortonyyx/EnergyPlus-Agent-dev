"""R1 修尺子 · 批 B 验收锁（S-2 EffectiveRunPolicy 冻结 + S-3 dimensioned
applicability fail-closed）.

施工 = GLM · 2026-08-03 · 上游 = 派工单 + orchestrator 裁定。

每条锁对应一个主 mutation：摘掉其唯一对应的实现改动，跑同一组锁，记录
"恰好红哪一条 / 有无连带"。锁绿 ≠ 锁真绑。

⛔ 不碰真实 sm24/sm21 manifest 字节（裁定 §2 附带边界）：真实 case 的
``content_sha256`` 必须逐字节不变 —— ``test_real_manifests_byte_identical``
是贯穿全批的保哈希铁律守卫，任何 S-3 wire 改动打穿它即整批作废。
"""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest

from src.agent.execution.isolation import build_isolation_workspace, merge_isolated_output
from src.agent.execution.manifest import RunManifestV2, ensure_run_manifest_v2, load_run_manifest
from src.agent.execution.run_policy_freeze import (
    provision_run_policy,
    resolve_frozen_run_policy,
)
from src.agent.execution.run_provision import (
    provision_run,
    validate_dimensioned_applicability,
)
from src.agent.execution.view_manifest import (
    DimensionedApplicability,
    build_view_manifest,
    dimensioned_state,
    provision_view_manifest,
)
from src.validator.checks.schema import CheckReport
from src.validator.checks.view_manifest import check_reading_stage

SM24 = Path("case_tests/e2e_tests/sm24_anchor")
SM21 = Path("case_tests/e2e_tests/sm21_anchor")
SM24_MANIFEST_SHA = "459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a"
SM21_MANIFEST_SHA = "f52ca79c1bcacaf8fccc9436e165b4bfdc08814ec770370dd1acefd76b6e493e"

_USABLE_ORIGIN = {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _case_copy(tmp_path: Path, src: Path) -> Path:
    # keep the original directory name so case_id (derived from it) is identical
    # — content_sha256 must match the checked-in manifest byte-for-byte.
    dest = tmp_path / src.name
    shutil.copytree(src, dest)
    return dest


def _structured_dim_decl(view: str, dim_flag: bool, reviewer: str = "hortonyyx") -> dict:
    """One structured dimensioned_views entry with provenance (裁定 §3 输入侧)."""
    return {
        "view": view,
        "dimensioned": dim_flag,
        "source": {
            "image_sha256": "0" * 64,
            "reviewer": reviewer,
            "date": "2026-08-02",
            "basis": "closed dimension-chain verification",
        },
    }


def _set_structured_dim(case_dir: Path, declarations: list[dict]) -> None:
    tp = case_dir / "case_data/testdata_prompt.json"
    data = json.loads(tp.read_text(encoding="utf-8"))
    data["dimensioned_views"] = declarations
    tp.write_text(json.dumps(data), encoding="utf-8")


def _plan_with_dims(*, overall=5.0, segments=None, chain_id="c", axis="x") -> dict:
    """A plan view payload whose only dimension-relevant variable is whether the
    chain closes (overall == Σ segments). Strokes carry full provenance +
    a usable scale_origin so no other check refuses — a refusal here can only
    come from the dimension checks."""
    if segments is None:
        segments = [2.0, 3.0]
    dims = [{
        "id": "D0", "text_verbatim": str(overall), "value_m": overall,
        "chain_id": chain_id, "role": "overall", "order": 0, "axis": axis,
        "from": [0, 0], "to": [overall if axis == "x" else 0, overall if axis == "y" else 0],
    }]
    running = 0.0
    for idx, value in enumerate(segments, start=1):
        start = running
        running += value
        dims.append({
            "id": f"D{idx}", "text_verbatim": str(value), "value_m": value,
            "chain_id": chain_id, "role": "segment", "order": idx, "axis": axis,
            "from": [start if axis == "x" else 0, start if axis == "y" else 0],
            "to": [running if axis == "x" else 0, running if axis == "y" else 0],
        })
    return {
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 8], "p2": [10, 8]}},
        ],
        "dimensions": dims,
        "scale_origin": dict(_USABLE_ORIGIN),
    }


def _result_map(rep) -> dict[str, dict]:
    """check_id -> {status, evidence} for assertion convenience."""
    return {r.check_id: {"status": r.status, "evidence": r.evidence} for r in rep.results}


# --------------------------------------------------------------------------- #
# 贯穿全批的保哈希铁律守卫
# --------------------------------------------------------------------------- #
def test_real_manifests_byte_identical():
    """S-3 wire 升级必须保哈希：真实 sm24/sm21 的 content_sha256 逐字节不变
    (sm24 = GT 侧车冻结的 base_view_manifest_sha256，打穿即摧毁评分信任链)。"""
    assert build_view_manifest(SM24).content_sha256 == SM24_MANIFEST_SHA
    assert build_view_manifest(SM21).content_sha256 == SM21_MANIFEST_SHA


# --------------------------------------------------------------------------- #
# L-13 · missing strict run_profile ⇒ provisioning fail-closed
# --------------------------------------------------------------------------- #
def test_L13_missing_strict_run_profile_fails_closed(tmp_path: Path):
    """摘掉 provision_run_policy 的 run_profile=None ⇒ raise（L-13）即整批 S-2
    fail-closed 契约。一个新 run 不得静默默认 exploratory。"""
    case_dir = _case_copy(tmp_path, SM21)
    run_dir = case_dir / "run_x"
    run_dir.mkdir()
    # a NEW provisioning that fails to declare its tier must fail closed
    with pytest.raises(ValueError, match="run_profile_not_declared"):
        provision_run(case_dir, run_dir, run_profile=None, capability_profile="rectangular")
    # and must NOT have written a frozen record (no silent exploratory default)
    assert not (run_dir / "_run/run_policy.json").exists()


def test_L13_declared_strict_run_profile_provisions(tmp_path: Path):
    """对照：声明了 run_profile 的新 run 正常冻结（证明 L-13 是缺声明才 fail，
    不是一切 strict 都 fail）。"""
    case_dir = _case_copy(tmp_path, SM21)
    run_dir = case_dir / "run_ok"
    run_dir.mkdir()
    manifest = provision_run(
        case_dir, run_dir, run_profile="regression", capability_profile="orthogonal_polygon",
    )
    record = resolve_frozen_run_policy(run_dir)
    assert record.run_profile == "regression"
    assert record.capability_profile == "orthogonal_polygon"
    assert not record.legacy_defaulted
    # manifest bytes unaffected by the policy freeze
    assert manifest.content_sha256 == SM21_MANIFEST_SHA


# --------------------------------------------------------------------------- #
# L-20 · dimensioned applicability unknown ⇒ strict provisioning fail-closed
# --------------------------------------------------------------------------- #
def test_L20_dimensioned_applicability_unknown_strict_fails(tmp_path: Path):
    """一个用了结构化 dimensioned_views 声明但漏掉某 required view 的 case，
    在 strict run 下 provisioning 必须 fail-closed（不得落一个把漏掉的 view
    静默压成 False 的 manifest）。"""
    case_dir = _case_copy(tmp_path, SM21)
    # structured declaration covering only ONE of sm21's six required views
    _set_structured_dim(case_dir, [_structured_dim_decl("1f_view", True)])
    run_dir = case_dir / "run_strict"
    run_dir.mkdir()
    with pytest.raises(ValueError, match="dimensioned_applicability_unknown"):
        provision_run(case_dir, run_dir, run_profile="regression", capability_profile="rectangular")


def test_L20_legacy_case_strict_run_does_not_fail(tmp_path: Path):
    """对照：legacy case（absent / stem-string dimensioned_views，bool manifest）
    跑 strict 不触发 L-20 —— legacy 只读不 fail（G-6）。这是 sm24 现状能在
    strict 下保持（五图 dimensioned=false 的 N/A）的原因，直到 R2 写真值。"""
    case_dir = _case_copy(tmp_path, SM24)
    run_dir = case_dir / "run_strict"
    run_dir.mkdir()
    manifest = provision_run(case_dir, run_dir, run_profile="regression", capability_profile="rectangular")
    assert manifest.content_sha256 == SM24_MANIFEST_SHA  # legacy bool manifest untouched


def test_L20_structured_complete_strict_run_succeeds(tmp_path: Path):
    """对照：结构化声明覆盖每个 required view ⇒ strict provisioning 成功。"""
    case_dir = _case_copy(tmp_path, SM24)
    views = ["1f_view", "South_view", "North_view", "East_view", "West_view"]
    _set_structured_dim(case_dir, [_structured_dim_decl(v, True) for v in views])
    run_dir = case_dir / "run_strict"
    run_dir.mkdir()
    manifest = provision_run(case_dir, run_dir, run_profile="regression", capability_profile="rectangular")
    # every required view now carries a structured declared_true applicability
    for e in manifest.required_entries():
        assert dimensioned_state(e.dimensioned) == "declared_true"


# --------------------------------------------------------------------------- #
# L-22 · product cannot set the exam (dimensioned is a trusted property)
# --------------------------------------------------------------------------- #
def test_L22_product_cannot_set_exam_dimensioned():
    """``dimensioned`` 是考卷属性（trusted manifest），不许从产品的 dimensions[]
    非空反推：固定 declared_true，分别给非空 / 空 dimensions[] 的两个产品 ——
    applicability 不变（都 declared_true），空数组使 dimensions_present FAIL
    （不是 N/A），证明产品内容决定不了考卷。"""
    from src.agent.reading import ReadingView
    from src.validator.checks.reading import check_reading_view
    from src.validator.checks.schema import CheckStatus

    wall = [{"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}}]
    base = {"image_kind": "plan", "uncaptured": [], "scale_origin": dict(_USABLE_ORIGIN)}
    view_full = ReadingView.model_validate({**base, "strokes": wall,
                                            "dimensions": _plan_with_dims()["dimensions"]})
    view_empty = ReadingView.model_validate({**base, "strokes": wall, "dimensions": []})

    rep_full = check_reading_view(view_full, dimensioned_state="declared_true", run_profile="regression")
    rep_empty = check_reading_view(view_empty, dimensioned_state="declared_true", run_profile="regression")

    def _dp(rep):
        return next(r for r in rep.results if r.check_id == "reading.dimensions_present")

    # applicability is identical: trusted, not derived from the product's dimensions[]
    assert _dp(rep_full).evidence["dimensioned_state"] == "declared_true"
    assert _dp(rep_empty).evidence["dimensioned_state"] == "declared_true"
    # full dimensions[] ⇒ PASS; empty ⇒ FAIL "empty dimensions[]" (NOT not_applicable)
    assert _dp(rep_full).status is CheckStatus.PASS
    assert _dp(rep_empty).status is CheckStatus.FAIL
    assert "empty dimensions" in _dp(rep_empty).message


# --------------------------------------------------------------------------- #
# L-23 · truly un-dimensioned N/A + the unknown/declared_false/legacy split
# --------------------------------------------------------------------------- #
def test_L23_truly_un_dimensioned_is_na_with_source_hash():
    """trusted declared_false 的无尺寸 view：dimensions_present 与
    dimension_p1a_fields 都是 N/A，带 dimensioned_state + source-derived reason，
    不阻断。"""
    from src.agent.reading import ReadingView
    from src.validator.checks.reading import check_reading_view
    from src.validator.checks.schema import CheckStatus

    view = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
                     "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}}],
        "dimensions": [],
        "scale_origin": dict(_USABLE_ORIGIN),
    })
    rep = check_reading_view(view, dimensioned_state="declared_false", run_profile="regression")
    dp = next(r for r in rep.results if r.check_id == "reading.dimensions_present")
    p1a = next(r for r in rep.results if r.check_id == "reading.dimension_p1a_fields")
    assert dp.status is CheckStatus.NOT_APPLICABLE
    assert p1a.status is CheckStatus.NOT_APPLICABLE
    assert dp.evidence["dimensioned_state"] == "declared_false"
    assert "declared not dimensioned" in dp.message
    # not_applicable never blocks even under regression
    assert rep.passed


def test_L23_unknown_vs_declared_false_never_folded():
    """追加约束 #1：unknown / declared_false / legacy_default 三态必须一路保留到
    checks.json evidence，不得在任何层折回 bool。同一空 view 在三态下产出三组
    不同的 (message, dimensioned_state)。"""
    from src.agent.reading import ReadingView
    from src.validator.checks.reading import check_reading_view

    view = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
                     "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}}],
        "dimensions": [],
        "scale_origin": dict(_USABLE_ORIGIN),
    })
    seen = {}
    for state in ("unknown", "declared_false", "legacy_default"):
        rep = check_reading_view(view, dimensioned_state=state, run_profile="regression")
        dp = next(r for r in rep.results if r.check_id == "reading.dimensions_present")
        # the state survives end-to-end in evidence (never folded to a bool)
        assert dp.evidence["dimensioned_state"] == state
        seen[state] = dp.message
    # three distinct reasons — folding would collapse these to one
    assert len(set(seen.values())) == 3, seen


# --------------------------------------------------------------------------- #
# L-21 · sm24 fixture dimension activation (structurally isomorphic, 裁定 §2.1)
# --------------------------------------------------------------------------- #
def _sm24_activation_fixture(tmp_path: Path, *, structured: bool) -> tuple:
    """Build a structurally-sm24-isomorphic case (1 plan + 4 elevation required
    views) and a 5-view product: 4 views carry a non-closing chain, 1 closes.
    Returns (manifest, produced) for check_reading_stage."""
    case_dir = tmp_path / f"sm24_{'true' if structured else 'leg'}"
    shutil.copytree(SM24, case_dir)
    if structured:
        views = ["1f_view", "South_view", "North_view", "East_view", "West_view"]
        _set_structured_dim(case_dir, [_structured_dim_decl(v, True) for v in views])
    manifest = build_view_manifest(case_dir)
    non_closing = _plan_with_dims(overall=6.0, segments=[2.0, 3.0])
    closing = _plan_with_dims(overall=5.0, segments=[2.0, 3.0])
    stems = [e.expected_output_id for e in manifest.required_entries()]
    produced = {stems[0]: closing}
    for st in stems[1:]:
        produced[st] = non_closing
    return manifest, produced


def test_L21_sm24_dimension_activation_fixture_isomorphic(tmp_path: Path):
    """裁定 §2.1：sm24 同构 fixture（5 required view 含 plan+elevation），声明
    declared_true 后 dimensions_present / dimension_p1a_fields 各 5 行由 N/A 转
    真实判定；其他 check-id 逐项不变；四条 closure 仍 block。"""
    from src.validator.checks.schema import CheckStatus

    manifest_leg, produced = _sm24_activation_fixture(tmp_path, structured=False)
    manifest_true, _ = _sm24_activation_fixture(tmp_path, structured=True)

    rep_leg = check_reading_stage(manifest_leg, produced, run_profile="regression",
                                  capability_profile="rectangular")
    rep_true = check_reading_stage(manifest_true, produced, run_profile="regression",
                                   capability_profile="rectangular")

    def _ids_statuses(rep):
        return {r.check_id: r.status for r in rep.results}

    leg, true = _ids_statuses(rep_leg), _ids_statuses(rep_true)

    # (a) dimensions_present + dimension_p1a_fields: 5 rows each, N/A → real verdict
    for stem in [e.expected_output_id for e in manifest_true.required_entries()]:
        assert leg[f"{stem}.reading.dimensions_present"] is CheckStatus.NOT_APPLICABLE
        assert true[f"{stem}.reading.dimensions_present"] is CheckStatus.PASS
        assert leg[f"{stem}.reading.dimension_p1a_fields"] is CheckStatus.NOT_APPLICABLE
        assert true[f"{stem}.reading.dimension_p1a_fields"] is CheckStatus.PASS

    # (b) other check-ids identical between the two manifests (same product)
    dim_check_suffixes = (
        "reading.dimensions_present",
        "reading.dimension_p1a_fields",
    )
    others_leg = {k: v for k, v in leg.items() if not k.endswith(dim_check_suffixes)}
    others_true = {k: v for k, v in true.items() if not k.endswith(dim_check_suffixes)}
    assert others_leg == others_true

    # (c) the four non-closing closures still block under regression
    closure_blocks = [
        r for r in rep_true.blocking() if r.check_id.endswith("reading.dimension_chain_closure")
    ]
    assert len(closure_blocks) == 4
    # ... and legacy_default did not silently wash them away either
    closure_blocks_leg = [
        r for r in rep_leg.blocking() if r.check_id.endswith("reading.dimension_chain_closure")
    ]
    assert len(closure_blocks_leg) == 4


# --------------------------------------------------------------------------- #
# L-10 / L-11 / L-12 · isolation policy truth / exploratory control / drift
# --------------------------------------------------------------------------- #
def _merge_with_policy(tmp_path: Path, tag: str, run_profile: str, capability_profile: str):
    """Build an isolation workspace under a frozen policy, merge a FIXED six-view
    sm21 product (4 non-closing chains + 2 closing), return (run_dir, attempt_dir,
    report). The product is byte-identical across tags so two policies can be
    compared fact-row-for-fact-row."""
    case_dir = tmp_path / f"case_{tag}"
    shutil.copytree(SM21, case_dir)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    provision_run_policy(run_dir, run_profile=run_profile, capability_profile=capability_profile)
    vm = provision_view_manifest(case_dir, run_dir)
    ensure_run_manifest_v2(run_dir, view_manifest_sha256=vm.content_sha256)
    staging = tmp_path / f"staging_{tag}"
    build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=staging)
    stems = [e.expected_output_id for e in vm.required_entries()]
    views = {
        st: _plan_with_dims(overall=(6.0 if i < 4 else 5.0), segments=[2.0, 3.0])
        for i, st in enumerate(stems)
    }
    (staging / "out").mkdir(parents=True, exist_ok=True)
    (staging / "out" / "output.json").write_text(json.dumps({"views": views}), encoding="utf-8")
    attempt_dir = merge_isolated_output(staging, run_dir, accept=True)
    report = CheckReport.model_validate_json((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    return run_dir, attempt_dir, report


def _facts_key(report: CheckReport):
    """check_id+status+evidence signature of a report's FACT rows — disposition
    is DERIVED from these, so two reports with identical facts differ only in
    blocking(). Excludes ``isolation_provenance_bound`` (a per-merge staging
    artifact whose hash differs between two physical workspaces, not a reading
    fact)."""
    return sorted(
        (r.check_id, r.status.value, json.dumps(r.evidence, sort_keys=True))
        for r in report.results
        if r.check_id != "reading.isolation_provenance_bound"
    )


def test_L10_isolation_policy_truth_regression_blocks(tmp_path: Path):
    """L-10: regression + orthogonal isolation fixture, 4 non-closing chains ⇒
    checks.json head is precisely regression/orthogonal + policy hash; attempt
    filed but NOT accepted; blocker is exactly the four closures (摘掉 merge 消费
    EffectiveRunPolicy ⇒ 头部会退回 rectangular/exploratory 且 0 block)。"""
    run_dir, _attempt_dir, report = _merge_with_policy(
        tmp_path, "reg", "regression", "orthogonal_polygon",
    )
    assert report.run_profile == "regression"
    assert report.capability_profile == "orthogonal_polygon"
    record = resolve_frozen_run_policy(run_dir)
    assert report.run_policy_sha256 == record.policy_hash
    assert report.run_policy_source == "structured_config"
    # attempt filed but NOT accepted (4 blocking closures downgrade accept=True)
    rm = load_run_manifest(run_dir)
    assert isinstance(rm, RunManifestV2)
    stage = rm.stages.get("0_reading")
    assert stage is None or not stage.accepted
    # blocker is EXACTLY the four closures — nothing else blocks
    closure_blocks = [r.check_id for r in report.blocking()
                      if r.check_id.endswith("reading.dimension_chain_closure")]
    assert len(closure_blocks) == 4
    assert len(report.blocking()) == 4


def test_L11_exploratory_control_same_facts_zero_blocker(tmp_path: Path):
    """L-11: byte-identical product, only the pre-issuance policy is exploratory
    ⇒ 0 blocker; head exploratory; fact rows identical to the regression run
    (摘掉 disposition 按 profile 走 ⇒ 会有 blocker 或事实行改变)。"""
    _, _, report_reg = _merge_with_policy(
        tmp_path, "reg", "regression", "orthogonal_polygon",
    )
    run_dir_exp, _, report_exp = _merge_with_policy(
        tmp_path, "exp", "exploratory", "rectangular",
    )
    assert report_exp.run_profile == "exploratory"
    assert report_exp.run_policy_sha256 == resolve_frozen_run_policy(run_dir_exp).policy_hash
    # exploratory ⇒ 0 blocker (the four closures FLAG, not BLOCK)
    assert report_exp.blocking() == []
    # fact rows are byte-identical to the regression run (only disposition differs)
    assert _facts_key(report_reg) == _facts_key(report_exp)


def test_L12_policy_drift_rejected_before_attempt(tmp_path: Path):
    """L-12: build under regression, then change run_config.yaml before merge ⇒
    rejected with run_policy_drift BEFORE any attempt is created (摘掉 policy
    hash 绑定 / 重验 ⇒ drift 会静默通过)."""
    case_dir = tmp_path / "case_drift"
    shutil.copytree(SM21, case_dir)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "run_profile: regression\ncapability_profile: orthogonal_polygon\n"
    )
    provision_run_policy(run_dir, run_profile="regression", capability_profile="orthogonal_polygon")
    vm = provision_view_manifest(case_dir, run_dir)
    ensure_run_manifest_v2(run_dir, view_manifest_sha256=vm.content_sha256)
    staging = tmp_path / "staging_drift"
    build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=staging)
    # drift: change the declared profile AFTER build (build→merge policy drift)
    (run_dir / "run_config.yaml").write_text(
        "run_profile: dev\ncapability_profile: orthogonal_polygon\n"
    )
    stems = [e.expected_output_id for e in vm.required_entries()]
    views = {st: _plan_with_dims(segments=[2.0, 3.0]) for st in stems}
    (staging / "out").mkdir(parents=True, exist_ok=True)
    (staging / "out" / "output.json").write_text(json.dumps({"views": views}), encoding="utf-8")
    with pytest.raises(ValueError, match="run_policy_drift"):
        merge_isolated_output(staging, run_dir, accept=True)
    # no attempt created (the drift raise precedes attempt_dir creation)
    attempts = run_dir / "0_reading" / "attempts"
    assert not attempts.exists() or not any(attempts.iterdir())


