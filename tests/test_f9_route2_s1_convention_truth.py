"""F-9 route② v2.1 §10 S1 / §12.2 "Convention truth" lock.

S1 merges four independent copies of the North/South/East/West sign
convention (`facade.py::_CONVENTION`, `window_sources.py::_BASE_SIGN`,
`facade_applicability.py::_BASE_SIGN`, `judge/score_inputs.py::_BASE_SIGN`)
plus five hand-inlined `mirrored XOR (local_x_positive ==
"image_right_to_left")` sites into the single, gt-free
`src.agent.correction.facade_convention` module. It is a BEHAVIOR-PRESERVING
refactor (v2.1 §10 S1: "行为保持不变") — this file proves that with a
hand-written external truth table, never by calling the merged module (or
any of its former call sites) to generate its own expected values (dispatch
§3 rule).

Lock inventory (v2.1 §12.2 "Convention truth" row), reworked 2026-08-11 per
sol MAJOR-3 (AI_agent/logs/reviews/verdict/
2026-08-11_f22_f9s0s1_crossreview_sol.md) -- the original blacklist-only AST
lock missed `facade.py::derive_facade_frame` (a REAL live entry point,
`src/validator/checks/correction.py:355-365`), which computed the same sign
with two sequential negations, never calling `facade_convention.
resolve_sign`. That call site is now fixed (§3 below) and the lock itself
is reworked to a positive whitelist plus per-call-site dynamic mutation:

  1. 4 facade x 2 mirror x 2 local-direction hand-written expected (axis,
     sign, along_origin) -- checked against BOTH the shared module directly
     AND the real facade.py entry point, with non-zero lo/hi.
  2. "true"/"false"/"unknown" mirror-string boundary.
  3. Live-consumer structure lock, POSITIVE form: for each of the 6 real
     call sites, does its AST contain an actual
     `facade_convention.resolve_sign(...)` call? (Old blacklist checks --
     exact `_BASE_SIGN`/`_CONVENTION` names, literal `^` -- kept below as
     explicitly weak/supplementary; sol constructed an `AnnAssign` +
     `operator.xor` variant that bypasses them but not the whitelist check.)
  4. A real-path dynamic neuter for EACH of the 6 real call sites
     (`facade.py::derive_facade_frame`, `facade.py::
     derive_view_projection_frame`, `window_sources.py::
     _advisory_elevation_world_frame`, `window_sources.py::
     materialize_current_ring_va_elevation_bindings`,
     `facade_applicability.py::_validate_bindings`, `judge/score_inputs.py::
     validate_score_view_bindings`): monkeypatching `facade_convention.
     resolve_sign` changes what each one actually produces.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.agent.correction import facade_convention

# ---------------------------------------------------------------------------
# 1. Hand-written external truth table (v2.1 §12.2: "手写 4 facade × 2
#    mirror × 2 local-direction expected；lo/hi 非零").
#
# Derivation (by hand, NOT by calling any project code): looking at a facade
# from outside, not mirrored, image-x left-to-right:
#   North: world axis x, base_sign -1     South: world axis x, base_sign +1
#   East:  world axis y, base_sign +1     West:  world axis y, base_sign -1
# effective_flip = mirrored XOR (local_x_positive == "image_right_to_left")
# sign = -base_sign if effective_flip else base_sign
#
# The real vertex ring used against the live entry point is x in [2, 10],
# y in [3, 7] (both non-zero, non-degenerate), so along_origin (= lo if
# sign > 0 else hi) is provably exercised, not accidentally 0.
# ---------------------------------------------------------------------------
L2R = "image_left_to_right"
R2L = "image_right_to_left"

# (facade, mirrored, local_x_positive) -> (axis, sign, along_origin)
TRUTH_TABLE: dict[tuple[str, bool, str], tuple[str, int, float]] = {
    ("North", False, L2R): ("x", -1, 10.0),
    ("North", False, R2L): ("x", 1, 2.0),
    ("North", True, L2R): ("x", 1, 2.0),
    ("North", True, R2L): ("x", -1, 10.0),
    ("South", False, L2R): ("x", 1, 2.0),
    ("South", False, R2L): ("x", -1, 10.0),
    ("South", True, L2R): ("x", -1, 10.0),
    ("South", True, R2L): ("x", 1, 2.0),
    ("East", False, L2R): ("y", 1, 3.0),
    ("East", False, R2L): ("y", -1, 7.0),
    ("East", True, L2R): ("y", -1, 7.0),
    ("East", True, R2L): ("y", 1, 3.0),
    ("West", False, L2R): ("y", -1, 7.0),
    ("West", False, R2L): ("y", 1, 3.0),
    ("West", True, L2R): ("y", 1, 3.0),
    ("West", True, R2L): ("y", -1, 7.0),
}

assert len(TRUTH_TABLE) == 16  # 4 facade x 2 mirror x 2 local-direction, §12.2 totality


@pytest.mark.parametrize("key", sorted(TRUTH_TABLE))
def test_truth_table_against_shared_module(key):
    facade, mirrored, local = key
    expected_axis, expected_sign, _ = TRUTH_TABLE[key]
    assert facade_convention.world_axis(facade) == expected_axis
    assert facade_convention.resolve_sign(facade, mirrored=mirrored, local_x_positive=local) == expected_sign


RING = [(2.0, 3.0), (10.0, 3.0), (10.0, 7.0), (2.0, 7.0)]  # non-zero, non-degenerate


@pytest.mark.parametrize("key", sorted(TRUTH_TABLE))
def test_truth_table_against_real_entry_point(key):
    """Real entry point: `facade.py::derive_view_projection_frame`, not a
    private helper — this is the function every C2 Vg/Va live consumer
    actually calls (facade_applicability.py imports `ViewProjectionFrame`
    from this same module).
    """
    from src.agent.correction.facade import derive_view_projection_frame

    facade, mirrored, local = key
    expected_axis, expected_sign, expected_origin = TRUTH_TABLE[key]
    frame = derive_view_projection_frame(
        vertices=RING, facade_family=facade, mirrored=mirrored, local_x_positive=local,
    )
    assert frame.world_axis == expected_axis
    assert frame.sign == expected_sign
    assert frame.along_origin == expected_origin
    # lo/hi non-zero requirement (§12.2): along_origin must be a genuine ring
    # extreme, never an accidental 0.
    assert frame.along_origin != 0.0


# ---------------------------------------------------------------------------
# 2. "true"/"false"/"unknown" mirror-string boundary (v2.1 §6.2/§12.2).
# ---------------------------------------------------------------------------

def test_mirror_bool_passthrough():
    assert facade_convention.normalize_mirror_flag(True) is True
    assert facade_convention.normalize_mirror_flag(False) is False


def test_mirror_legacy_string_true_false():
    assert facade_convention.normalize_mirror_flag("true") is True
    assert facade_convention.normalize_mirror_flag("false") is False


@pytest.mark.parametrize("value", ["unknown", None, "True", "FALSE", "", 1, 0])
def test_mirror_unresolved_values_fail_closed(value):
    with pytest.raises(facade_convention.UnresolvedMirrorError):
        facade_convention.normalize_mirror_flag(value)


def test_resolve_sign_rejects_unresolved_mirror_type():
    # resolve_sign itself never accepts a string -- normalize_mirror_flag is
    # a separate, explicit step (v2.1 §6.2: caller must resolve first).
    with pytest.raises(TypeError):
        facade_convention.resolve_sign("North", mirrored="true", local_x_positive=L2R)


# ---------------------------------------------------------------------------
# 3. Live-consumer structure lock -- REWORKED per sol MAJOR-3
#    (AI_agent/logs/reviews/verdict/2026-08-11_f22_f9s0s1_crossreview_sol.md):
#    the original blacklist-style AST checks (exact `_BASE_SIGN`/`_CONVENTION`
#    variable names as `ast.Assign(value=ast.Dict)`, `ast.BinOp(BitXor)` for
#    XOR) missed `facade.py::derive_facade_frame`, which computed the SAME
#    sign with two sequential in-place negations -- no `^`, no dict literal,
#    nothing the blacklist could match, and it is a REAL live entry point
#    (`src/validator/checks/correction.py:355-365` calls it directly). sol
#    also constructed an `AnnAssign` + `operator.xor` + dead-import variant
#    that the old checks would have passed.
#
#    Fix: a POSITIVE, whitelist check -- does the target function's AST
#    contain an actual `Call` node shaped `facade_convention.resolve_sign(
#    ...)`? This is structurally immune to every equivalent-XOR rewrite (any
#    rewrite that computes the sign WITHOUT that literal call, by
#    definition, is exactly the defect this batch must catch), whereas a
#    blacklist can only ever catch the specific patterns someone thought to
#    enumerate. The old blacklist checks are kept below as weak,
#    EXPLICITLY-labeled supplementary checks (sol confirmed they still catch
#    a naive revert), not the primary lock.
# ---------------------------------------------------------------------------

_MERGED_CONSUMER_FILES = [
    Path("src/agent/correction/facade.py"),
    Path("src/agent/correction/window_sources.py"),
    Path("src/agent/correction/facade_applicability.py"),
    Path("src/agent/judge/score_inputs.py"),
]

# Every REAL call site sol/orchestrator identified: (file, function name).
# `derive_facade_frame` is included -- it was the actual gap.
REAL_CALL_SITES: list[tuple[str, str]] = [
    ("src/agent/correction/facade.py", "derive_facade_frame"),
    ("src/agent/correction/facade.py", "derive_view_projection_frame"),
    ("src/agent/correction/window_sources.py", "_advisory_elevation_world_frame"),
    ("src/agent/correction/window_sources.py", "materialize_current_ring_va_elevation_bindings"),
    ("src/agent/correction/facade_applicability.py", "_validate_bindings"),
    ("src/agent/judge/score_inputs.py", "validate_score_view_bindings"),
]


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in module")


def _calls_module_attr(func_node: ast.AST, module_name: str, attr_name: str) -> bool:
    """True iff `func_node`'s body contains a `Call` shaped
    `<module_name>.<attr_name>(...)` -- e.g. `facade_convention.
    resolve_sign(...)`. A POSITIVE requirement: it is defeated by NO
    equivalent-sign-computation rewrite, because any such rewrite that
    doesn't literally make this call is, by construction, exactly the
    "computes the same answer without going through the shared formula"
    defect this lock exists to catch.
    """
    for node in ast.walk(func_node):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr_name
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == module_name
        ):
            return True
    return False


@pytest.mark.parametrize("path_str,func_name", REAL_CALL_SITES, ids=[f"{p}::{f}" for p, f in REAL_CALL_SITES])
def test_real_call_site_positively_calls_shared_resolve_sign(path_str, func_name):
    path = Path(path_str)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    func_node = _function_node(tree, func_name)
    assert _calls_module_attr(func_node, "facade_convention", "resolve_sign"), (
        f"{path}::{func_name} does not contain a `facade_convention.resolve_sign(...)` "
        "call -- an equivalent-XOR rewrite (operator.xor, continued negation, a "
        "reintroduced local table, an AnnAssign, an alias) would compute the same "
        "numbers without going through the single shared formula, and this "
        "whitelist check is what catches that (a name/pattern blacklist cannot)"
    )


# --- weak, supplementary blacklist checks (kept per sol 4.2: they still --
# --- catch a naive full revert; NOT relied on as the primary lock) --------

def _assigned_names(tree: ast.AST) -> set[str]:
    """Weak: only ast.Assign to an exact dict literal with an exact name.
    Misses AnnAssign, dict(), aliasing -- see class docstring above.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Dict):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _has_xor_binop(tree: ast.AST) -> bool:
    """Weak: only the literal `^` operator. Misses `operator.xor(...)` and
    any non-XOR-shaped equivalent (e.g. continued negation) -- see class
    docstring above; `test_real_call_site_positively_calls_shared_resolve_sign`
    is the check that actually closes those gaps.
    """
    return any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitXor) for node in ast.walk(tree))


