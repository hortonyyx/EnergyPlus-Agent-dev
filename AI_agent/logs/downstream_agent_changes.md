# 下游 subagent 改动记录

> 本文件记录本项目侧对**下游 9 个 subagent**（zone / material / schedule / construction / surface / fenestration / hvac / people / lights）以及其周边代码（cross_ref / validate / simulate / 共享 prompt）的所有本地改动。
>
> **背景**：按 [CLAUDE.md §2.2](../CLAUDE.md)，下游 subagent 的 prompt 演进归协作者维护权，但**代码托管在本项目仓库** ([src/agent/nodes/](../../src/agent/nodes))。当本地测试暴露的 bug 可通过改下游 prompt / 输入装配修复时，我们在这里 hotfix，并在本文件记录，以便：
> - 跟协作者下次 push 合并时不丢；
> - 必要时回退；
> - 形成"协作者下次 prompt 演进时应该带进去的强力数据点"。
>
> **备份约定**：每次动 [`src/`](../../src) 下任何文件，**先**把改动前版本 cp 到 [`../src_history/<YYYY-MM-DD>_<reason>/<file>.py`](../../src_history)（同日多次加 `_v2` / `_pre_X`）。
>
> **索引**：[CLAUDE.md §7](../CLAUDE.md) 文档表。

---

## 改动记录

### 2026-05-29 — 确定性 InterZone surface-pair 校验门(审阅 A 落地)

**Trigger**：2026-05-28 Codex [InterZone surface pairing 审阅](review/review/2026-05-28_interzone_surface_pairing_review.md) 两条 High：(1) surface 阶段后**缺确定性配对校验门**——`surface_converter.py` 只逐对象校验形状、不校验整张 `Outside Boundary Condition = Surface` 引用图;(2) 缺跨层楼板**覆盖**校验。配合 sm21 三模型实验:Sonnet 忠实复现 phase1 的 5cm 跨层抖动 → 切出 0.05m×3m 退化碎片 → EP 输入阶段 **段错 (exit 139)**,`.err` 空。EP 通过≠几何对、EP 段错前不写 `.err`,**"EP completed" 作唯一验收信号太晚太粗**。

