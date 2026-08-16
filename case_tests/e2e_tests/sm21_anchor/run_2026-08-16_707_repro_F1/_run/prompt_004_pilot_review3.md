Not approved. The interior walls are now all `dimension_derived`, but the dimensions they derive
from are not transcriptions — they are composites you assembled, and they do not survive their own
arithmetic. Three things, all checkable inside your own file:

1. One entry per transcribed number. `DX_C3` has
   `text_verbatim: "1240,2400,1300,1240,2400,1240,1300"` and `value_m: 11.08`. That is seven
   different numbers in one field plus a running total in another. `text_verbatim` means the single
   number printed on the drawing at that spot. Split them: one entry per printed segment, in chain
   order, each with its own verbatim text and its own value. Cumulative positions are something you
   compute from the chain, not something you store as a dimension.

2. Your own sum is wrong. 1240+2400+1300+1240+2400+1240+1300 = 11120, not 11080. A 40 mm arithmetic
   slip inside the field you are using to place walls means the wall positions built on it are also
   wrong.

3. The chain does not close and you used it anyway. You reported the horizontal segments summing to
   15360 against an overall of 15000 — a 360 mm gap — flagged it as "pending verification", and then
   placed S7–S12 from it regardless. A chain that does not close means at least one segment was
   misread. Find which one: crop_zoom each segment label along that chain and read it at zoom until
   the sum closes on 15000. That is the whole point of measure-before-draw — the closure check is
   what tells you the transcription is right, and you are skipping the check and keeping the number.

Also: `all_dimensions_transcribed` is back to `true` while your own `unknowns_noted` says the
horizontal chain is still unverified. Keep that field honest — it was honest one turn ago.

Fix the chain first, then re-place the interior walls from the fixed chain. Stop for review again.
