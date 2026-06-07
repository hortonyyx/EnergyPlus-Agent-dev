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

### 2026-06-07 — PartA 校正层 P0 接入 phase2 prompt

**Trigger**：识图建模质量主线（忠实建模 leg）落地。PartA 容差校正层 skill 文档库（[`skills/energyplus_mcp_twostep/phase2/PartA-correction/`](../../skills/energyplus_mcp_twostep/phase2/PartA-correction) 的 A0–A4 + README）已写 + 审 + 定稿（A0/A1/A2 经 Codex 审，A3/A4 为 P0）。需把它接进 phase2 实际执行。

**改动**（本项目侧 phase2 节点，非协作者下游 subagent；按 §6#5 备份 [`src_history/2026-06-07_phase2_partA_wiring/phase2.py`](../../src_history/2026-06-07_phase2_partA_wiring)）：
- [src/agent/phase2.py](../../src/agent/phase2.py) `build_phase2_messages`：从 skill 库载入 PartA-correction 5 篇（README + A0–A4，单一真源、不内联复制），作为 `===== RULE DOCUMENT: PartA-correction (Step 0) =====` 块加进 system prompt（置于 phase2/rules.md 之后、phase1 参考之前）。
- human 收尾指令加 **Step 0**：先对 phase-1 基元跑 A1（中线归一+z-stack）→ A2（规范轴集+跨层统一+吸附+链闭合+碎片防止）→ A3（仲裁补全，A4 先验仅在 A0/A3 门控下用），用**校正后**基元再走 rules.md Step 1→7。
- **P0 取舍**：输出**保持纯 IntakeOutput 不变**（不加 corrections[] audit wrapper，避免多吐 token 触发 64k 截断、最大化跑通率）；partA 作内部 Step 0 应用，效果靠输出几何（无 5cm 跨层碎片 / 中线轴 / 闭合链）+ thinking.txt 验证。**audit wrapper（corrections/conflicts/unsupported 落 sidecar）= 建评测 baseline 时的 fast-follow**（baseline 需"看错 vs 改错"归因）。

**影响范围**：仅 phase2 prompt 装配；输出契约不变（下游 9 subagent / cross_ref / validate / interzone 门全不受影响）。phase2 prompt 增大约 1.5–2 万字符（PartA 5 篇），DeepSeek thinking 可承受。

**验收**：在 sm21 / sm22 跑通（partA 应消除"同墙跨层 5cm 抖动→退化碎片"那类，InterZone 门更易过）；跑通后建评测 baseline。

---

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

**未做(审阅 A #2,需依赖)**:**覆盖完整性**校验。漏洞类型 = "本该是内部边界(楼上楼下之间的楼板 / 相邻 zone 之间的竖墙),但两侧都被标成对外(Outdoors/Adiabatic),于是这块区域根本不在配对图里"。per-pair 门查不到(它只审已声明的配对是否合法,这块没声明配对),EP 运行时也不报错(每个面单独看都合法,物理却凭空多了内外边界)。检测法 = 相邻层 zone footprint 求并→求交得"该被铺满的范围",所有水平 InterZone 配对多边形求并得"实际铺到的范围",求差≠空 → 报洞(竖墙同理按相邻 zone 公共边)。需多边形并/交/差。

**决策(2026-05-29,用户定调)**:**长期解走 `shapely`**(linux x86_64 wheel 自带 GEOS、无需系统库;天然支持 B5 的 L形/非凸/旋转外包,纯 numpy 矩形分解到 B5 必重写故不取)。**不急实现,当前仅标记**:风险("配对各自合法但集体不完整")至今未真咬过,Codex 亦把 #1 排 #2 前。落地时机 = 招到一个能真正暴露该洞的 case 坐实需求后,或 B5 非方形平面开工时一并做。届时 `pyproject.toml` 加 `shapely` + `uv sync` + 容器 rebuild。占位 follow-up。

**风险随复杂度升级评估(2026-05-29,定落地时机的依据)**:此缺口的概率不是常数,随几何复杂度抬升,拐点正好在路线图前方——
- **当前(矩形齐平,各层铺满同一 footprint)= 低**:"某区域该内部"几乎无歧义;漏配多半表现成悬空引用(dangling target),被 per-pair 门 #1 项抓,不会变成干净的"两侧都标 Outdoors"洞。
- **B5 非方形(L/U 形)= 明显上升**:相邻层 footprint 交集是非平凡多边形,下层天花**一部分合法地是 Outdoors(屋面)、一部分是内部楼板**;模型须正确切分,切错时"错误长得就像一个合法 Outdoors 面"——正是 per-pair 门看不见的形态。
- **B6 退台/挑空 = 成为首要风险**:退台下层露出屋面本就该 Outdoors、挑空该层本就无楼板;"这里到底有没有楼板"全靠模型判断,判错=干净的覆盖洞,per-pair 门完全盲。只有"footprint 求交必须被铺满"的全局覆盖约束能区分合法 Outdoors vs 错误 Outdoors。
- 结论:现在是**理论风险**,B5 转**现实风险**,B6 是**主要风险**。故"B5 开工时一并做 shapely 覆盖校验"卡在风险从理论转现实的拐点——早做无 case 可验、晚做 B5 真出洞。

**备份**:[src_history/2026-05-29_interzone_pair_validator/workflow.py](../../src_history/2026-05-29_interzone_pair_validator/workflow.py)(改前版本)。`interzone.py` 为新增文件无需备份。

**交协作者**:此门是确定性几何校验,与下游 prompt 正交;协作者下次合并下游代码时**保留**此门 + 校验器。若未来真出现合法 <0.1m 几何(罕见),调 `interzone.py` 的 `_MIN_EDGE`。

**审阅回环修正(2026-05-29,Codex [interzone_pair_gate review](review/review/2026-05-29_interzone_pair_gate_review.md))**:
- #1 High 修复:竖直墙配对之前只查 Floor/Ceiling/Roof 的 z 共面,漏了 Wall↔Wall(等面积/反法向但分处平行面也能过)→ 改成对所有互逆对做通用点到面共面校验(`_max_point_to_plane`,`_PLANE_TOL=0.02m`)。重标定 4 个真 IDF 零误杀。
- 加 [tests/test_interzone.py](../../tests/test_interzone.py) 12 个 mock 单测(含竖直墙偏移类);reciprocal 计数改数真实互指;`_check_interzone_pairs` 去重(validate 只跑一次)。全套 20/20。

### 2026-05-29 — intake_node 两步串行(B1.5.c,本项目侧核心非下游)

> 记此条仅为协作者合并 `src/` 时知情:`intake_node` 改为两步分发(短路 / phase1 矢量→phase2 / legacy 单步),新增 [src/agent/phase2.py](../../src/agent/phase2.py)(phase2 单一实现,raw OpenAI + thinking,读 `llm.yaml:intake_phase2`)。下游 9 subagent 契约(`IntakeOutput` 11 字段)**不变**。详见 [review/review/2026-05-29_twostep_intake_node_switch_review.md](review/review/2026-05-29_twostep_intake_node_switch_review.md) 的 Disposition(Codex 审,2 High + 2 Med + 1 Low 全修)。备份 [src_history/2026-05-29_intake_node_twostep/intake.py](../../src_history/2026-05-29_intake_node_twostep/intake.py)。

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
