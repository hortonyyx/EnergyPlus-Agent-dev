# 多模态输入 Agent 项目管理文档

> 负责人工作区：面向 EnergyPlus-Agent 项目的「多模态（图像+文本）输入 → IDF 自动构建」模块。
> 本目录（`AI_agent/`）用于沉淀该模块的方案设计、实验记录、模型迁移计划与交付物。

---

## 1. 项目总览（上下文索引）

### 1.1 仓库定位
- 根目录：[../](../)
- 项目说明：[../README.md](../README.md)
- 目标：将建筑设计意图（YAML / 自然语言 / 建筑图纸）自动转换为合法的 EnergyPlus IDF，并完成仿真。

### 1.2 与本模块相关的关键路径

| 路径 | 作用 | 与本模块的关系 |
|---|---|---|
| [../src/agent/](../src/agent/) | LangGraph 多阶段 Agent 实现 | 本模块直接扩展此处 |
| [../src/agent/graph.py](../src/agent/graph.py) | Agent 拓扑（intake → phase1 → cross_ref → … → simulate） | 入口为 `intake`，多模态信息从这里进入 |
| [../src/agent/nodes/intake.py](../src/agent/nodes/intake.py) | 多模态 intake 节点（text + base64 images → `IntakeOutput`） | **核心改造点**：结构化输出依赖 tool-calling |
| [../src/agent/llm.py](../src/agent/llm.py) | LLM 工厂（基于 LangChain `init_chat_model`） | **模型切换入口** |
| [../src/configs/llm.yaml](../src/configs/llm.yaml) | LLM provider / model / base_url / api_key 配置 | 切到开源模型时在这里改 |
| [../src/agent/state.py](../src/agent/state.py) | `AgentState` / `IntakeOutput` / `image_paths` | 多模态字段定义 |
| [../src/agent/nodes/](../src/agent/nodes/) | 各子系统阶段节点（zone / material / schedule / …） | intake 产出的 `*_specs` 在这里消费 |
| [../src/agent/tools/](../src/agent/tools/) | 阶段 Agent 调用的 MCP 工具封装 | 模型需支持稳定 tool-calling |
| [../skills/energyplus_mcp/](../skills/energyplus_mcp/) | 现有基于 Claude Opus 的 skill 提示词 | 迁移到开源模型时做提示词对齐 |
| [../scripts/run_demo.py](../scripts/run_demo.py) | 端到端 demo（硬编码文字输入） | 目前无图像通路的 demo |
| [../tests/test_zone_agent.py](../tests/test_zone_agent.py) | 仅 zone_agent 的单元测试 | **目前唯一自动化测试** |

### 1.3 当前技术栈要点
- **LangGraph + LangChain**：`init_chat_model("{provider}:{model_name}")` 路由到具体 provider。
- **多模态入口**：`intake_node` 将 `state.image_paths` 读成 base64 → `ImageContentPart` → `HumanMessage.content` 列表。
- **结构化输出**：`llm.with_structured_output(IntakeOutput, include_raw=True)` → 依赖 tool-calling（当前默认 Anthropic）。
- **下游阶段**：所有阶段 Agent 都以 intake 产出的自然语言 `*_specs` 为输入，调用 MCP 工具构建 `ConfigState`。

---

## 2. 我负责的范围（多模态输入部分）

### 2.1 范围界定
**In-scope**
1. `intake_node` 的多模态理解能力（图纸 + 文本 → `IntakeOutput`）。
2. `src/agent/llm.py` 的 provider 抽象与本地/开源模型接入。
3. Skill 提示词（`skills/energyplus_mcp/*.md`）向开源模型的迁移与重写。
4. 多模态测试数据集建设与回归基准。
5. 本地部署方案（推理后端、显存/吞吐、tool-calling 可用性）。

**Out-of-scope（其他同事负责）**
- 下游阶段 Agent 的工具实现与修正。
- RAG 知识库。
- IDF 转换器与 EnergyPlus runner。
- 结果解析/可视化。

### 2.2 当前状态快照

