# rules.md split map — geometry → kernel / physics → 4_mep / contract → assembly

> **Step 2 of the 0–5 pipeline refactor** (handoff
> [2026-06-09_pipeline_0-5_refactor_handoff.md](../logs/2026-06-09_pipeline_0-5_refactor_handoff.md)).
> Classifies every section of [phase2/rules.md](../../skills/energyplus_mcp_twostep/phase2/rules.md)
> by where it belongs under the target architecture
> ([pipeline_stage_contracts §0.1](pipeline_stage_contracts.md)), names the kernel
> function that already implements each geometry rule (or marks a GAP), and records
> the **sequencing decision**: rules.md is *not* gutted in Step 2 — it stays the live
> phase2b prompt until phase2b is decoupled at Step 5.

---

## 0. Why rules.md is not gutted yet (sequencing)

`rules.md` is the live system prompt for **phase2b** ([phase2.py](../../src/agent/phase2.py)
`run_phase2b`), which today authors the **entire** `IntakeOutput` including all geometry.
The deterministic geometry kernel ([geometry/build.py](../../src/agent/geometry/build.py))
already implements the geometry, but is **not wired into the pipeline** (Step 4) and
phase2b is **not yet decoupled** (Step 5). Removing geometry from rules.md now would
strip the live phase2b of rules it still needs → behavior change, violating the
no-behavior-change-until-wiring principle.

**Decision:** Step 2 = *verify + map* only. Geometry physically leaves rules.md at
**Step 5**, when phase2b is replaced by `4_MEP` (LLM physics) + `5_intakeoutput`
(deterministic assembly) and the kernel feeds the geometry specs. Until then this
map is the spec; `rules.md` is byte-for-byte unchanged.

## 1. Coverage verification (Step 2 risk retired)

The risk note was "verify the kernel covers the original LLM geometry edge cases
(benchmark vs sm20 clean IDF)". Added to
[tests/test_geometry_kernel.py](../../tests/test_geometry_kernel.py) (existing 6 tests
untouched):

- `test_sm20_shaped_misaligned_three_floor_clean` — 3 floors, **4 / 3 / 2 cells**,
  no shared partition break between any two floors (maximally misaligned cross-floor
  split-pairing). Passes the real `validate_interzone_surface_pairs` gate with **0
  issues** by construction — the case the one-step LLM got right and staged phase2
  broke (sm20/sm21, [split_pairing_kernel_reference §2.5](../reference/split_pairing_kernel_reference.md)).
- `test_window_attaches_on_upper_floors` — windows on F1/F2/F3 south facade each
  attach to the correct exterior wall with z inside the parent wall (the multi-floor
  fenestration / CHKSBS-prevention path rules.md Step 6 drove by hand).

8/8 kernel tests green.

## 2. Section-by-section destination

Destinations: **KERNEL** = deterministic geometry code (modelling+split_pairing);
**UPSTREAM** = phase2a correction (cells/windows already world-frame & corrected when
they reach the kernel); **PHYSICS** = `4_mep/`; **CONTRACT** = `5_intakeoutput`
deterministic assembly (today inside phase2b); **GAP** = not yet implemented anywhere.

