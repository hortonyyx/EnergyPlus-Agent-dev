# Reading-stage typed scoring: projection, capability, and totality plan

Status: **controller-ruled construction specification; construction authorized
slice-by-slice from 2026-07-31**.

Author: sol

Controller: Opus 5

Date: 2026-07-31
Authoritative brief: `AI_agent/logs/reviews/request/2026-07-31_reading_typed_scoring_brief.md`

This document is cumulative and self-contained. A later executor must not rely on an
older version of this proposal. Section 14 contains the final ruled boundaries. They
are normative construction requirements, not open questions.

## 0. Executive decision

The reading product is not, and must never again be pretended to be, a correction-v3
payload. Its recognized contract is:

```json
{"views": {"<expected_output_id>": "<ReadingView>"}}
```

The judge will add one new judge-only adapter between that artifact and the typed C2
scorer. The adapter will:

1. recognize the outer reading contract structurally, without a default schema value;
2. join view keys to the trusted `ViewManifest` and judge score bindings;
3. project plan coordinates through an explicit, hash-certified affine transform,
   counting every nonzero declared origin;
4. project elevation local-x through the existing reviewed elevation binding;
5. preserve every consumed coordinate in a normalization certificate;
6. emit a per-input, per-component applicability ledger;
7. separate measurement status from denominator disposition so product-side malformed
   geometry cannot shrink its own denominator;
8. feed only trusted-capability exclusions into denominator filtering; and
9. return a typed `not_applicable` result, never an exception or an empty false-red,
   whenever trusted inputs make all component denominators unscorable.

The two drawing channels are intentionally not treated as symmetric:

- **Elevation is an adaptation job with an explicit frame-reconciliation gate.** The reviewed local-x → world-along transform
  already exists in `ElevationScoreViewBindingV1` and
  `project_typed_elevation_observation` (brief F5). The missing step is a strict
  `ReadingView` stroke-to-observation adapter. The reviewed binding owns coordinates,
  but a product/binding disagreement on `local_x_positive` or `mirrored` makes only
  that input's elevation components NA with a two-sided witness while retaining its
  answer targets as misses. The judge never projects both ways and selects the result
  closest to GT.
- **Plan is a frame-contract job.** There is no current plan transform consumer and no
  transform in `PlanScoreViewBindingV1` (brief F6). The proposal makes the present
  metre/right-up/origin convention one explicit replaceable affine transform sourced
  from strict `scale_origin.world_x_m/world_y_m`. It never falls back to an implicit
  identity or parses `note`.

The scorer wire carries the capability ledger and certificates in strict score sidecar
schema **9**, with v8 remaining read-only/cache-miss legacy. Adding untyped
dictionaries to frozen v8 is not an acceptable fallback. Schema 9 is pure-additive for
correction judgment: correction public rows and wall criteria must be byte-identical to
their v8 baseline.

## 1. Scope, non-goals, and invariants

### 1.1 In scope

- A real `{"views": ...}` reading attempt entering typed v3 scoring from both
  `run_stage.py` and the score CLI.
- Plan wall geometry, plan window geometry, and elevation window geometry.
- Per-source and per-claim applicability, including partial plan/elevation capability.
- Coordinate-level audit rows and deterministic certificates.
- Honest top-level and partial `not_applicable` results.
- Totalization of scorer capability failures so one reading attempt cannot abort the
  grading loop or the downstream flow.
- Cache identity, rendering, and CLI/run-stage parity for the new contract.
- Preservation of the correction-v3 scorer's substantive behavior.

### 1.2 Out of scope

- Changing what gate ① accepts as a legal `ReadingView`.
- Changing the reading producer, prompt, guide, or pen vocabulary in this batch.
- Inferring room topology, window host zones, or exterior/interior labels into the
  reading product.
- Calibrating geometry from GT, fitting a transform to GT, or altering GT.
- Falling back to the legacy v2 scorer for a v3 GT (brief F4).
- Automatically accepting/rejecting `StageVerdict`; score evidence remains advisory to
  gate ②.
- Re-running sm24 to acceptance during construction. The construction acceptance is a
  live J0 passage that scores or loudly returns NA without crashing.

### 1.3 Invariants applied

1. **Geometry is deterministic code.** The adapter performs only typed parsing,
   coordinate projection, and deterministic registration. No LLM is introduced.
2. **One world frame.** Every coordinate admitted to matching is represented in the
   global building frame. Image-local coordinates remain alongside it for audit.
3. **GT is judge-only.** The adapter and matching code live below
   `src/agent/judge/`; gate ①, reading production, and ordinary execution modules do not
   import GT. `scripts/tool_scripts/run_stage.py` imports the adapter only inside the
   existing judge path.
4. **Production owns legality; judge owns measurability.** Malformed product geometry
   is recorded as unmeasurable, never called “broken” or converted into a production
   rejection. It cannot filter target denominators: those targets remain and miss.
   Trusted/frame capability failures become reasoned judge `not_applicable`.
5. **The transform seam is extensible.** The plan and vertical transforms use typed
   affine records even where the current coefficients are identity. No downstream
   matcher assumes a common footprint, one floor, axis alignment, or zero origin.
6. **Every score-affecting decision is certified.** Product bytes, manifest, bindings,
   transform preimages, normalized coordinates, source applicability, helper versions,
   and tolerances participate in strict wire hashes.
7. **Denominator eligibility is independent of every product byte.** Applicable zero
   observations, product-side unmeasurable geometry, and product/binding frame
   disagreement all leave targets in the denominator as misses. Only a cause derived
   exclusively from trusted manifest/binding/GT capability may filter, and it carries
   a stable reason and witness.

## 2. Current defect and required behavioral matrix

The current path reads top-level `segments`, `openings`, and
`elevation_observations`; a real reading attempt has only `views` (F2/F3). The runner
then supplies `"3"` for a missing top-level schema (F8), so reading passes an
unconditional capability decision (F1) and crashes at the tuple/list default in the
elevation normalizer (F9/F10).

The replacement behavior is:

| Input condition | Required outcome |
|---|---|
| Real reading envelope, at least one measurable component | `c2_scored`, with a channel applicability ledger |
| Real reading envelope, measurable component, no relevant strokes | applicable with zero observations; target rows are real misses |
| One product wall stroke is a rect | exclude only that stroke, increment `unmeasurable_observations`, retain the component and target denominator |
| Product geometry/view is malformed | explicit product-side unmeasurable status; target denominator is retained and missing evidence scores miss |
| Trusted-input-only capability makes one component unmeasurable | partial `c2_scored`; that component is NA, carries a witness, and may be filtered |
| Product/binding local-x or mirror disagreement | input elevation components NA with witness/count; targets remain and score as misses |
| Every component has trusted-input-only disposition `filter` | top-level `not_applicable/no_scorable_reading_channel` with all component reasons |
| Every component is product-side unmeasurable | component/channel NA remains visible, but payload is `c2_scored`; unchanged target denominators score as misses |
| Missing/invalid outer `views` | top-level `not_applicable/unsupported_reading_contract` |
| Trusted binding/GT/manifest identity is corrupt or mismatched | typed `rejected` judge-input result; never a product-quality verdict |
| Judge algorithm cannot resolve its own ambiguity | affected component NA with an ambiguity witness; never “take first” and never crash |
| `local_x_positive` or mirror disagrees with reviewed elevation binding | that input's elevation components NA with both raw declarations; never numerically disambiguated |
| Unexpected scorer exception | exploratory: loud counted top-level NA + warning; golden/regression: artifact then fail-closed |
| Atomic artifact write failure | remains an infrastructure error; it is outside measurement capability because no honest artifact can be committed |

`not_applicable` is a successful measurement outcome for process continuity. It does
not mean the reading passed gate ②. In `golden` or `regression`, any top-level NA is
committed for audit and then raises fail-closed.

## 3. End-to-end data flow

```text
output.json bytes
  │
  ├─ structural contract detector (no schema default)
  │      └─ ProductIdentity.output_schema = reading_views_v1 | unrecognized
  │
  ├─ strict ReadingView adapter (judge-only)
  │      ├─ manifest/binding join
  │      ├─ plan affine projection
  │      ├─ elevation reviewed projection
  │      └─ ReadingNormalizationCertificateV1
  │
  ├─ GT-side one-way registration/matching (judge-only)
  │      ├─ plan segment coverage
  │      ├─ opening global assignment by trusted source relation
  │      └─ SourceApplicabilityCertificateV1
  │
  ├─ capability-filtered Va reference/product/absence ledgers
  │
  └─ ScoreSidecarV9 + grade.png
         ├─ coordinate rows
         ├─ per-source/per-component NA reasons
         └─ hashes for every certificate/input/helper
```

The reading adapter must not import from `src.agent.judge.gt_schema`; it produces
product-side normalized evidence using the manifest and score bindings. A separate
judge matcher consumes that evidence plus typed GT. This keeps the product projection
independent of the answer and makes any later GT registration visibly one-way.

## 4. Product contract detection and the F8 capability guard

### 4.1 Detector

Add to `src/agent/judge/reading_typed_adapter.py`:

```python
READING_PRODUCT_CONTRACT = "reading_views_v1"
READING_CONTRACT_DETECTOR_VERSION = "reading_contract_detector_v1"

@dataclass(frozen=True)
class ReadingContractDecision:
    contract_id: Literal["reading_views_v1", "unrecognized"]
    reason: str | None

def identify_reading_contract(raw: object) -> ReadingContractDecision: ...
```

The detector is total and uses these exact rules:

1. `raw` must be a dictionary;
2. `raw.get("views")` must be a dictionary;
3. every view key must be a non-empty string;
4. each value may be any JSON value at this phase; per-view parsing owns its NA;
5. top-level extra keys do not change recognition and remain covered by
   `output_sha256`; no top-level `schema_version` is required or synthesized.

Failures return `unrecognized` with one of:
`reading_output_not_object`, `reading_views_missing`, `reading_views_not_object`, or
`reading_view_id_invalid`.

This deliberately recognizes the envelope before requiring every expected view. A
missing or malformed individual view is a component NA, allowing honest partial
scoring of other inputs.

### 4.2 Runner identity

Delete the reading use of:

```python
str(output.get("schema_version", "3"))
```

The runner instead passes the detector decision:

```python
output_schema = identify_reading_contract(output).contract_id
```

Correction continues to require its explicit schema key. It receives a missing
sentinel such as `"unrecognized"`, never a default `"3"`.

### 4.3 Capability decision

`decide_score_capability` must gain a reading branch before returning `c2_v3`.
Conceptually:

```python
if stage == "reading":
    if product_schema != "reading_views_v1":
        return NA("unsupported_reading_contract")
    if reading_adapter_version != "reading_typed_adapter_v1":
        return NA("unsupported_reading_contract")
    return c2_v3
```

The capability key includes:

- typed GT schema/profile;
- stage;
- detected product contract, not a guessed schema;
- accepted state and artifact contract as identity data (not as a prerequisite for
  scoring unaccepted reading attempts);
- base/effective/score-capability manifest hashes;
- score binding hash;
- reading adapter and contract detector versions;
- plan/elevation transform helper versions; and
- existing Va/Vg/scorer/tolerance identities.

This gate is demonstrably non-tautological:

