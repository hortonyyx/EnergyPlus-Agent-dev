# Per-run directive (session 2 of 2 — post-pilot)

## 1. Measurement (unchanged from the 2026-07-07 run this directive is restored from)

cv_toolbox.md is REQUIRED reading for this run, and wall-line / window-box /
storey-line positions must be measured with `python tools/run_cv_probe.py`
before drawing (measure-before-draw).

## 2. Where this session starts

A pilot pass over the first plan image already exists in `out/`, and a review of
that pilot is in `feedback.md`. **Read `feedback.md` first.** Redo the pilot
image against it, then do every remaining image in `input_inventory.json`.

## 3. This is the last session — no further review

Unlike the pilot session, do **not** stop partway. Work through to the end:
every row of `input_inventory.json` gets its output file, then rewrite
`reading_summary.md` to cover all of them (the file currently in `out/` is the
pilot-only summary and must be replaced).

Apply the review's method to **every** image, not only the one it was written
about. Each image gets its own calibration and its own candidate sweep; do not
carry a layout over from another image.
