# 行动清单（活计划）

> **本文件 = 当前开发计划的活文档**：记录最近的决策与待办，**动态调整、近细远粗**。不是"一次定终身"的路线图——
> 随开发进展滚动重写。**分出去的独立模块用单独文档**（见末尾「分出去的模块」）；项目结构/当前状态看
> [CLAUDE.md](CLAUDE.md)；已闭环里程碑与历史决策看 [decision_log.md](decision_log.md)；架构细节看
> [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)。
>
> 优先级：P0（立即）/ P1（一周内）/ P2（依赖 P0/P1）。术语口径见 CLAUDE.md 顶 banner。

---

## 当前焦点

0–5 管线 + 逐段校验架构（gate① 确定性 + gate② judge）已落地，sm20/sm21 两份 golden baseline 在册。
**当前在把"逐段 judge-in-the-loop 编排"真跑起来、出第一份带 judge 的规范 baseline**，并扫尾两步法/评测的残留。

---

## 近期（细）

### N1. [P0] ✅ sm21_anchor 出首份 judge-in-the-loop baseline（2026-06-21 完成）
- 用 [`scripts/tool_scripts/run_stage.py`](../scripts/tool_scripts/run_stage.py) 逐段真驱动 sm21_anchor（draw→gate①→judge②→盲重抽/几何 approve→4_mep）。**已跑通**：GPT-5.4 识图 run 端到端 clean，三份 baseline 在册（见 N1b）。
- 残留：更新 [test_baseline/index.md](../case_tests/test_baseline/index.md) + golden 测试（待 commit 时一并）。

### N2. [P0] ✅ 关闭 — sm21 South 2F 窗 x bug 不复现（2026-06-21）
- 诊断（Codex 探查 + Claude 自验）：GPT54 run 实际产出 South 2F 窗 x = gt 完全一致（[2.19,3.39]…[11.61,12.81]）。原"真 bug"是 **06-16 Opus 旧轮**产物（那轮 1_correction 把窗 x 沿立面平移 -0.24m）。随识图质量提升消失。诊断 `logs/review/request/2026-06-21_sm21_south2f_window_x_diagnosis.md`。
- 潜在隐患（降级 backlog，不急修）：Opus 轮的 -0.24m 疑似"墙厚补偿误加到 along-facade 轴"——当前好识图不触发，可能是潜伏 correction 逻辑 bug。

### N1b. [P0] sm21 双模型轮(2026-06-21) backlog —— GPT-5.4 跑测暴露的真问题
> 本轮：GPT-5.4(codex CLI `-i`)识图 → 干净 14区/112面/15窗、EP 0 severe；Sonnet 0/2 阻塞(J1/J0)；
> judge-in-the-loop 验证成功。三份 baseline 在 `case_tests/e2e_tests/sm21_anchor/run_2026-06-2*`。
> 本轮已改：run_stage S5 缺 IDD 初始化 → 加 `ensure_schema_initialized()`（待 commit）。

