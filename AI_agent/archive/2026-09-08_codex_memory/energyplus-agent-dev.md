# EnergyPlus-Agent-dev — user-confirmed direction and handover memory

Recorded: 2026-09-07 UTC. Workspace: `/workspaces/EnergyPlus-Agent-dev`.
Source: direct discussion with the user in Codex thread `01a07c5e-2434-7761-a6eb-6c7e3ea00884`.
Status: decisions accepted by user; implementation and project-management synchronization await handover.

## 1. Timing, ownership and authorization

- Claude is currently completing a full case run. Wait for that run to finish before taking over development.
- At handover: inspect actual outputs and outstanding changes/worktrees, make a suitable backup, then proceed according to the agreed goals. Preserve concurrent work; do not reset or overwrite Claude's changes.
- The user explicitly asked to save this discussion in Codex's own project memory first. Do not yet edit `AI_agent/CLAUDE.md`, `plan.md`, architecture documents or other shared management documents to impose the new direction.
- Once the handover occurs, synchronize those documents with the user's current decisions. Historical statements such as "主控恒 Claude", BEM-only scope, or mandatory completion of the old C2 batch must not be mistaken for the user's current strategic intent.
- Before handover, the user authorizes private memory writes, minimal model-family connectivity tests, model-capability/pricing research and sensible quota-aware delegation planning. No geometry refactoring or new case run is authorized yet.
- Current root session was verified from local turn metadata as `gpt-6-astra`, effort `xhigh`. User wants Astra to delegate sensibly rather than doing everything itself.

## 2. Core research and product goal

- Core artifact: a generic lightweight building information/geometry model, called "丐版 BIM" by the user.
- EnergyPlus is the first downstream simulation plugin. Later adapters may support daylight, acoustics, airflow and other building simulations.
- Final deliverable remains a stable, usable multi-agent harness/product. This is not merely a paper experiment or a one-off strong-model demonstration.
- Different agents can use configurable models, allowing users to trade quality against cost. Establish measured baselines for model configurations and input conditions.
- Research asks: given input information, model capability and run budget, how much fidelity can be achieved? Increased fidelity is accepted as useful; do not spend the main research effort proving its value.
- Intended use: early-stage, quick, comparatively detailed simulation/reference models. No requirement to replace formal engineering acceptance simulations or reproduce measured real-world building energy consumption.

## 3. Model constraints: production vs development

- Production/runtime targets: local-deployment-class models and Flash-class models. User examples are Qwen 27B-class and DeepSeek V4 Flash-class; exact deployed model IDs/versions still need checking when running experiments.
- Sonnet-class is the accepted runtime upper tier. Do not make models above that tier a hidden requirement for planning, interpretation, repair or judging within the production workflow.
- All runtime models are to be called through APIs initially, even models that could eventually be deployed locally. Offline deployment and hardware provisioning are not present prerequisites.
- Lower cost/capability is desirable, but there is no requirement to start with the lowest possible model.
- Target models must participate from the first experiments. The earlier assistant proposal "SOTA first, weak models only later" was explicitly rejected by the user.
- Development team is separate from production model ceilings. Latest user preference (2026-09-07): reserve GPT quota primarily for Astra and minimize calls to other GPT models (Sol/Terra/Luna). Delegate reasoning tasks to Claude Opus where appropriate, and use Claude, GLM and DeepSeek for other development tasks. Other GPT models remain available for exceptional needs, not routine default delegation. Development use of Opus does not raise the production/runtime ceiling above Sonnet class.
- Multi-agent is an explicit deliverable. Role count, boundaries, tools and repair loops should be informed by failures and measured results; do not preserve complexity solely because it already exists.

## 4. Scope: geometry first, collaborator owns physical properties

- Our principal task is getting the building geometry right.
- Another collaborator is implementing physical-property attachment and the user says that work is largely done. Do not reopen it as a new major workstream based on older DRAFT documents found in the repository.
- It is acceptable to attach the same physical-property configuration to generated models for EP connectivity checks and controlled geometry comparisons.
- Preserve room/space information in the source artifact. Initial EP mapping may be room-to-zone without thermal-zone merging.
- Thermal zoning/merging is a downstream derivation, not a prerequisite for generating the shared building artifact. Other simulation modules may need the original rooms and partitions.

## 5. Input routes and sequencing

### Route A: reconstruction from complete drawings
- Initial inputs are complete plans and elevations, like sm24/sm25.
- Aim for faithful building/room reconstruction, making good use of supplied dimensions and views.
- The July 7 experiments are valid evidence that target-class models with tools can achieve high drawing-reading fidelity on those cases. Do not restart the discussion by arguing that this fidelity is impossible or unnecessary.
- Preserve useful measurements and workflow lessons from those runs without treating their exact schemas, per-case preparation or old guardrails as permanent requirements.

