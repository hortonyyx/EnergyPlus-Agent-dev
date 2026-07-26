# sm24 v3 GT review fixtures

Frozen JSON **inputs** that four test modules read by absolute path. They used to
live under the (now deleted) root `logs/experiments/2026-07-2{4,5}_sm24_gt_review/`
packages, which were *not* in version control (`.gitignore` `20*_*/` ignored them),
so on a fresh clone those tests silently depended on files only present on one
machine. Moving them here makes that dependency explicit and tracked.

## Layout

Two sub-directories mirror the two source review packages — they are **not**
interchangeable (each package's `request_v3_calibrated.json` is a different file).

- `bundle_07_24/` — the 2026-07-24 draft package
  - `request_v3.json` — uncalibrated v3 conversion request
  - `request_v3_calibrated.json` — calibrated v3 request (16 KB)
- `bundle_07_25/` — the 2026-07-25 signed/final package
  - `request_v3_calibrated.json` — calibrated v3 request (**different bytes** from the 07-24 one)
  - `review_annotations.json` — human zone-role annotations
  - `manifest.json` — extraction manifest (GtExtractionManifestV1)
  - `gt/gt.json` — candidate GT document (GroundTruthV3)

## Where they are read

| file | consumer module |
|---|---|
| `bundle_07_24/request_v3.json`, `request_v3_calibrated.json` | `tests/test_tarch_elevation_must_red.py` |
| `bundle_07_24/request_v3_calibrated.json` | `tests/test_gt_overlay.py` (y-down rectangle test) |
| `bundle_07_25/{request_v3_calibrated,review_annotations}.json` | `tests/test_gt_promotion_path.py`, `tests/test_tarch_converter_reproducibility.py` |
| `bundle_07_25/{manifest.json, gt/gt.json}` | `tests/test_gt_overlay.py` (`_SM24_REVIEW_BUNDLE`) |

The source DXF these requests were authored against is **not** duplicated here; it
is the already-tracked `case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf`
(md5 `79d19b210c2cd1e75df3721fd44c3fa3`, byte-identical to the DXF that shipped in
the 07-24 package). Tests point at that tracked copy directly.

## Regeneration

These are review-artifact inputs, not outputs the test suite rebuilds. They are
produced by the GT review pipeline:

- `request_v3*.json` — the tarch→GT v3 conversion request (authored/calibrated
  against the source DXF; see `src/agent/judge/tarch_converter_schema.py`).
- `manifest.json` + `gt/gt.json` — emitted by
  `build_review_bundle` in `src/agent/judge/tarch_review_bundle.py`, which runs
  `run_p2_conversion` (`src/agent/judge/tarch_normalize.py`) + `extract_gt_v3`
  (`src/agent/judge/gt_extraction.py`) and writes the candidate GT + manifest.

To rebuild the 07-25 package end-to-end, point `build_review_bundle` at the
tracked source DXF and the calibrated request, then re-sign via
`sign_review_bundle` / `rerun_signed_review_bundle` (see
`tests/test_gt_promotion_path.py` for the exact invocation). Byte-reproducibility
of the augmented DXF / GT / renders is locked by
`tests/test_tarch_converter_reproducibility.py`.

## Fail-closed

Consumers read these with `Path(...).read_text()` / `model_validate_json(...)` — a
missing fixture raises (hard red), it never `skip`s. Removing/renaming this
directory therefore turns the four consumer modules red, which is the intended
signal that the repo is corrupted, not that the environment is "not ready".
