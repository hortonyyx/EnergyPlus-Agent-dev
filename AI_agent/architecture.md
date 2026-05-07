# 新架构总览（2026-05-05 起）

> **本文定位**：当前架构的事实参考。源自协作者侧 LangSmith trace 解码（`20260414_192502/` 335 个 run JSON）+ 本仓库 [src/agent/](../src/agent/) 实读 + 2026-05-05 会话澄清。
> **优先级**：本文与 [CLAUDE.md](CLAUDE.md) §1.2 / §6 #9（旧版"产 epJSON"语句）冲突时，**以本文为准**——旧描述被 trace 反证。

---

## 1. 一图看全

```
[文本 + 多模态图像（楼层平面 + 立面图 + 设计意图文本）]
   ↓
intake_node                              ← 我负责
   单次 LLM tool-call → IntakeOutput Pydantic 实例
   字段：building + site_location +
        10 个 *_specs（zone / material / construction / surface /
        fenestration / schedule / lights / people / hvac）
   ↓ state.intake_output 写入共享 AgentState
   ↓
[Phase 1：并行] zone / material / schedule         ← 协作者负责
   ↓
cross_ref_foundations  （命名一致性自动 schema 检查）
   ↓ 错误 → 短路到 validate（带 feedback 回 intake 重试）
   ↓ 通过 →
construction → surface → fenestration            ← 协作者负责
   ↓
[Phase 3：并行] hvac / people / lights             ← 协作者负责
   ↓
cross_ref_complete → validate → simulate → END   ← 协作者负责
```

