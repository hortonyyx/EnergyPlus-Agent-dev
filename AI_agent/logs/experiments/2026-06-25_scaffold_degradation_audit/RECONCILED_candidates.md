# Reading 脚手架退化 — 两路合并候选清单（2026-06-25）

> 两路独立排查的**去重合并**：`claude_findings.md`（锚 `127ba06` 三分强 prompt 时代 = sm21_pre 时代）+ `codex_findings.md`（含 `a628856` 最早单文件时代）。
> 仍遵守：**只枚举、不揣测哪条对应哪个退化、不开方**。来源标注 〔双〕=两路都找到 / 〔C〕=仅Claude / 〔X〕=仅Codex。
> 用途：下一步**逐条排查 + 恢复**的工作清单（优先级见末尾）。

## 关键定位（两路一致）
- vs **`127ba06`**：skill 三件套（guide/reading_guide/pen_library）字面 ~95% 相同 → 退化**不在 skill 文档本体**。
- 三处真 delta：**①启动 prompt 大幅精简 ②guide §0.1 错误预算软化(`fa04ef6`) ③schema 与 guide/prompt 多处不同步**。
- vs **`a628856` 最早**：另有 pen 集/门处置等**演化级**改动（Codex 覆盖），与近期回归区分开看。

## 组 1 · 启动 prompt 精简（老 `127ba06:.../prompt_template.md` → 新 `new_case_guide.md` 附录A）
1. 〔双〕**坐标精度硬线删除**："Once phase 1 … offsets a coordinate … phase 2 cannot backtrack — it takes what it gets as truth" → 新仅 "Perception errors can only be caught here. Prefer null over guessing."
2. 〔双〕**testdata 总尺寸/层高锚定指令删除**：老"learn floor count / floor height / total dimensions"用于校坐标 → 新只剩"Do not copy testdata content"。
3. 〔双〕**四立面 x_local↔world 映射表(summary)删除**（注：与新 image-local 架构相关，属架构变更）。
4. 〔双〕**8 条编号 Core discipline + 具体反例压缩**（如"south wall (0,0)→(15,0) is ONE stroke, do not split into 3"丢失）。
5. 〔X〕**每份 skill 文档的作用说明删除**（老逐份点明 guide/reading_guide/pen_library 各管什么 → 新只列路径）。
6. 〔X〕**"re-trace"的具体坐标示例删除**（老 "wall pen drew (0,0)→(15,0)" / "window rect (1.4,1.0)→(3.8,2.8)" → 新无示例、只剩否定句）。
7. 〔X〕**图/输出清单表删除**（老列 2f/3f/各立面/supp 的源→输出表 → 新泛化一句）。
8. 〔X〕**worked-example 锚弱化**（老指明人工范例文件+内容"不要重写" → 新只"follow the style"无路径）。
9. 〔X〕**门 healing 护栏缩短**（老"only heal door-symbol openings; doorless spans kept; windows not healed" → 新一句）。
10. 〔X〕**杂物 non-keep 警告缩短**（老列 columns/beams/decorative/index arrows/grid/stair treads → 新只 stairs/columns/grids/furniture）。
11. 〔X〕**workflow 措辞自相含糊**（"stop for review then batch" 与 "do the pilot, then wait"并存）。

## 组 2 · guide §0.1 错误预算软化（`fa04ef6`）
12. 〔双〕老 "phase 2 has no chance to backtrack" → 新 "unless the reading JSON still carries an independent redundant channel … offset coordinate with surviving dimension chain … can be recovered by correction"（`guide.md:47-52`）。

## 组 3 · reading-honest 新增（`fa04ef6`，含"可能帮/可能伤"两向）
13. 〔双〕Stroke 加 `provenance/confidence/dimension_refs`（`schema.py:43-45` + guide L122-124、A0 映射 L170-174）。
14. 〔双·可能=改善〕新增**反过度分割**条款（应保留，恢复老脚手架时别丢）：guide L57-59 双通道纪律 + L282-283 反例"dimension tick 当 interior wall"；reading_guide L153-154 wall card "Positive test: interior wall bounds rooms … ticks outside outline do not become walls"。
15. 〔X〕self-check 同步加了 provenance/tick 项 → 模型需同时满足的约束数增多。

## 组 4 · schema ↔ 文档不同步（NEW 内部矛盾）
16. 〔双〕**dimensions[] 形状漂移**：`schema.py:55-70` 已要 `text_verbatim/value_m/chain_id/role/order/anchor`，但 guide `dimensions[]` **示例仍是老 `text/from/to/axis`**（guide L178-186）→ 尺寸链没被结构化产出。
17. 〔双〕**立面朝向三处口径冲突**：guide §4(L258-270)仍教世界轴 `facade_axis_note` ；附录A + `schema.py:13-18` 说 image-local、世界轴归 correction、`facade_axis_note` 非 load-bearing。
18. 〔双〕**`uncaptured` vs `self_check.uncaptured_visual_elements` 契约分叉**：guide/prompt 教后者且"required 非空"(guide L311)；`schema.py:120-122` 是顶层 `uncaptured`、且 linter 只查"存在+是list"、可空。
19. 〔X〕guide schema 示例**自相不一致**：第一个 wall 例带 provenance，后面 window/polyline 例不带，但 self-check(L297)要求每条都带。
20. 〔X〕`pen: str` / `geometry: dict` 自由（`schema.py:35-43`），文档却给受限契约（pen 合法集 + geometry.kind）。
21. 〔X〕`image_kind` 扩到 section/supplementary/other（schema）vs prompt 只强调 plan/elevation。

## 组 5 · 演化级（vs 最早 `a628856`，Codex 覆盖；与近期回归分开）
22. 〔X〕plan pen 集去掉 `other`/`stair`（最早有）→ 现 unknown 可"best-guess 真 pen if clearly geometric"（`pen_library.md:43`）。
23. 〔X〕门处置：最早"record two strokes"(开口断墙) → 现"heal into one continuous wall"。
24. 〔X〕wall 识别 cue 从"粗黑实线/填充条"(视觉) 偏向"encloses rooms / close a region"(带拓扑味)。
25. 〔X〕新增 `room_labels`(RoomRoleObservation, from labels or furniture, `schema.py:97-119`) → reading 产物里引入房间角色观察。
26. 〔X〕plan window 动作含"which wall"措辞(`pen_library.md:21`) 与 guide"belongs-to 归 correction"(L250)轻微抵触。

## 下一步建议优先级（仅排序，不预判结论）
- **P0** 组1(1·2·4)+ 组2(12)：坐标精度硬线 + testdata 锚定 + 一段一笔反例 + 错误预算（实测 old_r1 的完美坐标与"尺寸链逐段转写"纪律相关，集中在这几条）。
- **P0** 组4(16)：dimensions[] 示例对齐 schema P1a（让尺寸链可结构化产出）。
- **P1** 组4(17·18·19)：三处口径冲突（朝向 / uncaptured / schema 示例自洽）——一致性问题，先消歧再谈能力。
- **P1** 组1(5·6·8) + 组3(15)：prompt 信息密度（doc 作用 / 坐标示例 / 范例锚 / 约束过载）。
- **保留不动**：组3(14) 反过度分割条款是 NEW 强于 OLD 处，恢复时务必留住。
- **单独评估**：组5 演化级（pen 集 / 门 / room_labels）——非 vs sm21_pre 时代的差异，按需再议。
