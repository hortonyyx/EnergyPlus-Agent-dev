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

### N1. [P0] sm21_anchor 出首份 judge-in-the-loop baseline
- 用 [`scripts/tool_scripts/run_stage.py`](../scripts/tool_scripts/run_stage.py) 逐段真驱动 sm21_anchor（draw→gate①→judge②→盲重抽/几何 approve→4_mep）。
- 跑完按 [new_case_guide.md](guides/new_case_guide.md) 记 `record_baseline` + RUN_REPORT + 🔍 肉视清单；更新 [test_baseline/index.md](../case_tests/test_baseline/index.md)。
- **用户已排期**：本轮文档整理完即跑。

### N2. [P0] sm21 South 2F 窗 along-facade x bug
- 现象：南立面 2F 窗 x 位置真错（gt 已 verified，差异定位在 1_correction）。核 correction 沿立面 x 推导，修后回归 sm21。

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
