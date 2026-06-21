# Codex 执行协作规约（Claude 编排 / Codex 执行）

> **目的**：用户有 Claude + Codex 两个订阅、各自 5h 重置窗口。本项目坚持 **Claude 主控开发**（保质量 + 记忆单一权威），但把**执行**尽量派 Codex——Codex 的模型推理算在 **Codex 额度**上，Claude 只花在「写 spec + 审 diff + 读简报」，从而省 Claude 上下文 + 拉长每周期可开发时间。
> 本文 = 操作手册；核心约定同时收录在 [../CLAUDE.md](../CLAUDE.md) §5。换主控模型读此接手。

## 1. 分工

- **Claude 主控（judgment 重、上下文便宜）**：架构决策、任务拆解、写 spec、审 git diff、judge②、改 memory + 管理文档、碰 5 条铁律/IntakeOutput 契约的判断题、git commit。
- **Codex 执行（已 spec 清楚、上下文重）**：按 spec 改代码 + 跑 pytest、为具体问题做探索式 read/grep（回 digest）、CLI 看图出 0_reading、per-stage 管线执行（run_stage）。**派不派、派哪个模型/sandbox 由主控按任务动态决定**（目标=保质量 + 减 Claude 消耗，非定死规则）。

## 2. 省上下文的四条机制（决定省得多不省）

1. **不在 prompt 里塞大文件**——给 Codex 文件路径，让它自己读盘；Claude 基本不再亲自 Read 大文件。
2. **产出走磁盘**——Codex 直接改工作树 + 详细日志/报告写文件；**回主对话只给简报**（X passed / 改了哪几个文件 / 关键结论 / 偏差 / **审阅需求**）。明确要求「Reply INLINE with ONLY a terse report, do NOT paste diffs/file contents」，且**简报必含「审阅需求(review-ask)」段**：Codex 自报哪些处它没把握 / 做了判断取舍 / 动了风险点或不变量、建议 Claude 复核（无则注明「none — routine spec'd execution」），并诚实标注不确定、不得过度自信。
3. **Claude 审 `git diff`**（自己跑，便宜），不让 Codex 回贴文件内容。
4. **多步迭代用 `codex-reply` 续同一 session**——context 留 Codex 侧，Claude 只发短追问。

## 3. 通道与参数

- **MCP `mcp__codex__codex` / `mcp__codex__codex-reply`**（主力）：session 持久（`threadId` 续），适合「写代码+跑测」多步执行 + 方案审阅。
- **CLI `codex exec -i <图>`**（看图专用）：MCP 无图像参数，识图/读平面立面必须走 CLI；大输出 redirect 到文件读 tail；坑=后台进程 stdin 不 EOF 致 codex 死等干耗（额度不掉），用 `echo "" | codex …` 喂 EOF。
- **模型/effort（宜高不宜低）**：Codex 额度充裕，执行/审阅都用高 tier。本机 `~/.codex/config.toml` 默认 `model=gpt-5.5` + `model_reasoning_effort=xhigh`，本项目 `trust_level=trusted`——直接继承默认即高 tier，无需显式降级。

## 4. 本机沙箱校准（硬坑，2026-06-21 实测）

- **read-only / workspace-write 两档不可用**：会去起 bwrap 沙箱，本机内核禁 userns 起不来，于是**静默回退去读 GitHub @main**（给的行号是远端、与本地分支不一致、不可信）。
  → **凡需碰本地文件的 Codex MCP 调用，一律 `sandbox=danger-full-access`**（它跳过沙箱、不走 bwrap）。这也是 review 一直用 full-access 的原因。
- **sandbox 在建 thread 时定死**：`codex-reply` 续会话**不能改 sandbox**（参数里没有）。想换权限→**新开 `codex` 会话**。
- 全自主执行：`approval-policy=never`（不打断），靠 Claude 审 diff 兜底。

## 5. 节点审阅方向（反转，替代旧 §5#8「Codex 审 Claude」）

