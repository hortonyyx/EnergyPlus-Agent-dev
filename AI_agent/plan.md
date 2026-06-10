# 行动清单

> **术语对照（2026-06-10 改名后）**：本文历史叙述沿用旧称——phase1=0_reading（识图）/ phase2a=1_correction（校正）/ phase2b 已拆为 2_modelling+3_split_pairing（几何，代码内核）+4_mep（物理）+5_intakeoutput（装配）；代码模块 `src/agent/pipeline.py`（`run_pipeline`）。详见 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)。

> **当前状态**：A 段「代码跑通 / 架构迁移」全部闭环（[CLAUDE.md §5.3](CLAUDE.md)）。B 段「识图建模能力提升」阶段 1（B1 旧 skill 迁移）✅ 完成 2026-05-12（[CLAUDE.md §5.5](CLAUDE.md)）。
>
> **2026-05-12 晚 — 两步法 POC PASS（[floorplan_redraw_strategy.md §9](capability/floorplan_redraw_strategy.md)）**：sm_20 全套两步法 + 下游 + EP 真跑验证；架构通透性 + 识图泛化 + 微调可行性同时验证。**新主线 = B1.5 两步法立项**（最高优先级，详见下节）。B2-B4 评测基线规范化与之并行推进。idfpy 替换主线（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）等协作者交付，仍搁置。
>
> **2026-06-10 — 0–5 管线 EP 跑通 + B 结案 + 路线锚定**：schedule 段错根因修（确定性门）+ 1_correction 稳定性硬化（重试+窗自检）；**sm21（2层）+ sm23（单层）EP cleanly 跑通**（详见 [CLAUDE.md §5.11 后 banner](CLAUDE.md)）。**用户定路线**：① Fable 5 完整体检 0–5 找硬伤（[review request](logs/review/request/2026-06-10_pipeline_0-5_full_audit_request.md)）② sm20+sm21 干净 anchor → 建 **test_baseline**（B2–B4）③ 接**国产 VLM API** 全流程（0_reading 自动化，B8 提前）④ **依次升级建筑复杂度**强化 0–5 各环节（B5–B7，建议清单 [pipeline_0-5_capability_upgrade_suggestions.md](architecture/pipeline_0-5_capability_upgrade_suggestions.md)）。
>
> 优先级：P0（立即）/ P1（一周内）/ P2（依赖 P0/P1）。

---

## 推荐执行顺序（2026-05-12 晚 — 两步法 POC PASS，主线切 B1.5）

```
阶段 1 [B1] ✅ 完成 2026-05-12
   旧 skill 能力迁移 + surface_agent z_floor hotfix。sm_20 半人工单步流
   EP cleanly 跑通；架构通透性 anchor 从 sm_16_newarch 切到 sm_20。

【新】阶段 1.5 [B1.5]：两步法 intake 立项 ← 当前最高优先级（2026-05-12 晚起）
   sm_20 两步法 POC PASS（[floorplan_redraw_strategy.md §9](capability/floorplan_redraw_strategy.md)）。
   下一步：异图 POC v2（噪声图）+ intake_node 重写串行调用两 phase +
   skills/intake_pipeline 持续迭代 + 评测嵌入。详见本文 B1.5 节。

阶段 2 [B2-B4]：评测基线规范化（与 B1.5 并行推进）
   建立测试评测基线：GT 集 / 自动评测脚本 / Opus baseline /
   校对方案 / 测试记录规范化 / token 统计协议升级。
   注：B1.5 把矢量 JSON 作为 phase2 输入和 GT 数据集字段之一，B2-B4 评测
   脚本要覆盖矢量 JSON diff（不仅 IntakeOutput diff）。

阶段 3 [B5-B7]：能力升级
   1. 引入非方形平面（如 L 形）
   2. 升级到全局坐标系做退台、挑空
   3. 引入规范化绘图实现门 / 窗 / 楼梯等识别
   注：B5-B7 都从两步法路径展开（phase1 schema 词典扩展 / phase2 规则扩展）。

远期 [B8-B9]：开源模型 + LoRA Pivot（[reference/pivot_criteria.md](reference/pivot_criteria.md)）
   两步法天然分两个微调目标：phase1 = (图, 矢量 JSON) VLM 微调；
   phase2 = (矢量 JSON, IntakeOutput) 纯文本 LLM 微调。
```

**当前最高优先级 = B1.5 两步法立项**。B2-B4 评测基线并行推进，但评测脚本要从一开始就支持
矢量 JSON 中间层。idfpy 替换主线仍按决策搁置。

---

## A. 代码跑通（已完成 ✅，2026-05-06）

| 项 | 描述 | 状态 |
|---|---|---|
| A1 | IntakeOutput schema 与协作者 trace 对齐 drift 检查 | ✅ 11 字段 / BuildingSchema 8 / SiteLocationSchema 5 全部一致，无 drift。详见 [CLAUDE.md §5.3.A](CLAUDE.md) |
| A2 | per-subagent LLM 配置（intake / default 两 section） | ✅ [llm.yaml](../src/configs/llm.yaml) 多 section + [llm.py:create_llm(node_name)](../src/agent/llm.py) 路由。详见 [CLAUDE.md §5.3.C](CLAUDE.md) |
| A3 | 端到端验收脚本 | ✅ [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py)（三入口：全自动 / `--intake-from` / `--intake-only`），原 A3 "preview_geometry 截止 fenestration" 设想被全图脚本替代——下游 DeepSeek 跑近免费，不必砍 |
| A4 | 文档同步（CLAUDE.md / architecture.md / new_case_guide.md） | ✅ 全部修订；[CLAUDE.md](CLAUDE.md) 410 → 175 行精简；[guides/new_case_guide.md](guides/new_case_guide.md) 重写为半人工 7 步流程 |

---

## B. 识图建模能力提升（视觉能力主线）