| rules.md section | destination | implemented by / note |
|---|---|---|
| §0 Input/Output (11-field contract, error budget) | CONTRACT | `IntakeOutput` schema; assembly owns field set |
| §1.1 world coordinate system | UPSTREAM + KERNEL | phase2a emits world-frame; kernel keeps it (build.py uses cell coords as-is) |
| §1.2 elevation local→world translation | UPSTREAM | phase2a applies `phase1_summary §3` formulas; CorrectedGeometry windows are already world-frame |
| §2.1 footprint dimensions | UPSTREAM | phase2a produces `footprint_x/y` + per-cell x/y |
| §2.2 floor heights / per-floor z | UPSTREAM | phase2a produces `Floor.z_floor` + `ceiling_height` |
| §2.3 wall enclosure → zones | UPSTREAM | phase2a derives cells from wall strokes; **kernel starts from cells by design** (not a kernel gap) |
| §2.4 window → world rect → parent facade | UPSTREAM (world rect) + KERNEL (parent wall pick) | phase2a gives `facade`+world `span`+`z`; kernel `_find_parent_wall` picks the exterior wall |
| §2.5 dimension two-way use / checksums | UPSTREAM | phase2a arbitration (trust dims); not a kernel concern |
| §2.6 coverage / unsupported-geometry | UPSTREAM | tiling (union=footprint, no overlap/void) + "don't fabricate" = phase2a/zonification. **No physics.** Kernel has a defensive OVERLAP guard (`build.py` notes) as backstop only |
| §3 Step 1 `building` | CONTRACT | from testdata; non-geometry |
| §3 Step 2 `site_location` | CONTRACT | from testdata; non-geometry |
| §3 Step 3 `zone_specs` (cell=zone, x/y/z, role, granularity) | KERNEL (geometry) + CONTRACT (role/naming) | `build_geometry` zone creation per cell; role carried from `Cell.role`; corridor/special-space granularity is an UPSTREAM zonification rule |
| §3 Step 4 `surface_specs` (4 walls+floor+ceiling, OBC, reciprocal pairing, **cross-floor split-pairing**) | **KERNEL** | walls: `_wall_verts` + same-floor boundary pairing; floor/ceiling: cross-floor `intersection` pairing; Outdoors/Ground/Surface OBC + `obc_obj` reciprocity — all in `build_geometry` |
| §3 Step 5 `material_specs`/`construction_specs` (+ §5.1 interzone single-construction reverse symmetry) | PHYSICS | construction assignment → `4_mep`. NB the **pairing** is KERNEL; assembly must give both paired faces the **same** construction name (`Cons_InterFloor`) to satisfy EP reverse-layer rule |
| §3 Step 6 `fenestration_specs` (per-window record, vertices, self-check) | KERNEL (vertices/parent/z) + CONTRACT (semantic fields) | `_window_verts` + `_find_parent_wall`; CHKSBS-prevention is structural (window z within parent wall) — kernel-enforced |
| §3 Step 7 `schedule/people/lights/hvac` | PHYSICS | already moved to [4_mep/mep.md](../../skills/energyplus_mcp_twostep/4_mep/mep.md) (Step 1); rules.md Step 7 points there |
| §4 vertex synthesis (CCW-from-outside table, window vertex table) | **KERNEL** | `_wall_verts` / `_ring_verts` / `_window_verts` + `_orient`/`_newell` (normal-based, supersedes the hardcoded tables) |
| §5 naming rules (EP-safe chars, cross-field literal-identical) | CONTRACT | assembly; kernel already emits EP-safe names via `_safe()` |
| §6 disallowed writing | CONTRACT | mostly anti-template discipline for the LLM; moot once geometry is deterministic |
| §7 self-check list | split | geometry items (coverage, split-pairing enumerated, CHKSBS, z-continuity, interzone single-construction) become KERNEL invariants + the InterZone gate; contract items (11 fields, naming, schedule completeness) stay CONTRACT |

## 3. Gaps found (feed Step 3 kernel module split)

No hard geometry GAP for the rectangular regime — `build_geometry` covers walls,
floor/ceiling split-pairing, roof/ground, windows, and outward-normal orientation, and
passes the gate on the sm20-shaped benchmark. Items to carry forward (not blocking):

1. **Construction naming on paired faces** (§5.1) is *assembly*, not kernel — but the
   kernel must expose enough to let assembly apply "same construction both sides". The
   kernel already pairs faces reciprocally; assembly (`5_intakeoutput`, Step 5) assigns
   `Cons_InterFloor` to both. Track in Step 5.
2. **Window on a partly-interior facade wall**: `_find_parent_wall` needs an `Outdoors`
   wall spanning the window. If a facade edge is split into interior+exterior pieces and
   the window lands on the exterior remainder, confirm the remainder wall still spans it.
   Not exercised by current cases; add a kernel test if such a case appears.
3. **Non-rectangular (L/U, setback)**: kernel is already polygon-native (shapely) and the
   L-shape/setback tests pass; the §4 hardcoded 4-vertex tables are superseded by
   `_newell`-based orientation. Confirmed covered, not a gap.
4. **Corridor / special-space granularity & coverage** (§2.6, §3 Step 3) are UPSTREAM
   (phase2a/zonification produce the cells); the kernel only realizes given cells. Keep
   as correction-layer responsibility.

## 4. What this means for later steps

- **Step 3** authors the `2_modelling/` + `3_split_pairing/` skill specs from the KERNEL
  rows above, paired with the two code modules `build.py` splits into.
- **Step 5** removes the KERNEL + (geometry half of) CONTRACT rows from `rules.md`, leaving
  `5_intakeoutput` with the CONTRACT residue and `4_mep` with PHYSICS; this is when
  `rules.md` is actually edited.
