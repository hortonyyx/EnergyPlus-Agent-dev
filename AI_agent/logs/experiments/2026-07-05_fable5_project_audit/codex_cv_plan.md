# Classic-CV Front-End Plan for 0_reading

Design target: upgrade the building-drawing -> EnergyPlus pipeline's `0_reading` stage with a classic-CV toolbox that helps weak or open VLMs measure drawing evidence instead of eyeballing it, while preserving drawing-style generalization as the central constraint.

This is a design plan only. It does not propose running the pipeline, EnergyPlus, or tests as part of this document.

## 1. Problem framing

The current reading contract is intentionally narrow: `0_reading` retraces each source drawing with semantically labeled pens and leaves topology to correction (`skills/intake_pipeline/0_reading/guide.md:24-36`). It must work in each image's local frame, especially for elevations, where facade orientation is explicitly image-local and not world-axis placement (`skills/intake_pipeline/0_reading/guide.md:88-99`). That boundary aligns with the project invariants: LLMs handle perception, correction judgment, and physical semantics, while code owns all geometry, modelling, split/pairing, and assembly (`AI_agent/CLAUDE.md:68-74`).

The immediate motivation is empirical. Under the same restored scaffold and same case, Haiku 4.5 collapsed on sm21 while Sonnet 5 read it near-perfectly: Haiku scored 0/9 plan walls, 0/7 plan windows, +9 extra walls, and 0/15 elevation windows, while the Sonnet 5 baseline scored 9/9 walls, 7/7 plan windows, and 15/15 elevation windows (`AI_agent/logs/experiments/2026-07-05_haiku_downgrade_test/README.md:3-19`). The recorded conclusion is that model capability is the dominant lever and the scaffold cannot raise a weak VLM above its perception floor (`AI_agent/logs/experiments/2026-07-05_haiku_downgrade_test/README.md:25-28`).

The useful part of the Sonnet 5 success is not just "better eyes." Forensics showed the model spontaneously built a classic-CV workflow: crop/zoom, grayscale masking, row/column projection to locate wall lines, pixel-to-meter calibration from dimensions, and connected components to count elevation windows (`AI_agent/capability/reading/improvement_methodology.md:43-50`). The methodology doc's core claim is that precision came from measuring rather than seeing: pixel-level 0.0 m offsets are evidence of measurement, not visual guesswork (`AI_agent/capability/reading/improvement_methodology.md:64-67`). The proposed front-end therefore makes those ad hoc "sight tools" explicit and reusable, avoiding the one-run invention cost while giving weaker models the same measuring crutch (`AI_agent/capability/reading/improvement_methodology.md:73-95`).

The boundary is non-negotiable:

- CV is a perception assist. It produces image-local evidence, candidate primitives, anchors, masks, OCR boxes, and measurement sidecars.
- The VLM still classifies semantic identity against the reading guide and chooses which evidence belongs in the reading schema.
- `0_reading` still emits the reading artifact, not IntakeOutput; downstream correction and deterministic geometry remain responsible for topology and world placement (`skills/intake_pipeline/0_reading/guide.md:389-401`).
- The deterministic kernel downstream remains the only place where building geometry is authored, normalized, split, and assembled, consistent with invariant #1 (`AI_agent/CLAUDE.md:68-74`).

This distinction matters because Phase A already hardened evidence visibility, but it did not fix perception. Phase A made weak reading visible through evidence gates and provenance/debt routing (`AI_agent/capability/reading/improvement_methodology.md:126-149`). Phase B is where arithmetic moves out of the VLM into deterministic code via dual-channel reading, dimension-driven reconstruction, and pixel anchors (`AI_agent/capability/reading/improvement_methodology.md:150-160`). The classic-CV toolbox is best treated as the practical front-end for Phase B's visual anchor channel, not as a replacement for the downstream geometry kernel.

The evaluation target should stay tied to the authoritative reading scorer. Reading quality is judged by coordinate matches against ground truth for walls and windows, with misses, extras, and signed offsets reported; rendered images are auxiliary (`src/agent/judge/reading_score.py:1-20`). The scorer's current wall/window tolerance framework is explicit (`src/agent/judge/reading_score.py:31-38`) and extracts wall/window primitives from the reading JSON (`src/agent/judge/reading_score.py:271-312`). Done signals below should therefore be phrased as scorer-visible improvements, not subjective visual claims.