- `{}` → unrecognized;
- `{"views": []}` → unrecognized;
- the former hand-built flat payload with `"schema_version":"3"` → unrecognized;
- `{"views": {}}` → recognized envelope; every expected product view is
  product-content NA, denominators remain, and targets score as misses;
- a real aggregate reading output → recognized.

No test may assert the reading schema by reconstructing the same default expression
used by production. Tests call the detector and the real run-stage assembler.

## 5. New strict internal and sidecar contracts

The names below are normative. Fields are strict/frozen, extra-forbid, finite, and
canonically hashed using the existing sorted compact UTF-8 JSON helper.

### 5.1 Transform records

```python
class Affine2DV1(StrictWire):
    # world_x = xx*local_x + xy*local_y + x0
    # world_y = yx*local_x + yy*local_y + y0
    xx: FiniteFloat
    xy: FiniteFloat
    x0: FiniteFloat
    yx: FiniteFloat
    yy: FiniteFloat
    y0: FiniteFloat

class PlanFrameCertificateV1(StrictWire):
    input_id: StableId
    floor_id: StableId
    source: Literal["reading_scale_origin_v1"]
    units: Literal["metre"]
    local_axes: Literal["drawing_right_up"]
    affine: Affine2DV1
    nonzero_origin: StrictBool
    preimage_sha256: Hex64

class VerticalDatumCertificateV1(StrictWire):
    input_id: StableId
    floor_ids: tuple[StableId, ...]
    status: Literal["applicable", "not_applicable"]
    source: Literal[
        "product_declared",
        "project_convention_2026_07_25",
        "multi_floor_unavailable",
    ]
    units: Literal["metre"]
    local_axis: Literal["drawing_up"]
    z_sign: Literal[1] | None
    z_origin: FiniteFloat | None
    authority: Literal[
        "reading_scale_origin_world_z_m",
        "user_ruling_grade_line_equals_interior_floor_zero",
        "reviewed_binding_multiple_floors",
    ]
    reason: Literal["elevation_floor_partition_unresolved"] | None
    preimage_sha256: Hex64
```

The first two sources require one floor, `status="applicable"`, `z_sign=1`, a finite
origin, their matching authority, and null reason. `multi_floor_unavailable` requires
at least two sorted floor IDs, `status="not_applicable"`, null sign/origin, the
reviewed-binding authority, and the exact non-null reason. A malformed non-null
product datum is not a coefficient source and therefore emits no datum certificate;
its product-content component applicability and raw-value hash carry that failure.

All matrix application happens in one helper:

```python
def apply_affine_2d(frame: Affine2DV1, point: tuple[float, float]) -> tuple[float, float]: ...
```

Downstream code never spells out `x + origin`, assumes identity, parses free text, or
knows the frame source. The determinant must be finite and nonzero. The current plan
frame is:

```text
xx=1, xy=0, x0=scale_origin.world_x_m
yx=0, yy=1, y0=scale_origin.world_y_m
```

`scale_origin.note` and `world_z_m` do not participate in the plan frame. Booleans are
not accepted as numbers. Missing or invalid structured x/y origin fields make both
plan components product-content NA/retain-as-miss; there is no identity fallback, but
the product cannot shrink its target denominator. `nonzero_origin` is
exactly `(x0 != 0.0 or y0 != 0.0)`, with no tolerance. Its count is first-class in the
payload and grade board; a product-declared translation is never silent.

The vertical datum has exactly three branches:

1. a strict finite non-null `scale_origin.world_z_m` gives
   `source="product_declared"`, `z_origin=<declared>`, and declaration authority;
2. missing/null `world_z_m` gives `z_origin=0.0` and
   `source="project_convention_2026_07_25"`, backed by the user's project ruling that
   the elevation grade line is the interior floor at ±0.000; use of this branch is
   counted in the payload and grade board; or
3. a binding naming multiple floors produces the typed unavailable certificate and
   trusted-capability NA `elevation_floor_partition_unresolved`.

A present non-null but non-finite/non-numeric `world_z_m` is product-side
unmeasurable vertical evidence: the z denominator remains and misses under §9.

### 5.2 Component applicability

```python
ReadingComponent = Literal[
    "plan_segments",
    "plan_openings",
    "elevation_opening_xy",
    "elevation_opening_z",
]

class ReadingComponentApplicabilityV1(StrictWire):
    source_input_id: StableId
    channel: Literal["plan", "elevation"]
    component: ReadingComponent
    floor_ids: tuple[StableId, ...]
    status: Literal["applicable", "not_applicable"]
    reasons: tuple[StableId, ...]
    cause_class: Literal[
        "none", "trusted_input", "trusted_frame",
        "product_content", "judge_ambiguity",
    ]
    denominator_disposition: Literal[
        "score", "filter", "retain_as_miss",
    ]
    observation_count: NonNegativeInt
    transform_sha256: Hex64 | None
```

Validation:

- `applicable` requires `reasons == ()`, `cause_class=="none"`, and
  `denominator_disposition=="score"`;
- trusted-input `not_applicable` requires a reason and
  `denominator_disposition=="filter"`;
- trusted-frame (reporting label only), product-content, or
  product-coordinate-dependent judge-ambiguity
  `not_applicable` requires a reason and
  `denominator_disposition=="retain_as_miss"`;
- `observation_count == 0` is legal in both statuses and is never itself an NA reason;
- status is final for the certificate phase. A matcher ambiguity produces a new final
  applicability certificate rather than mutating an earlier object.

Channel summaries are derived, never independently asserted:

- all components applicable → `applicable`;
- a nonempty mixture → `partially_applicable`;
- none applicable → `not_applicable`.

Channel summaries report measurement status. Denominators obey
`denominator_disposition`, not status alone. Thus a product-side component can be
visibly unmeasurable while its targets remain and miss; only `filter` removes targets.
`cause_class=="trusted_frame"` names the two-sided U-10 reporting boundary; because
the disagreement is triggered by product declarations, it confers no filtering right.
A top-level `c2_scored` payload is produced whenever at least one component disposition
is `score` or `retain_as_miss`, even if every channel's measurement summary is
`not_applicable`. `no_scorable_reading_channel` is reserved for the case where every
component disposition is `filter`.

### 5.3 Normalized observation audit union

Every ID is the full SHA-256 of the canonical tuple
`(output_sha256, input_id, stroke_id, component, primitive_index)`, prefixed by
`reading:`. Raw IDs are retained separately. No delimiter-based concatenation can
collide.

```python
class Point2V1(StrictWire):
    x: FiniteFloat
    y: FiniteFloat

class ClosedIntervalV1(StrictWire):
    lo: FiniteFloat
    hi: FiniteFloat

    @model_validator(mode="after")
    def _ordered(self):
        if self.lo > self.hi:
            raise ValueError("closed interval requires lo <= hi")
        return self

class ReadingPlanSegmentAuditV1(StrictWire):
    kind: Literal["plan_segment"]
    observation_id: StableId
    source_input_id: StableId
    source_stroke_id: StableId
    primitive_index: NonNegativeInt
    floor_id: StableId
    local_p1: Point2V1
    local_p2: Point2V1
    world_p1: Point2V1
    world_p2: Point2V1
    source_geometry_sha256: Hex64
    transform_sha256: Hex64
    topology: Literal["unknown"]

class ReadingPlanOpeningAuditV1(StrictWire):
    kind: Literal["plan_opening"]
    observation_id: StableId
    source_input_id: StableId
    source_stroke_id: StableId
    floor_id: StableId
    geometry_kind: Literal["line", "rect", "polyline"]
    local_vertices: tuple[Point2V1, ...]
    world_vertices: tuple[Point2V1, ...]
    source_geometry_sha256: Hex64
    transform_sha256: Hex64

class ReadingElevationOpeningAuditV1(StrictWire):
    kind: Literal["elevation_opening"]
    observation_id: StableId
    source_input_id: StableId
    source_stroke_id: StableId
    floor_id: StableId
    facade_family: CardinalFamily
    geometry_kind: Literal["line", "rect", "polyline"]
    local_x_interval: ClosedIntervalV1
    local_y_interval: ClosedIntervalV1
    world_along_interval: ClosedIntervalV1
    z_interval: ClosedIntervalV1
    source_geometry_sha256: Hex64
    horizontal_transform_sha256: Hex64
    vertical_transform_sha256: Hex64

ReadingObservationAuditV1 = Annotated[
    ReadingPlanSegmentAuditV1
    | ReadingPlanOpeningAuditV1
    | ReadingElevationOpeningAuditV1,
    Field(discriminator="kind"),
]
```

`ClosedIntervalV1` permits `lo == hi` for an incomplete product observation. GT target
intervals remain strictly positive. A zero-width observation is measurable: existence,
along, and width can be compared and normally miss. It is not converted to NA or
inflated by epsilon.

### 5.4 Certificates

```python
class ReadingMetadataFindingV1(StrictWire):
    source_input_id: StableId
    code: Literal[
        "image_kind_declaration_mismatch",
        "orientation_declaration_mismatch",
        "unbound_reading_view",
    ]
    declared_sha256: Hex64
    trusted_sha256: Hex64

class ReadingAmbiguityWitnessV1(StrictWire):
    source_input_id: StableId
    component: ReadingComponent
    floor_ids: tuple[StableId, ...]
    observation_ids: tuple[StableId, ...]
    candidate_target_ids: tuple[StableId, ...]
    objective_preimage_sha256: Hex64
    reason: Literal[
        "multiple_support_lines",
        "multiple_equal_opening_assignments",
        "coordinate_identity_unresolved",
    ]

class UnmeasurableObservationWitnessV1(StrictWire):
    source_input_id: StableId
    source_stroke_id: StableId
    component: ReadingComponent
    reason: Literal[
        "plan_wall_rect_has_no_centerline_contract",
        "consumed_geometry_malformed",
    ]
    cause_class: Literal["product_content"]
    source_geometry_sha256: Hex64

class ElevationFrameDisagreementWitnessV1(StrictWire):
    source_input_id: StableId
    binding_local_x_positive: Literal[
        "image_left_to_right", "image_right_to_left"
    ]
    product_local_x_positive_raw: Literal[
        "image_left_to_right", "image_right_to_left", "missing"
    ]
    product_local_x_positive_effective: Literal[
        "image_left_to_right", "image_right_to_left"
    ] | None
    binding_mirrored: StrictBool
    product_mirrored_raw: StrictBool | Literal[
        "true", "false", "unknown", "missing"
    ]
    product_mirrored_effective: StrictBool | None
    binding_frame_transform_sha256: Hex64
    product_facade_sha256: Hex64
    reason: Literal["elevation_local_x_sense_disagreement"]

class ReadingNormalizationCertificateV1(StrictWire):
    schema_version: Literal["1"]
    helper_version: Literal["reading_typed_adapter_v1"]
    contract_detector_version: Literal["reading_contract_detector_v1"]
    source_output_sha256: Hex64
    product_contract: Literal["reading_views_v1"]
    base_view_manifest_sha256: Hex64
    score_view_bindings_sha256: Hex64
    plan_frames: tuple[PlanFrameCertificateV1, ...]
    vertical_datums: tuple[VerticalDatumCertificateV1, ...]
    component_applicability: tuple[ReadingComponentApplicabilityV1, ...]
    observations: tuple[ReadingObservationAuditV1, ...]
    unmeasurable_observation_witnesses: tuple[
        UnmeasurableObservationWitnessV1, ...
    ]
    elevation_frame_disagreements: tuple[
        ElevationFrameDisagreementWitnessV1, ...
    ]
    metadata_findings: tuple[ReadingMetadataFindingV1, ...]
    content_sha256: Hex64

class ReadingFilteredComponentBasisV1(StrictWire):
    source_input_id: StableId
    component: ReadingComponent
    floor_ids: tuple[StableId, ...]
    cause_class: Literal["trusted_input"]
    reasons: tuple[StableId, ...]

class ReadingDenominatorBasisV1(StrictWire):
    helper_version: Literal["reading_denominator_v1"]
    gt_content_sha256: Hex64
    base_view_manifest_sha256: Hex64
    score_view_bindings_sha256: Hex64
    filtered_components: tuple[ReadingFilteredComponentBasisV1, ...]
    content_sha256: Hex64

class ReadingDenominatorAtomV1(StrictWire):
    atom_id: StableId
    target_id: StableId
    target_kind: Literal["plan_segment", "window"]
    component: ReadingComponent
    claim: ClaimName | None
    floor_id: StableId
    source_input_ids: tuple[StableId, ...]
    eligible_units: NonNegativeFloat

class SourceApplicabilityCertificateV1(StrictWire):
    schema_version: Literal["1"]
    helper_version: Literal["reading_source_applicability_v1"]
    normalization_sha256: Hex64
    gt_content_sha256: Hex64
    score_manifest_sha256: Hex64
    denominator_basis: ReadingDenominatorBasisV1
    denominator_atoms: tuple[ReadingDenominatorAtomV1, ...]
    denominator_basis_sha256: Hex64
    denominator_sha256: Hex64
    component_applicability: tuple[ReadingComponentApplicabilityV1, ...]
    ambiguity_witnesses: tuple[ReadingAmbiguityWitnessV1, ...]
    content_sha256: Hex64
```

