# Geometry-First Zonification Architecture Review

Date: 2026-05-30
Reviewer: Codex
Scope: Architecture review for `AI_agent/architecture/geometry_first_zonification.md` and `AI_agent/capability/recognition_modeling_capability.md` Section 8. No implementation diff reviewed.

## Verdict

Directionally sound. The proposed split is the right move: keep LLMs on perception / intent / zoning judgment, and move surface cutting, matching, reciprocal OBC assignment, and degeneracy avoidance into deterministic geometry code.

Two-leg parallel work is also the right portfolio choice. The faithful leg is the path to a reusable drawing-to-building-model capability; the re-topology leg is the path to robust BEM production. They share enough substrate that running both is not wasteful, as long as the shared artifact is typed resolved geometry rather than more natural-language `surface_specs`.

My main objection is wording strength, not direction: "coverage completeness becomes a construction invariant" is true only after the intermediate representation explicitly models not just zone floor polygons, but also voids, roofs/exposed slabs, vertical merge/open-to-below regions, and intended inter-story adjacency. A planar partition alone is insufficient for B5/B6. The design should promote those exceptions into first-class schema now, before the kernel is built.

## Findings

### 1. High - The "construction invariant" claim needs typed void / roof / slab semantics, not only planar partitions

Evidence:
- The proposal says a legal per-floor planar partition makes coverage holes impossible after extrusion and matching (`geometry_first_zonification.md` lines 90-92).
- The same document already admits setbacks, atria/open-to-below, and sloped roofs require exceptions (`geometry_first_zonification.md` lines 107-114).
- Current phase2 rules explicitly forbid silently normalizing setbacks, atria, and multi-footprint cases into one clean rectangular building (`phase2/rules.md` lines 126-139).
- The present interzone validator documents exactly the blind spot: absent intended interior regions are invisible to a per-pair graph (`interzone.py` lines 26-34).

Risk:
A floor can be perfectly partitioned and still produce the wrong vertical boundary semantics. Example: for a setback, the lower roof-exposed area is legitimately Outdoors; for an atrium/open-to-below, the area is legitimately not a floor pair; for a missed upper floor, the same shape is an erroneous coverage hole. Geometry alone cannot distinguish those cases without intent labels.

Recommended action:
Change the invariant from "planar partition alone guarantees coverage" to:

- `story_footprints[]`: per-floor exterior polygon, holes allowed.
- `zone_partitions[]`: zones tile `story_footprint - explicit_voids`.
- `vertical_features[]`: `open_to_below`, `stacked_zone`, `shaft`, `atrium`, `stairwell`, `setback_roof`, `cantilever`.
- `expected_adjacency[]`: generated from those features, then consumed by the kernel.

Then the invariant becomes sound: the kernel can guarantee coverage of all expected adjacencies, and any absent adjacency is either a declared void/roof condition or an error.

### 2. High - A/B split is useful but misses a third class: simulation abstraction fidelity

Evidence:
- The design splits problems into A = geometric watertightness and B = noisy perception arbitration (`recognition_modeling_capability.md` lines 137-147).
- The re-topology doc correctly notes zoning granularity has energy consequences (`geometry_first_zonification.md` lines 120-122).
- The re-topology leg deliberately discards real room geometry and replaces it with thermal-zone blocks (`recognition_modeling_capability.md` lines 132-135).

Risk:
Some failures are neither "can the blocks fit" nor "which drawing evidence is true." They are modeling-abstraction choices: perimeter/core zoning depth, grouping by use, window redistribution, envelope area conservation, internal mass / infiltration / adjacency exposure changes, and HVAC assignment after zones are merged. These can pass geometry gates and perception audits while materially changing loads.

Recommended action:
Add C class: **BEM abstraction fidelity**. Track it separately from A/B with acceptance metrics:

- floor area / exterior wall area / roof area residual by floor and facade;
- WWR residual by facade and floor;
- zone count / zoning method chosen (`room`, `perimeter_core`, `user_grouped`);
- room-to-thermal-zone mapping table;
- load assignment deltas when zones are merged.

This makes "wrong but watertight" visible without pretending it is a geometry failure.

### 3. Medium - "Crash safety net removed" is a real warning, but EP crashes are not a safety net worth preserving

