# Editable geometry-confirmation step — design notes (roadmap, not yet built)

> **Status: DESIGN / DEFERRED (2026-06-19).** Recorded for later detailed discussion; nothing implemented.
> Owner decision pending on channel + phasing (see §4). The read-only inspection viewer (#3,
> `scripts/tool_scripts/render_geometry_viewer.py`) is the substrate this would extend.

## 1. Goal
Make the geometry-confirmation gate (contracts §1 2/3 ②a; the human gate before the near-deterministic
downstream) **lightly editable**, so the user can fine-tune the model in 3D before committing. Result: the
pipeline after this step is almost fully determined → the outcome is far less black-box.

Editing abilities, by priority:
1. **Move a window** — 3-axis sliders (really 2 DOF on the facade plane + optional size).
2. **Push/pull a wall** — Rhino-style: user first sets a **grid-granularity slider**, then push/pulls a face in
   grid steps.
3. **Adjust material (much later)** — click a surface → show its construction/material → natural-language edit.

## 2. First principle — edit the AUTHORITATIVE geometry, never just the mesh
The pipeline's geometry truth is the **1_correction snapped geometry** (`correction_geometry_snapped.json`:
cells / floors / windows). The deterministic kernel (2_modelling + 3_split_pairing) rebuilds faces / pairing
from it. So every edit must:

    edit → write back to the correction layer → re-run the deterministic kernel → regenerate viewer

Editing `building_geometry.json` directly would bypass the kernel and risk an EP-invalid / inconsistent state
(broken closure / pairing). Routing all edits through the kernel keeps the result EP-valid by construction.

The geometry-confirmation **digest** (`geometry_checkpoint_digest`, approval.py) gives the re-confirm loop for
free: edit → geometry changes → digest changes → stale approval → user must re-confirm before downstream runs.

## 3. Edit → authoritative-layer mapping
| edit | correction-layer change | kernel effect |
|---|---|---|
| move window | window's (facade, along-facade span, z-range) on its wall | re-place fenestration |
| push/pull wall | the **cell rectangle** bound(s) the wall derives from (a shared wall resizes BOTH adjacent zones); snap to grid step | rebuild zones / faces / split-pairing |
| material (later) | 4_mep construction assignment (NOT geometry) | re-author MEP only |

Window-move also doubles as the **manual fix path** for the South-2F window-x issue ([[sm21-review-backlog]] #2).

## 4. Open decisions (discuss before building)
1. **Write-back channel** — the viewer is today a static offline HTML (no server). To persist edits we need a
   browser↔disk channel:
   - **A. local server mode** (`run_stage.py serve-viewer`): container serves localhost, VS Code forwards the
     port to the Windows browser; `fetch` posts edits → write correction → re-run kernel → regenerate. Fluid UX,
     but no longer "double-click offline". Keep the read-only offline viewer for pure inspection.
   - **B. export-patch**: viewer collects edits client-side → user downloads a patch JSON → `run_stage.py
     apply-edits` applies it. No server, but a manual round-trip.
2. **Phasing**: Phase 1 = window move (+ grid snap) — smallest, high value, fixes #2. Phase 2 = wall push/pull
   (cell-grid parametric op — the hardest; shared-boundary resize). Phase 3 = material NL edit (much later).
3. Whether editing lives **inside** the inspection viewer or as a separate "edit session".

## 5. Notes
- This is a meaningful new sub-project; when it starts, write a full design + go through a cross-model review
  cycle (Codex MCP, per §6 #14) before/while implementing.
- See memory [[editable-geometry-confirmation-vision]]; viewer status in [[sm21-review-backlog]] (#3 done).