Canonical ordering is `(source_input_id, component, floor_ids)` for applicability and
`(source_input_id, source_stroke_id, kind, primitive_index)` for observations. Duplicate
normalized IDs or duplicate component keys produce component NA
`normalization_identity_unresolved`, not an order-dependent winner.

Every `preimage_sha256` is the canonical hash of all fields in its model except the
hash itself. Every certificate `content_sha256` is the canonical hash of all fields
except `content_sha256`. Metadata hashes use the exact JSON value (or the sentinel
string `"missing"`) on each side. Ambiguity candidate and observation IDs are sorted;
the objective preimage contains the complete unrounded objective tuple for every
candidate assignment. No error message participates in a certificate.

`denominator_basis_sha256` equals `denominator_basis.content_sha256`.
`denominator_sha256` hashes the canonical JSON bytes of `denominator_atoms`. Atom
ordering is `(target_id, component, claim-or-empty, source_input_ids)`; IDs are full
hashes of those same canonical identity fields. Segment units are exact target lengths;
opening claim units are the existing exact target claim units. These are positive
reference atoms, not product-derived extra/duplicate accounts. The basis and atoms
exclude every stroke geometry, coordinate, stroke ID, observation/registration result,
and unmeasurable-observation witness. Only
`denominator_disposition=="filter"` appears in `filtered_components` and removes
mapped sources/atoms. The basis excludes product facade declarations as well as
product geometry. Any two products under identical trusted GT/manifest/bindings must
therefore have byte-identical serialized bases, atom tuples, and hashes even when
their geometry, `facade.local_x_positive`, and `facade.mirrored` bytes differ.

### 5.5 Score wire v9

The following changed v9 models are normative. Existing typed GT identity, tolerance,
Va ledger, claim-applicability, claim-summary, and rejection fields retain their
current strict meanings; they are embedded under the explicitly listed v9 fields.

```python
class ReadingChannelSummaryV1(StrictWire):
    channel: Literal["plan", "elevation"]
    status: Literal["applicable", "partially_applicable", "not_applicable"]
    source_input_ids: tuple[StableId, ...]
    applicable_components: tuple[ReadingComponent, ...]
    not_applicable_components: tuple[ReadingComponent, ...]
    reasons: tuple[StableId, ...]

class ReadingVisibilityCountsV1(StrictWire):
    nonzero_plan_origins: NonNegativeInt
    project_convention_vertical_datums: NonNegativeInt
    multiple_plan_view_floor_components: NonNegativeInt
    elevation_local_x_sense_disagreements: NonNegativeInt
    scorer_internal_failures: NonNegativeInt

class HelperIdentityV9(StrictWire):
    scorer_schema: Literal["9"]
    segment_scorer: StableId
    opening_matcher: Literal["reading_opening_global_assignment_v1"]
    gt_to_va_adapter: StableId
    denominator_helper: StableId
    grade_renderer: Literal["b4b_grade_png_v2"]
    va_helper: StableId
    vg_helper: StableId
    claims_contract: StableId
    reading_contract_detector: Literal["reading_contract_detector_v1"]
    reading_adapter: Literal["reading_typed_adapter_v1"]
    reading_source_applicability: Literal["reading_source_applicability_v1"]

class ScoreIdentityV9(StrictWire):
    gt: GtIdentityV8
    product: ProductIdentityV8
    manifest: ManifestIdentityV8
    helpers: HelperIdentityV9
    capability: CapabilityDecisionV8
    tolerances: C2ToleranceIdentityV8
    reading_normalization_sha256: Hex64 | None
    source_applicability_sha256: Hex64 | None
    score_manifest_sha256: Hex64
    denominator_basis_sha256: Hex64 | None
    denominator_sha256: Hex64 | None
    reference_applicability_sha256: Hex64 | None
    product_applicability_sha256: Hex64 | None
    absence_applicability_sha256: Hex64 | None

class ReadingSegmentScoreRowV1(StrictWire):
    row_contract: Literal["reading_segment_v1"]
    target_id: StableId | None
    observation_id: StableId | None
    floor_id: StableId
    target_exterior: StrictBool | None
    status: Literal[
        "complete", "within_tolerance", "miss", "extra", "duplicate",
        "not_applicable",
    ]
    eligible_units: NonNegativeFloat
    axis_alignment_error_m: NonNegativeFloat | None
    position_error_m: NonNegativeFloat | None
    extent_symmetric_difference_m: NonNegativeFloat | None
    na_reason: StableId | None

class OpeningSourceScoreRowV1(StrictWire):
    target_id: StableId
    target_kind: Literal["window", "door"]
    claim: ClaimName
    source_input_id: StableId
    channel: Literal["plan", "elevation"]
    eligible_units: Annotated[
        float, Field(strict=True, ge=0.0, le=1.0, allow_inf_nan=False)
    ]
    result: Literal[
        "complete", "within_tolerance", "miss", "conflict",
        "not_applicable",
    ]
    na_reason: StableId | None
    matched_observation_ids: tuple[StableId, ...]
    expected_intervals: tuple[ClosedIntervalV1, ...]
    observed_interval: ClosedIntervalV1 | None
    expected_scalar: FiniteFloat | None
    observed_scalar: FiniteFloat | None
    error_metric: Literal[
        "binary", "endpoint_max_abs", "length_abs",
        "masked_interval_length", "scalar_abs", "not_applicable",
    ]
    error_value: NonNegativeFloat | None
    tolerance: NonNegativeFloat | None
    source_applicability_sha256: Hex64

class ScoreCriterionV9(StrictWire):
    criterion_id: StableId
    eligible: StrictBool
    denominator_units: NonNegativeFloat
    passing_units: NonNegativeFloat
    failing_units: NonNegativeFloat
    na_reasons: dict[StableId, NonNegativeInt]
    verdict: Literal[
        "pass", "fail", "not_applicable", "insufficient_evidence"
    ]

class C2ScoredPayloadV9(StrictWire):
    kind: Literal["c2_scored"]
    channel_applicability: tuple[ReadingChannelSummaryV1, ...]
    unmeasurable_observations: NonNegativeInt
    visibility_counts: ReadingVisibilityCountsV1
    segment_rows: tuple[SegmentScoreRowV8 | ReadingSegmentScoreRowV1, ...]
    segment_extras: tuple[SegmentExtraV8, ...]
    opening_source_rows: tuple[OpeningSourceScoreRowV1, ...]
    claim_rows: tuple[ClaimScoreRowV8, ...]
    claim_summaries: tuple[ClaimSummaryV8, ...]
    extras: tuple[ExtraObservationV8, ...]
    score_criteria: tuple[ScoreCriterionV9, ...]
    reference_ledger_sha256: Hex64
    product_ledger_sha256: Hex64 | None
    absence_ledger_sha256: Hex64 | None

class NotApplicablePayloadV9(StrictWire):
    kind: Literal["not_applicable"]
    reason: Literal[
        "unsupported_reading_contract", "unsupported_gt_profile",
        "unsupported_view_contract", "no_scorable_reading_channel",
        "scorer_internal_failure",
    ]
    detail: StableId
    channel_applicability: tuple[ReadingChannelSummaryV1, ...]
    unmeasurable_observations: NonNegativeInt
    visibility_counts: ReadingVisibilityCountsV1
    score_criteria: tuple[ScoreCriterionV9, ...]

class RejectedPayloadV9(StrictWire):
    kind: Literal["rejected"]
    error_code: StableId
    cause_code: StableId | None
    gate_id: StableId
    detail: StableId
    channel_applicability: tuple[ReadingChannelSummaryV1, ...]
    unmeasurable_observations: NonNegativeInt
    visibility_counts: ReadingVisibilityCountsV1

ScorePayloadV9 = Annotated[
    C2ScoredPayloadV9 | NotApplicablePayloadV9 | RejectedPayloadV9,
    Field(discriminator="kind"),
]

class ScoreCertificatesV1(StrictWire):
    reading_normalization: ReadingNormalizationCertificateV1 | None
    source_applicability: SourceApplicabilityCertificateV1 | None
    aggregate_sha256: Hex64

class EmbeddedCertificateContractV1(StrictWire):
    certificate_kind: Literal[
        "reading_normalization", "source_applicability"
    ]
    present: StrictBool
    aggregate_sha256: Hex64

class ScoreArtifactContractV2(StrictWire):
    contract_version: Literal["2"]
    output_sha256: Hex64
    sidecar_schema_version: Literal["9"]
    grade_kind: Literal[
        "c2_grade", "not_applicable_board", "rejected_board"
    ]
    grade_png_sha256: Hex64
    embedded_ledgers: tuple[EmbeddedLedgerContractV1, ...]
    embedded_certificates: tuple[EmbeddedCertificateContractV1, ...]

class ScoreSidecarV9(StrictWire):
    schema_version: Literal["9"]
    identity: ScoreIdentityV9
    certificates: ScoreCertificatesV1
    artifact_contract: ScoreArtifactContractV2
    payload: ScorePayloadV9
    content_sha256: Hex64
```

Additional validators are exact:

- `ReadingSegmentScoreRowV1.status == "not_applicable"` iff `na_reason` is non-null and
  `eligible_units == 0`; other statuses require null `na_reason`;
