# Sonnet Plan Recognition Diagnosis - sm21

Date: 2026-06-21

Scope: local tree only. I did not inspect source images. Conclusions below are from reading JSONs, checks, judge verdicts, run reports, skill text, archived local skill snapshots, and git history. Any statement about what the drawings "show" is therefore either from judge text or from another artifact, not from my own image-grounded inspection.

## Executive Conclusion

Q1: The Sonnet degradation is best explained by a case-specific Sonnet recognition failure on sm21 plan clutter and dimension/window tick marks, with additional run variance on elevation doors. I do not find evidence that a recent 0_reading guide/schema change introduced the failure. The relevant recognition rules predate this round, and the only 2026-06-21 reading-path schema change is optional `room_labels`, which these artifacts do not use.

Q2: The local evidence does not support a clean "prompt shifted to elevations, so plans declined" root cause. There is a real system-level trend toward stronger facade/elevation handling in schema, validators, and correction rules, but the sm21 Sonnet failures originate in 0_reading plan perception before correction. The plan decline is more likely a combination of hard sm21 plan cues, Sonnet variance, missing structured provenance for dimension-derived wall coordinates, and a J0/J1 gate gap that let the first bad plan read pass J0.

## Q1 - Why Did Sonnet 0_reading Get Worse?

### A. Concrete Evidence / Failure Pattern

#### Run 1: `run_2026-06-20_sonnet_reading`

- The run report says the pipeline stopped at `human_redraw_required@1_correction`, not directly at J0. `0_reading` was marked `judge_pass`, while `1_correction` required human redraw: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/RUN_REPORT.md:3`, `:20-23`.
- The run manifest confirms that J0 was non-blocking but J1 was blocking and rooted to `0_reading`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/baseline.json:94-106`.
- J1 found two spurious interior partitions: F1 south over-split into 4 cells instead of 3, and F2 south over-split into 5 cells instead of 4. It also says window fidelity passed: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/1_correction/attempts/001/judge.json:6-18`.
- J1 explicitly attributes the root to Sonnet 0_reading tracing exterior south-wall dimension ticks / cumulative door-window positions as interior partitions, including F1 `3440/7560/11560` and F2 `5510`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/1_correction/attempts/001/judge.json:31-35`.
- The raw F1 plan JSON contains south-row wall strokes at x=3.44, x=7.56, and x=11.56, while the judge says true south-room dividers should be around x=5/x=10: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/1f_view.json:101-132`.
- The raw F2 plan JSON contains a south-row wall at x=5.51 in addition to x=3.75, x=7.50, and x=11.25, matching J1's extra-wall diagnosis: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/2f_view.json:90-132`.
- Door handling was not the problem in this first Sonnet run. The South and West elevation self-checks identify the F1 doors and log them as not-window / not-traced: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/South_view.json:415-423`; `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/West_view.json:182-195`.

#### Run 2: `run_2026-06-21_sonnet_reading_retry`

- The retry run report stopped directly at `human_redraw_required@0_reading`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/RUN_REPORT.md:3`, `:20-23`.
- The J0 judge marks `clutter traced as structure` severe: interior dimension ticks were traced as walls, including F1 x=3.44 and x=6.3, with true dividers at x=5/x=10; it also says F2 had an extra x=7.74 near-duplicate: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/attempts/001/judge.json:10-14`.
- The J0 judge also marks `pen misclassified` severe because South-F1 and West-F1 doors were emitted with the `window` pen, inflating facade window counts: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/attempts/001/judge.json:15-18`.
- The retry F1 plan JSON shows south-row walls at x=3.44, x=6.30, and x=10.00, so the first two are direct evidence of over-reading dimension/window positions as partitions: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/1f_view.json:101-132`.
- The retry South elevation JSON emits a door as `pen: "window"` with `x_range_m=[0.00,0.60]`, while its note admits it is a door: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/South_view.json:103-111`.
- The retry West elevation JSON similarly emits the F1 double door as `pen: "window"` and says "treating as an opening captured with window pen": `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/West_view.json:43-52`.
- The West retry self-check is internally contradictory: it identifies SW2 as a door, cites that the pen library says elevation doors are "not drawn (note only)", then says it captured it as a window because it visually breaks wall_fill: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/West_view.json:185-193`.
- The deterministic checks do not catch this class. They pass structure checks such as unique ids, legal pen kind, nondegenerate geometry, and parseable dimensions; dimension-chain closure is not applicable because no `chain_id` fields are present: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/attempts/001/checks.json:7-89`.