| 维度 | 现状 | 风险 |
|---|---|---|
| 模型 | `src/configs/llm.yaml` 写的是 `anthropic:gpt-5.4`（疑似占位/错配），实际案例测试调用 Claude Opus | 配置与实际运行不一致需核对 |
| 多模态入口 | `intake_node` 已实现 base64 图像注入 | 仅在 Anthropic Messages API 下验证过 |
| 结构化输出 | `with_structured_output(IntakeOutput)` 依赖 tool-calling | 开源多模态模型 tool-calling 成熟度参差 |
| 测试 | 只有 `test_zone_agent.py`（纯文本，不涉图像） | **没有多模态回归测试** |
| 基准数据 | `skills/energyplus_mcp/top_view.png` + `top_view_annotated.png` 各 1 张 | 样本量不足以支撑评测 |
| Skill 文档 | 写给 Claude（含 Python `PIL` 脚本、白底红字标注规范等） | 需适配开源模型的能力画像 |

---

## 3. 当前「测试方案」盘点

> 结论：**尚未形成系统化的多模态测试方案**，是一条人工驱动的对话流水线。

### 3.1 已有的测试资产

#### 3.1.1 自动化代码资产（弱）
1. **单元测试**：[../tests/test_zone_agent.py](../tests/test_zone_agent.py)
   - 覆盖：`zone_agent` 在纯文本 `zone_specs` 下生成 2 个 zone。
   - 不覆盖 intake、图像输入、端到端。
2. **端到端 demo**：[../scripts/run_demo.py](../scripts/run_demo.py)
   - 用 `HARD_USER_INPUT` / `SIMPLE_USER_INPUT`（[../scripts/_share.py](../scripts/_share.py)）硬编码文本。
   - 不读取图像；`AgentState.image_paths` 始终为空。

#### 3.1.2 人工测试数据集（[../test_data/](../test_data/)）
**14 个 SmallOffice 案例**：`smalloffice_0` … `smalloffice_12` 为早期无尺寸基线；`smalloffice_13` 是 2026-04-21 起的新规格首案(带两级尺寸链 + 4 facade 朝向命名 + 产物集中在 `output/`)。早期 13 案例包含：

| 文件 | 角色 |
|---|---|
| `testdata_prompt.json` | Format A 入口：位置、层数、每层 zone 数、总 zone 数、4 张视图路径 |
| `top_view.png` | 俯视平面图（主视觉输入） |
| `front_view.png` / `side_view.png` | 立面图 |
| `<hash>.png` | 补充平面图（可选） |
| `claude_ep.md` | LLM 产出的分区规划（邻接矩阵 + 坐标表 + ASCII 平面图） |
| `smalloffice_N.yaml` / `smalloffice_N_final.yaml` | 导出的 YAML 配置 |
| `top_view_annotated.png` | LLM 裁剪+6×放大后画的标注图（部分案例有） |
| `output/smalloffice_N.idf` | 转换后的 IDF |
| `output/eplusout.*` | EnergyPlus 仿真产物（仅 `smalloffice_0` 有全套） |

**流水线通过率（Claude Opus 人工基线，共 13 个案例）**：

| 环节 | 通过 | 通过率 | 案例 |
|---|---|---|---|
| claude_ep.md | 12/13 | 92% | 缺 sm_12 |
| YAML | 8/13 | 62% | sm_0,1,2,3,4,5,7,8,11 |
| IDF | 7/13 | 54% | sm_0,1,3,4,5,7,11 |
| EP 仿真启动 | 1/13 | 8% | 仅 sm_0 |
| **EP 仿真完成** | **0/13** | **0%** | sm_0 Fatal 终止（3 Severe） |

**几何正确性（zone 数量 vs `testdata_prompt.json` 声明）**：在生成到 YAML 的 8 个案例里，6 个匹配（sm_0/1/3/4/5/11），2 个偏差（sm_7 少 12 个 zone，sm_2 未完成）。整体 6/13 ≈ 46%。

**系统性缺陷**（7 个到 IDF 的案例统计）：
- 所有案例都缺 `Schedule:Compact`（0 个）
- 所有案例都缺 `Lights`（0 个）
- 所有案例都缺 `HVACTemplate:Zone:IdealLoadsAirSystem`（0 个）
- 仅 sm_1(1)、sm_11(24) 创建了 fenestration；其余为 0

