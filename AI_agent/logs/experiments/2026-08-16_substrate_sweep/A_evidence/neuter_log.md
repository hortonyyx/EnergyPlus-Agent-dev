# Neuter log (Lane A, 摊 A)

Three positive locks neutered, each by a single-line temporary edit to the
production code under `src/agent/reading/cv_toolbox/`, re-running only the
targeted subset of `tests/test_substrate_sweep_tools.py` before and after,
then reverting and confirming `git diff --stat -- src/` is empty. Baseline
before every round: `43 passed, 4 xfailed` (full file, `-n0`).

## Neuter 1 — `px_m_calibrator`'s scale formula

File: `src/agent/reading/cv_toolbox/tools.py`, function `px_m_calibrator`.

```diff
-    px_per_m = float(np.sum(values * spans) / np.sum(values**2))
+    px_per_m = float(np.sum(values * spans) / np.sum(values**2)) + 1.0  # NEUTER-1
```

Command: `pytest tests/test_substrate_sweep_tools.py -n0 -q -k "grid_px_m_calibrator or s2_anchors_json or doc_example_px_m"`

Result: **5 failed** (all `41.0 == 40.0 ± 0.2` mismatches), 0 passed in that
selection:
- `test_grid_px_m_calibrator[B]`
- `test_grid_px_m_calibrator[A]`
- `test_grid_px_m_calibrator[C]`
- `test_doc_example_px_m_calibrator_runs_and_computes_the_documented_scale`
- `test_s2_anchors_json_as_file_path_string_form_a`

Reverted (`px_per_m = float(np.sum(values * spans) / np.sum(values**2))`).
`git diff --stat -- src/agent/reading/cv_toolbox/tools.py` → empty.
Full-file rerun: `43 passed, 4 xfailed` (unchanged from baseline).

## Neuter 2 — `write_sidecar`'s source-size reporting (the F-51 fix)

File: `src/agent/reading/cv_toolbox/sidecar.py`, function `write_sidecar`.

```diff
     with Image.open(source_image) as _source_img:
         source_width_px, source_height_px = _source_img.size
+        source_width_px = source_width_px // 2  # NEUTER-2
```

Command: `pytest tests/test_substrate_sweep_tools.py -n0 -q` (full file)

Result: **10 failed**, 33 passed, 4 xfailed:
- `test_grid_crop_zoom[B]`, `[A]`, `[C]`
- `test_s3_source_size_reported_by_every_tool` — all 6 parametrizations
  (`crop_zoom`, `wall_line_profiler`, `storey_line_profiler`,
  `px_m_calibrator`, `window_cc_detector`, `overlay_logger`)
- `test_s3_crop_scale_roundtrip_within_one_pixel`

All ten failures show `assert 600 == 1200` (the halved width). No test
outside this list turned red — the other 33 passing + 4 xfailed cases are
untouched, i.e. the neuter's blast radius matches exactly what the code
change could plausibly affect.

Reverted. `git diff --stat -- src/agent/reading/cv_toolbox/sidecar.py` → empty.
Full-file rerun: `43 passed, 4 xfailed`.

## Neuter 3 — `window_cc_detector`'s area computation

File: `src/agent/reading/cv_toolbox/tools.py`, function `window_cc_detector`.

```diff
-                "area_px": int(box["area_px"]),
+                "area_px": int(box["area_px"]) + 7,  # NEUTER-3
```

Command: `pytest tests/test_substrate_sweep_tools.py -n0 -q` (full file)

Result: **3 failed**, 40 passed, 4 xfailed:
- `test_grid_window_cc_detector[B]`, `[A]`, `[C]` — all three show
  `assert 307 == 300` for both RECT_A and RECT_B, and `assert 12907 == 12900`
  for the cross-blob, i.e. every reported area is off by the injected +7.

Reverted. `git diff --stat -- src/` → empty (checked against the whole `src/`
tree, not just the one file, as a final sweep).
Full-file rerun: `43 passed, 4 xfailed`.

## Judgement

All three neuters flipped their target lock(s) red with no unrelated
collateral, and the reverts left zero trace (`git status --short -- src/`
clean throughout, verified before Neuter 1 and after Neuter 3). Per the
dispatch's criterion ("变红才算接线，形状匹配/代码审查不算"), these three
locks are confirmed wired to the real implementation, not merely
shape-matched against it.
