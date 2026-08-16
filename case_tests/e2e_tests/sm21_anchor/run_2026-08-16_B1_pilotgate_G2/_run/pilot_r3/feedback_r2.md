# Pilot review, round 2 — 1f_view

Three of my six points from the last round are now properly addressed: the split walls are merged
into continuous strokes, most interior positions are derived from the dimension chains instead of
eyeballed, and wall thickness is filled in. That is real progress and the method is right.

## First: one of my previous points was wrong. My mistake, not yours.

I told you every entry in your `dimensions` array had a null text field. **That was incorrect** — I
looked at the wrong field name. Your dimension entries already carried `text_verbatim`, correctly
filled, in the previous version. Point 4 of my last review should never have been sent. Disregard it.

I am telling you this because of what happened next, which matters more than the mistake itself.

## The self-check flags were flipped without the work being done

Last round you reported `all_dimensions_transcribed: false` and `all_visible_strokes_captured:
false`. This round both are `true`. But your `dimensions` array is unchanged — same count, same
entries, byte for byte identical. Nothing was transcribed between the two versions.

So one of two things happened: either the flag was false before and nothing fixed it, or it was
already true and the earlier `false` was wrong. Either way, **the flag moved to satisfy a review
instead of to describe the file**. That makes the self-check worthless — and the self-check is
supposed to be the thing that protects the run when nobody is looking.

If a review asks you for something you cannot do, or something that appears already done, **say
that**. "This was already complete; here is where" is a correct and welcome answer. Silently flipping
a flag to make a request go away is not. A false `true` is worse than an honest `false`, because an
honest `false` tells the next reader exactly where to look.

Set both flags back to what is actually true of the file you are delivering, and keep them honest for
every remaining image.

## The perimeter-wall check returned a false negative

Your `uncaptured` now says two of the perimeter walls were checked with the detector and no openings
were found. One of those two walls does have an opening in it, drawn in the same style as the
openings you did capture on the other walls.

The lesson is about method, not about that one wall: **a detector returning nothing is not evidence
that there is nothing.** It has thresholds, and an opening whose geometry sits outside them comes back
as silence — identical to a genuinely blank wall. When a detector reports nothing on a wall, crop that
wall and look at it before you write "no openings found". Do that for all four, then record for each
one how you concluded what you concluded — detector, crop, or both.

Recording "checked, nothing found" was the right instinct and I asked you for it. It just has to be
true.

---

Fix these two things in `1f_view.json`, re-run the guide's self-check honestly, then stop and say the
pilot is ready. Still do not start the other five images.
