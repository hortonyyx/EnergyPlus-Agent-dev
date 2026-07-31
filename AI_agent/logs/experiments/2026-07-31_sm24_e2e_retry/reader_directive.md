# Per-run directive — sm24 复验轮（directed mode）

These instructions are additional to `session_kickoff.md` and the three rule docs. Where this file
and the kickoff disagree on a *file location*, this file wins. Where they disagree on a *rule*, the
rule docs win.

> 主控注（不给执行者看的部分已剔除）：本稿相对 2026-07-30 版有**三处实质修订**，
> 见 §2、§4.7、§7。修订理由记在 `README.md`。

---

## 1. Worked-example location

The kickoff names a canonical worked-example plan JSON. It has been staged for you inside this
workspace and the kickoff text已 points at the staged copy. Read it as a **style / format anchor
only** — it is a different building. Do not copy any of its numbers, room names, or counts.
Do not modify it.

## 2. Measure first. A dimension chain corroborates a measurement; it never originates one.

**This is the single most important instruction in this file, and it is stricter than the previous
run's version of it.**

Every stroke you draw must be **located by a probe measurement you actually ran on the image you are
tracing**. A number transcribed from a dimension chain may then be used to *refine or confirm* that
measured position. A dimension chain is **not**, by itself, sufficient provenance for a stroke.

Concretely:

- **Never** convert a dimension chain's cumulative positions into strokes. A chain segments
  *something*, but the chain alone does not tell you **what** it segments — it may be dimensioning
  window openings, piers, structural bays, or partitions. **Determine what it segments by probing at
  those positions, and only then draw.** If a probe at that position shows no wall-like evidence,
  **do not draw a wall there**, no matter how cleanly the arithmetic works out.
- **Never** use a chain that runs along one drawing to place geometry in a different drawing.
  Elevation chains describe that facade; they do not locate interior partitions on the plan.
- **Never** write a coordinate that came from visually estimating a position. If you cannot measure
  it and cannot corroborate it, write `null` and say so.
- Establish the pixel-to-metre scale explicitly (calibrator recipe) before drawing any stroke, and
  state the scale you derived in your notes.
- Run probes **in a single call**, passing the arguments directly:

  ```
  python tools/run_cv_probe.py --tool wall_line_profiler --image case_data/1f_view.png --out-dir out/cv --axis col
  python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv --bbox 1200,400,1800,900 --sidecar-name 003_crop_zoom
  python tools/run_cv_probe.py --tool px_m_calibrator --image case_data/1f_view.png --out-dir out/cv --anchors-json requests/anchors.json
  ```

  You do **not** need to write a request file first. Measuring should cost you one call, not two —
  measure often.

- For a measurement sweep, do **not** issue those one-off calls sequentially. Put up to 32 ordinary
  probe requests into one bounded batch file under `requests/`, give every request a short stable
  `id`, and run the whole sweep with one command:

  ```json
  {
    "requests": [
      {"id": "plan_rows", "tool": "wall_line_profiler", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "axis": "row"}},
      {"id": "plan_cols", "tool": "wall_line_profiler", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "axis": "col"}}
    ]
  }
  ```

  ```
  python tools/run_cv_probe.py --batch requests/plan_sweep.json
  ```

  The command returns one JSON document whose `results` are keyed by those IDs, so consume the
  sweep from that single response. Every logical probe also writes its normal individual sidecar
  under `out/**`; batching changes latency, not evidence or measurement count. The guard validates
  the entire batch before anything runs, and one invalid request refuses the whole call. A normal
  20-probe sweep should therefore cost one `Write` plus one `Bash`, not 20 sequential probe calls.

  The rules for this form: arguments are strictly `--key value` pairs (no bare arguments, no repeated
  keys, no key left without a value), `--tool` and `--image` are required, `--out-dir` must be inside
  `out/`, and only the options `tools/cv_probe.py` actually declares are accepted. If you pass an
  unknown one, the refusal message lists every accepted option.

- The older form is still available and unchanged, for a request that is easier to express as JSON
  (for example a long inline `--candidates-json`): write the request under `requests/` and run
  `python tools/run_cv_probe.py --request <request.json>`.

**Provenance self-check (mandatory, per image).** After finishing an image, count your strokes by
`provenance`. If **no** stroke is `seen` / measured — i.e. everything is `dimension_derived` — that
is a **failure of this directive**, not a valid result. Say so explicitly in your notes and go back
and measure. Report the counts per image in `reading_summary.md`.

## 3. Deterministic prescan candidates — advisory input, and you must show your work

