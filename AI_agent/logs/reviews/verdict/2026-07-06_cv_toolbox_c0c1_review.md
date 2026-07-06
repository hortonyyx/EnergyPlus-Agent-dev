# CV toolbox C0+C1 review

Verdict: **APPROVE-WITH-CHANGES**.

The batch is feasible as an additive, execution-side toolbox. The dependency and placement claims check out locally, and the proposed file set can avoid existing schema/gate/pipeline behavior. The required changes are contract/spec tightening before implementation, not a redesign.

## Feasibility checks

- Dependencies are already direct project dependencies: `numpy>=2.3.4` at `pyproject.toml:19`, `pillow>=11.0.0` at `pyproject.toml:22`, and `scipy>=1.16.2` at `pyproject.toml:28`. No dependency edit or `uv lock` is needed.
- Local tree check: `find . -type d -name cv_evidence -print` returned no existing `cv_evidence` directories. The requested `0_reading/cv_evidence/{image_stem}/...` path is unoccupied.
- Existing flow does not collide with that path, but also will not collect it. `StageRunner.record` only writes `output.json` and `checks.json` into each attempt (`src/agent/execution/stage_runner.py:113-118`, `src/agent/execution/stage_runner.py:138-153`). `run_stage.py` renders only `0_reading/*_view.json` to `*_render.png` (`scripts/tool_scripts/run_stage.py:343-348`), exposes source images from `case_data/*.png` only (`scripts/tool_scripts/run_stage.py:393-401`), and judge packets list `source_images`, `renders`, `score_vs_gt`, and `grade`, not arbitrary sidecars (`scripts/tool_scripts/run_stage.py:997-1007`).
- Report eyeball collection is explicit, so there is no wildcard conflict: it copies only fixed grade/correction assets (`scripts/tool_scripts/report_assembly.py:100-105`), `0_reading/*_render.png` (`scripts/tool_scripts/report_assembly.py:122-125`), and `case_data/*_view.png` (`scripts/tool_scripts/report_assembly.py:139-144`). The report evidence index currently includes gate, judge, evidence-debt, and correction entries (`scripts/tool_scripts/report_assembly.py:425-428`) plus eyeball assets (`scripts/tool_scripts/report_assembly.py:447-448`), so `cv_evidence` remains future report/attempt integration as the brief says.
- `tests/test_gt_discipline.py` extends cleanly. The forbidden tokens are centralized (`tests/test_gt_discipline.py:35`), `_scan` already skips missing paths and reads text files generically (`tests/test_gt_discipline.py:38-47`), and the current executor set is just a list being extended (`tests/test_gt_discipline.py:57-61`). Exact test edit: add `executors.extend(sorted(Path("src/agent/reading").rglob("*.py")))` and `executors.append(Path("scripts/tool_scripts/cv_probe.py"))`. Local `rg "judge\.gt|judge import gt|load_gt|test_baseline/gt" src/agent/reading` returned no hits.
- Collection-only verification passed: `pytest --collect-only -q -p no:cacheprovider` collected **498 tests**.

## Answers to brief §8

1. Dependency status: present; see `pyproject.toml:19`, `pyproject.toml:22`, `pyproject.toml:28`.
2. Sidecar path conflict: no existing `cv_evidence` path and no current collector conflict. The only caveat is non-collection: attempts/report code will ignore it unless future work wires it in.
3. Phase B fields to reserve now: methodology Phase B sketches `visual{anchor_px|null, relative, confidence}` plus `metric{dimension_refs, raw_segments, confidence}` and provenance (`AI_agent/capability/reading_improvement_methodology.md:150-152`), then states `anchor_px` should be filled by the wall-line profiler (`AI_agent/capability/reading_improvement_methodology.md:156-158`). Sidecar v1 should reserve, per candidate: `candidate_id`, `coord_space`, `anchor_px`, `visual.relative`, `visual.confidence`, `metric.dimension_refs`, `metric.raw_segments`, `metric.scale_px_per_m`, `metric.residuals`, `metric.confidence`, and `provenance`.
4. Synthetic fixture thresholds: `±1 px` is fine for peak position when fixtures draw integer, non-antialiased strokes. Use exact or `1e-9`/`1e-6` numerical tolerances for calibrator scale. Use `±2 px` for estimated line width/FWHM if peak-width math is involved. Keep true-image smoke assertions broad, as the brief proposes.
5. CLI surface: `cv_probe.py <tool> ... --image <png> --out-dir <dir>` is workable for a Bash-only sub-agent if every tool has explicit flags and a `--params-json` escape hatch. Require common flags: `--recipe clean_vector_v1`, `--bbox x0,y0,x1,y1` where relevant, `--axis row|col`, `--scale`, `--min-area`, `--candidates-json`, and `--sidecar-name auto|NNN_tool`.
6. Pollution isolation: no conflict if `cv_probe.py` imports only `src.agent.reading.cv_toolbox` plus PIL/numpy/scipy and never imports execution, pipeline, judge, or gt code. Follow the `run_stage.py` CWD robustness pattern only for locating the repo module (`scripts/tool_scripts/run_stage.py:34-38`), and keep all data paths explicit CLI arguments.

## Required implementation changes

1. **MEDIUM - Tool APIs are underspecified enough to cause executor drift.**

Concrete fix: implement these definitions verbatim.

