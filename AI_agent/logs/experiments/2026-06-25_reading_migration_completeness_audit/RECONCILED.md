# Reading 脚手架 → 0-5 架构 迁移完整性通查 — 三路综合（RECONCILED）

> 日期：2026-06-27（Claude 综合 + 代码核验）
> 输入：`codex_findings.md`（xhigh，已迁49/遗漏1/⚠️冲突4/有意删2）+ `deepseek_findings.md`（v4-pro，已迁58/遗漏0/⚠️冲突2/有意删0）
> + **本轮 Claude 第三路 = 对每条冲突做 attempt 级代码核验**（用户 N1f 定"Claude 自己补一路"，且 [[judge-gt-authoritative-images-auxiliary]] 教训：归因须代码坐实、不靠他路判语）。
> 范围：reading 先做透（1-5 后推）。基线=两步法 sm21_pre 脚手架（`old_scaffold_127ba06`）。

---

## 1. 两路收敛点（无分歧）

- **绝大多数约束已迁**：术语 phase→stage，职责边界（reading 只重描、correction 不看图）完整保留；多条旧 prompt 约束**升级为代码门**（合法 pen×kind、禁拓扑字段、dimension parse/axis/closure、facade image-local 存在性、互逆配对、跨层对齐、窗 clamp/父墙）。计数差异（49 vs 58）纯属聚类粒度（DeepSeek 把高度相似项合并），非实质分歧。
- **两路都独立标出的真冲突**：**C1（facade 世界轴 vs image-local）**、**C4（uncaptured 载体/强度错位）**。

## 2. 两路分歧的裁决

| 项 | Codex | DeepSeek | Claude 核验裁决 |
|---|---|---|---|
| **C2** scale_origin world placement | ⚠️冲突 | 列"已迁"（只看到 schema 留了 dict） | **判⚠️冲突**：schema.py:115 确为 optional dict、**无 validator、无下游消费者**，guide 仍教 `world_x/y/z_m` 世界落位，与 schema 顶注 "world axis/sign/base NOT here" + kickoff "no world placement" 矛盾。DeepSeek 漏在没追消费者。 |
| **C3** pipeline §3 verbatim 悬空依赖 | ⚠️冲突 | 未发现（没读 pipeline.py） | **判⚠️冲突·坐实**：pipeline.py:351 correction prompt 写 "Use the facade translation formulas in reading_summary.md §3 verbatim"，但 kickoff:52-53 不再要求 reading 产 §3，且 P1b 要 correction 自己推世界轴。运行时引用一段不保证存在、且架构上反向的文本。 |
| **遗漏 #50** per-facade/floor window chain | ❌遗漏1 | 列"已迁"（认为受益于 dimension 结构化） | **判⚠️能力缺口（轻）**：B1 旧脚手架要求逐层独立读窗链（楼层间窗数/分布/blank 可不同）；现 reading 文档只说"逐个 rect 记"，pipeline 只做"有窗→correction 全丢"的 all-or-nothing。非硬冲突，归 backlog（见 §5）。 |
| 拓扑禁字段门覆盖面 | #18 备注：门只挡 zone/adjacent_*/obc/world_z，未覆盖旧例 is_exterior/parent_window_ids/rooms | #20 列"已升级为代码门"（未注意覆盖面） | **判轻缺口·坐实**：`_FORBIDDEN_STROKE_KEYS`(reading.py:31) = {zone, adjacent_zone, adjacent_surface, obc, world_z}，确实**不挡** is_exterior/parent_window_ids/rooms[]。guide §5 仍以这三者为反例 → 模型若误加只有 prompt 拦、无代码门。归 backlog 轻补。 |

## 3. 冲突桶 — Claude 代码级核验（attempt 级事实，非他路判语）

### C1 · facade 世界轴表 vs P1b image-local
- **旧**：guide §1/§4 教 elevation 写 `facade_axis_note`（四立面世界轴映射表），旧两步法里这是 phase2 把立面窗 rect 转世界的承重输入。
- **新落点**：`schema.py:13-18,83-95` canonical `FacadeOrientation` 只有 image-local（`view_facade/local_x_positive/mirrored/orientation_evidence`）；`reading.py:366-379` `_facade_fields` 是 **INVARIANT 阻塞门**，elevation 缺 `facade.view_facade` 即 FAIL；`legacy.py:57-100` 只把旧 note 当 low-confidence evidence。
- **断点（仍在 skill 文档）**：guide §1(L89-94) + JSON 示例(L106-116) + §4(L301-313) **原样保留旧 `facade_axis_note` 世界轴表**，JSON 示例**无** canonical `facade` 块。
- **核验严重度**：**非"照 guide 填必崩"**——产物经 `load_reading_view`(validation_run.py:117 / run_stage.py:101 全走它) → `_is_legacy` 判 legacy → `_migrate_facade` 从 label/note 正则兜底回填 `view_facade`。**但代价**：① 每张新立面被误标 `migrated_from_legacy=True` + migration_flags（一等产物冒充 legacy 迁移痕迹）；② 兜底**有条件**——label 和 note 都无 north/south/east/west 词则 `view_facade=None` → 真 FAIL；③ 语义反噬：guide 逼模型做 P1b 已搬到 correction 的世界轴推理（白费力 + 引入本可避免的错）；④ canonical image-local `facade` 块从不被一等产出，靠正则重建、脆。

