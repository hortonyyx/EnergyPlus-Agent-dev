# P0 交付说明 · 天正→GT v3 转换器（GLM-5.2 施工）

> 日期 2026-07-22 · 施工 GLM-5.2 · 主控 Opus 4.8 · 范围 **仅 P0**
> 施工基线 = [`proposals/tarch_to_gtv3_converter_plan.md`](../../../proposals/tarch_to_gtv3_converter_plan.md)
> 派单 = [`request/2026-07-22_tarch_converter_construction_dispatch.md`](../request/2026-07-22_tarch_converter_construction_dispatch.md)
>
> **本轮只做 P0，已到 §6.1 保护路径硬检查点停下，未进 P1。§6.1 给两方案 + 推荐 + 理由，等主控裁。**

---

## 0. 摘要

P0 = **契约冻结 + 诊断码骨架 + config/容差通道 + staging 跑通 + §6.1 方案**。退出门**全部达成**：

| 退出门 | 状态 | 证据 |
|---|---|---|
| 契约冻结（request / IR / report / source_map 可序列化往返）| ✅ | `test_*_round_trip*` 6 测 |
| 诊断码表全覆盖（每个 fail-closed 分支有码，无 WARN，每 BLOCK 有 remedy）| ✅ | `TARCH_DIAGNOSTIC_REGISTRY` 39 码 + 3 测 |
| config 通道 + sha256 记账（复用 `load_gt_tooling_config`，零新造容差）| ✅ | `resolve_converter_tooling` + 2 测 |
| staging 跑通（骨架能 import、实例化、在 staging 目录往返）| ✅ | `test_staging_skeleton_instantiates` |
| gt 隔离 opus §8.5 三条机械守 | ✅ | `test_gt_discipline.py` 扩展 |
| **§6.1 保护路径矛盾给方案 + 停下报主控裁** | ✅（**硬检查点，未自裁**）| 见本文 §7 |

**测试**：全量 **1473 passed + 9 xfailed**（基线 1456 + P0 新增 17，零回归）。

---

## 1. 改动文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/agent/judge/tarch_converter_schema.py` | **新增** | P0 全部契约 + IR + 报告 + 诊断码表 + config 通道 + staging 路径约定（~600 行）|
| `tests/test_tarch_converter_p0_schema.py` | **新增** | P0 退出门 16 测 |
| `tests/test_gt_discipline.py` | **扩展** | opus §8.5 三条：`_FORBIDDEN` 加 tarch token（①②）+ `test_case_data_has_no_dxf_or_dwg`（③）|
| `backup/src_history/2026-07-22_tarch_converter_p0/` | **备份** | 动 `src/` 前备份了 `judge/` + `test_gt_discipline.py`（CLAUDE.md §5#4）|

**未碰**：golden、gt.json、correction/内核/装配生产路径、v3 提取器本体（`gt_extraction.py`）、`gt_from_dxf.py`、`gt_schema.py`、`gt_manifest.py`。全部新增，零生产码修改。

---

## 2. 契约冻结（落点 `src/agent/judge/`，judge 侧）

全部模型 `extra="forbid"` + `strict=True`（与现有 `gt_schema`/`gt_manifest` 一致）。

### 2.1 输入契约 `TarchConversionRequestV1`（source-hash-bound，唯一非机器输入）
- 源绑定：`case / source_dxf_label / source_dxf_sha256 / normalized_source_id`；单位显式（`native_units / metres_per_unit`，不猜）。
- 每层逐 view：`floors[]` + `plan_views[]`（clip_box + world 仿射 + wall/opening/room_label selector + **`dialect_rules`** + `zone_intent` + `void_intent`）+ `elevation_views[]` + `north_axis` + `raster_overlays`。
- **天正专有规则封装在 `TarchDialectRulesV1`**（`window_block_names` / `door_block_prefixes` / `classifier_version`）——这是它们**唯一**的栖身地，绝不渗进 gate①/执行器（硬纪律#4，§6）。
- 区划意图 `ZoneIntentSpecV1`：`expected_count` **必填无默认** + `entries[]`；`intent_file` 模式下 entries 长度必须 == expected_count（抓"走廊被切开"的 G6 防线种子）。
- override `TarchOverrideKind` 是**窄白名单**（bind_opening_group / declare_free_end_non_zoning / confirm_joint / reviewed_zone|void_anchor / bind_face_pair[backlog]），**无"提交整套最终多边形"逃生口**。
- `request_sha256` 走与 manifest 同款 canonical 规则（hash 字段置零、`sort_keys`、`(",",":")`、`+b"\n"`）。

