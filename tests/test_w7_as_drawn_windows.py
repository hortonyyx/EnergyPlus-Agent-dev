"""as_drawn 腿的窗：目录 / 造窗 / 拒绝路径 / 容差派生 / 腿分派（2026-09-08 补窗）。

⛔ 这些锁**不读未跟踪数据**：夹具全部已入库
（`run_wallhunt/0_reading/*.json` 与 `run_wallhunt/1_correction/floor_*/projection_envelope.json`）——
与同日 W#3/W#5/W#6 那三组锁踩过的坑相反（它们读 untracked 目录，
换一棵树就 12 红；见提交 09.08g）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.as_drawn_windows import (
    derive_as_drawn_windows,
    derive_match_tolerance_m,
)
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.facade_visibility import (
    VisibilityTolerances,
    materialize_all_facade_segments,
)
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry,
    derive_floor_ladder,
    read_plan_calibration_declaration,
    snap_footprints_to_reference,
)
from src.agent.correction.projection_bridge import (
    CorrectedGeometryProjectionEnvelopeV1,
)
from src.agent.correction.window_sources import (
    ElevationSourceWindowV1,
    PlanSourceWindowV1,
    WindowResolverInputError,
    _parse_manifest,
    build_as_drawn_window_catalog,
)

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


@pytest.fixture(scope="module")
def staged(raw_readings):
    """两层真链几何 + Vg 段（喂入的是【真实产物】，⛔ 不是合成的）。"""
    geoms, decls = [], []
    for floor_dir, input_id in (("floor_1", "1f_view"), ("floor_2", "2f_view")):
        envelope = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
            (RUN / "1_correction" / floor_dir / "projection_envelope.json").read_bytes()
        )
        geoms.append(envelope.geometry)
        decls.append(read_plan_calibration_declaration(
            json.loads(raw_readings[input_id]), input_id=input_id))
    snapped, _ = snap_footprints_to_reference(geoms, decls)
    ladder = derive_floor_ladder(adapt_as_drawn_elevation(
        raw_readings["East_view"], input_id="East_view", facade_ref="East"))
    geom = assemble_multifloor_geometry(ladder, snapped)
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
    """⭐ 取值不承重：50/100/200 mm 给出【相同】结果，60 mm 落在其中。

    ⇒ 60 不是调到边界上的数（20 mm 会丢窗，实测 23 而非 31）。
    """
    def built(tolerance_m):
        windows, _ = derive_as_drawn_windows(
            staged, catalog=catalog, manifest=manifest,
            raw_reading_artifacts=raw_readings, match_tolerance_m=tolerance_m)
        return len(windows)

    plateau = {built(t) for t in (0.05, 0.10, 0.20)}
    assert len(plateau) == 1, f"平台期不成立: {plateau}"
    assert built(derive_match_tolerance_m(raw_readings)) == plateau.pop()
    assert built(0.02) < built(0.05), "更紧的容差应当真的丢窗（判据有分辨力）"


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
