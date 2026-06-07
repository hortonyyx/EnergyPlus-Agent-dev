# A0 — Correction contract (tolerances, evidence, audit, validation)

The shared contract every correction document (`A1`–`A4`) consumes and writes
against. A0 defines: the evidence model, the audit event taxonomy and schemas,
the tolerance registry, method profiles, the upstream input contract, and the
validation schema. A0 holds no transform rules of its own.

```
Consumes:        nothing (contract only)
Produces:        the schemas + named constants the other docs reference
Emit corrections[] when: n/a (A0 defines the schema; A1–A4 emit)
Emit conflicts[] / unsupported when: n/a
May change topology: no
```

---

## 1. Evidence model

Every primitive entering the correction layer is a typed **evidence item**, not
a bare number. Authority is resolved **per claim type**, not by one global ladder.

### 1.1 Evidence item schema

```
id               unique id
claim_type       numeric | topology_identity | semantic   (see §1.4)
grade            see §1.2
confidence       high | medium | low   (decoupled from grade)
source_kind      dimension | stroke | label | facade_window | self_check | inferred
source_ids[]     perception ids backing this item (compound for a dim chain)
floor_id
entity_id        the primitive it describes (axis / vertex / cell / window / ...)
coordinate_frame world | facade_local | plan_local
unit             m | mm | ratio | none
span             optional source bbox / extent
```

### 1.2 Evidence grades (authority, high → low)

| grade | meaning |
|---|---|
| `direct_measurement` | a value explicitly dimensioned/labelled and read directly |
| `transcribed_dimension` | derived by accumulating a dimension chain |
| `estimated_stroke` | a coordinate read off a drawn stroke, not separately dimensioned |
| `inferred_topology` | implied by enclosure/adjacency (e.g. a shared wall is one line) |
| `prior` | a commonsense/standard value from `A4`, fallback only |
| `unknown` | absent; must be completed (A3) or flagged |

Grade ranking is **claim-type-scoped** (§1.4): `inferred_topology` outranks
`estimated_stroke` for identity claims, but not for coordinate claims.

### 1.3 Confidence

`confidence ∈ {high, medium, low}`, independent of grade (a
`transcribed_dimension` can be low confidence if a chain segment was occluded).

### 1.4 Claim types and per-claim authority ladders

| claim_type | the question | authority ladder (high → low) |
|---|---|---|
| `numeric` | "what is this coordinate / length?" | `direct_measurement` > `transcribed_dimension` > `estimated_stroke` > `prior` |
| `topology_identity` | "are these the same intended wall/axis? does this cell close? is this a shared boundary?" | direct annotation / dimensioned boundary > `inferred_topology` (consistent enclosure/adjacency) > `estimated_stroke` (coordinate proximity) > `prior` |
| `semantic` | "what is this space / role?" | label / OCR > repeated layout pattern > `prior` |

Within a ladder, confidence is the tie-breaker. A genuine in-grade, in-confidence
tie is **not** silently split — it becomes a `conflict`. In particular, A2 must
**not** merge two axes on coordinate proximity alone (a `numeric` argument) when
`topology_identity` evidence says they are distinct.

---

## 2. Audit taxonomy

Four mutually exclusive event kinds. Only the last three are reportable.

| kind | definition | logged? |
|---|---|---|
| `normalization` | formatting / final-coordinate rounding within `OUTPUT_PRECISION`; no change to source value, topology, or authority | no |
| `correction` | changed a source value, closed a gap, snapped an axis, chose one evidence channel over another, or invoked a prior | **yes — `corrections[]`** |
| `conflict` | unresolved or over-threshold ambiguity | **yes — `conflicts[]`** |
| `unsupported` | cannot be safely corrected under the current regime | **yes — `unsupported[]`** |

### 2.1 Hard logging rule

If a transformation changes geometry beyond `OUTPUT_PRECISION`, changes topology,
changes evidence authority, or invokes a prior, it **must** produce a
`corrections[]` entry with `source_ids` + `rule_id`. If it cannot be logged that
way, emit `unsupported` instead of proceeding silently.

### 2.2 Audit envelope (every entry carries)