- Coordinate convention: all pixel coordinates are image-local, origin top-left. Bboxes are half-open `[x0, y0, x1, y1)`. Every result must include `coord_space: "source_px"` and, when cropped, both crop-local and source-mapped coordinates.
- `crop_zoom`: input `bbox_px` half-open and `scale >= 1`. Output crop PNG plus `crop_chain` step `{op:"crop_zoom", bbox_px, scale, source_size_px, crop_size_px, local_to_source, source_to_local}`. For simple scale/crop, `source_x = x0 + local_x / scale` and `source_y = y0 + local_y / scale`.
- `wall_line_profiler`: mask is `gray_lo <= mean(rgb) <= gray_hi` and `max(rgb)-min(rgb) <= rgb_tol`. For `axis="col"`, project with `mask.sum(axis=0)` and report vertical line x positions; for `axis="row"`, project with `mask.sum(axis=1)` and report horizontal line y positions. Normalize projection by the orthogonal image length. Use `scipy.signal.find_peaks` on the normalized projection. Define `strength` as normalized prominence in `[0,1]`; define `width_px` as FWHM from `scipy.signal.peak_widths(rel_height=0.5)`; define `position_px` as the weighted centroid inside the FWHM support, with `peak_index_px` also returned.
- `storey_line_profiler`: exactly the same kernel as `wall_line_profiler` with `axis="row"` and `candidate_kind="storey_line"`.
- `px_m_calibrator`: anchors are spans, not points: `{axis, px_a, px_b, value_m, dimension_ref?}`. Compute `span_px = abs(px_b - px_a)` for axis anchors, or Euclidean distance only if `axis="xy"`. Multi-anchor scale is forced-through-origin least squares: `px_per_m = sum(value_m_i * span_px_i) / sum(value_m_i ** 2)`. Single-anchor residuals are `null`; multi-anchor residuals are per-anchor `{residual_px, residual_m}` where `residual_px = span_px - px_per_m * value_m`. Return `m_per_px`, `rmse_px`, `rmse_m`, and warnings when residuals exceed explicit thresholds.
- `window_cc_detector`: use `scipy.ndimage.label` with 8-connectivity. Filter by `min_area_px` and optional bbox width/height/aspect bounds. Merge boxes by fixed-point iteration in sorted `(y0,x0,y1,x1)` order when gap in one axis is `<= merge_gap_px` and overlap ratio on the other axis is `>= merge_overlap_ratio`, or when IoU is `>= merge_iou`. Return each merged bbox with `source_component_ids`, `area_px`, `centroid_px`, and `merge_reason`.
- `overlay_logger`: input candidates must include `candidate_id`, `geometry`, `status: accepted|rejected|undecided`, and `reason`. Draw accepted green, rejected red, undecided amber. Return overlay PNG path and preserve the decisions in the JSON sidecar.

2. **MEDIUM - Sidecar v1 must reserve Phase B fields now, while still not changing reading schema.**

Concrete fix: each result object should include:

```json
{
  "candidate_id": "1f_view:wall_line_profiler:001:r12",
  "candidate_kind": "wall_line|storey_line|window_rect|calibration|crop",
  "coord_space": "source_px",
  "anchor_px": {"kind": "point|line|bbox|span", "value": {}},
  "visual": {"anchor_px": {}, "relative": {}, "confidence": "high|medium|low"},
  "metric": {
    "dimension_refs": [],
    "raw_segments": [],
    "scale_px_per_m": null,
    "residuals": [],
    "confidence": "high|medium|low"
  },
  "provenance": {"tool": "", "tool_version": "", "recipe_id": "", "source_image_sha256": "", "crop_chain_id": ""}
}
```

Do not write any of this into `*_view.json` in this batch. The current reading schema already treats dimension `anchor` as optional (`src/agent/reading/schema.py:70`) and keeps extra fields loadable (`src/agent/reading/schema.py:20-21`), but the brief is correct to defer schema changes.

3. **LOW - The report/attempt story must be worded as future integration, not current behavior.**

Concrete fix: in the skill doc and implementation notes, say `0_reading/cv_evidence/` is a flat-stage audit sidecar for this batch. Do not claim it is captured in attempts or report evidence yet. The brief already frames future attempts collection as a later seam (`AI_agent/logs/reviews/request/2026-07-06_cv_toolbox_c0c1_proposal.md:55`); keep that exact boundary.

4. **LOW - Scope wording should not overclaim OCR/dimension robustness.**

Concrete fix: keep OCR deferred as the brief states (`AI_agent/logs/reviews/request/2026-07-06_cv_toolbox_c0c1_proposal.md:49`), but document that this batch does not test weak-VLM dimension transcription. FABLE5 explicitly challenged the OCR deferral as an unverified weak-model assumption (`AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md:175`).

## Golden/behavior safety

Approved boundaries: new module under `src/agent/reading/cv_toolbox/`, new `scripts/tool_scripts/cv_probe.py`, new `skills/intake_pipeline/0_reading/cv_toolbox.md`, one pointer line in `session_kickoff.md`, and tests. No reading/correction schema edits, no gate edits, no pipeline/EP/case runs. This matches the brief's explicit non-goals (`AI_agent/logs/reviews/request/2026-07-06_cv_toolbox_c0c1_proposal.md:5`, `AI_agent/logs/reviews/request/2026-07-06_cv_toolbox_c0c1_proposal.md:47-49`).

Place the kickoff pointer alongside the existing three rule-doc pointers (`skills/intake_pipeline/0_reading/session_kickoff.md:17-22`) and keep it as a pointer only, consistent with the anti-drift policy in `skills/intake_pipeline/0_reading/session_kickoff.md:8-9`.