- an unmatched observation row has `target_id=None` and
  `target_exterior=None`; a target-backed row has both non-null;
- source row NA has zero units, an NA reason, no numeric error, and
  `error_metric="not_applicable"`; eligible source rows conserve their outcome units;
- existence uses applicability intervals plus the observed interval and a binary
  error; full along uses target/observed intervals plus endpoint-max error; partial
  along/width uses applicability intervals plus `masked_interval_length`; full width
  uses expected/observed scalar lengths plus `length_abs`; sill/head uses scalar
  endpoints plus `scalar_abs`; host is binary with no coordinate value; appearance/NA
  has no coordinate or error value;
- `ScoreCertificatesV1.aggregate_sha256` hashes the two optional certificate hashes in
  fixed name order; correction uses canonical `"absent"` sentinels;
- `payload.unmeasurable_observations` is present on every payload variant. When a
  normalization certificate is present it exactly equals
  `len(unmeasurable_observation_witnesses)`; before normalization it is zero. It is
  never derived from how many GT targets happened to match;
- every `visibility_counts` field is likewise derived from typed certificates or the
  totalizer event, never independently supplied: a plan frame contributes to
  `nonzero_plan_origins` iff its exact `nonzero_origin` flag is true; a vertical datum
  contributes to `project_convention_vertical_datums` iff it uses that named source;
  the remaining fields count exact applicability/witness events named by the field;
- embedded ledger order remains reference/product/absence; embedded certificate order
  is reading-normalization/source-applicability;
- a scored reading sidecar has both certificates and matching identity hashes; a
  reading NA/rejected before a certificate phase may omit the not-yet-constructed
  certificate only when the corresponding identity hash is null; a normalized
  `no_scorable_reading_channel` result has both certificates; correction has both
  certificates absent and both identity fields null;
- the score-manifest hash is always present (for correction it equals the effective
  manifest hash);
- a reading result with a source-applicability certificate has matching non-null
  denominator basis/denominator hashes in identity; correction and reading results
  produced before source applicability use null denominator hashes;
- artifact kind, output hash, PNG hash, certificate hashes, ledger hashes/counts, and
  sidecar content hash must all cross-validate.

For correction, v9 copies every existing `SegmentScoreRowV8`, `SegmentExtraV8`,
`ClaimScoreRowV8`, `ClaimSummaryV8`, `ExtraObservationV8`, and criterion value without
conversion. Its additive reading-only fields are canonical empty tuples, null hashes,
and zero counts. It must not serialize a reading row shape for correction. This is how
the §15.7 public projection remains byte-identical rather than merely numerically
equivalent.

`TypedScoreResult.payload` becomes the discriminated union, not
`C2ScoredPayload` only. Callers branch on `payload.kind`; they never unconditionally
read `payload.score_criteria`.

Schema 8 sidecars remain parseable only by their v8 loader. They are cache misses for a
v9 request. No in-place v8 semantic extension is permitted.

## 6. Common reading-envelope normalization

`normalize_reading_attempt` takes raw JSON, output hash, base manifest, and validated
score bindings. It returns an outcome and never raises because of product content.

### 6.1 Manifest join

For every required manifest entry whose `view_type` is plan or elevation:

1. resolve `expected_output_id`;
2. look up that exact key in `payload["views"]`;
3. look up the exact judge binding by manifest `input_id`;
4. verify binding kind against trusted manifest kind;
5. parse the value with `ReadingView.model_validate`, then strictly parse only consumed
   geometry fields from the original JSON so Pydantic coercion cannot alter certificate
   facts.

The outer dictionary key is the product key; normalized source identity is the trusted
manifest `input_id`. The binding's `gt_source_view_ids` remains a separate tuple. These
identities must not be conflated.

Per-view outcomes:

- missing view → all of its components product-side NA `reading_view_missing` with
  `denominator_disposition="retain_as_miss"`;
- non-object/ReadingView parse failure → all components NA
  `reading_view_schema_unsupported`, also product-side/retain-as-miss;
- a missing trusted manifest entry or binding is instead trusted-input NA/filter (or
  rejected when the trusted bundle fails its own required schema/identity validation);
- product `image_kind` mismatch → trusted binding still selects the adapter; record
  `image_kind_declaration_mismatch`, do not grant NA;
- elevation `view_facade` mismatch alone → record
  `orientation_declaration_mismatch`; reviewed binding controls facade selection;
- elevation `local_x_positive` or `mirrored` disagreement → both elevation components
  for that input are trusted-frame NA/retain-as-miss
  `elevation_local_x_sense_disagreement` with the exact witness defined in §8.1;
- unexpected view key → audit finding `unbound_reading_view`, never a score source.

Missing/malformed product views cannot shrink the reference denominator. The
local-x/mirror case is deliberately different: it is a ruled frame-contract
disagreement about how to interpret every coordinate, so it produces no positive
observation and is visibly counted. Because the triggering declarations are product
bytes, its answer targets remain in the denominator and miss. No numeric coordinate or
GT target is examined to reach that decision.

### 6.2 Visibility filter

For a recognized semantic stroke, `visibility == "hidden"` or
`line_style in {"dashed", "dash_dot"}` excludes it from physical observations.
`None`, `"visible"`, `"solid"`, and `"unknown"` remain eligible.

Exclusion does not make the component NA. If every stroke is excluded, the applicable
component has zero observations and missing targets score as misses. This is required
because visibility is product evidence, not judge capability.

Dimensions, OCR, room labels, wall-fill, outline, and uncaptured entries remain in the
output-byte hash but are not silently converted into wall/window observations.
`wall_fill` is not used to infer floor identity or a vertical datum.

## 7. Plan channel

### 7.1 Frame

A plan view is measurable only when:

- its plan binding names exactly one floor;
- its raw `scale_origin` is an object;
- `world_x_m` and `world_y_m` are strict finite numbers; and
- the plan frame certificate validates.

The guide's metre coordinates and drawing-right/up axes supply the linear part; the
two structured fields supply translation. Free prose supplies nothing. A missing
declaration yields:

```text
plan_segments = not_applicable(plan_frame_unavailable)
plan_openings = not_applicable(plan_frame_unavailable)
```

No coordinates enter either matcher.

### 7.2 Wall strokes → plan segment input

Only eligible `pen == "wall"` strokes are consumed:

- `kind == "line"` → one segment from `p1` to `p2`;
- `kind == "polyline"` → one segment for every consecutive point pair; add the
  last-to-first edge only when raw `closed is True`;
- a finite zero-length constituent edge remains a measurable segment and normally
  misses; it is not enlarged or converted to NA;
- a malformed consumed line/polyline makes `plan_segments` product-content NA
  `plan_geometry_unsupported`, but its target denominator remains and misses;
- a plan wall `rect` has no declared centerline. Exclude that stroke alone from both
  coverage and extra matching, append one
  `plan_wall_rect_has_no_centerline_contract` witness, and increment
  `payload.unmeasurable_observations`. The component remains applicable, every other
  measurable stroke scores normally, and uncovered targets miss.

Each endpoint is projected once by `apply_affine_2d`. Normalized plan observations have
`topology="unknown"`; the adapter never fills the current `PlanSegment.exterior=True`
default.

If parsing succeeds and there are no eligible wall strokes, the component is
applicable with zero observations.

### 7.3 Wall scoring and topology

Scoring is per floor:

- no applicable plan-segment source for the floor → one zero-unit NA row per GT target
  segment with the component reason;
- an applicable source, including one with zero observations → call the real
  coordinate matcher; uncovered GT length is miss;
- an observation eligible for two GT support lines under the judge's own configured
  tolerance → the whole floor component becomes NA
  `judge_support_registration_ambiguous`, with the observation and candidate support
  lines in the ambiguity certificate. Because this ambiguity depends on product
  coordinates, its denominator disposition is `retain_as_miss`: it is not a rejection,
  not assigned to the first line, and cannot shrink the target denominator.

Topology is target-derived only:

- target-backed exterior rows feed `boundary_complete`;
- target-backed interior rows feed `walls_complete`;
- unmatched product observations feed the generic `no_extra_walls` criterion
  regardless of topology;
- duplicate coverage feeds `no_duplicate_wall_strokes`;
- unmatched product rows carry `target_exterior=None`.

This removes the current false assertion that every reading segment is exterior while
still scoring every coordinate.

Exactly one plan input per floor is supported in v1. More than one makes that floor's
plan components trusted-capability NA/filter
`multiple_plan_views_per_floor_unsupported`; it is not silently unioned or
double-counted. Each affected component increments
`visibility_counts.multiple_plan_view_floor_components`.

### 7.4 Plan window strokes → opening primitives

Only eligible `pen == "window"` strokes are consumed:

- line vertices = `(p1, p2)`;
- rect vertices = the four corners from sorted `x_range_m/y_range_m`;
- polyline vertices = raw ordered points; closure does not add semantic width;
- every vertex is transformed and certified;
- malformed geometry makes `plan_openings` product-content NA
  `plan_opening_geometry_unsupported`, increments one unmeasurable witness per
  malformed consumed stroke, and retains every target in the denominator as a miss;
- no window strokes is applicable/zero and therefore exposes real plan-view misses.

No product facade segment or room is invented.

### 7.5 One-way plan opening registration

For each primitive and GT boundary candidate on the bound floor:

1. line/polyline candidate: all vertices must lie within
   `plan_position_tol_m` of the candidate support line;
2. rect candidate: the candidate support line must intersect the closed rectangle
   expanded only by `plan_position_tol_m`;
3. projection onto the boundary's world-along axis must overlap the finite boundary
   interval (a point interval may be contained);
4. the target opening must have a source ref in the plan binding's
   `gt_source_view_ids`;
5. target kind must be window; door is already NA under the typed target-kind policy.

The candidate-specific projected min/max is the plan along interval. Global assignment
then runs independently per trusted input, using the existing objective:
maximize match count, maximize overlap, minimize center error, minimize width error.
Ties inside `opening_assignment_tie_epsilon` make that input's plan-opening component
NA `judge_opening_assignment_ambiguous`; candidate IDs/metrics are certified.
The tie is product-coordinate-dependent, so its targets remain as misses under
`retain_as_miss`.

Zero candidates means a measurable unmatched product observation, not judge NA.
It may be an extra if Va can certify full negative coverage; otherwise the extra row is
`not_applicable/unresolved_absence_coverage`. GT targets still miss.

The reading product has no room membership or parent-wall topology by design.
Therefore every reading plan `host` source row is
`not_applicable/reading_topology_unavailable`. Judge-derived geometric registration
must never be recycled as proof that the product declared the correct host.

## 8. Elevation channel

### 8.1 What is already authoritative

For each elevation input, use only its validated
`ElevationScoreViewBindingV1` for:

- facade family;
- local-x positive convention;
- mirror state;
- world axis;
- sign; and
- along origin.

The existing `project_typed_elevation_observation` remains the sole local-x →
world-along helper. The adapter supplies its typed entries. Product facade metadata is
recorded but cannot alter the transform.

Before invoking that helper, reconcile the product's image-local sense with the
binding, without looking at a coordinate or GT:

1. read `facade.local_x_positive` and `facade.mirrored` from the raw view, preserving
   a `"missing"` sentinel in the witness;