#### Good sm21 GPT-5.4 Contrast

- The gpt54 run completed clean with 14 zones and 15 windows: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/RUN_REPORT.md:1-3`.
- GPT-5.4 J0 says interior dividers were at the expected F1 x=5/x=10 and F2 south x=3.75/7.5/11.25, not exterior-wall dimension ticks; it also says both gt doors were healed/logged rather than traced as windows: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/attempts/002/judge.json:6-23`, `:30-38`.
- GPT-5.4 F1 plan JSON has bottom/south partitions only at x=5.0 and x=10.0: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/1f_view.json:148-180`.
- GPT-5.4 F2 plan JSON has south partitions at x=3.75, x=7.5, x=11.25 and the north conference partition at x=7.5: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/2f_view.json:114-180`.
- GPT-5.4 West elevation logs the ground-floor double door as uncaptured and explicitly says it is not a window: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/West_view.json:78-82`.

#### Historical sm20 Sonnet-Like Positive Control

- The sm20 baseline is clean, EP-completed, 19 zones: `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/RUN_REPORT.md:1-3`.
- Its reading summary labels every plan/elevation high confidence, but also says the plans are clean CAD with no furniture, doors, or clutter: `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading/reading_summary.md:5-13`.
- The sm20 1F and 2F plan JSONs show clean regular grid partitions without window/dimension sub-edge over-reading: `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading/1f_view.json:57-122`; `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading/2f_view.json:57-133`.
- Therefore sm20 proves Sonnet can follow the schema on clean plans, but it is not an equal control for sm21 because sm20 lacks the sm21 furniture/door/dimension-chain noise called out in the sm21 request metadata and judges.

### B. Most Likely Root Causes, Ranked

1. High confidence: Sonnet has a sm21-specific visual discrimination weakness on interior walls versus exterior dimension/window/door tick marks.

Both Sonnet attempts over-read plan sub-dimension positions as partitions, while GPT-5.4 does not. The first Sonnet run's J1 root-cause note is exact and matches the raw JSON coordinates. The relevant failure is not missing whole regions; both judges say the broad north/corridor/south bands are present. The defect is over-segmentation inside the south bands.

2. Medium confidence: elevation door handling is partly model/run variance, partly residual prompt ambiguity.

The first Sonnet run handles South-F1 and West-F1 doors correctly, while the retry converts them to `window`. That is run variance. But the retry's self-check shows why the prompt is vulnerable: Sonnet knew there is no door pen and incorrectly chose `window` to represent an opening. The current pen library says elevation `door` is "not drawn (note only)": `skills/intake_pipeline/0_reading/pen_library.md:17-23`. The guide also says there is no door pen and doors should be logged/healed, not traced: `skills/intake_pipeline/0_reading/guide.md:276-283`; `skills/intake_pipeline/0_reading/pen_library.md:55-63`. This is clear to a careful reader, but the "opening breaks wall_fill" edge case needs a stronger explicit negative example.

3. Medium confidence: J0 currently under-catches plan over-segmentation that J1 later catches.

The first Sonnet run was accepted by J0 (`judge_pass`) even though J1 later rooted the redraw failure to 0_reading. J0 is designed to catch clutter-as-structure and door healing errors: `skills/intake_pipeline/0_reading/judge_rubric.md:12-32`. It did catch the retry, but missed the first bad plan. That is not the cause of the bad read, but it explains why the first run advanced and failed later.

4. Low confidence: a recent reading-skill/schema change caused the worsening.

I find evidence against this. The core wall/window/door/dimension recognition lines are blamed to the 2026-05-26 phase1 split, not to this round: `skills/intake_pipeline/0_reading/reading_guide.md:143-184` and `:255-265` blame to `127ba06c`. The current action mapping for doors and windows is also from `127ba06c`: `skills/intake_pipeline/0_reading/pen_library.md:17-23`. Diffing the 2026-05-28 archived phase1 guide/reading_guide/pen_library against current `skills/intake_pipeline/0_reading/` showed only terminology/path rename changes, not recognition-content changes. The only 2026-06-21 change in `src/agent/reading/` is optional room-role observations: `src/agent/reading/schema.py:94-116`, blamed to `04a02a86`; the inspected sm21/sm20 reading artifacts contain no `room_labels`.

### C. What I Cannot Determine Without Seeing Images

- Whether the exact marks at x=3.44, x=6.30, x=7.56, x=11.56, and x=5.51 visually look like wall stubs, dimension ticks, window jambs, furniture edges, or some combination.
- Whether the South-F1 and West-F1 elevation door symbols are visually unambiguous doors, glazed doors, storefront panels, or window-like openings. The judges say they are doors; I cannot independently verify that.
- Whether GPT-5.4 is visually faithful or merely aligned with GT/judge expectations.
- Whether any apparent "elevation improvement" is visible in the drawings, or only in JSON/judge/count artifacts.
- Whether the exact manual prompt used for each Sonnet run had extra instruction text not committed in the repo. `llm.yaml` says 0_reading is currently manual / Claude Code and not API-configured: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/llm.yaml:10-12`.

