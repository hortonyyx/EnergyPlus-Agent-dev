# 设计请求书 · ②-2 前置：**correction 要吃的「多形态墙证据」契约**

- **日期**：2026-08-30 · **请求方**：orchestrator · **出稿方**：**GPT 家族** · **审**：GLM 家族（交换审）
- **基线**：`bc8e354` · **交付物 = 一份设计稿，⛔ 不是代码**
- ⭐ **为什么点名你出这稿**：「correction 该吃**多形态墙证据**、⛔ 不该吃塌成中线的那一份」——
  **这条结论本来就是你 2026-08-25 跨家族证伪出来的**（你同时更正了基准归属：
  **是 correction 的提示词在要中线**，不是 reading 换格式要适配）。现在请你把它落成可施工的契约。

---

## 〇、⛔ 先读这三份

[本批开发指南](../../../guides/reading_correction_split_guide.md)（§一 分工四刀 · §三 correction 三拍循环 · §四之二 墙厚归属与 R-6）·
[reading 架构](../../../architecture/reading_pipeline_architecture.md) ·
[你 08-25 那份答复](../verdict/2026-08-25_reading_correction_unification_gpt_design.md)

---

## 一、承重前提（**全部是主控 2026-08-30 实测**，⛔ 请自己复核，不符就停下上报）

| # | 事实 | 出处（我核过） |
|---|---|---|
| 1 | correction 的提示词**逐字要中线** | [`pipeline.py:367`](../../../../src/agent/pipeline.py#L367) `"world-frame, wall-centerline, ..."` · [`:370`](../../../../src/agent/pipeline.py#L370) `"every coordinate in one world frame at wall CENTERLINE"` |
| 2 | correction **只吃声明过的契约**，未声明的**响亮失败**（F-97 的成果）；**今天声明的唯一一种** = 「parses as `reading/schema.py:ReadingView` **and declares a `strokes` list**」 | [`vector_contract.py:210`](../../../../src/agent/reading/vector_contract.py#L210) |
| 3 | ⭐⭐⭐ **新证据今天没有契约** —— as-drawn v2 产的是**裸 dict**，全仓**没有**对应的 pydantic 模型 | `grep "class .*Hypothes\|class .*Percept"` 全仓**零命中** |
| 4 | 六形态**部分已有产物**（但只是 dict 的键）：`non_wall_face_lines` · `solid_band_walls` · `ambiguous_face_lines` · `unpaired_wall_faces` · `pairs` · `pair_candidates` | [`as_drawn_v2.py:626-632`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L626) |

⇒ **本设计要填的正是第 3 条那个洞。** ⛔ 没有它，②-2 施工时只能现场发明架构。

---

## 二、⭐ 请回答的六个问题（这就是设计稿的骨架）

1. **六形态各自的字段与语义** —— `paired_faces` / `solid_band` / `single_face` / `axis_trace` / `ambiguous` / `non_wall`。
   每一形态：它**断言了什么**、**没断言什么**、**必带哪些原始引用**（回指到哪条面线 / 哪个 handle / 哪段像素）。
2. ⭐⭐⭐ **基准在哪一层转换、谁做？** —— reading 出的是**面线**，correction 的提示词要**中线**。
   ⛔ 在 reading 侧塞个转换层塌成中线 = 替 correction 干活并扔掉信息（**R-6 同形**，指南 §四之二 点名禁止）。
   ⇒ 请给出**基准该在哪里、由谁、用什么输入**完成，并说明**厚度信息怎么活到内核**
   （R-6 的原话：内墙厚度是「**量了、用掉了、存盘时扔了**」，⛔ 不是「没有」）。
3. **三拍循环怎么落到这份契约上**（指南 §三）：代码算出待裁决清单 → 模型逐条裁决 + 总体把控 → 代码执行裁决出坐标。
   ⇒ **哪些进待裁决清单、哪些代码自己处置并记账？** 铁律 = **模型输出「决定」，代码输出「坐标」**。
4. **`ambiguous` 与 `non_wall` 怎么进出**：它们是**弃权声明**。
   ⇒ 弃权在下游是「已知缺失」还是「错误」？**谁来判、判据是什么？**
5. **与已声明契约的关系**：新契约与那份「带 `strokes` 的旧 ReadingView」是**并存**还是**取代**？
   ⛔ 若并存，请说清**判别器怎么分辨**（F-97 的教训：未声明的形态必须**响亮**失败，⛔ 不许静默走一条腿）。
6. **迁移与验收**：怎么证明「新契约喂进去，correction 出的东西不比现在差」？
   ⭐ 本项目有个便宜手段可用：[[feed-the-answer-in-to-test-the-code-alone]] —— **捏一份答案从 correction 之后走，单测代码自己**。

---

## 三、⛔ 明确不做

⛔ **不写代码、不改任何 `src/` 文件**（本单交付物是 `.md` 设计稿）· ⛔ 不碰 gt 侧
（`gt_facts_staging` / `AnswerCompiler` / 出模形式 —— **GLM 席位此刻正在同一棵树上施工 ②-1c**）·
⛔ 不改 `promote_gt_v3` · ⛔ 不重签任何答案 · ⛔ 不跑全量（跑测归主控）。

⚠️ **同机有 GLM 席位在飞** ⇒ 若你要跑任何 pytest，一律 `-n 6`；⛔ 不许 `pip install -e .`。

---

## 四、⭐⭐⭐ 请把本单的分类句当【可能错的前提】

> 本项目的实证：**跨家族出设计稿最大的价值，就是不继承派工单的错误前提。**
> 「停下上报」**累计 47 次全部是派工方（我）的题错**。

⇒ **「六形态」这个划分本身就是一个没签字的前提** —— 它来自你 08-25 那句话被我转写成的一行 bullet，
**⛔ 从没有人逐条论证过它既不重叠也不遗漏**。
若你判断该分成五种 / 七种 / 或换一根轴切，**请直接改并说明理由**，⛔ 不要迁就我的写法。
同理：§二 那六个问题若漏了要害，请补。

---

## 五、交付

设计稿落 `AI_agent/logs/reviews/verdict/2026-08-30_o22_evidence_contract_gpt_design.md`。
⛔ 只写这一个文件。文末请附**你自己认为最薄弱的一处**，以及**你希望 GLM 复核时重点打哪里**。
