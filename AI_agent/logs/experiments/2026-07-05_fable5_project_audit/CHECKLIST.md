# Fable5 项目体检检查单（2026-07-05）

> **你（Fable5）是本次「项目体检」会话的自主主控。** 这是一次**审计/规划**任务：只产诊断与方案、**不改动项目代码**（不改 `src/skills/tests/MCP/下游`、不跑 pipeline/EP/改 git）。唯一交付 = 一份 markdown 报告 `AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md`。
>
> **省 token / 省上下文（硬要求，你 token 烧得快）**：调查取证**优先派 Codex**（`mcp__codex__codex`，本机必须 `sandbox=danger-full-access` 否则静默回退读 GitHub @main；不占你的额度），或**起子代理读文件 / 跑离散取证**（看你需求）。你自己只做：定框架、综合判断、写报告。别自己逐文件全仓扫。**同目录已有 `codex_cv_plan.md`**（Codex 预先出的 CV 工具箱方案）= B2 的现成参考输入，先读它。
>
> **交付口径**：
> - **「关于现在」= 诊断（根因，附 `file:line`）+ 大致修复方向**（不写完整实现，指方向/落点/风险）。
> - **「关于未来」= 分阶段方案**（staged，粗粒度即可，不要具体实现；后期我们再具体落地）。
> 每条结论**锚到 `file:line` 或权威文档章节**，别泛泛而谈；能证伪/证实现有结论就明说。

## 必读定位（按此顺序，别重新发明）
1. `AI_agent/CLAUDE.md` — 根文档：项目结构 + 当前状态 §2 + **关键不变量 §1.5**（尤其 #1 判断-几何分工 / #2 单一世界坐标 / #4 gt 铁律 / #6 建筑复杂度可扩展性铁律）。
2. `AI_agent/architecture/pipeline_stage_contracts.md` — 唯一「当前稳定架构」活文档：逐阶段 输入·输出·校验 + 两道门 + 不变量 + 接缝缺口。
3. `AI_agent/plan.md` — 活计划（近细远粗）；`AI_agent/decision_log.md` — 历史决策归档。
4. `AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md`（C2/C3/C4 阶梯）· `AI_agent/capability/reading_improvement_methodology.md`（reading 提升 + Phase A/B/C + CV 工具箱）· `AI_agent/proposals/geometry_first_zonification.md`（再拓扑休眠支线）· `AI_agent/architecture/judge_grade_model.md`（判卷子系统活规格）。
5. 代码地基：`src/agent/pipeline.py`（run_pipeline）· `src/agent/geometry/`（内核）· `src/agent/correction/` · `src/validator/checks/` · `src/agent/execution/validation_run.py`（validate_case capstone）· `src/agent/judge/`。

## 背景（体检要带上的当前判断）
- **2026-07-05 刚坐实**：Haiku 4.5 降级测试（同脚手架、唯一变量=reading 模型）→ reading 对 gt **平面墙 0/9·立面窗 0/15**，Sonnet 5 基线 9/9·15/15。**结论：模型能力是 reading 主导杠杆，脚手架有它托不起弱 VLM 的能力地板**（`logs/experiments/2026-07-05_haiku_downgrade_test/`）。这是「reading 上 CV」的直接动因。
- 迁移完整性此前经 Codex 三路 + 第二路 + 最终 GO 裁「相对 sm21_pre 在 validate_case 口径下迁移完全」——**你作为全新独立第四路，要么独立复现要么挑战它**。

---

## A. 关于现在（诊断 + 大致修复方案）

**A1 · 0–5 管线架构设计问题**
0→5 阶段边界 / 契约 / LLM↔代码分工接缝 / correction 永 image-blind 设计 / 两道门（gate① 确定性 + gate② judge）/ 单一世界坐标 / IntakeOutput 11 字段契约——有没有**架构层面**的设计隐患（坏味道、以后会崩的接缝、过耦合、职责错位）？重点看分工铁律 #1 与契约 #3 是否有被悄悄破坏处。

**A2 · 0–5 端到端工程问题**
工程层面：① `run_pipeline` 生产路径自校 vs `validate_case` 口径是否**真的**一致（桶③刚宣布关闭，独立验证 correction/mep/kernel/assembly inline 是否口径齐、有无遗漏 raise 路径）；② fail-closed 纪律 / run_profile 分档（exploratory vs golden/regression）是否自洽；③ manifest/attempts append-only 完整性、accepted 指针；④ **gt 隔离铁律**（`test_gt_discipline`，gate①/执行器/correction 零 gt import）有无漏网；⑤ provenance 记录完整性（run 溯源，尤其 reading 模型钉死）；⑥ **半接线/悬空件**——已知 `derive_facade_frame` 建了未接线 + E/W sign 与活口径相反且未测（`src/agent/correction/facade.py`），扫有没有同类其他悬空。给根因 + 修复方向。

**A3 · 脚手架迁移是否迁干净（独立第四路）**
6.10–6.16「两步法→0-5 几何确定性重构」是否把旧脚手架（`old_scaffold_127ba06`，sm21_pre 表现良好）对 reading 及 1-5 的**约束/能力**完整迁移？四桶归类：✅已迁 / ❌遗漏 / ⚠️冲突斩断 / 🗑有意删。重点复核前几轮裁为「已迁 validate_case」的项是否真在、Phase B 挂起项（S1-10 非矩形 cell vs polygon-native 内核、S1-12 derive_facade_frame）是否有更早该做的、残留 `NOT_APPLICABLE` 占位是否有应落实的。**发现任何 refactor 丢失的有效约束 = 高价值。**