## 2. The toolbox

The toolbox should be a set of callable, deterministic, image-local tools. Each tool returns structured evidence plus enough diagnostics for a VLM or human reviewer to understand why a candidate was produced. None of these tools should directly write final building geometry. Current schema fields include `Stroke` provenance/confidence/dimension refs (`src/agent/reading/schema.py:35-46`), `Dimension` chain/OCR/value/anchor fields (`src/agent/reading/schema.py:55-71`), image-local facade orientation (`src/agent/reading/schema.py:83-95`), and view-level `uncaptured`/`self_check` carriers (`src/agent/reading/schema.py:109-130`). Phase B can add or formalize `visual.anchor_px` and `metric` subchannels, as already sketched in the methodology doc (`AI_agent/capability/reading/improvement_methodology.md:150-159`).

| Tool | Callable input -> output | Reading-schema field it feeds | Primary failure modes |
|---|---|---|---|
| `sheet_segmenter` | Full sheet image plus optional label hints -> per-view ROIs, title/legend/titleblock masks, pixel transforms back to source. | `image_label`, `image_kind`, `uncaptured`, tool provenance sidecar. | Multi-panel sheets without clear frames; title text confused with room text; crop removes needed dimensions. |
| `roi_crop_zoom` | Image plus bbox or VLM natural-language region hint -> crop, scale factor, inverse transform, preview. | Evidence sidecar for every downstream anchor; supports `dimensions[*].anchor` and future stroke pixel anchors. | Cropping away context needed for semantic classification; over-zoom makes scale text illegible. |
| `declutter_mask` | ROI plus mask recipe -> wall-like, text-like, hatch/fill, furniture/clutter, and low-confidence masks. | Helps VLM decide keep-set vs ignore-set; feeds `uncaptured` when clutter is intentionally excluded. | Hatches or furniture have wall-like weight; legend symbols imitate geometry; scanned noise looks like thin lines. |
| `line_weight_profiler` | ROI -> stroke-width/color/contrast histograms and candidate layer thresholds. | Supports `confidence`, `provenance`, and the wall/window/dimension distinction before pen selection. | Clean color assumptions fail on monochrome scans; line weights are not differentiated; anti-aliasing changes apparent width. |
| `wall_line_profiler` | ROI, orientation prior, mask -> row/column projection peaks, line candidates, spans, thickness estimates, confidence. | Plan `strokes[*]` with `pen="wall"` after VLM acceptance; future `visual.anchor_px`; helps prevent dimension ticks/window jambs becoming walls. | Axis-aligned assumption; hatching creates repeated peaks; short real partitions may be suppressed; window jambs still look like vertical peaks. |
| `hough_lsd_line_detector` | ROI and optional angle bins -> arbitrary-angle line segments, colinear clusters, endpoint evidence. | Wall, outline, storey/floor-line, and dimension-extension candidates; C4 extension path for oblique walls. | Broken scans fragment lines; dense hatching dominates; endpoint snapping is ambiguous around corners. |
| `dimension_text_ocr` | ROI or text mask -> text boxes, verbatim strings, parsed value candidates, unit guesses, confidence. | `dimensions[*].text_verbatim`, `value_m`, `anchor`, `ocr_texts`. | Rotated/handwritten text; comma/mm/m ambiguity; superscripts; OCR can produce self-consistent but wrong numbers. |
| `dimension_chain_grouper` | OCR boxes plus line/tick/arrow candidates -> chain groups, `axis`, `chain_id`, `role`, `order`, from/to pixel anchors. | `dimensions[]` P1a fields needed for closure checks and redundant metric evidence. | Baseline dimensions with shared datum; missing overall; wall-thickness residuals that are honest but non-closing; dimension styles not covered. |
| `px_m_calibrator` | Dimension spans in pixels plus parsed dimension values, or graphic scale -> local affine scale, px/m, uncertainty, calibration residuals. | Converts accepted visual anchors to image-local meter coordinates; fills dimension `from`/`to` after VLM review; future `metric` channel. | Perspective photos, non-uniform scan scaling, wrong OCR, mixed scales on the same sheet, cropped dimensions not matching the measured line. |
| `window_cc_detector` | Elevation ROI, facade/wall-fill mask, floor bands -> connected-component boxes, merged window rects, per-floor counts. | Elevation `strokes[*]` with `pen="window"` and `geometry.kind="rect"` after VLM acceptance. | Balconies, louvers, sun-shades, shadows, mullions, and curtain walls can split or merge components. |
| `storey_floorline_profiler` | Elevation ROI -> horizontal floor/level candidates, y/z pixel anchors, floor-band proposals. | Elevation `wall_fill` y ranges, `dimensions[]` level markers, and `window_cc_detector` floor bands. | Decorative bands look like storey lines; sloped/stepped roofs; inconsistent floor heights; missing level markers. |
| `quality_overlay_logger` | Tool outputs plus accepted/rejected candidates -> debug overlay, rejected-candidate reasons, evidence ids. | `self_check`, `uncaptured`, provenance notes, evidence debt sidecar. | If overlays are treated as truth instead of diagnostics; too much evidence can overwhelm the VLM loop. |

