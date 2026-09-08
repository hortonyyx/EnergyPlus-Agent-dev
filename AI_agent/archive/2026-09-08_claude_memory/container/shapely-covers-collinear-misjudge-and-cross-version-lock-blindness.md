---
name: shapely-covers-collinear-misjudge-and-cross-version-lock-blindness
description: shapely covers 在共线段上 distance=0 仍返回 False；「同代码两次运行一致」的锁对跨版本产物漂移天生零覆盖
metadata: 
  node_type: memory
  type: project
  originSessionId: b2fcd417-6fc6-4558-92c9-f1aa53d64078
---

2026-08-21 GLM 交叉审 sm25（裁决 `AI_agent/logs/reviews/verdict/2026-08-21_sm25_plan_side_glm_verdict.md`）撞出的两条：

1. **shapely `covers` 在共线但顶点集不同的线段上会浮点误判**：边躺在 footprint.exterior 上
   （`distance == 0.0` 精确为零）却 `covers == False`。sm24 六条纯外轮廓边因此被误发射。
   选几何谓词时：`covers/covered_by` 对「共线+端点不在对方顶点集」不可靠；`distance<=tau`
   稳定但语义不同（接触即 0，分不清「完全躺上」与「部分伸出」）。需要区分后两者时必须
   分段覆盖/端点归属级别的判定，没有任何单一 shapely 谓词能兼任。
2. **「同代码两次运行一致」的确定性锁（deterministic/reproducibility 类）对跨版本产物漂移
   零覆盖**：主控全量 2946 绿与「sm24 重建产物 76 字段漂移」并存。凡「XX 逐字段不变」被
   当红线，唯一验证形态 = 用两个提交各重建一次产物做结构化 diff（本席做法：git worktree
   出父提交 + 同 fixture 全链重跑 + 递归 leaf diff），并区分「几何内容」与「生成句柄/溯源
   hash」两类字段——代码一变溯源 hash 必变（[[version-number-is-not-behavior-attestation]]
   的近亲），别把两类混在一个 hash 判据里。

相关：[[reproduce-the-form-not-the-run]]、[[hash-of-whole-report-is-not-an-equality-test-for-its-parts]]。
