# A1 — Coordinate normalization

Deterministic transforms over the typed evidence graph defined in `A0`: bring
every primitive into one world frame, express wall axes at centerline, and
reconcile the z-stack. Ambiguous inputs escalate to `A3`; A1 never guesses.

```
Consumes:        A0 evidence items (numeric coordinate + topology_identity);
                 perception frames (plan_local, facade_local); known wall thickness
Produces:        all geometry in one world frame; centerline wall axes; reconciled z-stack
Emit corrections[] when: a coordinate's frame is converted, a face coordinate is
                 moved to its wall centerline, or a z value is reconciled
Emit conflicts[] / unsupported when: frame/origin ambiguous, wall side / thickness
                 basis unknown, or facade–plan orientation conflicts
                 → reference_or_identity_ambiguity / facade_plan_mismatch → A3
May change topology: no  (frame / centerline / z only; A1 does not merge or split entities)
```

Applies under **all** method profiles.

---

## 1. World coordinate system

- A single world frame. Origin = the SW inner corner of the overall projected
  maximum boundary. **No per-floor local origins.**
- All output coordinates in meters, world frame.

## 2. Local → world transforms

### 2.1 Plan
Apply the plan's origin offset / rotation to bring `plan_local` coordinates into
the world frame.

### 2.2 Facade (elevation)
- Horizontal axis → the facade's world axis (x for North/South, y for East/West).
- `y_local` (height) → world z **directly**; do not add a per-floor offset on top
  (the elevation already carries absolute height).
- Facade orientation is fixed by the facade's world plane. If the declared
  orientation conflicts with the plan position, emit `facade_plan_mismatch`
  (claim_type `topology_identity`) → A3; do not silently re-orient.

## 3. Z-stack and floor-height reconciliation

- Per floor: `z_top = z_floor + ceiling_height`; the next floor's `z_floor`
  equals this floor's `z_top` (contiguous stack).
- On a shared horizontal boundary, lower-zone ceiling z **==** upper-zone floor z;
  carry the single shared value.
- Derive heights from an elevation's total + segment chains. If two derivations
  disagree beyond `DIMCHAIN_CLOSE_TOL`, emit `checksum_failure` → A3 — do not
  split the difference.

## 4. Centerline convention

All wall axes are expressed at the wall **centerline** in the world frame.

- Drawings mix conventions (interior walls often traced at the inner face,
  exterior walls at centerline). Convert a face coordinate to centerline using
  the wall's **measured** thickness.
- The coordinate shift is a `correction` with `claim_type = numeric`; the
  "which side / what thickness" decision rests on `topology_identity` evidence.
- A `prior` wall thickness (from `A4`) may be used **only** when measurement is
  absent, and must be logged with `prior_id`.
- Escalation: unknown wall side, no thickness basis, or conflicting origin →
  `reference_or_identity_ambiguity` → A3. Do not guess a centerline.

## 5. Out of scope for A1

A1 does **not** cluster/merge axes across floors, close gaps, quantize, or change
topology — those are `A2`.