**sm_0 Fatal 根因**：跨区内墙构造两侧不对称（`Int_Wall` vs `Default_Construction`，层数不同）→ InterZone 不匹配。正是 [export_idf.md](../skills/energyplus_mcp/export_idf.md) 规定要用 `Adiabatic + Int_Wall` 修复的问题，但导出时未执行该补丁。

**失败阶段分布**：
| 阶段 | 案例 | 主因 |
|---|---|---|
| 连 claude_ep.md 都无 | sm_12 | 对话中断 |
| 规划 → YAML 中断 | sm_6/9/10 | 大规模案例（≥30 zones）tool-call 轮数爆炸 |
| YAML → IDF 中断 | sm_2/8 | 未完成 |
| IDF → EP 仿真 | 全部 7 个 IDF 案例 | 缺 Schedule/Lights/HVAC/fenestration；内墙构造不对称 |

> **重要洞察**：① 视觉理解不是瓶颈（12/13 生成了 `claude_ep.md`）；② 真正瓶颈是**长链路 tool-calling 的稳定性**与**子系统覆盖完整性**（Schedule/Lights/HVAC 普遍缺失）；③ `export_idf.md` 的 4 条修复补丁必须脚本化为**强制后处理**，不能交给 LLM 记得打。这些洞察直接指导开源模型的选型（tool-calling 稳定性优先于视觉参数规模）和评测指标设计（必须分五档 + 子系统覆盖率）。

#### 3.1.3 人工测试流程（当前做法）
把 `test_data/SmallOffice/smalloffice_N/` 路径丢给 Claude Opus，Claude 按 4 个 skill 文档的规范：
① 读 JSON + 4 张视图 → ② 裁剪/放大/画标注图 → ③ 写 `claude_ep.md` → ④ 串行调 MCP 工具累积 `ConfigState` → ⑤ 导出 YAML → ⑥ `ConverterManager` 转 IDF + 打修复补丁 → ⑦ `energyplus -w Shenzhen.epw` 仿真。**依赖 Claude 的**：高质量视觉、多步 tool-calling、长上下文、会话中执行 Python 代码。**没有脚本化评测、没有自动比对、没有批量回归。**

### 3.2 4 个 skill 文档的分工

| Skill | 在流水线里的定位 | 主要规定 |
|---|---|---|
| [energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) | 主控流程（总则） | 分区粒度（每房一 zone + 走廊 + 楼梯/卫生间/电梯）；从中文尺寸链读房间边界；zone 命名约定；图像裁剪+6×+白底红字标注 PIL 模板；`claude_ep.md` 必含邻接矩阵+坐标表（CCW 顶点）+ASCII 平面图；工具调用顺序；**先 list_\* 再 create**（材料/构造/日程/恒温器等可复用属性） |
| [zonetool_prompt.md](../skills/energyplus_mcp/zonetool_prompt.md) | create_zone 专项 | `floor_vertices` 必须是绝对世界坐标且 CCW；`x/y/z_origin` 仅为 Zone 元数据（通常取质心）；楼层 Z 约定；create_zone 会自动造 6 个 surface（需后改构造）；窗/门另调 `create_fenestration_surface` |
| [schedule_compact_guide.md](../skills/energyplus_mcp/schedule_compact_guide.md) | create_schedule_compact 参数格式 | `times` 嵌套结构：`[{Through, Days:[{For, Times:[{Until:{Time, Value}}]}]}]`；`Through` 必为 `MM/DD` 且最后段必须 `12/31`；每 day 的 `Times` 必以 `24:00` 收尾；`For` 合法枚举；4 种常见错误 |
| [export_idf.md](../skills/energyplus_mcp/export_idf.md) | YAML → IDF 收尾 | `BaseSchema.set_idf(idd)` → `ConverterManager().convert_all()` → 4 处修复补丁（RunPeriod None、warmup days、内墙改 Adiabatic+Int_Wall、Schedule:Compact None 字段）→ `save_idf` → `energyplus -w` 运行 |

**依赖链**：`energyplus_mcp_prompt`（主）→ 调 zone 工具前读 `zonetool_prompt` → 调 schedule 工具前读 `schedule_compact_guide` → 完成配置后读 `export_idf` 收尾。