@pytest.mark.parametrize("path", _MERGED_CONSUMER_FILES, ids=lambda p: str(p))
def test_no_local_convention_table_reintroduced_weak_supplementary(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    reintroduced = _assigned_names(tree) & {"_BASE_SIGN", "_CONVENTION", "_AXIS"}
    assert reintroduced == set(), (
        f"{path} reintroduced a local convention dict {sorted(reintroduced)}; "
        "must import src.agent.correction.facade_convention instead"
    )


@pytest.mark.parametrize("path", _MERGED_CONSUMER_FILES, ids=lambda p: str(p))
def test_no_inline_xor_reintroduced_weak_supplementary(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not _has_xor_binop(tree), (
        f"{path} reintroduced an inline `^` mirror/local-direction flip; "
        "must call facade_convention.resolve_sign instead"
    )


def test_all_four_consumers_import_facade_convention():
    for path in _MERGED_CONSUMER_FILES:
        text = path.read_text(encoding="utf-8")
        assert "facade_convention" in text, f"{path} no longer imports the shared convention module"


def test_ast_blacklist_checks_are_provably_bypassable_by_a_renamed_table_variant():
    """Documents (does not merely assert) the exact SHAPE of gap sol found:
    the blacklist checks only ever match an EXACT, enumerated set of names
    (`_BASE_SIGN`/`_CONVENTION`/`_AXIS`) and the literal `^` operator, so
    ANY rewrite that avoids both -- a differently-named table (this test)
    or, as sol's own example showed, `operator.xor` instead of `^` -- slips
    through undetected. (Widening `_assigned_names` to also catch
    `AnnAssign` while reworking this lock, above, already closed sol's
    EXACT `AnnAssign`-with-the-old-names example; this test documents that
    the blacklist SHAPE -- exact enumerated names, exact operator syntax --
    remains bypassable in general, which is why the positive whitelist
    check below is the one this lock actually relies on.)
    """
    synthetic = ast.parse(
        "from src.agent.correction import facade_convention\n"
        "import operator\n"
        "_SIGN_TABLE: dict[str, int] = {'North': -1}\n"  # not in the blacklist's name set
        "sign = -_SIGN_TABLE['North'] if operator.xor(mirrored, rtl) else _SIGN_TABLE['North']\n"
    )
    assert not (_assigned_names(synthetic) & {"_BASE_SIGN", "_CONVENTION", "_AXIS"})  # blacklist misses it (wrong name)
    assert not _has_xor_binop(synthetic)  # blacklist misses it (operator.xor, not `^`)
    fake_func = ast.parse(
        "def f():\n"
        "    _SIGN_TABLE = {'North': -1}\n"
        "    sign = -_SIGN_TABLE['North'] if operator.xor(mirrored, rtl) else _SIGN_TABLE['North']\n"
    ).body[0]
    assert not _calls_module_attr(fake_func, "facade_convention", "resolve_sign")  # whitelist catches it


# ---------------------------------------------------------------------------
# 4. Real-path dynamic neuter for EVERY real call site (sol MAJOR-3: "对每个
#    真实 call site 都要有动态 mutation 验证"), not just one entry point and
#    not just "imports the module" for the rest.
# ---------------------------------------------------------------------------

def test_derive_facade_frame_is_really_wired_to_shared_resolve_sign(monkeypatch):
    """The call site sol found unwired. Real live entry point
    (`src/validator/checks/correction.py:355-365` calls this directly).
    """
    from src.agent.correction import facade as facade_module

    baseline = facade_module.derive_facade_frame(
        view_facade="North", footprint_x=[2, 10], footprint_y=[3, 7], mirrored="false",
    ).sign
    assert baseline == -1  # truth-table row (North, False, L2R)

    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: 1)
    mutated = facade_module.derive_facade_frame(
        view_facade="North", footprint_x=[2, 10], footprint_y=[3, 7], mirrored="false",
    ).sign
    assert mutated == 1
    assert mutated != baseline, (
        "mutating facade_convention.resolve_sign did not change facade.py's "
        "derive_facade_frame output -- the call site is not really wired to "
        "the shared module"
    )


def test_facade_entry_point_is_really_wired_to_shared_resolve_sign(monkeypatch):
    from src.agent.correction import facade as facade_module

    baseline = facade_module.derive_view_projection_frame(
        vertices=RING, facade_family="North", mirrored=False, local_x_positive=L2R,
    )
    assert baseline.sign == -1  # truth-table row (North, False, L2R)

    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: 1)
    mutated = facade_module.derive_view_projection_frame(
        vertices=RING, facade_family="North", mirrored=False, local_x_positive=L2R,
    )
    assert mutated.sign == 1
    assert mutated.sign != baseline.sign, (
        "mutating facade_convention.resolve_sign did not change facade.py's "
        "derive_view_projection_frame output -- the call site is not really "
        "wired to the shared module"
    )


