"""as_drawn 腿的窗：目录 / 造窗 / 拒绝路径 / 容差派生 / 腿分派（2026-09-08 补窗）。

⛔ 这些锁**不读未跟踪数据**：夹具全部已入库
（`run_wallhunt/0_reading/*.json` 与 `run_wallhunt/1_correction/floor_*/projection_envelope.json`）——
与同日 W#3/W#5/W#6 那三组锁踩过的坑相反（它们读 untracked 目录，
换一棵树就 12 红；见提交 09.08g）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.agent.correction.as_drawn_windows import (
    derive_as_drawn_windows,
    derive_match_tolerance_m,
)
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.facade_visibility import (
    VisibilityTolerances,
    materialize_all_facade_segments,
)
from src.agent.correction.window_sources import (
    ElevationSourceWindowV1,
    PlanSourceWindowV1,
    WindowResolverInputError,
    _parse_manifest,
    as_drawn_plan_record_folds,
    build_as_drawn_window_catalog,
)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tool_scripts"))

RUN = Path("case_tests/e2e_tests/sm25-L_anchor/run_wallhunt")


@pytest.fixture(scope="module")
def raw_readings() -> dict[str, bytes]:
    return {p.stem: p.read_bytes() for p in sorted((RUN / "0_reading").glob("*_view.json"))}


@pytest.fixture(scope="module")
def manifest():
    return _parse_manifest((RUN / "_run/view_manifest.json").read_bytes())


@pytest.fixture(scope="module")
def catalog(manifest, raw_readings):
    return build_as_drawn_window_catalog(
        manifest=manifest, raw_reading_artifacts=raw_readings
    )


def _fixed_responses(rdir: Path, product_filename: str):
    """The deterministic model beat (same shape as ``test_w3_chain_replay_
    lock``): round 0 selects every open item's FIRST candidate, round 1
    accepts — ⛔ zero billed provider calls."""
    from src.agent.correction.decision_executor import (
        FixedDecisionV1,
        build_decision_packet,
        compile_wall_ir,
        decision_hash,
    )
    from src.agent.correction.decision_schema import (
        CorrectionDecisionResponseV1,
        ItemDecisionV1,
    )
    from src.agent.correction.evidence_adapters import adapt_as_drawn_plan

    stem = Path(product_filename).stem
    raw = (rdir / product_filename).read_bytes()
    artifact = adapt_as_drawn_plan(
        raw, input_id=stem, floor_ref=stem.removesuffix("_view"), view_type="plan"
    )
    packet0 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"), bundle=artifact, round_index=0
    )
    picks = tuple(
        (item.item_id, item.candidates[0].candidate_id)
        for item in packet0.open_items
    )
    select = CorrectionDecisionResponseV1(
        packet_hash=packet0.packet_hash,
        item_decisions=tuple(
            ItemDecisionV1(
                item_id=item_id,
                action="select_candidate",
                candidate_id=candidate_id,
                reason_code="FIXTURE_LOCK",
            )
            for item_id, candidate_id in picks
        ),
        whole_building_review={"verdict": "accept"},
    )
    packet1 = build_decision_packet(
        compile_wall_ir(
            artifact,
            profile="exploratory",
            decisions=tuple(
                FixedDecisionV1(item_id=i, candidate_id=c) for i, c in picks
            ),
        ),
        bundle=artifact,
        round_index=1,
        previous_decision_hashes=(decision_hash(select),),
    )
    accept = CorrectionDecisionResponseV1(
        packet_hash=packet1.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    return [select, accept]


@pytest.fixture(scope="module")
def staged(tmp_path_factory):
    """两层真链几何 + Vg 段 —— 跑【当前生产链】（`run_multifloor_correction`，
    含 W#6 的 cut-lines 层间协调），输入 = 入库的 run_wallhunt 0_reading 产物。

    ⛔ 不再读 `floor_*/projection_envelope.json`（09.08u 登记的 4 把锁卡点）：
    那两份是 W#6 之前落盘的产物，其二层 cells 停在旧 ring 上
    （14.8749 vs 新链 14.8784）⇒ 窗的 room 匹配 n_cells_matched=0。
    跑真链 = 夹具几何与生产代码【同一次推导】，永不脱同步
    （病根根治，⛔ 不是给匹配加容差 —— 加了会盖掉一个已经修好的病）。
    """
    from run_stage import _w1_cross_check_elevation_ladders
    from src.agent.execution.view_manifest import ViewManifest
    from src.agent.pipeline import MultiFloorPlanRun, run_multifloor_correction

    run_dir = tmp_path_factory.mktemp("w7_chain")
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True)
    (run_dir / "_run").mkdir(parents=True)
    (run_dir / "_run" / "view_manifest.json").write_bytes(
        (RUN / "_run" / "view_manifest.json").read_bytes()
    )
    for p in (RUN / "0_reading").glob("*_view.json"):
        (rdir / p.name).write_bytes(p.read_bytes())
    manifest_obj = ViewManifest.model_validate_json(
        (RUN / "_run" / "view_manifest.json").read_text("utf-8")
    )
    entries = manifest_obj.required_entries()
    plan_entries = sorted(
        (e for e in entries if e.view_type == "plan"), key=lambda e: e.floor_ref
    )
    elevation_entries = [e for e in entries if e.view_type == "elevation"]
    elevation_evidence = _w1_cross_check_elevation_ladders(elevation_entries, rdir)
    s1 = run_dir / "1_correction"
    plan_runs = [
        MultiFloorPlanRun(
            vector_dir=rdir,
            product_filename=f"{e.expected_output_id}.json",
            out_dir=s1 / f"floor_{e.floor_ref}",
            profile="exploratory",
            fixed_responses=_fixed_responses(
                rdir, f"{e.expected_output_id}.json"
            ),
        )
        for e in plan_entries
    ]
    geom = run_multifloor_correction(
        elevation_evidence,
        plan_runs,
        snap_ledger_path=s1 / "footprint_snap_ledger.json",
        evidence_debt_path=s1 / "evidence_debt.json",
    )
    tol = load_core_tolerances()
    vis = VisibilityTolerances(
        depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
        endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m)
    return geom.model_copy(update={
        "facade_segments": list(materialize_all_facade_segments(geom, tolerances=vis))})


# ── 目录 ──────────────────────────────────────────────────────────────────── #

def test_catalog_carries_both_channels_from_the_real_products(catalog):
    """⭐ 两个通道各有对方没有的一半（本批的核心事实）。"""
    plan = [r for r in catalog if isinstance(r, PlanSourceWindowV1)]
    elevation = [r for r in catalog if isinstance(r, ElevationSourceWindowV1)]
    assert plan and elevation
    # 平面能声称 host，⛔ 不能声称 sill/head
    for row in plan:
        assert "host" in row.positive_claims
        assert "sill" not in row.positive_claims and "head" not in row.positive_claims
    # 立面能声称 sill/head，⛔ 不能声称 host
    for row in elevation:
        assert "sill" in row.positive_claims and "head" in row.positive_claims
        assert "host" not in row.positive_claims
        assert row.local_z_interval is not None, "立面行必须带 z —— 那是它独有的那一半"


def test_plan_cross_interval_uses_the_declared_thickness_not_the_measured_spacing(
    catalog, raw_readings
):
    """⛔ 墙厚取【声明值】(matched_declared_mm)，⛔ 不取像素量出的 spacing_m。

    sm25 上两者可分辨：声明 240 mm vs 实测 spacing 0.2384 m。
    """
    doc = json.loads(raw_readings["1f_view"])
    pairs = doc["hypotheses"]["pairs"]
    declared = {float(min(p["matched_declared_mm"])) / 1000.0
                for p in pairs if p.get("matched_declared_mm")}
    measured = {round(float(p["spacing_m"]), 4) for p in pairs if "spacing_m" in p}
    assert declared & {0.24} and 0.2384 in measured, "夹具本身要能分辨两者"
    widths = set()
    for row in catalog:
        if not isinstance(row, PlanSourceWindowV1) or row.floor_ref != 1:
            continue
        for interval in (row.world_x_interval, row.world_y_interval):
            widths.add(round(float(interval.hi) - float(interval.lo), 6))
    assert 0.24 in widths, "跨向区间宽度应等于声明墙厚"
    assert round(0.2384, 6) not in widths, "⛔ 不许出现实测 spacing 的宽度"


# ── 容差：派生 + 平台期 ────────────────────────────────────────────────────── #

def test_match_tolerance_is_derived_from_declared_callouts(raw_readings):
    """容差 = 半个最薄声明墙厚，⛔ 零发明常数。sm25 声明 [240,120] ⇒ 60 mm。"""
    assert derive_match_tolerance_m(raw_readings) == pytest.approx(0.060)


def test_match_tolerance_has_no_declared_source_is_refused():
    """⛔ 没有声明来源就【拒绝】，⛔ 不许默认一个数。"""
    with pytest.raises(WindowResolverInputError):
        derive_match_tolerance_m({"x": json.dumps({"declarations": {}}).encode()})


def test_derived_tolerance_sits_inside_a_stability_plateau(staged, catalog, manifest, raw_readings):
    """⭐ 取值不承重：50/60/100 mm 给出【相同】结果，60 mm 落在其中。

    ⇒ 60 不是调到边界上的数（20 mm 会丢窗，实测 23 而非 31）。
    ⚠️ 200 mm 一档 2026-09-08h 起不再同数（31→30）：容差宽过「同洞」语义
    （半墙 = 120 mm）时，North_view/O04 会在球内同时捞到同墙两条记录
    （L023g2/L024g4，span 端差 151 mm > 半墙 ⇒ 平面自己的语义说是两个洞）
    ⇒ 歧义门拒绝整洞口 —— 旧实现静默挑走更优的一条，正是影子校验拒 21/31
    的形状，⛔ 不许吞。
    """
    def derive(tolerance_m):
        return derive_as_drawn_windows(
            staged, catalog=catalog, manifest=manifest,
            raw_reading_artifacts=raw_readings, match_tolerance_m=tolerance_m)

    plateau = {len(derive(t)[0]) for t in (0.05, 0.06, 0.10)}
    assert len(plateau) == 1, f"平台期不成立: {plateau}"
    assert len(derive(derive_match_tolerance_m(raw_readings))[0]) == plateau.pop()
    assert len(derive(0.02)[0]) < len(derive(0.05)[0]), "更紧的容差应当真的丢窗（判据有分辨力）"
    # 歧义门在 200 mm 一档有牙：真歧义（同墙两记录、span 端差 151 mm > 半墙）
    # 必须亮成 ambiguous 拒绝 + 记账，⛔ 不许静默挑一条保住 31
    windows_far, account_far = derive(0.20)
    assert len(windows_far) == 30
    assert account_far.ambiguous_pair_openings == (
        "North_view/O04->1f_view/L023g2,1f_view/L024g4",)


# ── 造窗 + 记账 ───────────────────────────────────────────────────────────── #

def test_windows_are_built_and_every_absence_is_accounted(staged, catalog, manifest, raw_readings):
    """⭐ 缺席被做成【信号】：门不进 windows[]，但落在账上，⛔ 不是静默空白。"""
    windows, account = derive_as_drawn_windows(
        staged, catalog=catalog, manifest=manifest, raw_reading_artifacts=raw_readings)
    assert windows, "as_drawn 腿必须产出窗 —— 无窗围护结构对能耗模型无意义"
    assert account.windows_built == len(windows)
    elevation_rows = [r for r in catalog if isinstance(r, ElevationSourceWindowV1)]
    # 每一个立面洞口都有去处：要么成窗，要么进未分类账
    assert (account.windows_built
            + len(account.unclassified_elevation_openings)) == len(elevation_rows)


def test_every_window_carries_both_channels_in_its_provenance(staged, catalog, manifest, raw_readings):
    """⛔ 单通道造不出合法窗：host 必引平面、sill/head 必引立面。"""
    windows, _ = derive_as_drawn_windows(
        staged, catalog=catalog, manifest=manifest, raw_reading_artifacts=raw_readings)
    plan_ids = {f"{r.source_input_id}/{r.observation_id}"
                for r in catalog if isinstance(r, PlanSourceWindowV1)}
    elevation_ids = {f"{r.source_input_id}/{r.observation_id}"
                     for r in catalog if isinstance(r, ElevationSourceWindowV1)}
    for window in windows:
        provenance = window.provenance or {}
        assert set(provenance["host"].source_ids) <= plan_ids
        for claim in ("sill", "head"):
            assert set(provenance[claim].source_ids) <= elevation_ids
        assert window.room, "plan 分支硬要求 room —— ⛔ 不许留空"


def test_every_window_lands_on_exactly_one_visible_segment(staged, catalog, manifest, raw_readings):
    """归属墙面由 Vg 的 visible_intervals 决定（按构造是不重叠划分）。"""
    windows, _ = derive_as_drawn_windows(
        staged, catalog=catalog, manifest=manifest, raw_reading_artifacts=raw_readings)
    for window in windows:
        hits = [
            segment for segment in staged.facade_segments
            if segment.floor_id == window.floor_id
            and segment.facade_family == window.facade
            and any(float(i.lo) <= window.span[0] and window.span[1] <= float(i.hi)
                    for i in segment.visible_intervals)
        ]
        assert len(hits) == 1, f"{window.id} 落进 {len(hits)} 个可见段"


# ── 物理洞收编（2026-09-08h：双胞胎并列 ⇒ 最近邻不唯一 ⇒ 21/31 影子拒绝）── #

def test_catalog_carries_one_row_per_physical_opening(catalog, manifest, raw_readings):
    """⭐ 一个物理洞在墙的两条面线上各留一个缺口（62 候选 = 33 物理洞）——
    目录每个物理洞只留一行（幸存 = 字典序最小观测 id），⛔ 不许双胞胎并列
    进最近邻决策。"""
    plan = [r for r in catalog if isinstance(r, PlanSourceWindowV1)]
    assert len(plan) == 33, f"物理洞行数应为 33，实际 {len(plan)}"
    ids = {f"{r.source_input_id}/{r.observation_id}" for r in plan}
    # 具名抽查：L016g6/L017g6 是同一洞的两条面线记录（区间逐位相同）
    assert "1f_view/L016g6" in ids
    assert "1f_view/L017g6" not in ids, "被折叠的孪生不许再进目录"


def test_record_folds_are_a_ledger_not_a_silence(catalog, manifest, raw_readings):
    """收编是【动作】必须可对账：29 条折叠逐条 "folded->survivor" 有名有姓，
    幸存者都在目录里、被折叠者一条不漏进目录。"""
    folds = as_drawn_plan_record_folds(
        manifest=manifest, raw_reading_artifacts=raw_readings)
    assert len(folds) == 29, f"折叠应为 29 条，实际 {len(folds)}"
    assert ("1f_view/L017g6", "1f_view/L016g6") in folds
    catalog_refs = {f"{r.source_input_id}/{r.observation_id}" for r in catalog}
    for folded, survivor in folds:
        assert survivor in catalog_refs, f"幸存者 {survivor} 必须在目录里"
        assert folded not in catalog_refs, f"被折叠者 {folded} 不许在目录里"


def test_account_reports_the_new_pairing_ledgers(staged, catalog, manifest, raw_readings):
    """双向配对的账本：31 建 + 3 未分类 + 2 真平面孤儿 + 29 折叠 +
    0 歧义 + 0 冲突（sm25 收编后应全绿）。"""
    windows, account = derive_as_drawn_windows(
        staged, catalog=catalog, manifest=manifest, raw_reading_artifacts=raw_readings)
    assert len(windows) == account.windows_built == 31
    assert len(account.unclassified_elevation_openings) == 3
    assert len(account.plan_windows_without_elevation) == 2, \
        "孤儿必须是【真·平面独有】—— 旧实现把 29 条被折叠孪生也记成孤儿"
    assert len(account.plan_records_folded) == 29
    assert account.ambiguous_pair_openings == ()
    assert account.conflicting_pair_openings == ()
    payload = account.to_payload()
    assert payload["schema"] == "as_drawn_window_account_v1"
    assert "plan_records_folded" in payload and "ambiguous_pair_openings" in payload


def test_a_second_in_ball_candidate_is_ambiguity_not_a_pick(
    staged, catalog, manifest, raw_readings
):
    """⛔ 歧义门有牙：同一洞口在容差球内出现第二个【不同墙】候选 ⇒
    整洞口拒绝 + 记账，⛔ 不许静默挑残差小的（旧实现正是这么做的）。"""
    dup = None
    for row in catalog:
        if isinstance(row, PlanSourceWindowV1) and f"{row.source_input_id}/{row.observation_id}" == "1f_view/L016g6":
            dup = row.model_copy(update={"observation_id": "L900g0"})
            break
    assert dup is not None
    windows, account = derive_as_drawn_windows(
        staged, catalog=tuple(catalog) + (dup,), manifest=manifest,
        raw_reading_artifacts=raw_readings)
    assert len(windows) == 30, "歧义洞口必须少建一个窗"
    assert any(entry.startswith("East_view/O02->")
               and "1f_view/L016g6" in entry and "1f_view/L900g0" in entry
               for entry in account.ambiguous_pair_openings), account.ambiguous_pair_openings


def test_a_record_whose_nearest_is_another_opening_is_a_conflict(
    staged, catalog, manifest, raw_readings
):
    """⛔ 互为最近有牙：把 O02 挪到 O05 的平面记录附近（残差比 O05 自己大）
    ⇒ 该记录的最近是 O05，O02 必须按冲突拒绝，⛔ 不许单向认领。"""
    bumped = []
    for row in catalog:
        if (isinstance(row, ElevationSourceWindowV1)
                and f"{row.source_input_id}/{row.observation_id}" == "East_view/O05"):
            o05 = row
        if (isinstance(row, ElevationSourceWindowV1)
                and f"{row.source_input_id}/{row.observation_id}" == "East_view/O02"):
            o02 = row
    shifted = o02.model_copy(update={
        "local_along_interval": o02.local_along_interval.model_copy(update={
            # 挪到 O05 的洞口 +2 cm：仍在其平面记录容差球内，但残差必大于 O05 自己
            "lo": float(o05.local_along_interval.lo) + 0.02,
            "hi": float(o05.local_along_interval.hi) + 0.02,
        })})
    windows, account = derive_as_drawn_windows(
        staged, catalog=tuple(r for r in catalog if r is not o02) + (shifted,),
        manifest=manifest, raw_reading_artifacts=raw_readings)
    assert len(windows) == 30, "冲突洞口必须少建一个窗"
    assert any(entry.startswith("East_view/O02->") and "back=East_view/O05" in entry
               for entry in account.conflicting_pair_openings), account.conflicting_pair_openings


# ── 拒绝路径有牙（⛔ 不是猜） ─────────────────────────────────────────────── #

def test_opening_outside_every_storey_is_a_named_refusal(staged, catalog, manifest, raw_readings):
    """z 不落在恰好一层 ⇒ 具名拒绝，⛔ 不挑最近的一层。"""
    bumped = []
    for row in catalog:
        if isinstance(row, ElevationSourceWindowV1):
            row = row.model_copy(update={"local_z_interval": row.local_z_interval.model_copy(
                update={"lo": 900.0, "hi": 901.0})})
        bumped.append(row)
    with pytest.raises(WindowResolverInputError):
        derive_as_drawn_windows(staged, catalog=tuple(bumped), manifest=manifest,
                                raw_reading_artifacts=raw_readings)


def test_opening_off_every_visible_segment_is_a_named_refusal(staged, catalog, manifest, raw_readings):
    """沿面区间落在楼外 ⇒ 具名拒绝。"""
    shifted = []
    for row in catalog:
        if isinstance(row, ElevationSourceWindowV1):
            row = row.model_copy(update={"local_along_interval": row.local_along_interval.model_copy(
                update={"lo": 500.0, "hi": 501.0})})
        shifted.append(row)
    with pytest.raises(WindowResolverInputError):
        derive_as_drawn_windows(staged, catalog=tuple(shifted), manifest=manifest,
                                raw_reading_artifacts=raw_readings)
