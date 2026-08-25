# sol 跨家族架构意见 · reading + correction 一体改（含 grade 侧复核）

- **日期**：2026-08-26　**出稿方**：**GPT 家族 sol**（`gpt-5.6-sol` / effort `xhigh`，只读未改，HEAD `5bc0264`）
- **讨论稿** → [`../request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md`](../request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md)
- **前一版备料**（同家族 08-25）→ [`2026-08-25_reading_correction_unification_gpt_design.md`](2026-08-25_reading_correction_unification_gpt_design.md)

## ⭐ 总判：**部分采纳**，推翻我方四条前提

采纳「reading 保留多形态证据 · correction 负责工程化坍缩 · 代码产坐标」的方向；
**推翻**：①「有了双面墙 R-3 自然消失」②「reading/correction 各造一个判分器」
③「correction 产物未变所以判分只需小补」④ 把三拍展开成通用 Pareto 协议。

⭐ **它给的第三形态**（稿子里没有的）：**一份版本化参考包 → 两个投影 → 共享评分内核**
（来源空间投影喂 reading 适配器 · 指定出模投影喂 correction 适配器；两侧答案先归一化，再走同一套 criterion/报告）。
⇒ **不是造两套 grader**，而是「共享 scorer + 分阶段适配器」，而仓库里**已有雏形**（`score_service.py:393` / `score_policy.py:116`）。

## ⚠️ orchestrator 的独立核查（⛔ 不照抄）

**它说「提示词与 judge 的墙线约定互相矛盾」—— 部分成立，但需说准**：
- 提示词确实逐字要求「全部按 wall CENTERLINE」（[`pipeline.py:365-369`](../../../../src/agent/pipeline.py#L365)），
  schema docstring 也写 centerline（[`schema.py:234`](../../../../src/agent/correction/schema.py#L234)）。
- judge 侧声明的约定是「**外墙外皮 + 内墙中轴**」（[`correction_score.py:55-75`](../../../../src/agent/judge/correction_score.py#L55)）。
- ⭐ **但两者本来是靠确定性核的外包变换（F-17）对齐的，且注释写明只对 schema v3 成立** ⇒ **不是无人处理的矛盾，是一次有意的转换。**

⭐⭐ **由此把 F-99 那 12 cm 定位得更准了**（⛔ 覆盖此前「correction 全程中线」的说法）：
产物的 **footprint 已经在外皮**，而**立面段（facade span）没有跟着做那次外包变换** ——
实测 `South product (0.12,5.13) vs gt (0.00,5.00)`、`North (14.88,24.89) vs (15.00,25.00)`，
两端各内缩半个墙厚 ⇒ **F-17 的外包变换覆盖了 footprint，漏了 facade segments**。
（F-99 仍挂起等新产物，但一体改设计必须知道这一条。）

## ⭐⭐⭐ 它带回的两条最重、必须进设计的结论

1. **当前 gt 不能直接当新 reading 的答案** —— 它只有设计/楼层/zone/opening 等**最终语义**
   （[`gt_schema.py:73`](../../../../src/agent/judge/gt_schema.py#L73) / [`:164`](../../../../src/agent/judge/gt_schema.py#L164)），
   **没有来源空间的墙面、也没有可信的栅格标定** ⇒ 直接影响本批第三件目标（gt 出判分答案）。
2. ⭐ **产品自报的标定不能用来换算它自己的答案** —— 那是**自证回路**。
   描图分必须比来源像素/来源原生坐标，或用**裁判自己拥有的**变换；标定只能作为**另一个被判的答案**。
   ⇒ 判别实验：故意改产品标定 ⇒ 标定分该变、**描图分不该变**。

---

## 以下为 sol 意见正文（逐字，未改）