2. when the facade object exists, an omitted local-x field has the reading schema's
   effective default `image_left_to_right`; an omitted/`"unknown"` mirrored field has
   no effective boolean; `"true"`/`"false"` and strict JSON booleans normalize to the
   corresponding boolean;
3. when the facade object is absent, both effective declarations are unknown;
4. any invalid raw facade value has already made the view product-schema NA under
   §6.1; it is not coerced for this comparison;
5. if either effective declaration is unknown or differs from the binding, set both
   elevation components for that input to trusted-frame NA/retain-as-miss reason
   `elevation_local_x_sense_disagreement`, append a witness containing both binding
   values, both product raw/effective values, and both hashes, then increment
   `visibility_counts.elevation_local_x_sense_disagreements`;
6. otherwise, and only otherwise, project with the binding.

The product's facade-family mismatch by itself remains a metadata finding because the
trusted manifest/binding selects the input's facade. The local-x/mirror disagreement
is not a metadata-only finding: it means the scorer cannot tell which image-local
frame produced the numbers. The scorer must not project both interpretations, inspect
range plausibility, compare either result with GT, or select a lower-error
interpretation.

The real sm24 attempt exercises this gate: East and South agree; North and West
declare `image_right_to_left` while their reviewed bindings declare
`image_left_to_right` (the same two bindings have `sign=-1`). Thus North and West are
expected input-scoped elevation NA with witnesses and answer-target misses, not
silently mirrored score rows or filtered denominator atoms.
The reproducible four-input comparison is in §15.

### 8.2 Window stroke conversion

Only eligible `pen == "window"` strokes are observations. Strict geometry bounds are:

- rect: its sorted `x_range_m` and `y_range_m`;
- line: min/max of its two x and y coordinates;
- polyline: min/max across all points.

Malformed consumed geometry makes both elevation components for that input
product-content NA `elevation_opening_geometry_unsupported`, creates one
unmeasurable-observation witness per malformed consumed stroke, and retains the target
denominator as misses. A degenerate but finite range remains a measurable closed
interval and normally scores poorly; it is not an NA escape hatch. No window strokes
means both components are applicable with zero observations.

The adapter creates a typed local observation with:

```text
observation_id       = certified reading ID
source_input_id      = manifest input_id
floor_id             = binding floor (see below)
kind                 = window
facade_family        = binding facade_family
local_x_interval     = geometry x bounds
z_interval           = explicit vertical transform(geometry y bounds)
```

It then invokes the existing projection helper. It does not search for
`facade_segment_id` in the reading JSON.

### 8.3 Floor and vertical boundary

The floor/datum branches are exact:

- a binding with exactly one `floor_id` uses that floor;
- for that binding, a strict finite non-null raw `scale_origin.world_z_m` produces
  `z=local_y+world_z_m` and a `product_declared` vertical certificate;
- an absent/null `world_z_m` produces `z=local_y+0` and a
  `project_convention_2026_07_25` certificate backed by the ruled project convention
  “grade line = interior floor ±0.000”; this is counted on the sidecar and board;
- a present non-null non-finite/non-numeric datum makes only
  `elevation_opening_z` product-content NA/retain-as-miss; horizontal elevation
  scoring remains available;
- a binding naming multiple floors makes both elevation components trusted-input
  NA/filter `elevation_floor_partition_unresolved` until a reviewed
  vertical/floor-partition binding exists.

The restriction is a capability branch, not a single-floor assumption in the matcher.
The normalized and score wires already carry arbitrary floor tuples and replaceable
vertical transforms.

### 8.4 Elevation opening registration and scoring

Target candidates must:

- be windows on the bound floor;
- have boundary facade family equal to the reviewed binding;
- have a source ref in `binding.gt_source_view_ids`;
- overlap the projected world-along interval (or contain its point); and
- meet the configured center tolerance.

Global assignment uses the same deterministic objective and ambiguity treatment as
plan, independently per input. No raw or normalized observation needs a product
facade-segment ID. Once a target is matched, its boundary ID is audit output from the
one-way judge assignment, not product evidence.

Elevation source rows score:

- existence from overlap;
- along from projected endpoints;
- width from projected extent;
- sill/head from transformed z endpoints; and
- host and appearance as NA.

An unmatched elevation observation is classified extra only when it maps to a unique
GT facade segment and Va certifies its entire interval as negative. Otherwise it is
explicit `not_applicable` with reason; no host-resolution exception escapes.

## 9. Source-specific applicability and denominator control

Empty tuples are not capability signals. A strict source applicability overlay controls
which trusted source/claim combinations may enter Va and target denominators.

### 9.1 Score-capability manifest

After normalizing and resolving matcher-level ambiguity, derive an in-memory
`score_manifest` from the effective manifest. Do not mutate or rewrite the base
manifest.

Capability is split by cause before changing a single reference atom:

| Cause/disposition | Examples | Reference denominator and Va treatment |
|---|---|---|
| trusted input / `filter` | binding absent, unsupported trusted view kind, multi-floor binding, multiple plan inputs per floor | remove only that source/component's mapped positive claims and negative completeness |
| trusted-frame reporting / `retain_as_miss` | product/binding local-x or mirror disagreement | component NA with two-sided witness/count; keep its answer targets and score them as misses |
| product content / `retain_as_miss` | missing/malformed view, bad scale origin, bad stroke/range, rect wall exclusion | keep the base positive denominator and trusted negative-capability declarations; absent measurable evidence produces misses |
| product-coordinate-dependent judge ambiguity / `retain_as_miss` | equal support/assignment candidates caused by an observation coordinate | keep the denominator; the affected source supplies no passing observation and therefore misses |
| applicable / `score` | valid zero or nonzero observations | keep the denominator; zero observations produce misses |

Only `denominator_disposition=="filter"` removes the corresponding claim from the
manifest entry's `potentially_observable_claims`, from
`negative_evidence_capable_claims`, and from matching positive source evidence.
Remove a coverage/assertion only when its remaining trusted negative-claim set is
empty. Both `score` and `retain_as_miss` preserve the base reference atoms exactly.
Malformed/excluded product observations are never admitted as product positives or
extras, but they also never edit reference atoms.

Mappings:

| Component | Claims retained while applicable |
|---|---|
| plan openings | existence, along, width |
| elevation opening xy | existence, along, width |
| elevation opening z | sill, head |
| reading topology | none; host is always NA |
| target appearance | none; reference value remains unavailable |

Doors remain target-kind NA; reading never fabricates a door pen.

The derived manifest is strictly revalidated and canonically hashed. Its hash and the
source applicability certificate are in score identity. Only a trusted-input-filtered
source creates neither a target miss nor trusted negative evidence. Supported-zero,
trusted-frame-disagreement, and product-content-unmeasurable sources retain reference
evidence and create real misses; the latter two also expose their NA reason and
witness/count.

The denominator constructor is a pure function named
`derive_reading_denominator_v1(gt, base_manifest, bindings,
trusted_capability_dispositions)`.
Its preimage contains target IDs/claim/unit atoms, trusted manifest and binding
identity, helper version, and trusted-input-only capability exclusions. The fourth
argument is a strict tuple of `ReadingFilteredComponentBasisV1`; its cause literal can
only be `trusted_input`. It contains
no stroke ID, pen, geometry kind, coordinate, observation ID, registration result, or
unmeasurable witness. It receives neither U-10 product declaration; those values affect
normalization/applicability evidence only. It emits the strict
`ReadingDenominatorBasisV1`, the canonical
`tuple[ReadingDenominatorAtomV1, ...]`, and their SHA-256 values. Callers serialize
those strict values with the repository's canonical JSON helper; the pure function
does no I/O and never receives any raw product value.

The blocking purity lock runs the constructor twice under byte-identical GT,
manifest, and bindings: once with the real product and once with every product stroke
geometry malformed **and** every elevation product `facade.local_x_positive` and
`facade.mirrored` declaration flipped.
It asserts byte equality of the canonical denominator preimages, byte equality of the
canonical denominator outputs, and equality of both hashes—not merely equal numeric
totals. Both attempts must expose different normalization/unmeasurable and frame-
disagreement evidence, proving both mutation classes reached the adapter. This lock is
not satisfied by returning no denominator for either product.

### 9.2 Input ID versus GT view ID

Opening observations carry `source_input_id`. Candidate targeting uses the binding's
separate `gt_source_view_ids`. Va decisions and source score rows use input IDs. No code
compares `1f_view` directly to `plan-F1`, and no code chooses the first GT source view.
A target is source-compatible if the two source-ref sets intersect.

### 9.3 Source rows and fusion

Add one strict `OpeningSourceScoreRowV1` for every target/claim/relevant input:

```text
target_id, target_kind, claim
source_input_id, channel
eligible_units
result = complete | within_tolerance | miss | conflict | not_applicable
na_reason
matched_observation_ids
expected coordinate/interval
observed coordinate/interval
error metric/value/tolerance
applicability certificate reference
```

Target-level claim rows are then fused deterministically from source rows:

- only trusted-filtered source rows → target claim NA with the source capability
  reason(s);
- a trusted-frame, product-content, or product-coordinate-ambiguity NA component → an
  eligible miss row plus the separate component NA/witness; it does not become a
  zero-unit NA row;
- eligible rows and no product observation → miss;
- agreeing passing rows → best passing class;
- passing and miss from independent positive sources → conflict;
- trusted-negative conflict remains governed by Va;
- a source NA never votes and never becomes an inferred absence.

Policy criteria consume source rows:

- `window_plan_geometry`: plan along + width;
- `window_elevation_geometry`: elevation along + width + sill + head;
- `windows_placed`: fused target existence, with source rows available for audit;
- reading `host`: explicit NA;
- appearance: explicit NA.

This removes the current acknowledged debt where fused along/width is omitted from the
elevation criterion.

## 10. Total NA/rejected behavior

### 10.1 Stable NA reasons

Top-level reasons:

- `unsupported_reading_contract`
- `unsupported_gt_profile`
- `unsupported_view_contract`
- `no_scorable_reading_channel`
- `scorer_internal_failure`

Component reasons:

- `reading_view_missing`
- `reading_view_schema_unsupported`
- `plan_frame_unavailable`
- `plan_geometry_unsupported`
- `plan_opening_geometry_unsupported`
- `elevation_opening_geometry_unsupported`
- `elevation_vertical_datum_unsupported`
- `elevation_floor_partition_unresolved`
- `elevation_local_x_sense_disagreement`
- `multiple_plan_views_per_floor_unsupported`
- `normalization_identity_unresolved`
- `judge_coordinate_identity_unresolved`
- `judge_support_registration_ambiguous`
- `judge_opening_assignment_ambiguous`
- `reading_topology_unavailable`
- `reference_value_unavailable`
- `unsupported_target_kind`
- `unresolved_absence_coverage`

No reason string contains exception text, file order, or arbitrary product prose.

### 10.2 Error classification

