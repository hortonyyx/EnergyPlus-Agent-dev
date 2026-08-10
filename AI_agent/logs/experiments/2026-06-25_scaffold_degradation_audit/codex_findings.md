# Codex findings: reading-stage scaffold degradation candidates

Scope: independent forensic enumeration of scaffold-level changes that could plausibly degrade the image-reading stage. This file intentionally does not map any item to a specific observed symptom and does not prescribe fixes.

## Startup Prompt

- Candidate: the current startup prompt compresses the old error-budget warning and drops the concrete failure list.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:23-33` says: "perception errors can only be caught in phase 1" and "Once phase 1 misreads a dimension, offsets a coordinate, flips the elevation x-axis, or misses a stroke, phase 2 cannot backtrack".
  - New evidence: `AI_agent/guides/new_case_guide.md:257-260` says only: "Perception errors can only be caught here. **Prefer null over guessing.** Plan walls have no thickness... Do not copy testdata content".

- Candidate: the current prompt drops the concrete coordinate/stroke examples that anchored what "re-trace" means.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:15-17` gives examples: "the wall pen drew a wall stroke from (0,0)→(15,0)" and "the window pen drew a filled rectangle at elevation (1.4, 1.0)→(3.8, 2.8)".
  - New evidence: `AI_agent/guides/new_case_guide.md:252-255` defines the mental model without examples and adds only negatives: "It does NOT enclose strokes into rooms / judge exterior-vs-interior / say a window belongs to a wall / place anything in world coordinates."

- Candidate: the required-reading instruction no longer explains what each skill doc is for.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:37-43` names each doc and its role: "`guide.md` — flow / error budget / global constraints...", "`reading_guide.md` — how to *recognize* each element...", "`pen_library.md` — what to *do* with each recognized category".
  - New evidence: `AI_agent/guides/new_case_guide.md:263-264` only says: "Read the three skill docs (required): `skills/intake_pipeline/0_reading/{guide.md, reading_guide.md, pen_library.md}`."

- Candidate: the worked-example anchor is weakened; the old prompt identified the hand-authored example and its content, while the current prompt gives no path.
  - Old evidence: `a628856:skills/energyplus_mcp_twostep/phase1_prompt_template.md:26-27` says to read the schema and then use `phase1_vector/1f_view.json`, "已经由人工降级写好（10 根 wall stroke + 16 个 dim，**不要重写**）".
  - New evidence: `AI_agent/guides/new_case_guide.md:265` says only: "Follow the worked-example plan JSON's style (do not rewrite it)."

- Candidate: the startup prompt no longer tells the reader how to use `testdata_prompt.json` for contextual scale metadata.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:58-60` says: "Read metadata from `testdata_prompt.json` — but only to learn the floor count / floor height / total dimensions; **do not copy testdata_prompt content directly**".
  - New evidence: `AI_agent/guides/new_case_guide.md:257-260` says "Do not copy testdata content into the JSON" but the task list at `AI_agent/guides/new_case_guide.md:262-267` does not instruct the reader to read `testdata_prompt.json` for floor count, height, or total dimensions.

- Candidate: the old prompt enumerated the expected image/output set, while the current prompt leaves it generic.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:48-57` includes a source/output table for `2f_view.png`, `3f_view.png`, `South_view.png`, `North_view.png`, `East_view.png`, `West_view.png`, and `supp_plan.png`.
  - New evidence: `AI_agent/guides/new_case_guide.md:266` says only: "One JSON per image (`<case>/0_reading/<name>_view.json`); plans `image_kind=plan`, elevations `=elevation`."

- Candidate: door-healing guardrails are much shorter in the startup prompt.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:70-75` says to heal doors, but also: "only heal openings carrying a door symbol; doorless large open spans are kept, not welded... windows are not healed".
  - New evidence: `AI_agent/guides/new_case_guide.md:270` says only: "Heal door openings into one continuous wall (note it in `uncaptured_visual_elements`)."