LangGraph 编译产物见 [src/agent/graph.py:55 build_graph](../src/agent/graph.py#L55)。10 个业务节点 + 通用 ReAct 子节点（`llm` / `tools`）+ 编排节点（`cross_ref_*` / `validate` / `simulate`）。

---

## 2. 节点清单

| 节点 | 类型 | 输入 | 产物 | 谁负责 |
|---|---|---|---|---|
| `intake` | LLM 单次 tool-call | text + images | `IntakeOutput` 写入 state | **本项目** |
| `zone` | ReAct subagent | `intake_output.zone_specs` + 其他 specs (reference) | 一组 Zone 对象 | 协作者 |
| `material` | ReAct subagent | `material_specs` + ref | Material 对象（standard/nomass/airgap/glazing） | 协作者 |
| `schedule` | ReAct subagent | `schedule_specs` + ref | ScheduleTypeLimits + Schedule:Compact | 协作者 |
| `cross_ref_foundations` | 编排节点 | state | 检查 zone × material × schedule 命名一致性 | 协作者 |
| `construction` | ReAct subagent | `construction_specs` + ref | Construction 对象 | 协作者 |
| `surface` | ReAct subagent | `surface_specs` + ref | BuildingSurface:Detailed 对象 | 协作者 |
| `fenestration` | ReAct subagent | `fenestration_specs` + ref | FenestrationSurface:Detailed 对象 | 协作者 |
| `hvac` | ReAct subagent | `hvac_specs` + ref | IdealLoadsAirSystem + Thermostat | 协作者 |
| `people` | ReAct subagent | `people_specs` + ref | People 对象 | 协作者 |
| `lights` | ReAct subagent | `lights_specs` + ref | Lights 对象 | 协作者 |
| `cross_ref_complete` | 编排节点 | state | 全字段交叉引用最终检查 | 协作者 |
| `validate` | 编排 + interrupt | state | 触发人工/自动审批；不通过则 feedback 回 intake | 协作者 |
| `simulate` | 工具节点 | IDF | 调 EnergyPlus 跑仿真 | 协作者 |

每个 subagent 独立 system prompt + 严格隔离的 MCP 工具子集（schedule 只挂 6 个 schedule_*，material 只挂 4 个 create_*_material + list/get/delete，…）。

---

## 3. 数据流：`IntakeOutput` 是核心交接物

`IntakeOutput` 定义在 [src/agent/state.py:23](../src/agent/state.py#L23)，**11 个字段**：

| 字段 | 类型 | 几何依赖 | 谁消费 |
|---|---|---|---|
| `building` | BuildingSchema | 无 | 整图（顶层 Building 对象） |
| `site_location` | SiteLocationSchema | 无（只需城市经纬度） | 整图（Site:Location） |
| `zone_specs` | str | **强**（zone 数 / 楼层 / 邻接） | zone subagent |
| `surface_specs` | str | **强**（每 zone 朝向 / 楼板 / 屋顶） | surface subagent |
| `fenestration_specs` | str | **强**（立面 WWR / 朝向） | fenestration subagent |
| `material_specs` | str | 弱（文本可定） | material subagent |
| `construction_specs` | str | 弱 | construction subagent |
| `schedule_specs` | str | 无 | schedule subagent |
| `lights_specs` | str | 弱（每 zone 功率密度，文本可定） | lights subagent |
| `people_specs` | str | 弱（每 zone 人员密度） | people subagent |
| `hvac_specs` | str | 弱 | hvac subagent |

**前 5 个字段是视觉硬骨头，后 6 个字段从文本可推**——这是我能力主战场的边界。

### 命名一致性约束

每个 `*_specs` 是自然语言段，但 zone / material / construction / schedule **名字必须跨字段精确一致**（[intake.py:60-89 INTAKE_SYSTEM_PROMPT 规则 4-5](../src/agent/nodes/intake.py#L60)）：

- `surface_specs` 提到 zone 名 → 必须在 `zone_specs` 里被定义
- `hvac_specs` / `people_specs` / `lights_specs` 引用 schedule 名 → 必须在 `schedule_specs` 里被定义
- `surface_specs` / `fenestration_specs` 引用 construction 名 → 必须在 `construction_specs` 里被定义
- 名字格式：仅 `[A-Za-z0-9_]`，禁逗号/空格/连字符（IDF 字段分隔符冲突）

`cross_ref_foundations` 和 `cross_ref_complete` 节点会自动检 drift；不通过短路到 `validate` 让你重跑 intake。

### 每个 subagent 看到的 prompt 结构（trace 实证）

```
System: <subagent 专属 prompt — 工具调用规范 + 领域 checklist>
Human:
   --- <Subsystem> specifications (primary task) ---
   <intake 产出的 <subagent>_specs 段>

   --- Downstream specs (reference only; do NOT create non-X here, but USE to infer references) ---
   [hvac_specs] <hvac specs 段>
   [people_specs] ...
   [lights_specs] ...
```

下游 specs 当只读引用 → schedule subagent 必须把 hvac/people/lights 将引用的所有 schedule 都建出来。

---

## 4. 我负责的范围

### 4.1 In-scope

| 模块 | 文件 | 备注 |
|---|---|---|
| **多模态视觉理解**（核心） | [src/agent/nodes/intake.py](../src/agent/nodes/intake.py) | 图像 + 文本 → 11 字段 IntakeOutput |
| **LLM provider 配置** | [src/agent/llm.py](../src/agent/llm.py) + [src/configs/llm.yaml](../src/configs/llm.yaml) | 模型切换唯一入口；待扩 per-subagent 配置（见 §7） |
| **Skill 提示词** | [skills/energyplus_mcp/](../skills/energyplus_mcp/) | 几何 + 开源模型分支 |
| **多模态测试数据 + GT** | [test_data/SmallOffice/smalloffice_*/](../test_data/SmallOffice/) | 图 + testdata_prompt.json + 待建 gt.json |
| **几何阶段 baseline + 评测** | [test_data/test_baseline/](../test_data/test_baseline/) + 待建 [AI_agent/eval/](eval/) | OpenStudio 视察 + 字段级 diff |
| **本地推理后端** | 待建 [AI_agent/deploy/](deploy/) | vLLM / SGLang / Langfuse self-hosted |

### 4.2 Out-of-scope（协作者维护权 ≠ 本地无代码）

> **2026-05-06 修订澄清**：下表 "协作者负责" 指**维护权移交**（prompt 演进 / LangSmith 部署 / token 优化主战场归他们），**不代表本地无实现**。本仓库 [src/agent/nodes/](../src/agent/nodes/) 实际有完整 9 个 subagent + cross_ref + validate + simulate 实现，本地可 in-process 跑全链路（subagent 用 [src/agent/tools/](../src/agent/tools/) 把 MCP 工具函数包成 LangChain tool，不走 MCP server 协议）。[scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 即基于此本地链路自动驱动 DeepSeek V4 pro 跑通下游。

- 9 个领域 subagent 的 system prompt + ReAct 实现（**本地有代码**；2026-05-06 起下游统一走 DeepSeek V4 pro，见 §7.1）
- MCP 工具集（[src/mcp/](../src/mcp/)；idfpy 切换 + 重写中，详见 [idfpy_embed.md](idfpy_embed.md)）
- `cross_ref_*` / `validate` / `simulate` 编排节点（**本地有代码**）
- EnergyPlus engine + 结果解析
- LangSmith 上的部署 / trace 收集（协作者侧独占）

---

## 5. 交接产物

### 5.1 同进程（生产路径，本地完整跑）

`intake_node` 跑完写入 `state.intake_output: IntakeOutput`，下游 9 个 subagent 直接读 `state.intake_output.<own>_specs`。**无文件、无序列化**——LangGraph 内 state 流转。

### 5.2 跨进程（调试 / 给协作者审）

```python
# 把 intake 单独跑一次，落 JSON
intake_state = AgentState(user_input=text, image_paths=[...])
result = intake_node(intake_state)
result.intake_output.model_dump_json(indent=2)
# → 给协作者，他们 IntakeOutput.model_validate_json(...) 还原
```

### 5.3 验收脚本（2026-05-06 已建）

[scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 提供两条路径：

- **Y-auto**：`python scripts/run_full_pipeline.py <case>` — 全自动跑，需 `ANTHROPIC_API_KEY`（intake）+ `DEEPSEEK_API_KEY`（下游）
- **Y-manual**（推荐 / 当前主路径）：`python scripts/run_full_pipeline.py <case> --intake-from output/intake_output.json` — intake 已在独立 Claude Code 会话里人工跑完，脚本短路 `intake_node`（[intake.py:158](../src/agent/nodes/intake.py#L158) 已加 `state.intake_output is not None` 检测），只跑下游 9 subagent + simulate
- **X**（最轻量调试）：`python scripts/run_full_pipeline.py <case> --intake-only` — 仅跑 intake LLM 调用，dump JSON

工作流详细步骤见 [new_case_guide.md](new_case_guide.md)（2026-05-06 重写）。

---

## 6. 验收方式

### 6.1 当前方案：方案 A（OpenStudio 视察）

| 阶段 | 检查 | 工具 |
|---|---|---|
| L1 schema | IntakeOutput 字段齐、类型对、不为空 | Pydantic（自动） |
| L2 跨字段命名 | zone / material / schedule / construction 名跨 specs 一致 | `cross_ref_foundations` + `cross_ref_complete`（自动） |
| L3 几何 | zone 数 / 楼层 / 外包尺寸 / 立面 WWR 与图纸一致 | OpenStudio 人工视察（**方案 A 主战场**） |
| L4 仿真 | EP simulate 完成无 fatal | `simulate_node` |

L3 是当前能力卡点。方案 A 的具体步骤等 [plan.md A3 脚本](plan.md) 写完后落 [new_case_guide.md](new_case_guide.md) §6。

### 6.2 未来：自动化字段级 diff（[plan.md B1-B3](plan.md)）

GT 数据集（B1）+ 评测脚本（B2）+ Anthropic baseline（B3）就位后，能给出：

- zone F1（zone 名集合 IoU）
- 楼层数对错 / 楼层 zone 数误差
- 外包 W×D 尺寸误差（m）
- 立面 WWR 误差（pct）

对应 [pivot_criteria.md](pivot_criteria.md) 视觉层阈值（zone ≥90% / 尺寸 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80）。

### 6.3 验收方式的演化

- **现在**：方案 A（人工 OpenStudio）+ 字段级 diff（待建）
- **idfpy 切换 + 协作者侧 MCP 重写完成后**：重新评估，可能切到 `idf.validate()` + 自动几何 mixin 比对（见 [idfpy_embed.md §4](idfpy_embed.md)）
- **开源模型评测期**：自动化 diff 是 CI 主力；OpenStudio 抽样验证

---

## 7. 已知限制 & 未来调整点

### 7.1 多 section LLM 配置（2026-05-06 已实施，A2 闭环）

[llm.yaml](../src/configs/llm.yaml) 现在多 section：
- `default`：所有 9 个下游 subagent 用，**DeepSeek V4 pro**（OpenAI 兼容协议）
- `intake`：仅 `intake_node` 用，**Claude Opus 4.7**（多模态识图必需）

[create_llm(node_name)](../src/agent/llm.py#L40) 路由：`intake_node` 调 `create_llm(node_name="intake")`；其他节点不传 → 走 `default` → DeepSeek。Old flat 格式仍 back-compat（[llm.py:_load_section()](../src/agent/llm.py)）。

env vars：`DEEPSEEK_API_KEY` + `ANTHROPIC_API_KEY`（[`.env.example`](../.env.example)）。

### 7.2 IntakeOutput schema drift（2026-05-06 已对齐）

本地 11 字段 / BuildingSchema 8 字段 / SiteLocationSchema 5 字段，与协作者 LangSmith trace `20260414_192502/run_00` 解码出的字段集**逐字段一致**，无 drift。详见 [test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/](../test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/) 的 notes.md。

### 7.3 idfpy 替换主线搁置

[idfpy_embed.md](idfpy_embed.md) §3.1 协作者侧 MCP 全线重写 ~1.5-2 周；本项目侧 §3.2（skill / scripts / 数据）等他们交付后再动。

→ 当前不启 §8.1 P1 / `src/mcp_v2/` 工作；优先做识图能力提升（[plan.md B](plan.md)）。

---

## 8. 关联文档

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 项目管理总览 / 决策时间线（§7.12 是本文的精简版） |
| [plan.md](plan.md) | 行动清单（代码跑通 + 识图能力提升） |
| [idfpy_embed.md](idfpy_embed.md) | idfpy 替换主线（**搁置中**，等协作者 MCP 重写） |
| [pivot_criteria.md](pivot_criteria.md) | 闭源 → 开源模型 pivot 阈值（视觉 + 流水线两层） |
| [new_case_guide.md](new_case_guide.md) | 新建 SmallOffice 测试样例的 7 步流程（待按方案 A 调整 §6） |
| [token_optimization.md](token_optimization.md) | Token 优化（已搁置，等 idfpy 切完后重评估） |
| [open_model_guide.md](open_model_guide.md) | 开源模型操作手册（Continue + 预处理 + MCP） |

---

_2026-05-05 首版起草。基于 LangSmith trace 解码 + 与用户 Q&A 澄清；统一旧 CLAUDE.md / plan.md 中"产 epJSON"等过期描述。_