The pen mapping remains unchanged at first. Plans legally keep only `wall` and `window` strokes; elevations keep `wall_fill`, `window`, and `outline`; everything else must be recognized and logged rather than traced as geometry (`skills/intake_pipeline/0_reading/pen_library.md:60-70`). Dimension chains go to `dimensions[]`, text to `ocr_texts[]`, and clutter/doors/stairs/grid axes/etc. go to the ignore-and-log path or healing path (`skills/intake_pipeline/0_reading/pen_library.md:17-52`).

The toolbox must expose uncertainty, not hide it. The reading guide already says that a wrong category contaminates downstream behavior and that uncertain marks should be low-confidence or logged as unknown rather than forced into a category (`skills/intake_pipeline/0_reading/reading_guide.md:34-42`). Tool outputs should preserve the same stance.

## 3. Integration into 0_reading

Use a hybrid integration rather than a pure deterministic pre-pass or pure VLM tool loop.

1. Deterministic pre-pass produces a conservative evidence packet.
   It segments sheets, proposes ROIs, runs OCR/text masks, detects candidate lines/components, and records masks/overlays. It does not emit final strokes. Its job is to reduce "I eyeballed it" to "here are measured anchors and candidates."

2. VLM tool-use loop classifies and requests refinement.
   The VLM applies the recognition guide's invariant-cue discipline, not a fixed visual template. The guide explicitly says drawings vary across hand-drawn/CAD/scanned/photo media, fill conventions, detail levels, and standards, and that recognition should lead with invariant cues rather than one rendering style (`skills/intake_pipeline/0_reading/reading_guide.md:20-33`, `skills/intake_pipeline/0_reading/reading_guide.md:125-141`). The VLM decides wall vs dimension tick vs furniture vs window using those cues and can ask tools for narrower crops, alternate thresholds, or Hough/CC variants.

3. Phase B arithmetic descent converts accepted evidence into metric reading output.
   Reading should stop doing cumulative arithmetic in the VLM. The methodology doc states the Phase B target: dual-channel schema with visual and metric evidence, a deterministic dimension constraint solver, and pixel anchors supplied by the wall-line profiler rather than empty anchors that force the VLM to accumulate dimension chains itself (`AI_agent/capability/reading/improvement_methodology.md:150-159`). The solver can reconcile dimension anchors, OCR values, and pixel positions, then populate current meter-valued fields while preserving evidence provenance.

4. Phase A gates remain the first safety net.
   Existing evidence gates require dimensions to be present for dimensioned views, chain fields to be populated, provenance to be meaningful, and dimension-derived strokes to carry refs (`AI_agent/capability/reading/improvement_methodology.md:128-145`). The CV integration should add better evidence to satisfy these gates, not bypass them. A high-confidence dimensioned wall without either a dimension ref or visual pixel anchor should remain suspect.

5. All evidence remains image-local.
   Elevation `facade` fields are image-local and intentionally exclude world-axis/sign/base (`src/agent/reading/schema.py:13-18`). CV tools should therefore output local pixel coordinates, local meter coordinates, and inverse crop transforms. World placement remains a correction/downstream responsibility.

A weak/open VLM loop should look like this:

1. Identify drawing kind and split the sheet into plan/elevation ROIs.
2. Ask `dimension_text_ocr`, `dimension_chain_grouper`, and `px_m_calibrator` to establish scale and dimension evidence.
3. For plans, ask `wall_line_profiler` and `hough_lsd_line_detector` for wall candidates; use the reading guide to reject furniture, dimension ticks, grid axes, window jambs, and hatches.
4. If dimensions do not close or calibration residuals are high, request targeted re-crops and OCR rechecks before emitting a confident coordinate.
5. For elevations, detect outline/floor lines first, then run `window_cc_detector` per facade/floor band; reject decoration and attachments per the recognition guide.
6. Emit the reading JSON with `provenance`, `confidence`, `dimension_refs`, `dimensions[]`, `uncaptured`, and `self_check` populated. Null is preferred over guessing, consistent with the current error budget (`skills/intake_pipeline/0_reading/guide.md:47-69`).

The artifact should include a tool evidence sidecar, even before a schema change. The JSON remains the contract, but the sidecar gives Fable5/human auditability: accepted/rejected candidates, thresholds used, crop transforms, calibration residuals, OCR alternatives, and candidate ids referenced in stroke notes or provenance.

## 4. Style generalization (core)

The goal is not "make sm21 easy." The recognition guide already frames style variation as first-class: architectural drawings vary by medium, fill convention, detail level, and national/office standard (`skills/intake_pipeline/0_reading/reading_guide.md:125-141`). The methodology doc also warns that the clean sm21 gray-threshold recipe is strongest on clean CAD PNGs and needs separate robustness tiers for scans/noisy drawings (`AI_agent/capability/reading/improvement_methodology.md:89-92`). Classic CV avoids self-trained model overfitting, but it has its own brittle points. The toolbox must therefore be recipe-driven and style-tested, not hardcoded to sm21.

Style variation taxonomy and mitigations:

| Variation axis | How classic CV breaks | Mitigation | Fallback |
|---|---|---|---|
| Clean vector CAD vs scanned/photo drawings | Fixed grayscale thresholds fail; scans have skew, broken lines, blur, speckle, and perspective distortion. | Tier tools by medium: clean-vector recipe, scanned recipe with deskew/adaptive threshold/morphological repair, photo recipe with perspective correction and lower confidence. | VLM-visible warning: "measurement unreliable"; require manual reread or stronger model for golden cases. |
| Wall fill: solid black, hollow double-line, hatched, poche, single-line schematic | Wall masks may either miss hollow walls or treat hatch strokes as many walls. | Use multiple wall recipes: stroke-width layer, double-line pairing, filled-region morphology, hatch suppression by periodicity/orientation, contour enclosure. | Emit wall candidates as low confidence and require VLM semantic acceptance against room-boundary cues. |
| Line weights and colors | Some drawings lack reliable weight hierarchy; color can be absent or misleading. | Profile line weights locally rather than assuming global thresholds; color only as weak evidence, matching the guide's warning that color is not reliable by itself (`skills/intake_pipeline/0_reading/reading_guide.md:108-121`). | Revert to geometry/context cues: room enclosure, joins, dimension references. |
| Dense furniture, sanitary symbols, stairs, legends, titleblocks | Clutter creates wall-like rectangles and repeated lines; legends/titleblocks can look like rooms. | `sheet_segmenter` masks titleblocks/legends; `declutter_mask` suppresses small repeated furniture-like components; VLM must log ignore-set items rather than silently drop them. | Keep uncertain marks in `uncaptured` or low-confidence notes, never as confident walls. |
| Dimension-line styles | Ticks, arrows, dots, baseline chains, stacked chains, and units vary; OCR may read numbers but group them wrong. | Separate OCR from chain geometry; detect extension lines/terminators; support chained, baseline, and overall roles; run closure checks with residual classification. | If a chain cannot be grouped, emit visible OCR text and low-confidence dimension evidence rather than inventing coordinates. |
| Hatching/floor paving/material patterns | Repeating strokes create projection peaks and Hough lines. | Detect periodic fine-line textures; treat hatches as fill context unless they bound rooms; use legend when available. The recognition guide says material hatch is interpreted by location and legend, not pattern alone (`skills/intake_pipeline/0_reading/reading_guide.md:329-339`). | Ask VLM to classify area context; low confidence if hatch and wall cues conflict. |
| Facade decoration, balconies, louvers, shadows, sun-shades | Connected components split/merge windows or count attachments as windows. | Combine rectangle score, floor-band alignment, glazing/mullion cues, and VLM rejection of decorations. The guide explicitly warns to keep attachments out of window/wall_fill (`skills/intake_pipeline/0_reading/reading_guide.md:219-235`, `skills/intake_pipeline/0_reading/reading_guide.md:379-394`). | Count windows with low confidence and emit rejected decoration candidates in the sidecar. |
| Non-orthogonal or curved geometry | Row/column projection misses oblique walls; axis-only calibration breaks. | Treat row/column projection as a C1/C2 orthogonal plugin only; keep Hough/LSD angle clustering and rotated local frames as the C4 path. | For oblique walls before C4 support, mark candidates and avoid pretending the orthogonal solver can place them exactly. |
| Multi-scale or partial drawings | One px/m value may not apply across details; detail callouts may be at different scales. | Segment by view frame and title; calibrate per ROI; reject mixed-scale reuse unless scale text/graphic scale confirms it. | Emit separate supplementary/other views or ignore detail views if they do not feed plan/elevation geometry. |