def test_advisory_elevation_world_frame_is_really_wired(monkeypatch):
    """`window_sources.py`'s first real call site."""
    import json as _json

    from src.agent.correction import window_sources
    from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry

    entry = RequiredViewEntry(
        input_id="North_view", source_image="case_data/North_view.png", image_sha256="a" * 64,
        view_type="elevation", declared_direction_token="North",
        direction_source="user", direction_semantics="building_axis", semantics_source="standard_assumption",
        building_view_direction="North", dimensioned=True, expected_output_id="North_view",
        opening_evidence=OpeningEvidence(
            potentially_observable_claims=["existence", "along", "width", "sill", "head", "appearance"],
        ),
    )
    reading_bytes = _json.dumps({
        "image_kind": "elevation",
        "facade": {"view_facade": "North", "mirrored": False, "local_x_positive": "image_left_to_right"},
        "dimensions": [{"id": "d1", "role": "overall", "axis": "x", "value_m": 12.0}],
        "strokes": [], "uncaptured": [],
    }).encode("utf-8")

    baseline_sign, baseline_width = window_sources._advisory_elevation_world_frame(entry, reading_bytes)
    assert baseline_sign == -1  # truth-table row (North, False, L2R)
    assert baseline_width == 12.0

    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: 1)
    mutated_sign, _ = window_sources._advisory_elevation_world_frame(entry, reading_bytes)
    assert mutated_sign == 1
    assert mutated_sign != baseline_sign, (
        "mutating facade_convention.resolve_sign did not change window_sources."
        "_advisory_elevation_world_frame's output"
    )


