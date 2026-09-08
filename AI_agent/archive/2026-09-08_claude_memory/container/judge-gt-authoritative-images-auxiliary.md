---
name: judge-gt-authoritative-images-auxiliary
description: 用户硬规约——judge 评测一律以 gt 坐标数据为权威指标，看图只作辅助；看图裁断权只归用户
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8251d8f3-807b-45b8-9d57-e1f642586016
---

**2026-06-24 用户定（硬规约）**：之后所有 judge/评测，**以 gt 为权威指标**——即把识图/产物的**坐标数据**和 gt 的坐标逐元素对账（命中/漏/多/偏移多少）才是好坏的**唯一标准**；**judge 看图只做辅助**，不得据此下结论。**看图的裁断指标只归用户**——主控/judge 不能通过"看渲染图"直接得出好/坏结论。

**Why**：这次我犯了错——用"数墙数/窗数 + 看渲染图 + 信子代理自评布局"得出"Sonnet 这次满分",一做坐标级对账就崩(Sonnet 1f 竖墙偏 0.36m、7 窗只 1 窗位置对)。数量对≠位置对,看图会骗人,且视觉裁断的标准/容差只有用户能定。

**How to apply**：① 任何"X 读得好/坏"的结论必须来自**坐标 vs gt** 的数值对账(墙竖线 x/横线 y、窗 facade+x+宽),报命中率+实际偏移,不靠数量、不靠看图、不靠模型自述；② **✅ 评分器已落地(2026-06-24)**:`src/agent/judge/reading_score.py` + CLI `scripts/tool_scripts/score_reading_vs_gt.py`(用法 `score_reading_vs_gt.py <reading_dir> --case <case>`)+ `tests/test_reading_score.py`;从 gt zone rect 派生内墙竖/横线+窗 span,逐元素匹配报命中/漏/多+偏移;经 load_gt 读 gt 不破隔离铁律。实测 sm21:Opus 墙9/9窗10/15、Sonnet 墙7/9窗4/15。残留=zone_f1/WWR 综合指标 + 嵌 record_baseline；③ judge harness 的 verdict 以 gt-diff 为准、VLM 看图仅辅助；④ 渲染图只给用户裁断,主控不下视觉结论。归校验架构 judge 口径 + [[per-stage-validation-judge-architecture]]。相关 [[reading-quality-investigation-2026-06-24]] [[contamination-hard-isolation-requirement]]。