- **[P0] ✅ 核加跨层内墙对齐 + 外包优先（2026-06-21 完成，`6.21_CrossFloorWallAlign`）**：根因修正——轴线图**本就全楼共享**，真因=同层/跨层共用 `axis_jitter_tol=0.05`，走廊跨层差恰 0.10m 卡在容差缝（不聚类、sliver `<0.10` 严格不并）→ 两轴幸存生碎面。修=`deterministic.py` 新增 `_reconcile_cross_floor`：per-floor identity → footprint 硬锚 → **mutual-nearest** 跨层匹配（图级冲突即 flag、不静默合）→ provenance-aware sliver；新容差 `cross_floor_align_tol_m=0.11`。走廊两层对齐到 y[3.15,4.85]，**sm21 112→100 面**、zones/windows 不变。经 Codex 双审（REWORK→APPROVE-WITH-CHANGES）+ 四重验证。审计轨迹 `logs/review/{request,review}/2026-06-21_cross_floor_wall_alignment_*.md`。
- **[P1] ✅ viewer 挪独立人工文件夹（2026-06-21 `6.21_ViewerToManualReview`）**：`2_modelling/geometry_viewer.html` → `<run>/manual_review/geometry_viewer.html`（run_stage 输出改路 + 补 role 着色、record_baseline 文档 + .gitignore 同步）。后续接编辑回写 [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md)。
- **[P1] 房间类型(role) 移回 reading — ✅ phase-1 落地（2026-06-21 `6.21_RoleObservationsPhase1`）**：reading 加可选 `room_labels`(RoomRoleObservation,topology-light) + 共享词表 `src/agent/roles.py` + correction prompt 把 room_labels 当输入优先采用。绑定仍 correction 隐式做（输入升级）。**phase-2（远期，"更精准修法"用户定缓做）**：确定性绑定 sidecar `role_assignments.json` + `Cell.role_source_label_id` + gate① role-provenance INVARIANT + 4_mep unknown 策略 + sm21 baseline 重录 + **plan-local→world 一等可审变换产物**（确定性 anchor-in-cell 的使能件，把 LLM 移出空间绑定）。完整设计在 `logs/review/{request,review}/2026-06-21_role_to_reading_plan_*.md`（含 v1/v2/v3 演进 + Codex 三轮审）。
- **[P1] 命名确定性化（下一项）**：现 zone cell id 由 DeepSeek 出（各 run 口径乱 `R_1F_Cor` vs `F1_corridor`），surface/window 名内核派生。改**代码确定性生成**，约定 **楼层-类型-方位-序号**（序号含 SW/NE 方位）。**注：blast radius 极宽**（全下游精确名引用 + 30+ 测试 + golden baseline 字节相等需重录）、且类型段依赖 role 可靠（已 phase-1 就位）。侦察 map `logs/review/request/2026-06-21_role_and_naming_recon.md`。
- **[P1] ✅ 机制落地（2026-06-22 `6.22_ReadingHonestJudgeRouting`）— 查 Sonnet 识图变差 + 平面降质**：诊断=**不是 Sonnet 变差/不是新回归**，是 2026-06-07 founding 框架（trust-the-dim）**reading 半边没落进 0-5 schema**（Stroke 无 provenance、缺 stroke↔dimchain check、无双通道纪律/门≠窗负例、verdict 无 recoverability 轴）→ correction 收不到冲突信号、照抄识图错穿到 J1。修=两战线（**reading 诚实** provenance/confidence/dimension_refs + stroke↔dimchain CROSS_CHECK + guide/pen prose；**judge 两轴** recoverability，J0-scoped blocking + 四条放行判据+默认中止 + J1 确认门归因），**correction(A1-A4+核)不动、不需重录 baseline**。架构总纲 D1-D5（correction 永 image-blind 不做 VLM / 脚手架=降智机制服务国产VLM→开源北极星 / 看图仲裁归 judge+重读 / who-fixes=证据冗余在+不靠猜才放行）用户全程 ratify。详 decision_log §A + contracts §0.3/§5.3 + logs/review/2026-06-21 提案+审。**残留=sm21 重跑验证**（与下方命名确定性化等待改项攒齐一次性跑，用户定）。
- **[P1] 同源欠债收尾（reading-honest 配套，让错可见→可归因→可重读恢复三件套的后两件）**：① **✅ audit→评测归因 baseline 侧（PR-A，2026-06-22）**——`record_baseline` 读 `1_correction/corrections.json` → `baseline.json.corrections_summary` + `RUN_REPORT` 加「校正审计（看错↔改错归因）」节（**不动 gate flags/计数**，Codex Finding 6）；残留=gt-diff×corrections 机械 JOIN 并入 N4 评测。② **✅ 0_reading auto re-read（PR-B，2026-06-22 落地，测试 →307 绿）**——**子代理即 0_reading runner**（主控冷启隔离子代理重看图，非 VLM-API-gated，先前误判已纠正）、3 次不过终止、每步 judge 判定，与 0–5 一致；`AWAITING_REREAD` 非终止态 + `RunPolicy.reading_runner_available` 默认 False 向后兼容 + 子代理写 flat `0_reading/*_view.json` 再 `resample --force` 记 attempt + 预算线程化到 root 段（J1 root=0_reading）+ 预声明 model/effort ladder（盲、判语不注入）。方案+审 `logs/review/2026-06-22_audit_attribution_and_auto_reread_{proposal,review}`（Codex `APPROVE-WITH-CHANGES`，7 findings 全采纳 + 用户定 SPLIT）。
- **[P2] ✅ 主控汇报优化（2026-06-23 `6.23_ReportOrgCuratedFolder`，五审闭环 8→4→2→1→0）**：每 run 产**单一 `report/`** = `FACTS.md`(确定性事实卡) + `REPORT.md`(主控+judge 动态撰写、**四桶建议** 机制/能力/脚手架/修法) + `eyeball/`(显式 collector 汇 2D 肉检图；3D viewer 留 manual_review 指针)。事实层(代码)/叙事层(主控)分离 + `REPORT.md` create-if-absent 防覆写；新增 **evidence_index**(坐标式稳定 id + dup 断言) + **citation linter**(建议必挂证据、纯词法) + **run_state**(复用 TERMINAL_STOP/ADVANCE_OK + PENDING + 几何 supersede，状态感知不发死链)；RUN_REPORT.md→report/ 原子迁移；新 `scripts/tool_scripts/report_assembly.py`、测试→320。两份真实 run（gpt54 clean / sonnet stopped）已生成 report/ 验证。审计轨迹 logs/review/2026-06-22_run_report_organization_{proposal,review}（一~五审）+ 2026-06-23_report_org_execution_log。**残留**：主控撰写 REPORT.md 叙事+四桶建议是**每次跑后**的活（骨架已就位，sm21 重跑时实操）。

