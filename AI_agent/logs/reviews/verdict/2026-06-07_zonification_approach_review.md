# Plane-First Zonification Approach Research Review

Date: 2026-06-07
Reviewer: Codex
Scope: Research review for `AI_agent/logs/review/request/2026-06-07_zonification_approach_request.md`. This is not a code review; no implementation, prompt contract change, or `IntakeOutput` change is requested here.

## Verdict

Accepted, with two important refinements.

The request's core hypothesis is right: **"algorithm vs LLM" is the wrong split; "deterministic planar geometry vs semantic / policy judgment" is the right split**. Geometry should own zone footprint construction, polygon coverage, overlap / gap detection, perimeter-depth slicing, facade orientation buckets, and validation. LLMs or rules should own room-use interpretation, exception handling, grouping policy, and user-facing tradeoff explanation.

My recommended route is an adjustable zonification spectrum, not a single paradigm:

1. `perimeter_core` - first MVP for the heat-zone re-topology leg. It is closest to ASHRAE / BEM practice, needs the least internal-wall precision, and gives the most robust EP-ready abstraction.
2. `use_grouped_rooms` - second mode. It keeps real room cells but groups adjacent cells by use / schedule / load / HVAC / exposure. It is more faithful, but it needs closed room-cell topology and better phase1 semantics.
3. `room_identity` - faithful-modeling baseline. It is mostly outside this request, but should remain the comparison endpoint of the same granularity spectrum.

The practical implementation seam should be a sidecar `zonification_output.json`, not a change to the current `IntakeOutput` contract. Keep source `room_cells` separate from output `thermal_zones`; in `perimeter_core`, a thermal zone may cut across rooms, so attribution is fractional by area rather than whole-room membership.

## Findings

### 1. High - Start with `perimeter_core`, but design the API as a zoning spectrum

Evidence:
- Current phase2 rules explicitly default to "every enclosed room is its own thermal zone" and mark perimeter/core or merge-by-use as a future step (`skills/energyplus_mcp_twostep/phase2/rules.md` Step 3).
- ASHRAE 90.1 Appendix G-style rules distinguish perimeter from interior regions and split perimeter regions by glazed facade orientation.
- The simplified 90.1-2019 addendum route models each floor as either one block or five blocks, with four perimeter zones and one core zone, and exposes perimeter depth as an input range.
- LBNL's UBEM zoning-method study reports materially different loads and capacities between one-zone, auto-zoned perimeter/core, and prototype methods, so zone granularity is a modeling decision, not a harmless implementation detail.

Risk:
If the project picks only `perimeter_core`, it will be robust but may erase semantically important small spaces such as shafts, equipment rooms, stairs, or schedule-distinct rooms. If it picks only `use_grouped_rooms`, it gives up much of the correction-precision benefit that made re-topology attractive.

Recommended action:
Make `method` a first-class parameter:

- `perimeter_core`: default for "robust BEM abstraction / early design / noisy drawing".
- `use_grouped_rooms`: use when phase1 has reliable room cells and labels.
- `room_identity`: faithful baseline / comparison leg.

Treat the user's chosen method and perimeter depth as reviewable inputs, rendered before downstream geometry modeling.

### 2. High - Deterministic geometry should own the planar partition; a simple inward buffer is not enough

Evidence:
- Shapely can compute negative buffers, polygon unions, polygonization from linework, and coverage validity, which are exactly the primitives needed for project-owned planar validation.
- OpenStudio Standards exposes core/perimeter polygon creation examples, including a default 15 ft perimeter depth, but those examples are primarily a reference for BEM convention rather than a drop-in arbitrary-floorplan solver.
- Autozoner literature argues that robust core/perimeter subdivision for arbitrary massing is better understood as a straight-skeleton / topological polygon-subdivision problem, because simple offsets fail on concave and complex shapes.

Risk:
For rectangles, "inner offset + facade strips + core" works. For L-shapes, courtyards, narrow wings, concave corners, or collapsing tips, a naive negative buffer can create empty cores, multi-part cores, slivers, or perimeter regions with ambiguous orientation. If the model silently normalizes those shapes, the heat-zone leg will produce clean but physically misleading BEMs.

Recommended action:
For MVP:

- Allow simple rectangles and simple orthogonal L/U shapes only when the deterministic coverage verifier passes.
- Use Shapely to construct and validate the planar coverage.
- Borrow Autozoner / straight-skeleton logic for general concave footprints, or gate those cases as unsupported until a robust algorithm is implemented.
- Keep OpenStudio/openstudio-standards as an oracle / reference implementation for comparison, not as the first hard dependency.