def _real_geom_manifest_fact():
    """Real geom + manifest + direction fact, modeled on
    `tests/test_c2_b5_source_routing.py::_geom/_entry/_manifest/_base` (a
    South-facing single-floor rectangle) -- enough to exercise
    `materialize_current_ring_va_elevation_bindings` and
    `facade_applicability._validate_bindings` through their real, public
    entry points.
    """
    from src.agent.correction.facade_visibility import VisibilityTolerances, materialize_all_facade_segments
    from src.agent.correction.schema import CorrectedGeometryV3
    from src.agent.correction.window_sources import ElevationDirectionFactV1
    from src.agent.execution.manifest import hash_obj
    from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry, ViewManifest

    plan_entry = RequiredViewEntry(
        input_id="plan", source_image="case_data/plan.png", image_sha256="a" * 64,
        view_type="plan", floor_ref=1, declared_direction_token=None,
        direction_source="standard_assumption", direction_semantics="building_axis",
        semantics_source="standard_assumption", building_view_direction=None,
        dimensioned=True, expected_output_id="plan",
        opening_evidence=OpeningEvidence(potentially_observable_claims=["existence", "host", "along", "width"]),
    )
    south_entry = RequiredViewEntry(
        input_id="south", source_image="case_data/south.png", image_sha256="a" * 64,
        view_type="elevation", declared_direction_token="South",
        direction_source="standard_assumption", direction_semantics="building_axis",
        semantics_source="standard_assumption", building_view_direction="South",
        dimensioned=True, expected_output_id="south",
        opening_evidence=OpeningEvidence(
            potentially_observable_claims=["existence", "along", "width", "sill", "head", "appearance"],
        ),
    )
    payload = {
        "view_manifest_schema_version": "1", "claims_vocab_version": "1",
        "generator_version": "1", "completeness_ruleset_version": "1",
        "case_id": "s1-neuter", "case_metadata_sha256": "a" * 64,
        "entries": [plan_entry.model_dump(mode="json"), south_entry.model_dump(mode="json")],
    }
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))

    geom = CorrectedGeometryV3.model_validate({
        "schema_version": "3", "footprint_x": [0.0, 4.0], "footprint_y": [0.0, 3.0],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]},
            "cells": [{"id": "r1", "x": [0.0, 4.0], "y": [0.0, 3.0]}],
        }],
        "windows": [],
    })
    segments = materialize_all_facade_segments(geom, tolerances=VisibilityTolerances(1e-9, 1e-9))
    geom = geom.model_copy(update={"facade_segments": list(segments)})
    fact = ElevationDirectionFactV1(
        input_id="south", resolved_building_direction="South", resolution_source="manifest_building_axis",
        mirrored=False, local_x_positive="image_left_to_right", orientation_output_hash=None, adapter_version=None,
        view_manifest_sha256=manifest.content_sha256,
    )
    return geom, manifest, fact


