# F-5 施工 · 窗源字段名钉契约 + ⚠️真链路边界上报（待 orchestrator 确认）

- **日期**：2026-08-05
- **施工席**：GLM-5.2
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_f5_window_source_field_names_dispatch.md`
- **状态**：**F-5 代码完成 + 单元/neuter/真链路窗源点均证明修好；但派工单 §5.5「flow 进 2_modelling」未达成，因两个独立 correction 问题；提交与 F-2c 在 `window_sources.py` 交织。⬇ 见 §5/§6，请 orchestrator 裁。**

---

## 1. 缺陷与修法（已完成）

**契约单一来源**（两处独立声明，口径一致）：`schema.py:36`「rect: x_range_m/y_range_m」+ `guide.md:175/360`「Elevation window strokes use geometry.kind=rect + x_range_m / y_range_m」。真实产物（07-07 sm21）plan 与四立面 window stroke 全用 `_m`。

**消费侧**（`window_sources.py:_window_strokes`）原读 `x_range`/`y_range`/`z_range` ⇒ 取 None ⇒ `_interval` 抛 `source_identity_invalid` ⇒ 1_correction 死。

**修法**（只改消费侧，⛔ 未碰契约、未写兼容层）：
- plan 通道：`x_range`→`x_range_m`、`y_range`→`y_range_m`（→ `world_x/y_interval`，世界坐标定位）。
- elevation 通道：`x_range`→`x_range_m`（→ `local_along_interval`，沿面）；`z_range`→**`y_range_m`**（→ `local_z_interval`，sill/head 竖直）。**契约无 `z_range` 字段**（见 §2），原读恒 None ⇒ sill/head 证据从未进链。

下游语义已核（`window_host.py:634/647/653`、`window_sources.py:668`）：plan 区间是世界 XY、elevation along 由 `frame.to_world_along` 映射、elevation z 检查 `z_floor…ceiling_height`。改读 `_m` 语义完全对齐。

## 2. ⛔ `z_range` 无别处契约来源（派工单 §6 边界，无需停下）

全仓 `z_range` 命中：消费侧（本次修）+ 夹具（本次改）+ 历史文档 + **`src/mcp/api/common.py:96`**。后者是 **EnergyPlus 3D 顶点 Z 值一致性检查**（surface 顶点的 Z 范围），与 reading stroke 的 `geometry.z_range` **完全无关、不同模块不同语义**。⇒ reading 契约里 `z_range` 零来源，按派工单可放心改成 `y_range_m`，未两边都改。

## 3. 夹具钉契约（已完成）

`_context`/`_reading`/`_plan_geometry`/`_with_plan_marker` 都把 geometry dict 直接当 stroke.geometry。改契约拼写后自洽。改了 4 文件：
`test_c2_b5_host_resolution.py`、`test_c2_b5_source_routing.py`、`test_c2_b5_parent_and_verts.py`、`test_c2_b2b_envelope_transform.py`：`x_range`→`x_range_m`、`y_range`→`y_range_m`、`z_range`→`y_range_m`（立面竖直）。

**连锁**：`parent_and_verts.py` 的硬编码回归锚 `SOUTH_RESOLUTION_SHA256` 变值（geometry 字段名变 → reading artifact 字节变 → output_sha256 → source_locator → resolution_sha256 变；`SOUTH_SEGMENT_ID` 不变，印证几何/拓扑逻辑未坏）。已更新为新值 `c388b0ddef9e…`（仅此文件引用，非跨系统冻结信任根）。

四件套改完后**全绿**（排除 F-2c 的 B5 A6 红，见 §6）。

## 4. 锁（`tests/test_f5_window_source_fields.py`，12 passed）

- **真实产物锁**（07-07 sm21 S11/S3 逐字数值）：plan 拿到 `world_x=[1.24,3.64]`/`world_y=[7.76,8.0]`；**elevation 拿到 `local_along=[3.4,4.6]` 且 `local_z=[4.0,5.8]` 非 None**（sill/head 证据 F-5 后才进链）。
- **四格实测**：{plan,elevation}×{真实, 缺字段坏产物} — 真实拿到区间，缺 `x_range_m`/`y_range_m` fail-closed。
- **结构性锁**：消费侧源码只读 `x_range_m`/`y_range_m`、旧拼写（`geometry.get("x_range")` 等 + `field="x_range"` 等）从消费侧消失；4 夹具文件 + 本锁文件扫描无 `"(x|y|z)_range":` 旧拼写；契约源（`schema.py`）仍声明 `_m` 名；字段名来自单一契约常量 `CONTRACT_RECT_FIELDS`（fixture 用 `zip` 构造，非手抄）。

## 5. neuter（自己跑，3 红对靶、无连带、无假锁）

`git stash` 把 `window_sources.py` 隔离回 HEAD（摘掉 F-5a 修法）→ 跑本锁文件：
- **红 3 条，全 F-5a 对靶**：`test_plan_compliant_product_yields_world_intervals`、`test_elevation_compliant_product_yields_along_and_z_intervals`、`test_consumer_reads_only_contract_field_names`。
- **绿 9 条**：四格 fail-closed（旧拼写下任何产物都 fail-closed，碰巧仍绿）、夹具扫描锁、契约源码锁（不受 window_sources neuter 影响）。
- 无「本该红却绿」的假锁。stash pop 恢复后 12 passed。

## 6. ⚠️ 真链路复现（派工单 §5.5）—— **F-5 修好窗源，但 flow 未进 2_modelling，因两个独立 correction 问题**

命令：`run_stage.py flow sm21_anchor run_2026-08-05_smoke_downstream_r2 --judge off --geometry auto --to 2_modelling`（exit 1）。

**前**：`1_correction/correction_parse_error.txt` = `WindowResolverInputError ... source_identity_invalid`；`2_modelling/` 不存在（correction 从未进内核）。

**后**（F-5 修好后重跑）：
```
src/agent/correction/window_sources.py:690 build_verified_window_resolver_inputs
  → :634 _claim_links
  → WindowResolverInputError: source_identity_invalid: {'window_id': 'W-1F-N-1', 'source_locator': 'D2'}