Generalization test strategy:

1. Build a style-diverse eval set before claiming success. It should include clean CAD PNGs, scanned drawings, monochrome line drawings, filled/hatched walls, outline-only walls, dense furniture plans, elevation drawings with decoration/shadows, GB tick dimensions, arrowhead dimensions, and at least one oblique or non-rectangular stress case.
2. Partition evaluation by style axis, not just by case. sm21 remains a pilot and regression anchor, not the definition of success.
3. Score with the authoritative reading scorer where GT exists: wall/window hit counts, misses, extras, signed offsets, and boundary completeness (`src/agent/judge/reading_score.py:782-830`). For style-only cases without GT, use evidence completeness and human/Fable5 review but do not call them scorer wins.
4. Track false positives by category. A plan-wall hit rate improvement that adds many extra walls is not acceptable because over-segmentation is already a known failure mode.
5. Require recipe diversity. A "pass" that only works with the sm21 gray threshold is a failed generalization result.

Where classic CV still breaks:

- It cannot reliably decide semantic identity when geometry is ambiguous. The VLM remains necessary for category recognition and for applying invariant cues.
- It cannot recover from absent dimensions if the required metric coordinate is not visually measurable with enough scale evidence.
- It can produce self-consistent but wrong measurements if OCR and chain grouping are both wrong. Phase A/Phase B must make those conflicts visible.
- It is weakest on photos, low-resolution scans, heavy hatching, and highly decorative elevations. Those should be explicit lower-confidence tiers, not hidden under a single "CV enabled" label.

## 5. Phasing

The names below are CV rollout phases, not building-complexity C2/C3/C4 levels.

| Phase | Lands first | Dependencies | Done signal tied to scorer |
|---|---|---|---|
| C0 - evidence sidecar and tool contracts | Define callable tool interfaces, sidecar schema, crop transform convention, provenance vocabulary, and no-final-geometry rule. Add design fixtures for tool outputs but do not change reading behavior yet. | Phase A evidence vocabulary; current reading schema fields. | No scorer target yet; Fable5/human audit agrees that every proposed tool output maps to image-local evidence and not downstream geometry. |
| C1 - clean CAD plan measurement | `sheet_segmenter`, `roi_crop_zoom`, `line_weight_profiler`, `wall_line_profiler`, `px_m_calibrator`, and `quality_overlay_logger` for clean vector-like plan drawings. | Minimal Phase B bridge: a place to store/point to pixel anchors, even if only sidecar + notes initially. | On sm21-like clean CAD plans with weak/open VLM, plan wall hits improve materially from the Haiku 0/9 baseline, with extras reduced below the +9 failure mode. A stricter acceptance target for promotion: >=8/9 plan walls within scorer tolerance and <=1 extra interior wall. |
| C2 - elevation floor/window measurement | `storey_floorline_profiler` and `window_cc_detector` for clean elevation views, with per-floor window counts and rect proposals. | C1 crop/calibration; elevation image-local facade discipline; current elevation `window` rect schema. | On sm21 elevations with weak/open VLM, elevation windows improve from 0/15 placed to >=12/15 within scorer tolerance and <=3 extras. Promotion target: 15/15 complete or within tolerance on clean CAD style before calling it Sonnet-5-equivalent. |
| C3 - OCR and dimension chains | `dimension_text_ocr`, `dimension_chain_grouper`, calibration residuals, and closure/reread loop. | Phase A chain closure and Phase B dimension-driven reconstruction. | Dimensioned views produce complete `dimensions[]` chains where available; closure failures become loud evidence debt, not silent guesses. Scorer should show reduced coordinate drift on wall/window placements that depend on dimensions. |
| C4 - Phase B arithmetic descent integration | Formal dual-channel reading: visual anchors + metric dimension evidence, deterministic solver writes metric coordinates or a reconstructed reading artifact. | Phase B schema/solver decision; correction contract update; evidence gate update. | Coordinate offsets move from "within tolerance" toward "complete" on clean CAD anchors, with no increase in missed or extra walls/windows. The scorer's signed offsets should expose the improvement. |
| C5 - style-generalization hardening | Multiple recipes per medium/style; style-diverse eval set; fallback tiers; human-readable failure classification. | C1-C4 tools; Fable5-approved eval taxonomy. | Performance is reported by style bucket. A phase cannot be accepted based only on sm21. Minimum bar: no major regression on clean CAD, clear improvement for weak VLMs on at least two non-sm21 style buckets, and explicit known-fail labels for unsupported buckets. |
| C6 - optional learned-CV comparison | Only after classic-CV limits are measured: compare off-the-shelf or trained detectors against classic tools on the style-diverse set. | Style eval set and classic baseline. | Learned CV must beat classic CV across style buckets without sacrificing out-of-domain generalization. Otherwise it remains research, not the default path. |

