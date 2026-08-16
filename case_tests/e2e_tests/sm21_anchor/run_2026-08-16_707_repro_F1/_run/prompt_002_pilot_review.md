Pilot review. Not approved yet. Every point below is a contradiction inside your own output or a
step of cv_toolbox.md you skipped — resolve them on 1f_view before touching any other image.

1. Your calibration disagrees with itself. You recorded x = 15.00 m / 1613 px and
   y = 8.00 m / 1244 px. Those are 0.00930 and 0.00643 m/px — 44% apart. On an orthogonal plan at
   one scale the two axes must agree. So at least one of those pixel spans, or the dimension you
   paired it with, is wrong. Do not write any coordinate until the two axes agree; find which
   endpoint pair is wrong and re-measure it.

2. Dangling dimension references. S2 cites D6 and S4 cites D7, but your `dimensions` array only
   contains D1–D4. Either those entries were never transcribed or the ids are invented.

3. `all_dimensions_transcribed: true` is not consistent with 4 dimension entries and an empty
   `ocr_texts`. Go read the drawing's dimension chains — all of them, including the ones that break
   the overall span into segments — and transcribe them verbatim.

4. `all_visible_strokes_captured: true` is not consistent with your own note that windows were
   deferred. A self-check field that disagrees with your summary is worse than a false one, because
   nothing downstream can tell.

5. Every interior stroke (S5–S12) has an empty `dimension_refs`, and their coordinates are all
   round numbers. That is eyeballing. The directive for this run is measure-before-draw: each of
   those positions must come from a dimension chain or from a pixel measurement you can point at.

6. You had 19 row + 29 column profiler candidates and emitted 12 strokes, with no crop_zoom calls
   and no logged accept/reject reasons. cv_toolbox.md requires you to verify candidates by cropping
   and to log each accept and each reject with its reason — rejected candidates are evidence, not
   clutter to drop silently. Right now there is no way to tell which of those 48 candidates you
   considered, or why the ones you dropped were dropped.

Redo the 1f pilot on that basis and stop again for review. Do not batch the other images yet.
