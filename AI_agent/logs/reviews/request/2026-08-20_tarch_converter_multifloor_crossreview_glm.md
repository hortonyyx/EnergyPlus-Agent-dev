# 交叉审阅请求 · 天正转换器多层化（GLM 审 GPT 施工）

- **日期**：2026-08-20 · **审阅席**：GLM `glm-5.3` · **施工席**：GPT `gpt-5.6-sol`（⛔ 谁写谁不批，故换你）
- **档位**：工程档 · **主控**：claude-opus-5（我在你之后另跑一道轻门：独立全量 + 抽查 diff）
- **你只看三样**：原始需求（派工单）· `git diff` · 测试输出。⛔ **不要读施工席的长篇自述当依据。**

## 一、材料

| 项 | 位置 |
|---|---|
| 原始需求（派工单，**含三次修订**） | `AI_agent/logs/reviews/request/2026-08-20_tarch_converter_multifloor_dispatch_gpt.md` |
| 施工席定案说明（**仅供索引，不作依据**） | `AI_agent/logs/reviews/execution/2026-08-20_tarch_converter_multifloor_sol_verdict.md` |
| 改动 | 工作区未提交：`src/agent/judge/{gt_extraction,tarch_normalize,tarch_review_bundle}.py` + 三份 tests（`git diff` 可见，838 增 / 26 删）|

## 二、⭐ 审阅重点（按你最强的那一面设计）

本仓 2026-07-21 对 GLM 的实测画像：**验证性审阅 = 顶档**（查「锁是不是真绑目标门」零漏判零误报）；
**探索性审阅 = 不及格**。⇒ **本单只要求你做前者**，探索面由 orchestrator 的轻门补，不要求你承担。

**逐条验，每条都要给「我实跑了什么、看到什么」**：

1. **每一把新锁做 neuter**：把它所针对的那处生产改动摘掉 ⇒ 该锁必须变红，**且只红它、零连带**。
   施工席自称三把硬锁 + 立面 must-red 都做过 neuter —— **⛔ 不采信，你自己做一遍**。
2. **`gt_extraction.py` 那处是 gt 侧信任根**（立面开洞按竖向归层）。重点验两件：
   - 它**真的用上了**竖向区间（此前 `_z` 参数在 38 行函数体里只出现在解包那一行、从未被引用）；
   - ⛔ **没有为了让两层通过而放宽单层下的歧义判定**——歧义该报还得报。请构造/找出一个**本应报歧义**的用例，确认它仍然报。
3. **sm24 内容零漂移：验它是不是【实跑】的，还是只是【声称】**。判据见派工单 §5.2：
   规范化 DXF + 几何（floors/zones/footprint/openings 全部坐标）必须逐字节一致；
   溯源哈希**允许**如实更新、⛔ **不许保留旧值**（保留旧值 = 伪造 provenance，属 BLOCKER）。
   **七张 render 的差异是【已知并接受】的**（用户已表示会重签 sm24），⛔ 不要把它报成缺陷。
4. **全仓回归**：基线 = **2911 绿 + 14 strict xfail**（orchestrator 2026-08-20 在 `f2ea22e` 实测）。
   施工后应为 **2918 绿 + 14 xfail**。**自己跑一遍 `python -m pytest -n auto` 对账**；
   ⚠️ **xfail 数若变了要报**（意味着有 xfail 被意外修复或被压掉）。
5. **派工单 §四 四条前提 + §三 D/E + 那三处 `plan_views[0]`**：施工席给了结论，
   **验它的结论有没有实据**，而不是复述派工方或它自己的话。

## 三、⛔ 边界

- ⛔ 不许改任何生产代码去「顺手修好」你发现的问题 —— **报出来，由 orchestrator 决定**。
  做 neuter 时的临时改动**必须还原**，还原后跑一次 `git diff --stat` 自证零残留。
- ⛔ 不许 `git add` / `git commit`。
- ⛔ 不许碰 `case_tests/test_baseline/gt/**` 与 `skills/intake_pipeline/0_reading/**`。
- ⛔ 不许改 `AI_agent/` 下除你自己的裁决文件以外的任何文档。

## 四、交付

裁决写到 `AI_agent/logs/reviews/verdict/2026-08-20_tarch_converter_multifloor_glm_verdict.md`：
**APPROVE / REWORK** + 逐条 finding（BLOCKER / MAJOR / MINOR / NIT）+ **每条附「我实跑了什么、看到什么」**
+ neuter 结果表（哪把锁、摘了什么、红了几条、有无连带）+ 你自己跑出的全仓数字。
⛔ 不要长篇复述改动内容。