```
id
stage            A1 | A2-detect | A3-resolve | A2-apply
method_profile   room_identity | use_grouped_rooms | perimeter_core
entity_type      axis | vertex | edge | cell | surface | window | zone_input
entity_id
floor_id
parent_id        optional
coordinate_frame world | facade_local | plan_local
unit
```

### 2.3 `corrections[]` entry (envelope +)

```
rule_id
claim_type
conflict_type       one of §3, or null for a plain regularization
source_ids[]
original_value
resolved_value
value_type          scalar | point | line | polygon | ratio | area | facade_extent
tolerance_name      a name from §4
tolerance_value     the applied numeric value + unit
delta               resolved − original
evidence_grade      the grade chosen as authoritative
confidence_before
confidence_after
changes_topology    bool
prior_id            set only if a prior was invoked (else null)
note
```

### 2.4 `conflicts[]` entry (envelope +)

```
conflict_type       one of §3
claim_type
candidates[]        each: {value, source_ids[], evidence_grade, confidence}
reason_unresolved
fallback_action     what was emitted instead (kept stroke / marked unsupported / ...)
```

### 2.5 `unsupported[]` entry (envelope +)

```
reason
regime_assumption_violated   which baseline assumption broke (§6)
```

---

## 3. Conflict types

```
stroke_vs_dimension            stroke coordinate disagrees with its dimension chain (numeric)
cross_floor_axis_jitter        same intended axis differs across floors by a numeric amount (numeric)
checksum_failure               inner segments do not sum to the outer total
facade_plan_mismatch           an elevation and the plan disagree on a position/extent
semantic_size_prior            a measured size is implausible vs a prior, with a semantic label in play
unsupported_geometry           a feature outside the current regime (§6)
reference_or_identity_ambiguity "what object is this?" — frame/origin/local-to-world conflict,
                               unknown wall side or missing thickness for centerline conversion,
                               same-vs-different wall/axis where proximity and topology/semantic
                               evidence disagree (the higher-level type; cross_floor_axis_jitter
                               is its numeric subtype)
```

---

## 4. Tolerance registry

Named constants the other documents reference **by name**. Coordinates use an
**absolute grid**; areas and ratios use **relative error** — never mix. A rule
may consume a constant only if its `status` is `calibrated` or
`provisional`(with basis); a `disabled` constant forces the consuming path to
emit `unsupported`.

| name | value | unit | status | profiles | hard/warn | basis |
|---|---|---|---|---|---|---|
| `OUTPUT_PRECISION` | 10 | mm | calibrated | all | format | M/10 submodule (`GB/T 50002-2013` 3.1.2) |
| `SNAP_GRID` | 50 | mm | calibrated | all | transform | M/2 submodule (`GB/T 50002-2013`); matches partition-thickness granularity |
| `MIN_EDGE_LENGTH` | 0.10 | m | calibrated | all | hard_fail | EP very-small-vertex warning (~0.01 m) + sliver safety gate; below → merge/re-snap/unsupported |
| `DIMCHAIN_CLOSE_TOL` | 10 | mm | calibrated | all | close / conflict | `\|Σsegments − total\|`; = M/10 |
| `GAP_CLOSE_THRESHOLD` | ≤100 | mm | calibrated | all | auto-close w/ evidence | wall-thickness series (`GB/T 50002-2013` 4.3.2) |
| `GAP_CONFLICT_BAND` | 100–300 | mm | calibrated | all | escalate → A3 | inner-face vs centerline/exterior-face ambiguity |
| `GAP_UNSUPPORTED` | ≥500 | mm | calibrated | all | unsupported / A3 | too large for wall noise; likely real void or source error |
| `AXIS_JITTER_TOL` | 50 | mm | calibrated | all | same-axis only with identity evidence | = `SNAP_GRID`; beyond, or if topology says distinct → `reference_or_identity_ambiguity` → A3 |
| `AREA_REL_TOL` | ±5 | % | calibrated | all | warn / accept | BEM QA; `GB 50189-2015` 3.4.3 |
| `WWR_REL_TOL` | ±5% or ±0.02 | ratio | calibrated | all | warn / accept | `GB 50189-2015` 3.2.2 / 3.3.1 |
| `PERIMETER_DEPTH` | 4.6 (range 2.4–6.1) | m | calibrated | — (downstream zoning, **not** PartA) | n/a | `ASHRAE 90.1-2019 Add. ag`; listed for reference, PartA rules must not consume it |

