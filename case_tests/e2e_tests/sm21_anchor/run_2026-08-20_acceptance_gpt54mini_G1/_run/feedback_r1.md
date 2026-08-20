Pilot review: one process item, then re-run the pilot self-check and stop again.

Your calibration used a SINGLE axis: the `px_m_calibrator` call carries one anchor
(axis "x") and no anchor for the other axis.

`px_m_calibrator` accepts BOTH axes in ONE call. The reading guide's cross-axis
agreement check exists precisely to compare the two independently-derived scales
against each other; with only one axis supplied, that check has nothing to compare
and is silently inert for this reading.

Required: redo the calibration as a SINGLE call supplying both an x anchor and a y
anchor, each tied to its own overall dimension chain, so the cross-axis agreement
figure is actually produced. Then propagate the resulting scale through the strokes
you have already drawn and re-run the self-check.

Do not re-trace the drawing. This is about how the scale was established, not about
what you saw.