> **能力主战场是 [architecture.md §3](architecture/architecture.md) 表格里"几何依赖：强"的 5 个字段**：`building.name` / `site_location` / `zone_specs` / `surface_specs` / `fenestration_specs`。其余 6 个字段从文本可推，不是瓶颈。
>
> 主指标：[reference/pivot_criteria.md](reference/pivot_criteria.md) 视觉层阈值 — zone F1 ≥90% / 尺寸误差 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80。
>
> **三阶段总览**：B1 恢复 → B2-B4 评测基线规范化 → B5-B7 能力升级 → B8-B9 远期 pivot。详见各节。

---

### B0. [P0] 端到端首跑（验证半人工流）— ✅ 完成 2026-05-07

**实跑案例**：`smalloffice_16_newarch`（复制 sm_16 用于测试架构）

**已 PASS**：
- 14 节点机制全部跑通（intake 短路 → phase1 → cross_ref_foundations → construction → surface → fenestration → phase3 → cross_ref_complete → validate → simulate）
- L1 Pydantic ✅ / L2 cross_ref errors=[] ✅
- DeepSeek tool-calling 多轮 ReAct 通（`thinking={'type':'disabled'}` 修复有效）
- L4 simulate 真跑（手工修一行 Construction 后）：`EnergyPlus Completed Successfully` 全年 RunPeriod / 0 severe / 9 warnings / 14.8 秒
- 总耗时 ~28 min（surface ~4min / construction ~20min 占大头）

**架构结论**：✅ 半人工 intake → 自动下游 → IDF → EP 全链路机制 100% 通；零架构层 bug。剩余问题全是单一 subagent prompt 级建模质量，属 Plan B / idfpy 范畴。