- Candidate: the current startup prompt shortens the non-keep/clutter warning.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:81-84` lists "Columns / beams / decorative lines / index arrows / grid lines / stair treads" and says they are "recognized then logged... not traced as strokes".
  - New evidence: `AI_agent/guides/new_case_guide.md:273` lists only "Stairs/columns/grids/furniture" and says they are "recognize then log... NOT traced."

- Candidate: the one-stroke rule lost old prompt caveats about windows and door-healed walls.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:89-91` says: "One stroke per continuous stroke... Door openings do not break a wall... a window on a plan is a sub-face and also does not break a wall".
  - New evidence: `AI_agent/guides/new_case_guide.md:274` says only: "One stroke per continuous wall. Fill null when not found. OCR verbatim."

- Candidate: the elevation orientation contract in the startup prompt changed from world-axis/sign output to image-local fields, while other current docs still preserve the old world-axis wording.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:94-95` says: "Elevation facade_axis_note must include the sign".
  - New evidence: `AI_agent/guides/new_case_guide.md:275-276` says: "emit the image-local facade fields (`view_facade` from the trusted image name; do NOT write east/west into the in-image axis). World axis/sign is derived later".
  - Current conflict evidence: `skills/intake_pipeline/0_reading/guide.md:260-270` still says "`facade_axis_note` must state which world axis the local x maps to + the increasing direction (with sign)".

- Candidate: the old final summary required a facade local-to-world table; the current prompt does not.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:102-106` requires a `phase1_summary.md` with "the four-facade x_local ↔ world-axis table (actual filled values)".
  - New evidence: `AI_agent/guides/new_case_guide.md:278-280` asks for `0_reading/reading_summary.md` with "per-image confidence + repeatedly-null fields + schema feedback", with no facade axis table.

- Candidate: the current workflow wording is internally more ambiguous about when batching is allowed.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:99-101` says: "Do one pilot first... stop and let me review" and "After I approve the pilot, batch the rest".
  - New evidence: `AI_agent/guides/new_case_guide.md:278-284` says "Do one pilot image first, stop for review, then batch the rest" but also "Do the pilot, then wait for feedback."

## Guide

- Candidate: the guide's error budget was softened from an absolute "no backtrack" rule to a recoverability exception.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:47-53` says: "Every error about 'a value / position / stroke type in the image' must be caught in phase 1. Once phase 1 writes it wrong, phase 2 has no chance to backtrack."
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:47-52` says the error must be caught "unless the reading JSON still carries an independent redundant channel that pins the truth" and that "An offset coordinate with a surviving dimension chain and honest provenance can be recovered".

- Candidate: the guide adds provenance/confidence/dimension bookkeeping to strokes.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:112-123` shows a stroke with `id`, `pen`, `geometry`, and `note`.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:119-131` adds `"provenance": "seen"`, `"confidence": "high"`, and `"dimension_refs": []` inside the stroke example.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:170-174` adds a provenance mapping: "`seen = visual existence evidence; its numeric coordinate is estimated_stroke, NOT direct_measurement`" and "`dimension_derived = numeric transcribed_dimension`".

