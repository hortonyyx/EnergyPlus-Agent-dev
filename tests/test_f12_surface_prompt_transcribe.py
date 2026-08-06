"""F-12 lock: surface/fenestration system prompts must command the downstream
LLM to TRANSCRIBE vertices verbatim from surface_specs / fenestration_specs
(the kernel already computed them), not RECOMPUTE them from zone_specs'
z_floor/ceiling_height or from a window-to-wall ratio (WWR).

Background (see AI_agent/logs/reviews/request/2026-08-06_f12_surface_prompt_transcribe_dispatch_claude.md):
`SURFACE_SYSTEM_PROMPT` used to command the LLM to re-derive every wall
vertex's Z from `zone_specs.z_floor` / `ceiling_height`, even though
`surface_specs` already carries the complete, kernel-correct, CCW-from-
outside vertex polygon for every surface (src/agent/geometry/specs.py
`_fmt_verts`). That mismatch made the LLM re-derive a different vertex
order/start-point than the deterministic kernel emitted, which
`_vertex_drift_issues` (src/validator/output_coordinates.py:816, exact
positional equality) then rejected as VERTEX_FRAME_DRIFT on every real run.

These assertions are pinned to the SPECIFIC old defect wording (not vague
keywords) so that reverting the prompt to its pre-fix form is guaranteed to
flip them red — see the neuter check in the execution log for a live replay
of that flip.
"""

import re

from src.agent.nodes.fenestration import FENESTRATION_SYSTEM_PROMPT
from src.agent.nodes.surface import SURFACE_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# surface.py
# ---------------------------------------------------------------------------


def test_surface_prompt_instructs_verbatim_transcription_from_surface_specs():
    """Positive: the prompt must explicitly tell the LLM surface_specs already
    carries the authoritative vertices and to transcribe them verbatim."""
    assert re.search(
        r"transcribe.{0,40}verbatim.{0,40}surface_specs",
        SURFACE_SYSTEM_PROMPT,
        re.IGNORECASE | re.DOTALL,
    ), "prompt must instruct verbatim transcription from surface_specs"

    # The explicit prohibition on using zone_specs to compute vertex Z.
    assert re.search(
        r"do not use zone_specs.{0,60}z_floor.{0,60}ceiling_height.{0,60}compute",
        SURFACE_SYSTEM_PROMPT,
        re.IGNORECASE | re.DOTALL,
    ), "prompt must explicitly forbid deriving vertex Z from zone_specs"


def test_surface_prompt_does_not_command_z_floor_arithmetic():
    """Negative: must NOT contain the old "compute z from zone_specs" recipe.

    These three patterns are pinned to the exact defect wording that shipped
    before F-12 (see backup/src_history/2026-08-06_f12_surface_prompt_transcribe/
    surface.py.orig) — each one individually reproduced the defect on the old
    prompt text and does NOT match generic vocabulary like "z_floor" appearing
    in an unrelated, safe sentence.
    """
    # "bottom z = z_floor of that zone"
    assert not re.search(
        r"bottom\s+z\s*=\s*z_floor", SURFACE_SYSTEM_PROMPT, re.IGNORECASE
    ), "surface prompt must not command bottom-z = z_floor arithmetic"

    # "top z    = z_floor + ceiling_height of that zone"
    assert not re.search(
        r"top\s+z\s*=\s*z_floor\s*\+\s*ceiling_height",
        SURFACE_SYSTEM_PROMPT,
        re.IGNORECASE,
    ), "surface prompt must not command top-z = z_floor + ceiling_height arithmetic"

    # Workflow step 3's old phrasing: "using zone_specs' per-zone z_floor +
    # ceiling_height for vertex z"
    assert not re.search(
        r"using\s+zone_specs.{0,40}z_floor.{0,40}ceiling_height.{0,40}for\s+vertex\s+z",
        SURFACE_SYSTEM_PROMPT,
        re.IGNORECASE | re.DOTALL,
    ), "surface prompt must not instruct using zone_specs z_floor/ceiling_height for vertex z"


def test_surface_prompt_ccw_instruction_says_already_ccw_not_rederive():
    """The CCW-ordering rule must say the order is ALREADY correct in
    surface_specs (transcribe as-is), not command the LLM to independently
    determine/derive CCW-from-outside order itself."""
    assert re.search(
        r"already\s+CCW-from-outside", SURFACE_SYSTEM_PROMPT, re.IGNORECASE
    ), "prompt must state surface_specs' vertex order is already CCW-from-outside"
    # The bare old imperative ("Order counter-clockwise when viewed from
    # OUTSIDE the zone.") with no reference to surface_specs already having
    # solved it must be gone.
    assert not re.search(
        r"^-\s*Order counter-clockwise when viewed from OUTSIDE the zone\.\s*$",
        SURFACE_SYSTEM_PROMPT,
        re.IGNORECASE | re.MULTILINE,
    ), "prompt must not leave a bare re-derive-CCW-yourself instruction"


# ---------------------------------------------------------------------------
# fenestration.py
# ---------------------------------------------------------------------------


def test_fenestration_prompt_instructs_verbatim_transcription():
    assert re.search(
        r"transcribe.{0,60}verbatim",
        FENESTRATION_SYSTEM_PROMPT,
        re.IGNORECASE | re.DOTALL,
    ), "fenestration prompt must instruct verbatim vertex transcription"


def test_fenestration_prompt_does_not_command_wwr_derivation():
    """Negative: must NOT contain the old "derive from WWR + parent wall
    corners" instruction. Pinned to the exact old defect phrase structure
    (see backup/.../fenestration.py.orig) so a generic mention of "WWR" inside
    a *prohibition* sentence (which the fixed prompt legitimately has) does
    not trip this lock."""
    assert not re.search(
        r"derive\s+vertex\s+coordinates\s+from\s+the\s+parent\s+wall.{0,60}corners.{0,60}WWR",
        FENESTRATION_SYSTEM_PROMPT,
        re.IGNORECASE | re.DOTALL,
    ), "fenestration prompt must not command deriving vertex coords from WWR + parent wall corners"

    # Also forbid the standalone WWR-ratio-derivation sentence in any form:
    # "window-to-wall ratio ... derive" with derive AFTER window-to-wall
    # ratio and not negated.
    assert not re.search(
        r"window-to-wall ratio[^.]*;\s*derive", FENESTRATION_SYSTEM_PROMPT, re.IGNORECASE
    ), "fenestration prompt must not chain WWR mention directly into a derive instruction"
