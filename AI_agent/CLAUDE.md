# 多模态输入 Agent 项目管理文档

> 负责人工作区：面向 EnergyPlus-Agent 项目的「多模态（图像+文本）输入 → IDF 自动构建」模块。
> 本目录（`AI_agent/`）用于沉淀该模块的方案设计、实验记录、模型迁移计划与交付物。

---

## 1. 项目总览

### 1.1 仓库定位
- 根目录：[../](../)
- 项目说明：[../README.md](../README.md)
- 目标：将建筑设计意图（YAML / 自然语言 / 建筑图纸）自动转换为合法的 EnergyPlus IDF，并完成仿真。

### 1.2 上下游架构（2026-04-28 起）

```
[图像 + 文本输入]
   ↓
[本项目侧] 多模态 intake + 几何阶段 IDF 构建
   ↓
   产出标准 epJSON / idfpy 对象（通过 idfpy）
   ↓
[协作者侧 / LangSmith 上的下游 intake] MEP 阶段 + 仿真 + 解析
```

- **上游**（协作者侧 / LangSmith 编排）：完整多步 agent 架构在 LangSmith 上维护，本项目不直接管
- **本项目**（中间几何层）：多模态 intake + Zone/Surface/Fenestration 几何构建，产出标准 epJSON
- **下游**（协作者侧）：MEP（Materials/Schedules/HVAC）+ EnergyPlus 仿真 + 结果解析
- **统一中间格式**：[idfpy](../idfpy_dev/) Pydantic 模型 / `idf.to_dict()` epJSON 结构 — 由协作者维护

### 1.3 关键路径

| 路径 | 作用 |
|---|---|
| [../src/agent/](../src/agent/) | LangGraph 多阶段 Agent（intake → phase1 → cross_ref → … → simulate） |
| [../src/agent/nodes/intake.py](../src/agent/nodes/intake.py) | 多模态 intake 节点（text + base64 images → `IntakeOutput`），核心改造点 |
| [../src/agent/llm.py](../src/agent/llm.py) + [../src/configs/llm.yaml](../src/configs/llm.yaml) | LLM 工厂 + provider 配置（模型切换唯一入口） |
| [../src/mcp/](../src/mcp/) | MCP 工具集（**待协作者按 idfpy 全线重写**，详见 [idfpy_embed.md](idfpy_embed.md)） |
| [../skills/energyplus_mcp/](../skills/energyplus_mcp/) | Claude Opus 用 skill 提示词（几何阶段拆分版） |
| [../test_data/](../test_data/) + [../test_data/test_baseline/](../test_data/test_baseline/) | 案例数据 + baseline runs |
| [../tests/test_zone_agent.py](../tests/test_zone_agent.py) | 目前唯一自动化测试（纯文本，不涉图像） |

### 1.4 当前技术栈
- **LangGraph + LangChain**：`init_chat_model("{provider}:{model_name}")` 路由
- **多模态入口**：`intake_node` 把 `state.image_paths` 读 base64 → `ImageContentPart` → `HumanMessage.content`
- **结构化输出**：`llm.with_structured_output(IntakeOutput, include_raw=True)` 依赖 tool-calling
- **IDF 构建（迁移中）**：原 13 个手写 converter + ConverterManager → **idfpy 全线替换**（[idfpy_embed.md](idfpy_embed.md)）

---

## 2. 我负责的范围

### 2.1 In-scope
1. `intake_node` 多模态理解（图纸 + 文本 → `IntakeOutput`）
2. `src/agent/llm.py` provider 抽象与开源模型接入
3. Skill 提示词（`skills/energyplus_mcp/*.md`）开源模型迁移
4. 多模态测试数据集 + 几何阶段 baseline
5. 本地部署方案（推理后端 / 显存 / tool-calling）

### 2.2 Out-of-scope（协作者）
- 下游 MEP 阶段 + EnergyPlus runner + 结果解析
- RAG 知识库
- **MCP 工具基于 idfpy 的全线重写**（详见 [idfpy_embed.md](idfpy_embed.md) §3.1）
- LangSmith 上的多步 agent 编排