现以 Claude 主导出方案、Codex 主执行，故审阅链反转：

```
Claude 出方案 → Codex 审方案（adversarial，落 review/）→ Claude 裁决（不盲从）
  → 派 Codex 执行器实现（简报含「审阅需求」自报需复核处）
  → Claude 按 review-ask 复核 + 大节点全面审 → commit
```

- **执行结果不逐次全审**：Claude 把 Codex 当**可靠执行工具**，由 Codex 在简报「审阅需求」里**自决**哪些要 Claude 再核；Claude 只复核被 escalate 的处，**routine spec'd 执行直接采信**（逐次全审会抵消省消耗的初衷）。
- **大节点才全面审**：里程碑 commit 前的实质改动、集成接缝、碰 5 条铁律/IntakeOutput 契约的改动、或 Codex escalate 不确定时 → Claude 全面审（含自跑 pytest + 逐行审 + 端到端回归）。
- **方案类决策双审后再派**：Claude 拟方案 + Codex 审 + Claude 裁决（= 双审），无 BLOCKER 才 dispatch 给执行 Agent。
- **审计留痕**：`logs/review/request/<date>_<topic>_request.md` = Claude 方案（含 v2/v2.1 revise 演进）；`logs/review/review/<date>_<topic>_review.md` = Codex 审（含二审）。
- 方案 revise 多轮时用 `codex-reply` 续同会话二审（Codex 已加载方案+代码，省上下文）。

## 6. 信任边界：Codex 当可靠执行工具，escalation + 大节点驱动复核

核心：**把 Codex 当一个可靠的执行工具**，常规执行直接采信、由它自报哪些需复核；Claude 的核验集中在「判断题」和「大节点」，不摊到每一步（否则不省消耗）。

- **执行结果不逐次审**：采信 Codex 简报的测试数字与结论；只复核它「审阅需求」里 escalate 的处。**大节点**（里程碑 commit 前实质改动 / 碰铁律/契约 / Codex 报不确定）才全面审（自跑 pytest + 逐行审 diff + 端到端回归，如 sm21 面数）。
- **判断题仍 Claude 自持**（这些便宜且是质量命门，不外包）：① 方案地基事实（根因定位、不变量）动方案前 Claude 亲自**聚焦** read 确认；② Codex 给 REWORK/critique 时逐条裁决（采纳/校准/反驳），不照单全收（例：本轮把 tol 0.20 校准为 0.11、flag 路由 unsupported→advisory）。
- **让 Codex 诚实自报**：执行 prompt 要求简报含「审阅需求」段，明令标注不确定/判断取舍/动了风险点，不得过度自信——Claude 的复核精度取决于此。

## 7. 守质量 + 记忆一致的铁律

- **memory + 管理文档只 Claude 写**（CLAUDE.md §5#1）→ Codex 永不碰，杜绝「各自记忆不同步」。
- **git commit 只 Claude**（§5#7）；Codex 改工作树**绝不** commit/push。
- **改 src 前 Claude 先备份**（§5#4，`backup/src_history/<date>_<reason>/`），git clean 之外再加一层。
- Codex 只做**已 spec 清楚的执行**，不做开放式设计；碰铁律/契约/judge verdict 的判断题留 Claude。

## 8. 一轮完整范例（P0#1 跨层墙对齐，2026-06-21）

1. Claude 兜底读 `deterministic.py` 核实根因 → 写方案落 `request/`。
2. Codex full-access 审方案 → REWORK（3 DISAGREE + 2 BLOCKER，落 `review/`）。
3. Claude 裁决采纳 + 校准 → v2.1 spec；`codex-reply` 二审 → APPROVE-WITH-CHANGES 无 BLOCKER。
4. Claude 备份 src → 派 Codex full-access 执行器实现（默认 gpt-5.5/xhigh）→ 回简报 281 passed。
5. Claude 自验：审 diff 逐行 + 自跑 pytest 281 + 读新测非空 + sm21 端到端 112→100。
6. Claude 同步 plan/decision_log/memory + commit。
