# Review of the pilot — approach APPROVED, deliverable INCOMPLETE

Your method is right and is approved. Keep it. Specifically these were good and should not change:
the explicit pixel-per-metre calibration before drawing anything; verbatim dimension transcription
with chain ids and ordering; deriving perimeter stroke endpoints from the dimension chain rather than
from eyeballing; honest self-check flags; recognize-then-log for furniture.

What is wrong is only the **scope of the deliverable**. A pilot means **one image done completely**,
not a partial skeleton of one image. Your own self-check says `all_visible_strokes_captured: false`
and your unknowns list interior partitions and door arcs as "not yet traced" — by your own report the
image is not finished.

## What to do in this session

Because the approach is already reviewed and approved, do not stop again after the plan. Work through
all five drawings in one pass:

1. **Finish the plan completely.** Every interior partition that separates two spaces, traced by
   measurement. Door openings healed per the pen rules into continuous walls. The correct pen set,
   not `wall` alone. Everything recognized-but-not-traced logged with a reason.
2. **Then do the four elevations**, same discipline: calibrate first, measure, transcribe dimension
   chains verbatim, fill the facade-orientation fields exactly as the schema defines them.
3. Write the summary file at the end, including the two sections the directive asked for
   (prescan/toolbox usage, and the effort log).

## Four specific corrections

1. **Check every `dimension_refs` value actually points at the chain that dimensions that stroke.**
   In the pilot, the stroke you describe as the bottom exterior wall cites a dimension id that belongs
   to the top horizontal chain. Wrong cross-references are worse than absent ones.
2. **You flagged that one side's labels sum to 20400 against a 20000 overall.** Resolve it by
   measuring at pixel level. If it still does not reconcile, record it explicitly as an unresolved
   discrepancy with both numbers — do not silently pick one and do not quietly re-derive.
3. **You concluded "no visible windows in the plan".** Re-check the exterior wall bands at pixel level
   before standing by that. Openings in a plan are usually a break or a thinner parallel pair inside
   the wall band, not a separate symbol. Whatever you conclude, back it with a measurement, not an
   impression.
4. **Only one pen appeared in the pilot.** Re-read the pen rules and use the full legal pen set for a
   plan, including the per-floor fill pen.

## Reminder on where numbers come from

Every coordinate must come from a dimension chain you read verbatim, or from a probe you actually ran.
If neither is available, write `null` and note it. Do not fill gaps by inference from the room layout
or from the count in the supplied text description — that count is context, not a licence to invent
geometry that you did not measure.
