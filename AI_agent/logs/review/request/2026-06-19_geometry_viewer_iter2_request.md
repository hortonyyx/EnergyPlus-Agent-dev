# Review request — geometry viewer iteration 2 (select-by metrics + display fixes)

- **Date**: 2026-06-19
- **Branch**: 6.15_ValidationArchM0toM4
- **Reviewer**: Codex via MCP (danger-full-access, user-authorized; self-driven read + node --check + pytest)
- **Author**: Opus 4.8
- **Prior review**: [2026-06-19_geometry_viewer_review.md](../review/2026-06-19_geometry_viewer_review.md) (CLOSEABLE). Since then the viewer
  went through several user-driven iterations; this re-reviews the CURRENT `render_geometry_viewer.py`.

## Scope (only this file + its test)
- `scripts/tool_scripts/render_geometry_viewer.py` (generator + embedded app JS in `_APP_JS`)
- `tests/test_geometry_viewer.py`

The rendered 3D cannot be visually verified headless — judge by READING the app JS + `node --check`
(`python -c "import sys;sys.path.insert(0,'scripts/tool_scripts');import render_geometry_viewer as v;open('/tmp/app.js','w').write(v.app_js())"` then `node --check /tmp/app.js`).

## What changed since the prior review (focus points)
1. **z-fighting fix WITHOUT deleting faces**: ALL faces kept (each zone a closed box, EP reciprocal split-pairing
   preserved). At explode=0 ONE face of each coincident reciprocal pair is HIDDEN (`isDup` = obc==Surface &&
   name>obc_obj) → solid clean shell, no gaps; at explode>0 ALL faces shown, separated by the explode offset.
   Windows are pushed proud of their wall by `popOut` (`WIN_POP=0.03 m`) so they don't z-fight + are pickable.
   Verify: `applyFilter` hides dups only when explode==0; `applyExplode` calls `applyFilter`.
2. **select-by metrics (B)**: SELECT BY = floor / zone / surface / edge. Click reports a metric in `#sel`:
   - surface → polygon AREA (Newell). For a Wall this is GROSS area (the wall polygon is the full rectangle;
     window openings are separate child surfaces and are NOT deducted — labelled as such). **Confirm walls are
     not having window area subtracted.**
   - zone → VOLUME via divergence theorem over the zone's faces (sanity: sum of sm21 zone volumes = 754.5 m³ =
     14.75×7.75×6.6, i.e. zones tile the bbox exactly).
   - edge → LENGTH, via screen-space nearest-segment pick (`edgePick`/`segDist`) on TRUE geometry.
   - All metrics computed on TRUE (un-popped) verts → exact.
3. **measure**: a toggle BUTTON (+Esc), CONTINUOUS (each new click after a pair clears the previous; only latest
   shown), CAD-style screen-space VERTEX snap on TRUE geometry with a live snap ball; markers small (`BALL`).
4. **explode**: by floor (up only) / by zone (full 3D radial from centre). 4_mep gate unaffected.
5. **uniform selection highlight** (`SEL_COLOR` orange) across all modes; `selGroup` overlay for edge highlight.
6. **safety / hygiene**: `_js_embed` escapes `<`/`>`/`&`/U+2028/U+2029 so embedded geometry can't break out of
   `<script>` (regression-tested); `html.escape` on title; offline (no CDN); panel English-only.

## Focus for you
- Correctness of area (Newell) / volume (divergence) / edge length / vertex+edge screen-space picking (incl.
  behind-camera `p.z` guards, explode offset applied consistently to picks).
- The dup-hide-at-explode-0 vs show-all-when-exploded logic — any state where a zone looks non-closed when
  exploded, or gaps/z-fight at rest, or dups wrongly shown/hidden under floor filter + toggles.
- Wall area must be GROSS (not minus windows) — confirm.
- `_js_embed` still escapes correctly (spaces preserved, no `</script>` breakout); no remaining CJK in authored
  HTML/JS/CSS.
- General correctness / resource / edge-case (empty geometry, single floor, window without matching zone prefix).

## Acceptance
- High/Medium/Low + file:line + fix; run `python -m pytest -q` (author: 253) + `node --check`; verdict CLOSEABLE / CHANGES REQUESTED.
