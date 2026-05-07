# Test Baseline

> 几何阶段 IDF 构建的最小测评骨架。承接 [AI_agent/CLAUDE.md §7.1 评测基线先行](../../AI_agent/CLAUDE.md) 与 [AI_agent/token_optimization.md](../../AI_agent/token_optimization.md)。
>
> **当前阶段**：仅记录几何阶段产物 + token 消耗 + 人工尺寸验收。MEP 验收 / 自动几何 diff / capability 维度等待流程改造（YAML→IDF → 函数包）落地后再扩展。

---

## 1. 范围约定

- **唯一验收维度**：几何（zone / surface / fenestration counts + OpenStudio 三维尺寸目视通过）
- **不在范围**：5 档 stage 通过率、MEP 子系统覆盖、EP 仿真跑通率、capability 命中度
- **跨 run 比较前提**：先按 `meta.pipeline_version` 分桶。`yaml_to_idf_v1` 与未来的 `function_pkg_v1` 不直接比较 token / counts。

---

## 2. 目录结构

```
test_data/test_baseline/
├── README.md                            ← 本文件
└── runs/
    └── <YYYY-MM-DD>_<case>_<tag>/       ← 每一次 run 一个目录
        ├── meta.json                    ← 模型 / skill / mcp / pipeline 标识
        ├── tokens.json                  ← 总量 + 按 phase / 按 tool 分布
        ├── geometry.json                ← counts + dimension check + 异常清单
        └── notes.md                     ← 自由文本观察、改进想法、失败归因
```

`<tag>` 用于区分同一 case 在不同 P0 / pipeline 状态下的 run，例：
- `2026-04-26_sm15_pre_p0/`（P0 改动 1/2/4 都未做）
- `2026-04-27_sm15_post_p0/`（P0 三档全做完后重跑）
- `2026-XX-XX_sm15_function_pkg/`（函数包流程上线后重跑）

---

## 3. 字段定义

### 3.1 `meta.json`（不变量字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `timestamp` | ISO8601 | run 启动时间 |
| `case` | str | 案例名（如 `sm_15`） |
| `model` | str | LLM 模型 ID（如 `claude-opus-4-7`） |
| `skill_version` | str | Skill_history 快照目录名或 hash |
| `mcp_tool_count` | int | MCP server 注册的工具总数（识别 batch 等增量） |
| `pipeline_version` | str | **关键**：`yaml_to_idf_v1` / `function_pkg_v1` 等 |
| `p0_flags` | str[] | 已启用的 P0 优化项：`ack_only` / `batch` / `export_idf_externalized` |

### 3.2 `tokens.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | int | 累计 token（含掉线重灌） |
| `session_count` | int | 实际开过的会话数（1 = 一次跑完，>1 = 有掉线/续跑） |
| `by_phase` | dict[str,int] | phase 名是**自由字符串**，明天换流程时只换 key（例：`vision_understanding`、`create_zones`、`update_surfaces_batch`） |
| `by_tool` | dict[str,{calls,tokens}] | （可选）按 MCP 工具维度。batch 化后值得记，便于看 batch ROI |

> Token 数字来源：会话窗口中的 token 计数 / Continue trace / 自行估算。**反填的 anchor run 必须在 `notes.md` 标注估算依据**。

### 3.3 `geometry.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `counts` | `{zones, surfaces, fenestration}` | 实际 IDF 产物对象计数 |
| `counts_expected` | 同上 | 案例 GT。本阶段直接写在 run 里，不抽出独立 cases 文件 |
| `dimensions_check` | enum | `pass` / `fail` / `partial`：OpenStudio 三维视图人工核对结果 |
| `openstudio_screenshot` | str? | （可选）截图相对路径，存放 run 目录下 |
| `anomalies` | str[] | 异常清单（如 "Zone_F2_N2 顶点逆序"、"S1 西墙未贴邻"） |

### 3.4 `notes.md`

自由文本。建议至少含：
- **本次目的**（一句话）
- **失败/异常**（如有）
- **下次改进候选**

---

## 4. 如何记录新 run

### 4.1 触发约定（用户视角）

**会话末尾的两步**:

1. 用户在 Claude Code 中输入 `/context`，**完整复制**输出文本，粘贴到运行目录(待 Claude 创建)的 `context.txt` 文件
   - 顶部应含 `Tokens: X / 1m (xx%)` 一行
   - 下方应有 `Estimated usage by category` 表
   - 这是 `tokens.total` 的**唯一权威来源** —— 不接受估算
