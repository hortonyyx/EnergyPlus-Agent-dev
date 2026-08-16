Better — the self-check is honest now and five strokes are dimension-backed. Still not approved,
for one reason: you keep deferring the actual measuring to "the next pass". There is no next pass.
The pilot is the pass.

Finish it now, on 1f_view:

1. Read the horizontal dimension chain. You already spotted it (you wrote "1240, 2400, 1300, ...").
   Transcribe every segment verbatim into `dimensions`, in order, with its chain id, and check that
   the chain closes against the overall span the same way you closed the vertical one. If a segment
   is unreadable at native resolution, crop_zoom it until it is readable — that is what the tool is
   for. `ocr_texts` is still empty; the numbers you read belong there too.

2. Then place the interior walls from that chain, not by eye. S6 and S7 are still `seen` with no
   refs and round coordinates. Either a dimension pins them, or a pixel measurement does — and if
   it is a pixel measurement, the note must say which pixel coordinate, which origin, and which
   sidecar it came from, so the number can be recomputed.

3. Work through the profiler candidates instead of dropping them silently. For each candidate that
   you did not turn into a stroke, crop it, look at it, and log why it was rejected — a furniture
   edge, a dimension tick, the second face of a wall band, whatever it is. Four crop_zoom calls for
   48 candidates means most of them were never looked at. Rejected candidates are evidence.

4. You went from 12 strokes to 7 by deleting the ones you could not defend. Deleting is not the
   same as verifying: an interior partition that is really on the drawing must end up traced, with
   its position measured. Do not leave a real wall out because it was easier to drop than to
   measure — go measure it.

Then stop for review again. Still only 1f_view.
