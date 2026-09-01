"""Discriminating-power probe for tests/test_o21d_exclusion_gap.py.

⛔ Touches no production file.  It patches the TEST module's own
``read_facts_for_compilation`` attribute (⭐ the parent attribute, because the
test module did ``from ... import read_facts_for_compilation`` --
[[shadow-module-swap-must-touch-parent-attr]]) so every lock runs through the
real entry point against a DEFECTIVE substrate.

Pick the injection with -D: none | unlicensed_gap | ledger_disagreement |
undeclared_code | forged_licence
"""
import os

from src.agent.judge.answer_compiler import (
    read_facts_for_compilation as _real, reconcile_boundary_basis,
    _footprint_polygon, _wall_region, _cavity_id)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import ConversionReportV1
from src.agent.judge.gt_schema import REPO_ROOT

MODE = os.environ["O21D_MUTATION"]
SPAN = {"axis": "y", "const": 1, "lo": 0, "hi": 1000, "side": 1,
        "p1": [1, 1000], "p2": [1, 0]}
REPORT = ConversionReportV1.model_validate_json(
    (REPO_ROOT / "case_tests/test_baseline/gt/sm25-L_anchor/review/"
     "conversion_report.json").read_bytes())


def _pick(signed):
    base = reconcile_boundary_basis(signed, REPORT)
    areas = {}
    for view in signed.views:
        fp, _ = _footprint_polygon(view)
        g = fp.difference(_wall_region(view))
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "Polygon" and not part.is_empty and part.area > 0:
                areas[(view.view_id, _cavity_id(view.view_id, part))] = part.area
    proof = max(base.pairings, key=lambda p: areas[(p.view_id, p.cavity_id)])
    return proof, areas[(proof.view_id, proof.cavity_id)]


def _mutate(signed, *, strip, licence):
    proof, area = _pick(signed)
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        if view["view_id"] != proof.view_id:
            continue
        if strip:
            view["boundary_edges"] = [e for e in view["boundary_edges"]
                                      if e["cavity_id"] != proof.cavity_id]
        if licence:
            view["boundary_ring_losses"] = view["boundary_ring_losses"] + [{
                "cavity_id": proof.cavity_id, "area_units2": int(area),
                "span": SPAN, "reason": "merged_lt_3", "owner_count": None}]
    return AsSignedV1.model_validate(raw)


def _renumber_one_cavity(signed):
    """Produce an UNDECLARED structural code (facts_boundary_sequence_not_contiguous)
    -- neither this file's branch nor a code another lock owns."""
    proof, _ = _pick(signed)
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        if view["view_id"] != proof.view_id:
            continue
        for edge in view["boundary_edges"]:
            if edge["cavity_id"] == proof.cavity_id:
                edge["sequence"] = edge["sequence"] + 10
    return AsSignedV1.model_validate(raw)


def _patched(case):
    measured, ledger, signed = _real(case)
    if MODE == "none":
        return measured, ledger, signed
    if MODE == "unlicensed_gap":                 # the ②-1d defect itself
        return measured, ledger, _mutate(signed, strip=True, licence=False)
    if MODE == "ledger_disagreement":            # as_signed ledger != as_measured
        return measured, ledger, _mutate(signed, strip=True, licence=True)
    if MODE == "undeclared_code":
        return measured, ledger, _renumber_one_cavity(signed)
    if MODE == "forged_licence":                 # ring AND loss for one cavity
        return measured, ledger, _mutate(signed, strip=False, licence=True)
    raise SystemExit(f"unknown mode {MODE}")


def pytest_collection_modifyitems(session, config, items):
    """⭐ Patch the module pytest ACTUALLY imported.

    ``tests/`` has no ``__init__.py``, so pytest imports the file as top-level
    ``test_o21d_exclusion_gap``; ``import tests.test_o21d_exclusion_gap`` in
    ``pytest_configure`` builds a SECOND module object and patches nothing --
    the whole matrix then reads as "all green", i.e. a false all-clear
    ([[shadow-module-swap-must-touch-parent-attr]]).  Patched here, and the
    patch proves itself landed.
    """
    modules = {item.module for item in items}
    assert modules, "no items collected -- nothing was mutated"
    for module in modules:
        assert hasattr(module, "read_facts_for_compilation"), module
        module.read_facts_for_compilation = _patched
        assert module.read_facts_for_compilation is _patched
    print(f"\n[mutation_plugin] mode={MODE} patched={sorted(m.__name__ for m in modules)}")