### D. Candidate Fix Directions

Do not implement in this diagnosis pass.

- Add an explicit negative example to 0_reading docs: "elevation floor-height door rectangles are not windows even when they are openings in wall_fill; log them only."
- Add a plan-specific "candidate interior wall audit" to the prompt/checklist: for every vertical partition candidate, record whether it visually bounds rooms and joins the relevant corridor/perimeter walls, or whether it is only a dimension/window/door sub-position.
- Add a J0 judge checklist item for plan row cell counts and over-segmentation by bands: F1 3N+corridor+3S; F2 2N+corridor+4S for sm21-like rectangular plans. This belongs in the judge packet, not as blind topology reasoning in the reading JSON.
- Add structured provenance/confidence on strokes: `visual_wall_boundary` versus `dimension-derived_estimate` versus `low_confidence`. A0 already says perception should not emit estimated coordinates indistinguishable from measured strokes and should carry provenance/confidence: `skills/intake_pipeline/1_correction/A0_contract.md:226-245`.
- In the deterministic reading linter, add a non-blocking simple rectangular plan cell-count/tripwire when `testdata_prompt.json` has per-floor `thermal_zones`. The sm21 metadata says floor 1 has 7 thermal zones and floor 2 has 7: `case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json:7-10`.
- Store the exact 0_reading prompt/session model in run artifacts, since `llm.yaml` only records downstream LLM config and marks 0_reading as manual.

## Q2 - Why Did Plan Recognition Decline While Elevation Recognition Improved?

### A. Concrete Evidence / Failure Pattern

The premise is partly true but needs qualification:

- For the degraded Sonnet artifacts, plan recognition definitely declined: both Sonnet attempts over-segment plans from dimension/sub-dimension cues. Evidence is in Q1.
- Elevation recognition is not uniformly improved across those same Sonnet artifacts: the first Sonnet run handled elevation doors/windows correctly, but the retry misread South-F1 and West-F1 doors as windows. The retry J0 explicitly says South count inflated to 8 vs truth 7 and West count to 2 vs truth 1: `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading/attempts/001/judge.json:15-18`.
- The accepted gpt54 run does have strong elevation/window results, and its final run completed clean: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/RUN_REPORT.md:1-3`; its J0 says window counts match truth and doors are healed/logged: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/attempts/002/judge.json:6-23`, `:30-38`.
- The older sm21 Opus run report says 0_reading itself was faithful for both plans and elevations, including correct window counts and West-F1 door absence: `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/RUN_REPORT.md:18-39`.
- A separate local diagnosis found the historical South-2F window-x bug in `run_2026-06-16_opus_e2e` was not a 0_reading elevation miss; 0_reading South spans were correct and the error began in 1_correction: `AI_agent/logs/review/request/2026-06-21_sm21_south2f_window_x_diagnosis.md:13-17`, `:58-63`, `:160-185`.