---

## 3. 测试现状（重要历史数据，作 idfpy 切换前的基线参考）

### 3.1 资产
- **单元测试**：[../tests/test_zone_agent.py](../tests/test_zone_agent.py)（zone_agent 纯文本生成 2 zone）
- **端到端 demo**：[../scripts/run_demo.py](../scripts/run_demo.py)（无图像通路）
- **人工案例集**：[../test_data/SmallOffice/smalloffice_0..16/](../test_data/SmallOffice/)
  - 早期 sm_0..12 无尺寸基线；**sm_13** 起新规格（两级尺寸链 + 4 facade 朝向命名 + 产物在 `output/`）
  - sm_15 起严格全程 MCP（不再走 `build_yaml.py` 直写 YAML）
  - **sm_16** 起多层平面输入（每层独立 `{k}f_view.png`，外包围共享）— testdata_prompt.json 用 schema A `Floor plans` 数组

### 3.2 旧 ConverterManager 流水线通过率（13 案例 Opus 人工基线）

| 环节 | 通过 | 通过率 |
|---|---|---|
| claude_ep.md | 12/13 | 92% |
| YAML | 8/13 | 62% |
| IDF | 7/13 | 54% |
| EP 仿真启动 | 1/13 | 8% |
| **EP 仿真完成** | **0/13** | **0%** |

**系统性缺陷**（7 个 IDF 案例统计）：所有缺 `Schedule:Compact` / `Lights` / `HVACTemplate:Zone:IdealLoadsAirSystem`；仅 sm_1(1) / sm_11(24) 有 fenestration。sm_0 Fatal 根因：跨区内墙构造不对称。

> ⚠️ 此基线基于已废弃 ConverterManager + eppy + 手写 schema 路径，**idfpy 切换后需用 §4 验收门槛重建**。`validate_config` 类问题（fenestration 静默丢失等）由 idfpy 的 `idf.validate()` 在 IDF 阶段强制暴露。

### 3.3 关键洞察（仍有效）
1. **视觉理解不是瓶颈**（12/13 出 claude_ep.md）
2. 真正瓶颈：**长链路 tool-calling 稳定性 + 子系统覆盖完整性**（Schedule/Lights/HVAC 普遍缺失）
3. **强制后处理补丁**不能交给 LLM 记得打 → 已通过 [Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py) 5 条补丁脚本化；idfpy 切换后大部分由 `idf.validate()` 顶替

---

## 4. 开源模型迁移计划（终态）

### 4.1 候选模型（待评估）
- **Qwen2.5-VL-7B / 32B / 72B-Instruct**（首选，tool-calling 较成熟、中英文图纸友好）
- InternVL2.5/3、Llama 3.2-Vision、MiniCPM-V 2.6/o 2.6、Pixtral-12B

评估维度：① 图纸尺寸数字识别 ② 房间/走廊/楼梯区分 ③ JSON/tool-call 合规率 ④ 中文输出稳定性 ⑤ 显存

### 4.2 推理后端
首选 **vLLM + OpenAI 兼容 API**（只需改 `llm.yaml` 的 provider/base_url，`create_llm` 不动）。备选 SGLang / LMDeploy / Ollama。

### 4.3 里程碑
| M | 目标 | 产出 |
|---|---|---|
| M1 | 多模态 golden 数据集 v0.1（≥10 case） | `AI_agent/datasets/` |
| M2 | 自动评测脚本（IntakeOutput diff + zone 几何比对） | `AI_agent/eval/` |
| M3 | Anthropic 流水线基线分数（**重建**，旧基线已废） | 基线报告 |
| M4 | vLLM + 候选开源模型，跑同一套评测 | 对比报告 |
| M5 | gap 修补（tool-calling、尺寸识别）：prompt / few-shot / 微调 | v1 迁移方案 |
| M6 | 切 `llm.yaml` 默认 provider，全量回归 | 切换 PR |