### C3 · pipeline §3 verbatim 悬空（与 C1 同根）
- pipeline.py:351-352 让 correction "verbatim 用 reading_summary.md §3 立面翻译公式"；guide §4 L313 对称地说"correction 用 `facade_axis_note` 翻回世界系"。**两处都是 P1b-stale**：都假设 reading 产世界轴映射、correction 照抄；P1b 决定 correction 从 image-local `facade` + footprint/envelope **自己推**。kickoff 已不要求 reading 写 §3 → 运行时该引用悬空。

### C4 · uncaptured 载体/强度错位
- guide JSON 示例(§2 self_check, L246-254) 教模型把 trace 写进 **`self_check.uncaptured_visual_elements`**（嵌套·标 "**required**" 非空）；schema 是**顶层** `uncaptured: list=[]` + `self_check: dict|None`；validator `_uncaptured_list`(reading.py:51-59) 只读**顶层** `uncaptured` 或顶层 extra，**从不读嵌套** `self_check.uncaptured_visual_elements`。
- **核验**：模型照 guide 嵌套写 → linter 读不到 → 看顶层默认 `[]` → 只验 "exists+list" → PASS。**不 FAIL**，但旧"留痕≠静默丢失"纪律对机器门**完全失效**（door-heal trace / clutter 清单不被任何代码门看见）。

### C2 · scale_origin world placement
- guide §1(L94)+JSON(L111-116) 保留 `scale_origin.world_x/y/z_m`（世界落位 + 立面 base z）；schema.py:115 仅 `dict|None`、无门无消费者；correction/core 实际从 reading vectors+testdata+envelope/z-stack 重建世界系。**"prompt 还在、承重链断了"的死字段**，与"no world placement"矛盾。

## 4. 有意删（确认无须动作）
- **#55/#56**（Codex）：旧 reading 作世界轴 sign/base 承重源 + uncaptured 对 clean drawing 也必须非空——均为 P1b/架构有意删，**正确**。残留只是 guide 文档未随之清理（即 C1/C4 的文档侧），不是要恢复旧硬线。

## 5. 遗漏/缺口 → backlog（非冲突，不进本轮取舍）
- **#50 per-facade/floor window chain**：补 reading 文档"每 facade×floor 独立窗链、不复制 typical floor" + correction 侧 per-facade/floor expected-vs-output count/blank CROSS_CHECK flag。
- **拓扑禁字段门覆盖面**：`_FORBIDDEN_STROKE_KEYS` 补 `is_exterior/parent_window_ids/rooms`（与 guide §5 反例对齐）。

---

## 6. 冲突桶取舍（**用户定 Claude 不自决** — 待用户裁）

> C1+C2+C3 同根（reading→world-axis 残留），可统一处置；C4 独立。下面是 Claude 的核验后推荐 + 备选。

- **F1（C1+C2+C3 统一）· reading 纯 image-local 化**：清 guide §1/§4 + JSON 示例 → 教 canonical `facade` 块；`scale_origin` 改纯 image-local（去 world_x/y/z）；删 pipeline.py:351 的 §3 verbatim 依赖（correction 已有 envelope+image-local facade 自推世界系）。**子决策**：旧 `facade_axis_note`/`scale_origin` world 字段是 **(a) 降级为 optional 非承重 human-note 保留** 还是 **(b) 从 guide/示例彻底删**。
- **F2（C4）· uncaptured 纪律**：**(a)** 仅对齐载体（guide 改写顶层 `uncaptured`，低风险纯文档）；还是 **(b)** 在 (a) 基础上**恢复机器门**（有 door-heal/skip 时 `uncaptured` 必须非空 = 重新加一道确定性门，逆转 contracts §128 的有意放松）。

---

## 7. 决议 + 执行（2026-06-27，用户取舍后落地 `6.27_ReadingImageLocalUncaptured`）

- **Q1 = F1 / 删（B）**：reading 纯 image-local；`facade_axis_note` + `scale_origin.world_*` 从 guide 彻底删（schema 字段保留 extra=allow，老产物仍加载）。理由：旧表硬编码正交假设、在 C2/C4 斜交/多边形上**主动误导**，保留只会让模型继续做 P1b 已搬走的世界轴推理。
- **Q2 = F2 / 对齐 + door-heal 条件门（B）**：CROSS_CHECK flag（不 block），仅在真发生 heal 时要求 `uncaptured` 留痕，不误伤 clean drawing、不逆转 §128。
- **朝向 sign 表搬家**：从 reading guide §4 搬进 correction `A1 §2.2`（world placement 的正确归宿）；当前 LLM 仍做翻译（`Window.span`=世界坐标），A1 表给它正交默认约定 + North/West 翻号提醒；斜交从平面墙向推 θ = A1 已有 seam。
- **代码核验副产（两路都漏）**：`correction/facade.py:derive_facade_frame` 是**已建未接线**的确定性 facade→world 翻译（contracts §158b "应补"="全局坐标侧"，用户定先不启）；其 **East/West sign 与活口径相反 + E/W sign 测试未覆盖** → 接核前须对 gt 验，勿凭推理擅改（呼应 judge-gt-authoritative）。
- **落地**：reading 三 skill 文档 + A1 + pipeline.py + validator/checks/reading.py + 4 测试 → **346 passed/9 xfailed**。冲突桶 4 条全闭。遗漏 #50 / 禁字段门覆盖面 / derive_facade_frame 接核 = backlog。