```
⇒ **correction 已过 `_window_strokes`（F-5 修复点，不再死 `source_identity_invalid: x_range`），死在后续 `_claim_links`**。这证明 F-5 字段名修法在真链路生效。

但 flow 仍未进 2_modelling，因**两个独立问题（均非 F-5 = 窗源字段名）**：
1. **correction LLM（deepseek-v4-pro）`provenance` 枚举不合规**：产出 `'transcribed_dimension'`/`'inferred_topology'`，不在 `CorrectedGeometryV3` 的 `'observed'/'derived'/'assumed'` 枚举里，attempt 1/3（1 error）、2/3（60 errors）、3/3 全拒。
2. **`_claim_links`：旧 `correction_geometry.json`（03:36 残留产物）的 `W-1F-N-1` provenance `source_ids` 是裸 stroke id（`['D2','D3']`/`['D22']`/`['S11']`…），其中 `D2` 在任何 reading artifact 里都不存在**（pen 非 window 或被 correction 编造/版本不一致）——非 locator 格式，关联失败。

两者都与 F-5（`_window_strokes` 读 `x_range_m`）无关：F-5 把 flow 的死点从 `_window_strokes`（x_range）推进到了 `_claim_links`（D2），正是修法生效的证据。

**请 orchestrator 裁**：F-5 的真链路证明（窗源 `_window_strokes` 已过 + 单元锁 + neuter）是否足够视为 F-5 完成？两个独立 correction 问题（provenance 枚举 + claim_links D2 不一致）是否另立排查（不在 F-5 范围）？

## 7. ⚠️ 提交交织（F-5 与 F-2c 共享 `window_sources.py`）

工作树当前 = F-5 + F-2c（裁定照收的）共存。两任务唯一共享文件是 `window_sources.py`：F-5 改 `_window_strokes`，F-2c 改 `verify_reading_stage_root_against_accepted_attempt`（含 `from src.agent.judge... import`，违 B5 A6 ⇒ 当前工作树 2 条 B5 A6 守卫红，待 F-2c 收口改 `reading.contract` 后转绿）。

**我的提交方案（符合「各自单独提交 / 只 add 自己改的文件」）**：
1. `git stash push` 隔离 F-2c 整文件改动（`isolation.py` F-2c-1 + `run_stage.py` docstring + `test_e2e_break_r2_locks.py` F-2c 锁）；
2. `window_sources.py` 用 `git hash-object -w` 存 blob（F-5+F-2c）→ `checkout HEAD` → 重 apply F-5（3 处）；
3. 工作树此时 = 纯 F-5 → 跑全仓三数字（应 0 红，B5 A6 绿）→ `git add` window_sources + 4 夹具 + 锁 → commit F-5；
4. `git stash pop` + `git cat-file` 恢复 F-2c 改动 → 继续 F-2c 收口。

F-2c 改动全程在 git object/stash 里不丢。**请确认此方案可否，或是否接受更简粒度。**

## 8. 全仓三数字

F-5+F-2c 共存态（工作树）：**2190 passed / 10 xfailed / 2 failed**（322s）。
- 2 failed = `test_b5_a6_production_source_is_judge_blind` + `test_c5_production_correction_and_geometry_sources_import_no_judge`，**全是 F-2c 的 B5 A6 守卫**（`window_sources.py` import judge，待 F-2c 收口改 `reading.contract` 后转绿）。
- **F-5 零引入红**：新增 12 锁 + 4 夹具修复 + `SOUTH_RESOLUTION_SHA256` 连锁全绿；基线 2177 → 2190（+13 = F-5 的 12 锁 + 1）。
- 隔离 F-2c 后的 F-5 纯净三数字在提交前另跑（预期 0 红，B5 A6 绿）。