### 2.2 内部 IR `NormalizedBuildingIRV1`（**v1 起保留多环 + 逐层 footprint + 逐墙逐段厚度 proof**）
- `PolygonIRV1 = exterior(RingV1) + interior_rings[]` —— **多环从 v1 就在**（即使当前 profile 拒洞，IR 形状模型已为 §11-U1 带洞 profile 留好）。
- `floors[].footprint: FootprintIRV1` —— **逐层 footprint**，从不假设共用（不变量 #6）。
- `WallRibbonV1.segments: list[WallRibbonSegmentV1]`，每段带自己的 `thickness_evidence: ThicknessEvidenceV1` —— **逐段厚度**，同一道墙中途变厚 = 多段（测试用 0.120/0.240 两段验证）。
- `ThicknessEvidenceV1.source_kind` 是**六类离散证据** Literal（window_block_short_side / wall_cap_or_opening_jamb / pub_dim_explicit / pub_hatch_outer_wall / reproduced_from_segment / source_hash_override）+ `value_m` + `proof_handles`。
- zone 边 `ZoningEdgeV1.basis: outer_skin | wall_axis`（D7 溯源补偿 + G8 反演输入）。
- IR 里**无** `W_m/D_m`、行列、band、全局墙厚、共用 footprint、固定楼层数（plan §3.3）。

### 2.3 报告 `ConversionReportV1`
- `status: PASS | BLOCKED`；绑**全部** sha256：`source_dxf / normalized_dxf / request / judge_config / vg_config / converter`。
- 状态契约：`PASS` ⇒ 必有几何（zones/walls）、无 BLOCK 诊断、有 `normalized_dxf_sha256`；任一 BLOCK 诊断 ⇒ 不能 PASS（§5.6 反 false-green，代码化）。
- 记账三清单：`unconsumed_source_handles / opening_coverage / wall_proof_coverage / zone_intent_coverage`。

### 2.4 source_map `SourceMapV1`（D7 缓解）
- 每条生成边 → ancestry（`source_entity_refs[]` + `operation` + `wall_ribbon_ids/opening_id/joint_id/proof_ids`），`source_map_sha256` canonical 闭合。

---

## 3. 诊断码表（39 码，全覆盖两稿去重去配对类）

合并 opus（§6）+ sol（§7.2），统一 `tarch_` 前缀，**删配对类码**（主干不做双线配对，plan §0/§3）。`DiagCode` Literal 与 `TARCH_DIAGNOSTIC_REGISTRY` key 集合**机械相等**（测试断言）。**severity 只有 BLOCK / INFO，无 WARN**（§5.6）。每 BLOCK 码有 remedy + 指明触发闸门。

| 阶段 | 码（BLOCK 除非标 INFO） |
|---|---|
| S0 体检 | `input_source_hash_mismatch` `source_proxy_present` `units_undeclared` `view_frame_missing` `view_frame_ambiguous` `entity_unsupported` |
| S1 量化 | `wall_nonorthogonal` `wall_degenerate_line`(INFO) `quantization_conflict` |
| S2 墙 | `wall_thickness_unevidenced` `wall_entity_unaccounted` |
| S3 洞口 | `opening_block_unresolved` `opening_block_ambiguous` `opening_fill_conflict` `opening_gap_unexplained` `opening_evidence_unbound` `opening_host_ambiguous` `opening_kind_ambiguous` `skin_gap_unattributed` `interior_opening_excluded`(INFO) |
| S4 拓扑 | `topology_residual` `wall_free_end` |
| S5 腔体 | `footprint_multiple` `profile_hole_unsupported` `profile_floor_footprint_unsupported` |
| S6 意图 | `cavity_count_mismatch` `cavity_unclaimed` `cavity_multi_label` `role_unmapped` `zone_seed_near_boundary` `zone_intent_split` |
| S7 外扩 | `edge_thickness_inconsistent` `edge_far_side_ambiguous` `zone_tiling_residual` `opening_skin_gap_mismatch` |
| S8/跨 | `reconstruction_residual`(G8) `v3_precondition`(G9) `provenance_incomplete` `nondeterministic_output` |

- `ConversionDiagnosticV1` 强制：severity/stage 必须与 registry 一致；**BLOCK 必须可定位**（至少一个 `source_entity_handle` 或 `source_points_dxf_mm`，否则构造即拒）。
- 每码有 `action_code`（稳定机器码）+ `overlay_asset`（指向标红图）。

---

## 4. config 通道 + sha256 记账（硬纪律#3，零新造容差）

```python
resolve_converter_tooling(gt_config_path, vg_config_path)
    → load_gt_tooling_config(...)  # 复用现有,返回 GtResolvedToolingConfigV1
        .tolerances(七值) + .judge_config_sha256 + .vg_config_sha256
derive_quantization_step(tooling) → dxf_node_join_tolerance_m / 10  # 派生量,非配置项
```