### 4.4 Pivot 双阈值（来自 [pivot_criteria.md](pivot_criteria.md)）
- **视觉层**：zone 匹配率 ≥90% / 房间尺寸误差 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80
- **流水线层**：claude_ep.md ≥95% / 几何 IDF round-trip ≥90% / EP 完成 ≥50%
- **当前**：均远低于阈值，Pivot 议题尚未到判定时机

---

## 5. 本目录文档索引

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文档 — 项目管理总览 / 下次会话初始上下文 |
| [idfpy_embed.md](idfpy_embed.md) | **idfpy 全线替换执行计划**（P0-P3 阶段、协作者/本项目分工、~3-4 周） |
| [idfpy_bug_case_insensitive.md](idfpy_bug_case_insensitive.md) | idfpy IDF parser 大小写 bug 报告（26.1.0.post1 实测仍存在） |
| [token_optimization.md](token_optimization.md) | Token 优化方案（4 段结构：占用问题 / 解决方案 / 已做 / 计划做） |
| [new_case_guide.md](new_case_guide.md) | 新建 SmallOffice 测试样例的 7 步流程 |
| [plan.md](plan.md) | 输入端 VLM 准确性提升方案（CoT vs 前置小模型） |
| [pivot_criteria.md](pivot_criteria.md) | 闭源 → 开源模型 pivot 判定准则 |
| [open_model_guide.md](open_model_guide.md) | 开源模型操作手册（Continue + 预处理 + MCP，sm_14 Qwen 实战沉淀） |
| [../test_data/test_baseline/README.md](../test_data/test_baseline/README.md) | 几何阶段最小测评骨架 |

### 5.1 规划中目录（按需创建）
```
AI_agent/
├── design/         # 方案设计
├── datasets/       # 多模态 golden（v0 直接复用 ../test_data/）
├── eval/           # 评测脚本 & 指标
├── experiments/    # 单次实验记录（按日期 / 模型）
├── prompts/        # 开源模型分步 CoT 各版本
└── deploy/         # vLLM / SGLang / Langfuse self-hosted
```

---

## 6. 协作者约定

1. **模型切换入口唯一**：`src/configs/llm.yaml` + `src/agent/llm.py`，不在节点内硬编码
2. **多模态改动只改 intake**：不绕过 `intake_node` 把图像直接塞下游
3. **每次模型/提示词变更**：在 `AI_agent/experiments/` 新建运行记录（模型 ID / 提示词 hash / 评测结果 / 失败样本）
4. **回归门槛**：切默认 provider 前，端到端跑通率不得低于 Anthropic 基线 80%
5. **Skill 版本管理**：修改 `skills/energyplus_mcp/`（含子目录）前，**必须先备份**：
   ```bash
   cp -r skills/energyplus_mcp Skill_history/<YYYY-MM-DD>_energyplus_mcp
   ```
   同日多次备份加后缀（如 `_v2` / `_pre_batch`）
6. **MCP 改动备份同理**：`MCP_history/<YYYY-MM-DD>_mcp_<reason>/`
7. **Baseline 记录触发**：用户说 `记录这次跑 <case> <tag>` → 严格按 [test_baseline/README.md §4.3](../test_data/test_baseline/README.md) 执行清单：先 `Tool_scripts/baseline_record.py <case> <tag>` 生成 skeleton，再按 §4.2 字段所有权填 `<FILL_ME>`，最后 ≤6 行总结。**不替用户填 `dimensions_check`**（OpenStudio 人工验收专属）
8. **idfpy 替换期**：[idfpy_embed.md](idfpy_embed.md) §3.1 划归协作者；本项目侧并行 §3.2（skill / scripts / 数据 / 文档）
9. **本项目不再输出完整 IDF**（2026-04-28 决策）：几何阶段产出标准 epJSON / `idf.to_dict()`，喂给协作者侧 intake；`Tool_scripts/export_idf.py` P2 可大幅缩减或删除

---

## 7. 关键决策时间线

### 7.1 评测基线先行（2026-04-20）
任何优化（CoT / 前置小模型 / 模型切换）前必须有可复现 baseline。当前 13 案例通过率是人工统计、非自动化回归。