#### Hypothesis Test Against Git Diffs

Evidence supporting a system-level elevation/facade emphasis:

- M1 introduced P1a dimension-chain/provenance fields and P1b facade image-local fields in the reading schema. The schema docstring explicitly calls out facade image-local fields and says world axis/sign/base are derived by 1_correction: `src/agent/reading/schema.py:1-18`.
- The deterministic reading validator has a dedicated elevation facade-field invariant: `src/validator/checks/reading.py:361-374`.
- The correction contract has a `perimeter_core` profile where exterior footprint, facade orientation, floor heights, roof/ground exposure, facade window area, and WWR are strict, while internal partition coordinates may relax: `skills/intake_pipeline/1_correction/A0_contract.md:216-223`. A3 repeats "envelope / facade / window" first for `perimeter_core`: `skills/intake_pipeline/1_correction/A3_arbitration.md:55-61`.

Evidence against this being the direct cause of Sonnet's plan decline:

- The 0_reading recognition guide and pen library did not recently change their wall/window/door/dimension content; the key lines blame to 2026-05-26 (`127ba06c`), before this round: `skills/intake_pipeline/0_reading/reading_guide.md:143-184`, `:255-265`; `skills/intake_pipeline/0_reading/pen_library.md:17-23`.
- The 2026-06-21 reading-path schema change only adds optional `RoomRoleObservation` and `ReadingView.room_labels`: `src/agent/reading/schema.py:94-116`. No inspected sm21/sm20 reading artifact contains `room_labels`.
- The Sonnet plan defects are in raw 0_reading JSON before correction. A correction-profile rule about `perimeter_core` cannot make Sonnet draw F1 x=3.44 or F2 x=5.51 walls in the source reading.
- sm21 itself is not a perimeter-core-only case in the evidence. The metadata carries `thermal_zones` 7+7, and J1 blocks 16 vs expected 14: `case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json:7-10`; `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/1_correction/attempts/001/judge.json:21-28`.

### B. Most Likely Root Causes, Ranked

1. High confidence: the apparent reversal is primarily model/case/gate behavior, not a recent 0_reading skill shift.

sm21 plans have dense dimension/window/furniture/door cues that Sonnet over-traced; sm21 elevations have explicit rectangular windows, height chains, and facade counts that the current judges and gpt54 artifacts handle well. The local diffs do not show a recent plan-reading instruction being removed.

2. Medium confidence: stronger elevation/facade validation improved downstream elevation outcomes, but it did not directly de-prioritize plan interior reading.

The schema/validator/correction architecture has stronger facade machinery than the old prose-only flow. That plausibly improves accepted elevation outcomes and makes elevation defects more visible. But the same artifacts show plan-interior correctness remains required and is judged. The first Sonnet run was blocked specifically because plan over-segmentation produced 16 zones instead of 14.

3. Medium confidence: plan interior detail still lacks the same structured provenance/gate sharpness as facade windows.

Facade windows now have strong count/z/span artifacts and judges. Interior plan walls still rely on raw wall strokes whose coordinates may be visually estimated or dimension-derived without structured provenance. The A0 contract asks for provenance, but `Stroke` currently has only `id`, `pen`, `geometry`, and `note`: `src/agent/reading/schema.py:35-43`. This makes plan errors harder to distinguish from faithful but low-confidence tracing.

4. Low confidence: `room_labels` / role-to-reading work shifted attention from plan geometry.

The new schema field is optional, no inspected artifact uses it, and it records topology-light roles rather than partitions. I do not see a causal path from `room_labels` to door/window confusion or dimension ticks as walls in these outputs.

### C. What I Cannot Determine Without Seeing Images