### 3.2 已识别的测试空白（迁移开源模型前必须补齐）

| 空白 | 说明 | 优先级 |
|---|---|---|
| 无多模态 golden 数据集 | 缺少 (图像, 文本, 期望 IntakeOutput) 三元组 | P0 |
| 无几何准确度指标 | 需要 zone 数量、x/y 范围、相邻矩阵的自动比对 | P0 |
| 无 tool-calling 稳定性测试 | 开源模型易回吐文本而非 tool call | P0 |
| 无视觉能力分级 benchmark | 裁剪/标注/尺寸读取/走廊识别分别多难，未量化 | P1 |
| 无端到端跑通率指标 | intake → simulate 的成功率、失败阶段分布 | P1 |
| 无推理成本指标 | 显存、token/s、首 token 延迟 | P2 |

---

## 4. 迁移到开源模型的推进计划

### 4.1 候选开源多模态模型（待评估）
- **Qwen2.5-VL-7B / 32B / 72B-Instruct**（tool-calling 较成熟，中英文图纸友好）
- **InternVL2.5 / InternVL3 系列**
- **Llama 3.2-Vision-11B / 90B**
- **MiniCPM-V 2.6 / o 2.6**（轻量、适合单卡）
- **Pixtral-12B**

评估维度：① 图纸尺寸数字识别；② 房间/走廊/楼梯区分；③ JSON/tool-call 合规率；④ 中文输出稳定性；⑤ 本地部署显存。

### 4.2 推理后端候选
- `vLLM`（OpenAI 兼容端点，tool-calling 对齐 `langchain-openai`）
- `SGLang`
- `LMDeploy`
- `Ollama`（易部署，但 tool-calling 能力有限）

> 选型建议：首选 **vLLM + OpenAI 兼容 API**，只需把 `llm.yaml` 的 `provider` 改成 `openai`、`base_url` 指向本地服务，`create_llm` 无需改动。

### 4.3 里程碑（建议）

| M | 目标 | 产出 |
|---|---|---|
| M1 | 建立多模态 golden 数据集 v0.1（≥10 个建筑案例） | `AI_agent/datasets/` |
| M2 | 实现自动评测脚本（IntakeOutput diff + zone 几何比对） | `AI_agent/eval/` |
| M3 | 用现有 Anthropic 流水线跑出基线分数 | 基线报告 |
| M4 | 接入 vLLM + 候选开源模型，跑同一套评测 | 对比报告 |
| M5 | 针对 gap（tool-calling、图纸尺寸识别）做提示词 / few-shot / 必要时微调 | v1 迁移方案 |
| M6 | 切换 `llm.yaml` 默认 provider，回归全部测试 | 切换 PR |

### 4.4 风险登记

| 风险 | 缓解 |
|---|---|
| 开源模型 tool-calling 返回纯文本，`with_structured_output` 拿不到 `parsed` | 在 `intake_node` 加 JSON 修复层 / 回退到 `PydanticOutputParser` |
| 视觉模型读不准图纸尺寸数字 | 预处理时做 OCR 增强，或提供文字版尺寸清单作为冗余 |
| 上下文窗口不足（多图 + 长 prompt） | 分轮对话 / 图像压缩 / 只保留关键视图 |
| Skill 文档中 Python 执行步骤无法沿用 | 将「裁剪 + 标注」改成外部工具节点，不再由 LLM 自己写代码 |

---

## 5. 本目录（`AI_agent/`）结构与文档索引

### 5.1 当前已有文档（2026-04-20 盘点）

| 文档 | 作用 | 关键结论 |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文档 — 项目管理总览 / 下次会话初始上下文 | 范围界定、案例基线、里程碑、本轮会话决策沉淀 |
| [new_case_guide.md](new_case_guide.md) | 新建 SmallOffice 测试样例的 7 步流程 | 5 档验证清单 + 常见坑位 + 自动化蓝图 |
| [plan.md](plan.md) | 输入端 VLM 准确性提升方案（CoT vs 前置小模型）| **P0 评测基线先行 → P1 CoT + PaddleOCR → P2 符号检测 → P3 全矢量化** |
| [pivot_criteria.md](pivot_criteria.md) | 闭源 → 开源模型的 pivot 判定准则 | 双阈值（视觉 ≥90% + 流水线 ≥75% IDF）；四象限决策；低上限 4 条退路 |

