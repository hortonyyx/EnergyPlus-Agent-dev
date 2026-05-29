# 开源 VLM 手动测试指南

> 面向**用开源多模态模型**（Qwen3.5-35B-A3B、Qwen2.5-VL-32B、InternVL 等）
> 手动跑 EnergyPlus-Agent 流水线的操作手册。
>
> 闭源基线（Claude Opus）用 [../guides/new_case_guide.md](../guides/new_case_guide.md) + [../../skills/energyplus_mcp](../../skills/energyplus_mcp) intake 规则文档库；
> 本文只覆盖「开源模型专用」的差异步骤。

---

## 0. 何时走本指南

| 场景 | 该用的文档 |
|---|---|
| 用 Claude Opus 跑一个案例 | [../guides/new_case_guide.md](../guides/new_case_guide.md) |
| 用开源 VLM（Continue / vLLM）跑一个案例 | **本文** + [../guides/new_case_guide.md](../guides/new_case_guide.md) §1–§3（素材准备） |
| 自动化评测（跨模型对比） | 等 [plan.md P0](../plan.md) 的 `AI_agent/eval/run_case.py` 落地 |

两条流水线共用案例目录、`testdata_prompt.json`、MCP 工具；分叉在**提示词、图像预处理、会话节奏**三处。

---

## 1. 为什么有这条分叉

在 2026-04-22 的 SiliconFlow L0 档（RPM=1000, **TPM=40k**）上用 Qwen3.5-35B-A3B 实测踩到的坑：

| 现象 | 根因 |
|---|---|
| 图像读取失败 → LLM 改写 Python 脚本处理图 | Continue 把大图 base64 传过去前就超 TPM / 单请求 body 上限 |
| 一轮几千 tokens 的 tool-call 历史累积到几轮就触发 TPM | 40k 的 per-minute 硬上限 |
| `filepath argument has issue with whitespace` | 开源模型在 Windows 中文+空格路径上 escape 不稳 |
| 多步 tool-call 中途忘记 Fenestration 步 | 长 skill 文档 + 长历史让"工作记忆"衰减 |

**应对策略**：
1. 把图缩小到合理大小再喂模型（§3）
2. 开源模型专用流程仍沿用旧的瘦身 + 分步几何 skill（当前主仓已移除 `open_model/` 目录，使用时应参考历史备份或后续重建版；见 [Skill_history/](../../Skill_history)）
3. 路径软链到纯 ASCII 目录（§2.4）
4. 一次只让模型做一步，人工确认后放行（§5）

---

## 2. 前置准备

### 2.1 API key 安全

