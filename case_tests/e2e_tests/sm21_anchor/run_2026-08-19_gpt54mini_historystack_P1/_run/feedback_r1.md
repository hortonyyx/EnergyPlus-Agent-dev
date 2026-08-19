PILOT REVIEW — not approved yet. Rework `1f_view` only, then stop again.

This review is about METHOD and INTERNAL CONSISTENCY of your own file. It contains no
information about the building. Every point below is something your own artifact says.

1. Your file contradicts itself.
   `self_check.all_visible_strokes_captured` is `true`, but your own `uncaptured` list
   names "healed door openings on upper corridor wall" and "...on lower corridor wall".
   You referred there to wall runs for which there is no corresponding stroke in `strokes`.
   Reconcile it: either those runs belong in `strokes`, or the self-check is not `true`
   and you must say why they are absent.

2. Your provenance does not describe what you actually did.
   All 15 wall strokes are `provenance: "seen"` with empty `dimension_refs`, yet you really
   did run the toolbox (crop_zoom x3, wall_line_profiler x2, window_cc_detector x1).
   Any coordinate that came from evidence must point at that evidence.

3. You never calibrated.
   `px_m_calibrator` was not called once. Per `cv_toolbox.md`: calibrate before writing metre
   coordinates, take anchors from dimension-chain ticks / extension lines located with
   high-zoom `crop_zoom` (not wall endpoints, not text baselines), target residual <= 1 px,
   and derive every metre coordinate from that single conversion — recorded in the note.

4. Legal exit — use it, do not fake around it.
   If after re-checking you conclude something genuinely is not there, write it in
   `uncaptured` with your reason and leave the self-check honest. Do NOT invent a stroke,
   and do NOT adjust a transcribed number, to make a check pass. An honest "I could not
   measure this" is a better answer than a number that closes the arithmetic.

Scope: `1f_view` only. Do not start the other five images. Stop when the pilot is rewritten.
