# Correction to the previous review — `provenance` vocabulary

My previous review said "the label has to match how you got the number" without
telling you what the legal labels are. That was my omission, and it led you to
write `provenance: "pixel-measured"`, which is not a value the schema accepts.
All six of your view files are currently rejected for this one reason.

`provenance` is a **closed vocabulary**. Exactly four values are legal
(`guide.md` §2, reading schema):

- `dimension_derived` — the coordinate was computed from transcribed dimension
  chain values (and the stroke cites those ids in `dimension_refs`)
- `seen` — you located it in the image, including by pixel measurement with the
  CV probes, without deriving it from a dimension chain
- `estimated` — you approximated it
- `unknown`

A coordinate you measured in pixels and converted with your calibration, but did
not derive from a dimension chain, is **`seen`**. That is what `seen` means
here; it does not mean "eyeballed". Nothing else about your files needs to
change for this correction.

## What to do

Replace every `"pixel-measured"` with the correct legal value for how that
particular coordinate was actually obtained, in all six files. Leave your
existing `dimension_derived` strokes as they are. Change nothing else — do not
re-trace, do not re-measure, do not adjust coordinates.

Then re-check every file against `guide.md` §6 and confirm no other field uses a
value outside its schema vocabulary.

There is no further review after this one.
