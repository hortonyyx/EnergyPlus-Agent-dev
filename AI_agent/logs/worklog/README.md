# logs/worklog/ —— 翻篇的日更与状态摘要（**归档，⛔ 非活文档**）

> **为什么有这个目录**（2026-08-18 用户令「东西放到该放的地方，不要全挤在这两个管理文档」）：
> `CLAUDE.md` §2 与 `plan.md` 长期把**每日叙述**往里堆 —— 清理前 CLAUDE.md **1658 行**、plan.md **4765 行**，
> 其中绝大部分是已经翻篇的过程记录，导致根文件读不动、当前口径被历史叙述淹没。
>
> **纪律（权威条文 = [CLAUDE.md §0.5 管理文档体量纪律](../../CLAUDE.md)，本节只是它的操作面）**：
> - **当前一轮**的日更留在 [plan.md](../../plan.md)；**当前状态**留在 [CLAUDE.md §2](../../CLAUDE.md)。
> - 一轮翻篇后，日更整段搬到本目录，**逐字不改**，在 plan.md / CLAUDE.md 留一行指针。
> - ⛔ 本目录的内容**不再是权威口径** —— 与 CLAUDE.md / plan.md 冲突处一律以后者为准。

| 文件 | 内容 |
|---|---|
| [`status_digest_to_2026-08-17.md`](status_digest_to_2026-08-17.md) | 原 CLAUDE.md §2 的历史节点摘要（2026-08-17 → 08-02），**摘要层** |
| [`2026-08_plan_log.md`](2026-08_plan_log.md) | 原 plan.md 日更 2026-08-01 → 08-16，**全档层** |
| [`2026-07_plan_log.md`](2026-07_plan_log.md) | 原 plan.md 日更 2026-07-31 + 原「当前焦点」章节正文（07-26 → 07-28） |
| [`2026-06_backlog_closed.md`](2026-06_backlog_closed.md) | 原 plan.md「近期（细）」整节（2026-06 批次，绝大多数已 ✅） |

**什么时候往这里搬**：每轮**收工**时（[CLAUDE.md §5#12](../../CLAUDE.md) 第 ② 步）跑一次
`wc -l AI_agent/CLAUDE.md AI_agent/plan.md` —— CLAUDE.md >400 行 / plan.md >900 行 / plan.md 里还留着上一轮的日更，
三者任一命中就当场搬，⛔ 不留到「以后再整理」。

**找东西的顺序**：先 [plan.md](../../plan.md) / [CLAUDE.md](../../CLAUDE.md) → 找不到再来这里 →
决策级结论看 [decision_log.md](../../decision_log.md) → 某一次跑的实况看 `logs/experiments/` 与 run 目录。
