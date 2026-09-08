---
name: sm_16 multi-floor plan input upgrade
description: Per-floor plan images (Floor plans schema A) with shared exterior footprint hard constraint; setbacks deferred to next iteration
type: project
originSessionId: 558457b8-7c96-4523-af67-88667e5b0f81
---
sm_16 (2026-04-29) introduces per-floor plan input support to EnergyPlus-Agent geometry phase.

**Why:** Real buildings often have different internal partitioning per floor (sm_16 uses 7/8/4 zones across F1/F2/F3) but share the same exterior footprint. Single `top_view.png` couldn't express this.

**How to apply:**
- testdata_prompt.json schema A: `"Floor plans": [{"floor": k, "path": "{k}f_view.png", "thermal_zones": int}, …]`. Legacy single `Top view path` field still accepted (treated as shared plan).
- Hard constraint encoded in skill prompts (§D3.1 invariant): every floor's outer chain must give the same `W × D` (≤0.01 m tolerance). Setbacks / cantilevers / atria are **out of scope** this iteration — flag and ask the user if exterior outlines disagree.
- Internal partitioning is per-floor: `xs_f, ys_f` are independent arrays per floor; `create_zone` must loop per floor with that floor's own boundaries.
- Skill files updated: [skills/energyplus_mcp/energyplus_mcp_prompt.md](../../../../Desktop/科研2/EnergyPlus-Agent-dev/skills/energyplus_mcp/energyplus_mcp_prompt.md), [skills/energyplus_mcp/zonetool_prompt.md](../../../../Desktop/科研2/EnergyPlus-Agent-dev/skills/energyplus_mcp/zonetool_prompt.md). open_model variant deliberately not touched (Opus-only this iteration).
- Backup before edits: `Skill_history/2026-04-29_energyplus_mcp_pre_multifloor/`.
- intake.py prepends each image with `[Next image] <label>` derived from filename regex (`{k}f_view` / `{dir}_view` / `top_view` / `supp_plan`).
- Setbacks / multi-footprint support: deferred to sm_17+; will need to revisit §D3.1 invariant and global-origin definition.
