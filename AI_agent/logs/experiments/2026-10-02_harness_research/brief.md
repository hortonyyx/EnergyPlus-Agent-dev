# 派工：Agent 运行底座（harness）调研

派工人：Opus 5.5（还原建模负责人，本会话由用户直接安排）。用户要求：“这部分你派 Astra 去调研，回来之后你们先讨论，然后我拍板开做”。本次只做调研与设计建议，不写代码、不改仓库；你回来后我们先讨论，再交用户拍板。

## 背景（请先读）

- `AI_agent/Agent.md`（项目入口与权限）。
- `AI_agent/logs/worklog/2026-10-02_reconstruction_discussion.md`：今天用户与 Opus 的讨论结论。要点：工作模型现在就换、不再等 Sonnet 恢复（09-27 起 Sonnet 同请求思考量约 5 倍，修复包跨例与重复都出严重错误，开发模型用同一套工具亲做三例基本达标）；底座先调研再设计；暂不实跑。
- 现状：工作模型（含 09-30 GLM 试跑）都经 Claude Code CLI 运行，入口 `scripts/tool_scripts/run_bim_agent.py`；开发模型调用同一套 BIM 工具用 `scripts/tool_scripts/bim_agent_bridge.py`。模型服务和 Claude Code 后台配置都不在我们控制内。
- 已有自有原型：`src/agent/execution/chat_mcp.py`（约 220 行，35 项离线检查，只用过测试桩，无上下文压缩）、`src/agent/model_routes.py`、`src/configs/model_roles_paratera.yaml`、设计说明 `AI_agent/design/model_configuration.md`。
- 10-01 完整行为记录规则见 `AI_agent/workflow/development.md`“用实际行为解释质量”一节；脚本在分支 `dev/opus-guidance-recovery-20260929` 的 `AI_agent/logs/experiments/2026-10-01_behaviour_records/record.py`（可用 `git show` 读）。
- 总体架构 `AI_agent/design/architecture.md`、部分推理框架 `AI_agent/design/partial_inference_framework_start.md`、模型约定 `AI_agent/workflow/models.md` 顶部几条，按需读。

## 用户对底座的要求

1. 轻量、专为本项目服务；以后可作为成果开源。
2. 覆盖目前暂定的三类路线（还原、部分推理、完全推理），但不一定是三套系统，只是目前大概这么分。
3. 支持多子代理（subagent）系统：按角色分，不按模型分；角色可接模型，可有默认和推荐，但不指定死。
4. 模型、底座、推理参数都能锁版本；模型看到的每个字由我们掌控。
5. 目标档：Qwen 27B 这类可本地部署模型为主力，Flash 档辅助；产品支持用户自接模型和服务器多模型调度。
6. 初期可由开发模型（强模型）调度 27B 完成任务，之后再看能否把开发模型换成工作档。底座要支持这种“强模型调度弱模型”，记录里分清各模型分别做了什么。
7. 每次运行生成完整行为记录（逐步工具调用参数与返回、可见文字、思考量或内容、用量）。
8. 今天定的几何规整（对齐、容差）属于工具层，不是底座本身；但底座要承载“确定性工具负责计算、模型负责裁决”的分工。

## 调研对象

源码已浅克隆到 `/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/0da38f9c-6318-47d6-9216-09532d64ea88/scratchpad/harness_repos/`（只读）：

- `pi`（earendil-works/pi，MIT，TypeScript；0.99 版刚加 MCP，走 Codemode）
- `deepseek-harness`（MIT，v0.1 开发者预览，插件微内核）
- `codex`（openai/codex，Apache-2.0，Rust）
- `qwen-code`（QwenLM，目标模型同家族）
- `mini-swe-agent`（极简 Python 参照）

另：Claude Code 不开源（公开仓库只有插件、示例和问题追踪，许可证为保留所有权利），只看官方公开文档和 Claude Agent SDK 文档，不要使用 3 月泄露的源码。其他方案（OpenHands、opencode、Goose、smolagents、Gemini CLI 等）只在确有借鉴价值时简要提及。

## 比较维度

1. 模型可见内容的掌控：系统提示、工具说明、中途注入的提醒能否完全自定义；默认注入了什么。
2. 工具调用：直接调用还是写代码调用；MCP；工具返回的图片能否送回模型（我们的建模工具大量返回图片）；并行调用。
3. 多模型：接口抽象；OpenAI 兼容与本地部署（vLLM 等）；思考字段处理；跨模型续接；按角色独立配置。
4. 多子代理：角色怎么定义、上下文隔离、结果回传、并发；能否让一个模型把带图子任务交给另一个模型并核对。
5. 长任务上下文管理：压缩、摘要、丢旧图的策略和可配置性（我们一次运行有 60–120 次工具调用、大量图片）。
6. 记录与可复现：完整轨迹导出、会话持久化、重放。
7. 预算与停止：token、时间、调用次数上限，出错与重试。
8. 版本与稳定性：发布节奏、破坏性变更、依赖体量、许可证。
9. 与我们的衔接成本：语言、能否作为库嵌入、和我们的 Python MCP 工具及评价链的衔接。
10. 规模：核心代码量（数关键目录的行数）。

同样按这些维度评估我们的原型，列出缺口。

## 交付

最终回复就是完整报告（程序会把它存成文件），中文、白话，必要术语加一句解释。正文控制在一次能读完的长度（约 4000–8000 字），细节放附表：

1. 一页结论：每个方案一句话定位，以及对我们的价值（借鉴什么、能否直接用）。
2. 对比表（按上面的维度）。
3. 对我们自有底座的设计建议：组件与边界、角色和子代理模型、上下文策略、记录格式、与现有工具和运行器的衔接、分阶段实施与工作量粗估；写明哪些借鉴自哪个项目。
4. 风险与未决问题：需要和 Opus 讨论的点、需要用户拍板的点。
5. 来源：网址和本地源码路径（文件:行）；官方声明、源码核实和推断分开标注。

## 约束

- 只读，不改仓库；不派子代理。
- 除网页搜索外不调用任何模型或付费 API；不调用 DeepSeek（研究 DeepSeek Harness 只读代码和文档，不运行）；不运行克隆仓库里的代码。
- 不确定的写“未核实”，不要用推测填空。