Architectural-commonsense priors (door/window/room/height values) live in `A4`,
not here; they are advisory (`prior_score` / `warning`), never executable
tolerances.

---

## 5. Method profiles

Correction strictness depends on the downstream zoning target. Each rule in
`A1`–`A4` states the profiles it applies under and how strict it is.
`A1`/`A2` apply under **all** profiles.

| profile | must be strict | may relax | A3 / A4 posture |
|---|---|---|---|
| `room_identity` | every internal wall (each room boundary becomes a thermal boundary); full geometry fidelity | very little | **full strength** on every internal boundary |
| `use_grouped_rooms` | room-cell closure + adjacency graph + use/schedule/load/HVAC labels + exception spaces (shafts, stairs, toilets, equipment, high-load) | exact wall thickness, tiny offsets | **semantic-grouping and closure heavy**; wall-thickness precision relaxed |
| `perimeter_core` | exterior footprint, facade orientation, floor heights, roof/ground exposure, facade window area / WWR | internal partition coordinates, except declared void/shaft/high-load exceptions and room attribution | **conservative**; envelope/facade/window first, internal arbitration only for exceptions |

---

## 6. Upstream input contract (perception)

For correction to be safe, perception input should:

- not emit estimated coordinates indistinguishable from measured strokes;
- carry structured provenance + confidence for strokes, dimension chains, labels,
  facade windows, and self-check notes;
- link estimated geometry to the dimension ids / inference rule that produced it.

### 6.1 Provenance mode and coverage

```
provenance_mode      full | partial | legacy
provenance_coverage  per evidence class {dimensions, strokes, labels, facades, windows}
```

`legacy` (no provenance) input may still run, but affected items are downgraded
to `estimated_stroke` / `unknown`, their confidence lowered, and more
`conflicts[]` emitted. Low-provenance input must not become high-confidence
output.

### 6.2 Profile-specific stop conditions

- `room_identity`: fail / mark `unsupported` when internal-wall provenance is too sparse.
- `use_grouped_rooms`: fail / mark `unsupported` when room-cell closure or labels are too sparse.
- `perimeter_core`: may continue if exterior footprint, floor height, facade orientation, and window/WWR evidence meet minimum coverage.

---

## 7. Validation schema

After correction, the layer emits a validation block (the gate after
`A2-apply`). Targets are **PartA artifacts**, not the downstream thermal-zone
artifact.

```
status                      pass | pass_with_warnings | fail   (top-level)

floor_footprint_coverage    corrected floor boundary is a valid, closed polygon
room_cell_coverage          (room_identity / use_grouped_rooms only) cells tile the footprint,
                            no overlap, no undeclared hole
facade_segment_coverage     exterior boundary attributed; every segment has an orientation
window_anchor_validation    each window ∈ its parent facade/surface; WWR attribution present
thermal_zone_coverage       RESERVED — produced by the later zonification step, not validated here
```

Additional hard checks:

```
no_invalid_polygons         no self-intersecting / zero-area polygons
inside_footprint            no geometry outside the declared footprint
min_edge_satisfied          no edge < MIN_EDGE_LENGTH
checksums_passed            all dimension chains within DIMCHAIN_CLOSE_TOL
id_uniqueness               no duplicate / missing entity ids
attribution_complete        every source item is mapped, fractionally attributed, or unsupported
z_stack_consistent          floor heights / z-stack coherent (lower ceiling z == upper floor z)
```

Soft (relative-tolerance) checks: `facade_area_residuals`, `wwr_residuals`
(within `WWR_REL_TOL`), area residuals (within `AREA_REL_TOL`),
`unsupported_count_by_severity`.

### 7.1 Fail / continue policy

- **fail**: any hard check fails (invalid polygon, overlap, undeclared hole,
  sub-`MIN_EDGE_LENGTH` edge, failed containment, outside-footprint, id clash,
  failed checksum that A3 could not resolve, broken z-stack).
- **pass_with_warnings**: hard checks pass; residuals within their relative
  tolerances; `unsupported` items present but profile stop conditions met.
- **pass**: hard checks pass and no warnings.

Anything that could not be corrected is carried as `unsupported`, never silently
normalized away.
