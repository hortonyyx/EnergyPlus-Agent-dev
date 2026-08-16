# Pilot review — 1f_view

The calibration work is good: you ran a real two-axis calibration and both axes agreed, so your
pixel-to-metre conversion is trustworthy. Keep working that way. What follows are method problems in
the pilot, not a list of answers — fix them on this image before you touch the other five.

## 1. You healed door openings and then still split the wall

Your own notes say a door opening was healed on the long horizontal interior walls, but each of those
walls is emitted as two separate strokes. Those two statements contradict each other: a healed
opening means the wall is continuous through it and must be ONE stroke. Right now the same physical
wall is counted twice, which inflates the wall count.

Go through every stroke and ask: is this a whole wall, or a piece of a wall that I cut at a door, a
furniture overlap, or a place where the line looked interrupted? Merge the pieces that belong to one
continuous wall. Use `crop_zoom` on each junction you are unsure about rather than deciding from the
full-size view — a crop is the only way to tell "two walls meeting" from "one wall crossing".

## 2. Check every perimeter wall for openings, not only two of them

Your window strokes all sit on two of the four perimeter walls. Do not assume the remaining two are
blank. Run `window_cc_detector` (or crop and look) along EACH of the four perimeter walls
independently and record what you find on each. If a wall genuinely has none, say so explicitly in
`uncaptured` — "I checked and there is nothing" and "I never looked" must not produce the same
silence in your output.

## 3. Use the dimension chains you already transcribed

Almost every interior wall you emitted is marked `seen`, yet this drawing carries dimension chains
along its edges that fix those positions. `seen` means "I could only eyeball it". Where a chain
number pins a position, derive it and mark it `dimension_derived`, and put the chain entries you used
in `dimension_refs`. If a position truly is not pinned by any chain, keep `seen` — but then it should
be a small minority, not the default.

## 4. Transcribe the dimension text verbatim

Every entry in your `dimensions` array has a null `text`. The number as printed on the drawing is the
evidence for everything downstream; without it nobody can re-derive your reasoning. Transcribe what
is printed, exactly, for every dimension you use. Your own self-check already reports
`all_dimensions_transcribed: false` — that flag is not something to file and move past, it is the
thing to go fix.

## 5. Wall thickness is annotated on this drawing

Your wall strokes carry `thickness_m: null`. Look for the thickness annotations and use them.

## 6. Two self-check items are false

You reported `all_dimensions_transcribed: false` and `all_visible_strokes_captured: false` and then
declared the image finished. A false self-check item is a defect to repair, not a caveat to publish.
Resolve both, or state precisely what blocks each one.

---

Redo `1f_view.json` addressing all six points, then re-run the guide's self-check against the
corrected file.

**Then stop again and say the corrected pilot is ready.** Do not start the other five images yet —
the pilot is not approved until the corrections have been looked at. Ending your turn there is the
right move.