| Failure owner | Result |
|---|---|
| Product envelope/view/geometry cannot be interpreted by this scorer | NA |
| Product has zero observations after successful interpretation | scored, normally misses |
| Judge's tolerance/assignment has multiple valid answers | affected component NA |
| Trusted GT/manifest/binding hash or schema mismatch | rejected judge request |
| GT-side identity/conservation certificate fails | rejected judge request |
| Unexpected `Exception` in normalization/matching/policy/render preparation | top-level NA `scorer_internal_failure`; stack logged and count incremented |
| `KeyboardInterrupt`, `SystemExit` | not caught |
| Atomic artifact persistence failure | infrastructure exception after rollback |

The totalizer catches `ScoreContractError` and maps it through an explicit table; it
does not classify by message text. Any unmapped `ScoreContractError` becomes
`scorer_internal_failure`, not a crash.

`run_profile` is passed through the existing run policy; it is never inferred from a
path name. The existing strict set is exactly `{"golden", "regression"}`.
`exploratory` and the existing non-strict `dev` profile emit one warning for an
internal failure, write the NA artifacts, increment
`visibility_counts.scorer_internal_failures`, and continues to later attempts. Golden
and regression perform the same deterministic artifact construction/commit, then
raise `TopLevelNotApplicableError(reason)`; the exception contains only the stable
reason. This same post-commit fail-closed rule applies to every top-level NA in those
two profiles, not only internal failures.

### 10.3 Result production

`score_typed_attempt_total` always returns `TypedScoreResult` once raw bytes and trusted
score inputs are loadable. For NA/rejected results it:

1. builds the full identity available at that phase;
2. includes component applicability in the payload;
3. renders the deterministic existing NA/rejected board path;
4. finalizes and atomically commits the sidecar/PNG pair; and
5. exposes criteria by a payload-kind-safe helper.

The grading loop handles every attempt independently. One attempt's NA cannot prevent
later attempts from being graded in exploratory mode. Golden/regression intentionally
stop after committing a top-level NA artifact.

## 11. Run-stage, CLI, cache, and rendering

### 11.1 Run-stage

In `_grade_typed_attempt_artifacts`:

- parse raw JSON into a total contract decision;
- never default a schema;
- reading attempts continue regardless of accepted state, as required by F7;
- correction's accepted-six-artifact restriction stays unchanged;
- load and validate judge inputs;
- call the total score service;
- commit scored, NA, or rejected artifacts;
- obtain criteria through `score_criteria_for_payload(payload)`;
- return score/grade paths for NA as well as scored results.

The loop catches only failures that occur before a total result can exist (for example
unreadable trusted sidecars) and routes them through the same typed rejected/NA
assembler where possible. It does not silently return `None` for a v3 reading
measurement failure.

### 11.2 CLI

The primary CLI input is the aggregate reading `output.json`. It calls exactly the
same detector, adapter, service, and artifact commit functions as run-stage.

Automatic flat-reading dispatch is removed. The old `--typed-elevation-json`
hand-built contract is not a production format and is rejected as
`unsupported_reading_contract`; no compatibility mode is added in this batch. It is
never selected by run-stage or by missing-key defaults.

CLI exit semantics:

- exploratory/dev scored or top-level NA measurement result: exit 0 after writing
  artifacts;
- golden/regression scored result: exit 0; top-level NA commits artifacts then exits
  2 through `TopLevelNotApplicableError`;
- rejected trusted-input request: exit 2 after writing artifacts;
- artifact persistence failure: exit 2.

### 11.3 Cache

A cache hit requires strict equality of the full v9 identity, sidecar validation, and
PNG hash. At minimum the following changes invalidate cache:

- output bytes;
- reading contract detector/helper version;
- normalized observation coordinates;
- any plan/vertical/elevation transform;
- source applicability/ambiguity result;
- base/effective/score manifest;
- binding;
- GT;
- tolerances; or
- renderer/helper schema.

Old v8 is always a cache miss for v9.

### 11.4 Renderer

The coordinate grade consumes normalized certificate coordinates; it does not
re-normalize raw reading JSON. It adds a compact channel-status panel. Unsupported
components are labeled `N/A: <stable reason>`, never shown as zero hits. A top-level NA
board includes all component reasons. The sidecar remains authoritative; pixels are an
aid. Every board prints the exact first-class
`unmeasurable_observations` count plus the five named `visibility_counts`, including
zeroes. Therefore a rect wall, nonzero plan origin, vertical convention fallback,
multiple-plan-floor NA, local-x disagreement, or swallowed exploratory internal
failure cannot be visually silent.

Expose the panel's pure text source as
`reading_grade_status_lines(payload) -> tuple[str, ...]`; the renderer draws those
exact strings. The first six count lines are exactly
`Unmeasurable observations: N`, `Nonzero plan origins: N`,
`Project-convention vertical datums: N`, `Multiple-plan floor components: N`,
`Elevation local-x disagreements: N`, and `Scorer internal failures: N`.
Tests assert these strings before separately asserting that the PNG is emitted, so
render visibility is not inferred from sidecar presence alone.

## 12. Construction slices: RED locks first

For every slice, land the listed tests in a tests-only commit, run them against current
code, and record the exact RED output before implementation. A test that errors only
because its new production symbol is absent must be paired with a behavioral test
against an existing entry point. After the slice turns green, perform the named neuter
in a disposable worktree and record which lock turns red. Do not retain neuters.

### Slice 0 — reproduce and lock the real boundary

Land these locks before production. Items 1–6 are the acceptance spine and therefore
precede broader unit coverage:

1. `test_real_views_attempt_reaches_typed_total_service` invokes
   `_grade_typed_attempt_artifacts` on a temporary copy of real attempt 003 and expects
   a typed score or reasoned NA sidecar/PNG. It never derives a product coordinate
   from GT. Current RED: `elevation_observations_not_list`. This proves F2/F3/F9 at the
   real boundary and is the required genuine `{"views":...}` E2E.
2. `test_reading_contract_is_not_inferred_from_missing_schema` exercises the detector
   matrix and captures the real run-stage product identity. Current RED: the detector
   symbol is absent and the runner supplies `"3"`. This proves the F8 guard is not a
   permanently true product-schema check.
3. `test_product_geometry_bytes_cannot_change_denominator` sends byte-distinct normal
   and mutated products under identical trusted inputs. The second product has every
   stroke geometry malformed and every elevation `local_x_positive`/`mirrored`
   declaration flipped. It requires byte-identical denominator
   preimages/outputs/hashes plus distinct normalization, unmeasurable, and
   frame-disagreement evidence. Current RED: the real envelope crashes and no
   denominator certificate exists. This is the blocking U-13 pure-function lock.
4. `test_rect_wall_is_per_stroke_unmeasurable_and_counted` changes exactly one real
   plan wall line to a rect, keeps the other strokes, and requires the plan component
   applicable, exactly one `plan_wall_rect_has_no_centerline_contract` witness,
   `payload.unmeasurable_observations == 1`, unchanged denominator bytes, and grade
   board count `1`. Current RED: the payload/count/certificate fields do not exist
   (the real envelope currently crashes first). This proves U-05 is per-stroke rather
   than whole-component NA.
5. `test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness` requires
   North/West elevation xy+z trusted-frame NA/retain-as-miss, East/South free of that
   reason, exactly two witnesses containing the raw declarations, visible count `2`,
   denominator bytes identical to a product whose declarations agree, and eligible
   North/West miss rows. Current RED: no reading adapter/applicability/witness exists.
   This is the blocking U-10/D-2 lock.
6. `test_correction_public_judgment_sha_matches_pre_v9_baseline` runs the existing
   correction-v3 fixture and requires schema 9 plus exact pre-construction
   `public_rows` and `wall_criteria` byte hashes. Current RED: current output is schema
   8. Any changed public judgment byte remains RED after v9 lands. This is the
   blocking U-03 before/after proof and records `blocking_change=false` only when both
   hashes match.
D-1 maintenance in this tests-first commit is not presented as a RED scoring lock:
rename the existing GT-echo test so it says parity, add the required one-line comment,
and preserve its byte-parity assertion unchanged.

Neuters:

- restore the `"3"` default → lock 2 red;
- restore the tuple default for missing elevation observations → lock 1 red;
- let any product geometry or facade declaration filter reference atoms → lock 3 red;
- make one rect wall invalidate the component → lock 4 red;
- silently project North/West with the binding → lock 5 red;
- mark North/West NA but filter their targets → locks 3 and 5 red;
- change a correction public row/criterion value → lock 6 red;

### Slice 1 — contract detector, v9 wire, and total result

Tests:

1. strict detector table for object/list/missing/flat/real envelopes;
2. capability decision rejects unrecognized reading and accepts only
   `reading_views_v1`;
3. component applicability validator distinguishes applicable-zero from NA-zero;
4. normalization/source certificate hashes change for every score-affecting field and
   are order-invariant after canonical sort;
5. v8 cache is a miss, exact v9 is a hit, altered certificate is a miss;
6. stable error mapping: product shape→NA, trusted identity→rejected, unexpected
   exception→internal NA;
7. scored/NA/rejected result variants all render and round-trip strictly.
8. `test_product_invalid_plan_frame_is_na_but_denominator_retained` removes the
   structured plan origin and requires product-content NA plus unchanged denominator
   misses;
9. `test_supported_empty_plan_component_is_scored_as_miss` requires
   applicable-zero plus real target misses;
10. `test_reading_score_error_does_not_abort_later_attempts_in_exploratory` injects an
    internal adapter exception, requires a counted/warned NA artifact, then requires
    the later attempt's artifacts;
11. `test_na_payload_never_reads_c2_only_member` routes top-level NA through the real
    caller without unconditional C2-field access;
12. golden/regression commit each top-level NA artifact and then fail closed.

Current RED defects proved: there is no reading guard (F1), schema identity is guessed
(F8), v8 cannot carry channel reasons/certificates, and result callers assume C2.

Neuters:

- make the detector accept flat `"schema_version":"3"` → detector lock red;
- remove NA-reason nonempty validation → applicability lock red;
- omit normalization hash from score identity → cache lock red;
- map an unexpected exception to re-raise → totality lock red.
- replace product-content NA with trusted filtering → lock 8 red;
- turn applicable-zero into NA → lock 9 red;
- remove per-attempt exploratory totalization → lock 10 red;
- read a C2-only member unconditionally → lock 11 red;

Stop after Slice 1 and re-read this cumulative specification before geometry
construction.

### Slice 2 — elevation `ReadingView` adapter

Tests:

1. real sm24 elevation views consume canonical `x_range_m/y_range_m` and produce one
   certified observation per visible window stroke;
2. each repeated raw stroke ID (for example `S3` in different views) produces a unique
   normalized ID;
3. East/South coordinates project through the reviewed binding with exact expected
   intervals;
4. North/West local-x disagreement produces input-scoped xy+z NA plus exact raw
   witnesses; changing an agreeing declaration to disagree makes NA, never a second
   numerical interpretation;
5. no `facade_segment_id` is required in reading JSON;
6. a source with zero window strokes is applicable and its observable targets miss;
7. a missing/malformed product elevation view is explicit product-content NA while its
   denominator remains/misses; a missing trusted binding filters both positive and
   negative source capability;
8. product-declared and project-convention one-floor vertical certificates are
   distinct and counted; multi-floor is trusted-filtered NA;
9. line/rect/polyline bounds and degenerate point observations follow §8.2;
10. unique assignment scores coordinates; assignment ambiguity returns source NA.