- **七容差全部来自 `src/configs/judge_gt.yaml`**（`load_gt_tooling_config` 解析），转换器**不新增任何容差常量**。
- `judge_config_sha256` 记进 `ConversionReportV1`，且测试断言它 == `judge_gt.yaml` 原始 bytes 的 sha256（与 v3 提取器自身绑的字节一致）。
- 量化步长 = `τ_node/10` 以代码固定（`derive_quantization_step`），**无法**通过加配置项悄悄改 snapping。

---

## 5. staging 跑通 + gt 隔离

- **staging 纪律代码化**（§6.1 两稿一致）：`is_protected_tarch_path` / `assert_staging_input`（fail-closed）/ `staging_work_dir`（`AI_agent/logs/experiments/<date>_<case>_gt/work/`）。
- **gt 隔离 opus §8.5 三条**（`test_gt_discipline.py`）：
  - ①② `tarch_converter` / `normalize_tarch_dxf` / `tarch_to_gtv3` 进 `_FORBIDDEN`，扫 gate①（`src/validator/checks/*`）+ 执行器（pipeline/execution/correction/reading/cv_probe）断言不含 —— 转换器模块 + CLI 不得被 runtime import；
  - ③ `test_case_data_has_no_dxf_or_dwg`：`case_tests/**/case_data/` 下零 DXF/DWG（含将来的 normalized.dxf）。

---

## 6. 测试结果

- `tests/test_tarch_converter_p0_schema.py`：**16 测全绿**（契约往返 / 诊断码表全覆盖 / config 通道 / staging 纪律 / 硬纪律结构守卫 / staging 集成）。
- `tests/test_gt_discipline.py`：扩展后全绿（现有 + 新 case_data 测）。
- **全量：1473 passed + 9 xfailed**（基线 1456 + P0 新增 17，**零回归**，9 xfail 为既有 legacy golden 待 sm21 批次重录）。

---

## 7. ⚠️ §6.1 保护路径矛盾 —— 两方案 + 推荐 + 理由（**硬检查点，等主控裁，未自裁**）

### 7.1 矛盾的精确形态（已读码确认）

- `_protected_dxf_source(path)`（`gt_from_dxf.py:21`）拒**三类路径作 gt 重建输入**：`case_tests/test_baseline/gt/`（DEFAULT_GT_DIR）、`gt_sources/`、`e2e_tests/*/case_data/`。
- `_protected_candidate_path(out)`（`gt_schema.py:707`，`write_gt_v3_candidate` 调用）拒**把 candidate 写进**保护路径。
- ⇒ 保护是**双侧**的：既禁从答案区读重建、又禁往答案区写 candidate。
- **现有 bundle 结构**：`gt/<case>/{gt.json, renders/}`（答案 + 人核件）；`gt_sources/<case>/source.dxf`（源 DXF，sm21/sm24 都在）。两者都受保护。
- **出稿方 bundle 约定**（plan §8.5）：`gt/<case>/{gt.json, source.dxf, normalized.dxf, conversion_report.json, renders/}` —— 把 `source.dxf`/`normalized.dxf` 塞进 `gt/<case>/` ⇒ 被 `_protected_dxf_source` 拒，无法用 `gt_from_dxf.py --dxf gt/<case>/normalized.dxf` 直接重建。

**本质**：这不是 bug，是出稿方"一站式 bundle"设想与仓库既有"答案区双侧重保护 + `gt/` vs `gt_sources/` 分工"原则的冲突。

### 7.2 方案 A —— 改 bundle 约定（对齐既有分工，**不动**保护逻辑）
- 不把 `source.dxf`/`normalized.dxf` 放进受保护的 `gt/<case>/` 答案区；沿用并扩展现有分工：
  - `gt/<case>/` = `gt.json`（答案）+ `renders/`（人核件）——**现状不变**；
  - `gt_sources/<case>/source.dxf` = 原始天正导出 DXF ——**现状，sm24 已有**；
  - 转换器 staging 产物晋升时：`normalized.dxf` + `conversion_report.json` + `extraction_manifest.json` + `source_map.json` 进 `gt_sources/<case>/`（重建依据区，与 `source.dxf` 同处）。
- 重建 = 从 staging 跑：`gt_from_dxf.py --dxf <staging>/normalized.dxf`（staging 在 `logs/experiments/`，不在任何保护路径）。
- **优点**：双侧重保护（正确设计）零改动；bundle 约定对齐既有 `gt/` vs `gt_sources/` 分工；sm21 现状不受影响；失败模式清晰（从受保护区重建一律拒）。
- **代价**：出稿方"一站式 bundle"被拆成两目录。

