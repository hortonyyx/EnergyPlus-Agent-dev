---
name: run-provenance-recording-requirement
description: 用户定硬纪律——每 run 必须详记全链路模型配置 + 脚手架/skill 状态，否则回归归因卡死
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8251d8f3-807b-45b8-9d57-e1f642586016
---

**2026-06-24 用户定**：之后每个 run **必须详细记录全链路模型配置 + 脚手架/skill 状态**，否则回头定位问题（尤其识图回归归因）非常麻烦。

**Why**：这次 reading-honest 回归诊断卡在「`sm21_pre`（06-09）那份识图是 Sonnet 还是 Opus、旧 schema 还是新 schema」无法从产物坐实——产物无 model 字段、无 skill/schema 版本戳，只能靠 decision_log 文档推（软证据），逼得要靠 A/B 控变量才能证明。讽刺的是 `fa04ef6` commit message 当时已写「Component 2 (persist manual 0_reading prompt/model) deferred」——缺口早识别、被推迟，这次教训坐实该补。

**How to apply**：两块缺口要在 run 记账（record_baseline / `_run/` 元数据）里补齐——
1. **全链路模型配置**：`llm.yaml` 只记 correction/mep/下游，**reading 模型没记**（注释写"人工/会话不经 API 无需配置"——正是归因最关键变量）。要补 **reading 模型 + effort/ladder + 主控 orchestrator 模型**。
2. **脚手架/skill 状态**：run 产物无 git SHA、无 skill 版本。要戳 **git HEAD SHA + dirty flag**，且因 skill 可能有未提交改动，理想是连 `skills/intake_pipeline/` + `src/agent/reading/` 的**内容哈希**一起记（这样"这 run 跑在 reading-honest 之前/之后"事后可硬证）。

落点 = `record_baseline` 写 `baseline.json` 时 stamp 这些字段；归校验架构 provenance。等 sm24 看完、不急做（用户定"修可慢慢修"）。详 plan.md。相关 [[reading-quality-investigation-2026-06-24]] [[reading-honest-judge-routing-architecture]] [[contamination-hard-isolation-requirement]]。

**⚠️ 2026-07-03 又栽一次（教训坐实、升级要求）**：sm21 正规重跑（`run_2026-07-02_sonnet_flow_e2e`）我用 Agent tool `model="sonnet"` 冷启 reading 子代理，**别名默默解析到最新 = Sonnet 5（`claude-sonnet-5`）、不是历史 sm21 全用的 Sonnet 4.6**，我 llm.yaml 头只写"cold-start Sonnet"没钉具体型号。结果窗 15/15 的大提升**归因被污染**（4.6→5 模型升级 vs 脚手架恢复无法隔离）。**新硬要求：模型一定要确认到具体型号 `model_id`**——用别名 spawn 子代理时，别名会随时间漂移到最新，必须在 run 溯源里钉死实际 model_id（reading 也要进 `baseline.models`，现只记 correction/default）。**用户 2026-07-03 把「跑前全流程模型配置确认点 + 型号钉死」列入下轮流程清理批次**（连同 run 根目录配置文件 run_config.yaml）。相关 [[standardize-test-flow-and-judge-arch]]。