- Whether the plan cue ambiguity is objectively hard or just a Sonnet miss on clear drawings.
- Whether the elevation windows are truly more visually faithful than before, or only more consistent with GT/counts after correction.
- Whether the actual manual 0_reading session prompt contained extra recent instructions emphasizing facade/elevation beyond committed docs.
- Whether a human image-grounded reviewer would agree that F1/F2 south bands have exactly the divider counts asserted by the judges.
- Whether the "reversal from before" refers to raw 0_reading recognition, 1_correction geometry, final IDF geometry, or human visual overlay review. The local evidence separates these stages, and some prior elevation bugs were correction-stage, not reading-stage.

### D. Candidate Fix Directions

Do not implement in this diagnosis pass.

- Preserve the facade/elevation machinery, but add symmetric plan-interior machinery: plan-wall provenance/confidence, candidate-wall audit, and a band/cell-count judge checklist.
- Make J0 stricter for plan over-segmentation, so a bad reading does not need to wait for J1 correction/redraw to be rooted back to 0_reading.
- Add an explicit "dimension tick / window edge / door edge is not an interior partition" section with sm21-style examples in the recognition guide or a case-specific judge prompt supplement.
- In correction profiles, ensure room-identity or thermal-zone-count cases cannot inherit `perimeter_core` relaxations for internal walls.
- Add a report artifact that records the exact model and prompt used for manual 0_reading, including any extra session text, so future regressions can separate prompt drift from model variance.

## Review Ask for Image-Grounded Follow-Up

The image-grounded reviewer should verify exactly these items:

1. On `1f_view.png`, confirm whether the south band has only two true interior vertical dividers around x=5 and x=10, and whether Sonnet's x=3.44, x=6.30/7.56, and x=11.56 marks are dimension ticks, window/door sub-dimensions, furniture, or real walls.
2. On `2f_view.png`, confirm whether the south band has exactly three true dividers at x=3.75, x=7.5, x=11.25, and whether x=5.51 is a furniture/window sub-dimension rather than a wall.
3. On `South_view.png` and `West_view.png`, confirm the F1 elements judged as doors are visually doors and should not be counted as windows.
4. Compare Sonnet render overlays against source plans to verify whether J0 should have failed the first Sonnet run before J1.
5. Compare gpt54 overlays against source images to verify that the "good" contrast is visually faithful, not just count/GT-aligned.
6. Check whether any image evidence supports a real plan/elevation conflict rather than a model recognition error.

Assumptions I made:

- Judge verdicts are accepted as image-grounded evidence, but not infallible.
- `testdata_prompt.json` thermal zone counts are a valid coarse tripwire for sm21 plan cell count, not a prompt source for drawing geometry.
- The current local git history is representative of the prompts/skills used for these runs, except that manual Claude session text may not have been fully persisted.

---

## Claude 独立看图核实 + 历史追溯（2026-06-21，本人 image-grounded pass）

### A. 图像层面核实 Codex 的 review-ask —— 三点全部坐实
看了 sm21 源图 `case_data/{1f_view,South_view,West_view}.png`：
1. **平面过切 = 把绿色尺寸链刻度当灰色内墙**：F1 真·内隔墙只 2 道（≈x=5.0/10.0，南北各 3 间房）。Sonnet 读出的 x=3.44/6.30 = 南立面**尺寸链累计位**（底部 dim 链 540+900+2000=3440、+1200+360+1300=6300），这些是**画在建筑轮廓外的绿色标注**，非墙。
2. **门当窗**：South-F1 最左 = 落地单门（带门扇把手，约 2100 高）；West-F1 居中 = 落地**双开门**（两扇+中梃把手）。都被 retry 标成 window → 南窗虚增 8(真7)、西窗 2(真1)。
3. 两类错都发生在**清晰图**上（人一眼能分 绿标注 vs 灰墙、落地门 vs 抬高窗）= **模型视觉判别错**，非图歧义。Codex 结论方向正确。

