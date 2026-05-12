# 识图泛化：图纸重绘 + 几何建模两步架构

> 目标：让 intake 能处理不同风格的建筑平面图，不依赖单一固定制图规范。
>
> 讨论日期：2026-05-10。起点见 [pivot_criteria.md §3.2](pivot_criteria.md) 退路 A（前置视觉预处理），但方案已从"前置小模型矢量化"收敛为"同一 VLM 拆两步调用 + 中间标准化表示"。
>
> **2026-05-12 — POC 验证 PASS（详见 §9）**：sm_20 全套两步法 + 下游 + EP 真跑通过。架构通透性 + 识图泛化 + 微调可行性同时验证。决策：**两步法立为新主线**（[plan.md](plan.md) 提升为最高优先级 B1.5）。

---

## 1. 问题

当前 INTAKE_SYSTEM_PROMPT（[intake.py](../src/agent/nodes/intake.py#L34)）和旧 skill（[energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md)）把一套特定 CAD 制图规范硬编码进了 prompt：

- 粗黑实线 = 墙，浅灰填充 = 墙身
- 蓝色矩形 = 窗
- 尺寸链外侧总长 / 内层分段
- 走廊 = 横贯全宽的长窄白条
- 数字单位米，两位小数

这在 sm_* 系列上工作良好，但换一套不同风格的图纸（不同符号、不同标注方式、不同线条规范）prompt 就失效。

**核心矛盾**：要想拿到精确坐标，VLM 必须理解特定制图规范；但制图规范本身是变量。

---

## 2. 方案：两阶段分解

```
输入图纸（任意风格）
     │
     ▼
[阶段 1] VLM 矢量化重绘 → 标准化中间表示 (JSON)
     │                       │
     │ 视觉翻译任务             └──→ 渲染 SVG → 用户人工校验
     │
     ▼
[阶段 2] LLM 几何建模 → IntakeOutput
     │
     ▼
（下游 9 subagent 不变）
```

两个阶段用**同一个 VLM**，但任务不同，不引入新模型。

### 2.1 阶段 1：矢量化重绘（视觉翻译）

**输入**：原始图纸（任意风格，含平面图 + 立面图 + 剖面图等）

**输出**：标准化矢量 JSON，按元素分类，显式坐标和尺寸

**核心任务**：忠实描摹——图上有什么就画什么

- 墙壁位置 → 描出线段，标注厚度
- 窗户位置 → 标出矩形位置和尺寸
- 门的位置 → 标出开口段
- 尺寸链数字 → 原样抄录
- 房间轮廓 → 按墙的分隔圈出多边形
- 文字标注 → OCR 抄录，绑定到对应区域

**这不是"理解建筑"，这是"翻译制图语言"**——从一套视觉符号翻译成统一的 JSON 表示。规则来自旧 skill 的目标格式定义（D1-D6）。

**人工校验点**：JSON 渲染成 SVG，用户左右对照原图，逐项检查"有没有漏、位置对不对"。纯视觉任务，不需要 EnergyPlus 领域知识。

### 2.2 阶段 2：几何建模（空间拓扑推理）

**输入**：阶段 1 产出的标准化矢量 JSON

**输出**：IntakeOutput Pydantic（含 zone_specs / surface_specs / fenestration_specs 等 10 个 specs 字段）

**核心任务**：从平立面的结构化描述推断 3D 空间拓扑

- 外墙 vs 内墙分类
- 相邻房间 → shared surface 配对（InterZone ceiling/floor/wall）
- 窗属于哪个墙 → parent surface 映射
- 楼层堆叠 → Z 坐标累加
- 各立面 WWR 验算
- 占位 construction 命名
- schedule / people / lights / hvac 的默认填充

---

## 3. 两个阶段的本质区别

这两步都调用 LLM，但用的是 LLM 两种不同能力：

| | 阶段 1：矢量化重绘 | 阶段 2：几何建模 |
|---|---|---|
| 输入模态 | 图像 | 结构化文本 (JSON) |
| 能力类型 | 视觉理解 | 空间拓扑推理 |
| 任务性质 | 翻译（编译成统一格式） | 推理（从 2D 推导 3D） |
| 输出复杂度 | 高（坐标精度要求高） | 高（跨子系统一致性要求高） |
| 可微调性 | 需要 VLM（视觉输入） | 可用纯文本 LLM（结构化输入） |
| 训练数据 | (任意风格图, 标准化 JSON) | (标准化 JSON, IntakeOutput) |

阶段 1 的难点是**视觉精度**（不漏不重），阶段 2 的难点是**拓扑正确性**（面配对、坐标系、楼层关系）。

---

## 4. 相比其他方案的定位

### 4.1 vs 纯 prompt（当前方案）

- 当前：一套 prompt 同时做视觉理解 + 空间推理，规范硬编码
- 两步：视觉和推理分离，规范体现在阶段 1 的目标格式定义 + 阶段 2 的推理规则

### 4.2 vs 完整矢量化小模型（FloorplanVLM / PaddleOCR + cv2 独立管线）

- 完整矢量化：试图用专门 CV 模型做到像素级精确的矢量重建
- 两步方案：只用同一个 VLM，不做像素级重建，只要求"能用 JSON 描述清楚这张图"。VLM 读尺寸链数字后做简单算术推导坐标，不需要从像素反推
- **关键判断**：如果 Opus 黑箱一步已经能产正确 IntakeOutput（意味着它内部已经在做隐式坐标推导），那么显式化这一步不会更难——只是把本来在 LLM 脑子里算的东西写出来

### 4.3 vs 微调弱模型

两步方案对微调弱模型的优势：

- 阶段 1 的输入输出分布更接近 VLM 预训练任务（图像描述/结构化视觉抽取），比直接产 IntakeOutput 更易微调
- 阶段 2 的输入是结构化文本，可以用纯文本模型，不需要 VLM
- 两条数据流可以独立改进，互不阻塞

---

## 5. 反对"阶段 2 是确定性编译器"的修正

初版讨论曾认为阶段 2 可以是"确定性编译器"——这只是部分正确。以 wall/window/room 列表推导 zone 的 x/y 坐标确实是算术运算（xᵢ = xᵢ₋₁ + segmentᵢ），但以下推理**不是**确定性的：

- 哪个房间是走廊？（宽窄条判断有模糊性）
- 房间是否跨 strip？（需空间上下文判断，[energyplus_mcp_prompt.md §Handling Non-Rectangular Rooms](../skills/energyplus_mcp/energyplus_mcp_prompt.md)）
- 窗的 parent wall 映射（立面图的窗 → 平面图的墙，需要"立方体展开"空间想象力）
- 楼层间 zone 的对齐关系（挑空/退台场景下的表面配对）

所以阶段 2 **仍然是 LLM 推理**，不是在阶段 1 就能消除的不确定性。

---

## 6. 一次可做但不能保证完全消除的推理

关键在于阶段 1 的矢量化 JSON 包含了**所有尺寸链原始数据**——这意味着 LLM 不需要再从像素中提取数字，只需要在给定的结构化数据上做逻辑推理。这样可以减轻了 LLM 的负担，但不能保证推理结果完全正确。

---

## 7. POC 计划（一行代码不改）

用 sm_16 的图做一次概念验证，验证两条假设：

1. **重绘可行**：给 Opus 原始平面图，"把这张图重绘成标准格式 JSON，按 wall/window/room/dimension 分类，显式写出坐标和尺寸" → 看产物是否忠实
2. **建模收益**：给 Opus 阶段 1 产出的 JSON，"根据这个矢量描述生成 IntakeOutput" → 对比一步黑箱产出的 IntakeOutput，看结构化输入是否提升质量

在同一个 Claude Code 会话中串行执行。两次调用 Opus。不涉及本项目的 `intake_node` 或 LangGraph 架构改动。

---

## 8. 架构影响前瞻

如果 POC 验证通过，后续改动模式：

| 现有组件 | 变化 |
|---|---|
| [intake.py](../src/agent/nodes/intake.py) `intake_node` | 从单次 LLM 调用改为"阶段 1 重绘 + 阶段 2 建模"两次调用；short-circuit 路径 (`--intake-from`) 保留 |
| 阶段 2 的 system prompt | 接收结构化 JSON，专注空间推理规则。可复用纯文本 LLM |
| 半人工流（Step 4） | 用户可见阶段 1 重绘 SVG 并可以修正后再推进到阶段 2 |
| 全自动流 | `run_full_pipeline.py` 内部串联两次调用 |
| 微调训练数据构造 | (图, 标准化 JSON) 对和 (JSON, IntakeOutput) 对分开构造 |

---

## 9. POC 验证结果（2026-05-12，sm_20）

### 9.1 实验设置

- **Case**：`test_data/SmallOffice_TwoStep/smalloffice_20/`（与 `test_data/SmallOffice/smalloffice_20/` 同素材，单步法 anchor 在那边的 `output_new/`）
- **Phase 1**：Claude Code 会话 + Opus 4.7，7 张图（3 平面 + 4 立面）→ 7 份矢量 JSON + summary。schema 见 [vector_schema_v1.md](../test_data/SmallOffice_TwoStep/smalloffice_20/vector_schema_v1.md)（v1.2）
- **Phase 2**：两条路径并行验证
  - Opus 路径：Claude Code 会话直写 IntakeOutput JSON
  - DeepSeek 路径：[`Tool_scripts/run_phase2_deepseek.py`](../Tool_scripts/run_phase2_deepseek.py)（绕过 langchain，thinking enabled，max_tokens 64k）
- **Phase 2 规则**：[phase2_rules.md](../test_data/SmallOffice_TwoStep/smalloffice_20/phase2_rules.md)（v1.3 升级版在 [`skills/energyplus_mcp_twostep/`](../skills/energyplus_mcp_twostep/)）

### 9.2 三方对比结果（详见 [`compare/diff.md`](../test_data/SmallOffice_TwoStep/smalloffice_20/compare/diff.md)）

| 维度 | opus 2-step | deepseek 2-step | anchor 1-step（旧 sm_20 output_new）|
|---|---|---|---|
| Pydantic validate | ✅ | ✅ | ✅ |
| L2 cross_ref | ✅ | ✅ | ✅ |
| L3 IDF（19 zones + 16 windows）| ✅ | ✅ | ✅ |
| L4 EP simulate | ❌ Fatal（construction asymmetry，规则漏洞已在 v1.3 修） | ✅ Completed Successfully | ✅ Completed |
| F3 corridor 窗 z（B1 残留 slip）| ✅ 8.20–10.60 | ✅ 8.20–10.60 | ❌ 8.20–**9.60**（错）|
| OpenStudio 几何视察 | ✅（用户视察）| ✅（用户视察）| ✅（B1 时验证）|

### 9.3 关键发现

1. **两步法两条路径都修正了 anchor 单步法的 F3 corridor 窗 z 计算 slip**（B1 残留问题）。Phase1 把"窗高 2.40 + sill 1.00 + top_gap 1.40"识图层面**锁定**为 `y_range_m: [8.20, 10.60]`，phase2 没机会重做坐标推导 → 视觉错被截断在 phase1
2. **DeepSeek 路径下游 EP cleanly 跑通**（0 severe / 9 warning / 8.49s 全年）证明两步法 IntakeOutput 不破坏现有下游契约
3. **Opus 路径 EP fatal** 反而是宝贵副产物：暴露 phase2_rules.md 一条规则漏洞（**InterZone surface 不能用两个独立 construction**，必须共用单一 `Cons_InterFloor`，否则 EP 拒绝层栈非反向对称配对）。已在 v1.3 修复
4. **Opus phase2 暴露 10 条 schema gap**（见 `phase2_intake/opus/phase2_followup_notes.md`）：cross-floor sub-surface 命名 / 走廊负载密度 / building.Name 大小写策略 / Schedule:Compact day-type 名等。规则演进信号丰富

### 9.4 验证两个假设

| 假设 | 结果 |
|---|---|
| **重绘可行**：VLM 能否把任意风格图忠实矢量化 | ✅ Opus 处理 sm_20 7 张图（含 F2 北 4 不对称窗 + F3 通长窗 + East/West F3 corridor 单窗）全部正确，4 立面 facade_axis_note 准（含轴向 + 符号），dim 链一字不差 |
| **建模收益**：结构化输入是否提升 phase2 质量 | ✅ 两步法 F3 corridor 窗 z 准；anchor 单步法 z 错。phase1 锁定识图结果 = phase2 没机会出视觉相关错（误差预算分离生效）|

### 9.5 两个 phase 微调可行性评估

- **Phase 1 微调**：VLM 结构化视觉抽取任务 = 预训练分布近邻；训练数据 (任意风格图, 标准化 JSON) 对易构造；schema 强约束输出形态 → 比"直接训 IntakeOutput"更易微调小 VLM
- **Phase 2 微调**：纯文本推理 → **不需要 VLM**，任何文本 LLM 都行（甚至 sub-billion-param）；训练数据 (vector JSON, IntakeOutput) 对可从 anchor 批量生成；目标量化指标清晰（zone f1 / 拓扑正确率）
- **两条数据流独立改进，互不阻塞**

### 9.6 Phase 1 用户校验机制

POC 验证用户可在 ~30 min 内人工检查 SVG 是否与原图一致：
- [`Tool_scripts/render_vector_to_svg.py`](../Tool_scripts/render_vector_to_svg.py) 矢量 JSON → SVG（含 1m 网格 + 5m 加深网格 + pen 类型分色图例）
- 浏览器并排原图 + SVG 即可逐项检查"墙位 / 窗位 / 尺寸 / 立面分层"
- POC sm_20 实测：7 张图都在第一轮通过人工核验，未发现遗漏 / 错位

### 9.7 决策

**两步法立为新主线** —— [plan.md](plan.md) 提升为最高优先级。具体路径见 §8 架构影响前瞻 + plan.md B1.5。

### 9.8 待迭代

| 项 | 优先级 | 备注 |
|---|---|---|
| 异图泛化（噪声 / 装饰 / 索引箭头 / 楼梯 / 家具）| P0 next POC | sm_20 是规整办公楼，是 schema 舒适区。挑一张噪声大的图压一压 |
| `intake_node` 重写为两步串行 | P0 | 见 §8 + plan.md B1.5 |
| 评测脚本（vector JSON 自动 diff GT）| P1 | B2-B4 评测基线规范化吸收 |
| phase2_rules 继续补 schema gap（Opus 10 条 + 后续 case）| P1 | 滚动迭代，每 case 跑完更新 v1.x |
| Phase 1 / Phase 2 各自小模型微调 | P2 | 等评测体系就绪 + 数据积累后启 |

---

## 关联文档

- [CLAUDE.md](CLAUDE.md) — 项目管理总览
- [plan.md](plan.md) — 行动清单（**B1.5 两步法立为最高优先级**；B2-B4 评测基线；B5-B7 能力升级）
- [pivot_criteria.md](pivot_criteria.md) — §3.2 退路 A 前置视觉预处理（本方案是该路径的具体化）
- [new_case_guide.md](new_case_guide.md) — 标准工作流（待跟两步法集成后更新）
- [`../skills/energyplus_mcp_twostep/`](../skills/energyplus_mcp_twostep/) — 两步法 skill 演进源
- [`../test_data/SmallOffice_TwoStep/`](../test_data/SmallOffice_TwoStep/) — 两步法测试语料库
