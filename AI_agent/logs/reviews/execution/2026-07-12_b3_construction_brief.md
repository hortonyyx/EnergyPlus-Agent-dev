# C2 B3 覆盖硬门 v2 — 执行简报

- 执行档：terra；日期：2026-07-12；主控回审：Claude / Fable5（Opus）。
- 基座：`bac689b`（工作区另有两处用户既存改动，未触碰：`AI_agent/CLAUDE.md`、`AI_agent/guides/codex_execution_protocol.md`）。
- 范围：仅 B3 覆盖硬门、其配置/A0 登记和回归测试；未改 anchor、golden、gt；未提交 git commit。

## 落地结果

`correction.coverage` 升级为覆盖门 v2，仍是 `INVARIANT` / BLOCK。逐层经
`src.agent.correction.footprint.floor_footprint()` 取得唯一权威 footprint：v1/v2
走 legacy bbox ring，v3 走 `Floor.footprint` ring。cells 采用 polygon union，比较
`cells_union_area_m2` 与 `footprint_area_m2` 的绝对差；面积差、重叠、洞、越界任一
超过独立 `coverage_area_tol_m2` 均 BLOCK。实际 ring 面积由 polygon 计算，不使用
bbox 近似。

默认 `coverage_area_tol_m2: 0.050` 已进入：

- `src/configs/correction.yaml`
- `skills/intake_pipeline/1_correction/A0_contract.md`（`COVERAGE_AREA_TOL`）

依据为替换前 `correction.coverage` 的 0.05m² 判定阈值，因此 legacy 语义不放宽；它
是独立面积单位容差，不复用 `min_edge_length_m` 等线性容差。`CoreTolerances` 从 YAML
载入并验证为正数。

## Check 映射与双路径

| 旧 check_id | B3 处理 | 理由 |
|---|---|---|
| `correction.coverage` | 保留 ID，语义升级为 v2 | 该 ID 已是 correction invariant、失败路由和 `validate_case` / `run_pipeline` parity 的共同契约；迁移会无必要地破坏下游。|

原有重叠、洞、越界分别判定仍保留（面积守恒本身不能发现等面积的洞/越界互换或重复 cell）。
`tests/test_check_parity.py` 已显式断言两条路径均暴露 `correction.coverage`，未新增 parity 排除项。

## 测试与计数

聚焦回归：`pytest -q tests/test_b3_coverage_gate.py tests/test_check_parity.py tests/test_checks_reading_correction.py tests/test_c2_b2_v3.py tests/test_c2_b1_cell_polygon.py tests/test_deterministic_core.py tests/test_kernel_guards.py`

- **116 passed**，另有 **1** 条既有 Pydantic serializer warning（`test_f3_tampered_v3_and_feature_state_fail_closed`）。
- 新 B3 用例覆盖：v1 legacy bbox-ring 正例、超 `coverage_area_tol_m2` 负例、union 面积守恒但 cells 重叠负例、v3 L 形 footprint 的正例及以 bbox 误铺的负例。

曾启动全量 `pytest -q`；该进程在环境中停留于 Linux `D` 状态且未返回汇总，故不报告为全量通过，留主控补跑。

## 备份

改前副本位于 `backup/src_history/2026-07-12_b3_coverage_gate/`，涵盖修改前的
coverage/config/A0/parity 相关源与测试文件。

## 未决 / 偏离

无。未作形态、阈值或 check-id 的设计扩张；0.05m² 仅继承既有门的数值口径并显式命名。

## Review ask（Claude / Opus）

请复核：

1. `correction.coverage` 保留 ID 的兼容映射是否符合 B-08；
2. `floor_footprint()` 是 B3 唯一 footprint 入口，v3 L 形面积未退回 bbox；
3. v2 evidence 的 union/footprint/差值账与独立面积容差命名是否足以验收；
4. 主控环境补跑全量 suite，并确认停留的 pytest 进程不是环境性阻塞。

## 回审补强（主控核录，2026-07-12）

Opus 次高档回审=APPROVE-WITH-CHANGES（零 MAJOR，5 条 MINOR/NIT 补强）。补强由 Sonnet 执行档接手（terra 撞 GPT 限额），执行至收尾时撞 Claude 会话限额中断——**主控事后验伤确认 5/5 已全部落地**：①docstring 澄清 area_delta=记录用守恒账非独立闸门 ②自交环 footprint 有效性守卫负例 `test_v3_self_intersecting_footprint_blocks_on_invalid_footprint` ③容差恰等边界 `test_hole_area_exactly_at_tolerance_passes_strictly_above_blocks` ④v3 内部洞路径 `test_v3_l_shape_footprint_internal_hole_blocks_distinct_from_outside_path` ⑤problems 精度统一 round(...,6)。聚焦四文件 39 passed（主控自跑）；全量另行核录于收录 commit。本节由主控代录（执行档中断于简报步骤，代码/测试交付完整）。