- **永远不要**把 `sk-...` 粘贴到 Claude / ChatGPT / 任何第三方对话
- 配置文件里的 key 用环境变量或 `~/.continue/config.yaml`（仅本机可读）
- 已泄露的 key 立即去 [SiliconFlow 后台](https://cloud.siliconflow.cn/account/ak) 撤销重新生成

### 2.2 Continue 配置（L0 tier 推荐）

```yaml
name: Local Config
version: 1.0.0
schema: v1
models:
  - name: Qwen3.5-35B-A3B VLM
    provider: openai
    apiBase: https://api.siliconflow.cn/v1
    model: Qwen/Qwen3.5-35B-A3B
    apiKey: <your_siliconflow_key>
    defaultCompletionOptions:
      contextLength: 32768   # 不要放到 256K;L0 TPM=40k,单次请求超 40k 必失败
      maxTokens: 4096        # 输出也算 TPM;留足 input 余量
    roles:
      - chat
```

**单次请求 token 预算（必须 ≤ 36k，留 10% TPM 余量）**：

| 项 | tokens |
|---|---|
| 图像（5 张预处理后） | ~8,600 |
| 系统 prompt + skill | ~6,000–8,000 |
| tool schema | ~2,000 |
| 对话历史 | ~14,000 |
| `maxTokens` 预留输出 | 4,096 |
| **Total** | **~35,000** |

升 Pro tier 后（TPM 一般到 200k–1M），可把 `contextLength` 提到 `131072` 或 `262144`。

### 2.3 仓库侧无特殊改动

MCP server 启动方式与 Opus 流水线一致（参见 [new_case_guide.md §4](../guides/new_case_guide.md)）。
开源模型通过 Continue 连 MCP 时，在 Continue 里把 [`../.mcp.json`](../../.mcp.json) 挂到工作区。

### 2.4 中文路径规避（推荐）

项目根路径 `c:\Users\Horton\Desktop\科研2\EnergyPlus-Agent-dev` 含中文+空格，
会让开源模型在返回文件路径时 escape 出错。管理员 PowerShell 建一个 ASCII 软链：

```powershell
New-Item -ItemType SymbolicLink -Path "C:\work\ep-agent" `
  -Target "c:\Users\Horton\Desktop\科研2\EnergyPlus-Agent-dev"
```

Continue 的 workspace 打开 `C:\work\ep-agent` 即可。脚本里用到的所有相对路径保持不变。

---

## 3. 图像预处理（强制步骤）

开源模型会话开始前，**必须**为每个案例跑一次预处理（`<case_dir>` 替换成实际案例路径，
例如 `test_data/SmallOffice/smalloffice_14`）：

```bash
python Tool_scripts/preprocess_images.py <case_dir>
```

该脚本：
- 裁掉图外围的白色页边（保留外围尺寸链，CLAUDE.md §7.5.4 强约束）
- 把长边限制到合理尺寸（top_view ≤ 1536 px，立面图 ≤ 1024 px）
- 产物写到 `<case_dir>/output/preprocessed/`：5–7 张 PNG + `manifest.json`
- `manifest.json` 记录每张图的视觉 token 预估，便于核对 TPM 预算

### 3.1 参数调优（当主视图尺寸链被裁）

默认参数（阈值 248 / padding 24）对 sm_13 工作良好。如果发现某张图主体或尺寸链被裁：

```bash
# 阈值调更高（更保守，只裁近纯白）
python Tool_scripts/preprocess_images.py <case> --trim-threshold 252

# 加大保留边距
python Tool_scripts/preprocess_images.py <case> --trim-padding 40

# 完全跳过裁白边
python Tool_scripts/preprocess_images.py <case> --no-trim
```

### 3.2 覆盖式重跑

脚本每次运行都会覆盖 `output/preprocessed/` 里的同名文件和 `manifest.json`，
不会追加污染。放心重跑直到满意。

---

## 4. 启动会话流程

### 4.1 在 Continue 打开工作区 + 挂 MCP

Continue **不读仓库根的 `.mcp.json`**（那是 Claude Code / Claude Desktop 的格式），
必须在 Continue 自己的 `~/.continue/config.yaml` 里用 YAML 列表格式的 `mcpServers` 段。

1. 在 VSCode 打开工作区：`C:\work\ep-agent`（若做了 §2.4 软链）或仓库原路径
2. 编辑 `~/.continue/config.yaml`，在文件末尾追加：
   ```yaml
   mcpServers:
     - name: EnergyPlus-Agent
       command: uv
       args:
         - --directory
         - C:/Users/Horton/Desktop/科研2/EnergyPlus-Agent-dev  # 或 C:/work/ep-agent
         - run
         - python
         - main.py
         - mcp-server
         - --transport
         - stdio
   ```
3. `Ctrl+Shift+P` → `Developer: Reload Window`（Continue 完整重载后才会读 config）
4. **切到 Agent 模式**（MCP 工具只在 Agent 模式下可见，Chat 模式看不到）
5. 选模型 `Qwen3.5-35B-A3B VLM`
6. 验证挂载成功（任选）：
   - 在 Chat 输入 `@`,看是否有 `EnergyPlus-Agent` / `create_zone` 等条目
   - 查看 VSCode `View → Output → Continue`,启动日志应显示 MCP server 连接成功

**挂不上的备选方案（HTTP transport）**:终端手动起
```bash
uv run python main.py mcp-server --transport http --host 127.0.0.1 --port 8765
```
配置改为:
```yaml
mcpServers:
  - name: EnergyPlus-Agent
    url: http://127.0.0.1:8765
```
代价是每次用都要保持终端窗口开着。

### 4.2 第一轮 prompt 模板

**关键前置步骤**:Continue 不会自动把路径当图像读取——必须用 `@Files` 菜单
把 `<case_dir>/output/preprocessed/` 下的每张 PNG 显式附加为 attachment
(点输入框的 `@` → 选 `Files` → 选 PNG),聊天框上方出现缩略图才算成功附加。
同时附加 skill 文档。

附加的 image attachments 至少包含:
- `top_view.png`(必需)
- `{South|North|East|West}_view.png` 中 JSON 里路径非空的那几张
- `supp_plan.png`(可选)

然后发送下面的文本(`<case_dir>` 替换为实际路径,如
`test_data/SmallOffice/smalloffice_14`):

````text
请按以下历史 open-model skill 文档完成 EnergyPlus IDF 构建,严格遵守 §0 的硬约束
(一次一步、不要写 Python 画标注图、不要用 read_file 读 PNG)。

skill 文档(从 `Skill_history/` 历史备份中读取):
@Skill_history/2026-05-10_energyplus_mcp_pre_intake_doclib/open_model/energyplus_mcp_prompt.md

案例目录:<case_dir>
图像已作为 chat attachments 随本消息附上,共 N 张(top_view + 立面图)。

请从 Step 0 开始:
1. 确认我附上了哪些图(Preprocessed views attached: ...)
2. 读 <case_dir>/testdata_prompt.json
3. 读 <case_dir>/output/preprocessed/manifest.json
一句话总结后停,等我说"继续"再进 Step 1。
````

**关键点**：
- 读取的是 `Skill_history/.../open_model/energyplus_mcp_prompt.md` 历史瘦身版，
  **不是**当前 `skills/energyplus_mcp/` 下的 intake 规则文档库
- `zonetool_prompt.md` 和 `schedule_compact_guide.md` 让模型自己在用到时再读
  （skill §0 hard constraint #6）；**不要**第一轮就投这俩
- 明确写出"从 Step 0 开始"，防止模型一轮跳多步

### 4.3 逐步放行

- 每个 tool-call 返回后，模型应该吐一句总结 + 下一步意图
- 人工看一眼"下一步意图"是否跟 skill 的 Step 流程一致，OK 就回 `继续`
- 发现模型走偏（例如跳过 list_*、或想一次 create 多个 zone），立即打断：
  > 停。回到 Step X。按 skill 规定一次只做一步。

---

## 5. TPM 节流策略

L0 tier 单次 ~35k + 60s 窗口 = 实际每分钟只能走 **1 次完整请求**。
Continue 默认行为会把整个对话历史 + 完整 system prompt 每轮重发，累积很快打穿。

### 5.1 主动收缩历史

当看到 Continue 右下角 token 计数接近 28k 时：
1. 让模型写 `output/run_log.md`，记录已完成的步骤 + 下一步计划
2. **新开一个 Continue 会话**（清历史）
3. 第一轮 prompt 变为（`<case_dir>` 替换成实际路径）：
   ````text
   @Skill_history/2026-05-10_energyplus_mcp_pre_intake_doclib/open_model/energyplus_mcp_prompt.md
   @<case_dir>/output/run_log.md

   从 run_log 记录的下一步继续。
   ````

### 5.2 429 / rate-limit 恢复

- Continue 报 429 → 等 60s 再手动 `继续`
- 连续 429 → 说明上次请求过大，去 §5.1 主动收缩

### 5.3 升 Pro 的判断

L0 单案例跑下来约 15–25 次独立请求 × 每分钟 1 次 = 20–30 分钟，还要加上 429 重试。
如果打算跑 13+ 个案例的批量评测（[plan.md P0](../plan.md)），**建议直接升 Pro** —
节省的人工守候成本远大于月费。

---

## 6. 常见错误排查

| 错误 | 原因 | 处理 |
|---|---|---|
| `RateLimitError 429` | 单次请求 + 历史 > 40k tokens | §5.1 收缩历史 |
| `filepath argument has issue with whitespace` | 模型返回带中文/空格路径未 escape | §2.4 软链 ASCII 目录 |
| 模型说 "image files are too large to read directly" | 读了原图而不是预处理后的 | Step 0 漏判：检查 `output/preprocessed/manifest.json` 是否存在 |
| 模型开始写 `process_images.py` 之类脚本 | 违反 skill §0 hard constraint #3 | 打断，指向 §0 #3 重新下指令 |
| `mcp__EnergyPlus-Agent__*` 工具不可见 | MCP server 未挂载 | 检查 Continue MCP 面板；确认仓库根有 `.mcp.json` |
| 模型一轮吐多个 `create_zone` 调用 | 违反 §0 hard constraint #4 | 打断：「一次只调一个工具，等返回再下一步」 |
| 模型跳过 Fenestration 步 | 历史累积后忘记 Step 8 | §5.1 新会话带 `run_log.md` 续跑，重点引用 Step 8 |
| `validate_config` 报 construction 引用不存在 | Step 6 漏创建 `Ext_Window` | 回到 Step 6 补 `create_construction` |

---

## 7. 会话结束后的留痕

一次实验跑完，产出应归档到：

```
AI_agent/experiments/<YYYY-MM-DD>_<model-short>/
├── transcript.md           # Continue 导出的对话记录
├── result.json             # 5 档指标 + 子系统覆盖度(参见 new_case_guide §6.2 / §6.3)
├── decision.md             # 本轮踩坑、偏离、下次改进点
└── <case_name>/
    ├── preprocessed_manifest.json   # 从 output/preprocessed/ 复制
    ├── claude_ep.md                 # 从 <case>/output/ 复制
    ├── <case>.yaml
    └── run_log.md
```

`decision.md` 的作用是攒**每个模型的能力画像**（视觉准确度、tool-call 稳定性、路径处理、长链路保持），用于 [pivot_criteria.md](pivot_criteria.md) 的四象限判定。

---

## 8. 与 Opus 基线的对照

跑同一个案例时，Opus 和开源模型的产出目录结构一致，可直接 diff：

```bash
# Opus baseline produced 里
test_data/SmallOffice/smalloffice_13/output/
  claude_ep.md / smalloffice_13.yaml / smalloffice_13.idf

# Open-source 实验里（在 experiments/ 下复制一份）
AI_agent/experiments/2026-04-22_qwen35/smalloffice_13/
  claude_ep.md / smalloffice_13.yaml
```

对照维度（参考 [pivot_criteria.md §1](pivot_criteria.md)）：
1. Dimension Extraction 数字精确度
2. Zone 数量匹配率
3. 坐标表与 Fenestration Table 完整度
4. YAML 通过 `validate_config`
5. IDF 成功生成（含 4 条修复补丁）
6. EP 仿真 Fatal/Severe 数

---

## 9. 未来工作（不在本指南覆盖范围）

- ~~`AI_agent/tools/export_idf.py`~~ — **已完成（2026-04-27）**：脚本落地为
  [../../Tool_scripts/export_idf.py](../../Tool_scripts/export_idf.py)，含 5 条补丁
  （多了占位 Construction 预注入），主 skill 与 open_model skill 的 IDF 导出步骤
  已改为单行 `python Tool_scripts/export_idf.py <case_dir>`。
- `AI_agent/eval/run_case.py` — 自动化评测，不再需要本指南的手动放行（[plan.md P0](../plan.md)）
- vLLM 本地部署（摆脱 SiliconFlow TPM 约束）的 `AI_agent/deploy/` 脚本

---

_最后更新：2026-04-22（首版；针对 SiliconFlow L0 tier + Qwen3.5-35B-A3B）_
