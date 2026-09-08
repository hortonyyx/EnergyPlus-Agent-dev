---
name: DeepSeek v4-pro thinking 默认关闭
description: 多轮 tool-calling 时 langchain_openai 不会回传 reasoning_content，必须在 llm.yaml 关掉 thinking
type: feedback
originSessionId: 7dd08f4a-2004-433d-a281-03e9103623c8
---
DeepSeek v4-pro / v4-flash 在 thinking 模式下要求多轮对话把上一轮 `reasoning_content` 回传 API；`langchain_openai` 标准 `ChatOpenAI` 不知道这个 DeepSeek 私有字段，第二轮 ReAct tool result 回灌时丢字段 → API 400：`The reasoning_content in the thinking mode must be passed back to the API.`

**Why:** 2026-05-07 sm_16_newarch 端到端首跑实测，phase 1 material_agent 第二轮 tool result 回灌即 400。单 turn intake capability test（2026-05-06）不暴露此 bug，多轮 ReAct（9 个下游 subagent）必踩。

**How to apply:**
- `src/configs/llm.yaml` `default` section 必须保留 `extra_body.thinking.type=disabled`，不要轻易删
- 修改下游模型配置时确认这一行还在；`intake` section 走 Anthropic 不受影响
- 升级路径：等 surface T-vertex bug（plan.md B0'）修了仍翻车 → 写 `ChatOpenAI` 子类回传 `reasoning_content`（约 30 行）；不要乱删 thinking-off 切换到 thinking-on
- 能力影响：v4-pro 关 thinking ≈ v4-flash 非 thinking；CRUD 类 subagent 够用，瓶颈在 surface 几何（已证）