2. 对 Claude 说: `记录这次跑 <case> <tag>`，例 `记录这次跑 sm_15 post_p0`

Claude 收到触发后按 §4.3 执行。用户**不需要**额外指明参考文档 —— `AI_agent/CLAUDE.md §6` 已约定看到此触发要查本 README。

> **为什么必须粘 `/context`**: 历史经验(2026-04-27 sm_15 复盘)表明，估算的 token 总量与 `/context` 真实值能差近一倍 —— 估算把每次 MCP 调用当独立成本,忽略 history 累积 + harness 固定开销(~100k)。所以 `tokens.total` 字段以后**强制**从 context.txt 读，估算只能作 by_phase / by_tool 的相对分布参考。

### 4.2 字段所有权（谁填什么）

| 字段 | 谁填 | 怎么填 |
|---|---|---|
| `meta.timestamp` / `meta.case` | 脚本 | 自动 |
| `meta.model` | Claude | 从当前模型 ID（自知） |
| `meta.skill_version` | Claude | 当前 `Skill_history/` 最新快照目录名 |
| `meta.mcp_tool_count` | Claude | 调用 `ListMcpResourcesTool` 或当前 `<tools>` 列表点数（仅数 `mcp__EnergyPlus-Agent__*` 前缀） |
| `meta.pipeline_version` | Claude | 当前流程标识（如 `yaml_to_idf_v1` / `function_pkg_v1`） |
| `meta.p0_flags` | Claude | 当前已启用的 P0 项（参考 [token_optimization.md](../../AI_agent/token_optimization.md) §2） |
| `tokens.total` | Claude（从 context.txt 读） | **必须**从用户粘贴的 `context.txt` 顶部 `Tokens: X / 1m` 一行解析；缺 context.txt 时停下来要 |
| `tokens.messages` | Claude（从 context.txt 读） | `Messages` 一行的数字；剔除 harness 开销后的"实际工作量" |
| `tokens.harness_overhead` | Claude（从 context.txt 读） | system prompt / tools / mcp / autocompact 等分项,直接抄 context.txt 表格 |
| `tokens.session_count` | Claude | 实际会话数（掉线 +1）；用户告知或从对话上下文推断 |
| `tokens.by_phase_estimate` | 可选 | Claude 从 session memory 估算分布；**仅作相对参考**,不参与 Δ 比较 |
| `tokens.by_tool_estimate` | Claude | calls 数从 session memory 精确数；tokens 是估算,不参与 Δ 比较 |
| `geometry.counts` | 脚本 | 自动从 IDF 解析 |
| `geometry.counts_expected` | 脚本预填 = counts | Claude 校验 → 若 LLM 知道真实 GT 不同则改 |
| `geometry.dimensions_check` | **用户** | OpenStudio 打开后人工填 `pass` / `fail` / `partial` |
| `geometry.openstudio_screenshot` | **用户** | 截图扔进 run 目录后填相对路径 |
| `geometry.anomalies` | Claude / 用户 | 异常 zone / 顶点错位等清单 |
| `notes.md` | Claude | 按 stub 章节填写 |

### 4.3 Claude 收到触发后的执行清单

接受触发 `记录这次跑 <case> <tag>` 后:

1. **Bash 调脚本**:
   ```bash
   uv run python Tool_scripts/baseline_record.py <case> <tag>
   ```
   验证 stdout 报告 `[ok] Counts: ...` 三个数字 ≠ null。
   - 若脚本报 `[warn] No IDF found`，停下来问用户 IDF 路径，**不要继续填**。
   - 若 `run_dir already exists`，问用户是否要换 tag。

2. **检查 `context.txt` 是否存在于 run_dir**:
   ```bash
   ls test_data/test_baseline/runs/<run_id>/context.txt
   ```
   - 若不存在: 停下来要用户粘贴 `/context` 输出到该文件，**不要继续填 tokens.json**
   - 若存在: Read 解析,按 §4.2 把 `total` / `messages` / `harness_overhead` 字段写进 tokens.json
     - `tokens.total` ← context.txt 顶部 `Tokens: X / 1m` 那个 X(单位 k 转数字)
     - `tokens.messages` ← `Messages` 一行
     - `tokens.harness_overhead` ← system_prompt / system_tools / mcp_tools / autocompact_buffer 等分项

