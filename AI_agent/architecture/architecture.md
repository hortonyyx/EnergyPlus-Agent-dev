# 新架构总览（2026-05-05 起）

> **本文定位**：当前架构的事实参考。源自协作者侧 LangSmith trace 解码（`20260414_192502/` 335 个 run JSON）+ 本仓库 [src/agent/](../../src/agent) 实读 + 2026-05-05 会话澄清。
> **优先级**：本文与 [../CLAUDE.md](../CLAUDE.md) §1.2 / §6 #9（旧版"产 epJSON"语句）冲突时，**以本文为准**——旧描述被 trace 反证。

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

LangGraph 编译产物见 [src/agent/graph.py:55 build_graph](../../src/agent/graph.py#L55)。10 个业务节点 + 通用 ReAct 子节点（`llm` / `tools`）+ 编排节点（`cross_ref_*` / `validate` / `simulate`）。

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

`IntakeOutput` 定义在 [src/agent/state.py:23](../../src/agent/state.py#L23)，**11 个字段**：

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

每个 `*_specs` 是自然语言段，但 zone / material / construction / schedule **名字必须跨字段精确一致**（[intake.py:60-89 INTAKE_SYSTEM_PROMPT 规则 4-5](../../src/agent/nodes/intake.py#L60)）：

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
| **多模态视觉理解**（核心） | [src/agent/nodes/intake.py](../../src/agent/nodes/intake.py) | 图像 + 文本 → 11 字段 IntakeOutput |
| **LLM provider 配置** | [src/agent/llm.py](../../src/agent/llm.py) + [src/configs/llm.yaml](../../src/configs/llm.yaml) | 模型切换唯一入口；待扩 per-subagent 配置（见 §7） |
| **Intake 规则文档库** | [skills/energyplus_mcp/](../../skills/energyplus_mcp) | **2026-05-10 起重新启用** —— 由 [src/agent/nodes/intake.py](../../src/agent/nodes/intake.py) 运行时加载，作为 intake 识图 / 几何 / 输出契约规则库；能力优化会直接改这里 |
| **多模态测试数据 + GT** | [test_data/SmallOffice/smalloffice_*/](../../test_data/SmallOffice) | 图 + testdata_prompt.json + 待建 gt.json |
| **几何阶段 baseline + 评测** | [test_data/test_baseline/](../../test_data/test_baseline) + 待建 [AI_agent/eval/](../eval) | OpenStudio 视察 + 字段级 diff |
| **本地推理后端** | 待建 [AI_agent/deploy/](../deploy) | vLLM / SGLang / Langfuse self-hosted |

### 4.2 Out-of-scope（协作者维护权 ≠ 本地无代码）

> **2026-05-06 修订澄清**：下表 "协作者负责" 指**维护权移交**（prompt 演进 / LangSmith 部署 / token 优化主战场归他们），**不代表本地无实现**。本仓库 [src/agent/nodes/](../../src/agent/nodes) 实际有完整 9 个 subagent + cross_ref + validate + simulate 实现，本地可 in-process 跑全链路（subagent 用 [src/agent/tools/](../../src/agent/tools) 把 MCP 工具函数包成 LangChain tool，不走 MCP server 协议）。[scripts/run_full_pipeline.py](../../scripts/run_full_pipeline.py) 即基于此本地链路自动驱动 DeepSeek V4 pro 跑通下游。

- 9 个领域 subagent 的 system prompt + ReAct 实现（**本地有代码**；2026-05-06 起下游统一走 DeepSeek V4 pro，见 §7.1）
- MCP 工具集（[src/mcp/](../../src/mcp)；idfpy 切换 + 重写中，详见 [../deferred/idfpy_embed.md](../deferred/idfpy_embed.md)）
- `cross_ref_*` / `validate` / `simulate` 编排节点（**本地有代码**）
- EnergyPlus engine + 结果解析
- LangSmith 上的部署 / trace 收集（协作者侧独占）

### 4.3 能力优化作用面边界图（2026-05-07 新增）

> 易混淆：本地仓库里**所有目录都是项目侧的**，但"我能优化什么 vs 等协作者交付什么 vs idfpy 切换时机械同步什么"分得很清。下表面向"我下一步该改哪个文件"。

| 作用面 | 文件 / 目录 | 我能直接改？ | 何时改 | 备注 |
|---|---|---|---|---|
| **🎯 桥接 prompt**（半人工流 Opus 实际执行的） | [new_case_guide.md §4.2](../guides/new_case_guide.md#L130) | ✅ 现在 | 短期主战场 | B4 CoT 拆分先打补丁到这里 |
| **🎯 INTAKE_SYSTEM_PROMPT**（API 自动 intake 的） | [src/agent/nodes/intake.py L34-109](../../src/agent/nodes/intake.py#L34) | ✅ 现在 | 与 §4.2 同步演进，B6 切 API 时生效 |
| **GT 数据集** | `test_data/SmallOffice/<case>/gt.json` | ✅ 现在 | B1 任务（待建） | 没 GT 就没 B2 评测 |
| **diff 评测脚本** | `AI_agent/eval/intake_diff.py` | ✅ 现在 | B2 任务（待建） |
| **OCR / cv2 预处理 hook** | `Tool_scripts/preprocess_floor_plan.py` | ✅ B5 任务（待建） | 给 Opus 做 hint 注入，不动 graph |
| **测试输入素材** | [test_data/SmallOffice/<case>/](../../test_data/SmallOffice) | ✅ 现在 | 新案例直接 Step 1-3 起 |
| **下游 9 subagent prompt** | [src/agent/nodes/{material,zone,surface,...}.py](../../src/agent/nodes) | ⚠️ 改但属维护 | bug 修补可改（如 B0' surface T-vertex），prompt 演进归协作者 | idfpy 切换时**必随之改** |
| **下游 LangChain tool 包装层** | [src/agent/tools/*_tools.py](../../src/agent/tools) | ⚠️ 改但属维护 | 紧贴 MCP 工具签名 | idfpy 切换时**必随之改**（工具数 79→20-25） |
| **MCP 工具实现** | [src/mcp/tools/](../../src/mcp/tools) + [src/mcp/api/](../../src/mcp/api) | ❌ 等协作者交付 | idfpy 切换主体，~1.5-2 周 | 协作者主导 |
| **converters / validator** | [src/converters/](../../src/converters) + [src/validator/data_model.py](../../src/validator/data_model.py) | ❌ 等协作者交付 | idfpy 切换时整体删 / idf.validate() 顶替 |
| **Intake 规则文档库** | [skills/energyplus_mcp/](../../skills/energyplus_mcp) | ✅ 现在 | 与 intake prompt 同步演进 | 由 [src/agent/nodes/intake.py](../../src/agent/nodes/intake.py) 运行时拼接加载；当前能力恢复主战场之一 |
| **EP engine / LangSmith** | — | ❌ 协作者侧 | — |

**判断规则**：

1. 看到任务在 `图 → IntakeOutput JSON` 这一段 → 落在前 6 行（🎯 / ✅），**当下就动**
2. 看到任务在下游 subagent 出错（如 sm_16_newarch 的 surface T-vertex bug）→ 中间 2 行（⚠️），**改但要意识到 idfpy 切换时还会再改一遍**，写补丁前评估"短期忍 + 等切换时统一处理"vs"立即修"
3. 看到任务在 MCP 工具 / converter / validator → ❌，等协作者，写 issue 不动手
4. 看到 `skills/energyplus_mcp/` → 这是 **intake 规则文档库**，属于当前能力恢复主战场，可直接改；仅旧 `open_model/` / `export_idf` 流程已废弃

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

[scripts/run_full_pipeline.py](../../scripts/run_full_pipeline.py) 提供两条路径：

- **Y-auto**：`python scripts/run_full_pipeline.py <case>` — 全自动跑，需 `ANTHROPIC_API_KEY`（intake）+ `DEEPSEEK_API_KEY`（下游）
- **Y-manual**（推荐 / 当前主路径）：`python scripts/run_full_pipeline.py <case> --intake-from output/intake_output.json` — intake 已在独立 Claude Code 会话里人工跑完，脚本短路 `intake_node`（[intake.py:158](../../src/agent/nodes/intake.py#L158) 已加 `state.intake_output is not None` 检测），只跑下游 9 subagent + simulate
- **X**（最轻量调试）：`python scripts/run_full_pipeline.py <case> --intake-only` — 仅跑 intake LLM 调用，dump JSON

工作流详细步骤见 [../guides/new_case_guide.md](../guides/new_case_guide.md)（2026-05-06 重写）。

---

## 6. 验收方式

### 6.1 当前方案：方案 A（OpenStudio 视察）

| 阶段 | 检查 | 工具 |
|---|---|---|
| L1 schema | IntakeOutput 字段齐、类型对、不为空 | Pydantic（自动） |
| L2 跨字段命名 | zone / material / schedule / construction 名跨 specs 一致 | `cross_ref_foundations` + `cross_ref_complete`（自动） |
| L3 几何 | zone 数 / 楼层 / 外包尺寸 / 立面 WWR 与图纸一致 | OpenStudio 人工视察（**方案 A 主战场**） |
| L4 仿真 | EP simulate 完成无 fatal | `simulate_node` |

L3 是当前能力卡点。方案 A 的具体步骤等 [plan.md A3 脚本](../plan.md) 写完后落 [../guides/new_case_guide.md](../guides/new_case_guide.md) §6。

### 6.2 未来：自动化字段级 diff（[plan.md B1-B3](../plan.md)）

GT 数据集（B1）+ 评测脚本（B2）+ Anthropic baseline（B3）就位后，能给出：

- zone F1（zone 名集合 IoU）
- 楼层数对错 / 楼层 zone 数误差
- 外包 W×D 尺寸误差（m）
- 立面 WWR 误差（pct）

对应 [../reference/pivot_criteria.md](../reference/pivot_criteria.md) 视觉层阈值（zone ≥90% / 尺寸 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80）。

### 6.3 验收方式的演化

- **现在**：方案 A（人工 OpenStudio）+ 字段级 diff（待建）
- **idfpy 切换 + 协作者侧 MCP 重写完成后**：重新评估，可能切到 `idf.validate()` + 自动几何 mixin 比对（见 [idfpy_embed.md §4](../deferred/idfpy_embed.md)）
- **开源模型评测期**：自动化 diff 是 CI 主力；OpenStudio 抽样验证

---

## 7. 已知限制 & 未来调整点

### 7.1 多 section LLM 配置（2026-05-06 已实施，A2 闭环）

[llm.yaml](../../src/configs/llm.yaml) 现在多 section：
- `default`：所有 9 个下游 subagent 用，**DeepSeek V4 pro**（OpenAI 兼容协议）
- `intake`：仅 `intake_node` 用，**Claude Opus 4.7**（多模态识图必需）

[create_llm(node_name)](../../src/agent/llm.py#L40) 路由：`intake_node` 调 `create_llm(node_name="intake")`；其他节点不传 → 走 `default` → DeepSeek。Old flat 格式仍 back-compat（[llm.py:_load_section()](../../src/agent/llm.py)）。

env vars：`DEEPSEEK_API_KEY` + `ANTHROPIC_API_KEY`（[`.env.example`](../../.env.example)）。

### 7.2 IntakeOutput schema drift（2026-05-06 已对齐）

本地 11 字段 / BuildingSchema 8 字段 / SiteLocationSchema 5 字段，与协作者 LangSmith trace `20260414_192502/run_00` 解码出的字段集**逐字段一致**，无 drift。详见 [test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/](../../test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake) 的 notes.md。

### 7.3 idfpy 替换主线搁置

[../deferred/idfpy_embed.md](../deferred/idfpy_embed.md) §3.1 协作者侧 MCP 全线重写 ~1.5-2 周；本项目侧 §3.2（skill / scripts / 数据）等他们交付后再动。

→ 当前不启 §8.1 P1 / `src/mcp_v2/` 工作；优先做识图能力提升（[plan.md B](../plan.md)）。

---

## 8. 新人快速上手 QA（2026-05-07 新增）

> 来源：2026-05-07 sm_16_newarch 首跑后用户提的 5 个结构性问题。常见误解直接答清。

### Q1：旧 [skills/energyplus_mcp/](../../skills/energyplus_mcp) 还需要吗？

**需要，但角色已变化。** 旧流程里它是 Opus 单会话驱动 MCP 几何 / MEP 建模的主 skill；当前新流程里它不再承担 MCP tool-calling 工作流，而是被 [src/agent/nodes/intake.py](../../src/agent/nodes/intake.py#L34) 运行时加载为 **intake 规则文档库**，用于约束图 → IntakeOutput 的识图、几何推导、拓扑和输出契约。能力恢复与升级（B1-B7）会直接改这里；旧的 `open_model/`、`export_idf` 等分支已废弃或移出当前主路径。

### Q2：下游 subagent 的 prompt 和 schema 在哪？已经写好了吗？

**是的，已写好且固化**。每个 subagent = 一个 Python 文件 + 硬编码 system prompt + 一组工具：

| 实体 | 位置 |
|---|---|
| 9 个 subagent system prompt | [src/agent/nodes/{material,zone,schedule,construction,surface,fenestration,hvac,people,lights}.py](../../src/agent/nodes) `*_SYSTEM_PROMPT` 常量 |
| 9 套 LangChain tool 包装层 | [src/agent/tools/*_tools.py](../../src/agent/tools) `make_*_tools(ConfigState) -> list[BaseTool]` |
| MCP 工具实现（被 wrap 的对象） | [src/mcp/tools/](../../src/mcp/tools) |
| 拓扑编排 | [src/agent/graph.py:55 build_graph](../../src/agent/graph.py#L55) |

**契约**：`intake_node` 把 IntakeOutput 装进 `state.intake_output`；每个 subagent 读 `state.intake_output.{name}_specs`（自然语言段，str），跑 ReAct 直到完成。

### Q3：现在架构相当于把旧 skill 拆给 subagent？

**大体对，但不是 1:1 切片**：

1. 粒度变细 + 模型换人：旧 skill 是给 Opus 一份"通才说明书"；新 prompt 是给 DeepSeek 一份"专才说明书"，因此重写。
2. 横切关注点上移：旧 skill 的"输入格式 / 共享外包硬约束 / 后处理补丁"等抽到 [intake.py INTAKE_SYSTEM_PROMPT](../../src/agent/nodes/intake.py#L34) 和 [cross_ref 自动节点](../../src/agent/nodes/cross_ref.py)，subagent 拿到的已是清洗过的局部任务。

### Q4：为什么全流程没调 MCP server 了？

**MCP 协议层没了，MCP 工具实现还在用**。区别：

| | 旧 | 新 |
|---|---|---|
| 工具调用通路 | stdio JSON-RPC → [src/mcp/server.py](../../src/mcp/server.py) → tool 实现 | `@tool` 包装（[src/agent/tools/](../../src/agent/tools)）→ **直接 Python 调用** [src/mcp/tools/](../../src/mcp/tools) 同一份实现类 |

证据：[material_tools.py](../../src/agent/tools/material_tools.py) 第 4 行 `from src.mcp.tools.material import MaterialTool` —— 仍是同一个类，只是不通过 MCP 协议而是 in-process 调用。**好处**：①免启动 server ②无 IPC round-trip ③9 个 subagent 共享同一 `ConfigState` 实例 ④LangGraph checkpoint 直接 pickle Python 对象。

### Q5：idfpy 切换对项目 / 我侧的影响？

**协作者主导改 [src/mcp/](../../src/mcp) 实现层；我侧主导改 wrap + prompt + 测试**。具体见 §4.3 边界图。**最值钱的设计**：IntakeOutput Pydantic 契约**完全不受 idfpy 切换影响**——你的 Opus 半人工 intake 流照旧。**意外收益**：[B0' surface T-vertex bug](../plan.md) 大概率自动消失（`validate_geometry_closure` 这个超严格本地校验被 idfpy 的 `idf.validate()` 真实 IDD 检查替代；EnergyPlus 本身只要 boundary object 配对，不要每顶点 ≥3 共享）。

### Q6：能力优化的主作用对象到底是什么？

见 §4.3 表头 **🎯** 标记的两行：

1. **半人工流当前**：[new_case_guide.md §4.2](../guides/new_case_guide.md#L130) 桥接 prompt（用户贴给 Opus 那段）
2. **B6 API 自动 intake 后**：[INTAKE_SYSTEM_PROMPT](../../src/agent/nodes/intake.py#L34) L34-109

外加 GT 集（B1）、diff 评测（B2）、OCR 预处理（B5）等基础设施。**所有不在这 4 处的代码改动都不属于能力优化主战场**。

---

## 9. 关联文档

| 文档 | 作用 |
|---|---|
| [../CLAUDE.md](../CLAUDE.md) | 项目管理总览 / 决策时间线（§7.12 是本文的精简版） |
| [../plan.md](../plan.md) | 行动清单（代码跑通 + 识图能力提升） |
| [../deferred/idfpy_embed.md](../deferred/idfpy_embed.md) | idfpy 替换主线（**搁置中**，等协作者 MCP 重写） |
| [../reference/pivot_criteria.md](../reference/pivot_criteria.md) | 闭源 → 开源模型 pivot 阈值（视觉 + 流水线两层） |
| [../guides/new_case_guide.md](../guides/new_case_guide.md) | 新建 SmallOffice 测试样例的 7 步流程（待按方案 A 调整 §6） |
| [../deferred/token_optimization.md](../deferred/token_optimization.md) | Token 优化（已搁置，等 idfpy 切完后重评估） |
| [../reference/open_model_guide.md](../reference/open_model_guide.md) | 开源模型操作手册（Continue + 预处理 + MCP） |

---

_2026-05-10 — `skills/energyplus_mcp/` 从“死代码”改判为运行时 intake 规则文档库：由 [intake.py](../../src/agent/nodes/intake.py) 自动加载，承担图→IntakeOutput 的识图 / 几何 / 拓扑 / 输出契约约束。旧 `open_model/` 与 `export_idf` 分支不再位于当前主路径；相关开源模型流程改为引用 `Skill_history/` 历史备份。_

_2026-05-07 增补：§4.1 标注 skills/ 为死代码；新增 §4.3 能力优化作用面边界图（11 行 + 4 条判断规则，区分 🎯/✅/⚠️/❌ 四档）；新增 §8 新人快速上手 QA（Q1-Q6，源自 sm_16_newarch 首跑后澄清）。原 §8 关联文档下移为 §9。_

_2026-05-05 首版起草。基于 LangSmith trace 解码 + 与用户 Q&A 澄清；统一旧 CLAUDE.md / plan.md 中"产 epJSON"等过期描述。_
