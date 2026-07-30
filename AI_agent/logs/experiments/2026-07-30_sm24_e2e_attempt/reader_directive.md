# Per-run directive (directed mode)

These instructions are additional to `session_kickoff.md` and the three rule docs. Where this file
and the kickoff disagree on a *file location*, this file wins. Where they disagree on a *rule*, the
rule docs win.

## 1. Worked-example location

`session_kickoff.md` names a canonical worked-example plan JSON by a repository path. That path is
outside this workspace and is not readable here. The same file has been provided to you at:

    reference/worked_example_plan.json

Read it as a **style / format anchor only** — it is a different building. Do not copy any of its
numbers, room names, or counts. Do not modify it.

## 2. The pixel toolbox is REQUIRED, not optional — measure, do not eyeball

This is the single most important instruction in this file.

- Every coordinate you write must trace back to either (a) a number you read verbatim from a
  dimension chain in the drawing, or (b) a deterministic probe measurement you actually ran.
- **Never** write a coordinate that came from visually estimating a position on the image. If you
  cannot measure it and cannot read it from a dimension chain, write `null` and say so.
- Run the probes through `python tools/run_cv_probe.py --request <request.json>` with the request
  JSON written inside this workspace. Use crop-zoom to verify anything you are unsure about, at the
  pixel level, before you commit a number.
- Establish the pixel-to-metre scale explicitly (calibrator recipe) before drawing any stroke, and
  state the scale you derived in your notes.

## 3. Deterministic prescan candidates — advisory input, and you must show your work

Prescan output is provided under `prescan/cv_evidence/<image_stem>/prescan/`
(`candidates.json` + `combined_overlay.png`). It is **machine-produced pixel evidence only**, with
no semantics: it does not know which bands are walls, which are dimension lines, which are furniture,
or which are text. Semantic acceptance is entirely your call.

For this run you are required to record your decisions explicitly, per image:

- roughly how many candidates you accepted as real structure, and how many you rejected;
- the *reasons* you rejected the main groups you rejected (e.g. "outer ring of short bands = dimension
  ticks", "small boxes in the lower-left room = furniture");
- anything real you found that prescan **missed**;
- whether the prescan overlay actually saved you probe calls, or whether it cost you time to filter.

Put a short per-image version of this in your notes, and a consolidated version in
`reading_summary.md` under a heading `## prescan and toolbox usage`.

## 4. Completeness self-check before you call an image done

Walk this list explicitly for each image and state the result:

1. Every continuous exterior boundary run is **one** stroke — not chopped at window jambs, dimension
   ticks, door openings, or furniture. Over-segmentation is the number one failure mode on cluttered
   plans; door openings get healed into one continuous wall per the pen rules.
2. Every interior partition that separates two rooms is traced, including partitions that are only
   partly visible behind furniture.
3. Dimension chains transcribed verbatim, including the totals — do not re-derive, do not round.
4. For elevations: every opening you can see, with its vertical extents, and the facade-orientation
   fields filled exactly as the schema defines them (do not invent your own convention).
5. Anything you recognized but deliberately did not trace goes into the `uncaptured` log with a
   reason — recognize-then-log, never silently drop.
6. No spatial-topology reasoning, no world placement, no downstream fields.

## 5. Order of work

Pilot = `1f_view.png` (the plan). Do it alone, write it out, then **stop and wait** for review.
Do not start the elevations until the pilot has been reviewed.

## 6. Effort logging

At the end of `reading_summary.md`, add a heading `## effort log` with: how many probe calls you made
in total, broken down by recipe; how many rounds of self-correction you needed; and which parts of the
work were still guesswork rather than measurement. Be honest — an accurate low number is more useful
than a flattering one.

## 7. Workspace shell and writing constraints (read this before you write anything)

The workspace guard does a purely lexical scan of **every** tool input, including the *content* of
files you write. These will be rejected outright, and retrying with the same character wastes your
budget:

- The tilde character, anywhere — including in prose as an "approximately" sign. Write "about 18",
  never the tilde form.
- Two consecutive dots, anywhere — including a three-dot ellipsis in prose, and numeric ranges.
  Write "8 to 12", not a dotted range, and end sentences with a single full stop.
- Shell pipes, semicolons, ampersands, backticks, redirects, and command substitution. One command
  per call, no chaining. Do not redirect to the null device.
- The only executable command is the probe wrapper, invoked as exactly four tokens:
  `python tools/run_cv_probe.py --request <file.json>`. To inspect a file, use the Read tool, not
  a shell command.
- Absolute paths outside this workspace, and a handful of reserved words tied to the evaluation
  machinery. If a write is rejected and you cannot see why, rephrase the sentence in plainer words
  rather than retrying it unchanged.

Budget one attempt, not three. If a phrasing is rejected twice, change the phrasing.
