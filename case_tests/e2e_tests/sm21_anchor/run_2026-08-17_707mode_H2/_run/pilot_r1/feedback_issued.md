# Pilot review — 1f_view (NOT approved, rework required)

Two things you did here are right and I want you to keep doing them, because the
main problem below is not that you failed to measure — it is what happened after
you measured.

**Right:** you calibrated **both** axes and the two agree. That is what makes the
`confidence: high` on your calibration mean something; a single-axis calibration
reports the same word while having nothing to check itself against.

**Right:** you ran the dimension-chain closure check, found a side that does not
close, and said so instead of writing a clean self-check over a broken file.

## 1. The main problem: your output does not match your own measurements

You ran `wall_line_profiler` across the whole image on both axes and it returned
peaks. Then you emitted interior wall positions that **do not correspond to those
peaks**. At least one horizontal position you wrote has no peak anywhere near it,
and at least one pair of peaks your own run found is not represented in your
output at all.

So the evidence is sitting in your workspace, correct, unused. This is worse than
not measuring, because the artifact looks evidence-backed and is not.

**Do this:** for every interior stroke in `1f_view.json`, open
`out/cv/cv_evidence/1f_view/*_wall_line_profiler.json`, find the specific peak
that stroke rests on, and make the emitted coordinate follow from that peak and
the calibration — arithmetic only. If a stroke has no peak behind it, it does not
belong in the file. If a peak has no stroke, explain why you rejected it. I want
each interior position traceable to a `candidate_id`.

## 2. Fix what the self-check finds — do not just report it

You found that one side's dimension chain sums to less than the overall
dimension, correctly concluded "this indicates my reading has errors", and then
submitted anyway. The instruction is to run the self-check **and fix what it
finds**. A discrepancy you have located is the cheapest error you will ever get;
it is telling you exactly where to re-measure.

## 3. You never magnified anything

Your whole measurement pass ran at `scale: 1.0` over the full image, and you made
no `crop_zoom` calls at all. At this drawing's calibration a wall is on the order
of ten pixels wide, and two walls with a narrow gap between them will merge into
one blob — or split into peaks you then have to guess at — at that scale. A
whole-image profile is the right way to find *where to look*; it is not sufficient
for deciding *what is there*. Crop to each region you are about to write a stroke
for, at a scale where the wall faces are unambiguous, and profile that.

## 4. Your interior is over-segmented

You emitted 24 wall strokes, several of them well under a metre and several
sharing an endpoint with no visible reason for the break. Some of that is probably
you splitting one continuous element at a junction, and some is probably door
openings being treated as wall ends. Before you re-emit: for each break in a wall,
point to the thing in the image that causes the break. If you cannot, it is one
stroke, not two.

## What to do now

Rework `1f_view.json` only — do not start the other images. When you are done,
report for each interior stroke which `candidate_id` it rests on, and re-run the
closure check and tell me it closes.