### 7.2 P0 → P3 视觉优化分期（[plan.md](plan.md)）
P0 评测基线 → P1 分步 CoT + PaddleOCR + cv2 走廊预处理 → P2 YOLOv8 符号检测（按需） → P3 全矢量化（不推荐）。**结论**：视觉理解非瓶颈，P1 必须同时做"提示词结构化 + 强制后处理补丁"。

### 7.3 Langfuse self-hosted 评测平台（2026-04-20）
不用 LangSmith SaaS（与本地可控目标相悖）。Langfuse 用 Docker Compose 起，OpenTelemetry + LangChain callback。P0 先文件化 `reports/*.csv`，Langfuse 接入挪 P1。
> 📝 注：协作者侧多步 agent 仍在 LangSmith 上维护（§1.2），本项目侧评测用 Langfuse，两者并行不冲突。

### 7.4 sm_13 输入规格升级（2026-04-21）
- **两级尺寸链**（外部总链 + 外层分段链，黑色等宽 mm）成为硬约束 → 房间尺寸中位误差有 GT 可比
- 立面图按朝向命名 `{South|North|East|West}_view.png`，缺文件 = 该朝向 0 窗
- `testdata_prompt.json` 移除所有 GT 字段，未来另拆 `gt.json`
- Fenestration 提升为 IDF Workflow 独立 Step 5（防 0 窗），`zonetool_prompt §M7` Wall-index → facade 映射
- MCP 挂载基础设施：修复 typer/click 签名冲突 + `.mcp.json` server key = `EnergyPlus-Agent`
- 标注图改为不裁剪 + 最多 2× 放大；产物全部进 `<case_dir>/output/`

### 7.5 sm_14 开源模型基础设施（2026-04-22）
- 新建 [Tool_scripts/preprocess_images.py](../Tool_scripts/preprocess_images.py)（白边裁剪 + resize，解 Continue 16k per-attachment 上限）
- 新建 [skills/energyplus_mcp/open_model/](../skills/energyplus_mcp/open_model/) 10 步工作流
- 新建 [open_model_guide.md](open_model_guide.md)（Continue 配置 / TPM 策略 / MCP 挂载 / 图像 UX）
- **关键发现**：Continue 客户端 token 估算（W×H/28）vs 模型侧（ceil(W/28)×ceil(H/28)）差 27.7×；本地部署 TPM 消失但上下文容量 + tool-chain 稳定性更脆弱
- 安全提醒：会话曾明文粘贴 SiliconFlow API Key，建议 revoke

### 7.6 sm_15 几何阶段 + skill 拆分（2026-04-25/26）
- **核心决策**：IDF 建模拆「几何阶段」+「MEP 阶段」，独立会话可由不同模型执行
- 当前 skill 仅几何阶段；占位 construction：`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`
- sm_15 首次全程 MCP 跑通：14 zones / 84 surfaces / 12 fenestration / 1 location + 1 building + 14 create_zone + 84 update_surface + 12 create_fenestration + 1 export_yaml
- 多楼层 / 退台 / 挑空原则：**全局唯一世界坐标系**（原点 = 整栋投影最大边界 SW 内角，禁止每层本地原点）

### 7.7 P0 三档 token 优化全部落地（2026-04-27）
1. **改动 4** [Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py) 外置 + 5 条补丁（含**补丁 0** 预置占位 Construction，否则 fenestration 静默丢失）
2. **改动 1** MCP CRUD 默认 ack-only（base.py + create_zone 特例）
3. **改动 2** `update_surfaces_batch` + `create_fenestration_surfaces_batch`（envelope.py inline 120 行）
- MCP 工具数 77 → 79
- 备份：`MCP_history/2026-04-27_mcp_pre_*` + `Skill_history/2026-04-27_*`