### Route B: exterior geometry plus image skin
- Input is a 3D exterior geometry model plus images/textures, which may be incomplete; Google Earth-like is the user's scenario, not an instruction to download restricted data.
- Use the supplied geometry directly and infer plausible interior structure using available facade evidence and building context.
- Preserve the distinction between observed geometry and inferred internal layout. A detailed generated interior is not proof of recovering the unique actual hidden interior.
- Can progress in parallel as a bounded prototype sharing geometry representation and viewer with Route A; Route A remains the immediate main acceptance route.

### Later: arbitrary mixed input
- Once both routes work reasonably, support mixtures such as exterior model plus partial plans plus natural-language descriptions (dual cores, large central atrium, etc.).
- Design for new evidence to refine relevant assumptions and preserve reliable existing information; surface contradictions rather than regenerating everything blindly.
- Do not require unrestricted mixed-modal input support before the first two routes are usable.

## 6. Human participation and manual-view

- Human participation is allowed and is a product feature: interactive information completion, direct visual geometry changes and natural-language modifications.
- Before simulation there should be a checkpoint to inspect, supplement and modify the model, then confirm and continue.
- Existing code: `scripts/tool_scripts/render_geometry_viewer.py` generates a self-contained HTML viewer with orbit/zoom, transparency, clipping, floor/zone explosion, picking, measurement and PNG capture.
- Existing flow: `scripts/tool_scripts/run_stage.py` renders `<run>/manual_review/geometry_viewer.html` and supports geometry confirmation/resume.
- Existing proposal: `AI_agent/proposals/editable_geometry_confirmation.md` (2026-06-19, DESIGN/DEFERRED). Window movement, wall push/pull and write-back are proposed, not already implemented. Natural-language geometry editing is part of the user's newer, broader goal.
- Editing should update authoritative source geometry, rebuild affected derived geometry, validate and refresh the viewer. Editing only the displayed mesh would not update simulations.
- Direct and natural-language actions should share geometry operations. Distinguish source-building partition edits from simulation-only thermal-zone grouping.
- Preserve automatic and human-assisted outputs separately for evaluation; record added information, intervention count and time. Human-assisted results are legitimate, but must not be reported as unattended automation.

## 7. Accepted lightweight BIM scope and thickness decision

The user accepted the common foundation proposed after reviewing primary simulation documentation:

- Rooms/spaces with geometry, floor/height and basic semantics.
- Boundary faces with types, orientation and relations to the two sides; retain shared physical partition identity across derived per-room faces.
- Windows, doors and unfilled openings with hosts, shape, position and connected spaces/outdoors.
- Space adjacency and actual connectivity; physical partitions must be distinguishable from virtual computational boundaries.
- Independent scene/context geometry such as overhangs, balconies, significant obstacles and neighboring buildings, which need not form zones.
- Optional thickness, reference-plane offsets and reveal depth; record whether coordinates represent inner face, outer face or a reference/middle plane.
- Stable object references and source/assumption/user-edit information sufficient for updates and inspection. Do not turn this into a broad proof/signature infrastructure project.

Keep the surface-based core. Full solid walls are not a universal requirement and must not become the next prerequisite for progress.

Distinguish:
1. Construction-layer thickness used by physical solvers: can be attached later.
2. Geometric effects such as net room dimensions, window inset/reveal depth and shading: require explicit geometry or parameters from which adapters can create it.
3. Detailed local component cross-sections/solid domains for thermal bridges and similar tasks: specialized extensions, not mandatory full-building detail.

Common geometry is suitable as a base for energy, daylight, geometrical room acoustics and multizone airflow. CFD, smoke and egress require derived flow/navigation geometry and additional scene/connectivity inputs. Local heat bridges, detailed hygrothermal sections and structural analysis require extra specialized information. Do not claim all downstream integrations are already validated.

Key exporter issue: EP parent face plus subsurface is not automatically a ray-tracing-ready model. Radiance export needs the opaque wall punched for openings; airflow and egress need connections. "Adding a door rectangle" alone is insufficient.

## 8. Evaluation and engineering priorities

