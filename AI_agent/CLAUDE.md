# 多模态输入 Agent 项目管理文档

> 项目管理上下文，主要供 LLM 会话首加载读取。详细架构见 [architecture.md](architecture.md)；标准工作流见 [new_case_guide.md](new_case_guide.md)；行动清单见 [plan.md](plan.md)。

---

## 1. 项目总览

### 1.1 仓库 / 目标
- 根目录：[../](../)；项目说明：[../README.md](../README.md)
- 目标：建筑设计意图（YAML / 自然语言 / 建筑图纸）→ 合法 EnergyPlus IDF + 仿真完成

### 1.2 当前架构（2026-05-06 起：半人工 intake + 自动下游）

```
[图像 + 文本输入]
   ↓
[本项目侧] 半人工 intake（Claude Opus 4.7 订阅会话；多模态识图）
   ↓ 落盘 IntakeOutput Pydantic JSON
   ↓
[本项目侧] 自动下游（DeepSeek V4 pro × 9 subagent，本地 in-process LangGraph）
   ↓
   YAML / IDF / EnergyPlus simulate 完成
```

- **intake**：[../src/agent/nodes/intake.py](../src/agent/nodes/intake.py)；多模态识图主战场
- **下游 9 subagent + simulate**：[../scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) `--intake-from output/intake_output.json` 调 [../src/agent/graph.py](../src/agent/graph.py) 自动跑
- **协作者侧 LangSmith**：trace `20260414_192502/` 是本地 graph 的镜像 / 演化版（[§5.2](#52-协作者侧-langsmith-trace-20260414_192502-2026-05-05)），他们维护 prompt 演进，本项目本地有完整可独立跑代码
- **完整工作流**：[new_case_guide.md](new_case_guide.md)（2026-05-06 重写）

### 1.3 关键路径

| 路径 | 作用 |
|---|---|
| [../src/agent/](../src/agent/) | 14 节点 LangGraph（intake → 9 subagent → cross_ref → validate → simulate）|
| [../src/agent/nodes/intake.py](../src/agent/nodes/intake.py) | INTAKE_SYSTEM_PROMPT + intake_node（含 `--intake-from` short-circuit）|
| [../src/agent/llm.py](../src/agent/llm.py) + [../src/configs/llm.yaml](../src/configs/llm.yaml) | LLM 工厂 + 多 section（intake=Anthropic / default=DeepSeek）|
| [../src/mcp/](../src/mcp/) | MCP 工具集（idfpy 替换主线搁置中，[idfpy_embed.md](idfpy_embed.md)）|
| [../scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) | 端到端 / 半人工 / 仅 intake 三种入口 |
| [../test_data/SmallOffice/](../test_data/SmallOffice/) | 案例（sm_0..17）|
| [../test_data/test_baseline/runs/](../test_data/test_baseline/runs/) | baseline + capability 实验日志归档（2026-05-06 起）|
| [../tests/test_zone_agent.py](../tests/test_zone_agent.py) | 唯一自动化测试（zone_agent 纯文本）|
| `D:\EnergyPlusV25-2-0\energyplus.exe` | EnergyPlus 引擎本地位置（v25.2.0）。runner.py 解析顺序: `$ENERGYPLUS_EXE` env → PATH → 硬编码默认（同此路径）。已写进 [`.env`](../.env)。本机不会改动。 |
| [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw) | 默认 EPW 气象文件 |

### 1.4 技术栈
LangGraph + LangChain（`init_chat_model("{provider}:{model_name}")` 路由）；多模态走 `HumanMessage.content` base64 图块；结构化输出 `with_structured_output(IntakeOutput, include_raw=True)` 依赖 tool-calling；EnergyPlus engine 通过 `WorkflowTool.run_simulation`（eppy + ConverterManager 路径，idfpy 切换搁置）。

---

## 2. 责任范围

### 2.1 In-scope
1. `intake_node` 多模态理解（图 + 文本 → IntakeOutput Pydantic JSON）— **核心战场**
2. [../src/agent/llm.py](../src/agent/llm.py) provider 抽象与开源模型接入
3. Skill 提示词演进（`../skills/energyplus_mcp/`，几何阶段拆分版）
4. 多模态测试数据集 + baseline + 评测
5. 本地推理后端（vLLM / SGLang，等 Pivot 准入）

### 2.2 Out-of-scope（协作者维护权 ≠ 本地无代码）
- **下游 9 subagent + cross_ref + validate + simulate 的 prompt 演进**（本地有完整代码可跑；协作者负责 prompt 优化 + LangSmith 部署）
- MCP 工具基于 idfpy 的全线重写（[idfpy_embed.md §3.1](idfpy_embed.md)，搁置中）
- LangSmith 上的多步 agent 编排
- RAG 知识库

---

## 3. 关键洞察（仍有效）

1. **视觉理解非首要瓶颈**（13 案例 12/13 出 claude_ep.md = 92% 通过）
2. 真正瓶颈：**长链路 tool-calling 稳定性 + 子系统覆盖完整性**（旧基线 Schedule/Lights/HVAC 普遍缺失；新流程下交给 cross_ref + validate 兜底）
3. **强制后处理补丁**不能交给 LLM 记得打 → [Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py) 5 条补丁脚本化；idfpy 切换后大部分由 `idf.validate()` 顶替
4. **token 口径**：`/context` 真值才作准；deferred MCP / autocompact / system tools deferred 都不计入 Total（[memory project_context_token_accounting.md](../memory/project_context_token_accounting.md)）

---

## 4. 标准工作流（详见 [new_case_guide.md](new_case_guide.md)）

```
Step 1-3  素材 / 目录 / testdata_prompt.json（schema A：Floor plans 数组 + 共享外包硬约束）
Step 4    半人工 intake（Claude Code 会话 + Opus）→ <case>/output/intake_output.json
Step 5    python scripts/run_full_pipeline.py <case> --intake-from output/intake_output.json
Step 6    L1 Pydantic / L2 cross_ref / L3 OpenStudio / L4 EP completion 四层验收
Step 7    用户说"记录这次跑 <case> <tag>" → 落 test_data/test_baseline/runs/
```

---

## 5. 关键决策（精简版）

> 历史细节（sm_0..16 baseline / token 优化 P0 全过程 / Claude Code harness 切换 / sm_13/14/15/16 输入规格演进）已沉淀在各专题文档 + `test_baseline/runs/` 各 baseline 目录 + git log。本节只保留**对当前架构仍有约束力**的决策。

### 5.1 几何 / MEP 阶段拆分（2026-04-25, sm_15）
IDF 建模拆「几何阶段」+「MEP 阶段」，独立会话可由不同模型执行；占位 construction：`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`。**全局唯一世界坐标系**：原点 = 整栋投影最大边界 SW 内角，禁止每层本地原点。

### 5.2 协作者侧 LangSmith trace 解码（2026-05-05）
`20260414_192502/` 共 335 个 run JSON。锁定 10 节点 LangGraph 拓扑（intake → schedule → material → construction → zone → surface → fenestration → lights → people → hvac）+ 子 ReAct 节点。每个 subagent 输入合同：「主任务 specs + 下游 specs（reference only）」。本项目侧职责真正边界 = **产 IntakeOutput Pydantic（不产 epJSON）**。

### 5.3 半人工工作流固化 + A2 多 LLM 配置（2026-05-06）

**A. IntakeOutput schema drift 验证 PASS**
- 协作者 trace 与本地 [state.py:23](../src/agent/state.py#L23) + [validator/data_model.py BuildingSchema/SiteLocationSchema](../src/validator/data_model.py) 逐字段对账：top-level 11 字段 / BuildingSchema 8 字段 / SiteLocationSchema 5 字段，**全部一致**

**B. DeepSeek V4 pro 文本通路 capability test PASS**
- HARD_USER_INPUT（5 层办公楼 + 中庭，1953 字符）→ 49k completion / 11 字段齐 / Pydantic PASS / 0 命名违规 / 跨字段引用 100% 一致
- 软风险：DeepSeek 用 `Floor_N_*` 模板写法（协作者是逐个枚举）→ 已在 [new_case_guide.md §4.2](new_case_guide.md) Step 4 prompt 加硬约束补丁
- artifacts：[../test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/](../test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/)

**C. A2 多 section LLM 配置已实施**
- [llm.yaml](../src/configs/llm.yaml) 拆 `default`（DeepSeek V4 pro）+ `intake`（Claude Opus 4.7）
- [llm.py:create_llm(node_name)](../src/agent/llm.py) 路由；back-compat 旧 flat 格式
- [intake.py:158](../src/agent/nodes/intake.py#L158) 加 short-circuit（`state.intake_output is not None` → 跳 LLM 调用）让 `--intake-from` 半人工流可用
- env vars：`DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY`（[`.env.example`](../.env.example)）

**D. 半人工工作流固化**
- [new_case_guide.md](new_case_guide.md) 重写（旧版备份 [backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06)）
- [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 三种入口（`<case>` 全自动 / `--intake-from` 半人工 / `--intake-only` 调试）

**E. 实验日志归档目录迁移**
- 旧 `AI_agent/experiments/` 全空已废
- 一律落 [../test_data/test_baseline/runs/](../test_data/test_baseline/runs/)
- 命名：建模 baseline `<YYYY-MM-DD>_<case>_<tag>/`；capability test `<YYYY-MM-DD>_capability_<topic>/`

### 5.4 simulate 全链路通验证 + 真因定位（2026-05-07 晚）

**A. 真跑 EP 实证**：把 sm_16_newarch IDF 直接喂 EnergyPlus 25.2.0
- T-vertex **不卡 EP**：warm-up 无任何几何相关 severe → [plan.md B0'](plan.md) 关闭
- 真 fatal：window 求解器在 `F1_NORTH_W_WINDOW` 收敛失败（4 个 glazing face 温度全 NaN）
- Root cause：fenestration_agent 把 `WindowMaterial:SimpleGlazingSystem` 当作一层玻璃片，组成 玻璃→空气→玻璃 三明治 Construction（EP IDD 硬约束：SimpleGlazing 必须 standalone）
- 手工把 `Window_Double_Glazing` Construction 改成单层引用 SimpleGlazing 后 EP `Completed Successfully` / 0 severe / 9 warnings / 14.8 秒（artifacts [`smalloffice_16_newarch/output/ep_run_glazingfix/`](../test_data/SmallOffice/smalloffice_16_newarch/output/ep_run_glazingfix/)）

**B. 架构结论**：✅ 半人工 intake → 自动下游 → IDF → EnergyPlus 全链路机制 100% 通；零架构层 bug。所有剩余问题都是单一 subagent prompt 级建模质量

**C. 决策：不调 fenestration / construction prompt**
- 理由：idfpy 自带 schema 校验，切换后会原生拒绝该组合；短期 prompt 修属重复投资
- 主线焦点切到**几何正确性**（[plan.md B1/B2/B3](plan.md)），simulate 跑通暂不作短期目标

**D. validator 临时放宽永久化**：[src/validator/data_model.py](../src/validator/data_model.py) `validate_geometry_closure` 保持 `logger.warning`，不恢复 raise；待 idfpy 切换时整体删

### 5.5 B1 阶段闭环 + surface_agent z_floor hotfix（2026-05-12）

**A. B1 整体迁移交付**（[plan.md §B1](plan.md)）
- 3 个 skill 文档库（[`energyplus_mcp_prompt.md`](../skills/energyplus_mcp/energyplus_mcp_prompt.md) / [`intake_output_contract.md`](../skills/energyplus_mcp/intake_output_contract.md) / [`zonetool_prompt.md`](../skills/energyplus_mcp/zonetool_prompt.md)）按 [`energyplus_mcp_migration_audit_2026-05-11.md`](energyplus_mcp_migration_audit_2026-05-11.md) 4 个 Gap 全部补硬约束
- 关键补强：per-floor window chain hard rule（Gap A）/ cross-floor split-pairing required enumeration（Gap B/D，直接挡 `RoofCeiling references not-found` fatal）/ fenestration absolute-world-z primary + per-window self-check（Gap D，但下面 B 揭示这还不够）/ unsupported-case 双标统一（Gap C）/ fenestration chain N-window 通式 + 反例（针对 sm_20 暴露的 top_gap 混淆 slip）
- 旧 vertex synthesis 表恢复回 [`zonetool_prompt.md`](../skills/energyplus_mcp/zonetool_prompt.md)
- artifacts：sm_18（deepseek 起稿，EP fatal anchor）/ sm_19（codex 起稿，10 CHKSBS warning anchor）/ sm_20 output（B1 only，10 CHKSBS）/ sm_20 output_new（B1 + surface fix，0 CHKSBS）

**B. surface_agent z_floor hotfix**（[downstream_agent_changes.md](downstream_agent_changes.md) 2026-05-12 条）
- 真因：[`src/agent/nodes/surface.py`](../src/agent/nodes/surface.py) 的 `SURFACE_SYSTEM_PROMPT` 只收 `surface_specs`、看不到 `zone_specs`，且 prompt 没指引读 `z_floor / ceiling_height` → DeepSeek 默认按 3 m 层高建墙 → 上层窗 z 落在墙外 CHKSBS partial-overlap
- 修复：(a) 同时传 `zone_specs + surface_specs` 两段；(b) 加 "per-floor z values come from zone_specs" 硬指引；(c) worked example 改为 F2_S1 (`z_floor=3.60, h=3.60`)
- 备份：[src_history/2026-05-12_surface_agent_zfloor_fix/](../src_history/2026-05-12_surface_agent_zfloor_fix/)
- 验证：sm_20 output_new EP `Completed Successfully` / 0 severe / 14 warning（全无害）/ F2 wall z=[3.60,7.20] / 窗 z=[4.60,6.40] 严格落在墙内

**C. 架构通透性新基准**：sm_20 取代 sm_16_newarch 成为"全链路真跑 cleanly 通"的新 anchor（sm_16_newarch 要手工修一行 Construction，sm_20 一把过）。

**D. 残留**：intake 对 East/West F3 corridor 窗有偶发 `z_max = z_min + top_gap` 计算 slip（写成 9.60 应为 10.60）—— 已在 [`intake_output_contract.md`](../skills/energyplus_mcp/intake_output_contract.md) `fenestration_specs > Right-side chain pattern (general)` 加 N 窗通式 + 反例 + 自检规则，下次跑新 case 应被挡住；sm_20 落盘的错值保留作 audit anchor，未手工修。

**E. 工程改动**
- [src/mcp/tools/workflow.py](../src/mcp/tools/workflow.py)：显式传 `output_directory` 给 `runner.run_idf`，EP 产物现在落 `<case>/output/` 而不是全局 `output/results/`（commit `1a817e0`）
- [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py)：加 `--output-subdir` flag 方便同 case 多版对照（sm_20 跑了 `output/` 和 `output_new/` 两版）

### 5.6 两步法 intake POC PASS + B1.5 立项最高优先级（2026-05-12 晚）

**A. POC 验证结果**（sm_20 全套两步法，详见 [floorplan_redraw_strategy.md §9](floorplan_redraw_strategy.md)）

- **Phase 1**（识图）：Claude Code 会话 + Opus 4.7，7 张图 → 7 份矢量 JSON + summary。schema = strokes[] + pen 类型（wall / wall_fill / window / outline / other），含 plan / elevation 词典分拆 + 4 立面 facade_axis_note 含符号
- **Phase 2**（拓扑）：双路径对比
  - Opus 路径（Claude Code 会话直写）
  - DeepSeek 路径（[`Tool_scripts/run_phase2_deepseek.py`](../Tool_scripts/run_phase2_deepseek.py)，绕过 langchain、thinking enabled、max_tokens=64k、`_fix_js_concat` regex 修 JS 风格字符串拼接、`ensure_schema_initialized()` 初始化 IDD）
- **Step 6 全链路**：Opus 路径 + 下游 9 subagent + EP fatal（construction asymmetry 规则漏洞，phase2_rules v1.3 已修）；**DeepSeek 路径 EP cleanly Completed**（0 severe / 9 warning / 8.49s 全年）
- **F3 corridor 窗 z 修正**：两步法两条路径都对（z=10.60）/ anchor 单步法错（z=9.60）—— phase1 锁定识图结果让 phase2 无机会重做坐标推导，误差预算分离生效

**B. 决策**：**两步法立为新主线**。B1.5 提升为最高优先级（[plan.md B1.5](plan.md)）。B2-B4 评测基线规范化并行推进但必须从一开始就支持矢量 JSON 中间层。

**C. Artifacts 迁移**
- 测试 case：[`test_data/SmallOffice_TwoStep/smalloffice_20/`](../test_data/SmallOffice_TwoStep/smalloffice_20/)（与 `SmallOffice/smalloffice_20/` 同素材，两步法跑）
- Skill 演进源：[`skills/energyplus_mcp_twostep/`](../skills/energyplus_mcp_twostep/)（`phase1_vector_schema.md` v1.2 + `phase2_rules.md` v1.3 + 两个 prompt 模板 + README）
- DeepSeek 自动跑批脚本：[`Tool_scripts/run_phase2_deepseek.py`](../Tool_scripts/run_phase2_deepseek.py)
- SVG 渲染（phase1 人工校验工具）：[`Tool_scripts/render_vector_to_svg.py`](../Tool_scripts/render_vector_to_svg.py)
- 三方对比详表：[`test_data/SmallOffice_TwoStep/smalloffice_20/compare/diff.md`](../test_data/SmallOffice_TwoStep/smalloffice_20/compare/diff.md)

**D. 后续主线动作**（[plan.md B1.5](plan.md)）
- B1.5.a 异图 POC v2（噪声 / 装饰 / 索引 / 楼梯）
- B1.5.b phase2_rules.md / phase1_vector_schema.md 持续迭代（吸收 Opus 10 条 followup notes）
- B1.5.c `intake_node` 重写为两步串行调用（保留 `--intake-from` short-circuit）
- B1.5.d `Tool_scripts/run_phase2_deepseek.py` 迁入主线作 phase2_node
- B1.5.e [`new_case_guide.md`](new_case_guide.md) Step 4 拆 4a phase1 / 4b phase2
- B1.5.f 评测脚本支持识图错 ↔ 推理错自动归因

---

## 6. 协作者 / 助手约定

1. **模型切换入口唯一**：[llm.yaml](../src/configs/llm.yaml) + [llm.py](../src/agent/llm.py)；不在节点内硬编码
2. **多模态改动只改 intake**：不绕过 `intake_node` 把图像直接塞下游
3. **每次 prompt / 模型变更**：在 [test_baseline/runs/](../test_data/test_baseline/runs/) 新建 capability run 记录（模型 ID / prompt hash / 评测结果 / 失败样本）
4. **回归门槛**：切默认 provider 前，端到端跑通率不得低于 Anthropic 基线 80%
5. **Skill / MCP / 下游 subagent 改动备份**：
   - 动 `../skills/` 或 `../src/mcp/` 前先 `cp -r` 到 `Skill_history/<YYYY-MM-DD>_<reason>/` 或 `MCP_history/<YYYY-MM-DD>_<reason>/`（同日多次加 `_v2` / `_pre_X`）
   - 动 `../src/` 下任何下游 subagent 代码（`agent/nodes/*.py` / `agent/tools/*` / 其他下游 prompt 装配点）前先 `cp` 到 `src_history/<YYYY-MM-DD>_<reason>/<file>.py`，并在 [downstream_agent_changes.md](downstream_agent_changes.md) 加一条改动记录 + 跟协作者交接清单
   - `Skill_history/` / `src_history/` / `MCP_history/` 都被 `.gitignore` 排除——这些是本地 audit / 回退用
6. **Baseline 记录触发**：用户说 `记录这次跑 <case> <tag>` → 严格按 [test_baseline/README.md §4.3](../test_data/test_baseline/README.md) 执行（先 `Tool_scripts/baseline_record.py <case> <tag>` 起骨架，用户粘 `/context` 到 `context.txt`，助手填非用户字段，**不替用户填 `dimensions_check`**）
7. **本项目交接产物 = IntakeOutput JSON**（2026-05-06 起）：本项目侧职责到 [IntakeOutput Pydantic](../src/agent/state.py#L23)；下游走 [run_full_pipeline.py](../scripts/run_full_pipeline.py) 自动跑产 IDF + 仿真。与此对应，`../skills/energyplus_mcp/` 现为 intake 规则文档库，由 [src/agent/nodes/intake.py](../src/agent/nodes/intake.py) 运行时加载，不再是旧 MCP 主 skill。
8. **idfpy 替换搁置**（[idfpy_embed.md](idfpy_embed.md) §3.1 协作者侧 MCP 重写未交付）：本项目侧 P1/P2 动作冻结
9. **git 权限下放**：助手可在重要节点（跑通新案例 / skill / MCP / prompt 重大重写完成 / 阶段性里程碑）自行 `git add` + `commit`；commit message 仿仓库风格（`<月.日>_<英文标签>`，如 `5.6_HalfmanualWorkflow`），body 必须含①改动核心 ②为何此刻是节点 ③影响范围。**禁**：`git push`（除非用户明确要求）/ force push / `reset --hard` / 跳 hook / 动 `git config`
10. **Step 5 对话触发协议**（2026-05-07 起）：用户说 "跑下游 <case>" / "Step 5 <case>" → 助手依次①L1 Pydantic 校验 `<case>/output/intake_output.json` ②echo `llm.yaml` `default` section 关键字段（含 `extra_body.thinking`）③`y/n` 确认 ④后台启动 `run_full_pipeline.py` 并 tee log。详见 [new_case_guide.md §5.0](new_case_guide.md)
11. **DeepSeek v4-pro thinking 模式默认关闭**（2026-05-07 起）：根因 = langchain_openai 不会回传 `reasoning_content`，多轮 tool-calling 必踩 400。[llm.yaml](../src/configs/llm.yaml) `default.extra_body.thinking.type=disabled`。何时升级见 [new_case_guide.md §5.0.1](new_case_guide.md)
12. **DeepSeek bridge MCP 协作约定**：用户本地有 `deepseek-bridge` MCP，可连 DeepSeek API。若当前会话工具视图中可调用该 MCP，助手可把简单、边界清晰、文本型的非阻塞任务派给 DeepSeek 以节省 token / 额度；架构决策、仓库编辑、最终集成和验证仍由 主模型 负责。若 MCP 显示启用但工具视图不可见，先向用户说明当前会话无法直接调用，而不是臆造调用结果。
13. **开发环境统一走 VS Code Dev Container**（2026-05-19 起，[../.devcontainer/README.md](../.devcontainer/README.md)）：Win / Mac / 云端共用同一 Linux 容器，代码 / 终端 / EnergyPlus / AI CLI 全在容器内字节级一致。要点：
    - 容器内 EnergyPlus 为 `25.1.0`（基础镜像 `nrel/energyplus:25.1.0`）；§1.3 表中 `D:\EnergyPlusV25-2-0` 是宿主机 Windows 引擎（v25.2.0）。**patch 版有差异，仿真数值严格对齐时以容器版为准**。
    - venv 在 `/opt/venv`（挂载工作区外，不与宿主机 `.venv` 冲突）；Node + 三个 AI CLI（Claude Code / Codex / Gemini）在镜像构建期装入 Dockerfile，`postCreateCommand` 只剩 `uv sync`。
    - 改了 `.devcontainer/`（`Dockerfile` / `devcontainer.json` 等）后必须 `Dev Containers: Rebuild Container`，Reopen 不重跑。
    - git 是唯一同步通道，切设备前 `git push`（WIP 也推分支）；**禁**用 Seafile 等文件同步工具同步本目录。
    - **两套 Docker 资产别混**：`.devcontainer/`（不 COPY 代码、靠 bind mount，VS Code 用）vs [`docker/`](../docker/)（COPY 代码进镜像、构建 MCP server 发布制品）。
    - `docker/` 用法：服务器部署 `docker compose -f docker/docker-compose.yml up -d`（HTTP MCP server 在 :8000，`docker/Dockerfile`）；本地带热重载调试 `docker compose -f docker/docker-compose.dev.yml up`（`docker/Dockerfile.dev` + watchfiles，挂 `src/` 即时生效，读 `.env`，固定 `linux/amd64`）。两者基础镜像都是 `nrel/energyplus:25.1.0`。

---

## 7. 文档索引

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文档 — 项目管理总览（精简版）|
| [architecture.md](architecture.md) | 当前架构事实参考（2026-05-06 反映半人工流）|
| [new_case_guide.md](new_case_guide.md) | 新建测试样例标准 7 步流程（半人工版）|
| [plan.md](plan.md) | 行动清单（A 代码跑通 / B 识图能力提升 — 三阶段：恢复 / 评测基线规范化 / 能力升级）|
| [pivot_criteria.md](pivot_criteria.md) | 闭源 → 开源模型 pivot 双阈值 |
| [floorplan_redraw_strategy.md](floorplan_redraw_strategy.md) | 识图泛化：VLM 重绘 + 几何建模两步架构（2026-05-10 策略讨论 + 2026-05-12 §9 POC PASS 结果）|
| [`../skills/energyplus_mcp_twostep/`](../skills/energyplus_mcp_twostep/) | **两步法 skill 演进源**（phase1_vector_schema + phase2_rules + 两个 prompt 模板 + README）|
| [`../test_data/SmallOffice_TwoStep/`](../test_data/SmallOffice_TwoStep/) | **两步法测试语料库**（与 `SmallOffice/` 并列，2026-05-12 新建）|
| [token_optimization.md](token_optimization.md) | Token 优化（idfpy 切换后再做）|
| [open_model_guide.md](open_model_guide.md) | 开源模型操作手册（Continue + 预处理 + MCP）|
| [idfpy_embed.md](idfpy_embed.md) | idfpy 全线替换计划（搁置中）|
| [downstream_agent_changes.md](downstream_agent_changes.md) | 本项目侧对下游 9 subagent / cross_ref / validate / simulate 代码的 hotfix 记录（备份在 [`../src_history/`](../src_history/)）|
| [backup/](backup/) | 旧版本 / 历史快照 |
| [../test_data/test_baseline/README.md](../test_data/test_baseline/README.md) | baseline 字段定义 + 触发流程 |
| [../.devcontainer/README.md](../.devcontainer/README.md) | 多端开发环境指南(VS Code Dev Container 统一 Win/Mac/云)|

---

## 8. 待办（滚动）

### 8.1 当前活跃
- [x] `.env` 落盘（`DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL=https://api.deepseek.com`） ✅ 2026-05-07
- [x] sm_16_newarch 端到端首跑（14 节点机制 + L1/L2 + L4 EP simulate 全 PASS，2026-05-07；L4 通过手工修一行 Construction 后 EP `Completed Successfully`）✅
- [x] surface_agent T-vertex bug 调查闭环 ✅ 2026-05-07：EP 实测不卡，validator 永久放宽足够，[plan.md B0'](plan.md) 关闭
- [x] per-subagent 模型配置入口 ✅ 2026-05-07：[llm.yaml](../src/configs/llm.yaml) 9 个下游 subagent 各自可单独配 section；当前 surface/construction/fenestration 走 default(pro)，其余 6 个走 flash
- [x] **B1 [P0] 阶段 1 — 旧 skill 约束迁移到新架构** ✅ 2026-05-12：sm_20 半人工流 EP cleanly 跑通（0 severe / 0 fatal / 14 无害 warning），架构通透性 anchor 切到 sm_20。详见 [§5.5](#55-b1-阶段闭环--surface_agent-z_floor-hotfix2026-05-12)
- [x] **两步法 POC（sm_20）** ✅ 2026-05-12 晚：phase1 + phase2 + 下游 + EP 全链路验证 PASS（DeepSeek 路径 EP cleanly），架构通透性 + 识图泛化 + 微调可行性同时验证。详见 [§5.6](#56-两步法-intake-poc-pass--b15-立项最高优先级2026-05-12-晚)
- [ ] **B1.5 [P0] 两步法立项** ← **当前最高优先级**（[plan.md B1.5](plan.md) 6 个子任务，~3 周）
- [ ] **B2-B4 [P0] 阶段 2 — 评测基线规范化**：与 B1.5 并行推进；评测脚本要从一开始支持矢量 JSON 中间层 diff。详见 [plan.md B2-B4](plan.md)
- [ ] B5-B7 [P1] 阶段 3 — 能力升级（非方形 / 全局坐标退台挑空 / 规范化绘图）
- [ ] sm_17 端到端首跑（[plan.md B0''](plan.md)）—— 异图验证可复用性；可在 B2-B4 期间穿插
- [ ] OpenStudio 验收 sm_15 / sm_16 / sm_16_newarch / sm_17 / sm_20（用户填 `dimensions_check`）

### 8.2 暂搁置（外部依赖未交付前冻结）
- [ ] idfpy 替换主线（[idfpy_embed.md](idfpy_embed.md) P0-P3）：协作者侧 MCP 重写未启动
- [ ] [token_optimization.md §4.1-§4.5](token_optimization.md)：等 idfpy 切换后大量 CRUD 工具消失再重评估
- [ ] **fenestration / construction Construction layer 兼容性 prompt 修**：等 idfpy schema 校验原生覆盖（[plan.md §C](plan.md)；2026-05-07 sm_16_newarch 真跑发现 `WindowMaterial:SimpleGlazingSystem` 被当一层叠加导致 EP NaN fatal；用户决策当前几何优先，不动 prompt）
- [ ] Sonnet 4.6 / Haiku 4.5 降级测试

### 8.3 Pivot 准入后（双阈值达标前冻结，[pivot_criteria.md](pivot_criteria.md)）
- [ ] 部署 vLLM + Qwen2.5-VL 系列 / DeepSeek-VL
- [ ] LoRA SFT + holdout 评测，要求 ≥ Opus 80%
- [ ] 切 [llm.yaml](../src/configs/llm.yaml) `intake` section 默认 provider，全量回归

---

_2026-05-19 — 多端开发环境上线：§6 新增 #13（VS Code Dev Container 统一 Win/Mac/云，容器内 EnergyPlus 25.1.0 与宿主机 v25.2.0 patch 差异提示），§7 文档索引加 [`../.devcontainer/README.md`](../.devcontainer/README.md)。三个 AI CLI 改在 Dockerfile 构建期装（修原 postCreateCommand 静默半完成 bug）。#13 补 `docker/` 服务器/MCP-server 部署镜像用法（docker-compose 正式版 vs dev 热重载版），与 `.devcontainer/` 区分。_

_2026-05-12 (晚) — **两步法 POC PASS + B1.5 立项**：新增 §5.6（sm_20 全套两步法验证结果 + 决策切主线 + artifacts 迁移目录），§7 索引加两步法 skill / corpus 路径，§8.1 加 B1.5 最高优先级 todo。详见 [`floorplan_redraw_strategy.md §9`](floorplan_redraw_strategy.md) + [plan.md B1.5](plan.md)。_

_2026-05-12 — B1 阶段闭环：新增 §5.5（sm_18/19/20 真跑发现 + B1 全部交付 + surface_agent z_floor hotfix）；§6 #5 升级为"Skill / MCP / 下游 subagent 三类备份"并加 src_history/ + downstream_agent_changes.md 流程；§7 文档索引加 downstream_agent_changes.md；§8.1 B1 标 ✅ 切主线到 B2-B4。详见 [`downstream_agent_changes.md`](downstream_agent_changes.md) 2026-05-12 条 + [plan.md B1](plan.md)。_

_2026-05-07 (晚 v3) — runner.py 加 EP exe 三级解析（`$ENERGYPLUS_EXE` env → PATH → 硬编码 `D:\EnergyPlusV25-2-0\energyplus.exe`）；`.env` / `.env.example` 同步加 `ENERGYPLUS_EXE`；§1.3 路径表说明同步。下次跑 `run_full_pipeline.py <case>` 不再卡 FileNotFoundError。_

_2026-05-07 (晚 v2) — §1.3 加 EnergyPlus 引擎本地路径 + EPW 默认气象；§7 plan.md 描述更新为三阶段；§8.1 加新主线 B1 (阶段 1 恢复) + B2-B4 / B5-B7 阶段汇总。详见 [plan.md changelog](plan.md)。_

_2026-05-07 (晚) — 真跑 sm_16_newarch IDF 实证 EP 全链路通：T-vertex 不卡 EP，真 fatal 是 fenestration SimpleGlazing layer 兼容性 bug。决策不调 prompt（与 idfpy 切换一并解），主线焦点切到几何正确性。新增 §5.4；§8.1 重写活跃 todo（关 T-vertex / 加 per-subagent 模型配置）；§8.2 加 fenestration glazing deferred item。_

_2026-05-07 — 重写精简：原 410 行压到 ~150 行；§7 历史 timeline（sm_13/14/15/16 各 baseline + token 优化 P0 全过程 + Claude Code harness 切换等）整体下移到 baseline runs / git log；保留对当前架构仍有约束力的决策（几何/MEP 拆分 / trace 解码 / 半人工固化 + A2）；§5 索引补 backup/；§6 #5 合并 Skill_history/MCP_history 备份约定；§8 拆活跃 / 搁置 / Pivot 三档。详细历史变更日志见 git log。_
