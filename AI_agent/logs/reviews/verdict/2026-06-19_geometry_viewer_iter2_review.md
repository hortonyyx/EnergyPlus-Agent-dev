# Review — geometry viewer iteration 2 (select-by metrics + display fixes)

- **Date**: 2026-06-19
- **Reviewer**: Codex via MCP (danger-full-access, user-authorized; self-driven read + node --check + pytest)
- **Request**: [2026-06-19_geometry_viewer_iter2_request.md](../request/2026-06-19_geometry_viewer_iter2_request.md)
- **Author**: Opus 4.8

## VERDICT (after fixes): CLOSEABLE

First pass = CHANGES REQUESTED (0 High / 3 Medium / 1 Low); all addressed; re-verify = CLOSEABLE.
Confirmed by Codex: gross wall area (no window subtraction), `_js_embed` escaping intact (spaces preserved,
no `</script>` breakout), no CJK in authored files, `node --check` + `pytest` (253) pass.

## Findings + disposition
- **Medium-1 — window→zone via prefix-only** (`zoneOfParent`): a window whose parent name didn't start with a zone
  fell to `?` → no pop-out, broken grouping. **Fixed**: `zoneOfWindow(w)` resolves parent→its surface's zone
  (longest-prefix over `_surfZoneByName`), then zone-name prefix, then nearest zone centroid — never `?`. All three
  window sites (mesh build / measure CAND / edge list) use it. PASS.
- **Medium-2 — edgePick ignored visibility**: could pick an edge currently hidden by floor filter / dup-at-rest /
  display toggles. **Fixed**: EDGES carry {floor,dup,kind}; `edgeVisible(e)` mirrors `applyFilter`; edgePick skips
  failing edges. PASS.
- **Medium-3 — one-endpoint clip**: a segment with one endpoint behind the camera could give a false nearest hit.
  **Fixed**: skip if EITHER endpoint's `p.z` is outside [-1,1]. PASS.
- **Low — stale docstring/comment**: header + an internal section comment still said "shrink"/"polygon-offset".
  **Fixed**: both now describe hide-one-reciprocal-face-at-rest + `WIN_POP` pop-out. PASS.

## Scope recap (iteration 2 of #3 viewer)
select-by floor/zone/surface/edge with metrics (surface→gross area Newell, zone→volume divergence, edge→length);
z-fighting fixed without deleting faces (hide one of each reciprocal pair at explode=0, all shown when exploded);
windows popped proud (`WIN_POP`); continuous vertex-snap measure (button+Esc); explode by floor(up)/zone(3D radial);
uniform orange selection highlight; English-only panel; `_js_embed` script-safe embedding.
Numeric sanity: Σ sm21 zone volumes = 754.5 m³ = 14.75×7.75×6.6 (zones tile the bbox exactly).
