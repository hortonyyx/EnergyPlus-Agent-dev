---
name: sm24-e2e-blocked-reading-judge
description: sm24 端到端第一次尝试卡在识图判卷门（2026-07-30）——v3 判卷层对 reading 阶段无投影无守卫，任何 v3 答案 case 识图必崩；用户拍板先停、修好再跑复验
metadata: 
  node_type: memory
  type: project
  originSessionId: c02036eb-681e-4abb-8620-709bcd18989a
  modified: 2026-07-30T16:09:21.559Z
---

**2026-07-30 Opus 5 主控**：sm24 端到端跑测第一次尝试，**卡在 J0、下游全部未跑**，用户拍板「先停，修好判卷器再跑复验」。无生产码改动，测试 1786 绿不变。commit `f98d248`，实况全档 `AI_agent/logs/experiments/2026-07-30_sm24_e2e_attempt/`。

**⛔ BLOCKER（F-6）= v3 判卷层对 reading 阶段既无生产投影、也无能力守卫**，一进 J0 即抛未捕获的 `ScoreContractError: score_product_identity_invalid`，**带崩整条 flow**。根因两处叠加：
1. `decide_score_capability`（`src/agent/judge/score_schema.py`）对 correction 有两道守卫（`product_schema` 必须 v3 + `artifact_contract` 必须 B5 两契约之一），不满足即 `not_applicable`；**对 reading 一道都没有**，直落 `c2_v3`。
2. `score_typed_attempt`（`score_service.py`）里 `stage == "correction"` 走真生产提取器 `extract_correction_plan_segments`；**else 分支要顶层 `segments` + `elevation_observations`**，而识图产物形态是 `{"views": {…}}`（`strokes`/`dimensions`），**全仓无任何生产代码产出该形态**（`grep elevation_observations` 仅命中测试与一个审计脚本 ⇒ 测试全靠手搓 payload）。

⇒ **任何 v3 答案 case 的识图阶段必崩**。sm24 是史上第一个 v3 签字答案 case，故从未触发（管理文档早写过「v3 判卷层此前从未在任何真实 case 上跑过」）。同族于 07-20 的 M2（判卷撞 `ScoreContractError` 全链无捕获→flow 崩），但**那次在非 accepted attempt、这次在 accepted attempt 且无条件**；并违 R-4「判卷只许说 unsupported、不许崩」。

**附带小缺陷（同处）**：`payload.get("elevation_observations", ())` 默认值是**元组**、校验却要求 **list** ⇒「键不存在」被报成 `elevation_observations_not_list`，错误文案指错方向（主控初查被误导一次）。

**修法是设计决策不是补丁 ⇒ 必须走派工，主控不自行拍**：
- 出口 A = 判定「识图不做 v3 类型化判卷」⇒ reading 在 v3 答案下走 `not_applicable`（响亮给理由）或回落 legacy `score_reading_vs_gt`。代价 = 识图与签字答案之间少一把坐标级尺子。
- 出口 B = 判定「识图要做」⇒ 生产侧需写 reading views → `{segments, elevation_observations}` 投影层。代价 = 识图 image-local、答案 building-axis 世界系，投影需标定与朝向绑定，是真几何活。
- 无论选哪个都应补 reading 侧能力守卫，让不支持组合以 `not_applicable` 收口而非抛异常。

**复验轮注意**：run 目录 `case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/` 原地保留，识图 attempt 003 已 accepted 但**质量仅 1/8、不得复用，须重跑识图**（见 [[reading-cv-toolkit-methodology]] 07-30 条 = 硬隔离脚手架导致的机制退化）。判卷侧车四项身份已用生产加载器核过全吻合，J0 不会因缺件 fail-closed。

相关 [[reading-cv-toolkit-methodology]] [[contamination-hard-isolation-requirement]] [[gt-standard-artifact-checklist]] [[pre-run-config-confirmation]]。
