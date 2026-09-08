---
name: 主动调度 DeepSeek 做适合的子任务
description: 用户希望 Claude 定位为架构师+监工，自主判断哪些子任务该外派给 DeepSeek 以加快进度、降低成本
type: feedback
originSessionId: 2f29c1f2-5734-4e74-8f34-8053b6ea2e7f
---
用户希望我把自己定位为**架构师 + 监工**，主动评估子任务类型/难度，自主调用 `deepseek-bridge` MCP（`deepseek_ask` / `deepseek_execute` / `deepseek_review`）外派合适工作，不要每件事都亲自做。

**Why**：用户说项目进展会更快、成本也更低。这是 2026-05-05 会话末尾的明确指令，针对的是我此前一整次会话（解码 LangSmith trace + 升级 idfpy + 写 architecture.md / plan.md）全程没用 DeepSeek、错失 review 机会的反思。

**How to apply** — 默认外派 / 默认自做的判断规则：

**应该外派给 DeepSeek**：
- **review 落盘前的重要文档** — 特别是 `AI_agent/*.md` 这类要长期参考的文档；落盘前用 `deepseek_review` 找盲点
- **review 重要 commit 前的代码改动** — 跨文件、>50 行、或动核心模块的 commit
- **大段非结构化文本理解** — paper、长 blog、长设计稿；多文件相似形态文本中 grep 解决不了的语义抽取
- **自包含代码生成** — 需求已 spec 清楚的算法 / 转换函数 / 评测脚本（如 `intake_diff.py` 这种 B2 任务）
- **sanity-check 我把握不大的技术声明** — 用 `deepseek_ask` 第二视角验证

**不该外派**（自己做更快）：
- 需要本会话上下文 / 文件系统状态的事（git / 当前 todo / 用户刚才说的话）
- 小改动（一两文件 / <30 行 edit / 重命名 / 改文档措辞）
- shell / build / file IO 操作
- 架构 + 优先级 + scope 决策（监工本职，不能下放）
- 用户明确说"你来做"的事

**实践细节**：
- `deepseek-bridge` 是 deferred MCP，调用前用 `ToolSearch query="select:mcp__deepseek-bridge__deepseek_review,..."` 加载 schema
- 外派前把上下文给足（不能只丢"review 这份文档"，要带项目背景 + review 重点）
- 外派结果**我自己再过一遍**才落盘 / 给用户——监工不替结果背书前不能签字

**触发清单**（自检用）：
- [ ] 我现在写的东西要落盘吗？要 → review 候选
- [ ] 我要做的事是几十次重复模式抽取吗？是 → 看 grep 能不能干，不能就外派
- [ ] 这是个独立函数/脚本吗？是 → execute 候选
- [ ] 我对刚说的技术声明 100% 确定吗？不是 → ask 候选