Prescan output is provided under `prescan/cv_evidence/<image_stem>/prescan/`, now split by the
toolbox's existing mechanical `kind` classification:

- start with `structural_candidates.json` and `combined_overlay.png`; these contain/render only
  `line_band_candidate` entries and are the default low-noise presentation;
- `cc_box_candidates.json` / `cc_box_overlay.png` and
  `tick_candidates.json` / `tick_overlay.png` keep boxes and known dimension-tick candidates
  separately addressable when you need them;
- `candidates.json` plus `all_candidates_overlay.png` remain the lossless all-candidate view.
  Nothing was filtered or dropped; do not start with this noisy view unless the split views leave a
  specific question unanswered.

All of this remains **machine-produced pixel evidence only**. “Structural” is a presentation bucket
for line bands, not a semantic claim that a band is a wall; boxes may be furniture, text, or useful
openings. Semantic acceptance is entirely your call. **Prescan is a place to look, never a reason to
draw.** A candidate becomes a stroke only after §2's measurement.

For this run record your decisions explicitly, per image:

- roughly how many candidates you accepted as real structure, and how many you rejected;
- the *reasons* you rejected the main groups you rejected;
- anything real you found that prescan **missed**;
- whether the prescan overlay actually saved you probe calls, or cost you time to filter.

Put a short per-image version in your notes, and a consolidated version in `reading_summary.md`
under a heading `## prescan and toolbox usage`.

## 4. Completeness self-check before you call an image done

Walk this list explicitly for each image and state the result:

1. Every continuous exterior boundary run is **one** stroke — not chopped at window jambs, dimension
   ticks, door openings, or furniture. Over-segmentation is a known failure mode on cluttered plans;
   door openings get healed into one continuous wall per the pen rules.
2. Every interior partition that separates two rooms is traced, including partitions that are only
   partly visible behind furniture.
3. Dimension chains transcribed verbatim, including the totals — do not re-derive, do not round.
   (Transcribing a chain is required. *Drawing from* a chain is not permitted — see §2.)
4. For elevations: every opening you can see, with its vertical extents, and the facade-orientation
   fields filled exactly as the schema defines them. `local_x_positive` is **purely in-image** —
   it describes which way local-x increases across the screen. It is **not** a world direction and
   must not encode one; do not flip it because you believe the facade faces a particular way.
5. Anything you recognized but deliberately did not trace goes into the `uncaptured` log with a
   reason — recognize-then-log, never silently drop.
6. No spatial-topology reasoning, no world placement, no downstream fields.
7. **Before asserting that a feature class is absent, prove the absence.** If you are about to write
   that an image contains no windows, no interior partitions, or no openings of some kind, first run
   a probe that *would have found them if present*, and record that probe and its result. An
   unprobed absence claim is not acceptable output.

## 5. Order of work

Pilot = `1f_view.png` (the plan). Do it alone, write it out, then **stop and wait** for review.
Do not start the elevations until the pilot has been reviewed.

## 6. Effort logging

At the end of `reading_summary.md`, add a heading `## effort log` with: how many **logical probes**
you ran in total, broken down by recipe; how many batch Bash calls and one-off Bash calls carried
those probes; how many rounds of self-correction you needed; and which parts of the work were still
guesswork rather than measurement. Do not count a 20-request batch as one probe — batching reduces
round trips, never the amount of measurement. Be honest: an accurate low number is more useful than
a flattering one.

## 7. Workspace writing rules (revised — the previous run's constraints no longer apply)

The workspace guard was rebuilt for this run. **It no longer scans the text you write.** You may use
ordinary prose freely — approximation signs, ellipses, ranges, and domain terms such as the exterior
grade line are all fine now. Write normally; do not contort your wording.

What the guard does enforce:

- **You may only write under `out/` and `requests/`.** Everything else in the workspace is read-only,
  including the toolbox, the staged reference file, and the workspace bookkeeping files.
- **A probe's output directory must be inside `out/`.** If you use the optional request-file form,
  the request JSON goes in `requests/`.
- **Shell**: one command per call, no chaining, no redirects, no pipes. The only executable command
  is the probe wrapper, in one of its three forms (see §2):
  `python tools/run_cv_probe.py --tool <name> --image <path> --out-dir out/... [--key value ...]`
  or `python tools/run_cv_probe.py --request <file.json>`
  or `python tools/run_cv_probe.py --batch <file.json>`.
  To inspect a file, use the Read tool.
- Absolute paths outside this workspace are refused.

If a call is refused, the reason string tells you which of the above it hit. Fix that specific thing
rather than rephrasing at random.