### 7.8 测评 baseline 框架 + 实测复盘（2026-04-28）
- 建立 [../test_data/test_baseline/](../test_data/test_baseline/) 几何阶段最小骨架（runs 目录 + meta.json / tokens.json / geometry.json / notes.md / context.txt）
- 自动化脚手架 [Tool_scripts/baseline_record.py](../Tool_scripts/baseline_record.py)：用法 `<case> <tag>`，自动建目录 + regex 解析 IDF counts + skeleton
- sm_15 实测对比：**pre_p0 anchor 221.3k vs post_p0 163.4k = -26%**（不是预测的 -50%）；纠正了 token_optimization.md "150k baseline" 严重低估 ~71k harness 开销的错误
- 估算方法论：`tokens.total` **必须**从 `/context` 真读，不接受估算；估算系统性低估 50%+

### 7.9 Claude Code harness 切换 + idfpy 引入（2026-04-28 下半）

**A. Claude Code 切换到 deferred MCP 架构**
- Session 启动只预载 9 个核心工具（Agent/Bash/Edit/Glob/Grep/Read/Skill/ToolSearch/Write）
- 100+ MCP 工具按需通过 `ToolSearch` 取 schema，**不预占 context**
- 新版 `/context` 实测：total 73.3k / system tools 11.8k / 上下文窗 1.0M
- → §7.8 anchor 221.3k 已不可比；`deniedMcpServers`（旧 -20k 杠杆）和 MCP description 压缩在新架构下都是 **no-op**
- token_optimization.md 已重写为 4 段结构（占用问题 / 解决方案 / 已做 / 计划做）