**真跑 simulate 关键发现**（见 [§C](#c-暂搁置依赖外部进展不安排时间) fenestration glazing 条）：
- T-vertex 实证**不卡 EP**（warm-up 0 几何 severe）→ B0' 关闭
- 真 fatal = fenestration_agent 把 `WindowMaterial:SimpleGlazingSystem` 当一层叠加 → window 求解器 NaN
- 手工修 Construction 单层引用后 EP PASS；artifacts 在 [`smalloffice_16_newarch/output/ep_run_glazingfix/`](../test_data/SmallOffice/smalloffice_16_newarch/output/ep_run_glazingfix)

**遗留 todo**（已沉到 [§8.1](CLAUDE.md)）：
- [ ] sm_17 端到端再跑一次（不同图纸验证可复用性，不再被 T-vertex 阻塞）
- [ ] OpenStudio 验收 sm_15 / sm_16 / sm_17 / sm_16_newarch（用户填 `dimensions_check`）

---

### B0'. ~~[P0] surface_agent T-vertex 缺失~~ — ✅ 关闭 2026-05-07

**结论**：T-vertex 缺失**不是 EP 阻塞**，本节作废保留为决策记录。

**2026-05-07 真跑实证**（sm_16_newarch IDF 直接喂 EnergyPlus 25.2.0）：
- validator 临时放宽（raise→warning）后，IDF 顺利落盘，无下游拦截
- EP warm-up 阶段无任何 surface area mismatch / heat balance unbalanced / 几何相关 severe
- 与 [memory feedback_validator_closure_loosened](feedback_validator_closure_loosened) 判断一致：EP 只检查 surface-pair InterZone 配对，不要求 polyhedral manifoldness

**留在 codebase 的临时措施**：
- [src/validator/data_model.py validate_geometry_closure](../src/validator/data_model.py) 永久保持 `logger.warning`，不恢复 raise
- 待 idfpy 切换时整体删 validator，这条临时性约束自然消失（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）

**作废**：原 A 改 prompt / B 后处理 / C 放宽 validator 三方案，不再做。

---

### B0''. [P1] sm_17 端到端首跑（异图验证）

**任务**：
- 用户在新 Claude Code 会话按 [new_case_guide.md §四](guides/new_case_guide.md) 跑 Step 4 → 产 `smalloffice_17/output/intake_output.json`
- 助手按 [§5.0](guides/new_case_guide.md) 触发协议跑下游
- 触发 `记录这次跑 sm_17 e2e_v1` 落 baseline

**验收**：与 B0 类似；关注 sm_17 是否暴露**新**类型 bug。
- 注意：simulate 跑通**不是**严格目标 —— 当前已知 fenestration glazing layer 兼容性 bug（[§C](#c-暂搁置依赖外部进展不安排时间)）会让 EP fatal，需手工修一行 Construction 才能跑（参考 sm_16_newarch glazingfix），或接受 IDF 落盘 + OpenStudio 视察作为终验
- 重点观察项：几何（zone 数 / 楼层 / 外包 / WWR）正确性、是否有**新**类型 prompt-level bug

**依赖**：无（T-vertex 阻塞已解除；fenestration glazing bug 已知非新阻塞）

---

## 阶段 1 — 恢复（✅ 完成 2026-05-12）

### B1. [P0] 旧 skill 能力迁移到新架构（恢复 sm_16 旧建模水平）— ✅ 完成 2026-05-12

**背景**：旧架构（[skills/energyplus_mcp/](../skills/energyplus_mcp) + Claude Opus 单会话 + skill 分步约束）能在 sm_16 上拿到准确建模。新架构（半人工 Step 4 prompt + 9 subagent 自动下游）的 intake 路径虽然已切到 [src/agent/nodes/intake.py](../src/agent/nodes/intake.py#L34) + `skills/energyplus_mcp/*.md` 规则文档库，但在迁移初期仍是简版，**没把旧 skill 的分步识图 / 绘图标注 / 自检约束等内容完整迁过来** → sm_16_newarch 建模质量不及旧架构 sm_16 baseline。

**第一原则**：**先恢复，再升级**。新架构必须先到达旧架构能做到的水平，才有资格谈 B5-B7 的能力扩展。

**任务**（全部完成）：
- [x] 审计旧 skill 内容 → codex 完成的 [`energyplus_mcp_migration_audit_2026-05-11.md`](energyplus_mcp_migration_audit_2026-05-11.md) 列出 4 个 Gap
- [x] 增强新架构 intake 规则文档库（3 个 md 文件全改）：
  - [`energyplus_mcp_prompt.md`](../skills/energyplus_mcp/energyplus_mcp_prompt.md) §D4.2 per-floor window chain hard rule / §D4.3 absolute world z 公式 + 3 层 worked example / §D5 unsupported-case 双标统一 / Mandatory Internal Derivation Order 9 步顺序
  - [`intake_output_contract.md`](../skills/energyplus_mcp/intake_output_contract.md)（新增）：surface_specs cross-floor split-pairing required enumeration / fenestration_specs Right-side chain pattern N-window 通式 + 3 worked example (A 单窗等高 / B sm_20 corridor 不等高 / C 同层堆叠双窗) + counter-example + 自检规则 `z_max_i - z_min_i == win_h_i`
  - [`zonetool_prompt.md`](../skills/energyplus_mcp/zonetool_prompt.md) 恢复 4 立面 CCW-from-outside vertex synthesis 表 + Floor 2 南窗 worked example
- [x] `Floor_N_*` 模板禁用规则合并到 intake_output_contract.md "No Compression, No Placeholders"
- [x] **下游 surface_agent hotfix**（[downstream_agent_changes.md 2026-05-12 条](logs/downstream_agent_changes.md)）：[`src/agent/nodes/surface.py`](../src/agent/nodes/surface.py) 同时传 zone_specs + surface_specs 到 agent，加 "per-floor z values come from zone_specs" 硬指引，worked example 改 F2_S1 (3.60 m)；备份 `src_history/2026-05-12_surface_agent_zfloor_fix/`
- [x] 用 sm_20（= sm_19 plans）跑半人工流双版对照：
  - `test_data/SmallOffice/smalloffice_20/output/`（B1 only，仍 10 CHKSBS partial-overlap）
  - `test_data/SmallOffice/smalloffice_20/output_new/`（B1 + surface fix，0 CHKSBS，EP cleanly 完成）

**工作量**：实际 ~半天集中产出（audit + 文档撰写 + surface hotfix + 双版跑 + diagnose）

**验收**：
- ✅ sm_20 半人工流 EP `Completed Successfully` / 0 severe / 0 fatal / 14 无害 warning
- ✅ 上层窗 z 严格落在父墙 z 范围内（F2 wall z=[3.60,7.20]，F2 窗 z=[4.60,6.40]）
- ✅ cross-floor split-pairing 无 `RoofCeiling references not-found` fatal
- ⚠️ 残留：intake 对东西立面 F3 corridor 窗有偶发 `z_max = z_min + top_gap` 计算 slip（写 9.60 应 10.60）—— intake_output_contract.md 已补 N 窗通式 + 反例 + 自检，下次跑新 case 应被挡住；sm_20 落盘错值保留作 audit anchor

**架构通透性 anchor 更新**：sm_20 取代 sm_16_newarch（后者要手工修一行 Construction）。

---

## 阶段 1.5 — 两步法 intake 立项（2026-05-12 晚起，最高优先级）

### B1.5. [P0] 两步法 intake 主线立项

**背景**：[`floorplan_redraw_strategy.md`](capability/floorplan_redraw_strategy.md) §9 — sm_20 POC PASS 2026-05-12 晚。两步法（phase1 矢量化重绘 → phase2 拓扑建模）相对单步法的硬证据：

- **F3 corridor 窗 z 修正**：两步法两条路径都准（z=10.60），anchor 单步法错（z=9.60，B1 残留 slip 再现）。phase1 把识图结果锁定在 `y_range_m: [8.20, 10.60]` → phase2 无机会重做坐标推导
- **DeepSeek 路径下游 EP cleanly 跑通**：0 severe / 9 warning / 8.49s 全年仿真。证明两步法 IntakeOutput **不破坏现有下游契约**
- **Opus 路径暴露 phase2_rules 漏洞**：InterZone construction asymmetry（已在 v1.3 修），同时贡献了 10 条 schema gap followup notes — 规则迭代信号丰富
- **微调可行性**：phase1 (图, 矢量 JSON) 是 VLM 结构化视觉抽取（预训练分布近邻）；phase2 (矢量 JSON, IntakeOutput) 是纯文本推理（不需 VLM，可用任意小模型）；两数据流独立迭代

**第一原则**：**先把两步法管线 SmallOffice_TwoStep 走通，再考虑切主线 intake_node**。POC 用 sm_20（规整办公楼，schema 舒适区）通过，但不代表泛化能力强。

**任务**：

#### B1.5.a [P0] POC v2 — 异图泛化压力测试 — ✅ 首个异图 PASS 2026-05-28（sm21）

> **结果（2026-05-28，sm21）**：2 层办公异图（15×8 m，家具/门噪声）全套两步法 EP `Completed Successfully` / 0 severe / 0 fatal / 6 无害 warning / 15 窗。phase1（冷启 Opus 子代理）重绘忠实、误差预算守住；phase2（DeepSeek 盲跑）首跑暴露 **phase2 规则缺口**：`material_specs` 漏声明具名 glazing 材料、把玻璃只写进 `construction_specs` 内联 → construction 子代理找不到材料正确跳过 `Default_Window` → 0 窗 → EP 段错。**根因在咱们侧 phase2/rules.md（非协作者下游 prompt）**。补 Step 5 "material ↔ construction split" 硬规则后重跑 → PASS。sm21 成为继 sm_20 的第二个干净 EP anchor。详见 [CLAUDE.md §5.7](CLAUDE.md) + [twostep memory]。**B1.5.c（intake_node 串行重写）就此解禁**。

> 设计框架已在 [`floorplan_redraw_strategy.md §10`](capability/floorplan_redraw_strategy.md)（2026-05-22 讨论）收敛：测「信息噪声 / 选择性提取」而非「全局像素降质」；phase1 走选择性提取(B) + 门洞补成连续墙；zone 重划分归 phase2。

- [ ] **图纸准备**（用户）：矩形几何同 sm_20 级 + 信息杂物（家具 / 铺装 / 纹理 / 楼梯 / 轴网圈 / 房间文字）+ **每房间 1-2 个门** + **1-2 处故意遮挡某段尺寸标注** + testdata_prompt.json（楼层/区/外包/WWR）
- [x] **schema v1.3 amendment（先于跑批，依据 §10.4）** ✅ 2026-05-25：`phase1_vector_schema.md`（后于 2026-05-26 拆分为 [`phase1/`](../skills/intake_pipeline/phase1) 三份：guide/reading_guide/pen_library）§2 "开洞打断成两段"→"门洞补成连续墙 + 留痕"+ 新增 §2.1 四条护栏；门处理改"识别以驱动补墙、不出 door 笔、note 记 heal"；`uncaptured_visual_elements` 提为**必填**（扩为"凡看到但没画的都登记"，含主动排除杂物 + heal 门）；`door`/`arc` 退出词典；同步 [`phase1/prompt_template.md`](../skills/intake_pipeline/phase1/prompt_template.md) 纪律段。备份 `Skill_history/2026-05-25_twostep_phase1_v1.3_door_healing/`
- [x] 跑两步法（phase1 子代理 + phase2 DeepSeek）+ 下游 + EP ✅ sm21 PASS（修 glazing material 规则后）
- [ ] **判分项**（§10.2 + 选择性提取观察点）：
  - 杂物→结构假阳性（家具/铺装/纹理被当 wall/window）⛔ 最致命
  - 漏真墙/真窗假阴性 ⛔
  - 尺寸链污染（非结构标注进 `dimensions[]`）⛔
  - 遮挡下是否老实填 `null`（诚实性）⚠️
  - `uncaptured_visual_elements` 是否真触发 ⚠️
  - 门是否补成连续墙、没误补无门开口、留了痕 ⚠️
  - phase2 在更复杂矢量 JSON 上能否保持 Step 6 PASS
- [x] 跑通后落 `test_data/SmallOffice_TwoStep/<new_case>/` ✅ sm21；跑挂补规则 ✅ phase2/rules.md Step 5 glazing material split（备份 `Skill_history/2026-05-28_phase2_glazing_material_rule/`）
- [ ] 再跑 1-2 张异图坐实泛化（可挑 phase1_generalization 的矩形图 test1/test7 补 testdata 跑全链路）
- [x] 注（2026-05-26 已修）：[`run_pipeline_deepseek.py`](../Tool_scripts/run_pipeline_deepseek.py) 原写死 `PHASE1_FILES`，已改 `_discover_phase1_files()` 扫 `phase1_vector/*.json`（楼层数字序 → 立面 → supp/section），不再需手改

#### B1.5.b [P0] phase1 / phase2 skill 持续迭代

**phase1 辅助 skill = 识图库 + 笔库（两面，喂 POC v2；2026-05-25 框架确立）**：
- [ ] **识图库（新产物，先做一版）**：一般建筑图画法知识库——墙的多种画法（粗黑线 / 双线 / 影线 / 灰填充）、窗的表达、家具 / 铺装 / 轴网圈 / 楼梯符号长相。目标 = 提升 phase1 跨**风格 / 画法**泛化识别力（认出来才能按选择性提取正确画 keep-set、把杂物排除进 `uncaptured`）。与 [B7](#b7-p1-能力升级-3--规范化绘图--门--窗--楼梯识别)「规范化绘图」**反方向互补**（B7 约束输入按规约画；识图库教 phase1 读杂多规约），别重复造
- [ ] **笔库（定调）**：审视 pen 集——留哪些、多少够。准则 = [floorplan_redraw_strategy.md §10.3](capability/floorplan_redraw_strategy.md) 最小词典 + 按需提拔，提拔触发器 = 「phase2 是否需要这条信息」。守最小集，不为家具 / 门造笔（门 heal、家具 exclude）
- [ ] 跑 POC v2 时用识图库 + 笔库观察：phase1 在噪声 / 异风格图上的 keep-set 分类准确率 + 杂物排除率

**phase2_rules 规则合并（吸收 Opus phase2_followup_notes 可机械化项）**：
- [ ] cross-floor sub-surface 命名约定（如 `<parent>_seg<n>`）
- [ ] 走廊负载密度（30 m²/p / 5 W/m²）vs 办公室典型值
- [ ] building.Name 大小写策略（推荐 PascalCase）
- [ ] site.Name 规范化为 `<City>_<ISO2>`
- [ ] Schedule:Compact day-type 名（EnergyPlus 接受 `Weekdays/Weekends/Holiday/AllOtherDays`）

> 注（2026-05-25 起）：`skills/intake_pipeline/` 是纯当前版本 spec，**文件内不再写版本号 / changelog / 缘起 case**（决策史归 git commit + 本 plan + [capability/floorplan_redraw_strategy.md](capability/floorplan_redraw_strategy.md)）。每次改 skill 仍按 [CLAUDE.md §6#5](CLAUDE.md) 备份到 `Skill_history/`。

#### B1.5.c [P0] `intake_node` 重写为两步串行 — ✅ 完成 2026-05-29（[CLAUDE.md §5.8](CLAUDE.md)）
- [x] [`src/agent/nodes/intake.py`](../src/agent/nodes/intake.py) 三路分发：短路 `--intake-from` / `phase1_vector_dir`→phase2 / legacy 单步；`--intake-from` short-circuit 保留
- [x] [`src/configs/llm.yaml`](../src/configs/llm.yaml) 加 `intake_correction`（text-only, thinking enabled）；`intake_phase1`（VLM）预留注释段（全自动 phase1 待 pivot）
- [x] 备份 `src_history/2026-05-29_intake_node_twostep/`，[logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 加记录
- [x] [`scripts/run_full_pipeline.py`](../scripts/run_full_pipeline.py) 加 `--reading-from`（半人工 phase1 矢量 → intake_node 跑 phase2）；保留 `--intake-from`
- [x] **附加**：per-case 模型配置（`<case>/llm.yaml` 经 `EP_AGENT_LLM_CONFIG` 覆盖全局，`--init-llm-config` 拷模板）；e2e 首次完整跑通新架构

#### B1.5.d [P0] `run_pipeline_deepseek.py` 迁入主线 — ✅ 完成 2026-05-29
- [x] 核心提为 [`src/agent/pipeline.py`](../src/agent/pipeline.py) 单一实现（`_fix_js_concat` + thinking enabled + JSON-only 直出 + `discover_phase1_files`），`intake_node` 与脚本共用、不漂移
- [x] `ensure_schema_initialized()` 内置进 `run_phase2`（任何调用方安全）；[`run_pipeline_deepseek.py`](../Tool_scripts/run_pipeline_deepseek.py) 收成薄 CLI 包装

#### B1.5.e [P0] `new_case_guide.md` 正式化为两步流程 — ✅ 完成 2026-05-29
- [x] [`new_case_guide.md`](guides/new_case_guide.md) 正式版：Step 4 phase1 半人工 + Step 5 一次性自动（phase2+下游+EP）+ §5.1 per-case 模型配置 + Step 6 InterZone 门验收层 + dev临时模式vs正式模式边界
- [x] phase1/phase2 启动 prompt 并入 [`new_case_guide.md`](guides/new_case_guide.md) 附录 A/B；临时 `new_case_guide_twostep.md` **已删**（guide 完全并轨）；旧单步法版备份 `logs/backup/.bak_2026-05-29`

#### B1.5.g [P0] InterZone 确定性几何门 — ✅ 完成 2026-05-29（审阅 A，[CLAUDE.md §5.8.B](CLAUDE.md)）
- [x] [`src/validator/interzone.py`](../src/validator/interzone.py) 接进 [`WorkflowTool`](../src/mcp/tools/workflow.py) EP 前 fail-fast；2 份 Codex review 全修、re-verify 全 PASS；测试 5→23
- [ ] 残留：**覆盖完整性校验**（抓"本该是内部边界、两侧却都标 Outdoors/Adiabatic、于是不在配对图里"的洞——per-pair 门 + EP 都查不到）。**决策 2026-05-29：长期解走 `shapely`，不急实现、当前仅标记**（风险未真咬过；落地时机 = 招到能暴露该洞的 case，或 B5 非方形平面开工时一并做）。详见 [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 2026-05-29 条

#### B1.5.f [P1] 评测嵌入
- [ ] phase1 矢量 JSON diff 评测（与 GT 数据集 v0 字段对齐）
- [ ] phase2 IntakeOutput diff 评测（沿用 B3 设想）
- [ ] 误差归因机制：识图错 ↔ 推理错可自动归类

**工作量估算**：B1.5.a ~1 周（异图 POC + 规则迭代滚动）；B1.5.b ~半周；B1.5.c ~1 周（intake_node 改写 + 测试）；B1.5.d ~半天；B1.5.e ~半天；B1.5.f ~1-2 天（依赖 B2-B4 评测脚本基础）。总 ~3 周。

**验收**：
- 至少 3 个 case（含异图）两步法全链路 EP cleanly 跑通
- `intake_node` 重写后主线 `run_full_pipeline.py <case>` 自动跑两步
- 评测脚本能区分 phase1 识图错 vs phase2 推理错

**依赖**：B1 ✅（已完成）

---

## 阶段 2 — 评测基线规范化

### B2. [P0] GT 数据集（M1 milestone）

**任务**：
- 在每个 case 目录下加 `gt.json`（不另起 `AI_agent/datasets/`，与素材就近）
- 起步集：sm_13 / sm_14 / sm_15 / sm_16（已有人工 baseline 的 4 个），后续扩到 ≥10 case
- 字段（最小集）：

  ```json
  {
    "zones": ["GF_Lobby", "GF_Atrium", "..."],
    "num_floors": 5,
    "zones_per_floor": {"GF": 6, "F2": 12, "...": "..."},
    "footprint_W_m": 40.0,
    "footprint_D_m": 30.0,
    "facade_wwr": {"South": 0.40, "North": 0.25, "East": 0.40, "West": 0.25},
    "special_zones": {
      "atrium": ["GF_Atrium", "F2_Atrium"],
      "core":   ["GF_Core"],
      "server": ["F2_East_Server"]
    }
  }
  ```

- 标注源：手动从 testdata_prompt.json + 已存 baseline + OpenStudio 截图反推

**工作量**：~2 天（4 case × 0.5 天）

**验收**：
- `test_data/SmallOffice/smalloffice_{13,14,15,16}/gt.json` 都存在且字段齐
- 与 [test_baseline/](../test_data/test_baseline) 现有数据交叉对验

**依赖**：B1 完成（确保新架构识图能力已恢复，评测才有意义）

---

### B3. [P0] IntakeOutput diff 评测脚本（M2 milestone）

**任务**：
- 新建 `AI_agent/eval/intake_diff.py`：
  - 输入：candidate IntakeOutput JSON 路径 + gt.json 路径
  - 解析 candidate 的自然语言 specs（regex / 二次 LLM 抽结构）
  - 输出指标：

    | 指标 | 计算 |
    |---|---|
    | `zone_f1` | candidate zone 名集合与 GT 的 F1 |
    | `num_floors_match` | 整数对错（0/1）|
    | `zones_per_floor_mae` | 每层 zone 数绝对误差均值 |
    | `footprint_W_err_m` / `footprint_D_err_m` | 外包尺寸绝对误差 |
    | `wwr_mae_pct` | 各立面 WWR 绝对误差均值（百分点）|
    | `special_zone_f1` | atrium / core / server 等特殊 zone 检测 F1 |

  - 输出 CSV 到 `test_data/test_baseline/runs/<date>_<model>_<case>/eval.csv`
- README 到 `AI_agent/eval/README.md`

**工作量**：~1 天

**验收**：
- `python -m AI_agent.eval.intake_diff --candidate <path> --gt <path>` 跑出指标
- 用任一已存 baseline 的 `intake_output.json` + 对应 GT 跑通

**依赖**：B2 数据就位

---

### B4. [P0] Opus baseline 重建 + 校对方案 + token 协议升级（M3 milestone）

**A. Opus baseline 重建**：
- 半人工流：用户在 Claude Code 会话按 [new_case_guide.md §四](guides/new_case_guide.md) 跑全部 GT case 一次（4 case × ~10 分钟人工 = ~半天）
- 每 case 产出 `intake_output.json`
- 助手跑 B3 `intake_diff` 对每 case 产 metrics CSV
- 汇总到 `test_data/test_baseline/runs/<date>_opus_baseline/summary.csv`

**B. 校对方案规范化**：
- 在 [test_data/test_baseline/README.md](../test_data/test_baseline/README.md) 加一节「校对方案」：
  - 自动校对项：B3 `intake_diff` 输出的 6 个指标
  - 半自动校对项：OpenStudio 几何视察（用户填 `dimensions_check`）/ IDF 落盘后 EP 真跑的可仿真性
  - 人工校对项：特殊 zone 命名是否符合规范 / surface 邻接是否符合常识
- 在 baseline 目录骨架加 `eval.csv`（B3 自动产出）+ `manual_check.md`（人工填）两个新文件
- 触发协议：`记录这次跑 <case> <tag>` 流程加入 B3 自动评测步

**C. Token 协议升级**（原 B0''' 并入此处）：
- [test_baseline/README.md §4.1 / §4.3](../test_data/test_baseline/README.md) 强制 `/context` 作 `tokens.total` 唯一权威源是为旧 `yaml_to_idf_v1`（Opus 单会话）设计；半人工流下不再单一来源：
  - Opus 端在用户 Step 4 临时会话 `/context`（手动粘）
  - 下游 9 subagent 走 DeepSeek API（不在任何 `/context`）
  - 助手协调会话与任务无关，不计入
- 任务：
  - [ ] [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 加 LangSmith / DeepSeek API usage 收集 hook → 落 `<case>/output/downstream_token.json`
  - [ ] [test_baseline/README.md §4.3](../test_data/test_baseline/README.md) 拆 `4.3a yaml_to_idf_v1` / `4.3b halfmanual_v1` 两套触发清单
  - [ ] `tokens.json` schema 加 `intake_total` / `downstream_total` / `total` 三字段
  - [ ] 已存半人工 anchor（`2026-05-07_sm_16_newarch_v4pro_no_sim_v1`）回填 `downstream_total`（如能从 DeepSeek 账单查到）

**工作量**：~1 天（A 半天用户人工 + 助手脚本 / B 半天 / C 半天）

**验收**：
- summary.csv 给出 zone_f1 / 尺寸误差 / WWR 误差等所有指标均值
- 校对方案落 README + baseline 目录骨架
- 下次跑半人工 case 时 `tokens.json` 自动填齐，`/context` 不再阻塞
- 与 [pivot_criteria.md §4.4](reference/pivot_criteria.md) 阈值对齐 → 看现状离阈值多远

**依赖**：B1 + B2 + B3 + 用户重复 Step 4 四次

> 注：原 plan.md "Anthropic API 直跑 4 case" 方案因用户无 API key 已废；改为半人工。

---

## 阶段 3 — 能力升级

### B5. [P1] 能力升级 1 — 非方形平面（如 L 形 / U 形）

**背景**：当前 sm_13-17 全是矩形平面。真实建筑常见 L 形 / U 形 / 凹凸异型。需要 INTAKE_SYSTEM_PROMPT + zone_specs / surface_specs 拓展支持任意闭合多边形外包。

> **架构方向（2026-05-29 会话收敛，两腿并行）**：B5 是 split-pairing/覆盖洞风险从"理论"转"现实"的拐点。处理它有两条**并行**的腿（**不二选一**）：
> - **忠实建模 leg**（[capability/recognition_modeling_capability.md §8](capability/recognition_modeling_capability.md)）：phase2 容差重生成保留真实几何，给 prompt 加非方形切分规则 + 仲裁/常识。有 beyond-EP 产品价值（图纸→建筑模型），**继续落地**。
> - **再拓扑 leg**（[architecture/geometry_first_zonification.md](architecture/geometry_first_zonification.md)）：切分/配对下沉为「平面再拓扑（热区积木）+ 确定性几何内核」，覆盖升为构造不变量；与 idfpy 同期做最省力。**作强力支线**实验，稳定再切。
>
> B5 case 可由任一腿驱动；下面的 prompt-扩展任务属忠实 leg 渐进路径。
>
> **术语对齐（2026-06-07）**：上文「再拓扑 leg ... 切分/配对下沉」口径已更新——**两条线只在 zonification（怎么定 zone）分叉**（忠实=房间为zone / 热区再拓扑=平面先划热区）；**切配（面切成 EP 一一对应）= 独立确定性算法、与两条线无关**（技术参考 [reference/split_pairing_kernel_reference.md](reference/split_pairing_kernel_reference.md)）。覆盖洞属切配/几何侧，不是腿的差异。详见 [architecture/geometry_first_zonification.md](architecture/geometry_first_zonification.md) 顶 banner。
>
> **落位反转（2026-06-09）**：切配从「下游另有人做」改为 **本项目侧确定性做、确定性核之后吃 cells**——连同 cell→面几何生成（建模·几何）一起收进**确定性造面/切配内核**。证据=sm20/sm21 对照（一步出 LLM 切配对、staged 退化）。目标总架构 `识图→校正→建模·几何(确定性)→切配·仿真(确定性)→物理挂载→下游`，LLM 只做感知+校正判断+物理语义、代码做所有几何+装配。详见 [CLAUDE.md §5.10](CLAUDE.md) + [pipeline_stage_contracts §0.1](architecture/pipeline_stage_contracts.md) + [split_pairing_kernel_reference §6](reference/split_pairing_kernel_reference.md)。**P0 待建。**

**任务（边做边细化）**：
- [ ] 在 `test_data/SmallOffice/` 加 1-2 个 L 形 case（含图纸 + testdata_prompt.json + GT）
- [ ] 评估当前 prompt 在 L 形上的失败模式（外包多边形 / WWR 立面定义 / surface 邻接）
- [ ] 升级 INTAKE_SYSTEM_PROMPT：外包从"width × depth"扩展为"vertex 列表"；WWR 按"立面 segment"而不是"东南西北"
- [ ] 评估 surface_agent / fenestration_agent 是否能消化新 schema（必要时小改 prompt）
- [ ] 用 B3 `intake_diff` + 几何专项指标（多边形面积误差 / 边数对错）验收

**工作量**：~1-2 周（探索性）

**依赖**：B1-B4 完成（必须先在矩形上恢复且评测体系就绪）

---

### B6. [P1] 能力升级 2 — 全局坐标系 + 退台 / 挑空

**背景**：[CLAUDE.md §5.1](CLAUDE.md) 已确立"全局唯一世界坐标系"原则（sm_15 起），但当前还没真用上**退台**（上层比下层小）和**挑空**（中庭跨多层无楼板）等需要全局坐标才能精确表达的几何。

**任务（边做边细化）**：
- [ ] 加 1 个退台 case（如顶层缩进） + 1 个挑空 case（中庭穿 2-3 层）
- [ ] 升级 zone_specs：每层 zone 的 x/y 范围以全局坐标出（已部分到位），新增"该 zone 是否有楼板/天花板"的可选标志
- [ ] surface_agent 处理挑空：相邻层中庭 zone 不再有 InterZone Floor/Ceiling 配对，而是 zone 高度直接跨层
- [ ] surface_agent 处理退台：上层缩进区域的"露出屋面"自动归到下层 zone 的 Roof
- [ ] 评测：几何对错由 OpenStudio 视察 + IDF 落盘 + EP 真跑（验可仿真性）

**工作量**：~2-3 周（探索性）

**依赖**：B5 完成（多边形外包先就绪）

---

### B7. [P1] 能力升级 3 — 规范化绘图 + 门 / 窗 / 楼梯识别

**背景**：当前 INTAKE_SYSTEM_PROMPT 让 LLM 直接读图,识别精度受限于 LLM 视觉能力。规范化绘图思路是让用户在前置流程里给图纸"打标"（图层 / 颜色 / 符号约定），让识别变成"按规约抽取"而不是"开放视觉理解"。

**两路：①用户侧规约 / ②工具侧预处理**：

- ① **用户侧规约**：
  - [ ] 写 `AI_agent/drawing_convention.md`：门 = 红色弧段 / 窗 = 蓝色双线 / 楼梯 = 灰色平行斜线 / WC = 蓝色"WC"标签 / etc.
  - [ ] 在 [new_case_guide.md §四](guides/new_case_guide.md) Step 1 加规约说明，让用户准备图纸时按约定标
  - [ ] INTAKE_SYSTEM_PROMPT 加"按规约识别"分支

- ② **工具侧预处理**（原 B5 PaddleOCR + cv2 内容并入此处）：
  - [ ] 新建 `Tool_scripts/preprocess_floor_plan.py`：
    - PaddleOCR 提平面图所有数字 + 坐标 → JSON
    - cv2 形态学找宽白连通区 → 走廊 bbox 候选
    - 颜色滤波 + 模板匹配找门 / 窗 / 楼梯符号 → 实例列表
    - 输出 `<case>/output/preprocess.json`
  - [ ] [new_case_guide.md Step 4](guides/new_case_guide.md) prompt 模板加「预处理结果（可信度高）」段，让用户先跑预处理脚本，把结果贴给 Opus 当 hint

**工作量**：~2-3 周（① 约半周 / ② 1-2 周）

**验收**：
- 同一 GT case 上，门 / 窗 / 楼梯实例数对错率显著下降
- footprint_W/D_err / wwr_mae 对 B4 baseline 进一步下降
- 落 `test_baseline/runs/<date>_capability_drawingconv_v1/notes.md`

**依赖**：B5 + B6 完成（先有非方形 + 全局坐标基础）

---

## 远期 — 开源模型 + Pivot

### B8. [P2] 开源模型评测（M4 milestone）

**任务**：
- 部署 vLLM + Qwen2.5-VL（先 7B，再 32B / 72B）/ DeepSeek-VL
- 把 [llm.yaml](../src/configs/llm.yaml) `intake` section 切到 vLLM endpoint（A2 已就绪）
- 半人工流改全自动：把 Step 4 从 Claude Code 会话改成 `python scripts/run_full_pipeline.py <case>` 直接走 vLLM
- 跑 B3 同一套评测
- 横向对比 Opus baseline + 阶段 1 恢复 + 阶段 3 升级 + 开源模型四档

**工作量**：~1 周（含部署 + 调参）

**验收**：
- 候选模型至少一档达 Opus 80%+（[pivot_criteria.md §4.4](reference/pivot_criteria.md) 阈值）
- 落对比表到 [reference/open_model_guide.md](reference/open_model_guide.md)

**依赖**：B1-B7 完成

---

### B9. [P3] LoRA SFT + Pivot 切换（M5/M6）

**任务**：
- 见 [pivot_criteria.md §4.1](reference/pivot_criteria.md)：用 Opus baseline 的 IntakeOutput JSON 集合作 SFT 数据种子（≥500 对，需扩 GT 集到 ≥10 case）
- LoRA 微调候选开源模型
- holdout 集评测达 Opus 80% 后切 [llm.yaml](../src/configs/llm.yaml) `intake` 默认 provider
- 全量回归

**工作量**：~2-3 周

**验收**：[reference/pivot_criteria.md](reference/pivot_criteria.md) 全部阈值达标

**依赖**：B8 完成 + Pivot 阈值达标判定

---

## C. 暂搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者完成 [§3.1 MCP 全线重写](deferred/idfpy_embed.md)；本项目侧 §3.2 等他们交付后再启
- **token_optimization §4.1-4.5**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换完成后大量 CRUD 工具消失，重新评估
- **OpenStudio 几何验收 sm_15/16/17**（[CLAUDE.md §8.1](CLAUDE.md)）：用户人工跑，不卡代码
- **fenestration / construction Construction layer 兼容性 prompt 修**（2026-05-07 sm_16_newarch 真跑发现）：
  - bug：`WindowMaterial:SimpleGlazingSystem` 被当作可串联玻璃层（与 air gap + 第二片玻璃组成三明治） → EP window 求解器收敛失败 NaN fatal
  - 实例：sm_16_newarch `Window_Double_Glazing` Construction → `F1_NORTH_W_WINDOW` fatal；手工把 Construction 改成单层引用 SimpleGlazing 后 EP `Completed Successfully` / 0 severe
  - 副 bug：`Glass_Clear_6mm` U=5.7 是单层透明玻璃值，但命名 `Double_Glazing` —— 命名/数值不一致
  - **不修原因**：用户决策当前焦点是几何正确性；idfpy 自带 schema 校验切换后会原生拒绝该组合，短期改 prompt 属重复投资
  - **启动条件**：idfpy MCP 重写交付后（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）一并解

---

## D. 与 Milestone（[CLAUDE.md §4.3](CLAUDE.md) — 注：§4.3 在精简版中已删除，原映射如下；2026-05-07 晚按三阶段重映射）

| Milestone | 对应本文 TODO |
|---|---|
| M0（旧 skill 约束新架构恢复 — 新增）| **B1** |
| M1（多模态 golden 数据集 v0.1）| B2 |
| M2（自动评测脚本）| B3 |
| M3（Opus baseline 重建 + 校对方案 + token 协议）| B4 |
| M4（vLLM + 开源模型评测）| B8 |
| M5（gap 修补：能力升级 3 维度）| B5 + B6 + B7 |
| M6（切默认 provider，全量回归）| B9 |

---

## 关联文档

- [architecture/architecture.md](architecture/architecture.md) — 当前架构事实参考
- [CLAUDE.md](CLAUDE.md) — 项目管理总览（精简版）
- [guides/new_case_guide.md](guides/new_case_guide.md) — 新建测试样例 7 步流程（半人工版）
- [reference/pivot_criteria.md](reference/pivot_criteria.md) — Pivot 双阈值
- [reference/open_model_guide.md](reference/open_model_guide.md) — 开源模型操作手册
- [deferred/idfpy_embed.md](deferred/idfpy_embed.md) — idfpy 替换主线（搁置中）

---

_2026-05-29 — **B1.5.c/d/e/g 交付（两步法切主线 + InterZone 门 + 正式指南）**：B1.5.c `intake_node` 三路分发串行 + `src/agent/pipeline.py` 单一实现 + `--reading-from` + per-case 模型配置；B1.5.d `run_pipeline_deepseek` 收成薄包装；B1.5.e `new_case_guide.md` 正式化两步法；新增 B1.5.g InterZone 确定性几何门（审阅 A，EP 前 fail-fast，e2e 全新输出抓 6 缺陷）。两份 Codex review 3 High + 4 Med/Low 全修、re-verify 全 PASS；测试 5→23。e2e 首次完整跑通新架构（机制 100% 通，几何质量挂门 = 建模质量主线问题，审阅 B 待落地）。详见 [CLAUDE.md §5.8](CLAUDE.md)。_

_2026-05-12 (晚) — **两步法 POC PASS + B1.5 立项最高优先级**：sm_20 全套两步法（phase1 矢量化 → phase2 拓扑建模）+ 下游 + EP 真跑通过（DeepSeek 路径 EP cleanly / Opus 路径暴露 InterZone construction rule 漏洞已在 phase2_rules v1.3 修）。F3 corridor 窗 z 修正（anchor 单步错 9.60，两步法都对 10.60）证明误差预算分离生效。新增 B1.5 节：POC v2 异图 / intake_node 改两步 / 评测嵌入 / new_case_guide 重写。详见 [floorplan_redraw_strategy.md §9](capability/floorplan_redraw_strategy.md) + B1.5 节。两步法 artifacts 迁到 [`test_data/SmallOffice_TwoStep/`](../test_data/SmallOffice_TwoStep)，skill 演进源在 [`skills/intake_pipeline/`](../skills/intake_pipeline)。_

_2026-05-12 — **B1 阶段闭环**：3 个 skill md 全部按 audit 4 个 Gap 补硬约束 + fenestration chain N 窗通式 + 反例；surface_agent prompt + 输入装配 hotfix（src_history 备份 + downstream_agent_changes.md）。sm_20 半人工流 EP cleanly 跑通取代 sm_16_newarch 成为新通透性 anchor。推荐执行顺序更新：主线焦点切到 B2-B4（评测基线规范化）。详见 [CLAUDE.md §5.5](CLAUDE.md) + B1 节本文。_

_2026-05-07 (晚 v2) — B 段三阶段重组（用户路线图）：阶段 1 恢复 [B1] / 阶段 2 评测基线规范化 [B2-B4] / 阶段 3 能力升级 [B5-B7] / 远期 [B8-B9]。新 B1 = 旧 skill 约束迁移到新架构（吸收原 B4 CoT 内容）；新 B4 = Opus baseline + 校对方案 + token 协议升级（吸收原 B0'''）；新 B5/B6/B7 = 非方形平面 / 全局坐标退台挑空 / 规范化绘图（含原 B5 PaddleOCR 预处理）；新 B8/B9 = 原 B6/B7 远期 pivot。Milestone 映射加 M0 恢复阶段。_

_2026-05-07 (晚) — 真跑 sm_16_newarch IDF 喂 EP 实证：T-vertex 不卡 EP（B0' 关闭），真 fatal = fenestration_agent SimpleGlazing layer 兼容性 bug，手工修后 EP PASS。决策：不调 prompt，与 idfpy 切换一并解；当前主线焦点切到几何正确性。推荐顺序去 B0；B0/B0'/B0''/§C 全更新。_

_2026-05-07 — A 段四项全闭环（A1 schema drift PASS / A2 多 section LLM / A3 run_full_pipeline 三入口 / A4 文档全修订），从主体下沉到表格；新增 B0 sm_17 端到端首跑作为半人工流验证；B3 改半人工版（用户无 Anthropic API）；B4 加入 Floor_N_* 模板禁用补丁；B5 改 Tool_scripts 预处理脚本（半人工流 intake 在会话外）；B6 footnote 去掉 A2 依赖（已就绪）；C 段加 sm_17。_

_2026-05-05 全文重写。删旧版 CoT vs 前置小模型探讨；按 architecture.md 新架构理解重组为「代码跑通 + 识图能力」两线 TODO。_
