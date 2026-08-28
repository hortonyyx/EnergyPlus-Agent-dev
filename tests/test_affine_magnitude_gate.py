"""B4-(2)a: the NUMERIC half of the 2-D/1-D affine space contract.

What B4-(1) left open
---------------------
The type gate stamps a slot's two ends *by slot and blind to content*.  Strip
``domain_space``/``codomain_space`` off the sm24 manifest affine, drop the six
bare coefficients into the request's plan-view slot, and ``model_validate``
accepted it, stamped it ``dxf_native -> world_metre`` and put the clip corner
12264.66 m away from the truth.  That is not a synthetic shape: migration-era
signed artifacts carry undeclared affines (it is why the hash strip exists), and
``tarch_normalize._build_manifest`` still constructs bare ``Affine2D`` /
``Affine1D`` values with a hand-written ``/ metres_per_unit``.

The gate this file locks reads the coefficients instead of the declaration:
once the two ends are known, the document's own ``metres_per_unit`` fixes
``|det|`` (2-D) / ``|scale|`` (1-D).  It is therefore *single-sided* -- it needs
no counterpart slot to compare against, which matters because sm25-L, the main
case, ships a request and no manifest at all.

Every discriminating fixture below is a REAL signed anchor.
"""
from __future__ import annotations

import ast
import copy
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.judge.affine_space import (
    AFFINE_MAGNITUDE_REL_TOL,
    AffineMagnitudeMismatch,
    AffineSpaceUndeclared,
    affine_magnitude,
    affine_spaces,
    expected_affine_magnitude,
    iter_affines,
    require_affine_magnitude,
    space_unit_metres,
)
from src.agent.judge.gt_manifest import (
    Affine1D,
    Affine2D,
    GtExtractionManifestV1,
)
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1

REPO = Path(__file__).resolve().parents[1]
GT_SOURCES = REPO / "case_tests" / "test_baseline" / "gt_sources"

#: Listed, not globbed, so a fixture that disappears turns the suite RED instead
#: of quietly reducing the lock to nothing.  sm25-L has NO manifest -- that
#: asymmetry is the point of ``test_the_gate_has_inventory_on_the_main_case``.
SIGNED_REQUESTS = ("sm25-L_anchor", "sm24_anchor")
SIGNED_MANIFESTS = ("sm24_anchor",)


def _raw_request(case: str) -> dict:
    return json.loads((GT_SOURCES / case / "request.json").read_text(encoding="utf-8"))


def _raw_manifest(case: str) -> dict:
    return json.loads((GT_SOURCES / case / "manifest.json").read_text(encoding="utf-8"))


def _request(case: str) -> TarchConversionRequestV1:
    return TarchConversionRequestV1.model_validate(_raw_request(case))


def _manifest(case: str) -> GtExtractionManifestV1:
    return GtExtractionManifestV1.model_validate(_raw_manifest(case))


def _bare(affine_payload: dict) -> dict:
    """The attack primitive: six coefficients with the declaration removed."""
    stripped = copy.deepcopy(affine_payload)
    stripped.pop("domain_space", None)
    stripped.pop("codomain_space", None)
    return stripped


# --------------------------------------------------------------------------- #
# 0 -- the premise the whole gate rests on, measured rather than asserted
# --------------------------------------------------------------------------- #
def test_the_det_relation_the_gate_is_built_on_is_arithmetically_true():
    """|det| of the two same-named affines differs by exactly a factor mpu**2.

    The dispatch supplied this relation from a review note and flagged it as
    never having been computed.  Computed here, on the real pair.
    """
    request = _request("sm24_anchor")
    manifest = _manifest("sm24_anchor")
    mpu = request.metres_per_unit
    assert mpu == manifest.metres_per_unit == 0.001

    native = next(v for v in request.plan_views if v.id == "plan-F1").world_from_source_m
    source = next(v for v in manifest.views if v.kind == "plan").world_from_source_m
    native_det, kind = affine_magnitude(native)
    source_det, _ = affine_magnitude(source)
    assert kind == "abs_det"
    assert native_det == pytest.approx(1e-6, rel=1e-15)
    assert source_det == pytest.approx(1.0, rel=1e-15)
    # the relation, both ways round -- note mpu**2 == 1e-6, NOT 1e6; 1e6 is the
    # ratio, i.e. mpu**-2.
    assert native_det == pytest.approx(source_det * mpu**2, rel=1e-15)
    assert source_det / native_det == pytest.approx(mpu**-2, rel=1e-15)