def test_materialize_current_ring_va_elevation_bindings_is_really_wired(monkeypatch):
    """`window_sources.py`'s second real call site."""
    from src.agent.correction.facade_visibility import VisibilityTolerances
    from src.agent.correction.window_sources import materialize_current_ring_va_elevation_bindings

    geom, manifest, fact = _real_geom_manifest_fact()
    baseline = materialize_current_ring_va_elevation_bindings(
        geom=geom, manifest=manifest, direction_facts=(fact,),
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9),
    )[0]
    assert baseline.sign == 1  # truth-table row (South, False, L2R)

    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: -1)
    mutated = materialize_current_ring_va_elevation_bindings(
        geom=geom, manifest=manifest, direction_facts=(fact,),
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9),
    )[0]
    assert mutated.sign == -1
    assert mutated.sign != baseline.sign, (
        "mutating facade_convention.resolve_sign did not change "
        "materialize_current_ring_va_elevation_bindings' output"
    )


def test_validate_bindings_is_really_wired(monkeypatch):
    """`facade_applicability.py::_validate_bindings` -- proven by flipping
    its ACCEPT/REJECT verdict on an otherwise-valid, real binding (built
    with the real, unmutated `resolve_sign`), not just by comparing numbers.
    """
    from src.agent.correction.facade_applicability import FacadeApplicabilityInvariantError, _validate_bindings
    from src.agent.correction.facade_visibility import VisibilityTolerances
    from src.agent.correction.window_sources import materialize_current_ring_va_elevation_bindings

    geom, manifest, fact = _real_geom_manifest_fact()
    bindings = materialize_current_ring_va_elevation_bindings(
        geom=geom, manifest=manifest, direction_facts=(fact,),
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9),
    )
    _validate_bindings(manifest, bindings)  # baseline: correctly-built binding must PASS

    real_sign = bindings[0].sign
    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: -real_sign)
    with pytest.raises(FacadeApplicabilityInvariantError):
        # Same binding, now judged against a mutated expectation -- proves
        # _validate_bindings recomputes its expected sign through
        # facade_convention.resolve_sign on every call, not once at import.
        _validate_bindings(manifest, bindings)