Cheapest/highest-leverage first:

- C1 and C2 should precede full OCR because the Sonnet 5 forensics did not need OCR for dimensions; it used VLM-read numbers plus pixel measurement (`AI_agent/capability/reading/improvement_methodology.md:50`). The Haiku collapse was mostly perception/measurement of walls and windows, not only dimension transcription (`AI_agent/logs/experiments/2026-07-05_haiku_downgrade_test/README.md:21-24`).
- C3 is still important because dimensions are the only reading error class that downstream cannot recover when the number is wrong and self-consistent (`AI_agent/capability/reading/improvement_methodology.md:116-122`).
- C4 should be designed with Phase B, not bolted on later, because the methodology explicitly ties `anchor_px` and arithmetic descent to the wall-line profiler (`AI_agent/capability/reading/improvement_methodology.md:156-159`).

Deferred:

- Full learned detection/segmentation is deferred until classic-CV limits are measured. The methodology records the project concern that self-trained CV generalizes poorly across drawing styles, while classic CV is a lighter front-end that keeps the VLM in the semantic loop (`AI_agent/capability/reading/improvement_methodology.md:162-169`, `AI_agent/capability/reading/improvement_methodology.md:186-192`).
- Photos and heavily degraded scans should be a named robustness tier, not a blocker for C1/C2 clean CAD delivery.
- C4 oblique walls are not a reason to delay C1/C2, but every C1/C2 tool must declare whether it assumes orthogonal geometry and how that assumption is relaxed later.

## 6. Risks + invariant #6

Invariant #6 requires every current decision to leave a path toward future building complexity: no baked-in shared footprint, fully tiled floor, or fixed floor-height assumptions (`AI_agent/CLAUDE.md:68-74`). The complexity roadmap names C2 as orthogonal polygon footprints and multi-plane facades, C3 as vertical complexity such as setbacks, atria, voids, and cross-floor zones, and C4 as oblique walls (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:60-65`).

Tool assumptions and how to keep them loosenable:

| Tool/assumption | Risk | Loosening path |
|---|---|---|
| `wall_line_profiler` assumes row/column orthogonality. | Works well for C1 and parts of C2 but fails on C4 oblique walls. | Treat it as an orthogonal recipe. Add `hough_lsd_line_detector` with angle clustering and rotated local coordinates as the C4 path. The roadmap already calls for direction clustering and rotated-system snapping in C4 (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:89-95`). |
| Rectangular ROI/envelope assumptions. | Overfits to shared rectangular footprint and misses L/U/concave buildings. | Use polygon masks and per-wing/per-floor ROIs. C2 explicitly needs orthogonal polygon footprints and multi-plane facades (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:68-76`). |
| Single global px/m per sheet. | Detail drawings, scans, and perspective photos can have local scale distortion. | Calibrate per ROI/view frame and store uncertainty. Reject cross-view reuse unless scale evidence supports it. |
| Floor-band elevation windows assume horizontal storeys and fully tiled floors. | C3 setbacks/voids/atria break "one floor band fills the whole facade." | Make floor bands candidates, not truth. Future C3 must support sections and per-cell z spans; the roadmap notes section inputs and z-span schema are needed for void/atrium evidence (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:78-87`). |
| Window detection assumes facade enum and axis-aligned spans. | C4 oblique walls weaken N/S/E/W facade semantics and require wall-local spans. | Keep current image-local facade fields for C1-C3, but design sidecar candidates with wall/segment references and along-segment coordinate fields so a later `wall_ref` schema can consume them. The C4 roadmap flags window wall projection and `wall_ref`/direction-angle evolution (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:91-94`). |
| Dimension-chain grouping assumes visible conventional ticks/arrows and one style per view. | Mixed standards or missing dimensions make chain closure ambiguous. | Store raw OCR boxes and grouping alternatives. Let Phase A/Phase B mark residuals and reread requests instead of forcing a chain. |
| Declutter recipes assume furniture/hatch are separable by size/frequency. | Real drawings can draw built-ins, cabinets, and hatches with structural line weights. | VLM semantic review remains mandatory. The reading guide's stable-cue approach is the defense against style overfitting (`skills/intake_pipeline/0_reading/reading_guide.md:20-33`). |

Complexity-specific outlook:

- C2 orthogonal polygon / multi-plane facade: the toolbox helps if it returns line segments, polygon contours, wing breakpoints, and facade segment evidence instead of only one bounding rectangle. This aligns with the roadmap's need for outer contour polylines, per-floor footprint, and window-to-wing arbitration (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:63-76`).
- C3 setback/atrium/void: CV can detect floor lines, section outlines, open-to-below text, and void hatches, but it must not infer z topology. It should feed section/plan evidence to the VLM and Phase B/C3 schema, where deterministic z-span and wall z-cut logic can own geometry (`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md:78-87`).
- C4 oblique-wall: row/column projection becomes a convenience tool only. The long-term interface must support arbitrary-angle line segments and along-wall window spans. Do not hardcode N/S/E/W facade-only assumptions into tool evidence even if the current JSON schema still uses facade labels.

Main risks:

- False confidence: deterministic-looking CV output can be wrong. Every tool needs confidence, residuals, and rejected alternatives.
- Gate mismatch: Phase A gates may flag honest no-overall or wall-thickness residual cases; the methodology already notes such false-positive debt on perfect readings (`AI_agent/capability/reading/improvement_methodology.md:146-149`). Phase B residual channels should distinguish honest drawing limitations from reading failure.
- Evaluation overfit: sm21 can become the hidden target. The style-diverse eval set and per-style reporting are required before calling the toolbox general.
- Schema churn: Phase B dual-channel schema is likely needed, but C1/C2 can start with sidecars to avoid blocking early measurement experiments.
- VLM overload: too many candidates can degrade weak models. Tool outputs should be ranked, grouped, and queryable rather than dumped wholesale.

## 7. Open questions / decisions for the humans

1. Phase B sequencing: should the toolbox land first as sidecar-only evidence, or wait for a formal dual-channel schema with `visual.anchor_px` and `metric` fields?
2. Tool placement: should these be stage-local scripts under the reading subsystem, reusable judge-side utilities, or a separate callable service? The placement affects gt isolation and audit boundaries.
3. Gate policy: when should missing CV anchors be a golden/regression block versus an exploratory warning?
4. Weak/open VLM target: which model is the first acceptance target after Haiku 4.5, and what scorer thresholds count as a meaningful win?
5. Style eval corpus: which drawings are in the first style-diverse set, and which style buckets are must-pass before "generalized" can be claimed?
6. OCR engine decision: PaddleOCR, Tesseract, EasyOCR, a managed OCR API, or a pluggable abstraction? The choice should consider Chinese/GB drawings, rotated text, local/offline constraints, and auditability.
7. Conflict policy: when pixel anchors and dimension chains disagree, should Phase B prefer dimensions, prefer calibrated pixels, solve with residuals, or force reread?
8. Learned-CV threshold: what evidence would justify adding a trained detector despite the generalization concern?
9. Complexity guardrail: which C2/C3/C4 evidence fields should be included in sidecars now so C1/C2 work does not need to be redesigned later?
10. Fable5 audit ask: should Fable5 review the toolbox as a Phase B component, a Phase C component, or a combined "CV as VLM sight-tools" front-end?