Evidence:
- sm21 showed Sonnet's faithful but jittered geometry can segfault EnergyPlus, while DeepSeek's worse geometry can complete (`recognition_modeling_capability.md` lines 47-65).
- The current validator was explicitly added because EnergyPlus may fail late or silently pass wrong physics (`interzone.py` lines 3-13).
- Section 8.1 says the faithful leg retains "错几何仍可能 EP 段错 = 有用信号" while re-topology removes that signal (`recognition_modeling_capability.md` lines 141-147).

Risk:
The warning is correct: watertight generated geometry can make bad interpretation harder to notice. But treating crashes as useful safety signals invites the wrong operating model. A segfault or fatal is sparse, late, nondiagnostic, and only catches some geometry errors.

Recommended action:
Rephrase as: re-topology removes accidental crash signals, so it must add intentional semantic validation. Required gates should include C-class residuals, source evidence coverage, `corrections[]`, unsupported-feature flags, and golden-case geometric diffs. Do not value EP instability itself.

### 4. Medium - Cost is probably under-estimated unless the first deliverable is a narrow typed geometry artifact

Evidence:
- The proposal says the main cost is coordination rather than code, and the kernel code is not large when built on shapely + idfpy (`geometry_first_zonification.md` lines 146-159).
- Current `surface_agent` does more than CRUD: it consumes `zone_specs` and `surface_specs`, maps z ranges, resolves construction names, chooses OBCs, writes vertices, and sets reciprocal references (`surface.py` lines 10-88 and 103-117).
- `surface_converter.py` is indeed thin and only writes objects after per-zone schema validation (`surface_converter.py` lines 13-64), so replacing the LLM means replacing behavior currently hidden in prompt reasoning.

Risk:
The hard parts are not just polygon booleans. They include polygonization from imperfect axes, tolerance clustering, holes, non-orthogonal edges, minimum-surface policy, parent-wall selection for windows, construction assignment, naming stability, diagnostics, and proving parity with the current path.

Recommended action:
Do not start with a full surface-node replacement. First build a sidecar artifact:

- `resolved_geometry.json`: stories, footprints, zones, openings/windows, intended adjacencies, voids, corrections, conflicts.
- A verifier that checks planar partition, min width/area, source residuals, and expected adjacency coverage.
- A renderer/diff tool for sm20/sm21/sm22.

Only after this artifact is stable should the deterministic surface generator replace the LLM path behind a flag.

### 5. Medium - Landing everything at "idfpy + B5" is good for the full switch, but too late for schema and verifier work

Evidence:
- The proposed timing ties the geometry-first kernel to idfpy and B5 non-rectangular work (`geometry_first_zonification.md` lines 177-186).
- idfpy migration itself has unresolved parser/version/dependency decisions (`idfpy_embed.md` lines 22-44).
- Current phase2 already asserts per-floor coverage and shared-footprint assumptions in prose (`phase2/rules.md` lines 77-80 and 126-139), but there is no typed artifact to test.

Risk:
If schema and verifier design waits for idfpy+B5, three risks collide at once: new IDF backend, new geometry kernel, and new non-rectangular cases. That makes regressions hard to attribute.

Recommended action:
Split timing:

- Now / before B5: define `resolved_geometry.json`, add shapely as a dev/runtime dependency if acceptable, and run non-blocking coverage/partition reports on existing rectangular cases.
- B5 start: turn the verifier into a blocking gate for unsupported geometry and non-rectangular footprints.
- idfpy switch: swap IO/schema plumbing and use idfpy mixins where helpful.
- After B5 evidence: replace the surface LLM with deterministic generation under a feature flag.

### 6. Medium - Existing technology should be spiked before committing to self-written matching

Evidence:
- The proposal references OpenStudio intersect/match as the conceptual target but leans toward self-writing under idfpy (`geometry_first_zonification.md` lines 82-83 and 186).
- OpenStudio has long-standing APIs for intersection/matching concepts; the OpenStudio SDK exposes `matchSurfaces` and `intersectSurfaces` behavior in its model geometry layer.
- Shapely is a strong fit for planar set operations; its manual documents set-theoretic operations such as intersection, union, difference, and symmetric difference.