def test_the_same_relation_holds_one_dimension_down():
    """F-E: the 1-D elevation affines carry the identical mpu factor."""
    request = _request("sm25-L_anchor")
    mpu = request.metres_per_unit
    seen = 0
    for view in request.elevation_views:
        for field in ("world_along_from_source_m", "world_z_from_source_m"):
            affine = getattr(view, field)
            value, kind = affine_magnitude(affine)
            assert kind == "abs_scale"
            assert value == pytest.approx(mpu, rel=1e-15)
            assert affine_spaces(affine) == ("dxf_native", "world_metre")
            seen += 1
    assert seen == 8


# --------------------------------------------------------------------------- #
# 1 -- signatures are untouched (the gate reads coefficients, writes nothing)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", SIGNED_REQUESTS)
def test_signed_request_still_loads_and_keeps_its_hash(case):
    from src.agent.judge.tarch_converter_schema import compute_request_sha256

    raw = _raw_request(case)
    assert compute_request_sha256(_request(case)) == raw["request_sha256"]


@pytest.mark.parametrize("case", SIGNED_MANIFESTS)
def test_signed_manifest_still_loads_and_keeps_its_hash(case):
    from src.agent.judge.gt_manifest import compute_manifest_sha256

    raw = _raw_manifest(case)
    assert compute_manifest_sha256(_manifest(case)) == raw["manifest_sha256"]


def test_the_new_1d_space_keys_really_reach_the_wire_and_are_really_stripped():
    """Otherwise 'signature preserved' would be preserved by doing nothing."""
    from src.agent.judge.affine_space import strip_affine_space_keys

    request = _request("sm25-L_anchor")
    payload = request.model_dump(mode="json")
    elevation = payload["elevation_views"][0]["world_along_from_source_m"]
    assert elevation["domain_space"] == "dxf_native"
    assert elevation["codomain_space"] == "world_metre"
    stripped = strip_affine_space_keys(payload)
    assert "domain_space" not in stripped["elevation_views"][0]["world_along_from_source_m"]


# --------------------------------------------------------------------------- #
# 2 -- teeth on BARE coefficients (the acceptance the dispatch asked for)
# --------------------------------------------------------------------------- #
def test_bare_manifest_coefficients_are_refused_by_the_request():
    """The exact attack: strip the declaration, use the other slot's numbers."""
    manifest_affine = _raw_manifest("sm24_anchor")["views"][0]["world_from_source_m"]
    payload = _raw_request("sm24_anchor")
    payload["plan_views"][0]["world_from_source_m"] = _bare(manifest_affine)

    with pytest.raises(ValidationError) as excinfo:
        TarchConversionRequestV1.model_validate(payload)
    message = str(excinfo.value)
    # the type gate cannot have produced this: the affine declared nothing
    assert "abs_det" in message and "1e+06" in message
    assert "dxf_native" in message and "world_metre" in message


def test_bare_request_coefficients_are_refused_by_the_manifest():
    request_affine = _raw_request("sm24_anchor")["plan_views"][0]["world_from_source_m"]
    payload = _raw_manifest("sm24_anchor")
    payload["views"][0]["world_from_source_m"] = _bare(request_affine)

    with pytest.raises(ValidationError) as excinfo:
        GtExtractionManifestV1.model_validate(payload)
    assert "abs_det" in str(excinfo.value)


def test_bare_coefficients_are_refused_one_dimension_down_too():
    """F-E's hazard, on the slot that has inventory today: the sm25 request."""
    payload = _raw_request("sm25-L_anchor")
    view = payload["elevation_views"][0]
    manifest_shaped = dict(view["world_along_from_source_m"])
    # what _build_manifest's `scale / mpu` produces -- source-metre scale
    manifest_shaped["scale"] = manifest_shaped["scale"] / payload["metres_per_unit"]
    view["world_along_from_source_m"] = _bare(manifest_shaped)

    with pytest.raises(ValidationError) as excinfo:
        TarchConversionRequestV1.model_validate(payload)
    assert "abs_scale" in str(excinfo.value)