**改动**(非下游 subagent prompt,属本项目侧**校验基础设施**;按 §6#5 仍备份 + 记录):
- **新增** [src/validator/interzone.py](../../src/validator/interzone.py)(纯 numpy,无新依赖):
  - `validate_interzone_surface_pairs(idf)` → 在装配好的 eppy IDF 上验:OBC=Surface 目标存在 / 目标本身 OBC=Surface / 互逆指回 / 单一引用(无多重 target)/ 配对面积匹配 / 单位法向相反(Newell)/ 楼板天花同 z 面 / **最小边长 ≥ 0.1m(退化碎片守卫,直接挡 Sonnet 段错那一类)**
  - `audit_interzone_surface_pairs(idf)` → 非失败汇总计数(总面数 / 各 OBC 计数 / 互逆对数 / issue 数),供 baseline run notes 记录(审阅 #4)
- **改** [src/mcp/tools/workflow.py](../../src/mcp/tools/workflow.py):`run_simulation` + `export_idf_only` 在 `manager.convert_all()` 后、跑 EP / 落最终 IDF 前调 `_check_interzone_pairs()`;有 issue → 返回 `success=False`(仍存 IDF 供检视),**不启动 EP**。读 `manager._idf`(live,只读)而非 `manager.idf`(deepcopy 一个 StringIO 已关闭的 IDF,会 `I/O operation on closed file`)。

**标定**(动手前拿 3 个已知 IDF 验,零误杀):
- sm21 OPUS(好,EP 完成)→ 0 issue ✅ 放行
- sm21 DEEPSEEK(EP 完成但几何最差/幽灵房)→ 0 issue ✅ 放行(幽灵房是"尺寸错"非"配对/退化错",配对图本身合法——印证 EP 通过≠几何对,此门只管 IDF 有效性)
- sm21 SONNET(段错)→ 4 issue ✅ 抓出 `F1_SM_Office_Ceiling_S2` 等 4 个 0.05m 退化碎片(正是 Codex 点名那条),`success=False` 挡在 EP 前
- sm_16_newarch glazingfix(好 anchor,135 面)→ 0 issue ✅ 放行
- `pytest` 5/5 通过。

**未做(审阅 A #2,需依赖)**:跨层楼板**覆盖完整性**校验(相邻层 footprint 求交、每个非零交集恰有一对、面积等于交集面积)需多边形求交;容器内 `shapely` 缺失,加依赖前与用户确认。Codex 自身优先级亦把 #1 排 #2 之前;且"配对各自合法但集体不完整"风险至今未真咬过。占位 follow-up。

**备份**:[src_history/2026-05-29_interzone_pair_validator/workflow.py](../../src_history/2026-05-29_interzone_pair_validator/workflow.py)(改前版本)。`interzone.py` 为新增文件无需备份。

**交协作者**:此门是确定性几何校验,与下游 prompt 正交;协作者下次合并下游代码时**保留**此门 + 校验器。若未来真出现合法 <0.1m 几何(罕见),调 `interzone.py` 的 `_MIN_EDGE`。

---

### 2026-05-12 — surface_agent z_floor / ceiling_height 修复

**Trigger**：sm_20 半人工流首跑（B1 强化版 intake）EP `Completed Successfully` 但仍有 10 个 `Base surface does not surround subsurface (CHKSBS) Partial-Overlap` warnings，集中在 F2 / F3 上层窗。诊断 IDF 发现：

- intake [fenestration_specs](../../test_data/SmallOffice/smalloffice_20/output/intake_output.json) 把 `absolute z_min/z_max` 写得**正确**（F2 窗 z=4.60..6.40）
- fenestration_agent **照写**进 IDF 窗 vertex
- 但 surface_agent **把墙建错了**：F2 wall vertex z 范围 = [3, 6]（高 3 m、底从 z=3 起算），不是应有的 [3.60, 7.20]
- 同时 zone_agent **建对**了 F2 zone `Z Origin = 3.60`
- 结果：zone Z Origin 与 wall vertex z 互相不一致；窗顶 6.4 > 墙顶 6 → CHKSBS partial-overlap

**真因**：[src/agent/nodes/surface.py](../../src/agent/nodes/surface.py) 的 `SURFACE_SYSTEM_PROMPT` 有两处问题：
1. system prompt 唯一的 worked example 是 "5m × 2m south wall ground to 2m tall" —— 误导 LLM 用小整数层高
2. surface_agent 只收到 `state.intake_output.surface_specs` 作为 user message；`z_floor` 和 `ceiling_height` 是写在 `zone_specs` 里的，**surface_agent 看不到**
3. 没有任何 instruction 告诉 surface_agent 去 zone_specs 找层高

DeepSeek pro 在这种缺信息条件下默认用 3 m 当层高，从 F1 z=[0,3] / F2 z=[3,6] / F3 z=[6,...] 这么累加。

**修复**（[src/agent/nodes/surface.py](../../src/agent/nodes/surface.py)）：
- **A. 输入装配**：surface_agent 现在同时收 `zone_specs + surface_specs`，包成两段（`=== ZONE_SPECS ===` / `=== SURFACE_SPECS ===`）
- **B. system prompt 加 "CRITICAL: per-floor z values come from zone_specs" 一节**：明文要求 `bottom z = z_floor`、`top z = z_floor + ceiling_height`；禁止默认 3 m
- **C. worked example 改为 F2_S1 南墙（z_floor=3.60, ceiling_height=3.60）**：覆盖 "3.60 m 不是 3 m" / "不同楼层可以不同 ceiling_height" / 上下层 InterZone z 配对

备份：[src_history/2026-05-12_surface_agent_zfloor_fix/surface.py](../../src_history/2026-05-12_surface_agent_zfloor_fix/surface.py)

**预期效果**：F2 / F3 wall vertex z 改用 intake 的真实 `z_floor` + `ceiling_height`；窗 z 范围天然落在墙 z 范围内；CHKSBS partial-overlap warnings 消除。

**验证**：sm_20 重跑（output 落 [test_data/SmallOffice/smalloffice_20/output_new/](../../test_data/SmallOffice/smalloffice_20/output_new)），对比 [`output/eplusout.err`](../../test_data/SmallOffice/smalloffice_20/output/eplusout.err) 看 CHKSBS warning 是否清零。

**协作者侧建议**：下次 prompt 演进务必带这一条进去 —— 没有"读 zone_specs 取 z_floor + ceiling_height"的硬指引，surface_agent 必默认 3 m。

---

## 与协作者交接

下次协作者推 prompt 更新前，建议先扫一遍本文件，确认下面这些 hotfix 仍然在他们的新 prompt 里：

| 日期 | 文件 | 关键改动 | 仍需保留？ |
|---|---|---|---|
| 2026-05-12 | [src/agent/nodes/surface.py](../../src/agent/nodes/surface.py) | 同时传 zone_specs + surface_specs；硬约束读 z_floor + ceiling_height；worked example 改 F2 | ✅ 是；丢了下次重现 CHKSBS partial-overlap |