### 5.2 规划中目录（按需创建，不提前 mkdir）

```
AI_agent/
├── claude.md / new_case_guide.md / plan.md / pivot_criteria.md   ← 已有
├── design/         # 方案设计（模型选型、提示词改造、架构图）
├── datasets/       # 多模态 golden 数据集（本项目直接复用 ../test_data/ 作为 v0）
├── eval/           # 评测脚本 & 指标
│   ├── run_case.py
│   ├── run_all.py
│   ├── metrics.py
│   └── reports/<YYYY-MM-DD>_<milestone>/
├── experiments/    # 单次实验记录（按日期 / 模型名）
│   └── <YYYY-MM-DD>_<model>/{transcript.md, trace.jsonl, result.json, decision.md}
├── prompts/        # 适配开源模型的提示词版本（分步 CoT 各版本）
└── deploy/         # vLLM / SGLang 启动脚本、Docker 配置、Langfuse self-hosted
```

---

## 6. 给接手者 / 协作者的约定

1. **模型切换入口唯一**：始终通过 [../src/configs/llm.yaml](../src/configs/llm.yaml) + [../src/agent/llm.py](../src/agent/llm.py) 切换，不在各节点内硬编码 provider。
2. **多模态改动只改 intake**：不要绕过 `intake_node` 把图像直接塞给下游阶段 Agent。
3. **每次模型/提示词变更**：在 `AI_agent/experiments/` 新建一次运行记录，至少包含：模型 ID、提示词 hash、评测结果、失败样本。
4. **提示词语言**：与主仓库保持一致（默认英文系统 prompt + 中文用户输入可接受）；若切到中文原生开源模型（如 Qwen-VL），可做对照实验。
5. **回归门槛**：在切换默认 provider 前，端到端跑通率不得低于当前 Anthropic 基线的 80%。

---

## 7. 本轮会话关键决策（2026-04-20 沉淀）

> 以下四条决策直接约束后续工作节奏。详细推演见对应子文档。

### 7.1 评测基线先行（最高优先级）
- **原则**：在任何优化（CoT 重写 / 前置小模型 / 模型切换）之前，必须先有可复现的 Opus 基线分数。
- **理由**：现有 13 个案例的通过率（§3.1.2）是人工统计的一次性结果，不是自动化回归；没有自动基线，任何优化都无法证明收益。
- **落地**：见 §7.5 Next Step。

### 7.2 P0 → P3 分期（来自 [plan.md](plan.md)）
| 阶段 | 内容 | 产出 |
|---|---|---|
| **P0（1 周）** | 写 `AI_agent/eval/run_case.py` + 5 档指标，跑 Opus 基线 | 可复现基线报告 |
| **P1（2–3 周）** | Skill 文档改写为分步 CoT + PaddleOCR 尺寸链 + cv2 走廊预处理 hook 接到 intake 前 | v1 提示词 + 前置预处理模块 |
| **P2（1.5–2 月，按需）** | YOLOv8 训练楼梯/WC/电梯符号检测器 | 符号检测模型（仅 P1 不足时） |
| **P3（不推荐）** | 全矢量化 raster-to-vector 流水线 | —— |

> 根因诊断（plan.md 已结论）：视觉理解**不是**主要瓶颈，真正瓶颈是长链路 tool-call 稳定性 + 子系统系统性漏调（Schedule / Lights / HVAC）。P1 必须同时解决「提示词结构化」和「强制后处理补丁」。

### 7.3 Pivot 双阈值（来自 [pivot_criteria.md](pivot_criteria.md)）
- **视觉层**：zone 匹配率 ≥ 90%、房间尺寸误差 ≤ 5%、走廊 F1 ≥ 0.85、特殊 zone F1 ≥ 0.80
- **流水线层**：claude_ep.md ≥ 95%、YAML ≥ 85%、IDF ≥ 75%、EP 完成 ≥ 50%
- **四象限决策**：两层都达阈值 → 可 Pivot；视觉达阈值但流水线不达 → 别动视觉模型先修下游；未达阈值且未收敛 → 继续调 prompt；触顶低于阈值 → 走 [pivot_criteria.md §3.2](pivot_criteria.md) 的 A/B/C/D 退路。
- **当前状态**：视觉 zone 匹配 ~46%（6/13）、流水线 IDF 54%、EP 完成 0% —— 均远低于阈值，**Pivot 议题尚未到判定时机**。