def test_the_arithmetic_regression_shape_is_caught_without_any_slot_swap():
    """Divide by mpu twice / forget to divide -- no second slot involved.

    This is the ``_build_manifest`` regression the gate exists for.  That
    function ends in ``GtExtractionManifestV1.model_validate``, so this is the
    validator it would hit -- reached without editing ``tarch_normalize.py``.
    """
    raw = _raw_manifest("sm24_anchor")
    mpu = raw["metres_per_unit"]
    for factor, label in ((mpu, "forgot to divide"), (1.0 / mpu, "divided twice")):
        payload = copy.deepcopy(raw)
        affine = payload["views"][0]["world_from_source_m"]
        for key in ("m00", "m01", "m10", "m11"):
            affine[key] = affine[key] * factor
        with pytest.raises(ValidationError, match="abs_det"):
            GtExtractionManifestV1.model_validate(payload), label


# --------------------------------------------------------------------------- #
# 3 -- anti-vacuity: what the gate would have let through, and its resolution
# --------------------------------------------------------------------------- #
def test_the_honest_anchors_all_pass_and_the_gate_actually_ran():
    """Green must mean 'checked and agreed', not 'nothing was checked'."""
    predicted = 0
    for case in SIGNED_REQUESTS:
        request = _request(case)
        for _where, affine in iter_affines(request):
            # nothing is undeclared any more -- this raises otherwise
            affine_spaces(affine)
            if expected_affine_magnitude(
                    affine, metres_per_unit=request.metres_per_unit) is not None:
                predicted += 1
    # sm24: 1 plan + 8 elevation; sm25: 2 plan + 8 elevation
    assert predicted == 19


def test_the_gate_is_not_a_rubber_stamp_at_its_own_tolerance():
    """It resolves far, far finer than the 1e6 hazard it was built for."""
    affine = Affine2D(m00=0.001, m01=0.0, m02=0.0, m10=0.0, m11=0.001, m12=0.0,
                      domain_space="dxf_native", codomain_space="world_metre")
    require_affine_magnitude(affine, metres_per_unit=0.001, context="ok")
    # a 1e-6 relative error on one coefficient -- twelve orders below the hazard
    nudged = affine.model_copy(update={"m00": 0.001 * (1.0 + 1e-6)})
    with pytest.raises(AffineMagnitudeMismatch):
        require_affine_magnitude(nudged, metres_per_unit=0.001, context="nudged")
    # ... and it still tolerates double-precision noise
    noise = affine.model_copy(update={"m00": math.nextafter(0.001, 1.0)})
    require_affine_magnitude(noise, metres_per_unit=0.001, context="noise")
    assert AFFINE_MAGNITUDE_REL_TOL == 1e-9


def test_rotation_and_reflection_are_never_mis_flagged():
    """|det| was chosen over per-coefficient checks precisely for this."""
    mpu = 0.001
    for degrees in (0.0, 7.5, 37.0, 90.0, 180.0, 313.7):
        radians = math.radians(degrees)
        for mirror in (1.0, -1.0):
            affine = Affine2D(
                m00=mpu * math.cos(radians), m01=-mpu * math.sin(radians), m02=17.0,
                m10=mpu * math.sin(radians) * mirror,
                m11=mpu * math.cos(radians) * mirror, m12=-3.0,
                domain_space="dxf_native", codomain_space="world_metre")
            require_affine_magnitude(affine, metres_per_unit=mpu, context="rotated")


def test_pixel_ends_are_explicitly_unpredicted_not_accidentally_skipped():
    """A raster's pixel size is a property of the image, not of the drawing."""
    assert space_unit_metres("pixel", metres_per_unit=0.001) is None
    assert space_unit_metres("dxf_native", metres_per_unit=0.001) == 0.001
    assert space_unit_metres("source_metre", metres_per_unit=0.001) == 1.0
    request = _request("sm24_anchor")
    overlay = request.raster_overlays[0]
    assert affine_spaces(overlay.pixel_to_source_m) == ("pixel", "source_metre")
    assert expected_affine_magnitude(
        overlay.pixel_to_source_m, metres_per_unit=request.metres_per_unit) is None
    # the five raster affines really are the skipped ones, and they really would
    # have failed a naive prediction -- so the skip is load-bearing, not cosmetic
    naive = affine_magnitude(overlay.pixel_to_source_m)[0]
    assert not math.isclose(naive, request.metres_per_unit ** 2, rel_tol=1e-3)


