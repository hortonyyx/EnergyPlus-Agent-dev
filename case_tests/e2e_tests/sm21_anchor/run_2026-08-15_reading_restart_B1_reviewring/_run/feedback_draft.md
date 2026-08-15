# Pilot review — 1f_view

Your calibration is sound and your candidate sweep was thorough. Five method
issues below, all of them things you already flagged yourself. Fix all five on
`1f_view` first, then apply the same method to the remaining images.

## 1. Your calibration is not on the record

Your summary says "Manual pixel-to-meter conversion". There is no
`px_m_calibrator` sidecar in `out/`. `cv_toolbox.md` §Disciplines: *"Use one
px-to-m formula and leave enough provenance to reproduce it ... Non-reproducible
numbers are invalid data."*

Re-establish the same scale through `python tools/run_cv_probe.py --tool
px_m_calibrator`, with the x and y anchors in **one** call so the tool's
cross-axis check actually runs and its residuals are recorded.

## 2. Interior positions are eyeballed, and you said so

Your summary, "Measurement Uncertainties" #1: the interior partition
coordinates are *"visual estimates from the floor plan grid, not extracted from
explicit dimension annotations"*.

`cv_toolbox.md` §Disciplines: *"Measure before drawing. Wall lines, window
boxes, storey lines, and similar coordinates must come from tool measurement
... Do not write pure eyeballed coordinates when the clean-vector toolbox
applies."*

You already ran the profilers and hold **29 column + 19 row** candidates. Every
interior wall you draw must land on a candidate from those sweeps. Work through
the candidate list one at a time and decide each one — accept it as a wall, or
reject it with a reason — rather than drawing the layout you infer and then
looking for support.

## 3. The dimension transcription is partial, and closure was never checked

Your summary, "Uncertainties" #3: *"Only ~10 representative dimension entries
provided. The floor plan contains many more dimension ticks and segment labels
... A complete audit would require OCR of all dimension text and closure
verification."*

`guide.md` §6 checklist: *"every dimension-chain number is in the dimensions
array"*. This is not optional and it is not a downstream job. Transcribe every
chain completely, then verify per chain that the segments sum to that chain's
overall. A chain that does not close means something was misread — find it
before you draw from it.

## 4. Most strokes carry `provenance: "seen"`

11 of your 15 strokes are `seen`; 4 are `dimension_derived`, and only those 4
cite anything in `dimension_refs`.

`seen` is the correct label for something you genuinely only saw. But once #2
and #3 are done, most of these coordinates should be coming from the chains,
and each such stroke must say so and cite the dimension ids it used. Do not
relabel anything you have not actually re-derived — the label has to match how
you got the number.

## 5. `ocr_texts` is empty

Your summary, "Uncertainties" #4, says text exists in the drawing. `guide.md`
§1 requires text labels transcribed verbatim. Transcribe what is there, with
anchors; write `null` only for what genuinely is not.

---

## What to do next

1. Redo `1f_view` with the five points above.
2. Then do the remaining images — every plan and every elevation — with the
   same method: calibrate through the tool, sweep candidates, decide each
   candidate explicitly, transcribe chains completely, cite what you derived
   from.
3. Applying this to only the first image is the failure mode this review exists
   to prevent. Each image gets its own measurement, not an inherited layout.

There is no further review after this one. Work through to the end.