- Candidate: the guide adds two-channel/dimension anti-contamination rules and makes them part of self-check, increasing the number of simultaneous constraints the reader must satisfy.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:47-53` had only the general error-budget implications and no two-channel bullet.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:57-59` adds: "wall/window strokes and dimension chains are independent evidence channels" and "A dimension annotation, cumulative tick, extension line, or window/door sub-dimension must NEVER become a `wall` stroke."
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:297-299` adds self-check items for provenance/confidence and dimension-chain ticks.

- Candidate: the guide's schema example is internally inconsistent about the new provenance fields.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:112-158` has no provenance fields in any stroke example and no self-check requiring them.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:122-124` adds provenance fields to the first wall example, but the later window example at `skills/intake_pipeline/0_reading/guide.md:135-143` and polyline example at `skills/intake_pipeline/0_reading/guide.md:146-155` omit them, while `skills/intake_pipeline/0_reading/guide.md:297-298` says "every wall/window/wall_fill/outline stroke carries `provenance` + `confidence`".

- Candidate: the current guide retains world-axis `facade_axis_note` requirements that conflict with the current startup prompt and Pydantic schema.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:243-255` required `facade_axis_note` with world axis/sign and said phase 2 uses it to translate coordinates.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:258-270` keeps the same world-axis/sign requirement.
  - Conflicting new evidence: `AI_agent/guides/new_case_guide.md:275-276` says not to write east/west into the in-image axis, and `src/agent/reading/schema.py:13-18` says "World axis / sign / base are NOT here" and `facade_axis_note` is "not load-bearing".

- Candidate: the guide still documents `self_check.uncaptured_visual_elements`, while the Pydantic schema has a different top-level field.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:188-196` documents `self_check.uncaptured_visual_elements`.
  - New guide evidence: `skills/intake_pipeline/0_reading/guide.md:203-211` still documents `self_check.uncaptured_visual_elements`, and `skills/intake_pipeline/0_reading/guide.md:311` says it is "non-empty (required)".
  - New schema evidence: `src/agent/reading/schema.py:120-122` defines a top-level `uncaptured` list and says the linter "only enforces 'exists + list', never non-empty."

- Candidate: evolution-only from the earliest scaffold: door handling changed from preserving wall breaks to healing across door openings. This is not an endpoint difference against `127ba06`, but it is part of the scaffold evolution that remains current.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:76-79` says: "If a stroke that should be continuous is broken by an opening (such as a door opening), record two strokes."
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:180` says: "plan 不收 `door`... 门弧 / 门洞一律忽略不进 strokes".
  - New/current evidence: `skills/intake_pipeline/0_reading/guide.md:111-116` says a door opening "does **not** break the wall" and to "heal the two segments split by the door into one continuous wall stroke".

- Candidate: evolution-only from the earliest scaffold: the current guide/pen-library combination no longer uses an `other` pen even though the guide keeps "all_visible_strokes_captured" language.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:171-179` lists plan legal pens including `stair` and `other`; `a628856:...:151` has `all_visible_strokes_captured`.
  - New evidence: `skills/intake_pipeline/0_reading/guide.md:196-198` still has `all_visible_strokes_captured`, while `skills/intake_pipeline/0_reading/pen_library.md:55-63` says the legal plan pens are only `wall` and `window`, with "There is no `other` pen".

## Reading Guide

- Candidate: the current wall card adds a "Positive test" that invokes room/network relationships.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/reading_guide.md:143-152` ends the wall card with confusables: furniture/cabinet outline, dimension extension lines, and grid axis.
  - New evidence: `skills/intake_pipeline/0_reading/reading_guide.md:153-154` adds: "**Positive test**: an interior wall bounds rooms and joins the perimeter / corridor wall network. Cumulative dimension positions or ticks outside the outline do not bound rooms and do not become walls."
  - Evolution evidence: `git log -S 'Positive test' -- skills/intake_pipeline/0_reading/reading_guide.md` attributes this addition to `fa04ef6 6.22_ReadingHonestJudgeRouting`.

- Candidate: compared with the earliest single-file scaffold, the wall-recognition cue moved from visual pen features toward room-bounding closure language, and that wording remains current.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:173-178` defines plan `wall` by "粗黑实线 / 黑色填充矩形条" and `other` as "上述都不是但确实画了".
  - New/current evidence: `skills/intake_pipeline/0_reading/reading_guide.md:145-146` defines `wall` as "a long, straight-ish boundary line that, together with others, encloses rooms" and "meets other walls at corners to close a region."

- Candidate: the uncertainty path changed from a catch-all drawn category in the earliest schema to "best category guess / unknown log" in the recognition guide.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:178` says `other` applies when "上述都不是但确实画了" and includes "指北针、轴网编号、家具、标题块".
  - New evidence: `skills/intake_pipeline/0_reading/reading_guide.md:34-42` says when unsure, "give your best category guess **with low confidence in the note**, or label it `unknown` and record it".