def test_validate_score_view_bindings_is_really_wired(monkeypatch):
    """`judge/score_inputs.py::validate_score_view_bindings` -- third
    distinct file, proven the same accept/reject-flip way.
    """
    from src.agent.correction.footprint import floor_footprint_fingerprint
    from src.agent.judge.score_inputs import frame_transform_sha256, validate_score_view_bindings
    from src.agent.judge.score_schema import (
        ElevationScoreViewBindingV1,
        JudgeScoreViewBindingsV1,
        PlanScoreViewBindingV1,
        ScoreContractError,
        canonical_sha256 as judge_canonical_sha256,
    )

    geom, manifest, _fact = _real_geom_manifest_fact()
    probe_kwargs = dict(
        kind="elevation", input_id="south", floor_ids=("f1",), facade_family="South",
        gt_source_view_ids=("gt-south",), resolved_building_direction="South",
        resolution_source="manifest_building_axis", orientation_output_hash=None, adapter_version=None,
        source_footprint_fingerprint=floor_footprint_fingerprint(geom, geom.floors[0]),
        world_axis="x", sign=1, along_origin=0.0, mirrored=False, local_x_positive=L2R,
    )
    probe = ElevationScoreViewBindingV1(**probe_kwargs, frame_transform_sha256="0" * 64)
    real_hash = frame_transform_sha256(probe)
    elevation_binding = ElevationScoreViewBindingV1(**probe_kwargs, frame_transform_sha256=real_hash)
    plan_binding = PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="f1", gt_source_view_ids=("gt-plan",))

    payload = {
        "schema_version": "1", "case_id": "s1-neuter", "gt_content_sha256": "b" * 64,
        "case_metadata_sha256": "a" * 64, "base_view_manifest_sha256": manifest.content_sha256,
        "bindings": [plan_binding.model_dump(mode="json"), elevation_binding.model_dump(mode="json")],
    }
    bindings_obj = JudgeScoreViewBindingsV1(
        schema_version="1", case_id="s1-neuter", gt_content_sha256="b" * 64,
        case_metadata_sha256="a" * 64, base_view_manifest_sha256=manifest.content_sha256,
        bindings=(plan_binding, elevation_binding), content_sha256=judge_canonical_sha256(payload),
    )

    validate_score_view_bindings(bindings=bindings_obj, base=manifest)  # baseline: must PASS

    monkeypatch.setattr(facade_convention, "resolve_sign", lambda *a, **k: -1)
    with pytest.raises(ScoreContractError):
        validate_score_view_bindings(bindings=bindings_obj, base=manifest)