---

## B. 关于未来（分阶段方案，不要具体实现）

**B1 · 建筑复杂度升级 C2/C3/C4 → 0–5 各阶段能力怎么升**
目标体量：
- **C2** 正交多边形 + 多平面立面（含 shapely 覆盖完整性门**提前落地**）
- **C3** 退台 / 挑空（墙配对 by_floor → z 区间重叠驱动；切配扩到**切墙**）
- **C4** 斜交墙

对**每个阶段**给分阶段升级方案（含**但不限于脚手架约束升级**）：`0_reading` schema/脚手架 · `1_correction` schema/判断 · `2_modelling+3_split_pairing` 几何内核 · `4_mep` · `5_intakeoutput` 契约 · gate① 确定性门 · gate② judge + **判卷模型**（见 C2 附加）· gt/答案模型。**硬约束不变量 #6**：复杂体量 = schema 加槽位（per-floor footprint / 变高区 / void）+ kernel 实现扩展 = **接缝内长，非架构推翻**；明确指出**哪些当前简化假设（共用 footprint / 每层满铺楼板 / 固定层高）被烤死在哪、如何松动**。

**B2 · reading 上 CV 到底怎么做（风格泛化是核心约束）**
基于 `capability/reading_improvement_methodology.md`（Phase A/B/C + CV 工具箱洞察：sm21_pre 好 reading 的 forensics 证强模型是**自发写经典 CV**——灰度投影定位墙线 + 连通域数窗——才拿 0.0m 精度）。给分阶段方案：CV 前端做成 0_reading 的**显式工具箱**（crop / 墙线投影 / px↔m 标定 / 窗连通域）给弱/开源 VLM 当拐杖；**怎么保证跨建筑图纸风格泛化**（不 overfit sm21，要吃各种画法/图例/线型）；怎么桥接 Phase B（算术下沉）与 Phase C。**注**：本目录 `codex_cv_plan.md` = Codex 预先出的更细 CV 工具箱方案，作交叉参考基线——你在它之上给**方向裁决 + 风格泛化策略 + 与 Phase B/C 的衔接**，认同/挑战它的分阶段，不必重抠实现细节。

**B3 · 再拓扑路径怎么启 + 怎么纳入 pipeline**
`proposals/geometry_first_zonification.md` 休眠支线（热区积木 + 确定性内核）。给分阶段方案：启动入口是什么、怎么作为**kernel 策略替换**与当前「造面+切配」内核共存/替换（不变量 #6 = 策略替换非架构推翻）、需要哪些 schema/契约变更、迁移路径、与 C2/C3/C4 的关系（再拓扑是否是复杂体量的更优解）。

---

## C. Claude 补充（也请 Fable5 一并查）

**C1 · reading 策略在「模型是杠杆」坐实后的连贯性**
既然已证脚手架托不起弱 VLM，现行「脚手架为弱/开源 VLM 北极星 + 先不上 CV」策略是否仍连贯？脚手架里有没有**因过度约束/已知无效**而该精简的死重（reading-honest 双通道、证据门、反过度分割条款等）？给一个对 reading 整体策略的新鲜判断（present=诊断，与 CV 上马如何排序=future 方向）。

**C2 · 判卷（gate② grade）子系统对复杂体量的泛化**
新建的立面+平面统一判卷模型（`architecture/judge_grade_model.md`，§8b backlog：墙粒度 / within_tol 移位vs变尺寸 / Hungarian / ambiguous config 化 / 非方形 segment-polyline）。判卷模型本身是否 sound？**能否泛化到 C2/C3/C4**（非方形 / 多平面立面 / 斜墙）？这条与 B1 的 gate② 升级合看。

**C3 · 契约与 schema 版本化接缝对 C2/C3/C4 是否够用**
IntakeOutput 11 字段 / CorrectedGeometry / reading schema 的「版本化槽位」接缝，面对 C2/C3/C4 会不会**必然破坏性变更**？做一遍不变量 #6 的「烤死假设」审计：任何 `共用 footprint / 每层满铺楼板 / 固定层高` 是否埋在了松不动的地方。

**C4 · 测试覆盖盲区**
468 绿 + 9 strict xfail（命名改名后 golden 精确重建待 sm21 批次重录）。覆盖盲区？尤其刚关闭的桶③（run_pipeline 自校）+ 判卷模型 + kernel 各不变量门。9 个 xfail 的处置路径是否清楚。

---

## 输出结构（写到 `FABLE5_REPORT.md`）
```
# Fable5 项目体检报告
## A 现在（诊断+大致修复）  —— A1/A2/A3 各：现象→根因(file:line)→修复方向→风险/优先级
## B 未来（分阶段方案）      —— B1(逐阶段×C2/C3/C4)/B2(CV+风格泛化)/B3(再拓扑) 各：分阶段步骤（粗）+ 依赖 + 与不变量#6 的关系
## C 补充                    —— C1/C2/C3/C4
## 总览：Top 风险清单（按严重度）+ 与既有结论的分歧点（哪些证实/哪些挑战）
```
