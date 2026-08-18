# Pilot review — 1f_view (NOT approved, rework required)

Your pilot is not accepted. The problems below are all about **method**, not about
which numbers I want to see. Do not guess at what I am looking for — re-derive
everything from the image with the tools.

## 1. Your interior geometry is not backed by any measurement

Look at what you actually ran: **one** `px_m_calibrator` call with **one** anchor on
**one** axis, and **one** `crop_zoom` at `scale: 1.0` — which is a plain crop, not a
zoom, so it magnified nothing. That is the entire measurement record for this image.

Then you emitted interior wall positions as short, round numbers. Those numbers
cannot have come from the pixels, because you never looked at the pixels at a
magnification where a wall edge is resolvable. **Every interior stroke position in
your output is currently an estimate presented as an observation.** That is the one
failure mode this pipeline exists to prevent.

Redo it: for **each** interior wall, crop to it at a scale where you can see the two
edges of the wall, read the edge positions in pixels, and convert with the
calibration. One crop per wall band that you actually need to resolve — not one crop
for the whole drawing.

## 2. Do not read interior positions off the dimension chains

The dimension chains around the outside of this drawing describe the **facade**
openings and the overall extents. They are not a description of where the interior
partitions are. If an interior position in your output can be traced to a number you
read in a dimension chain rather than to a pixel you measured, it is unsupported.
Measure the partition itself.

## 3. Verify composition before you commit to it

Where you have drawn a single stroke running the full width or full depth of the
plan, go back to the image and confirm from the pixels that it really is one
continuous element — and, separately, that it is only one. Do the same in the other
direction: where you have split something into several strokes, confirm the split
corresponds to something visible, not to a junction you assumed.

I am not telling you which way any particular element goes. Measure it and let the
pixels decide.

## 4. Calibrate both axes

You calibrated the horizontal axis only. With a single axis there is nothing for the
cross-axis agreement check to compare against, so the `confidence: high` on your
calibration is **not earned** — it is what the tool reports when it has nothing to
disagree with. Supply an anchor on the other axis too and look at what the tool says
about agreement between them. If it flags disagreement, that is information you must
act on, not a warning to pass over: the tool now returns success even when it
disagrees with itself.

## 5. Your own script did the setup and then threw the result away

`out/measure_1f.py` builds column and row intensity profiles — which is the right
idea and the right tool for finding wall lines — and then prints only aggregate pixel
counts and never extracts the peaks. You did the hard part and discarded the answer.
Print the peak positions, convert them, and compare them against what you wrote.

## 6. Your self-check reported something your file does not contain

Your closing summary states that `scale_origin` was "properly omitted (null)". Your
`1f_view.json` contains a populated `scale_origin` object. One of those two is wrong,
and I cannot tell which one you meant.

Run the §6 self-check **against the file on disk**, item by item, opening the file and
checking the actual value — not against your recollection of what you intended to
write. A self-check that reports on intent instead of content is worse than no
self-check, because it produces a clean bill of health for an artifact nobody read.

## What to do now

Rework `1f_view.json` only. Do not start the other images yet — when the pilot is
right, the method that made it right is what you will apply to the rest, and there is
no point mass-producing until then. When you have reworked it, run the §6 self-check
against the file as written, and report what you changed and what evidence each
interior position now rests on.