- Existing cases were hand-designed by the user for capability tests. Real drawings and additional inputs can be obtained later.
- Known designed geometry and manual reference models are valid geometric evaluation references; measured energy consumption is not required.
- Evaluate fidelity by dimensions, envelope/openings, spatial topology and completeness, alongside run success, manual effort, total model cost and time.
- Controlled EP comparisons can use identical physical assignments on generated and reference geometries. Do not label Ideal Loads heat/cold demand as actual electricity consumption.
- Vary supplied information and model/agent configurations; keep withheld answers out of producer input.
- Route A emphasizes reconstruction error; Route B also needs consistency with observed constraints and plausibility of inferred interiors. Hidden-layout exact match is not the sole criterion for reasonable completion.
- Reuse deterministic geometry, split/pairing, converters, visualization and measurement tools. Fix concrete failures and production disconnections first.
- Avoid millimeter-level convergence, exhaustive defensive tests, historical byte identity and old batch/debt closure becoming default research blockers. Keep useful geometric correctness checks and regression tests proportionate to real changes.
- Do not replace the requested stable multi-agent harness with a single SOTA prompt. Do not over-split tasks so target models lose necessary building context.

## 9. Primary references from the geometry requirements review

- EnergyPlus, Wall Thickness: https://energyplus.readthedocs.io/en/v25.1.0/essentials/essentials.html#wall-thickness
  Explicitly separates zero-thickness surface geometry from construction thickness; property changes do not update zone geometry/shading automatically.
- Honeybee common model: https://www.ladybug.tools/honeybee-core/docs/honeybee.model.html
- Honeybee punched face geometry: https://www.ladybug.tools/honeybee-core/docs/honeybee.face.html#honeybee.face.Face.punched_geometry
- Radiance primitives/thin glass: https://radsite.lbl.gov/radiance/refer/ray.html
- ODEON room modelling: https://odeon.dk/learn/odeon-manual/
- NIST CONTAM: https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887.pdf
- CFD geometry/meshing: https://doc.cfd.direct/openfoam/user-guide-v12/snappyhexmesh
- THERM cross-sections: https://windows.lbl.gov/therm-software-downloads
- WUFI 2D: https://wufi.de/en/software/wufi-2d/

## 10. Development model channels and live probes

- Historical channel guide: `AI_agent/guides/codex_execution_protocol.md`. Read operational details, but use current user decisions over obsolete project strategy/ownership rules.
- GLM launcher: `scripts/glm_code.sh`; default in file is `glm-5.3`, with per-run model override.
- DeepSeek launcher: `scripts/deepseek_code.sh`; default in file is `deepseek-v4-pro`, light model `deepseek-v4-flash`.
- Both launchers inject existing credentials only into child processes. Never export their Anthropic-compatible endpoint settings globally or expose credentials.
- DeepSeek shares a metered balance with the pipeline. Keep probes tiny and check available budget before long development jobs.
- GPT native collaboration probes on 2026-09-07: `gpt-5.6-luna` low returned `LUNA_OK`; `gpt-5.6-terra` low returned `TERRA_OK`; `gpt-5.6-sol` low returned `SOL_OK`.
- Claude/GLM/DeepSeek probes completed successfully on 2026-09-07 through existing CLI channels, run by a Terra sub-agent and independently read back by Astra:
  - Claude requested `sonnet`, CLI reported primary model `claude-sonnet-5`, response `CLAUDE_OK`, 3068 ms. Usage metadata also included `claude-haiku-4-5-20251001`; this was not a separate direct Haiku probe.
  - GLM requested/reported `glm-5.3`, response `GLM_OK`, 2028 ms.
  - DeepSeek requested/reported `deepseek-v4-flash`, response `DEEPSEEK_OK`, 2931 ms.
- Persistent probe summary: `/root/.codex/memories/energyplus-agent-dev-model-probes-2026-09-07.json`. Original external-family summary: `/tmp/ep-agent-model-probes-20260907-szqa6E/results.json` (temporary, may be removed later).
- External probes used isolated temporary working directories, safe mode, no available tools and no session persistence. No project code/management documents or credential configurations were changed. CLI cost estimates were not treated as real provider costs.
- Text probe success establishes connectivity only, not visual perception, tool execution, quality, long-job stability or remaining quota.
- Current development allocation, corrected by the user after the connectivity probes: Astra owns direction, major decisions and integration; Opus can handle reasoning and difficult analysis; Sonnet and GLM can implement bounded cohesive changes and provide independent reviews; Haiku/Flash/DeepSeek can handle suitable extraction and repetitive tasks. Minimize Sol/Terra/Luna usage to preserve the shared GPT quota for Astra. Adjust assignments to actual task performance and available quota; do not impose elaborate review chains on every small task. The earlier default proposal to delegate routinely to Terra/Luna/Sol is superseded.
- Latest researched routing and quota notes: [2026-09-07 model routing](energyplus-agent-dev-model-routing-2026-09-07.md). Current official GLM rules supersede old 3x peak records; GLM and DeepSeek now both have half-rate off-peak schedules with different peak windows. Claude requires checking five-hour and weekly shared capacity. User permits preflight quota/balance checks for large jobs and asking them to decide material allocations. Routine small jobs do not need repeated approval. No new model calls, account quota queries or scheduler installation occurred during this research.