### 7.4 评测平台选型：Langfuse self-hosted（不选 LangSmith）
- **结论**：采用 Langfuse 自部署（Docker Compose 起），不使用 LangSmith SaaS。
- **理由**：项目终态是开源模型本地部署，SaaS 平台与「本地可控」目标相悖；Langfuse 支持 OpenTelemetry + LangChain callback，trace 可离线归档到 `AI_agent/experiments/`。
- **实施顺序**：先把 P0 评测脚本跑通（文件化 `reports/*.csv`），Langfuse 的接入放到 P1 阶段再做。

---

## 7.5 sm_13 首轮会话沉淀（2026-04-21）

> 本日围绕 **smalloffice_13** 案例建立新规格 + 修复基础设施阻塞项。要点全部进入 skill / new_case_guide 强约束,后续案例直接继承。

### 7.5.1 输入规格升级
- **两级尺寸链**(`top_view.png` 外部总链 + 外层分段链,数字黑色等宽字体、单位统一 mm)成为 sm_13 起的硬约束——让"房间尺寸中位误差"第一次有 GT 可比(对应 [pivot_criteria.md §1.1](pivot_criteria.md) 视觉阈值)。
- 立面图改为**按朝向命名**`{South|North|East|West}_view.png`,每文件即对应朝向的 facade。空串/缺文件 = 该朝向所有楼层无窗,**零个** `create_fenestration_surface` 调用。取消 `front_view` / `side_view` 的同义写法。
- `testdata_prompt.json` **暂时移除所有 GT 字段**(`_gt_meta`、`Ground truth *`),评测方案搭好后另拆 `gt.json` 分层持有。
- 细节见 [new_case_guide §1.1 + §1.2](new_case_guide.md) 与 skill [§D4–§D6](../skills/energyplus_mcp/energyplus_mcp_prompt.md)。

### 7.5.2 Fenestration 被提升为 IDF Workflow 独立第 5 步
- 历史 7 个到 IDF 的案例有 **5 个 0 窗**——根因是 skill 把开窗埋在 IDF Step 4 的一句话里,且没有结构化 Fenestration Table 要求。
- 已改:skill 里 IDF Tool Usage Workflow 拆成 6 步,Step 5 专门为 Fenestration;[zonetool_prompt §M7](../skills/energyplus_mcp/zonetool_prompt.md) 新增 Wall-index → facade 映射表(Wall_1=南 / Wall_2=东 / Wall_3=北 / Wall_4=西,对应 zone CCW 顶点从 SW 起)。
- `claude_ep.md` 必须含 Fenestration Table,每行 → 一次 `create_fenestration_surface` 调用,父墙名直接用 `<zone>_Wall_<i>` 查表,不再让 LLM 用 `list_surfaces` 去试探。
- [new_case_guide §6.4](new_case_guide.md) 加了窗户专项自检脚本。

### 7.5.3 MCP 挂载基础设施修复
- **typer/click 0.24+8.3 签名冲突**:`uv run main.py mcp-server` 抛 `AttributeError: 'list' object has no attribute 'isidentifier'`,原因是 [main.py](../main.py) `run_agent` 命令用了 `Annotated[X, Option(default, "--flag", ...)]`——新版把 `Option()` 所有位置参数当 decls,`[]` / `Path("output")` 不是 str 就炸;一个命令坏会拖垮 `app()` 全部注册。已改为默认值写签名等号右侧,`Option()` 只留 flag 名。
- **仓库根补 [../.mcp.json](../.mcp.json)**(内容指向 `uv run python main.py mcp-server --transport stdio`,server key 用 `EnergyPlus-Agent` 与 skill 内工具名前缀 `mcp__EnergyPlus-Agent__*` 一致)。此前会话启动时工具列表没有 `mcp__*`,导致 sm_13 首轮退化到手写 `build_yaml.py`(见 [sm_13 run_log §4 / §5.1](../test_data/SmallOffice/smalloffice_13/output/run_log.md))。