### N3. [P1] CAD→gt 满配答案（见 [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md)）
- 工具链已就位（ezdxf + proxy-graphics 解码 + `gt_from_dxf` + overlay 核验）。**待用户从天正图形导出/另存 DXF** → 抽满配 gt（精确窗 x+宽、精确区划、门）。方案过 Codex 审、设计待落。

### N4. [P1] 两步法 / 评测残留（原 B1.5.b / B1.5.f / B2–B4）
- **skill 迭代**：phase1 识图库 + 笔库（跨画法泛化）；phase2 规则吸收可机械化项（命名约定 / 负载密度 / day-type 名）。
- **评测嵌入**：gt diff 评测脚本（zone_f1 / 尺寸误差 / WWR / special_zone_f1 + 识图错↔推理错归因）；嵌进 record_baseline 流程。
- **GT 数据集扩面**：sm20/sm21 已有 gt；按需补 ≥1 异图坐实泛化。

---

## 中期（粗）—— 能力升级（原 B5–B7）

按 **[capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md)** 的 C 阶梯推进（内核先行 + 守卫同步）：
- **C2 正交多边形 + 多平面立面**（含 shapely 覆盖完整性门提前落地）
- **C3 退台 / 挑空**（墙配对 by_floor → z 区间重叠驱动、切配扩到切墙）
- **C4 斜交墙**

并行支线：识图→建模质量主线见 [capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md)；再拓扑 leg（休眠）见 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md)。

---

## 远期 —— 开源模型 + Pivot（原 B8–B9）

- 部署 vLLM + Qwen2.5-VL / DeepSeek-VL；切 [llm.yaml](../src/configs/llm.yaml) `intake` section（A2 已就绪）；跑同一套评测横向对比。
- LoRA SFT（phase1=(图,矢量JSON) VLM / phase2=(矢量JSON,IntakeOutput) 纯文本，两数据流独立），holdout ≥ Opus 80% 后切默认 provider。
- 双阈值见 [reference/pivot_criteria.md](reference/pivot_criteria.md)。

---

## 分出去的独立模块（指针）

| 模块 | 文档 | 状态 |
|---|---|---|
| CAD→gt 满配答案 / CAD 输入模态种子 | [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md) | 设计待审，工具链就位 |
| 0–3 复杂度升级路径（C2/C3/C4）| [capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md) | 骨架已立，随中期推进 |
| 再拓扑 leg（热区积木 zonification）| [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) | 强力支线，休眠 |
| 可编辑几何确认环节 | [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md) | DEFERRED，先讨论 |

---

## 搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者侧 MCP 全线重写交付。
- **token 优化**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换后大量 CRUD 工具消失再评估。
- **fenestration/construction SimpleGlazing 兼容性 prompt 修**：等 idfpy schema 原生覆盖（当前几何优先，不动 prompt）。
- **Sonnet 4.6 / Haiku 4.5 降级测试**；**OpenStudio 几何验收**（用户人工，不卡代码）。

---

## 已完成（一行汇总，详见 [decision_log.md](decision_log.md)）

A 代码跑通 ✅ · B1 旧 skill 迁移恢复 ✅ · 两步法 POC + 切主线 + InterZone 门 + 正式指南 ✅ · 0–5 阶段重构（几何确定性化）✅ · EP 跑通 + schedule 门 ✅ · 完整体检 4H/3M/3L 全修 ✅ · 仓库整理 + 标准 case 布局 ✅ · 0–5 校验架构 M0–M4 ✅ · 新 baseline 方案 + 主 Agent 操作手册 + gt ✅ · 逐段 judge 编排 + 离线 3D 查看器 ✅ · CAD→gt 工具链 + gt 渲染 ✅