### B. 历史追溯 —— 部分挑战 Codex「无回归」结论
**关键**：此类错 2026-06-07 三模型实验（[capability/recognition_modeling_capability.md](../../../capability/recognition_modeling_capability.md) §2）已诊断，且**当时同一栋 sm21**：
- phase1 **「把估算的笔画坐标当测量值吐出，与自己抄对的尺寸链打架」**（§2.1 行41–45）——与现在 Sonnet 尺寸刻度当墙**同源**。
- 当时定的解法（§3/§4/§5，2026-06-07 审定）= 正是要补的护栏，且比 Codex 今天提的更完整：
  1. **0_reading 配套小改**：「别再吐估算的隔墙坐标冒充测量值；把**笔画 / 尺寸链作为两个独立通道 + 置信度**交出，不预先替 correction 仲裁」（§4 行83）。← 即 Codex 的「Stroke provenance/confidence」，但这是 **2026-06-07 已设计、未完全落进 0-5 Stroke schema**（现 Stroke 仅 id/pen/geometry/note）。
  2. **correction 升格约束求解器，「trust the dim」**：笔画与尺寸链冲突时**用尺寸链重新推导**内墙，而非逐字照搬笔画（§2.2 Opus 行为=「读尺寸链重新理解一次」，§2.4 教训3「正是要让所有模型强制做的事」）。
- **故对 Codex Q1 低置信「无回归」的修正**：确无近期 skill-**文本**回归（识别规则停 2026-05-26），但 **2026-06-07 设计的「双通道+置信度」护栏没完全在 0-5 schema 落地** → 任何模型（Sonnet 尤甚，因其本性=忠实转写）的笔画估算错都没被拦，correction 也没可靠地「trust the dim」回收（Sonnet run 过切一路到 J1 才被挡）。这不是「Sonnet 变差」，是「已设计的护栏缺位」。

### C. 用户「Sonnet 最忠实」记忆的澄清
- Sonnet 的**性格 = 忠实转写**（图/phase1 上有什么照画，§2.2「忠实复原 phase1 即 phase1 的错」）。**clean 图（sm20，无家具/尺寸链噪声）上=最忠实最好**；**杂图（sm21 带尺寸链+家具+门弧）上=忠实地把"误判"也照画**（尺寸刻度当墙）。
- 2026-05-28 那次 sm21 两步法 phase1 是 **Opus 4.7**（meta.json），Sonnet 是 phase2 的忠实转写者；用户记的"Sonnet 最忠实"是其转写性格 + clean 图表现，非 sm21 杂图识图。

### D. 明天修复方向（综合 Codex + 历史，未实施）
1. **0_reading**：落地 2026-06-07 设计——笔画/尺寸链双通道 + 每 stroke `provenance`(measured vs estimated_from_dimchain) + `confidence`；禁止把尺寸链估算位当 wall stroke 吐出。
2. **correction**：强制「trust the dim」——内墙笔画与尺寸链冲突时按尺寸链重导 + `corrections[]` 记审计（把 Opus 偶然做对升格为范式）。
3. **门确定性**：立面门≠窗显式反例（门只 log）；J0 平面带/区计数 checklist（sm21 F1=3N+走廊+3S、F2=2N+走廊+4S）；可加 stroke↔dimchain 一致性确定性 check。
4. **持久化手动 0_reading prompt/模型**到 run artifacts（现 llm.yaml 标 manual、未存 → 分不清 prompt 漂移 vs 模型波动）。

### E. Framing（用户 2026-06-21 确认）：本质 = 对 founding 框架的回归
[capability/recognition_modeling_capability.md](../../../capability/recognition_modeling_capability.md) §2.2 三模型 phase2 对比表 = **correction 环节 + 「定性＞定量」框架的起点**：Opus 的 "trust the dim"（冲突时选尺寸链这个更权威通道、重导 + 写仲裁理由）被升格为「所有模型强制做」→ correction = 约束求解/重生成器，**定性(布局/尺寸链/计数) > 定量(逐字笔画坐标)**。
- 今天 Sonnet 失败 **不是新问题，是对这套 founding 框架的回归**：① correction 对**内墙**的 trust-the-dim 执行没补齐（16 区一路到 J1 才挡，没在 correction 用尺寸链推翻笔画）；② reading 侧「别吐估算坐标冒充测量 + provenance/confidence」半截没落进 0-5 schema。
- **明日修 = 把这张表确立的框架对『内墙』执行到位，而非发明新机制**。§D 各条都应挂在这个 framing 下。
