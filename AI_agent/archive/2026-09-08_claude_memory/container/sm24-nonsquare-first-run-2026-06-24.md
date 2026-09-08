---
name: sm24-nonsquare-first-run-2026-06-24
description: sm24 首个非方形 case 端到端首跑发现——框架几何 hold 住，但非矩形开敞空间过度分区(缺区合并/air-boundary)
metadata: 
  node_type: memory
  type: project
  originSessionId: 8251d8f3-807b-45b8-9d57-e1f642586016
---

**2026-06-24** 跑通首个**非方形** case（sm23 复制成 `sm24_anchor`，以后 sm24 为该 case、下分 run）。`run_2026-06-24_opus_reading`：Opus 冷启子代理识图 + 全放行 + EP，自包含收口（`completed_clean`/blocked=False、REPORT.md AGENT 区已填）。footprint 10×20m 规整，但**内部 L 形走廊 + 阶梯西墙右下 office**（非矩形）。

**结果**：识图干净（J0 7 条全 pass，仅 L 拐 x 一条 minor recoverable）→ 1_correction flag 区数 tripwire 11≠8 → 内核 11 区/76 面/11 窗、kernel gate 0 issue → EP **0 severe / 6 warn**（全样板）。

**核心发现（归 C2 非方形能力升级）**：确定性内核把**非矩形开敞空间过度分区**——L 形走廊拆成 Z06_Corridor_N + Z10_Corridor_SE 两个 EP 热区、阶梯 office 拆 3 区（8→11）。拆出碎片**导热耦合正确**（76 面 = 40 内部相邻 + 25 室外 + 11 接地全互逆，`Z06_W1↔Z10_W5` 互为匹配面、InterZone 零缺陷）**但无空气耦合**（无 AirBoundary/ZoneMixing），EP 视为隔导热墙的独立区，物理上是一个连通开敞空间。→ 需在内核分解后加**区合并 / air-boundary** 步骤。

**对诊断②的旁证**：同样的 reading-honest schema，**Opus 没被 provenance/dimension_derived 带偏过度分割**（子代理 schema feedback：dimension_derived 仅用于周边墙、内墙用 seen）——支持"schema 给漏洞、弱模型(Sonnet/gpt-mini)才掉坑"的判断。

**Why/状态**：用户定"先完整收 sm24、后面做完 gt 再继续"。**sm24 无 gt**（待补，关键=约定非矩形房间"期望热区数"口径：L 走廊算 1 还是 2），补前不入册 golden。脚手架坑：run_full_pipeline 把 EP 写 `<case>/output/` 而非 `<run>/EP/EP_run/`，anchor 布局需手动归位。详 plan.md N3/N3b。相关 [[reading-quality-investigation-2026-06-24]] [[recognition-modeling-capability]]。

**✅ 续 2026-07-08（C2 B1 首实战，过度分区缺陷关闭）**：`run_2026-07-07_haiku_cv_probe`（Haiku reading）推 correction(DeepSeek)+内核，`--capability-profile orthogonal_polygon` + judge off。DeepSeek 出 schema v2：走廊=**8 顶点 C 形单一 polygon cell**、se_office=6 顶点 L 形 → 8 区（6 月是 11 区）、走廊单区连贯、InterZone 全净、geometry gate 停等用户 approve。实战抓出并修掉两个 B1 缺陷：①LLM 出 CW 绕向被 raise 炸 flow → core CW→CCW 无损规范化 + draw 级 polygon 检查镜像（盲重抽不炸）；②C 形（两翼+一边多邻居）polygon 墙法向错 3+配对同向 1 → modelling/split_pairing/kernel.normals 改 polygon 局部内外探针（Codex 修，sm24 简化 8-cell 进回归）。测试 546→556 绿。correction prompt 规则钉死"**一个房间=一个 cell，房间自身非矩形才出 polygon**"（Codex 初版"能拆矩形就不出 polygon"会让 polygon 变死代码，已改）。
