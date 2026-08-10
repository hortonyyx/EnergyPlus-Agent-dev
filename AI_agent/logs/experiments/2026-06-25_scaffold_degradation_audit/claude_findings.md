# Reading 脚手架退化排查 — Claude 独立枚举（2026-06-25）

> 任务：枚举 老/更早 vs 新脚手架 中**可能降低 reading 能力**的差异。**只枚举、不揣测哪个对应哪个退化、不开方**（下一步再逐个排查恢复）。
> 参照：OLD = `127ba06`（三分·强 prompt 时代，sm21_pre 时代形态）+ 必要时 `a628856`（最早单文件）；NEW = 当前 `skills/intake_pipeline/0_reading/` + `src/agent/reading/schema.py` + `new_case_guide.md` 附录A。
> 证据均给 文件/commit + 原文引述。

## 0. 总体观察（定位 delta 在哪）
**skill 三件套（guide / reading_guide / pen_library）old↔new ~95% 字面相同**——逐段比对仅"phase 1"→"the reading stage"、"phase1_summary.md"→"reading_summary.md"之类改名。**真正的能力相关 delta 集中在三处**：① 启动 prompt（老 `prompt_template.md` 详尽 → 新 附录A 精简）；② guide §0.1 错误预算被 `fa04ef6` 软化；③ 新增 schema 与 guide 的 `dimensions[]` 示例不同步。reading_guide 的识别卡片 old↔new 实质未变（§0–§I 一致）。

## A. 启动 prompt（最大 delta：老 `127ba06:.../phase1/prompt_template.md` vs 新 `new_case_guide.md` 附录A）
- **A1 坐标精度硬线被删**。老："**perception errors can only be caught in phase 1. Once phase 1 misreads a dimension, offsets a coordinate, flips the elevation x-axis, or misses a stroke, phase 2 cannot backtrack — it takes what it gets as truth**"。新 附录A 仅："Perception errors can only be caught here. **Prefer null over guessing.**"（"correction 不能回溯"那句没了）。
- **A2 testdata 总尺寸锚定被删**。老："Read metadata from `testdata_prompt.json` … to learn the floor count / **floor height / total dimensions**"（让模型用总尺寸校自己读的坐标）。新 附录A 只剩"Do not copy testdata content into the JSON"，**无总尺寸锚定指令**。
- **A3 四立面 x_local↔world 映射表（summary）被删**。老："the four-facade **x_local ↔ world-axis table** (actual filled values)" —— 逼模型显式做坐标变换算术。新 无此要求（注：新架构把世界轴推给 correction，这条是**架构变更**，列此仅为"老有新无"的客观差异）。
- **A4 "尺寸链锚定/转写算术"未强调**。老 prompt + 老 §0.1 通篇压"按尺寸读准坐标"；新 附录A 无"逐段转写尺寸链并做算术得坐标"的明确指令。（实测 old_r1 summary 自述"All dimension chains transcribed verbatim in mm; converted to meters"——该纪律来自老脚手架。）
- **A5 8 条编号 Core discipline 压缩**。老有 8 条编号纪律（含 "One stroke per continuous stroke. **E.g. the south perimeter wall from (0,0) to (15,0) is one wall stroke, do not split into 3**" 这种带具体反例的）。新 附录A 压成 ~7 条无编号 bullet、丢了具体反例。
- **A6 worked-example / pilot 工作流**：两版都提"先做 pilot"，但老 prompt 的"读三份 skill + 看 worked-example JSON 跟风格 + pilot 后停"流程更完整。

## B. guide.md §0.1 错误预算（`fa04ef6` 软化）
- **B1**。老 `guide.md` §0.1："Once phase 1 writes it wrong, phase 2 **has no chance to backtrack**." 新 `guide.md` §0.1（L48-52）改为："…**unless the reading JSON still carries an independent redundant channel** … An **offset coordinate with a surviving dimension chain** and honest provenance **can be recovered by correction**…"。→ 坐标"必须一次读准"的弦被放松为"有尺寸链可由 correction 恢复"。

## C. 新增内容（NEW 加的，也按任务列出——含可能帮/可能伤两向）
- **C1 schema 加 provenance/confidence/dimension_refs**（`fa04ef6`，`schema.py:43-45` Stroke + guide L122-124、L170-174 A0 映射）。新字段本意"诚实标注"。
- **C2（可能反向=改善，照实记）** 新 guide 加了**反过度分割**的负例 + 双通道纪律：L57-59 "Two-channel discipline: … A dimension annotation, cumulative tick, extension line… must NEVER become a `wall` stroke"；L282-283 新增反例"tracing a dimension-chain cumulative position or tick drawn outside the building outline as an interior `wall`"。→ 这条是**新脚手架比老更强**的地方（老 §5 反例无此条），记此以免片面归因"新一定更差"。
- **C3 pen_library** 新增反例 L91-92"elevation floor-height door as window"。pen_library 其余 old↔new 一致。

## D. schema ↔ guide 不同步（NEW 内部）
- **D1**。`schema.py` 的 `Dimension`（L55-71）已有 P1a 字段 `text_verbatim/value_m/chain_id/role(overall|segment|baseline)/order/anchor`，但 `guide.md` 的 `dimensions[]` **示例仍是老形状**（L178-186：`text/from/to/axis/note`）。→ 模型照 guide 示例产出，拿不到 schema 想要的可校验尺寸链字段。
- **D2**。`schema.py` 的 P1b `FacadeOrientation`（view_facade/local_x_positive/mirrored/orientation_evidence，L83-94）是 image-local 新模型；但 guide §4（L258-270）+ 附录A 仍教老的 `facade_axis_note` 世界轴写法。→ 立面朝向字段，schema 与 guide/prompt 三处口径不一。

## E. "更早"维度（`a628856` 最早单文件）
- 本轮我把 OLD 锚在 `127ba06`（=sm21_pre 时代的三分强 prompt 形态）。最早 `a628856:skills/energyplus_mcp_twostep/phase1_prompt_template.md` + `phase1_vector_schema.md`（单文件、pen 集更早含 `other`/`stair` 等）的细节，交由 Codex 那路覆盖（见 `codex_findings.md`），避免重复。

## 最高嫌疑 shortlist（仍不映射症状，仅"最像能力相关"）
1. **A1 + B1**：坐标精度硬线（"不能回溯"）在 prompt 和 guide 两处都被软化。
2. **A2 + A4**：testdata 总尺寸锚定 + "尺寸链逐段转写/算术得坐标"指令在新 prompt 缺失。
3. **D1**：schema 要 P1a 尺寸链字段，guide 示例还教老形状 → 尺寸链没被结构化产出。
4. **A5**：带具体反例的"一段连续墙一笔"等纪律被压缩。

## 与 Codex 那路的关系
两路独立产出。本文件 = Claude 自读 老/新全文 的枚举；`codex_findings.md` = Codex 独立 git 取证。下一步：合并去重 → 逐条排查恢复（按 shortlist 优先）。**注意 C2 这类"新比老强"的点要留住,恢复老脚手架时别把它一起丢了。**