Current RED defects proved: no production shape adapter exists (F3/F5); the current
normalizer requires flat rows and an invented segment ID; missing keys have misleading
shape errors.

Neuters:

- read `x_range/y_range` instead of canonical metre keys → test 1 red;
- ignore product/binding local-x sense disagreement → test 4 red;
- omit input ID from observation identity → test 2 red;
- treat supported-zero as NA → test 6 red;
- reintroduce required `facade_segment_id` → test 5 red.

### Slice 3 — plan affine adapter and topology-neutral scoring

Tests:

1. real sm24 structured plan frame produces the exact affine certificate and projected
   endpoints without parsing `note`;
2. changing only structured origin translates every world endpoint and changes
   certificate/cache identity;
3. changing only free prose changes output hash/audit identity but not projection;
4. missing/invalid product frame yields both plan components NA with retained
   denominator/misses, never implicit identity or trusted filtering;
5. wall line and polyline decompose exactly; closed behavior is pinned; each rect wall
   is excluded/counts once without invalidating other strokes;
6. supported zero wall strokes produce target misses;
7. matched/missed target rows derive exterior/interior from GT; generic extras have no
   invented topology;
8. plan line and rect window examples register and expose along/width coordinates;
9. plan host rows are NA `reading_topology_unavailable`, not falsely complete from
   judge registration;
10. an observation eligible for multiple support lines makes the floor component NA;
11. multiple plan inputs per floor are trusted-filtered per component and visibly
    counted;
12. nonzero structured origins are explicitly counted on sidecar and grade board;
13. static import test proves adapter/GT imports remain judge-only.

Current RED defects proved: `scale_origin` has no consumer (F6), coordinates are
currently taken as world implicitly, reading observations default exterior, and host
topology is absent.

Neuters:

- bypass `apply_affine_2d` → translation lock red;
- parse a number from free `note` → prose-independence lock red;
- restore `exterior=True` default as observation truth → topology lock red;
- turn frame NA into empty observations → supported/unsupported pair red;
- use judge-selected boundary as a complete product host → host lock red.

### Slice 4 — capability-filtered Va and source/channel scoring

Tests:

1. trusted-filtered source claim is absent from both positive and negative Va
   decisions;
2. supported empty source remains in the reference ledger and yields misses;
3. product-content plan NA plus elevation-applicable retains plan claims as misses and
   scores elevation claims;
4. trusted-filtered elevation NA plus plan-applicable scores plan geometry and makes
   filtered elevation claims NA;
5. source input ID and GT view ID mapping works when names differ (`1f_view` versus
   `plan-F1`);
6. multiple GT source IDs in one binding use set intersection, not first-entry choice;
7. source rows expose plan and elevation along/width independently;
8. target fusion conflict/NA/miss precedence is denominator-conserving;
9. trusted-filtered source negative completeness cannot create conflict or extra;
10. matcher ambiguity downgrades only the certified affected component while retaining
    its denominator as misses;
11. normal versus all-malformed products have byte-identical denominator preimage,
    bytes, and hashes but different unmeasurable evidence;
12. correction-v3 public rows and wall criteria retain the pinned pre-v9 byte hashes.

Current RED defects proved: the current reference ledger has no cause-split capability
mask, NA and applicable-zero cannot be distinguished, source IDs are conflated,
along/width are fused away from elevation criteria, ambiguity raises, and no
geometry-independent denominator certificate exists.

Neuters:

- leave trusted-filtered negative claims in score manifest → tests 1/9 red;
- let product-content causes remove any denominator byte → the U-13 lock red;
- compare input ID directly to GT ref ID → test 5 red;
- drop channel from source rows → test 7 red;
- turn ambiguity into sorted-first assignment → test 10 red.

### Slice 5 — run-stage, CLI, renderer, cache, and live J0

Tests:

1. real attempt 003 through run-stage emits a strict sidecar and PNG whose payload is
   scored or reasoned NA, never an exception;
2. CLI and run-stage on the same aggregate bytes emit byte-identical sidecar/PNG;
3. every reading attempt is graded independently; correction nonaccepted behavior is
   unchanged;
4. NA result paths appear in the judge packet with machine-readable reasons;
5. cache invalidates for transform, applicability, helper, binding, and output changes;
6. old flat reading payload is explicitly unsupported without automatic compatibility;
7. protected sm24 GT tree hash is byte-identical;
8. renderer labels NA and prints the exact unmeasurable/nonzero-origin/vertical-
   fallback/multi-plan/local-x/internal-failure counts, never displaying a
   trusted-filtered component as zero-hit false red;
9. current existing test assertions listed in §13.3 are preserved or changed only
   under the documented C8 rationale;
10. exploratory/dev top-level NA commits and exits normally; golden/regression
    top-level NA commits then fails closed;
11. correction before/after public hashes are equal and the execution record says
    `blocking_change=false`.

Current RED defects proved: production uses the flat test contract, CLI has a separate
typed-elevation input, run-stage crashes/assumes scored payload, and there is no
certificate-aware cache/render path.

Neuters:

- route CLI through its former separate normalizer → parity lock red;
- omit applicability from judge packet → NA packet lock red;
- remove certificate from cache identity → cache lock red;
- make NA renderer use empty score rows → false-red render lock red.

After Slice 5:

1. use `affected_tests.py` for the deterministic affected subset;
2. run the full repository once;
3. run live sm24 J0;
4. compare the protected-tree hashes;
5. write the required execution log; and
6. stop for controller review. Do not continue the downstream sm24 acceptance run in
   this batch without a separate instruction.

## 13. Files, compatibility, and C8 test discipline

### 13.1 Expected production file ownership

New:

- `src/agent/judge/reading_typed_adapter.py`
- `tests/test_reading_typed_adapter.py`
- `tests/test_reading_typed_score_integration.py`

Modified:

- `src/agent/judge/score_schema.py`
- `src/agent/judge/score_service.py`
- `src/agent/judge/score_inputs.py`
- `src/agent/judge/segment_score.py`
- `src/agent/judge/opening_claim_score.py`
- `src/agent/judge/score_policy.py`
- `scripts/tool_scripts/run_stage.py`
- `scripts/tool_scripts/score_reading_vs_gt.py`
- `scripts/tool_scripts/render_grade.py`
- affected score/render/run-stage tests

No change is expected in:

- `src/agent/reading/schema.py`
- gate ① validators
- reading skills/guides
- any GT file or signed review artifact.

If construction discovers that a producer/gate schema change is required, stop; it is
scope expansion, not an adapter implementation detail.

### 13.2 Existing behavior preserved

- v2 GT remains on the legacy path.
- correction v3 still requires the accepted B5 artifact bundle and verified proof.
- correction extraction, coordinate identity, tolerance, Va/Vg, and policy semantics
  remain unless v9 field adaptation requires a shape-only change.
- reading attempts, accepted or not, continue to the scorer.
- no automatic StageVerdict is introduced.

### 13.3 Ruled treatment of existing assertions

C8 forbids rewriting tests to fit implementation. Exactly two existing test edits are
authorized, with their substantive assertions preserved:

1. `tests/test_c2_b4b_phase_d.py::_typed_attempt_payload` manufactures flat reading
   `segments/openings/elevation_observations`, including GT-derived coordinates and a
   facade segment ID. This fixture remains valid for its actual purpose: run-stage ↔
   CLI byte parity. Keep the parity assertion, add a one-line comment saying the
   fixture echoes GT and measures transport parity only, and rename the test so it
   cannot be read as a reading-scoring E2E. Do not delete or weaken it. Add a separate
   real `{"views": ReadingView}` E2E using attempt 003 bytes and no GT-derived product
   coordinates.
2. That parity test's sidecar assertion migrates from `"8"` to `"9"` when v9 lands.
   This is a shape/version correction only. Its sidecar/PNG byte-parity and artifact
   validity assertions remain. Independently, the correction fixture's canonical
   `public_rows` and `wall_criteria` bytes are pinned before construction and must have
   identical SHA-256 values after migration.

No other current assertion may be weakened. If a new failure requires changing one,
record it separately with the exact false premise and obtain controller approval.

## 14. Final resolved boundaries — normative, none remain open

These 15 boundaries were under-specified by the initial brief. They are now final
construction requirements, not assumptions or choices left to an executor:

### U-01 — Plan local→world authority

Use strict structured `scale_origin.world_x_m/world_y_m` plus the metre/right/up
contract in an explicit replaceable `PlanFrameCertificateV1`. Ignore free-text `note`;
never fall back to implicit identity. Missing/malformed fields make plan
product-content NA with retained denominator. Count and render every exact nonzero
origin.

### U-02 — Elevation vertical datum and floor ownership

Use the three-way `VerticalDatumCertificateV1`: a finite non-null product
`world_z_m`; otherwise `z=local_y+0` from the 2026-07-25 project convention “grade
line = interior floor ±0.000”; or trusted-filtered NA for a multi-floor binding. Hash
and visibly count convention fallback. Invalid non-null product data is z-component
product-content NA with retained denominator; never infer a floor or fit GT.

### U-03 — Score wire version and correction blast radius

Write strict sidecar v9/artifact-contract v2; treat v8 as a cache miss and never hide
new semantics in free-form criteria. For correction, v9 is pure-additive: canonical
`public_rows` and `wall_criteria` bytes and SHA-256 values must equal their
pre-construction v8 baseline. Delivery records both before/after hashes and
`blocking_change=false`; one changed byte blocks acceptance.

### U-04 — NA granularity

Capability is per trusted input and per component, then applied per claim. Downgrade
only the affected component. A top-level NA exists only when every component
disposition filters; product-content NA retains denominator/misses and therefore
still produces a scored payload with visible component NA.

### U-05 — Plan wall rects

A wall rect has no centerline contract. Exclude that stroke alone from coverage and
extra matching, append one witness, increment the first-class
`unmeasurable_observations` payload field, and render it. Keep the plan-segment
component applicable, score other strokes, and count uncovered targets as misses. One
rect must never kill the whole ruler.

### U-06 — Plan openings and host

Project line/rect/polyline vertices and perform one-way global target assignment. Do
not require or invent `facade_segment_id`. Reading host claims are always
`not_applicable/reading_topology_unavailable`.

### U-07 — Elevation non-rect windows

Use finite x/y bounds for line and polyline as well as rect. Score degenerate finite
intervals normally. Malformed consumed geometry makes the affected input components
product-content NA but cannot filter their denominator.

### U-08 — Source identities

Keep manifest `source_input_id` distinct from binding `gt_source_view_ids`. Target
compatibility uses set intersection; Va and source rows use the input ID. Never choose
the first GT source ID.

### U-09 — Multiple plan inputs per floor

In v1, trusted manifest/binding evidence of multiple plan inputs for one floor makes
that floor's plan components trusted-filtered NA. Do not union, best-of fuse, or charge
duplicates. Count every affected component visibly.

### U-10 — Product/binding local-x disagreement

