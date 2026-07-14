# B4a Phase A construction brief — 2026-07-14

## Scope and change map

| Contract section | Delivered Phase-A change |
|---|---|
| §5, §5.4–5.5, §7 | `src/agent/judge/gt_schema.py`: strict v2/v3 Pydantic wire models, intrinsic semantic validation, canonical bytes/content hash, stable segment IDs, candidate-only atomic writer, implementation hashes. |
| §6 | `src/agent/judge/gt.py`: safe case/path derivation; `load_gt_document`/`load_gt_file`; v2/v3 dual-read; legacy raw-mapping compatibility; v3 typed-consumer gate.  Loader L2 uses only archived `doc.generator.tolerances`; it imports neither tooling config nor current profile. |
| §8.2–8.3 | `src/agent/judge/gt_manifest.py` and `src/configs/judge_gt.yaml`: strict manifest wire and frozen seven-value judge profile; resolver reads the two Vg values and raw-byte provenance from the existing correction config. |
| §8.4 | `skills/intake_pipeline/1_correction/A0_contract.md`: seven judge②-only registry entries; Vg values are cross-referenced through the pre-existing registry rows, not duplicated. |
| §14.1, §6.3 | `tests/test_gt_schema.py`: v3 strict/semantic/hash/candidate-writer coverage, v2 raw-equality dual-read, unknown-version/path failure, archived-profile loader regression, and config provenance coverage. |

No extractor, renderer, scorer, `run_stage.py`, correction/Vg/Va code, or assets were changed.  No commit was created.

## Preflight and acceptance

§14.5 preflight passed: Pydantic, Shapely, ezdxf, Pillow, OmegaConf, public Vg/fingerprint imports, correction tolerance loader, and `correction.yaml` all resolved without installation or network access.

| Test group | Result |
|---|---:|
| `tests/test_gt_schema.py` | 12 passed |
| `tests/test_gt_discipline.py` | 6 passed |
| `tests/test_gt_render.py` | 5 passed |
| `tests/test_reading_score.py` | 17 passed |
| `tests/test_elevation_score.py` | 16 passed |
| `tests/test_judge_harness.py` | 18 passed |

`git diff --check` passed.  No tracked GT/DXF/PNG/golden path is in the diff. `sm21_anchor/gt.json` remains SHA-256 `a9be379b1735163528396c36d96653cdf71a67ffe54dde6f942c7c86f53f3f8a`; `load_gt("sm21_anchor")` remains raw-JSON deep-equal.

## Expected behavior

Legacy scorer callers continue to receive the original v2 decoded mapping. A v3 file through `load_gt()` fails closed with `gt_v3_requires_typed_consumer`; any case-based typed loader requires `human_verified`, while only explicit `load_gt_file()` may read a candidate. Candidate output cannot overwrite or target protected GT/source/case-data roots.

## r1 rework (REWORK → construction response)

| r1 item | Rework delivered |
|---|---|
| PA-C1 | Completed opening semantic gate: mandatory plan ref, relevant elevation-view recomputation and exact z/ref consistency, endpoint-width floor, host-zone positive-width boundary recomputation; also added unique projection keys, elevation direction/full-partial coverage checks, and polygon area floor. |
| PA-C2 | Expanded `test_gt_schema.py` from 12 to 36 tests: z-null/z-observed, >4 segments, dynamic surface, complete opening and segment rejection families, zone gap/overlap/hash and verification rejection, canonical-order rejection, default/custom case-loader candidate prohibition, archived-profile mismatch and tampered-hash cases. Phase-B/C extractor/build-only rows remain n/a to this Phase-A dispatch. |
| PA-C3 | Candidate protected roots derive from `gt_schema.py`'s repository location, no longer cwd or existence gated; path membership resolves the nearest existing parent before symlink-aware comparison. Tests cover non-repo cwd, absent `gt_sources`, and symlink escape. `gt.py` default root and manifest correction-config root are likewise repository anchored. |
| PA-C4 | Applied main-control ruling: `load_gt_document()` rejects v3 candidates for every `gt_dir`; candidates are file-API only. |
| PA-C5 | Replaced the inert manifest-symbol patch with a guard on the actual `gt.py` `Path.read_bytes` path for both typed entry points, while using an archived profile different from current config. |
| PA-C6 | Manifest now validates canonical zeroed hash, opening/evidence/projection-key uniqueness, and raster view references; coverage tests added. |

Post-rework directed results: `test_gt_schema.py` 36 passed; `test_gt_discipline.py` 6; `test_gt_render.py` 5; `test_reading_score.py` 17; `test_elevation_score.py` 16; `test_judge_harness.py` 18. `git diff --check` passed. sm21 SHA remains `a9be379b1735163528396c36d96653cdf71a67ffe54dde6f942c7c86f53f3f8a` and asset-path diff is empty.

## r2 micro-patch (PA-R1)

Replaced the existing-case `glob("*/case_data")` protection with a repository-relative path-parts policy: every `case_tests/e2e_tests/<case>/case_data/**` path is protected, even when `<case>` and `case_data` do not yet exist. The candidate-writer attack regression now includes `brand_new_case/case_data/candidate.json` and confirms no directory is created. `pytest -q tests/test_gt_schema.py` → **36 passed**. PA-R2 remains explicitly deferred to Phase B per main-control ruling; no Phase-B code was changed.

## Deviations / unresolved

None within Phase A. Phase B/C/D code and their DXF/renderer round-trip matrices were intentionally not touched.

## Review ask

Please review the strict-loader boundary in `gt.py` and the semantic/canonical validation boundary in `gt_schema.py`, especially the archived-tolerance rule: loader validation deliberately does not compare stored tolerances with the current tooling profile.