3. **Read meta.json / notes.md**,按 §4.2 责任表填 `<FILL_ME>`:
   - 用 Edit 工具替换 `<FILL_ME>` 为实际值
   - `tokens.by_tool_estimate.calls` 必须从 session memory 数,不要瞎编;`tokens.*_estimate.tokens` 字段是相对参考,可估算

4. **核对 geometry.json**:
   - 若 Claude 知道真实 GT 与 counts 不同(例:案例文档声明 14 zones 但 IDF 解析得 13),把 `counts_expected` 改为 GT 值并在 `anomalies` 写明
   - `dimensions_check` 保持 `"pending"`,**留给用户** OpenStudio 验后改

5. **写 notes.md** 的 4 节:
   - 本次目的 (1-2 句)
   - 异常 / 失败点 (掉线、补丁失效等)
   - 与上一 anchor 的差异观察 (token Δ、call Δ、counts 是否一致;**Δ 必须基于 tokens.total 真实值,不用 estimate**)
   - 下次改进候选

6. **报告完成**: 给用户一段 ≤6 行的总结,含: run_dir 路径 / counts / 总 token(从 context.txt) / 与 anchor 比较的关键 Δ / 提醒"OpenStudio 验完改 dimensions_check"。

### 4.4 用户收尾

Claude 报告完成后:
1. OpenStudio 打开 `_source_idf` 路径下的 IDF
2. 检查尺寸是否符合输入图纸(简单 case 目视即可)
3. 截图存进 run 目录(建议命名 `openstudio_3d.png`)
4. 编辑 `geometry.json`: `dimensions_check` 改为 `pass` / `fail` / `partial`、`openstudio_screenshot` 填路径、`anomalies` 补充

### 4.5 半人工流（`pipeline_version=halfmanual_v1`）token 收集差异（2026-05-07 起）

> §4.1 / §4.3 的 `/context` 协议是为旧 `yaml_to_idf_v1`（Opus 单会话全流程）设计的。半人工流下 token 来源**不再单一**，README 流程升级中（plan.md B0''' 任务）。在升级落地前，半人工 case 按下表临时处理：

| token 来源 | 旧流（yaml_to_idf_v1）| 半人工流（halfmanual_v1）|
|---|---|---|
| Opus（intake） | 同一会话 `/context` 顶部 `Tokens:` | **用户主动粘** Step 4 临时会话的 `/context`；不粘则 `tokens.intake_total=null` |
| 下游 9 subagent（DeepSeek）| 不存在 | **API usage**：从 LangSmith trace 或 DeepSeek API 账单收集；本地 `pipeline_run.log` 不直接含 token 计数（待加 hook） |
| 总和（`tokens.total`）| 直接 `/context.Tokens` | `intake_total + downstream_total`（任一缺失则总和为 null）|
| 助手会话（本会话协助跑下游 / 写文档） | 与任务 token 同会话不可分 | 与任务无关，**不计入** `tokens.total`（只是协调成本）|

**临时填法（升级前）**：
- `tokens.total` 留 `null` 不强求
- `tokens.by_phase` 可写 `{"intake_session": <Opus 端 /context 数>, "downstream_api": null}` 留位
- `notes.md` 必须在 §"与上一 anchor 的差异观察" 注明"半人工流 token 计量协议升级前，本 run 不参与 Δ 比较"
- 第一份 anchor：[runs/2026-05-07_sm_16_newarch_v4pro_no_sim_v1/](runs/2026-05-07_sm_16_newarch_v4pro_no_sim_v1/)

**升级目标**：plan.md B0''' "半人工流 token 收集协议" 落地后，§4.1 / §4.3 拆为 `4.3a yaml_to_idf_v1` / `4.3b halfmanual_v1` 两套流程。

---

## 5. 后续扩展占位（明天起讨论）

- [ ] 流程改造为函数包后，`pipeline_version: function_pkg_v1` 起新桶
- [ ] 自动几何 diff 工具（IDF 顶点 vs GT，参考 README §6 讨论）
- [ ] capabilities.yaml + cases/ —— 等 case 数 ≥3 个不同复杂度后再抽
- [ ] `compare.py` —— 跨 run diff（token Δ / counts Δ / dimensions_check Δ）
- [ ] Langfuse 接入 —— case 数 >20 或多模型对比时
