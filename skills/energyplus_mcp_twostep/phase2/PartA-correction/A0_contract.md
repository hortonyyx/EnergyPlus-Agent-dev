# A0 — Correction contract (tolerances, evidence, audit, validation)

The shared contract every correction document (`A1`–`A4`) consumes and writes
against. A0 defines: the evidence model, the audit event taxonomy and schemas,
tolerance classes, method profiles, the upstream input contract, and the
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

Every geometric primitive entering the correction layer is a typed **evidence
item**, not a bare number.

### 1.1 Evidence grades (authority, high → low)

| grade | meaning |
|---|---|
| `direct_measurement` | a value explicitly dimensioned/labelled in the source and read directly |
| `transcribed_dimension` | derived by accumulating a dimension chain (sum of segments) |
| `estimated_stroke` | a coordinate read off a drawn stroke whose true value is not separately dimensioned |
| `inferred_topology` | implied by enclosure/adjacency, not measured (e.g. a shared wall must be one line) |
| `prior` | a commonsense/standard value from `A4`, used only as fallback |
| `unknown` | absent; must be completed or flagged |

### 1.2 Confidence

Each evidence item carries `confidence ∈ {high, medium, low}`. Grade and
confidence are independent (a `transcribed_dimension` may be low confidence if a
segment in its chain was occluded).

### 1.3 Data-priority ladder

When two evidence items describe the same quantity and disagree beyond the
relevant tolerance, authority is resolved by:

```
consistent measurement  >  dimension-chain derived  >  stroke estimate  >  prior
```

with confidence as the tie-breaker within a grade. A genuine, in-grade,
in-confidence tie is **not** silently split — it becomes a `conflict`.

---

## 2. Audit event taxonomy

Four mutually exclusive event kinds. Only the last three are reportable; the
first is silent.

| kind | definition | logged? |
|---|---|---|
| `normalization` | formatting / final-coordinate rounding within output precision; no change to source value, topology, authority | no |
| `correction` | changed a source value, closed a gap, snapped an axis, selected one evidence channel over another, or invoked a prior | **yes — `corrections[]`** |
| `conflict` | unresolved or over-threshold ambiguity | **yes — `conflicts[]`** |
| `unsupported` | cannot be safely corrected under the current regime | **yes — `unsupported[]`** |

### 2.1 Hard logging rule

If a transformation changes geometry beyond output rounding, changes topology,
changes evidence authority, or invokes a prior, it **must** produce a
`corrections[]` entry carrying `source_ids` + `rule_id`. If it cannot be logged
that way, the producing document must emit `unsupported` instead of proceeding
silently.

### 2.2 `corrections[]` entry

```
id                 unique id
target             geometric entity changed (axis / vertex / surface / window / zone)
rule_id            the A1/A2/A3 rule that fired
conflict_type      one of §3 (or null if a plain regularization)
source_ids[]       perception ids the decision rests on
original_value
resolved_value
threshold          the tolerance constant applied
delta              resolved − original
evidence_grade     the grade chosen as authoritative
confidence_before
confidence_after
changes_topology   bool
prior_id           set only if a prior was invoked (else null)
note
```

### 2.3 `conflicts[]` entry

```
id
conflict_type        one of §3
target
candidates[]         each: {value, source_id, evidence_grade, confidence}
reason_unresolved
fallback_action      what was emitted instead (e.g. kept stroke, marked unsupported)
```

### 2.4 `unsupported[]` entry

```
id
target
reason
regime_assumption_violated   which baseline assumption broke (see §5)
```

---

## 3. Conflict types

```
stroke_vs_dimension      stroke coordinate disagrees with its dimension chain
cross_floor_axis_jitter  the same intended wall/axis differs across floors
checksum_failure         inner dimension segments do not sum to the outer total
facade_plan_mismatch     an elevation and the plan disagree on a position/extent
semantic_size_prior      a measured size is implausible against a prior, with a semantic label in play
unsupported_geometry     a feature outside the current regime (§5)
```

---

## 4. Tolerance classes

Named constants the other documents reference by name. Coordinates use an
**absolute grid**; areas and ratios use **relative error** — never mix the two.

| name | purpose | value |
|---|---|---|
| `SNAP_GRID` | coordinate quantization grid | 50 mm *(provisional, pending calibration)* |
| `MIN_EDGE_LENGTH` | degenerate-sliver floor; pieces below this are rejected/absorbed | 0.10 m *(provisional, pending calibration)* |
| `GAP_CLOSE_THRESHOLD` | gaps narrower than this are closed, not preserved | *(pending)* |
| `AXIS_JITTER_TOL` | max cross-floor offset still treated as the same intended axis | *(pending; small, ≤ SNAP_GRID order)* |
| `AREA_REL_TOL` | relative tolerance for area checks | ±5% |
| `WWR_REL_TOL` | relative tolerance for WWR checks | ±5% |
| `DIMCHAIN_CLOSE_TOL` | max `\|sum(segments) − total\|` accepted before closure/conflict | ≤ 0.01 m |
| `PERIMETER_DEPTH` | reference depth for downstream perimeter zoning | 4.6 m (15 ft) *(provisional, pending confirmation)* |

Values marked *provisional/pending* are calibrated from external authority
before the deterministic documents are finalized.

---

## 5. Method profiles

Correction strictness depends on the downstream zoning target. Each rule in
`A1`–`A4` states the profiles it applies under and how strict it is.

| profile | what must be strict | what may relax |
|---|---|---|
| `room_identity` | every internal wall (each room boundary becomes a thermal boundary); full strictness | very little |
| `use_grouped_rooms` | room-cell closure + adjacency graph + labels | exact wall thickness, tiny drawing offsets |
| `perimeter_core` | exterior footprint, facade orientation, floor heights, roof/ground exposure, facade window area / WWR | internal partition coordinates, except void/shaft/high-load exceptions and room attribution |

`A3`/`A4` are invoked **conservatively** under `perimeter_core` and may run with
full force only under `room_identity`. `A1`/`A2` apply under all profiles.

---

## 6. Upstream input contract (perception)

For correction to be safe, perception input must:

- not emit estimated coordinates indistinguishable from measured strokes;
- carry structured provenance + confidence for strokes, dimension chains, labels,
  facade windows, and self-check notes;
- link estimated geometry to the dimension ids / inference rule that produced it.

**Degradation.** The layer may still run on perception JSON that lacks
provenance, but it must downgrade affected items to `estimated_stroke` /
`unknown`, lower their confidence, and consequently emit more `conflicts[]`.

---

## 7. Validation schema

After correction, the layer emits a validation block (the gate that follows
`A2-apply` in the runtime):

```
coverage_residual          union(zones) vs floor footprint
overlap_area               pairwise zone overlap
undeclared_hole_area       footprint − union, beyond declared voids
min_edge_satisfied         no edge < MIN_EDGE_LENGTH
checksums_passed           all dimension chains within DIMCHAIN_CLOSE_TOL
containment_ok             every window ∈ its parent surface
facade_area_residuals      per facade
wwr_residuals              per facade / floor, within WWR_REL_TOL
unsupported_flags          carried from §2.4
```

**Fail / continue policy.** A hard geometric defect (overlap, undeclared hole,
sub-`MIN_EDGE_LENGTH` edge, failed containment) fails the gate. Residuals within
their declared relative tolerances pass. Anything that could not be corrected is
carried as `unsupported`, not silently normalized away.
