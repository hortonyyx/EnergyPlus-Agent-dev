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

### N2. [P0] sm21 South 2F 窗 along-facade x bug
- 现象：南立面 2F 窗 x 位置真错（gt 已 verified，差异定位在 1_correction）。核 correction 沿立面 x 推导，修后回归 sm21。

### N1b. [P0] sm21 双模型轮(2026-06-21) backlog —— GPT-5.4 跑测暴露的真问题
> 本轮：GPT-5.4(codex CLI `-i`)识图 → 干净 14区/112面/15窗、EP 0 severe；Sonnet 0/2 阻塞(J1/J0)；
> judge-in-the-loop 验证成功。三份 baseline 在 `case_tests/e2e_tests/sm21_anchor/run_2026-06-2*`。
> 本轮已改：run_stage S5 缺 IDD 初始化 → 加 `ensure_schema_initialized()`（待 commit）。

- **[P0] 核加跨层内墙对齐 + 外包优先**：本轮主问题=GPT 版 112 面 vs 06-16 Opus 100 面。根因=GPT-5.4 两层走廊读得不一样宽（F1 y[3.1,4.9] / F2 y[3.2,4.8]，差 10cm）→ 确定性核**各层独立 snap、无跨层对齐** → 走廊↔房交界生碎面。修：同一条概念墙全楼统一坐标、**外包(总长宽)优先内部其次**。
- **[P1] viewer 挪独立人工文件夹**：现 `2_modelling/geometry_viewer.html`（切配后产物）→ 挪 `<run>/manual_review/`（后续加编辑回写，单独放合理；接 [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md)）。
- **[P1] 房间类型(role) 移回 reading**：现 role 由 1_correction(DeepSeek, image-blind) 出 → 判错（F1 东南圆桌房→office）。reading 看得见图，role 归 reading；**correction 不许改房间类型**。
- **[P1] 命名确定性化**：现 zone cell id 由 DeepSeek 出（各 run 口径乱 `R_1F_Cor` vs `F1_corridor`），surface/window 名内核派生。改**代码确定性生成**，约定 **楼层-类型-方位-序号**（序号含 SW/NE 方位）。
- **[P1] 查 Sonnet 识图为何变差**：Sonnet 曾出最忠实重绘，本轮 0/2（内墙↔尺寸刻度混淆、门当窗）。
- **[P1] 查平面识别为何下降**：现立面很准、平面降了（以前相反）。外包优先策略可能相关。
- **[P2] 主控汇报优化**：零散 json 分门别类收好、用户只看报告；产出"最终报告格式+内容"优化建议。

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