**B. idfpy 全线替换决策**
- 协作者维护的 [idfpy](https://pypi.org/project/idfpy/)（v26.1.0.post1，PyPI 直装）将替代本项目的 eppy + 13 个 converter + ConverterManager + 33 个手写 Pydantic schema
- sm_15 round-trip 验证通过：124 对象 / `idf.validate()` 0 errors / 几何 mixin (`area/normal/centroid`) 直接可用
- 完整执行计划：[idfpy_embed.md](idfpy_embed.md)（P0 阻塞解除 / P1 小试 / P2 全量切换 / P3 验收，~3-4 周）
- **本项目不再输出完整 IDF**（§6 #9）：几何阶段产 epJSON 给协作者侧 intake；`export_idf.py` P2 可大幅缩减或删除
- 已 `pyproject.toml` 加 `idfpy>=26.1.0.post1` + `pillow>=11.0.0`；`idfpy_dev/` 已删

**C. idfpy 已知 bug**（[idfpy_bug_case_insensitive.md](idfpy_bug_case_insensitive.md)）
- IDF parser 不识别大写对象类型名（`ZONE,` → 0 对象解析；`Zone,` 正常）
- 26.1.0.post1 实测**仍存在**；与 README 第 23 行宣称"Case-insensitive"矛盾
- 临时绕过：epJSON 主路径 / `Tool_scripts/idfpy_roundtrip_sm15.py` 的 `normalize_idf_case()`
- 已交协作者修复，等下个 patch（如 26.1.0.post2）

### 7.10 多层平面输入升级（2026-04-29，sm_16）

**A. JSON schema 演进（schema A）**
- 旧 `"Top view path of the building"` 单图字段保留为 back-compat（视为所有楼层共享同一平面）
- 新增 `"Floor plans"` 数组：`[{"floor": k, "path": "{k}f_view.png", "thermal_zones": int}, …]`，长度 = `"Number of floors"`
- sm_16 实测样例：3 层 / 7 + 8 + 4 = 19 zones / 单层 120 m² / 共享 W × D 外包

**B. 硬约束：共享外包围（§D3.1 invariant）**
- 本轮**仅支持**每层 outer chain 完全相同（`W_f == W_g`、`D_f == D_g`，容差 ≤0.01 m）
- 内部分区可任意不同（zone 数、走廊位置、楼梯/电梯位置）
- 退台 / cantilever / atrium / 缺层全部 **out of scope** → 检测到外包不一致即停，请用户确认
- 全局唯一世界坐标系仍延用（§7.6）：(x,y) = (0,0) 是共享外包的 SW 内角；Z = 0 是 F1 的 FFL；上层 `z_f = Σ_{k<f} h_k`

**C. 提示词 / 代码改动**（备份在 `Skill_history/2026-04-29_energyplus_mcp_pre_multifloor/`）
- [skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md)：§1 加 `Floor plans` 数组 + 共享外包硬约束；§D3 改名 `Per-Floor Plans`，新增 §D3.1 不变量；§1.5/§2/§3 全部循环化（每层一份 annotated PNG + Dimension Extraction sub-section）；§D6 footprint coverage 改为 per-floor 检查
- [skills/energyplus_mcp/zonetool_prompt.md](../skills/energyplus_mcp/zonetool_prompt.md)：§M1/M2/M3/M5 显式标注 per-floor `xs_f, ys_f`；不再共用一组数组
- [src/agent/nodes/intake.py](../src/agent/nodes/intake.py)：每张图前注入 `[Next image] <label>` TextContentPart；标签由文件名正则推断（`{k}f_view` / `{dir}_view` / `top_view` / `supp_plan`）；`INTAKE_SYSTEM_PROMPT` 加多层平面理解段落
- [AI_agent/new_case_guide.md](new_case_guide.md)：§1 表头新增 `{k}f_view.png` 行 + §1.1 加共享外包硬约束 + §1.2 字段表换 schema A（移除 `Number of total/per floor thermal zones`）+ §2 cp 命令逐层 + §3 JSON 模板换 schema A + §5 LLM prompt 第 2-5 步循环化 + §6.1 目录结构加逐层文件 + §6.2 zone 总数改 `sum(Floor plans[*].thermal_zones)` + §8 常见坑加 3 行 + §9 蓝图 `_collect_images()` 从 `Floor plans` 读图
- **未改**：`open_model/`（暂不支持开源模型路径）；MCP 工具签名（多层在 prompt 层而非工具层处理）

**D. 待办**
- [x] 跑 sm_16 全 MCP 通路；记 baseline `2026-04-29_sm_16_multifloor_v1`（详见 §7.11）
- [ ] OpenStudio 几何验收（§6 #7）
- [ ] 退台 / 多形态外包延后到 sm_17+；届时再扩展 §D3.1 与全局原点定义

### 7.11 sm_16 跑通 + token 口径二次修正（2026-04-29）

**A. sm_16 几何阶段端到端**（baseline `2026-04-29_sm_16_multifloor_v1`）
- 一次会话跑通：3 层 / 19 zones（F1 7 + F2 8 + F3 4）/ 114 surfaces / 16 fenestration / 4 facade（南 6 + 北 8 + 东 1 + 西 1，F3 南立面空白）
- 共享外包 W × D = 15 × 8 + 每层独立 `xs_f / ys_f`（F2 北/南条 x 链不对称：`3.75|3.75|3.75|3.75` vs `5|5|5`）+ 顶层 4.80 m 大开窗均一次到位
- `update_surfaces_batch` 一次喂 114 条 / `create_fenestration_surfaces_batch` 一次喂 16 条 — batch 化在更大规模仍线性 ROI（详见 §7.11.C）
- 标注脚本暗像素 bbox 检测改为"行/列暗像素密度阈值"剔除 dimension chain 箭头（沉淀在 [test_data/SmallOffice/smalloffice_16/output/annotate.py](../test_data/SmallOffice/smalloffice_16/output/annotate.py)）

**B. token 关键发现（修正 §7.8 / §7.9 的口径错误）**

比对 sm_15 anchor (2026-04-27) 与 sm_16 (2026-04-29) 的 `context.txt` 确认：**`/context` 各分类并非全部计入 `Tokens used` Total**。

| 计入 Total | 不计入 Total（display-only / 预留区） |
|---|---|
| System prompt / System tools / MCP tools (loaded) / Memory / Skills / Messages | MCP tools (deferred) / System tools (deferred) / Autocompact buffer / Free space |

直接修正了两处旧判断：
- **§7.9.A "新 harness ~55k"** 把 autocompact + deferred 算了进去 → 真实计入 Total 的 harness 仅 **~24k**；[token_optimization.md §0](token_optimization.md) 表格里"新 harness ~55k"也偏高
- **§7.8 sm_15 post_p0 复盘里"关掉无关 MCP server 省 ~20-36k"作废** — 那部分本就没花，新旧 harness 都是 deferred display 不计入 Total

已落 memory `project_context_token_accounting.md` + 修正 `2026-04-27_sm_15_post_p0/notes.md` + `2026-04-29_sm_16_multifloor_v1/notes.md`。

**C. 规模翻倍而 token 几乎持平**

| 指标 | sm_15 post_p0 anchor | sm_16 multifloor_v1 | Δ |
|---|---|---|---|
| `/context` Total | 163.4k | 164.3k | +0.9k (+0.5%) |
| Counts (z/s/f) | 14/84/12 | 19/114/16 | +36% / +36% / +33% |
| MCP 调用数 | 22 | 28 | +6 (+27%) |
| 输入图像数 | 5（单层 + 4 facade） | 7（3 层 + 4 facade） | +2 |
| 真实计入 Total 的 harness | ~24k | ~24k | ≈0 |

**结论**：batch 化 + 真实 harness 24k 联合作用下，复杂度 +36% 仅吃掉 ~1k token，messages 段反而微降。后续 token 优化的真正大头是 **messages（~140k 占 86%）**，**不是 harness**——这一发现影响 token_optimization.md §6 的实施顺序排期（详见 §8.0 与 token_optimization 同步更新）。

**D. 与开源模型迁移路线的关系**
- 100k context 对 Qwen3-30B-A3B 这类小激活 MoE 处于"能跑但容易掉链子"区间；164k 已偏紧
- 多图视觉（7 张）+ 长状态追踪（19 zone × 6 surface 邻接 + 16 window 父墙引用）+ 结构化批量 JSON（114 条 update + 16 条 fenestration）三重叠加，对小激活 MoE 是最不友好场景
- 现实路线：**会话切分**（phase A 出 `claude_ep.md` + 标注图存盘 → 关会话 → phase B 起新会话只读 ep.md 调 MCP）每段 ≤50k，A3B 完全够用；或选 22B+ 激活的 MoE（Qwen3-235B-A22B / DeepSeek-V3 / Llama-405B）
- 该判断已落到 `pivot_criteria.md` 候选模型选型；激活 idfpy 切换主线（§8.1）后再启 [pivot 评估](pivot_criteria.md)

---

## 8. 待办（滚动更新）

### 8.0 sm_16 收尾 + token 优化路线重排
- [x] 跑 sm_16 几何阶段全 MCP 通路（Opus），生成 `output/floor{1,2,3}_annotated.png` + `claude_ep.md` + YAML + IDF
- [x] `Tool_scripts/baseline_record.py sm_16 multifloor_v1` → `2026-04-29_sm_16_multifloor_v1/`
- [ ] OpenStudio 验收（19 zones / W × D 共享 / 每层 120 m²；用户填 `dimensions_check`）
- [x] [token_optimization.md](token_optimization.md) 同步：主体降 token 工作（§4.1-§4.5）整体推迟到 idfpy + MCP 重写完成后再做（理由：MCP 接口在 P2 切换中会大量重写，现在做的优化大概率会被推翻；且 sm_16 实测显示 batch 化已把 messages 段压到 140k，距离开源模型可承受区间还差一道"会话切分"工程，这道工程也应在 idfpy 切完后再设计）
- [ ] 触发 idfpy 切换主线（§8.1）

### 8.1 Next Step（idfpy 替换主线）
- [ ] **P0 阻塞解除**（[idfpy_embed.md §1](idfpy_embed.md)）
  - 协作者修 idfpy 大小写 bug
  - 本项目决策 EnergyPlus engine 版本（升 26.1 / 锁 25.2 / 等协作者补 25.2 schema）
- [ ] **P1 小试**（[idfpy_embed.md §2](idfpy_embed.md)，本项目 ~3 天）：`src/mcp_v2/` 起步，跑通 sm_15 几何阶段
- [ ] **P2 全量切换**（[idfpy_embed.md §3](idfpy_embed.md)，协作者主导 MCP 重写 + 本项目并行 skill / scripts / 数据，~1.5-2 周）
- [ ] **P3 验收**（[idfpy_embed.md §4](idfpy_embed.md)，~3-5 天）：sm_0..15 round-trip + 重建 baseline anchor

### 8.2 暂搁置（P2 前冻结，避免被推翻）
- [ ] [token_optimization.md §4.1-§4.5](token_optimization.md) 的 validate 截断 / blank facade / 顶点短形式 / ASCII 瘦身 / 自动 boundary 推断 — 待 idfpy 切换后重评估（很多 CRUD 工具会消失）
- [ ] OpenStudio 几何验收（[test_baseline/runs/2026-04-27_sm15_post_p0/geometry.json](../test_data/test_baseline/runs/2026-04-27_sm15_post_p0/) 改 `dimensions_check` + 截图）
- [ ] Sonnet 4.6 降级测试（idfpy 切换后再做，避免重复跑废）

### 8.3 P0 完成后再启
- [ ] 核对 `llm.yaml` 中 `model_name: gpt-5.4` 占位符，统一为可运行的 Claude Opus ID
- [ ] 按 [plan.md §P1](plan.md) 改写 skill 为分步 CoT + intake 前接 PaddleOCR + cv2 预处理 hook
- [ ] Langfuse self-hosted 部署 + LangChain callback handler
- [ ] 以 Opus baseline trace 作 SFT 数据种子（≥500 对，[pivot_criteria.md §4.1](pivot_criteria.md)）

### 8.4 Pivot 准入后（阈值达标前冻结）
- [ ] 部署 vLLM + Qwen2.5-VL-7B-Instruct
- [ ] LoRA SFT + holdout 评测，要求 ≥ Opus 80%
- [ ] 切 `llm.yaml` 默认 provider，全量回归

---

_2026-04-29 (下半) — sm_16 几何阶段端到端跑通；记 baseline `2026-04-29_sm_16_multifloor_v1`（19 zones / 114 surfaces / 16 fenestration / total 164.3k vs sm_15 anchor 163.4k 仅 +0.5%）；token 口径二次修正（deferred + autocompact 不计入 Total，真实 harness ~24k 而非 ~55k 或 ~100k）；token 优化主体（§4.1-§4.5）推迟到 idfpy + MCP 重写后再做；新增 §7.11、修订 §7.10.D、重排 §8.0；同步修订 [token_optimization.md](token_optimization.md) §0/§6_

_2026-04-29 — sm_16 多层平面输入升级：testdata_prompt schema A（`Floor plans` 数组）；skill / zonetool prompt + intake.py 改造；§D3.1 共享外包硬约束（退台延后）；备份 `Skill_history/2026-04-29_energyplus_mcp_pre_multifloor/`；新增 §7.10 + §8.0；同步重写 [new_case_guide.md](new_case_guide.md) 全 9 节适配 schema A_

_最后更新：2026-04-28（下半）— 重写整理 §7 时间线（合并 §7.5-§7.8 日记段）；新增 §7.9（A/B/C）：Claude Code deferred MCP 架构 + idfpy 引入决策 + idfpy 大小写 bug；§1.2 新增上下游架构图（LangSmith 上游 / 本项目几何中间层 / 协作者下游 intake）；§5 索引补 idfpy_embed.md + idfpy_bug_case_insensitive.md；§6 新增约定 #8（idfpy 分工）+ #9（不再输出完整 IDF）；§8 重排为 idfpy 替换主线 + token_optimization §4 暂搁置；删旧 §7.7.5/§7.8.4 等已被新决策覆盖的细节_

_2026-04-27 — P0 三档 token 优化全部落地（改动 1/2/4）；MCP 工具数 77 → 79_

_2026-04-26 — 新建 [token_optimization.md](token_optimization.md)；sm_15 几何阶段全 MCP 跑通；skill 拆分几何/MEP_

_2026-04-21..22 — sm_13 输入规格升级（两级尺寸链 + facade 朝向命名）；sm_14 开源模型基础设施（preprocess_images.py + open_model skill）_