The reviewed binding remains the sole coordinate transform. If effective product
`local_x_positive` or `mirrored` disagrees/is unknown, both elevation components for
that input are trusted-frame NA/retain-as-miss
`elevation_local_x_sense_disagreement`. Preserve both raw/effective product
declarations and both binding declarations in a witness and count it. Never project
both ways or use coordinate/GT plausibility to disambiguate. In real sm24,
East/South agree and North/West disagree; the latter two must be NA, not silently
mirrored. Because the disagreement is triggered by product bytes, North/West answer
targets stay in the denominator and score as misses; `trusted_frame` is reporting
granularity only and grants no filtering right.

### U-11 — Flat reading compatibility and the GT-echo test

Run-stage and the normal CLI reject the hand-built flat payload as
`unsupported_reading_contract`; no automatic or offline compatibility mode is added
in this batch. Preserve the existing GT-echo fixture's run-stage/CLI byte-parity
assertion, label and rename it as parity-only, and add a separate real
`{"views":...}` E2E with no GT-derived product coordinates.

### U-12 — Plan topology and extras

Only target topology classifies target-backed rows as exterior/interior. Unmatched
product strokes are generic extras with `target_exterior=None`. Never infer a product
exterior flag.

### U-13 — Cause-split denominator control

Only causes computed exclusively from trusted GT/manifest/bindings may filter mapped
positive and negative reference capability. Product-side causes—including U-10 frame
disagreement, malformed/missing views, origins, strokes, ranges, and rect wall
exclusions—must retain the denominator and produce misses; coordinate-dependent judge
ambiguity also retains it. The mandatory normal-versus-mutated lock changes every
geometry and flips `facade.local_x_positive`/`mirrored`, yet requires byte-identical
denominator preimages, atoms, and hashes while proving normalization, unmeasurable, and
frame-disagreement evidence differs.

### U-14 — Failure taxonomy and profile behavior

Product/capability and judge ambiguity become reasoned component NA; corrupt trusted
identity/conservation becomes rejected; unexpected exceptions become loud top-level
`scorer_internal_failure`, with stable sidecar reason, count, warning, and stack only
in judge logs. Exploratory/dev commit and continue. Golden/regression commit the
artifact then fail closed.

### U-15 — NA process and CLI behavior

Always write a deterministic NA sidecar and PNG. Exploratory/dev return normally and
CLI exits 0 so gate ② can judge the evidence. Golden/regression commit then raise/exit
2 for every top-level NA. Partial component NA inside a scored payload is not a
top-level process failure.

## 15. Reproducible probes and verification commands

Every empirical number quoted here or inherited into construction has a command below.
Protocol constants and schema version numbers are design values, not measurements.

### 15.1 Real attempt shape and stroke counts

This reproduces the real view IDs, per-view counts, pen counts, and consumed geometry
keys. It is the source for the brief's plan `15` strokes/`13` dimensions and for the
elevation observation fixture count.

```bash
python - <<'PY'
import json
from collections import Counter
from pathlib import Path

p = Path("case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("top_keys", sorted(d))
stroke_owners = {}
for key, view in d["views"].items():
    strokes = view.get("strokes", [])
    for stroke in strokes:
        stroke_owners.setdefault(stroke.get("id"), []).append(key)
    print(
        key,
        "kind=", view.get("image_kind"),
        "strokes=", len(strokes),
        "dimensions=", len(view.get("dimensions", [])),
        "pens=", sorted(Counter(s.get("pen") for s in strokes).items()),
        "geometry_keys=", sorted({
            (s.get("pen"), tuple(sorted((s.get("geometry") or {}).keys())))
            for s in strokes
        }),
    )
print("repeated_stroke_ids", sorted(
    (stroke_id, owners)
    for stroke_id, owners in stroke_owners.items()
    if len(owners) > 1
))
PY
```

### 15.2 GT target kinds, floors, and reviewed bindings

```bash
python - <<'PY'
import json
from collections import Counter
from pathlib import Path

gt = json.loads(Path(
    "case_tests/test_baseline/gt/sm24_anchor/gt.json"
).read_text(encoding="utf-8"))
bindings = json.loads(Path(
    "case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json"
).read_text(encoding="utf-8"))
print("floors", [
    (f["id"], f.get("z_floor_m"), f.get("ceiling_height_m"))
    for f in gt["floors"]
])
print("opening_kinds", sorted(Counter(o["kind"] for o in gt["openings"]).items()))
for b in bindings["bindings"]:
    print(
        b["kind"], b["input_id"],
        b.get("floor_id", b.get("floor_ids")),
        b.get("facade_family"), b.get("world_axis"),
        b.get("sign"), b.get("along_origin"),
        b.get("gt_source_view_ids"),
    )
PY
```

### 15.3 D-2 local-x declarations and U-02 vertical-datum facts

This reproduces all four elevation comparisons, including the two `sign=-1`
North/West disagreements, and all five null product z origins:

```bash
python - <<'PY'
import json
from pathlib import Path

b = json.loads(Path(
    "case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json"
).read_text(encoding="utf-8"))
r = json.loads(Path(
    "case_tests/e2e_tests/sm24_anchor/"
    "run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json"
).read_text(encoding="utf-8"))
for item in b["bindings"]:
    if item.get("kind") != "elevation":
        continue
    product = (r["views"].get(item["input_id"]) or {}).get("facade") or {}
    print(
        item["input_id"], item["local_x_positive"], item["sign"],
        "|", product.get("local_x_positive"),
    )
print("world_z_m")
for key, view in r["views"].items():
    print(key, (view.get("scale_origin") or {}).get("world_z_m"))
PY
```

### 15.4 F1/F2/F6/F8/F9 static probes

```bash
rg -n \
  'stage == "correction"|product_schema|product_artifact_contract|return CapabilityDecisionV8' \
  src/agent/judge/score_schema.py
rg -n \
  'product_payload.get\\("segments"|payload.get\\("openings"|elevation_observations' \
  src/agent/judge/score_service.py
rg -n 'scale_origin' src scripts tests skills case_tests
rg -n 'output.get\\("schema_version", "3"\\)' \
  scripts/tool_scripts/run_stage.py scripts/tool_scripts/score_reading_vs_gt.py
```

### 15.5 Protected sm24 tree

Take the before snapshot before Slice 0 and the after snapshot after Slice 5. These
commands write only `/tmp`, never the protected tree.

```bash
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 \
  | sort -z | xargs -0 sha256sum \
  > /tmp/reading_typed_scoring_sm24_before.sha256

test "$(find case_tests/test_baseline/gt/sm24_anchor -type f | wc -l)" -eq 14

# after construction
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 \
  | sort -z | xargs -0 sha256sum \
  > /tmp/reading_typed_scoring_sm24_after.sha256
cmp /tmp/reading_typed_scoring_sm24_before.sha256 \
    /tmp/reading_typed_scoring_sm24_after.sha256
```

### 15.6 Test commands

For each slice, supply the actual changed paths; run the exact pytest command printed
by the repository tool:

```bash
python scripts/tool_scripts/affected_tests.py --changed \
  src/agent/judge/reading_typed_adapter.py \
  src/agent/judge/score_schema.py \
  src/agent/judge/score_service.py \
  scripts/tool_scripts/run_stage.py \
  tests/test_reading_typed_adapter.py \
  tests/test_reading_typed_score_integration.py \
  --explain
```

Final full run reproducing the controller's stated baseline comparison:

```bash
python -m pytest -p no:cacheprovider -q
```

The brief's starting baseline is `1786 passed / 10 xfailed / 0 failed`; construction
must record the final numbers rather than copying that expectation.

### 15.7 Correction public-judgment before/after proof

The Slice 0 test serializes each projection with
`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` plus
one trailing LF. `public_rows` is the object with exactly
`segment_rows`, `segment_extras`, `claim_rows`, `claim_summaries`, and `extras`;
`wall_criteria` is the ordered score-criterion subset whose IDs are
`walls_complete`, `boundary_complete`, `no_extra_walls`, and
`no_duplicate_wall_strokes`. The test prints both SHA-256 values under `-s`; run it
before any v9 production change and after Slice 5:

The pre-construction v8 fixture hashes captured on 2026-07-31 are:

```text
public_rows.before_sha256=ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
wall_criteria.before_sha256=65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
```

```bash
python -m pytest -p no:cacheprovider -q -s \
  tests/test_reading_typed_scoring_slice0.py \
  -k correction_public_judgment_sha_matches_pre_v9_baseline
```

The execution log must record:

```text
public_rows.before_sha256=<hex>
public_rows.after_sha256=<same hex>
wall_criteria.before_sha256=<hex>
wall_criteria.after_sha256=<same hex>
blocking_change=false
```

### 15.8 Diff/scope proof

```bash
git status --short
git diff -- AI_agent/proposals/reading_typed_scoring_plan_sol.md
git diff -- src tests skills case_tests
```

The protected paths and parallel-seat exclusions must remain empty in the final diff.
Existing unrelated untracked request files are not to be altered.

## 16. Acceptance checklist

- [ ] Every final §14 boundary is implemented exactly.
- [ ] Reading capability is based on a detected contract, never default `"3"`.
- [ ] Real aggregate reading bytes are the integration fixture.
- [ ] Plan and elevation use their distinct, certified projection mechanisms.
- [ ] No free-text transform parsing exists.
- [ ] No product facade segment, room, host, or exterior flag is invented.
- [ ] Applicable-zero and NA-zero tests both exist and fail under opposite neuters.
- [ ] Trusted-filtered sources create neither positive nor negative evidence.
- [ ] Product-content failures retain denominator bytes and targets miss.
- [ ] Normal/all-malformed product geometry has byte-identical denominator preimage,
      bytes, and hashes.
- [ ] Every excluded/malformed product stroke increments the first-class
      `unmeasurable_observations` field and the board displays it.
- [ ] North/West sm24 elevation components are NA with raw two-sided local-x witnesses;
      East/South are not; North/West targets remain as eligible misses.
- [ ] Vertical project-convention fallback and nonzero plan origins are certified,
      counted, and rendered.
- [ ] Coordinate rows expose plan walls and plan/elevation windows separately.
- [ ] Every ambiguity is certified NA, never sorted-first.
- [ ] One failed reading attempt cannot abort later attempts or downstream flow.
- [ ] NA/rejected callers never assume a C2 payload.
- [ ] CLI and run-stage call one service and produce identical artifacts.
- [ ] v9 cache identity covers both certificates and every transform.
- [ ] Correction `public_rows` and `wall_criteria` before/after SHA values are
      byte-identical and `blocking_change=false`.
- [ ] No gate ①/execution import of GT is introduced.
- [ ] Protected sm24 tree hashes compare byte-for-byte.
- [ ] Every Slice has recorded current RED, GREEN, and named neuter evidence.
- [ ] Affected subset and one final full suite are recorded.
- [ ] Live sm24 J0 ends in a score or loud NA, never a crash.

## 17. Review ask

No boundary remains open and no ruling conflicts with another. Construction should be
reviewed most closely at four invariant-touching seams:

1. the denominator constructor must be byte-independent of all product bytes,
   including local-x/mirror declarations;
2. product-content and trusted-frame-reporting NA must remain visible while producing
   retained-denominator misses; only trusted-input-only NA filters;
3. v9 must not change one correction public-judgment byte; and
4. no plan calibration, multi-floor vertical partition, host/topology, or numerical
   local-x disambiguation may be invented.

Any implementation pressure to violate one of those seams is a stop condition, not a
builder choice.
