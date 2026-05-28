# 新建测试样例操作指南 —— 两步法 Step 4（临时版）

> **临时文档**。当前主线 [new_case_guide.md](new_case_guide.md) 的 Step 4 仍是单步法（半人工 intake）。本文件只覆盖**两步法的 Step 4**（拆 4a phase1 / 4b phase2），用模板临时驱动，方便 B1.5.a 异图 POC v2 期间跑两步法。
>
> **定位**：Step 1–3（备素材 / 建目录 / 写 testdata_prompt.json）与 Step 5–7（下游自动跑 / 验收 / 留痕）**完全复用 [new_case_guide.md](new_case_guide.md)**，本文件只替换中间的 Step 4。
>
> **何时退役**：POC v2 通过、按 [plan.md B1.5.c/e](plan.md) 把 `intake_node` 改成两步串行 + 正式重写 new_case_guide.md 后，本临时文件并入主指南删除。决策背景见 [floorplan_redraw_strategy.md §10](floorplan_redraw_strategy.md)。

---

## 零、与单步法的差异

| 阶段 | 单步法（new_case_guide.md）| 两步法（本文件）|
|---|---|---|
| Step 1–3 | 备素材 / 建目录 / testdata_prompt.json | **完全一致** |
| Step 4 | 一个会话：图 + 文本 → `intake_output.json` | **拆两步**：4a 识图→矢量 JSON；4b 矢量 JSON→`intake_output.json` |
| 规则库 | [skills/energyplus_mcp/](../skills/energyplus_mcp/)（单步法，中文）| [skills/energyplus_mcp_twostep/](../skills/energyplus_mcp_twostep/)（两步法，英文）|
| Step 5–7 | 下游自动跑 + L1–L4 + 留痕 | **完全一致**（下游入口见 §三）|

**案例目录**：两步法语料放 [test_data/SmallOffice_TwoStep/](../test_data/SmallOffice_TwoStep/)`<case>/`（与单步法 `SmallOffice/` 并列）。phase1/phase2 全部中间产物落这里。

误差预算（两步法的核心）：phase1 看图、只产「图上看到了什么」；phase2 不看图、只对矢量 JSON 做拓扑推理。任何图相关的错只能在 phase1 截断，phase2 只引入纯推理错。详见 [phase1_guide.md §0.1](../skills/energyplus_mcp_twostep/phase1/guide.md)。

---

## 一、Step 4a · phase1 识图（图 → 矢量 JSON）

> **目标**：每张图（逐层平面 + 各立面 + 补充图）→ 一份矢量 JSON（语义笔 strokes + 尺寸链 + OCR），外加一份 `phase1_summary.md`（含 4 立面 local↔world 翻译公式）。**只识图、不做拓扑**。

1. 在仓库根新起一个独立 Claude Code 会话，选多模态强模型（Opus 4.7）。
2. 把下面 `---` 之间整段作为首条消息粘进去，并**按本 case 改路径**（图名表 / 目录）。
3. 会话会先做一张 pilot（如 `2f_view`），停下等你审；审 OK 后再 batch 其余图。

#### Phase 1 启动 prompt（粘进新会话；按 case 改图名表）

> 在 `EnergyPlus-Agent-dev` 项目根新起会话（多模态强模型，如 Opus），把下面 `---` 之间整段作首条消息粘入。规则真身在 [skills/energyplus_mcp_twostep/phase1/](../skills/energyplus_mcp_twostep/phase1/)（`guide.md` / `reading_guide.md` / `pen_library.md`），会话运行时读取，不必拷进 case 目录。

---

I am doing **phase 1 of the two-step intake: redraw the source image with semantic pens** — trace
every visible structural stroke on the architectural drawing by type (wall pen / window pen / wall_fill pen / ...),
and do **no spatial-topology reasoning** at all.

## Mental model

Phase 1 = "re-trace the source image with a set of semantically labeled pens". For example "the wall
pen drew a wall stroke from (0,0)→(15,0)", "the window pen drew a filled rectangle at elevation
(1.4, 1.0)→(3.8, 2.8)".

Phase 1 does **not**: enclose multiple wall strokes into "a room" / judge whether a wall is
"exterior or interior" / say "this window belongs to that wall" / write "the z_min/z_max of the
middle window on the south elevation F2". **All topology reasoning is left to phase 2.**

## Error budget (key, see guide.md §0.1)

Phase 1 sees the image, phase 2 does not. So:

- **perception errors can only be caught in phase 1**. Once phase 1 misreads a dimension, offsets a
  coordinate, flips the elevation x-axis, or misses a stroke, phase 2 cannot backtrack — it takes
  what it gets as truth
