# 行动清单

> **当前状态**：A 段「代码跑通 / 架构迁移」全部闭环（[CLAUDE.md §5.3](CLAUDE.md)）。当前能力主战场切到 B 段「识图建模能力提升」。idfpy 替换主线（[idfpy_embed.md](idfpy_embed.md)）等协作者交付，搁置中。
>
> 优先级：P0（立即）/ P1（一周内）/ P2（依赖 P0/P1）。

---

## 推荐执行顺序（2026-05-07 晚 — 三阶段路线图）

新架构 sm_16_newarch 已验证半人工 → 自动下游 → IDF → EP 全链路通（[B0](#b0-p0-端到端首跑验证半人工流--完成-2026-05-07)），
但**新架构识图建模质量不及旧架构 skill 约束流的 sm_16 baseline**。识图建模能力主线按下列三阶段推进:

```
阶段 1 [B1]：恢复
   旧架构靠 skill 约束（分步识图 / 绘图标注等）实现 sm_16 准确建模。
   新架构尚未迁移这套约束 → 第一任务是把旧 skill 内容迁到新架构 INTAKE_SYSTEM_PROMPT，
   恢复到旧架构 sm_16 建模水平。

阶段 2 [B2-B4]：评测基线规范化
   恢复后建立测试评测基线：GT 集 / 自动评测脚本 / Opus baseline /
   校对方案 / 测试记录规范化 / token 统计协议升级。

阶段 3 [B5-B7]：能力升级
   1. 引入非方形平面（如 L 形）
   2. 升级到全局坐标系做退台、挑空
   3. 引入规范化绘图实现门 / 窗 / 楼梯等识别

远期 [B8-B9]：开源模型 + LoRA Pivot（[pivot_criteria.md](pivot_criteria.md)）
```

**当前主线焦点 = 几何正确性**（IntakeOutput → IDF 几何对错）。simulate 跑通**不是**短期目标 ——
已知 fenestration glazing layer 兼容性 bug（[§C](#c-暂搁置依赖外部进展不安排时间)）让 EP fatal，按决策延后到 idfpy 切换时一并解。

**接下来一周聚焦 B1**（阶段 1 恢复），完成后切 B2-B4。B5-B7 在阶段 1 收敛 + 评测体系就绪后启。

---

## A. 代码跑通（已完成 ✅，2026-05-06）

| 项 | 描述 | 状态 |
|---|---|---|
| A1 | IntakeOutput schema 与协作者 trace 对齐 drift 检查 | ✅ 11 字段 / BuildingSchema 8 / SiteLocationSchema 5 全部一致，无 drift。详见 [CLAUDE.md §5.3.A](CLAUDE.md) |
| A2 | per-subagent LLM 配置（intake / default 两 section） | ✅ [llm.yaml](../src/configs/llm.yaml) 多 section + [llm.py:create_llm(node_name)](../src/agent/llm.py) 路由。详见 [CLAUDE.md §5.3.C](CLAUDE.md) |
| A3 | 端到端验收脚本 | ✅ [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py)（三入口：全自动 / `--intake-from` / `--intake-only`），原 A3 "preview_geometry 截止 fenestration" 设想被全图脚本替代——下游 DeepSeek 跑近免费，不必砍 |
| A4 | 文档同步（CLAUDE.md / architecture.md / new_case_guide.md） | ✅ 全部修订；[CLAUDE.md](CLAUDE.md) 410 → 175 行精简；[new_case_guide.md](new_case_guide.md) 重写为半人工 7 步流程 |

---

## B. 识图建模能力提升（视觉能力主线）

> **能力主战场是 [architecture.md §3](architecture.md) 表格里"几何依赖：强"的 5 个字段**：`building.name` / `site_location` / `zone_specs` / `surface_specs` / `fenestration_specs`。其余 6 个字段从文本可推，不是瓶颈。
>
> 主指标：[pivot_criteria.md](pivot_criteria.md) 视觉层阈值 — zone F1 ≥90% / 尺寸误差 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80。
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
- 手工修 Construction 单层引用后 EP PASS；artifacts 在 [`smalloffice_16_newarch/output/ep_run_glazingfix/`](../test_data/SmallOffice/smalloffice_16_newarch/output/ep_run_glazingfix/)

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
- 待 idfpy 切换时整体删 validator，这条临时性约束自然消失（[idfpy_embed.md](idfpy_embed.md)）

**作废**：原 A 改 prompt / B 后处理 / C 放宽 validator 三方案，不再做。

---

### B0''. [P1] sm_17 端到端首跑（异图验证）

**任务**：
- 用户在新 Claude Code 会话按 [new_case_guide.md §四](new_case_guide.md) 跑 Step 4 → 产 `smalloffice_17/output/intake_output.json`
- 助手按 [§5.0](new_case_guide.md) 触发协议跑下游
- 触发 `记录这次跑 sm_17 e2e_v1` 落 baseline

**验收**：与 B0 类似；关注 sm_17 是否暴露**新**类型 bug。
- 注意：simulate 跑通**不是**严格目标 —— 当前已知 fenestration glazing layer 兼容性 bug（[§C](#c-暂搁置依赖外部进展不安排时间)）会让 EP fatal，需手工修一行 Construction 才能跑（参考 sm_16_newarch glazingfix），或接受 IDF 落盘 + OpenStudio 视察作为终验
- 重点观察项：几何（zone 数 / 楼层 / 外包 / WWR）正确性、是否有**新**类型 prompt-level bug

**依赖**：无（T-vertex 阻塞已解除；fenestration glazing bug 已知非新阻塞）

---

## 阶段 1 — 恢复

### B1. [P0] 旧 skill 能力迁移到新架构（恢复 sm_16 旧建模水平）

**背景**：旧架构（[skills/energyplus_mcp/](../skills/energyplus_mcp/) + Claude Opus 单会话 + skill 分步约束）能在 sm_16 上拿到准确建模。新架构（半人工 Step 4 prompt + 9 subagent 自动下游）的 intake 路径虽然已切到 [src/agent/nodes/intake.py](../src/agent/nodes/intake.py#L34) + `skills/energyplus_mcp/*.md` 规则文档库，但在迁移初期仍是简版，**没把旧 skill 的分步识图 / 绘图标注 / 自检约束等内容完整迁过来** → sm_16_newarch 建模质量不及旧架构 sm_16 baseline。

**第一原则**：**先恢复，再升级**。新架构必须先到达旧架构能做到的水平，才有资格谈 B5-B7 的能力扩展。

**任务**：
- [ ] **审计旧 skill 内容**：盘点 [skills/energyplus_mcp/](../skills/energyplus_mcp/) 当前规则文档库与 `../Skill_history/` 历史快照之间的能力映射，列清单
  - 历史备份在 `../Skill_history/` 各目录，参考 [CLAUDE.md §6 #5](CLAUDE.md)
  - 重点：sm_15 几何/MEP 阶段拆分（[CLAUDE.md §5.1](CLAUDE.md)）/ 全局唯一世界坐标系 / 占位 construction 命名
- [ ] **增强新架构 intake 规则文档库**（半人工流的 Step 4 prompt 模板也同步）：
  1. 先识别外墙边界（输出闭合多边形）
  2. 再读尺寸链数字（自检 `sum(segments) + 2 × wall ≟ total_width`）
  3. 再识别走廊（宽白连通区）
  4. 再识别楼梯 / WC / 电梯符号
  5. 综合为 zone 列表 + x/y 范围
  6. 再生成 surface 邻接矩阵（可机械推导）
- [ ] 把 [new_case_guide.md §4.2](new_case_guide.md) Step 4 prompt 里临时补的 `Floor_N_*` 模板禁用规则正式合并进 intake 规则文档库与运行时 intake 路径
- [ ] 用 sm_16 重跑半人工流，与旧架构 sm_16 baseline 对账（zone 数 / 楼层 / 外包 / WWR / 特殊 zone 命中）
- [ ] 落 `test_data/test_baseline/runs/<date>_capability_recovery_v1/notes.md`

**工作量**：~1 周

**验收**：
- sm_16 半人工流复跑结果在主指标上**追平或超过**旧架构 sm_16 baseline
- 关键差距点（如有）落到 notes.md 当作阶段 2 评测体系第一批锚点

**依赖**：无（B0 全链路通已具备，可直接迭代 prompt）

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
- 与 [test_baseline/](../test_data/test_baseline/) 现有数据交叉对验

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
- 半人工流：用户在 Claude Code 会话按 [new_case_guide.md §四](new_case_guide.md) 跑全部 GT case 一次（4 case × ~10 分钟人工 = ~半天）
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
- 与 [pivot_criteria.md §4.4](pivot_criteria.md) 阈值对齐 → 看现状离阈值多远

**依赖**：B1 + B2 + B3 + 用户重复 Step 4 四次

> 注：原 plan.md "Anthropic API 直跑 4 case" 方案因用户无 API key 已废；改为半人工。

---

## 阶段 3 — 能力升级

### B5. [P1] 能力升级 1 — 非方形平面（如 L 形 / U 形）

**背景**：当前 sm_13-17 全是矩形平面。真实建筑常见 L 形 / U 形 / 凹凸异型。需要 INTAKE_SYSTEM_PROMPT + zone_specs / surface_specs 拓展支持任意闭合多边形外包。

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
  - [ ] 在 [new_case_guide.md §四](new_case_guide.md) Step 1 加规约说明，让用户准备图纸时按约定标
  - [ ] INTAKE_SYSTEM_PROMPT 加"按规约识别"分支

- ② **工具侧预处理**（原 B5 PaddleOCR + cv2 内容并入此处）：
  - [ ] 新建 `Tool_scripts/preprocess_floor_plan.py`：
    - PaddleOCR 提平面图所有数字 + 坐标 → JSON
    - cv2 形态学找宽白连通区 → 走廊 bbox 候选
    - 颜色滤波 + 模板匹配找门 / 窗 / 楼梯符号 → 实例列表
    - 输出 `<case>/output/preprocess.json`
  - [ ] [new_case_guide.md Step 4](new_case_guide.md) prompt 模板加「预处理结果（可信度高）」段，让用户先跑预处理脚本，把结果贴给 Opus 当 hint

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
- 候选模型至少一档达 Opus 80%+（[pivot_criteria.md §4.4](pivot_criteria.md) 阈值）
- 落对比表到 [open_model_guide.md](open_model_guide.md)

**依赖**：B1-B7 完成

---

### B9. [P3] LoRA SFT + Pivot 切换（M5/M6）

**任务**：
- 见 [pivot_criteria.md §4.1](pivot_criteria.md)：用 Opus baseline 的 IntakeOutput JSON 集合作 SFT 数据种子（≥500 对，需扩 GT 集到 ≥10 case）
- LoRA 微调候选开源模型
- holdout 集评测达 Opus 80% 后切 [llm.yaml](../src/configs/llm.yaml) `intake` 默认 provider
- 全量回归

**工作量**：~2-3 周

**验收**：[pivot_criteria.md](pivot_criteria.md) 全部阈值达标

**依赖**：B8 完成 + Pivot 阈值达标判定

---

## C. 暂搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[idfpy_embed.md](idfpy_embed.md)）：等协作者完成 [§3.1 MCP 全线重写](idfpy_embed.md)；本项目侧 §3.2 等他们交付后再启
- **token_optimization §4.1-4.5**（[token_optimization.md](token_optimization.md)）：等 idfpy 切换完成后大量 CRUD 工具消失，重新评估
- **OpenStudio 几何验收 sm_15/16/17**（[CLAUDE.md §8.1](CLAUDE.md)）：用户人工跑，不卡代码
- **fenestration / construction Construction layer 兼容性 prompt 修**（2026-05-07 sm_16_newarch 真跑发现）：
  - bug：`WindowMaterial:SimpleGlazingSystem` 被当作可串联玻璃层（与 air gap + 第二片玻璃组成三明治） → EP window 求解器收敛失败 NaN fatal
  - 实例：sm_16_newarch `Window_Double_Glazing` Construction → `F1_NORTH_W_WINDOW` fatal；手工把 Construction 改成单层引用 SimpleGlazing 后 EP `Completed Successfully` / 0 severe
  - 副 bug：`Glass_Clear_6mm` U=5.7 是单层透明玻璃值，但命名 `Double_Glazing` —— 命名/数值不一致
  - **不修原因**：用户决策当前焦点是几何正确性；idfpy 自带 schema 校验切换后会原生拒绝该组合，短期改 prompt 属重复投资
  - **启动条件**：idfpy MCP 重写交付后（[idfpy_embed.md](idfpy_embed.md)）一并解

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

- [architecture.md](architecture.md) — 当前架构事实参考
- [CLAUDE.md](CLAUDE.md) — 项目管理总览（精简版）
- [new_case_guide.md](new_case_guide.md) — 新建测试样例 7 步流程（半人工版）
- [pivot_criteria.md](pivot_criteria.md) — Pivot 双阈值
- [open_model_guide.md](open_model_guide.md) — 开源模型操作手册
- [idfpy_embed.md](idfpy_embed.md) — idfpy 替换主线（搁置中）

---

_2026-05-07 (晚 v2) — B 段三阶段重组（用户路线图）：阶段 1 恢复 [B1] / 阶段 2 评测基线规范化 [B2-B4] / 阶段 3 能力升级 [B5-B7] / 远期 [B8-B9]。新 B1 = 旧 skill 约束迁移到新架构（吸收原 B4 CoT 内容）；新 B4 = Opus baseline + 校对方案 + token 协议升级（吸收原 B0'''）；新 B5/B6/B7 = 非方形平面 / 全局坐标退台挑空 / 规范化绘图（含原 B5 PaddleOCR 预处理）；新 B8/B9 = 原 B6/B7 远期 pivot。Milestone 映射加 M0 恢复阶段。_

_2026-05-07 (晚) — 真跑 sm_16_newarch IDF 喂 EP 实证：T-vertex 不卡 EP（B0' 关闭），真 fatal = fenestration_agent SimpleGlazing layer 兼容性 bug，手工修后 EP PASS。决策：不调 prompt，与 idfpy 切换一并解；当前主线焦点切到几何正确性。推荐顺序去 B0；B0/B0'/B0''/§C 全更新。_

_2026-05-07 — A 段四项全闭环（A1 schema drift PASS / A2 多 section LLM / A3 run_full_pipeline 三入口 / A4 文档全修订），从主体下沉到表格；新增 B0 sm_17 端到端首跑作为半人工流验证；B3 改半人工版（用户无 Anthropic API）；B4 加入 Floor_N_* 模板禁用补丁；B5 改 Tool_scripts 预处理脚本（半人工流 intake 在会话外）；B6 footnote 去掉 A2 依赖（已就绪）；C 段加 sm_17。_

_2026-05-05 全文重写。删旧版 CoT vs 前置小模型探讨；按 architecture.md 新架构理解重组为「代码跑通 + 识图能力」两线 TODO。_
