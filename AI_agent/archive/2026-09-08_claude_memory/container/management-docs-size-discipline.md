---
name: management-docs-size-discipline
description: 管理文档（CLAUDE.md / plan.md）体量纪律——翻篇的日更收工时当场搬进 logs/worklog/，权威条文 = CLAUDE.md §0.5 + §5#12 第②步
metadata:
  type: feedback
---

用户 2026-08-18 令：**「东西放到该放的地方，不要全挤在这两个管理文档」**，并要求写进治理与收工约束长期保持。
⇒ 已落 **CLAUDE.md §0.5（体量纪律，唯一权威）** + **§5#12 收工 ritual 第 ② 步（体量自检）**。

**Why**：清理前 `CLAUDE.md` **1658 行** / `plan.md` **4765 行**，其中 §2 有 1327 行是历史节点叙述、
plan.md 的「当前焦点」整节其实是 7 月的史、「近期（细）」整节是 6 月已完成的 backlog。
⇒ 根文件读不动、**当前口径被历史叙述淹没**，已造成实害：orchestrator 因在长文里读到 §1.5#7 旧条文，
**连续三次**得出「07-07 模式违规、须先实现 reading-agent」的错误结论（见 [[707-mode-accepted-reading-agent-deferred]]）。
⇒ 这不是洁癖，是 [[green-suite-is-a-property-of-tree-and-launcher]] 同类的「通道本身坏了」——
管理文档是换会话后**唯一**的跨会话通道，故 ⛔ 不适用 §0.1「能跑就不做」的登记不做
（见 [[research-first-p0-is-speed-not-completeness]]）。

**How to apply**：
- 每轮**收工**跑 `wc -l AI_agent/CLAUDE.md AI_agent/plan.md`：**CLAUDE.md >400 / plan.md >900 / plan.md 里还留着上一轮日更** ⇒ 当场搬，⛔ 不留到「以后再整理」。
- 搬家三步：① **逐字**搬进 `AI_agent/logs/worklog/YYYY-MM_plan_log.md`（⛔ 不改写不总结）② 原处只留一行指针 ③ 修相对链接层级（深两级补 `../../`）+ 机械对账「搬走的每行都在新文件里」。
- 超标时**先搬上一轮**；仍超 ⇒ 是本轮日更写太长 ⇒ 逐条经过归 run 目录 / `logs/experiments/`，plan.md 只留结论+指针。⛔ 不许调大限额。
- 验收判据（唯一）：**新接手的模型只读这两份，能否五分钟说出「卡在哪 / 下一步 / 什么明确不做」**。
- 同族归位：操作手册进 `guides/`（如角色矩阵长条已从 §5#8 搬回 codex_execution_protocol）· 能力主线进 `capability/`（§1.5#7 整包已搬进 reading 专项 §8）· 过程痕迹进 `logs/`（[[logs-reorg-process-only]]、[[no-stray-files-in-repo-root]]）。
