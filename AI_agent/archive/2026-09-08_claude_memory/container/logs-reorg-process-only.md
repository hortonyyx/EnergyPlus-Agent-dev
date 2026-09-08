---
name: logs-reorg-process-only
description: 2026-07-05 logs 全量重排为纯过程痕迹 + 活文档抽离；老 logs/review/ 路径已失效的重定向表
metadata: 
  node_type: memory
  type: project
  originSessionId: ec6ac772-d74f-4867-8076-eee5d7ba2e40
---

**2026-07-05（commit `7.05_LogsReorgProcessOnly`，未 push）**：`AI_agent/logs/` 全量重排 = **只放开发过程痕迹**，
活方案文档抽离归位。判据=「仍被前向引用为权威源 / 未落地的持续演进设计 = 活，拎出 logs；某次开发步骤的快照
（做完的 proposal / Codex review / execution log / audit / diagnosis）= 冻结，留 logs」。纪律锁 `logs/README.md`。

**路径重定向（其他 memory / 老文档里的 `logs/review/...` 已失效，按此换算）**：
- `logs/review/request/` → `logs/reviews/request/`（ask：brief/proposal/原型）
- `logs/review/review/` → `logs/reviews/verdict/`（Codex 裁决 *_review.md）
- 散落的 `*_execution_log.md` → `logs/reviews/execution/`
- 实验 bundle 目录 `logs/review/20xx_*/` → `logs/experiments/20xx_*/`（`20*_*/` gitignored）
- `logs/review/renders/` → `logs/renders/`

**活文档抽离去向**：
- 判卷权威 spec `grade_visual_model_spec.md` → `architecture/judge_grade_model.md`（判卷子系统活规格，§8b 开放 backlog）
- role phase-2 deferred 设计 → `proposals/role_binding_phase2.md`
- J23/P2 几何 judge deferred 设计 → `proposals/j23_geometry_judge.md`
（后两者是 Codex 独立复核抓出的我漏的半活文档；logs 原 request/verdict 留作冻结审轨。）

零逻辑改动·468 passed/9 xfailed·0 死链。见 [[standardize-test-flow-and-judge-arch]]。