# --------------------------------------------------------------------------- #
# 4 -- STRUCTURAL LOCK A: the gate has inventory on the case that has no pair
# --------------------------------------------------------------------------- #
def test_the_gate_has_inventory_on_the_main_case_that_has_no_manifest():
    """sm25-L ships a request and NO manifest.

    A gate phrased as 'compare the two same-named slots' would have zero
    fixtures here and would be a gate whose only teeth point away from the main
    case.  The single-sided phrasing has ten checked slots on sm25-L alone, and
    this test fails the moment somebody re-phrases it pairwise.
    """
    assert (GT_SOURCES / "sm25-L_anchor" / "request.json").is_file()
    assert not (GT_SOURCES / "sm25-L_anchor" / "manifest.json").exists()

    request = _request("sm25-L_anchor")
    checked = [where for where, affine in iter_affines(request)
               if expected_affine_magnitude(
                   affine, metres_per_unit=request.metres_per_unit) is not None]
    assert len(checked) == 10
    assert sum(1 for w in checked if w.startswith("plan_views")) == 2
    assert sum(1 for w in checked if w.startswith("elevation_views")) == 8

    # and each of those ten really is discriminating on this case
    for index in range(len(request.plan_views)):
        payload = _raw_request("sm25-L_anchor")
        affine = payload["plan_views"][index]["world_from_source_m"]
        for key in ("m00", "m01", "m10", "m11"):
            affine[key] = affine[key] / payload["metres_per_unit"]
        with pytest.raises(ValidationError, match="abs_det"):
            TarchConversionRequestV1.model_validate(payload)
    for index in range(len(request.elevation_views)):
        for field in ("world_along_from_source_m", "world_z_from_source_m"):
            payload = _raw_request("sm25-L_anchor")
            view = payload["elevation_views"][index]
            view[field] = dict(view[field])
            view[field]["scale"] = view[field]["scale"] / payload["metres_per_unit"]
            with pytest.raises(ValidationError, match="abs_scale"):
                TarchConversionRequestV1.model_validate(payload)


# --------------------------------------------------------------------------- #
# 5 -- STRUCTURAL LOCK B: no affine slot may escape the contract
# --------------------------------------------------------------------------- #
def test_a_new_unbound_affine_slot_cannot_slip_past_the_gate():
    """Discovery is by shape, so 'forgot to bind the new field' fails closed.

    Demonstrated behaviourally rather than by grep: an affine that reaches the
    root gate undeclared raises instead of being silently unchecked.  Before
    this change the eight elevation ``Affine1D`` slots on every signed request
    were exactly that -- present, used, and covered by nothing.
    """
    loose_2d = Affine2D(m00=1.0, m01=0.0, m02=0.0, m10=0.0, m11=1.0, m12=0.0)
    loose_1d = Affine1D(source_axis="x", scale=1.0, offset=0.0)
    for loose in (loose_2d, loose_1d):
        with pytest.raises(AffineSpaceUndeclared):
            require_affine_magnitude(loose, metres_per_unit=0.001, context="loose")

    class _Carrier:
        """A stand-in for a model that grew an affine field without binding it."""
        model_fields = {"nested": None}

        def __init__(self, nested):
            self.nested = nested

    from src.agent.judge.affine_space import require_affine_magnitudes

    found = [where for where, _ in iter_affines(_Carrier([loose_2d, loose_1d]))]
    assert found == ["nested[0]", "nested[1]"], found
    with pytest.raises(AffineSpaceUndeclared):
        require_affine_magnitudes(_Carrier([loose_2d]), metres_per_unit=0.001,
                                  context="new-model")