### 3. High - Separate source room cells from output thermal zones

Evidence:
- OpenStudio distinguishes spaces from thermal zones: a thermal zone can contain one or more spaces, and loads / ventilation can be aggregated.
- `perimeter_core` boundaries normally do not follow real walls; they may split a large room between perimeter and core regions.
- `use_grouped_rooms` boundaries do follow room cells, but still merge cells into fewer thermal zones.

Risk:
If the schema stores only final thermal zones, the pipeline cannot explain what original rooms were erased, split, or merged. If it stores only room membership, `perimeter_core` cannot represent boundaries that cut across rooms.

Recommended action:
Use both:

- `source_room_cells[]`: phase1 / reconciliation output, with room label, polygon, confidence, exterior exposure, and source evidence.
- `thermal_zones[]`: BEM zones, with polygon, semantic mix, load aggregation policy, and either whole-room membership or fractional room-area attribution.

For `perimeter_core`, expect `room_area_attribution[]` rather than exact room membership. For `use_grouped_rooms`, require whole-room membership unless a room is explicitly split.

### 4. Medium - LLM should classify and explain grouping, not draw the polygons

Evidence:
- The current phase2 failures are mostly geometry-heartbeat failures: coordinate drift, split enumeration, and parent/adjacent surface reasoning.
- The semantic grouping problem is different: labels, use, schedules, loads, HVAC service, and exception spaces are natural-language / building-commonsense inputs.

Risk:
Letting an LLM directly output perimeter/core polygons recreates the geometry mind-game the re-topology leg is trying to escape. Conversely, a purely geometric algorithm will merge a WC, equipment room, stair, or high-load room into an office block unless semantic exceptions are explicit.

Recommended action:
Use a hybrid:

- Deterministic code builds candidate partitions and validates coverage.
- Rules group by hard metadata where available: use type, schedule, load density, HVAC/system, exterior orientation, roof/ground exposure.
- LLM fills missing semantic labels, flags exceptions, and explains why a zone should deviate from the default.
- A deterministic verifier checks that every source room is either mapped, fractionally attributed, or explicitly declared ignored / unsupported.

### 5. Medium - The granularity knob needs BEM-fidelity metrics, not just EP completion

Evidence:
- The LBNL zoning-method comparison shows that zoning choices alter loads, capacities, and source energy.
- The internal project has already learned that EnergyPlus completion is not a correctness oracle.

Risk:
A five-zone model may be perfectly watertight and still wrong for the user's purpose if it erases major schedule differences or redistributes facade windows poorly. This will pass geometry gates.

Recommended action:
Track BEM abstraction residuals for every method:

- floor area by floor;
- exterior wall area by facade;
- roof / ground-contact area;
- WWR and window area by facade and floor;
- source room to thermal zone mapping or fractional attribution;
- semantic mix per thermal zone;
- zone count and chosen method.

Acceptance should include "BEM fidelity within declared residuals", not only "polygon coverage passes" and "EP runs".

### 6. Medium - OpenStudio is valuable as reference / oracle; Shapely is the better first project-owned integration

Evidence:
- OpenStudio has mature BEM concepts, measures, space/thermal-zone abstractions, and surface intersection/matching concepts.
- OpenStudio SDK / CLI is a heavier dependency and would introduce model-format and deployment integration costs.
- Shapely is already a close fit for the requested planar 2D operation: polygonize linework, union zones, difference against footprint, and validate polygonal coverage.

Risk:
Adopting OpenStudio immediately could entangle zonification with the separate downstream切配 / surface-generation track. Rejecting it completely would waste a mature source of BEM conventions and test oracles.

Recommended action:
Use Shapely for the owned sidecar verifier and partition generator. Run a short OpenStudio/openstudio-standards spike as:

- a reference for rectangle / bar perimeter-core behavior;
- a source of comparison outputs;
- a future candidate if the project later wants OpenStudio SDK integration.

Do not make OpenStudio a required dependency for the first reviewable `zonification_output.json` artifact.

## Direct Answers To The 8 Requested Questions

### 1. Paradigm Choice

Recommendation: **use a tunable spectrum with `perimeter_core` as the first heat-zone MVP and `use_grouped_rooms` as the next mode**.