- **prefer null over guessing**. null = "I couldn't see it / it isn't dimensioned", which phase 2
  knows is missing. A guessed value is contamination
- EP zones are enclosed by surfaces (2D faces), **walls have no thickness** — plan walls'
  `thickness_m` is always `null`, do not estimate visual stroke width

## Your task

1. Read all three phase-1 skill docs (**required**):
   - `skills/energyplus_mcp_twostep/phase1/guide.md` — flow / error budget / global constraints / output container / door-healing /
     facade_axis_note spec / self-check / downstream contract
   - `skills/energyplus_mcp_twostep/phase1/reading_guide.md` — how to *recognize* each element across drawing styles (the
     convention cards + the semantic-category vocabulary)
   - `skills/energyplus_mcp_twostep/phase1/pen_library.md` — what to *do* with each recognized category (which pen / keep-or-ignore /
     wall_fill convention)
2. Look at the worked example JSON (already hand-authored, e.g. the first plan view — **do not
   rewrite it**), and follow its style for the remaining images
3. Produce one JSON per remaining image, e.g.:

| source PNG | output JSON | image_kind |
|---|---|---|
| `2f_view.png` | `phase1_vector/2f_view.json` | plan |
| `3f_view.png` | `phase1_vector/3f_view.json` | plan |
| `South_view.png` | `phase1_vector/South_view.json` | elevation |
| `North_view.png` | `phase1_vector/North_view.json` | elevation |
| `East_view.png` | `phase1_vector/East_view.json` | elevation |
| `West_view.png` | `phase1_vector/West_view.json` | elevation |
| `supp_plan.png` | `phase1_vector/supp_plan.json` | decide yourself |

Read metadata from `testdata_prompt.json` — but only to learn the floor count / floor height / total
dimensions; **do not copy testdata_prompt content directly into the phase 1 JSON** (phase 1 should
reflect only what is seen in the image).

## Core discipline

1. **plan and elevation use different, minimal pen sets** (pen_library.md):
   - plan legal pens = `wall` / `window`
   - elevation legal pens = `wall_fill` / `window` / `outline`
   - there is **no `other` pen and no `door` pen**; stairs / columns / grids / furniture / decoration
     are recognized then logged in `uncaptured_visual_elements`, **not traced** (do not trace stair treads)
   - cross-use is an error. E.g. an elevation wall body must use `wall_fill`, not `wall`
2'. **Heal door openings into continuous walls (door-healing, guide.md §2.1)**: when you see a door
   leaf / arc on a plan, do not draw a door pen — heal the walls on its two sides into **one
   continuous wall stroke** + a note `healed door opening at <position>` (a door is ignored in EP, a
   wall is a continuous boundary face). Guardrails: only heal openings carrying a door symbol;
   doorless large open spans are kept, not welded (those are real topology signals); windows are not
   healed. Record each heal in `uncaptured_visual_elements`
2. **Split elevation wall bodies as "one wall_fill stroke per floor"** (pen_library.md §3). For a 3-story
   building, each elevation produces 3 wall_fills. Even if the gray looks visually continuous, split
   by the dimension chain's per-floor z ranges
3. **Topology is not phase 1's job.** Forbidden fields: `is_exterior` / `parent_wall_id` / `rooms[]`
   / any "X belongs to Y / X faces outside / X encloses" semantics
4. **Do not expand the pen set, and do not trace non-keep marks.** Columns / beams / decorative lines /
   index arrows / grid lines / stair treads are **recognized then logged in `uncaptured_visual_elements`**,
   not traced as strokes; do not invent enum values like `cornice` / `column` / `level_line` and do
   not fall back to an `other` pen (there is none)
4'. **`uncaptured_visual_elements` is required**: anything "seen but not drawn into strokes" must be
   acknowledged — out-of-dictionary strokes + clutter actively excluded by selective extraction
   (furniture / paving / texture / room text boxes) + healed doors. Even when the dictionary is truly
   enough, write a note rather than leaving it empty ("acknowledged skip" ≠ "silent loss")
