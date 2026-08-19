PILOT REVIEW — not approved. Rework `1f_view` only, then stop again.

This review is about METHOD. It contains no information about the building. Every point is
something your own artifact or the toolbox contract says.

1. You never called `crop_zoom` — not once — yet `cv_toolbox.md` requires calibration anchors to be
   dimension-chain ticks / extension lines LOCATED WITH HIGH-ZOOM `crop_zoom`, not picked off the
   drawing at a glance. Your two calibrator calls used the same anchor pair, `px_a=270, px_b=1170`.
   Those are suspiciously round numbers. An anchor located by zooming lands on a sub-pixel value;
   a round number is the signature of an estimate. Re-locate both anchors with `crop_zoom` and
   recalibrate.

2. You anchored ONE axis only (x). With a single axis there is nothing to cross-check against, so
   the tool's "confidence: high" means "no disagreement was detectable", not "this is right".
   Anchor BOTH axes independently and compare them. If the two axes disagree, say so rather than
   averaging them away.

3. `self_check.all_dimensions_transcribed` is `true`, but you recorded 4 dimensions for a fully
   dimensioned floor plan. Reconcile it: either transcribe what is on the drawing, or the
   self-check is not `true`.

4. You wrote 10 separate vertical wall runs. `cv_toolbox.md`'s discipline is that a profiler peak
   is a CANDIDATE, not automatically a wall — each candidate has to be verified before it becomes a
   stroke, and rejected candidates should be logged with a reason.

5. Legal exit — use it, do not fake around it.
   If after re-checking you conclude something genuinely is not there, or that you cannot measure
   it, write that in `uncaptured` with your reason and leave the self-check honest. Do NOT invent a
   stroke, and do NOT adjust a transcribed number, to make a check pass.

Scope: `1f_view` only. Do not start the other five images. Stop when the pilot is rewritten.
