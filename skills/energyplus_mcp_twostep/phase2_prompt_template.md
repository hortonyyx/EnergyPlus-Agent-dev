# Phase 2 startup prompt (for the session path; paste directly into a new Claude Code session)

> Usage: in the `EnergyPlus-Agent-dev` project root, start a new Claude Code session (a capable
> model, e.g. Opus), and paste the block between the "---" markers below as the first message. The
> automated path is run by the script `Tool_scripts/run_phase2_deepseek.py` and does not use this
> prompt. Copy this template per new case and adjust the paths.

---

I am doing phase 2 of the two-step intake. Phase 1 (image → vector JSON) is done (products in
`phase1_vector/`). This session does only **phase 2: vector JSON → IntakeOutput** — no image,
pure text reasoning.

## Required reading

Read in order:

1. `phase2_rules.md` — full phase 2 rules (input/output / coordinate translation formulas /
   IntakeOutput field derivation order / naming rules / vertex synthesis / self-check)
2. `phase1_vector_schema.md` — phase 1 output format reference (only to understand what your input looks like)
3. `phase1_vector/phase1_summary.md` — phase 1 summary (includes the 4-facade local↔world translation formulas, **apply directly**)
4. the phase 1 vector JSONs (read as needed, not all):
   - `phase1_vector/1f_view.json`, `2f_view.json`, `3f_view.json`
   - `phase1_vector/South_view.json`, `North_view.json`, `East_view.json`, `West_view.json`
5. `testdata_prompt.json` — metadata (floor count, area, city, use)

## Task

Following the field derivation order in `phase2_rules.md` §3, produce the IntakeOutput Pydantic JSON, written to:

```
phase2_intake/<model>/intake_output.json
```

For the format, reference the IntakeOutput Pydantic definition in [src/agent/state.py](src/agent/state.py).
All 11 fields must be present: building / site_location / zone_specs / material_specs /
schedule_specs / construction_specs / surface_specs / fenestration_specs / hvac_specs / people_specs
/ lights_specs.

The 9 `*_specs` fields are **natural-language instructions** (not structured data), but must be
explicit, mechanically executable, and internally consistent — the 9 downstream subagents rely on
these strings. Naming rules are strict (letters/digits/`_` only, literally consistent across fields,
no template writing).

## Mental model

- You have already "seen the image" — all visual info is in the phase 1 JSON. **Do not go back to the original PNG**
- Any error tied to "a value in the image" is phase 1's fault (already frozen); you can only
  introduce pure reasoning errors (topology, naming, field format, coordinate translation)
- A `null` in the phase 1 JSON = "phase 1 didn't see it", **do not treat it as 0**; if missing,
  annotate accordingly in your output
- Elevation local coordinates must be translated back to the world system per the `phase1_summary.md`
  §3 formula, **do not re-derive**

## Workflow

1. Read the required docs (rules / schema / summary / testdata_prompt + sample a few JSONs)
2. Walk through phase2_rules §3 Step 1→7 mentally, confirm you are confident before writing
3. Write `phase2_intake/<model>/intake_output.json` — write it all at once, **do not append in multiple passes**
4. After writing, run the self-check (phase2_rules §7, 9 items) and write the result to `phase2_intake/<model>/self_check.md`
5. If phase2_rules does not cover something and you had to "improvise" to finish, record it in
   `phase2_intake/<model>/phase2_followup_notes.md` so the rules can be extended later

## Boundaries

- Do not modify any phase1_vector/ file (phase 1 products are frozen)
- Do not modify phase2_rules.md / phase1_vector_schema.md (put suggestions in phase2_followup_notes.md)
- Do not modify any file under [src/](src/) / [skills/](skills/) / [AI_agent/](AI_agent/)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not look at the original PNGs (phase 2 discipline)

When done, output three files: `intake_output.json` / `self_check.md` / `phase2_followup_notes.md` (if any).