### 7.3 方案 B —— 改保护逻辑（松绑**输入侧**，动 `_protected_dxf_source`）
- 把输入侧语义从"禁从受保护区读 DXF 重建"松为"只禁写"（输出侧 `_protected_candidate_path` 已守写），允许从 `gt/<case>/normalized.dxf`（归档）**只读**重建验证。
- **优点**：支持"从 bundle 直接重建验证"；出稿方一站式 bundle 可保留。
- **代价**：动 v3 入口工具 `gt_from_dxf.py` 的保护闸门（触及派单 §2"不碰 gt.json" + plan §3.2 (A)"不改 v3 提取器本体"**附近**——`_protected_dxf_source` 在 CLI 层非本体，但属 v3 入口保护）；**削弱输入侧重保护**（原来连"读受保护区重建"都禁），语义稀释，存在"误从归档区读旧 normalized.dxf 重建"风险。

### 7.4 我的推荐 = **方案 A**

1. 双侧重保护是仓库**既有且正确**的 fail-closed 设计；松绑任一侧都是削弱保护。方案 A 零摩擦保留它。
2. 重建走 staging 是两稿**一致**工作流（plan §8.5 + sol §3.4 都要求 staging 跑），方案 A 直接落地。
3. 现有 `gt_sources/<case>/source.dxf` 分工已存在（sm21/sm24），方案 A 只**沿用 + 扩展**（加 normalized.dxf + report + manifest），不引入新目录、不动现有 sm21 答案。
4. 方案 B 为换"从 bundle 直接重建"便利而削弱保护 + 动 v3 入口闸门——不值得（这是答案生成器，保护宁可严）。
5. 方案 A 的"两目录"代价小：`gt_sources` 已是源/重建依据的既有归宿，转换器派生件（normalized.dxf 是源 DXF 的规范化副本）放它旁边语义自然。

> **本轮未自裁**：既未改 `_protected_dxf_source`，也未改 bundle 约定。P0 的 staging 骨架（§5）**不依赖** §6.1 最终裁决——无论主控选 A 还是 B，staging 跑都成立。**等主控裁定后再在 P1 起接入对应约定**（A：文档化晋升落 `gt_sources/`；B：改 `_protected_dxf_source` 并补双侧一致性测试）。

---

## 8. 诚实披露（未竟 / 拿不准 / 绕过）

对标 B4b Phase D 正面样板，逐条标明：

1. **P0 无算法体 S0–S9**：本批只冻契约 + 诊断码骨架，无任何几何算法实现（S0–S9 是 P1/P2）。`NormalizedBuildingIRV1` 是**形状契约**，构造逻辑未写。
2. **P0 无 CLI**（`scripts/tool_scripts/normalize_tarch_dxf.py`）：opus §8.5.2 的"CLI 不被 runtime import"靠 `_FORBIDDEN` 加 CLI 名 token **前瞻覆盖**（runtime 里本就没有这些名，绿）；真 CLI 待 P1 建，建后该守卫即生效。
3. **P0 无 manifest 草稿生成 / overlay 渲染**：manifest 对齐目标（`GtExtractionManifestV1`）已读清，但生成是 P2/P5；overlay 是 P2/P6。本批不产任何可消费 bundle。
4. **`compute_report_sha256` 的 canonical 规则自定**：report 无自 hash 字段（它已绑 source/request/judge_config/vg_config/converter 五个 sha256，自描述），故 report 的整体 sha256 由独立 helper 算（规则与 manifest 同款：`sort_keys`+`(",",":")`+`+b"\n"`+`-0.0→0.0`）。这是 P0 决策，**主控/sol 若认为 report 应自带 `report_sha256` 字段，P1 调整**。
5. **前向引用靠 pydantic 自动解析**：`TarchConversionRequestV1.floors: list["FloorIntentV1"]`（FloorIntentV1 后定义）在 `from __future__ import annotations` 下由 pydantic v2 自动解析成功（往返测试验证），**未显式调 `model_rebuild()`**。若后续新增跨模块前向引用报错，补 `model_rebuild()`。
6. **`ElevationViewIntentV1` 已从 `tuple[3]` 收紧为复用 `Affine1D`**（带 source_axis + 非零校验 + axes-differ validator）——发现初稿简化后即修，非遗留。
7. **§6.1 未自裁**：见 §7，按要求停下报主控，未改任何保护逻辑或 bundle 约定。

---

## 9. 下一站

- **等主控裁 §6.1**（方案 A / B 或第三方案）。
- 裁定后进 **P1**（S0–S4：体检 / 量化 / 端头 / 洞口双证据 / 拓扑闭合），退出门 = sm24 洞口 21/21、三项零残留、Σ面积零残差（**独立重导，不照抄 probes/ 数字**——硬纪律#7）。
- 审阅：派单定 **sol（gpt-5.6-sol，effort max）审**，谁写谁不批。