Risk:
Self-writing may still be right, but the decision should be evidence-based. OpenStudio SDK may be too heavy, hard to embed, or mismatched with idfpy; but it may also solve enough intersection/matching edge cases to be a better oracle or test reference.

Recommended action:
Add a one-day spike before implementation:

- feed two known sm20/sm21 geometry cases into OpenStudio SDK `intersect/match` and compare generated surfaces;
- test whether FloorspaceJS / Dragonfly-style perimeter-core zoning gives useful baselines for re-topology;
- use Shapely for the project-owned intermediate validation regardless of whether OpenStudio is adopted.

External references checked:
- OpenStudio SDK documentation: https://openstudio-sdk-documentation.s3.amazonaws.com/
- OpenStudio SDK source/documentation pages for surface matching/intersection concepts: https://github.com/NREL/OpenStudio
- Shapely manual, set-theoretic operations: https://shapely.readthedocs.io/en/stable/manual.html
- Ladybug Tools Dragonfly documentation for district/building energy model workflows: https://www.ladybug.tools/dragonfly.html

### 7. Low - 2D-first is the right default, but "exception" schema should be designed before edge cases arrive

Evidence:
- The proposal chooses 2D per-story partitions as the normative layer, with vertical phenomena as exceptions (`geometry_first_zonification.md` lines 103-114).
- Current rules already mark atria/voids/setbacks unsupported instead of fabricating them (`phase2/rules.md` lines 132-139).

Risk:
If exceptions remain prose until B6, the first atrium or sloped roof case will force schema churn across phase2, verifier, renderer, and kernel all at once.

Recommended action:
Keep 2D-first, but reserve fields now:

- `voids[]` and `holes[]` per story;
- `vertical_merge_groups[]` for open-to-below / multi-story zones;
- `roof_planes[]` for non-horizontal top faces;
- `unsupported_features[]` with exact source evidence and reason.

They can be mostly empty in rectangular cases.

## Review of Requested Focus Areas

1. **A/B decomposition**: Mostly valid, but add C = BEM abstraction fidelity. Geometry, perception arbitration, and simulation abstraction are distinct.
2. **Coverage as construction invariant**: Correct only after typed void/roof/slab/vertical-feature semantics exist. Planar partition alone is not enough.
3. **Crash safety net removal**: Real risk, but EP crashes are accidental signals. Replace them with intentional semantic validation.
4. **2D per-story vs direct 3D**: 2D-first is the right normative layer for this project. Design exception schema now.
5. **idfpy assessment**: Accurate in spirit. idfpy helps schema/cross-reference/geometry access; it does not solve polygon coverage or intended adjacency.
6. **Two legs vs one leg**: Two legs are justified. They should converge through a shared typed geometry artifact and shared evaluators.
7. **Contract / ownership cost**: Correct that coordination is the main program risk, but implementation cost is higher than "small" unless sliced through sidecar artifacts first.
8. **Landing time**: Full replacement can wait for B5/idfpy; schema + verifier should start earlier.
9. **Existing tech**: Do not adopt blindly, but spike OpenStudio intersect/match and use Shapely for owned planar validation.

## Omitted Failure Modes To Track

- Zone merging changes load distribution even when total area is conserved.
- Window redistribution across merged perimeter zones can preserve total WWR but lose solar orientation timing.
- Shafts/stairs/elevators can be small, vertical, and semantically important; re-topology may erase them as "noise."
- Thin-but-real spaces may be rejected by min-width gates unless the schema can mark them as service/shaft exceptions.
- Non-orthogonal or rotated footprints will expose assumptions hidden by x/y range prose.
- Internal mass / adiabatic partition treatment can change results after room-to-zone aggregation.

## Priority Recommendation

1. Define `resolved_geometry.json` and `corrections[]` / `conflicts[]` schema now.
2. Add a Shapely-backed non-blocking verifier for existing rectangular cases.
3. Add C-class BEM fidelity metrics to both legs.
4. Run a short OpenStudio SDK spike as an oracle / comparison, not as a committed dependency.
5. Keep the deterministic surface generator behind a feature flag until B5 has at least one successful non-rectangular anchor.

No code changes requested from this review.
