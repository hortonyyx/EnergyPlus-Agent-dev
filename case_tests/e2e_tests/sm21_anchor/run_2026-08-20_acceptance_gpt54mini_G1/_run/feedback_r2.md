Pilot review round 2. The calibration itself is now correct — that part is accepted.

The problem is that the stroke coordinates in your pilot output were derived from the
SUPERSEDED single-axis scale. Your own evidence shows this: the scale in your latest
calibration sidecar differs from the one that was in effect when those coordinates were
written, and the output file is unchanged since before the recalibration.

To be explicit, because the previous note was ambiguous and that was my mistake, not yours:

WHAT MUST CHANGE: the numeric coordinates of the strokes and openings you already
identified, so that they follow the corrected two-axis scale.

WHAT MUST NOT CHANGE: which walls and which openings you identified. Do not re-interpret
the drawing, do not add or remove strokes, do not revisit your reading decisions.

If you did not retain the pixel positions behind each stroke, you may re-measure them with
the toolbox — re-measuring pixels is expected and allowed. The earlier phrase "do not
re-trace" meant "do not redo your interpretation of what is there"; it did NOT mean "leave
the numbers as they are".

Then re-run the self-check and stop again.