5. **One stroke per continuous stroke.** E.g. the south perimeter wall from (0,0) to (15,0) is **one**
   wall stroke, do not split into 3. Door openings do not break a wall (heal into a continuous wall,
   see 2'); a window on a plan is a sub-face and also does not break a wall
6. **Fill null when not found**, no defaults. Plan walls' `thickness_m` is always null (simulation
   doesn't use it, guide.md §0.2); other fields not found in the image are also null
7. **Elevation facade_axis_note must include the sign** (guide.md §4 four-facade table)
8. **OCR verbatim**; if there are no text labels, leave ocr_texts as an empty array

## Workflow

1. Read guide.md + reading_guide.md + pen_library.md + the worked-example plan JSON (understand the style)
2. Do one pilot first (e.g. `2f_view.png`), then stop and let me review — **do not batch all images at once**
3. After I approve the pilot, batch the rest (other plans + elevations + supplemental plan)
4. When all are done, write a `phase1_vector/phase1_summary.md`:
   - per-image confidence self-assessment (high/medium/low, with reasons)
   - which fields were repeatedly null / unknown
   - the four-facade x_local ↔ world-axis table (actual filled values)
   - your feedback on the schema: where it falls short / where it is redundant / which pen enum values are insufficient

## Boundaries

- Do not modify any file under [src/](src/), [skills/](skills/), [AI_agent/](AI_agent/)
- Do not modify the worked-example JSON (it is the reference)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not produce IntakeOutput fields (zone_specs / surface_specs / fenestration_specs / ...), that is all phase 2's job

When ready, do the pilot first, then stop and wait for my feedback.

---
4. 人工校验：用 [Tool_scripts/render_vector_to_svg.py](../Tool_scripts/render_vector_to_svg.py) 把矢量 JSON 渲成 SVG，肉眼比对原图，重点看：
   - 杂物（家具/铺装/纹理）有没有被误当 wall/window（假阳性，最致命）
   - 真墙/真窗有没有漏（假阴性）
   - 门洞有没有按 v1.3 规则 heal 成连续墙（带门符号才补、留痕）
   - `uncaptured_visual_elements` 是否如实登记了「看到但没画」的

**产物**：`<case>/phase1_vector/{1f_view,2f_view,...,South_view,...}.json` + `<case>/phase1_vector/phase1_summary.md`。

---

## 二、Step 4b · phase2 拓扑（矢量 JSON → IntakeOutput）

> **目标**：读 phase1 矢量 JSON + testdata_prompt.json，按 [phase2_rules.md](../skills/energyplus_mcp_twostep/phase2/rules.md) 推出 11 字段 `IntakeOutput`。**不看原图**。

两条路径，任选：

### 路径 A — 会话（Opus 等）

新起会话，把下面 `---` 之间整段改好路径后粘入。产 `intake_output.json` + `self_check.md` + （如有）`phase2_followup_notes.md`。

> 规则真身在 [skills/energyplus_mcp_twostep/phase2/rules.md](../skills/energyplus_mcp_twostep/phase2/rules.md) + [phase1/guide.md](../skills/energyplus_mcp_twostep/phase1/guide.md) + [phase1/pen_library.md](../skills/energyplus_mcp_twostep/phase1/pen_library.md)，会话运行时读取。自动路径（路径 B）由 `Tool_scripts/run_phase2_deepseek.py` 跑，不用本 prompt。

---

I am doing phase 2 of the two-step intake. Phase 1 (image → vector JSON) is done (products in
`phase1_vector/`). This session does only **phase 2: vector JSON → IntakeOutput** — no image,
pure text reasoning.

## Required reading

Read in order:

1. `skills/energyplus_mcp_twostep/phase2/rules.md` — full phase 2 rules (input/output / coordinate translation formulas /
   IntakeOutput field derivation order / naming rules / vertex synthesis / self-check)
2. `skills/energyplus_mcp_twostep/phase1/guide.md` + `skills/energyplus_mcp_twostep/phase1/pen_library.md` — phase 1 output format reference (only to understand what your input looks like; phase 2 does not need the reading guide)
3. `phase1_vector/phase1_summary.md` — phase 1 summary (includes the 4-facade local↔world translation formulas, **apply directly**)
4. **every** phase 1 vector JSON under `phase1_vector/` (do not assume a fixed file set):
   - all floor-plan JSONs (`<N>f_view.json`) and all facade-elevation JSONs (`<Name>_view.json`)
   - any supplementary / section JSONs if present (e.g. `supp_plan.json`) — read them too
   - do not assume 3 floors or 4 facades; enumerate what actually exists
5. `testdata_prompt.json` — metadata (floor count, area, city, use)

## Task

Following the field derivation order in `rules.md` §3, produce the IntakeOutput Pydantic JSON, written to:

```
phase2_intake/<model>/intake_output.json
```

For the format, reference the IntakeOutput Pydantic definition in [src/agent/state.py](src/agent/state.py).
All 11 fields must be present: building / site_location / zone_specs / material_specs /
schedule_specs / construction_specs / surface_specs / fenestration_specs / hvac_specs / people_specs
/ lights_specs.

The 9 `*_specs` fields are **natural-language instructions** (not structured data), but must be
explicit, mechanically executable, and internally consistent — the 9 downstream subagents rely on
these strings. Naming rules are strict (letters/digits/`_` only, literally consistent across fields,
no template writing).

## Mental model

- You have already "seen the image" — all visual info is in the phase 1 JSON. **Do not go back to the original PNG**
- Any error tied to "a value in the image" is phase 1's fault (already frozen); you can only
  introduce pure reasoning errors (topology, naming, field format, coordinate translation)
- A `null` in the phase 1 JSON = "phase 1 didn't see it", **do not treat it as 0**; if missing,
  annotate accordingly in your output
- Elevation local coordinates must be translated back to the world system per the `phase1_summary.md`
  §3 formula, **do not re-derive**

## Workflow

1. Read the required docs (rules / schema / summary / testdata_prompt + sample a few JSONs)
2. Walk through phase2_rules §3 Step 1→7 mentally, confirm you are confident before writing
3. Write `phase2_intake/<model>/intake_output.json` — write it all at once, **do not append in multiple passes**
4. After writing, run the self-check (phase2_rules §7, 9 items) and write the result to `phase2_intake/<model>/self_check.md`
5. If phase2_rules does not cover something and you had to "improvise" to finish, record it in
   `phase2_intake/<model>/phase2_followup_notes.md` so the rules can be extended later

## Boundaries

- Do not modify any phase1_vector/ file (phase 1 products are frozen)
- Do not modify rules.md / phase1/guide.md / phase1/pen_library.md (put suggestions in phase2_followup_notes.md)
- Do not modify any file under [src/](src/) / [skills/](skills/) / [AI_agent/](AI_agent/)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not look at the original PNGs (phase 2 discipline)

When done, output three files: `intake_output.json` / `self_check.md` / `phase2_followup_notes.md` (if any).

---

### 路径 B — DeepSeek 自动跑

```bash
python Tool_scripts/run_phase2_deepseek.py --case test_data/SmallOffice_TwoStep/<case>
```

phase1 矢量 JSON 现在**按目录自动扫描**（`phase1_vector/*_view.json`，平面 `<N>f_view` 在前、立面在后），楼层/立面数不同的 case 无需再改脚本。

**产物**：`<case>/phase2_intake/<model>/intake_output.json`（或你约定的位置）。

### L1 校验（同 new_case_guide.md §4.4）

```bash
python -c "
import sys, json
sys.path.insert(0, '.')
from src.agent._share import ensure_schema_initialized
ensure_schema_initialized()
from src.agent.state import IntakeOutput
data = json.loads(open('<path>/intake_output.json', encoding='utf-8').read())
IntakeOutput.model_validate(data); print('OK 11 fields')
"
```

通过 = 可进 Step 5；Pydantic 报错 = 回 4b 让模型改 JSON 重存。

---

## 三、接 Step 5（下游自动跑）

> Step 5–7 流程与 [new_case_guide.md §五–§七](new_case_guide.md) 完全一致（含 `跑下游 <case>` 对话触发、L1–L4 验收、`记录这次跑` 留痕）。

[scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 现有 `--base-dir`，两步法 case 直接指向 `SmallOffice_TwoStep/`，不必再往 `SmallOffice/` 搬：

```bash
# 先把 phase2 产出的 intake_output.json 放到 <case>/output/ 下（--intake-from 相对 <case>/ 解析）
python scripts/run_full_pipeline.py <case> \
  --base-dir test_data/SmallOffice_TwoStep \
  --intake-from output/intake_output.json
```

> 正式两步法主线（B1.5.c）会把 `intake_node` 改成 phase1+phase2 串行调用，连 `--intake-from` 手工搬运一并消失。

---

## 四、与正式版的关系

- 本文件是 POC v2 期间的**操作脚手架**，规则真身在 [skills/energyplus_mcp_twostep/](../skills/energyplus_mcp_twostep/)（英文、纯当前版本 spec）。
- POC v2（[plan.md B1.5.a](plan.md)）通过 → 按 [plan.md B1.5.c/e](plan.md) 把两步法切成 `intake_node` 运行时串行调用 + 把 Step 4 两步正式写进 [new_case_guide.md](new_case_guide.md)（拆 4a/4b、改引用到 twostep 库、去掉 §三 的目录接缝）→ 删除本临时文件。
