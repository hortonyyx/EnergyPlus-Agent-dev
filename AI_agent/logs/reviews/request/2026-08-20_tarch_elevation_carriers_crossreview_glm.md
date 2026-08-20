# 交叉审阅请求 · 立面洞口载体方言层（GLM 审 GPT 施工）

- **日期**：2026-08-20 · **审阅席**：GLM `glm-5.3` · **施工席**：GPT `gpt-5.6-sol`（⛔ 谁写谁不批，故换你）
- **档位**：工程档（碰答案产出路径）· **主控**：claude-opus-5（我在你之后另跑一道轻门：独立全量 + 已逐行审过 diff）
- **你只看三样**：原始需求（派工单）· `git diff` · 你自己跑出来的测试输出。
  ⛔ **不要把施工席的自述当依据**（本仓实犯过：[[self-report-more-compliant-than-artifact]]）。

## 一、材料

| 项 | 位置 |
|---|---|
| 原始需求（派工单） | `AI_agent/logs/reviews/request/2026-08-20_tarch_elevation_opening_carriers_dispatch_sol.md` |
| 主控中途两次追加裁决（**属需求的一部分，必读**） | `AI_agent/logs/reviews/execution/2026-08-20_tarch_elevation_carriers_sol_execution.md` §2 |
| 改动 | 工作区未提交：`src/agent/judge/{tarch_converter_schema,tarch_normalize}.py` + 新增 `tests/test_tarch_opening_carriers.py`（`git diff` + 该未跟踪文件）|

**背景一句话**：立面洞口提取原先把「图怎么画」烤死在代码里（只认 `LINE`，
`window_selector.entity_types` 全文从未被读取 ⇒ sm25 静默产 0 窗）。本批改成
**「画法由请求声明、代码只匹配与执行」的方言层** + 一道**清点对账门**。

## 二、⭐ 审阅重点（按你最强的那一面设计）

本仓对 GLM 的实测画像：**验证性审阅 = 顶档**（查「锁是不是真绑目标门」零漏判零误报）；
**探索性审阅 = 不及格**。⇒ **本单只要求前者**，探索面由主控补。

**逐条验，每条都要给「我实跑了什么、看到什么」**：

### 1. 每一把新锁做 neuter（施工席自称都做过 —— ⛔ 不采信，你自己做一遍）

摘掉该锁针对的那处**生产改动**，锁必须变红，**且只红它、零连带**。涉及的锁：
L1（sm24 等价）· L2（撤载体规则）· L3（删窗规则 ⇒ 未消费）· L4（块指纹漂移）·
L5（双重消费）· L6（同带间距 < 声明值必红 / ≥ 声明值必绿）· 未知门块响度回归。

⚠️ **每把锁还要验「自证前提」**：不施加扰动时该用例**确实是绿的**。
只有负向断言的锁 = 恒红 = 结构上不可观测（[[gate-with-only-negative-assertions-is-unobservable]]）。

### 2. ⭐⭐ 最重的一条：sm24 那四条既有 must-red **是不是还因为原来的原因红**

`tests/test_tarch_elevation_must_red.py::test_door_structural_union_mutations_make_g3_red`
四个参数（`positive_gap` / `positive_overlap` / `t_shape` / `different_z`）现在仍报 PASSED。
**但「仍然红」不等于「防住了原来那件事」** —— 新加的对账门 / 双重消费门也会让 G3 红，
足以让一条 must-red 看起来还是绿灯通过，而它原本要抓的那个畸形联合体已经漏掉。

⇒ **请逐个确认红的诊断码仍是 `tarch_elevation_door_structure_invalid`**，
而不是被 `tarch_elevation_entities_unconsumed` / `tarch_elevation_entity_double_consumed` 顶替。
**这一条查出问题的话是 BLOCKER。**

### 3. 翻译层是不是「纯翻译」，而不是偷偷保留的第二条执行路

主控裁决要求：旧请求（`opening_carrier_rules is None`）**翻译成规则表后照常只走新解析器一条路**。
- 验 `_translate_legacy_opening_carrier_rules` **只产规则、不产任何洞口几何**；
- 验法建议：把 `_resolve_opening_carriers` 摘掉（或让它返回空），**sm24 必须立刻红**
  —— 若还能出洞口，说明旧路残留，属 BLOCKER。

### 4. 对账门是不是**真的落成 G3 门失败**，而不是一条 advisory 诊断

构造一个「声明图层内、无人消费、也未显式忽略」的实体，确认：
① `tarch_elevation_entities_unconsumed` 出现 ② **`G3` 门 `passed=False`** ③ 诊断里**逐个列出句柄**。

### 5. 门合并策略的边界

- `same_band_strict_union`（旧请求走这条）与旧行为**逐条等价**；
- `touching_rect_union` + `module_union_min_gap_m`：**恰好等于**声明值时的行为要确定且合理
  （施工席称「等于声明值 ⇒ 分成两樘且绿」，请复核这与代码里的 `<` 一致）；
- schema 侧：窗规则不许声明合并策略 / 门规则必须声明 / `touching_rect_union` 必须给间距且**无默认值**。

### 6. 全仓回归对账

基线 = **2917 绿 + 14 strict xfail**（主控 2026-08-20 在 `32ab707` 实测）。
施工后施工席报 **2937 绿 + 14 xfail**。**自己跑一遍 `python -m pytest -n auto` 对账**。
⚠️ **xfail 数若变了要报**（意味着有 xfail 被意外修复或被压掉）。

### 7. 机械可验的拓展性判据（派工单 §1#1）

数一个数：**新增一种载体画法，需要修改多少行【已有】代码？**
（预期答案 = 0 行已有分支，只加注册表项 + 新 resolver + schema 的 Literal 加一个值。）
若你数出来 > 0，列出具体位置。

## 三、⛔ 边界

- ⛔ 不许改任何生产代码去「顺手修好」你发现的问题 —— **报出来，由主控决定**。
  neuter 的临时改动**必须还原**，还原后跑 `git diff --stat` 自证与审阅前一致。
- ⛔ 不许 `git add` / `git commit` / `git push` / `git stash`。
- ⛔ 不许碰 `case_tests/test_baseline/gt/**` 与 `skills/**`。
- ⛔ 不许改 `AI_agent/` 下除你自己的裁决文件以外的任何文档。

## 四、交付

裁决写到 `AI_agent/logs/reviews/verdict/2026-08-20_tarch_elevation_carriers_glm_verdict.md`：
**APPROVE / REWORK** + 逐条 finding（BLOCKER / MAJOR / MINOR / NIT）+ **每条附「我实跑了什么、看到什么」**
+ neuter 结果表（哪把锁、摘了什么、红了几条、有无连带、自证前提是否成立）
+ §2 那条的诊断码逐个对账表 + 你自己跑出的全仓数字。
⛔ 不要长篇复述改动内容。
