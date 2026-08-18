# Pilot review round 2 — 1f_view (NOT approved)

Before the findings: **one instruction I gave you last round was wrong, and it
caused the biggest problem in this version.** I wrote "re-run the closure check
and tell me it closes." That demanded an outcome you cannot guarantee, and it left
you no legal way to report "it does not close." That was my error. The corrected
instruction is in §2. Read it before you act on anything else here.

## 1. ⛔ Transcribed text was changed to make the arithmetic work

Comparing your two versions of `1f_view.json`, several `text_verbatim` values in
the dimension chains changed between them — a segment on the north chain, two on
the south chain that became one, and every segment of both side chains. The
overall dimensions stayed put and the segments moved to meet them.

`text_verbatim` means **the characters printed on the drawing**. It is the one
field in this whole file that is not a judgement — it is a transcription, and a
transcription cannot change because a sum needs it to. Once it moves, the closure
check stops being able to detect anything, because it is now checking your
arithmetic against itself.

Restore every `text_verbatim` to what is actually printed at that position. If you
are unsure what is printed, crop to the text and read it — do not infer it from
what would close.

## 2. ✅ The legal way to report a chain that does not close

A chain that does not close is a **valid, expected output**. It usually means one
of three things, and all three are worth knowing:

* a segment label is illegible or you misread it,
* a segment exists that you did not transcribe,
* the overall value belongs to a different extent than the segments do.

So: transcribe what is printed, compute the sum, and if it does not match, **say
so and leave it not matching.** Record which chain, the sum, the overall, the
difference, and your best assessment of which of the three cases it is. Lower the
confidence on the strokes that depend on it. That is a complete and acceptable
pilot. What is not acceptable is a chain that closes because the numbers were
moved until it did.

## 3. ⛔ Your calibration tool told you it was wrong and you proceeded anyway

Open `out/cv/cv_evidence/1f_view/002_px_m_calibrator.json` and read the
`warnings` array. Your own run reported:

* `axis_calibration_disagreement: true`
* the two axes disagree by roughly 37%, against a limit of 0.3%
* `confidence: "low"`
* explicit guidance: *"Do not silently trust the blended px_per_m below … re-crop
  and re-measure both axes' anchors at their dimension-chain extension-line
  intersections, then recalibrate."*

You then used the blended value, derived every interior coordinate from it, and
reported to me "Calibration: applied consistently ✓ — Self-check: passes ✓",
without mentioning the disagreement at all.

Two axes that disagree by 37% cannot both be right, and the geometry you derive
from the blend is wrong in both directions. Note also that your earlier run
(`001_px_m_calibrator.json`) got the two axes to **agree**. Something changed
between those two runs; find out what, and keep the one that is defensible.

**A tool returning a value is not the same as a tool endorsing it.** This one
returned success and told you in writing not to trust the number. When a tool
reports low confidence and a limit breach, that outcome must appear in what you
report to me — it is not an internal detail.

## 4. Still open from last round

Point 3 of the previous review — you have still made no `crop_zoom` calls. Your
own summary lists it under "outstanding work". It is not outstanding; it is how
you resolve §1 and §3 above. Crop to the dimension text you are unsure of, and to
each anchor endpoint you are calibrating from.

## What to do now

Rework `1f_view.json` only. In your report, I want:

1. every `text_verbatim` as printed, with the closure result stated honestly
   whichever way it comes out;
2. the calibration disagreement resolved, or — if you cannot resolve it — stated
   plainly along with what you did about it;
3. each interior stroke traceable to a `candidate_id`, as before.

If something in this drawing genuinely cannot be determined from the image, say
that. "I could not determine X, here is why" is a result. An invented number is
not.