## Pen Library

- Candidate: the legal pen set dropped `stair` and `other` from the earliest scaffold; the current scaffold requires non-keep marks to be logged instead of drawn.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:171-179` lists plan pens `wall`, `window`, `stair`, and `other`; `a628856:...:182-193` lists elevation pens `wall_fill`, `window`, `outline`, and `other`.
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:55-63` says legal pens are plan `wall`/`window` and elevation `wall_fill`/`window`/`outline`, and "There is no `other` pen and no `door` pen."

- Candidate: the current `unknown` action permits converting an uncertain geometric mark into a real pen.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:178` used `other` for "上述都不是但确实画了".
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:43` says `unknown` can "best-guess a real pen (wall/window) with a low-confidence note **only if clearly geometric**".

- Candidate: the current keep/ignore split makes more categories invisible to `strokes`.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:157-160` says `uncaptured_visual_elements` is for visible strokes that cannot be assigned to the current pen dictionary, with an empty array meaning the dictionary was enough.
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:45-51` says the keep-set is "just walls, windows, wall_fill, outline, dimensions, levels, and text" and everything else is the ignore-set, "recognized, then logged".

- Candidate: the pen-library door action changed from "not in strokes" in the earliest schema to an active wall-healing trigger.
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:180` says plan doors are ignored and not put into `strokes`.
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:22` says `door` is "**not drawn** → trigger wall-healing".

- Candidate: the current outline rule introduces a downstream-style judgment about whether outline "adds z".
  - Old earliest evidence: `a628856:skills/energyplus_mcp_twostep/phase1_vector_schema.md:188-189` says `outline` is "立面整体外轮廓粗线" and used "仅当外轮廓与 wall_fill 边不重合 / 单独画了一根整体外框".
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:26` says `outline` is used "**only when it adds z that wall_fill + levels don't**".

- Candidate: the current pen-library adds a new counterexample that can redirect floor-height elevation openings away from the `window` pen.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/pen_library.md:81-90` has no floor-height-door/window counterexample.
  - New evidence: `skills/intake_pipeline/0_reading/pen_library.md:91-92` adds: "tracing an elevation floor-height door as `\"pen\": \"window\"` because it breaks `wall_fill`" is wrong; "a door is recognized and logged, never emitted with the window pen".

- Candidate: the plan-window action contains topology-colored language even though the guide forbids parent/child judgments.
  - Old/current evidence: `skills/intake_pipeline/0_reading/pen_library.md:21` says plan `window` gives "x/y + which wall".
  - Current conflict evidence: `skills/intake_pipeline/0_reading/guide.md:250-251` says judging "which wall a window belongs to" is spatial topology left to correction.

## Schema

- Candidate: the Pydantic schema makes `pen` a free string and `geometry` a free dict, while the docs present a constrained pen/geometry contract.
  - Old markdown evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:114-120` says `pen` is tied to the legal set and `geometry.kind` is `line | rect | polyline`.
  - New schema evidence: `src/agent/reading/schema.py:35-43` defines `pen: str` and `geometry: dict = Field(default_factory=dict)`.
  - New schema evidence: `src/agent/reading/schema.py:20-21` says "`extra=\"allow\"` everywhere keeps older artifacts loadable; the deterministic linter ... enforces the real invariants."

- Candidate: the schema shifts elevation orientation to image-local fields and explicitly de-loads the old world-axis note.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:243-255` says `facade_axis_note` must include world axis + increasing direction and phase 2 uses it to translate to world coordinates.
  - New schema evidence: `src/agent/reading/schema.py:13-18` says facade orientation is "image-local only", "World axis / sign / base are NOT here", and `facade_axis_note` is retained "but is not load-bearing."
  - New prompt evidence: `AI_agent/guides/new_case_guide.md:275-276` matches the schema by saying world axis/sign is "derived later by 1_correction".

- Candidate: the schema adds dimension-chain closure fields and parsed numeric values beyond the old simple dimension annotation.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:161-170` has dimension fields `id`, `text`, `from`, `to`, `axis`, and `note`.
  - New schema evidence: `src/agent/reading/schema.py:55-70` adds `text_verbatim`, `value_m`, `chain_id`, `role`, `order`, and `anchor`.
  - New schema evidence: `src/agent/reading/schema.py:7-11` explains this is so "dimension-chain-closure check (Σ segments == overall) can run".