### 7.5.4 标注图 + 产物目录规范
- **废弃 6× crop 模板**:旧 [skill §2b](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 的 `img.crop(LEFT,TOP,RIGHT,BOTTOM) + 6× NEAREST` 把外围尺寸链都裁掉、再把 PNG 放成 10k+ 像素宽——人工审图时只看得到建筑主体左 1/3。改为**不裁剪** + 最多 2× 放大,保留外围尺寸数字可读。
- **产物全部进 `output/`**:`top_view_annotated.png` / `claude_ep.md` / YAML / IDF / 临时脚本 / `run_log.md` / `eplusout.*` 都写 `<case_dir>/output/`;输入 PNG + `testdata_prompt.json` 保留在案例根。衍生品与输入分层,便于覆盖式重跑。[new_case_guide §6.1](new_case_guide.md) 目录树重画。

### 7.5.5 下轮 Claude 开会的变更检查点
1. 启动 Claude Code 时应自动弹出挂载 `EnergyPlus-Agent` server 的请求,接受后 `mcp__EnergyPlus-Agent__create_zone` 等工具出现在工具列表。
2. Opus 会话必须严格走 MCP(`list_* → create_*`),不得再落回 `build_yaml.py` 手写 YAML。
3. 标注图必须整图(带外围尺寸链),不得 crop。
4. 所有 LLM/脚本产物必须在 `<case_dir>/output/`,不得散落案例根。
5. Fenestration Table 每行 → 一次 `create_fenestration_surface`,父墙走 §M7 Wall-index 映射。

### 7.5.6 仍未解决 / 下一步
- **EnergyPlus 版本错配**:engine `D:\EnergyPlusV25-2-0\energyplus.exe` 是 25.2.0,仓库 [../data/dependencies/Energy+.idd](../data/dependencies/Energy+.idd) + 生成的 IDF 都是 25.1.0——直接跑会报 IDD mismatch。方案在 [sm_13 run_log §5.2](../test_data/SmallOffice/smalloffice_13/output/run_log.md)(推荐路线 A:升 IDD 回归旧案例)。
- **评测基线**:§8.1 的 Opus 基线脚本(`AI_agent/eval/run_case.py`)仍未启动;sm_13 完成后应先把其纳入 `P0` 的 13+1 案例集合。

---

## 8. 待办（滚动更新）

### 8.1 Next Step（唯一下一步行动）
- [ ] **按 [plan.md](plan.md) P0，写 `AI_agent/eval/run_case.py`，跑 Opus 基线 13 案例并归档到 `AI_agent/eval/reports/<YYYY-MM-DD>_opus_baseline/`**
  - 指标：① claude_ep.md 合规率 ② YAML 生成率 ③ IDF 生成率 ④ EP 仿真完成率 ⑤ zone 数匹配率 + 房间尺寸中位误差 + 走廊 F1 + 特殊 zone F1
  - 产出：`summary.csv`（13 行 × 指标列）+ `per_case/<n>/{trace.jsonl, intake_output.json, decision.md}`

### 8.2 P0 完成后再启
- [ ] 核对 `llm.yaml` 中 `model_name: gpt-5.4` 是否为占位符，统一为可运行的 Claude Opus 模型 ID
- [ ] 按 [plan.md §P1](plan.md) 改写 4 个 skill 为分步 CoT；在 intake 前接入 PaddleOCR + cv2 预处理 hook
- [ ] 部署 Langfuse self-hosted，接 LangChain callback handler
- [ ] 以 Opus 基线产出的 trace 作为 SFT 数据种子（数据量目标 ≥ 500 对，见 [pivot_criteria.md §4.1](pivot_criteria.md)）

### 8.3 Pivot 准入后（阈值达标前冻结）
- [ ] 部署 vLLM + Qwen2.5-VL-7B-Instruct
- [ ] LoRA SFT + holdout 评测，要求领域内达到 Opus 的 80%
- [ ] 切换 `llm.yaml` 默认 provider，全量回归

---

_最后更新：2026-04-21(新增 §7.5 sm_13 首轮会话沉淀;§3.1.2 案例数 13 → 14)_