`perimeter_core` is best aligned with the re-topology leg's purpose: robust BEM abstraction from noisy real drawings. It needs reliable exterior footprint, floor height, facade orientation, and window/WWR evidence; it does not need every internal wall to be corrected to high precision.

`use_grouped_rooms` is the right second mode when phase1 already produced reliable closed room cells and labels. It preserves more architectural intent, but it no longer gets the full "ignore noisy internal wall geometry" benefit.

`room_identity` remains the faithful leg and should be preserved as the baseline / comparison endpoint, not folded into the heat-zone MVP.

### 2. Geometry Partition Algorithm

For project-owned MVP, prefer Shapely:

- build footprint polygons;
- generate perimeter strips and core regions;
- split perimeter regions by facade orientation;
- validate coverage with union / difference / overlap checks;
- render and diff outputs.

For simple rectangular floors, the algorithm can be:

1. Normalize footprint and facade segments.
2. Choose `perimeter_depth_m` (default 4.6 m / 15 ft; allow user override).
3. Compute core by inward offset.
4. Compute perimeter as `footprint - core`.
5. Assign perimeter pieces to N/E/S/W facade buckets.
6. Validate zone polygons as a coverage.

For concave / courtyard / non-orthogonal floors, simple offset is not enough. Either borrow Autozoner / straight-skeleton-style cell decomposition or explicitly mark the case unsupported until the robust solver exists.

OpenStudio/openstudio-standards should be used as reference and test oracle first. It is too heavy and cross-cutting to make it the first project dependency for zonification alone.

### 3. Semantic Grouping

Use a hybrid graph-clustering approach.

Inputs:

- room cell polygon and area;
- room label / OCR text;
- inferred use type;
- schedule family;
- internal load density family;
- HVAC/system or thermostat grouping if known;
- exterior exposure and facade orientation;
- roof / ground / exposed floor flags;
- confidence / provenance.

Rules:

- Only adjacent room cells can be merged in `use_grouped_rooms`.
- Merge when use, schedule, load density, HVAC/system, and exposure are sufficiently similar.
- Keep high-impact exceptions separate: equipment rooms, stairs/shafts, toilets, lobbies, large corridors, spaces with very different schedules or loads.
- Let LLM propose classifications and exceptions, but let deterministic code execute the graph merge and verify coverage.

For `perimeter_core`, semantic grouping is not primary; semantics mainly assign load/schedule mix and flag exceptions that should override pure perimeter/core.

### 4. Partition Legality Validation

Use deterministic polygonal coverage checks:

- every polygon is valid and non-empty;
- `coverage_is_valid` or equivalent edge-matching check passes when available;
- `unary_union(thermal_zones)` equals the target floor coverage within tolerance;
- pairwise overlaps are below tolerance;
- `target_coverage - union` has no undeclared gap / hole;
- `union - target_coverage` is empty;
- minimum zone area / edge length / width thresholds pass;
- every source room is mapped or area-attributed;
- every window anchor maps to exactly one facade/perimeter zone or is explicitly unresolved.

Important distinction: Shapely's per-polygon `is_valid` is not enough. A set of individually valid polygons can still overlap or leave gaps. The artifact must validate the coverage as a collection.

### 5. Granularity Knob

Yes. The granularity should be a user-confirmed parameter.

Suggested controls:

- `method`: `perimeter_core | use_grouped_rooms | room_identity`;
- `perimeter_depth_m`: default 4.6 m, user range roughly 2.4-6.1 m for the simplified five-zone style;
- `orientation_buckets`: N/E/S/W by default, with 45-degree tolerance for near-aligned facades;
- `merge_policy`: conservative / standard / aggressive;
- `exception_policy`: keep service / circulation / high-load rooms separate vs absorb into dominant zone.

The preview should show zone polygons, original room cells, facade/window residuals, and area attribution before downstream geometry modeling. This prevents the pipeline from silently choosing a load-changing abstraction.

### 6. Correction-Precision Coupling

Approximate coupling by mode:

| Mode | Required correction precision | What can be relaxed |
|---|---|---|
| `perimeter_core` | Exterior footprint, facade orientation, floor heights, roof/ground exposure, facade window area / WWR should be within BEM residual targets, typically about 5% for area/WWR checks. Orientation bucket must be reliable enough for N/E/S/W or within the chosen 45-degree bucket. | Internal partition coordinates can be coarse or ignored unless they define major voids, shafts, high-load exceptions, or source-room attribution. |
| `use_grouped_rooms` | Room cells must close, adjacency graph must be reliable, labels/use metadata must be usable, and merged room areas should stay within declared residuals. Snapping tolerances around 50-100 mm are reasonable after reconciliation, with no sub-tolerance slivers. | Exact wall thickness and tiny drawing offsets can be normalized if topology, area, and semantic grouping are preserved. |
| `room_identity` | Highest precision: every room boundary becomes a thermal boundary. Cross-floor jitter and small offsets must be resolved before geometry modeling because they can create slivers and bad interzone surfaces. | Very little internal geometry can be ignored; errors become actual zone/surface errors. |

So the re-topology leg saves the most correction work only in `perimeter_core`: a 20-room plan can become 4-5 thermal zones using envelope/facade evidence plus broad semantic exceptions. `use_grouped_rooms` saves zone count but still depends on reliable room topology.

### 7. Intermediate Representation Schema

Use a sidecar `zonification_output.json` before touching `IntakeOutput`.

Sketch:

```json
{
  "schema_version": "zonification_output.v0",
  "method": "perimeter_core",
  "parameters": {
    "perimeter_depth_m": 4.6,
    "orientation_buckets": ["N", "E", "S", "W"],
    "orientation_tolerance_deg": 45,
    "merge_policy": "standard",
    "exception_policy": "keep_high_impact_exceptions"
  },
  "floors": [
    {
      "floor_id": "F1",
      "z_floor": 0.0,
      "ceiling_height": 3.6,
      "footprint": {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0], [0.0, 0.0]]]
      },
      "source_room_cells": [
        {
          "room_id": "F1_Room_01",
          "label": "Office",
          "use_type": "office",
          "polygon": {"type": "Polygon", "coordinates": []},
          "area_m2": 24.0,
          "exterior_orientations": ["S"],
          "confidence": "medium",
          "source_ids": ["plan_1f:S12", "plan_1f:OCR3"]
        }
      ],
      "facade_segments": [
        {
          "facade_id": "F1_South",
          "orientation": "S",
          "line": [[0.0, 0.0], [15.0, 0.0]],
          "window_area_m2": 12.96,
          "wwr": 0.24,
          "source_ids": ["south_elevation"]
        }
      ],
      "window_anchors": [
        {
          "window_id": "W_F1_S_01",
          "facade_id": "F1_South",
          "span_m": [1.2, 3.6],
          "z_range_m": [1.0, 2.8],
          "assigned_thermal_zone_id": "F1_S_Perimeter"
        }
      ],
      "thermal_zones": [
        {
          "thermal_zone_id": "F1_S_Perimeter",
          "method_role": "south_perimeter",
          "polygon": {"type": "Polygon", "coordinates": []},
          "area_m2": 45.0,
          "exterior_orientations": ["S"],
          "semantic_mix": [{"use_type": "office", "area_fraction": 0.82}],
          "source_room_attribution": [
            {"room_id": "F1_Room_01", "area_m2": 12.5, "fraction": 0.52}
          ],
          "load_aggregation_policy": "area_weighted"
        }
      ]
    }
  ],
  "validation": {
    "coverage_area_residual_m2": 0.0,
    "overlap_area_m2": 0.0,
    "undeclared_hole_area_m2": 0.0,
    "facade_area_residuals": [],
    "wwr_residuals": [],
    "unmapped_source_rooms": [],
    "unsupported_flags": []
  }
}
```

Keep this as a sidecar / intermediate artifact. Generate current downstream natural-language specs from it later, or feed it to the future geometry modeling /切配 layer once that contract exists.

### 8. Existing Solutions To Borrow

Borrow:

- ASHRAE 90.1 thermal-block logic: perimeter vs interior, orientation buckets, ground/roof separation, and 15 ft / 4.6 m perimeter depth convention.
- ASHRAE 90.1-2019 simplified block logic: one block vs five blocks per floor, perimeter depth as user input, facade-based window abstraction.
- OpenStudio's Space / ThermalZone separation: source spaces can aggregate into thermal zones.
- OpenStudio Standards geometry examples: reference behavior for rectangular / bar-style perimeter-core generation.
- Shapely coverage operations: project-owned polygonal validation and partition verification.
- Autozoner literature: robust arbitrary-footprint perimeter/core decomposition using skeleton-style topology rather than naive inward offset.
- LBNL zoning-method impact study: evidence that zoning method materially changes simulated loads/capacity, so the granularity knob needs review and metrics.

Do not borrow blindly:

- Do not import OpenStudio SDK as the first implementation dependency unless a spike shows it is worth the deployment and ownership cost.
- Do not let LLMs hand-draw final polygons.
- Do not treat EnergyPlus completion as enough validation.

## Review Of The Request's Initial Judgment

Accepted:

- "Algorithm vs LLM is not the right cut" - yes.
- "Geometry skeleton should be algorithm-led" - yes.
- "Semantic merging and exceptions belong to LLM/rules" - yes.
- "Paradigm determines the algorithm/LLM weight" - yes.
- "A pure perimeter/core mode is the most robust and least correction-hungry" - yes.

Refined:

- `perimeter_core` should be the MVP, but not the only future mode.
- "Shapely inward offset" is only the rectangle/simple-shape implementation, not the general algorithm.
- `use_grouped_rooms` should be framed as a graph clustering problem over source room cells, not as free-form LLM grouping.
- The output schema must support fractional room-to-zone attribution because perimeter/core boundaries may cut through rooms.
- Add BEM-fidelity residuals as a separate acceptance layer; geometry validity alone does not protect simulation abstraction quality.

Rejected / cautioned:

- Do not adopt OpenStudio as a hard dependency before a focused spike.
- Do not assume a legal planar partition automatically preserves semantic zoning intent.
- Do not ask phase1 to fully correct every internal wall before `perimeter_core`; that would erase the re-topology leg's main advantage.

## Suggested Delivery Sequence

1. Define `zonification_output.json` as a sidecar artifact and renderer/diff target.
2. Implement non-blocking Shapely validation reports on existing rectangular cases.
3. Implement `perimeter_core` for simple rectangles and simple orthogonal footprints with explicit unsupported flags.
4. Add user-confirmed controls: method, perimeter depth, orientation buckets, exception policy.
5. Add BEM-fidelity residuals and source-room attribution.
6. Spike OpenStudio/openstudio-standards and Autozoner-style decomposition as references for complex footprints.
7. Add `use_grouped_rooms` graph clustering once source room-cell topology and labels are reliable.

## Test And Acceptance Criteria

Golden cases:

- Simple rectangle: five-zone perimeter/core should pass exactly.
- L-shape: should either produce a valid coverage or mark unsupported with a clear reason.
- Concave / courtyard: should exercise skeleton/unsupported behavior; naive buffer-only output is not acceptable unless validated.
- Noisy 20-room office: compare `perimeter_core` vs `use_grouped_rooms` vs `room_identity` residuals.

For every case:

- `unary_union(thermal_zones) ~= footprint`;
- pairwise overlap area below tolerance;
- `footprint - union` has no undeclared area;
- every source room is mapped, fractionally attributed, or explicitly unsupported;
- exterior facade area and window area / WWR are conserved within declared residuals;
- rendered preview shows original room cells and final thermal zones;
- chosen granularity and perimeter depth are visible in the artifact.

## Sources Checked

Internal:

- `AI_agent/logs/review/request/2026-06-07_zonification_approach_request.md`
- `AI_agent/architecture/geometry_first_zonification.md`
- `AI_agent/capability/recognition_modeling_capability.md`
- `AI_agent/reference/split_pairing_kernel_reference.md`
- `AI_agent/reference/drawing_to_model_research_landscape.md`
- `skills/energyplus_mcp_twostep/phase2/rules.md`

External:

- ASHRAE 90.1 addenda thermal block rules: https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90.1-2016/90_1_2016_k_o_x_ab_ac_ad_ae_ag_ah_ak_am_20210324.pdf
- ASHRAE 90.1-2019 Addendum ag simplified five-zone block: https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_1_2019_ag_20220909.pdf
- OpenStudio Standards geometry docs: https://rubydoc.info/gems/openstudio-standards/OpenstudioStandards/Geometry
- OpenStudio thermal zones docs: https://openstudiocoalition.org/getting_started/creating_your_model/
- Shapely coverage validation: https://shapely.readthedocs.io/en/2.1.2/reference/shapely.coverage_is_valid.html
- Shapely polygonize: https://shapely.readthedocs.io/en/2.1.2/reference/shapely.polygonize.html
- Shapely buffer: https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html
- LBNL zoning-method impact study: https://eta-publications.lbl.gov/publications/impacts-building-geometry-modeling
- Autozoner DOI page: https://www.tandfonline.com/doi/abs/10.1080/19401493.2015.1006527

No code changes requested from this review.
