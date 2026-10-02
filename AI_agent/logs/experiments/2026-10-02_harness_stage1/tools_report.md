# Frozen BIM tools: stage 1 classification

The catalog comes from a real stdio launch of the `run_bim_agent.py serve`
registration at frozen baseline `5bb10538`. An image-only run exposes 42
coordinator tools and 13 local-observer tools. A run whose admitted manifest has
`mesh_input` exposes seven additional coordinator tools and five additional
local-observer tools: 49 and 18 respectively. The transport follows every
`tools/list` page and rejects repeated cursors and duplicate names.

The classification is based on implementation effects, not merely whether a tool
is absent from the server's `--readonly` mode:

| Class | Count | Meaning in this adapter |
| --- | ---: | --- |
| `read_only` | 23 base; 29 with mesh | Does not modify source BIM or persistent workflow decisions. It may append the legacy audit log or create a replaceable view/measurement cache. |
| `idempotent_write` | 0 | The frozen protocol provides no stable operation key and server-side duplicate-application contract. |
| `non_idempotent_write` | 19 base; 20 with mesh | Creates or changes a candidate, claim, inference/audit, review, calibration, continuation decision, or delivery selection. A lost reply therefore stops the run without retry. |

The 13 tools in both the coordinator and local-observer catalogs are
`get_bim_reference`, `inputs`, `view_image`, `pixel_profile`,
`view_pixel_profile`, `view_pixel_region_overview`, `view_pixel_region`,
`preview_space_trace`, `view_space_trace`, `select_space_trace`,
`map_dimension_chain`, `compare_facade_spans`, and `map_pixels`.

Ten coordinator-only tools are also classified as reads after implementation
inspection: `inspect_inference`, `inspect_plan_draft`,
`view_plan_wall_support`, `view_claim_evidence`, `claim_status`,
`check_wall_dimensions`, `inspect_candidate`, `read_candidate_items`,
`inspect_parametric_plan`, and `view_candidate`. Some create rendered images,
measurement sidecars, or append `tools.jsonl`; those observational files are
included in stop artifacts but excluded from source-state recovery snapshots.
They do not edit a candidate or create a decision consumed as model state.

The 19 non-idempotent writes are `record_inference`,
`audit_inference_candidate`, `revise_plan_bim`, `record_claim`,
`replace_claim_sources`, `decide_claim`, `confirm_claims`,
`check_source_space_relation`, `check_openings`, `record_work_review`,
`finish_bim`, `overlay_candidate`, `revise_bim`, `review_detail`,
`build_plan_bim`, `assemble_plan_bim`, `build_parametric_bim`,
`build_bim`, and `view_elevation_candidate`. The check tools in this group
persist reviews or audits that affect later status, coverage, or replay, so they
remain writes even though they do not edit source BIM.

Mesh admission adds `inspect_mesh`, `inspect_mesh_directions`, `view_mesh`,
`measure_mesh_pixels`, and `view_mesh_observation` to both roles. It adds
`set_candidate_mesh_frame` and `overlay_mesh_candidate` to the coordinator.
The first five are observations; their saved render/evidence sidecars are the
same disclosed read-side effect as image views. `overlay_mesh_candidate` also
only creates a replaceable inspection projection. `set_candidate_mesh_frame`
creates a new candidate and is therefore a non-idempotent write.
The two role definitions whitelist the union of their legitimate conditional
tools. The live catalog still contains only the variant selected by `inputs.json`;
an image-only request never sends mesh definitions to the model, while a mesh
request is checked against the 49/18 hashes before its first model request.

`review_detail` stays visible with its exact frozen name, description, and
schema. Phase 1 never executes it because its implementation launches another
image model. The adapter returns a normal MCP-style error envelope with
`status=blocked` and `failure_stage=before_execution`; this records a known
policy refusal instead of an unknown write outcome.

## Byte evidence

The base files `coordinator_tools.json` and `local_observer_tools.json`, plus
`coordinator_mesh_tools.json` and `local_observer_mesh_tools.json`, retain the
exact JSON-compatible definitions returned by all four live MCP variants under `tools`.
`definition_sha256_by_name` hashes each complete definition, including name,
description, input schema, output schema, annotations, and any future fields.
`definitions_sha256` hashes the complete ordered definition list using the
documented UTF-8 canonical JSON encoding. Policy is stored separately under
`policy_by_name`, so adding the classification cannot silently change a
definition.

`material_manifest.json` gives the UTF-8 byte count and SHA-256 of both system
prompts and every exact reference string. It also binds the source files that
produce them and register tools to their frozen byte hashes. Export refuses to
claim the frozen baseline if any of those source bytes differ.

The drawing prompt is generated exactly as
`build_guide(images="drawings", mesh=False)`. The mesh prompt is generated as
`build_guide(images="mesh_views", mesh=True)`. At runtime, preserve the original
runner selection with
`build_guide(images=image_kind if images else None, mesh=bool(mesh))`.

## Launch example

```python
from pathlib import Path

from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client
from src.harness_contracts.budget import BudgetAmounts

run_directory = Path("path/to/prepared/run")
async with frozen_bim_client(run_directory) as client:
    tools = FrozenBimTools(
        client,
        coordinator_role(BudgetAmounts(calls=20)),
        run_directory=run_directory,
    )
    definitions = await tools.list_tools()
```

The generic `McpToolClient` knows only `command`, `args`, `cwd`, and
`run_directory`. The building-specific `serve RUN [--readonly]` command is
assembled only by `frozen_bim_client`.

## Offline validation evidence

The final tool-package test used the following exact shell command. `-n0` means
zero xdist workers: pytest ran in one main process. It did not make provider or
model calls.

```bash
find AI_agent/logs/experiments/2026-10-02_harness_stage1/.tmp/pytest -depth -delete 2>/dev/null || true; mkdir -p AI_agent/logs/experiments/2026-10-02_harness_stage1/.tmp/pytest_related && TMPDIR="$PWD/AI_agent/logs/experiments/2026-10-02_harness_stage1/.tmp" PYTHONDONTWRITEBYTECODE=1 pytest -n0 -s --basetemp="$PWD/AI_agent/logs/experiments/2026-10-02_harness_stage1/.tmp/pytest_related" tests/test_runtime_frozen_tools.py tests/test_agent_runtime.py tests/test_harness_core_contracts.py tests/test_stage1_behaviour.py tests/test_bim_agent_guidance.py
```

Observed result: `69 passed in 21.15s` after collecting 69 tests:

| File | Collected and passed | Relationship to this tool work package |
| --- | ---: | --- |
| `tests/test_runtime_frozen_tools.py` | 8 | Tool-package tests, including both live base catalogs, both live mesh catalogs, hashes, role policy, MCP pagination, startup cleanup, images, artifacts, and blocked delegation. |
| `tests/test_agent_runtime.py` | 24 | Runtime-loop tests from the runtime work package; not modified by this tool work package. |
| `tests/test_harness_core_contracts.py` | 24 | Existing stage-0 core-contract regression tests; not modified by this tool work package. |
| `tests/test_stage1_behaviour.py` | 7 | Behaviour-report tests from its separate work package; not modified by this tool work package. |
| `tests/test_bim_agent_guidance.py` | 6 | Existing frozen-runner guidance regressions; not modified by this tool work package. These directly cover drawing/photo/unknown prompt selection, mesh prompt selection, manifest routing, and frozen reference placement. |

This 69-test invocation was observed in the development command result but was
not piped to a standalone log file. The stage-wide final ten-file run is saved
separately as `pytest_final.log`; it is not duplicated here.
