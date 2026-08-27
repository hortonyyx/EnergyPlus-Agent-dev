# gt_sources/ — signed conversion inputs (persistent, judge-only)

> **F-118**: this directory previously had no README anywhere in the repo. The
> management docs listed it only as "must not be modified" — but "must not be
> modified" is not the same statement as "must not be deleted or relocated",
> and nothing had ever said the second one. This file says it.

## What lives here

`gt_sources/<case>/` holds the two inputs the human reviewer actually signed
when a case's `gt.json` was approved — the source Tianzheng DXF and the
conversion `request.json` — plus whatever intermediate converter artefacts
(`normalized.dxf`, `manifest.json`, `source_map.json`, `conversion_report.json`)
happen to have been placed alongside them. Population is now automatic: since
F-117, `promote_gt_v3` (`src/agent/judge/gt_promotion.py`) writes `source.dxf`
and `request.json` here itself, atomically, as part of promoting a case.

## Why this directory must persist

This is the **only** place `src/agent/judge/gt_raw_layer.py`'s mechanical
reproduction gate (`find_signed_request` / `find_signed_source_dxf`) will ever
look. Those two functions never trust a file because of *where* it sits —
every match is re-verified by recomputing its content hash against the value
the human actually signed (`review_ack.json`) — but they only ever look
**here**. If a file is not in this directory, it does not exist as far as the
reproduction gate is concerned, no matter how many byte-identical copies of it
survive somewhere else in the repo (this happened once already: see F-111 in
`AI_agent/plan.md`).

## This is a different kind of directory than `AI_agent/logs/`

[`AI_agent/logs/README.md`](../../../AI_agent/logs/README.md) declares that
tree to be **process traces that may be cleaned at any time** — that is
correct and intentional for *that* directory, and it is exactly why signed
requests that used to be resolved out of `AI_agent/logs/experiments/` were an
availability bug (F-111): the trust root's *authority* never depended on
location, but its *availability* did, and it was sitting somewhere declared
disposable.

`gt_sources/<case>/`, like its sibling `gt/<case>/` (see
[`../gt/README.md`](../gt/README.md)), is answer-adjacent data with no
disposable-copy declaration anywhere else. ⛔ Do not delete, move, or
`.gitignore` this directory or any case subdirectory under it as part of a
cleanup pass — doing so does not merely lose a convenience copy, it makes that
case's mechanical reproduction gate report `inputs_unavailable` until a human
re-signs it.