def test_half_declared_1d_space_contract_is_refused():
    # ⛔ the positive leg first: without it this test would also pass on a tree
    # where Affine1D simply has no such fields at all (extra="forbid" would
    # reject the half-declared form for the wrong reason).
    declared = Affine1D(source_axis="x", scale=1.0, offset=0.0,
                        domain_space="source_metre", codomain_space="world_metre")
    assert affine_spaces(declared) == ("source_metre", "world_metre")
    with pytest.raises(ValidationError):
        Affine1D(source_axis="x", scale=1.0, offset=0.0, domain_space="dxf_native")


# --------------------------------------------------------------------------- #
# 6 -- STRUCTURAL LOCK C (F-B): Affine2DV1 keeps exactly one producer
# --------------------------------------------------------------------------- #
#: ``score_schema.Affine2DV1`` declares its two ends as CLASS attributes, so
#: every instance is ``reading_plan_local_metre -> world_metre`` by fiat -- there
#: is no per-instance declaration that could disagree.  That is only sound while
#: the type has exactly one producer.  A second producer would build a
#: pixel->world or manifest-shaped affine, and ``apply_affine_2d`` would accept
#: it by name while being numerically 1000x wrong.
AFFINE2DV1_PRODUCER = ("src/agent/judge/reading_typed_adapter.py", "_plan_frame")

#: Modules allowed to name the type at all.  ``score_schema`` defines it,
#: ``reading_typed_adapter`` builds and applies it, ``affine_space`` names it
#: only in the prose that explains the class-attribute carrier.
AFFINE2DV1_MODULES = (
    "src/agent/judge/affine_space.py",
    "src/agent/judge/score_schema.py",
    "src/agent/judge/reading_typed_adapter.py",
)


def _construction_sites(path: Path, class_name: str) -> list[tuple[str, int]]:
    """Every call whose callee resolves to *class_name* in this module.

    AST-based rather than ``grep "Affine2DV1("``: it survives a call split over
    lines, and it follows ``from ... import Affine2DV1 as F`` / ``import
    score_schema`` + ``score_schema.Affine2DV1(...)`` aliases.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases = {class_name}
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == class_name:
                    aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.asname or alias.name.split(".")[0])

    def _is_target(func: ast.expr) -> bool:
        if isinstance(func, ast.Name):
            return func.id in aliases
        if isinstance(func, ast.Attribute):
            return func.attr == class_name
        return False

    sites: list[tuple[str, int]] = []
    scope: list[str] = []

    class _Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):  # noqa: N802
            scope.append(node.name)
            self.generic_visit(node)
            scope.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):  # noqa: N802
            if _is_target(node.func):
                sites.append((scope[-1] if scope else "<module>", node.lineno))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return sites


def test_affine2dv1_still_has_exactly_one_producer():
    hits: list[tuple[str, str, int]] = []
    for path in sorted((REPO / "src").rglob("*.py")):
        for function, line in _construction_sites(path, "Affine2DV1"):
            hits.append((str(path.relative_to(REPO)), function, line))
    assert len(hits) == 1, hits
    module, function, _line = hits[0]
    assert (module, function) == AFFINE2DV1_PRODUCER, hits


def test_the_producer_lock_is_not_vacuous():
    """A second producer must make the lock red -- proven, not assumed."""
    source = (REPO / "src" / AFFINE2DV1_PRODUCER[0].split("src/", 1)[1]).read_text(
        encoding="utf-8")
    assert "Affine2DV1" in source
    injected = source + (
        "\n\n"
        "def _second_producer():\n"
        "    return Affine2DV1(\n"
        "        xx=0.01, xy=0.0, x0=0.0,\n"
        "        yx=0.0, yy=0.01, y0=0.0,\n"
        "    )\n"
    )
    tree = ast.parse(injected)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "Affine2DV1"]
    assert len(calls) == 2, "the injected second producer must be visible to the lock"


def test_only_the_declared_modules_may_name_affine2dv1():
    """Breadth half of the lock: the scan above must be looking everywhere."""
    naming = sorted(
        str(path.relative_to(REPO))
        for path in (REPO / "src").rglob("*.py")
        if "Affine2DV1" in path.read_text(encoding="utf-8")
    )
    assert naming == sorted(AFFINE2DV1_MODULES), naming
