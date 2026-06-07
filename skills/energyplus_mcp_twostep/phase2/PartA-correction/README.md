# PartA — Correction layer

The correction layer turns perceived geometric primitives (possibly noisy or
self-contradictory) into a clean, self-consistent, simulation-friendly set,
and records every material change. It is the **first sub-stage of phase2** (the
vector-JSON → IntakeOutput node), ahead of zoning and geometry build:

```
phase1 perception → [ PartA correction → zoning → geometry build ]phase2 → surface matching → EnergyPlus
```

## Documents (read in order)

| doc | type | concern |
|---|---|---|
| `A0_contract.md` | spine | tolerances, evidence model, audit schema, validation schema, method profiles, upstream input contract — referenced by all others |
| `A1_coordinate_normalization.md` | deterministic (over typed evidence) | world frame, local→world, z-stack, centerline convention |
| `A2_regularization.md` | deterministic (over typed evidence) | canonical axis sets, snapping, dimension-chain closure, quantization, sliver prevention |
| `A3_arbitration.md` | judgment | conflict arbitration, completion, prior usage, unsupported policy |
| `A4_priors.md` | data | architectural commonsense priors (advisory) |

## Runtime (staged, with feedback)

```
A1 → A2-detect → A3-resolve (+A4) → A2-apply → validate
```

A1/A2 are deterministic only over an already-typed evidence graph; ambiguous
inputs escalate to A3. A4 is advisory data, never a self-acting corrector.

## Every document starts with a header block

```
Consumes:        <input fields this doc reads>
Produces:        <output fields this doc may write>
Emit corrections[] when: <...>
Emit conflicts[] / unsupported when: <...>
May change topology: yes | no
```