- Candidate: the schema adds stroke provenance/confidence/dimension refs after the first Pydantic version.
  - Old schema evidence: `0d267bf:src/agent/reading/schema.py:35-43` defines `Stroke` with `id`, `pen`, `geometry`, and `note`.
  - New schema evidence: `src/agent/reading/schema.py:43-45` adds `provenance`, `confidence`, and `dimension_refs`.

- Candidate: the schema adds `room_labels`, admitting room-role observations from labels or furniture inside the reading artifact.
  - Old schema evidence: `0d267bf:src/agent/reading/schema.py:94-107` defines `ReadingView` without `room_labels`.
  - New schema evidence: `src/agent/reading/schema.py:97-119` defines `RoomRoleObservation` as "Topology-light room-role observation from visible labels or furniture" and adds `room_labels` to `ReadingView`.
  - Current doc tension evidence: `skills/intake_pipeline/0_reading/pen_library.md:36-38` says `furniture`, `sanitary`, and `equipment` are "ignore → log", while `skills/intake_pipeline/0_reading/guide.md:250-251` leaves room/wall topology to correction.

- Candidate: the schema's `uncaptured` contract diverges from the guide/prompt's `self_check.uncaptured_visual_elements` contract.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md:188-196` documents only `self_check.uncaptured_visual_elements` and says it is required.
  - New schema evidence: `src/agent/reading/schema.py:120-122` defines top-level `uncaptured` and says a clean drawing may use `[]`, with the linter enforcing only "exists + list".
  - New prompt/guide evidence: `AI_agent/guides/new_case_guide.md:270` and `skills/intake_pipeline/0_reading/guide.md:203-211` still tell the reader to use `uncaptured_visual_elements`.

- Candidate: the schema permits metadata/image-name orientation evidence, whereas the old prompt bounded metadata use more narrowly.
  - Old prompt evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md:58-60` says metadata is only for "floor count / floor height / total dimensions" and the JSON should "reflect only what is seen in the image".
  - New schema evidence: `src/agent/reading/schema.py:13-15` says `view_facade` comes "from the trusted image name/metadata"; `src/agent/reading/schema.py:74-80` allows orientation evidence sources including `"image_name"` and `"metadata"`.

- Candidate: the schema broadens accepted `image_kind` values beyond what the current startup prompt emphasizes.
  - Old evidence: `127ba06:skills/energyplus_mcp_twostep/phase1/reading_guide.md:87-100` says only plan and elevation are in scope and non-orthographic views are out of scope.
  - New schema evidence: `src/agent/reading/schema.py:31-32` defines `ImageKind = Literal["plan", "elevation", "section", "supplementary", "other"]`.
  - New prompt evidence: `AI_agent/guides/new_case_guide.md:266` mentions only plans and elevations.

## Highest-Suspicion Candidates

- The startup prompt compression: especially the shortened error budget, missing per-doc role descriptions, missing concrete examples, and shortened guardrails.
- The current orientation split/conflict: startup prompt and schema say image-local/no world sign, while the guide still requires `facade_axis_note` with world axis/sign.
- The `fa04ef6` reading-honest additions: recoverability exception, provenance/confidence/dimension_refs, and the added wall-card positive test.
- The schema/docs mismatch around `uncaptured` versus `self_check.uncaptured_visual_elements`.
- The removal of `other`/`stair` drawn pens from the earliest scaffold plus the current `unknown` best-guess path.
- The added `room_labels` schema channel and other topology-colored wording inside reading-stage artifacts.