# ---------------------------------------------------------------------------
# 5. MINOR-3 (sol verdict, 2026-08-11): registering the legacy mirror
#    coercion mismatch as a PINNED, executable debt fact -- not fixing it
#    (fixing it would strictify legacy behavior, a real behavior change S1
#    must not make) and not leaving it as prose-only either.
# ---------------------------------------------------------------------------

def test_minor3_legacy_mirror_coercions_disagree_is_a_pinned_debt_fact():
    """Reproduces sol's exact verdict probe: the SAME `mirrored` value
    produces DIFFERENT resolved bools depending on which of the project's
    two legacy coercions reads it. This is deliberately kept as-is (S1 must
    not strictify legacy behavior -- see facade.py::_is_mirrored's comment)
    but must never silently drift further (e.g. one side accidentally
    starts accepting "unknown" as True) without this test catching it.
    """
    from src.agent.correction.facade import _is_mirrored
    from src.agent.correction.window_sources import _resolve_facade_flip_fields

    class _FakeFacade:
        def __init__(self, mirrored):
            self.mirrored = mirrored
            self.local_x_positive = "image_left_to_right"

    # The exact disagreement sol found: facade.py accepts the string "true";
    # window_sources.py's coercion only ever honors a real bool.
    assert _is_mirrored("true") is True
    assert _resolve_facade_flip_fields(_FakeFacade("true"))[0] is False

    # Both sides agree on real bools and on "unknown" (neither treats
    # "unknown" as mirrored) -- the debt is specifically the "true" string,
    # not a total disagreement across every input.
    assert _is_mirrored(True) is True and _resolve_facade_flip_fields(_FakeFacade(True))[0] is True
    assert _is_mirrored(False) is False and _resolve_facade_flip_fields(_FakeFacade(False))[0] is False
    assert _is_mirrored("unknown") is False and _resolve_facade_flip_fields(_FakeFacade("unknown"))[0] is False

    # The strict adapter (new, unwired into either legacy site) disagrees
    # with BOTH legacy coercions on "true" in its own way: it raises rather
    # than silently picking either answer.
    with pytest.raises(facade_convention.UnresolvedMirrorError):
        facade_convention.normalize_mirror_flag("unknown")
    assert facade_convention.normalize_mirror_flag("true") is True  # agrees with facade.py here, not window_sources.py
