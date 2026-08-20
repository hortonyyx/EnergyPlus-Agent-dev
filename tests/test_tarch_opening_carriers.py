"""Contract and skeleton tests for request-declared elevation opening carriers."""
from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import ezdxf
import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.gt_manifest import ClipBoxDxf
from src.agent.judge.tarch_converter_schema import (
    OpeningCarrierRuleV1,
    TarchConversionRequestV1,
    compute_request_sha256,
    diagnostic_spec,
    resolve_converter_tooling,
)


REPO = Path(__file__).resolve().parents[1]
SM24_REQUEST = (
    REPO / "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json"
)
SM24_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
TOOLING = resolve_converter_tooling(
    REPO / "src/configs/judge_gt.yaml", REPO / "src/configs/correction.yaml")


def _line_rule(carrier_id: str = "window-line-frame") -> OpeningCarrierRuleV1:
    return OpeningCarrierRuleV1(
        carrier_id=carrier_id,
        opening_kind="window",
        match={"entity_type": "LINE", "layers": ["E_WINDOW"]},
        outline={"kind": "connected_line_group_rect"},
    )


def test_opening_carrier_schema_binds_new_rules_without_moving_old_request_hash():
    request = TarchConversionRequestV1.model_validate_json(SM24_REQUEST.read_text())
    assert request.opening_carrier_rules is None
    assert request.ignore_selector is None
    assert compute_request_sha256(request) == request.request_sha256

    declared = request.model_copy(update={"opening_carrier_rules": [_line_rule()]})
    assert compute_request_sha256(declared) != request.request_sha256
    declared_ignore = request.model_copy(update={"ignore_selector": []})
    assert compute_request_sha256(declared_ignore) != request.request_sha256


def test_block_outline_allows_multiple_structural_line_roles():
    rule = OpeningCarrierRuleV1(
        carrier_id="door-block-frame",
        opening_kind="door",
        module_union_strategy="same_band_strict_union",
        match={
            "entity_type": "INSERT",
            "layers": ["E_WINDOW"],
            "block_name_exact": "$EWDLib$00000621",
            "block_definition_sha256": "a" * 64,
        },
        outline={
            "kind": "block_entity_rect",
            "block_entity_roles": [
                {"entity_handle": handle, "role": "structural_outline"}
                for handle in ("35E", "35F", "360", "361")
            ],
        },
    )
    assert len(rule.outline.block_entity_roles or []) == 4


def test_touching_union_requires_explicit_domain_gap_parameter():
    payload = {
        "carrier_id": "door-lines",
        "opening_kind": "door",
        "match": {"entity_type": "LINE", "layers": ["E_WINDOW"]},
        "outline": {"kind": "connected_line_group_rect"},
        "module_union_strategy": "touching_rect_union",
    }
    with pytest.raises(ValueError, match="requires module_union_min_gap_m"):
        OpeningCarrierRuleV1(**payload)
    rule = OpeningCarrierRuleV1(**payload, module_union_min_gap_m=0.5)
    assert rule.module_union_min_gap_m == 0.5


@pytest.mark.parametrize(
    "union_field,union_value",
    [
        ("module_union_strategy", "same_band_strict_union"),
        ("module_union_min_gap_m", 0.5),
    ],
)
def test_window_carrier_rejects_door_module_union_fields(
        union_field, union_value):
    payload = {
        "carrier_id": "window-lines",
        "opening_kind": "window",
        "match": {"entity_type": "LINE", "layers": ["E_WINDOW"]},
        "outline": {"kind": "connected_line_group_rect"},
        union_field: union_value,
    }
    with pytest.raises(
            ValueError,
            match="window opening carriers cannot declare module union"):
        OpeningCarrierRuleV1(**payload)


@pytest.mark.parametrize(
    "match,outline",
    [
        ({"entity_type": "LINE", "layers": ["B", "A"]},
         {"kind": "connected_line_group_rect"}),
        ({"entity_type": "LINE", "layers": ["A"], "block_name_exact": "B"},
         {"kind": "connected_line_group_rect"}),
        ({"entity_type": "LWPOLYLINE", "layers": ["A"]},
         {"kind": "connected_line_group_rect"}),
    ],
)
def test_opening_carrier_schema_rejects_ambiguous_or_incompatible_declarations(
        match, outline):
    with pytest.raises(ValueError):
        OpeningCarrierRuleV1(
            carrier_id="bad-carrier", opening_kind="window",
            match=match, outline=outline)


def test_connected_line_group_resolver_reuses_existing_geometry_helpers(monkeypatch):
    doc = ezdxf.new("R2010")
    doc.layers.add("E_WINDOW")
    doc.layers.add("UNDECLARED")
    msp = doc.modelspace()
    declared = [
        msp.add_line((0.0, 0.0), (4.0, 0.0), dxfattribs={"layer": "E_WINDOW"}),
        msp.add_line((4.0, 0.0), (4.0, 3.0), dxfattribs={"layer": "E_WINDOW"}),
        msp.add_line((4.0, 3.0), (0.0, 3.0), dxfattribs={"layer": "E_WINDOW"}),
        msp.add_line((0.0, 3.0), (0.0, 0.0), dxfattribs={"layer": "E_WINDOW"}),
    ]
    for start, end in [((10.0, 0.0), (14.0, 0.0)),
                       ((14.0, 0.0), (14.0, 3.0)),
                       ((14.0, 3.0), (10.0, 3.0)),
                       ((10.0, 3.0), (10.0, 0.0))]:
        msp.add_line(start, end, dxfattribs={"layer": "UNDECLARED"})

    line_component_calls: list[tuple[str, ...]] = []
    rect_calls: list[tuple[str, ...]] = []
    original_components = tn._line_components
    original_rect = tn._rect_from_lines

    def components_spy(lines, q):
        line_component_calls.append(tuple(entity.dxf.handle for entity in lines))
        return original_components(lines, q)

    def rect_spy(lines, q):
        rect_calls.append(tuple(entity.dxf.handle for entity in lines))
        return original_rect(lines, q)

    monkeypatch.setattr(tn, "_line_components", components_spy)
    monkeypatch.setattr(tn, "_rect_from_lines", rect_spy)
    view = SimpleNamespace(
        id="South_view",
        clip_box_dxf=ClipBoxDxf(xmin=-1.0, ymin=-1.0, xmax=20.0, ymax=10.0),
    )
    tols = tn._Tols(
        metres_per_unit=0.001,
        node_join_m=0.001,
        axis_align_m=0.001,
        topo_area_m2=0.001,
    )

    carriers, diagnostics = tn._resolve_opening_carriers(
        view, [_line_rule()], msp, tols)

    handles = tuple(sorted(entity.dxf.handle for entity in declared))
    assert carriers == [
        ("window-line-frame", "window", (0.0, 0.0, 4.0, 3.0), handles, handles)
    ]
    assert diagnostics == []
    assert line_component_calls == [tuple(entity.dxf.handle for entity in declared)]
    assert len(rect_calls) == 1
    assert set(rect_calls[0]) == {entity.dxf.handle for entity in declared}
    assert tn._OPENING_CARRIER_RESOLVERS["connected_line_group_rect"] \
        is tn._resolve_connected_line_group_rect


def test_closed_polyline_outline_rejects_non_rectangular_carrier():
    rule = OpeningCarrierRuleV1(
        carrier_id="window-polyline-frame",
        opening_kind="window",
        match={"entity_type": "LWPOLYLINE", "layers": ["E_WINDOW"]},
        outline={"kind": "closed_polyline_rect"},
    )
    view = SimpleNamespace(
        id="East_view",
        clip_box_dxf=ClipBoxDxf(xmin=-1.0, ymin=-1.0, xmax=1.0, ymax=1.0),
    )
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    doc = ezdxf.new()
    doc.layers.add("E_WINDOW")
    entity = doc.modelspace().add_lwpolyline(
        [(-0.5, -0.5), (0.5, -0.5), (0.0, 0.5)], close=True,
        dxfattribs={"layer": "E_WINDOW"})
    carriers, diagnostics = tn._resolve_opening_carriers(
        view, [rule], doc.modelspace(), tols)
    assert carriers == []
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "tarch_elevation_opening_component_invalid"
    assert diagnostics[0].source_entity_handles == [entity.dxf.handle]
    assert diagnostics[0].context == {
        "view_id": "East_view", "carrier_id": "window-polyline-frame"}


def _block_rule(doc, name: str, structural_handles: set[str], *,
                opening_kind: str, carrier_id: str) -> OpeningCarrierRuleV1:
    block = list(doc.blocks.get(name))
    payload = {
        "carrier_id": carrier_id,
        "opening_kind": opening_kind,
        "match": {
            "entity_type": "INSERT",
            "layers": ["E_WINDOW"],
            "block_name_exact": name,
            "block_definition_sha256": tn.elevation_block_definition_sha256(doc, name),
        },
        "outline": {
            "kind": "block_entity_rect",
            "block_entity_roles": [
                {"entity_handle": entity.dxf.handle,
                 "role": ("structural_outline"
                          if entity.dxf.handle in structural_handles
                          else "nonstructural_detail")}
                for entity in block
            ],
        },
    }
    if opening_kind == "door":
        payload.update({
            "module_union_strategy": "touching_rect_union",
            "module_union_min_gap_m": 0.5,
        })
    return OpeningCarrierRuleV1(**payload)


def test_block_definition_tamper_is_blocking_after_green_premise():
    doc = ezdxf.new("R2010")
    doc.layers.add("E_WINDOW")
    block = doc.blocks.new("DOOR_FRAME")
    structural = [
        block.add_line((0.0, 0.0), (800.0, 0.0)),
        block.add_line((800.0, 0.0), (800.0, 2100.0)),
        block.add_line((800.0, 2100.0), (0.0, 2100.0)),
        block.add_line((0.0, 2100.0), (0.0, 0.0)),
    ]
    insert = doc.modelspace().add_blockref(
        "DOOR_FRAME", (0.0, 0.0), dxfattribs={"layer": "E_WINDOW"})
    rule = _block_rule(
        doc, "DOOR_FRAME", {entity.dxf.handle for entity in structural},
        opening_kind="door", carrier_id="door-frame")
    view = SimpleNamespace(
        id="West_view",
        clip_box_dxf=ClipBoxDxf(
            xmin=-1.0, ymin=-1.0, xmax=1000.0, ymax=2200.0),
    )
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    carriers, diagnostics = tn._resolve_opening_carriers(
        view, [rule], doc.modelspace(), tols)
    assert len(carriers) == 1 and diagnostics == []

    block.add_circle((400.0, 1000.0), 10.0)
    carriers, diagnostics = tn._resolve_opening_carriers(
        view, [rule], doc.modelspace(), tols)
    assert carriers == []
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "tarch_elevation_door_block_drift"
    assert diagnostics[0].source_entity_handles == [insert.dxf.handle]
    assert diagnostics[0].context["reason"] == "block_definition_sha256_mismatch"


def test_touching_union_near_gap_is_red_and_declared_gap_is_green():
    rule = OpeningCarrierRuleV1(
        carrier_id="door-modules", opening_kind="door",
        match={"entity_type": "LINE", "layers": ["E_WINDOW"]},
        outline={"kind": "connected_line_group_rect"},
        module_union_strategy="touching_rect_union",
        module_union_min_gap_m=0.5)
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)

    def modules(second_x: float):
        return [
            (rule.carrier_id, "door", (0.0, 0.0, 800.0, 2100.0),
             ("A",), ("S",)),
            (rule.carrier_id, "door", (second_x, 0.0, second_x + 800.0, 2100.0),
             ("B",), ("S",)),
        ]

    merged, diagnostics = tn._merge_door_carriers(
        modules(900.0), [rule], tols, "West_view")  # 100 mm < signed 500 mm
    assert merged == []
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "tarch_elevation_door_structure_invalid"
    assert diagnostics[0].source_entity_handles == ["A", "B"]

    merged, diagnostics = tn._merge_door_carriers(
        modules(1300.0), [rule], tols, "West_view")  # 500 mm is accepted
    assert len(merged) == 2
    assert diagnostics == []


def _sm25_rules(doc):
    window_block = _block_rule(
        doc, "$EWDLib$00000533", {"316", "317", "319", "31B"},
        opening_kind="window", carrier_id="window-block-frame")
    door_block = _block_rule(
        doc, "$EWDLib$00000621", {"35E", "35F", "360", "361"},
        opening_kind="door", carrier_id="door-block-frame")
    window_polyline = OpeningCarrierRuleV1(
        carrier_id="window-polyline-frame", opening_kind="window",
        match={"entity_type": "LWPOLYLINE", "layers": ["E_WINDOW"]},
        outline={"kind": "closed_polyline_rect"})
    return [window_block, window_polyline, door_block]


SM25_FRAMES = {
        "West_view": (-76501.594584, -12864.622462, -42725.900792, 8567.031916),
        "South_view": (-36320.065548, -12864.622462, -2544.371756, 8567.031916),
        "North_view": (13845.772082, -12864.622462, 51419.112373, 8567.031916),
        "East_view": (59025.745772, -12864.622462, 88678.722533, 8567.031916),
}


def _sm25_view(view_id: str):
    xmin, ymin, xmax, ymax = SM25_FRAMES[view_id]
    return SimpleNamespace(
        id=view_id,
        clip_box_dxf=ClipBoxDxf(
            xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))


def test_sm25_three_declared_carriers_resolve_31_windows_and_3_doors():
    doc = ezdxf.readfile(SM25_SOURCE)
    rules = _sm25_rules(doc)
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    expected = {
        "West_view": (4, 2), "South_view": (7, 0),
        "North_view": (8, 0), "East_view": (12, 1),
    }
    actual = {}
    for view_id in SM25_FRAMES:
        view = _sm25_view(view_id)
        carriers, diagnostics = tn._resolve_opening_carriers(
            view, rules, doc.modelspace(), tols)
        assert diagnostics == []
        assert tn._audit_opening_carrier_consumption(
            view, rules, [], doc.modelspace(), carriers) == []
        windows = [carrier for carrier in carriers if carrier[1] == "window"]
        doors, door_diagnostics = tn._merge_door_carriers(
            [carrier for carrier in carriers if carrier[1] == "door"],
            rules, tols, view_id)
        assert door_diagnostics == []
        actual[view_id] = (len(windows), len(doors))
    assert actual == expected
    assert sum(counts[0] for counts in actual.values()) == 31
    assert sum(counts[1] for counts in actual.values()) == 3


def _sm25_resolve_all(doc, rules):
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    resolved = {}
    for view_id in SM25_FRAMES:
        view = _sm25_view(view_id)
        carriers, diagnostics = tn._resolve_opening_carriers(
            view, rules, doc.modelspace(), tols)
        assert diagnostics == []
        resolved[view_id] = (
            view, carriers,
            tn._audit_opening_carrier_consumption(
                view, rules, [], doc.modelspace(), carriers))
    return resolved


def test_l2_request_side_withdrawal_of_block_carriers_is_loud():
    doc = ezdxf.readfile(SM25_SOURCE)
    rules = _sm25_rules(doc)
    green = _sm25_resolve_all(doc, rules)
    assert all(not diagnostics for _view, _carriers, diagnostics in green.values())

    reduced = [rule for rule in rules if rule.outline.kind != "block_entity_rect"]
    red = _sm25_resolve_all(doc, reduced)
    diagnostics = [diagnostic for _view, _carriers, found in red.values()
                   for diagnostic in found]
    handles = [handle for diagnostic in diagnostics
               if diagnostic.code == "tarch_elevation_entities_unconsumed"
               for handle in diagnostic.source_entity_handles]
    assert len(handles) == 21
    assert len(set(handles)) == 21


def test_l3_removing_one_window_rule_lists_all_14_unconsumed_handles():
    doc = ezdxf.readfile(SM25_SOURCE)
    rules = _sm25_rules(doc)
    green = _sm25_resolve_all(doc, rules)
    assert all(not diagnostics for _view, _carriers, diagnostics in green.values())

    reduced = [rule for rule in rules
               if rule.carrier_id != "window-polyline-frame"]
    red = _sm25_resolve_all(doc, reduced)
    diagnostics = [diagnostic for _view, _carriers, found in red.values()
                   for diagnostic in found
                   if diagnostic.code == "tarch_elevation_entities_unconsumed"]
    handles = [handle for diagnostic in diagnostics
               for handle in diagnostic.source_entity_handles]
    assert len(handles) == 14
    assert len(set(handles)) == 14


def test_l5_duplicate_request_rules_double_consume_the_same_entity():
    doc = ezdxf.new("R2010")
    doc.layers.add("E_WINDOW")
    entity = doc.modelspace().add_lwpolyline(
        [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)],
        close=True, dxfattribs={"layer": "E_WINDOW"})
    view = SimpleNamespace(
        id="North_view",
        clip_box_dxf=ClipBoxDxf(xmin=-1.0, ymin=-1.0, xmax=5.0, ymax=4.0))
    first = OpeningCarrierRuleV1(
        carrier_id="polyline-a", opening_kind="window",
        match={"entity_type": "LWPOLYLINE", "layers": ["E_WINDOW"]},
        outline={"kind": "closed_polyline_rect"})
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    carriers, resolver_diagnostics = tn._resolve_opening_carriers(
        view, [first], doc.modelspace(), tols)
    assert resolver_diagnostics == []
    assert tn._audit_opening_carrier_consumption(
        view, [first], [], doc.modelspace(), carriers) == []

    duplicate = first.model_copy(update={"carrier_id": "polyline-b"})
    carriers, resolver_diagnostics = tn._resolve_opening_carriers(
        view, [first, duplicate], doc.modelspace(), tols)
    assert resolver_diagnostics == []
    diagnostics = tn._audit_opening_carrier_consumption(
        view, [first, duplicate], [], doc.modelspace(), carriers)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "tarch_elevation_entity_double_consumed"
    assert diagnostics[0].source_entity_handles == [entity.dxf.handle]
    assert diagnostics[0].context["consumers"] == {
        entity.dxf.handle: ["polyline-a", "polyline-b"]}


def test_explicit_ignore_is_exact_by_layer_and_entity_type():
    doc = ezdxf.new("R2010")
    doc.layers.add("E_WINDOW")
    ignored = doc.modelspace().add_circle(
        (1.0, 1.0), 0.25, dxfattribs={"layer": "E_WINDOW"})
    view = SimpleNamespace(
        id="East_view",
        clip_box_dxf=ClipBoxDxf(xmin=0.0, ymin=0.0, xmax=2.0, ymax=2.0))
    rules = [_line_rule()]
    red = tn._audit_opening_carrier_consumption(
        view, rules, [], doc.modelspace(), [])
    assert red[0].source_entity_handles == [ignored.dxf.handle]

    selector = tn.TarchEntitySelectorV1(
        entity_types=["CIRCLE"], layers=["E_WINDOW"])
    assert tn._audit_opening_carrier_consumption(
        view, rules, [selector], doc.modelspace(), []) == []


def test_new_ledger_diagnostics_are_blocking_g3_owners():
    for code in ("tarch_elevation_entities_unconsumed",
                 "tarch_elevation_entity_double_consumed"):
        spec = diagnostic_spec(code)
        assert spec.severity.value == "BLOCK"
        assert spec.gates == ("G3",)


def _run_sm24(tmp_path: Path, source_bytes: bytes | None = None):
    source = tmp_path / "source.dxf"
    source.parent.mkdir(parents=True, exist_ok=True)
    payload = SM24_SOURCE.read_bytes() if source_bytes is None else source_bytes
    source.write_bytes(payload)
    request = TarchConversionRequestV1.model_validate_json(SM24_REQUEST.read_text())
    if source_bytes is not None:
        draft = request.model_copy(update={
            "source_dxf_sha256": hashlib.sha256(payload).hexdigest()})
        request = draft.model_copy(update={
            "request_sha256": compute_request_sha256(draft)})
    result = tn.run_p2_conversion(
        source, request, request.plan_views[0], TOOLING, tmp_path / "work")
    return request, result


def test_sm24_legacy_translation_needs_no_ignore_declarations():
    request = TarchConversionRequestV1.model_validate_json(SM24_REQUEST.read_text())
    doc = ezdxf.readfile(SM24_SOURCE)
    tols = tn._Tols(0.001, 0.001, 0.001, 0.001)
    expected_ledger_counts = {
        "North_view": 6, "South_view": 9, "West_view": 20, "East_view": 14}
    actual = {}
    for view in request.elevation_views:
        rules = tn._opening_carrier_rules_for_view(request, view)
        ignores = tn._opening_ignore_selectors_for_view(request, view)
        assert ignores == []
        carriers, resolver_diagnostics = tn._resolve_opening_carriers(
            view, rules, doc.modelspace(), tols)
        assert resolver_diagnostics == []
        assert tn._audit_opening_carrier_consumption(
            view, rules, ignores, doc.modelspace(), carriers) == []
        layers = {layer for rule in rules for layer in rule.match.layers}
        actual[view.id] = len([
            entity for entity in doc.modelspace()
            if entity.dxf.layer in layers
            and tn._inside(entity, view.clip_box_dxf)])
    assert actual == expected_ledger_counts


def test_unknown_insert_on_declared_door_layer_blocks_g3_after_green_premise(
        tmp_path):
    _request, green = _run_sm24(tmp_path / "green")
    assert next(gate for gate in green.gates if gate.id == "G3").passed
    assert not any(diag.code == "tarch_elevation_entities_unconsumed"
                   for diag in green.diagnostics)

    doc = ezdxf.readfile(SM24_SOURCE)
    block = doc.blocks.new("UNDECLARED_DOOR_BLOCK")
    block.add_lwpolyline(
        [(-100.0, 0.0), (100.0, 0.0), (100.0, 200.0), (-100.0, 200.0)],
        close=True)
    insert = doc.modelspace().add_blockref(
        "UNDECLARED_DOOR_BLOCK", (25000.0, 5000.0),
        dxfattribs={"layer": "E_WINDOW"})
    altered = tmp_path / "altered.dxf"
    doc.saveas(altered)

    _request, red = _run_sm24(tmp_path / "red", altered.read_bytes())
    assert not next(gate for gate in red.gates if gate.id == "G3").passed
    diagnostics = [diag for diag in red.diagnostics
                   if diag.code == "tarch_elevation_entities_unconsumed"]
    assert len(diagnostics) == 1
    assert diagnostics[0].context["view_id"] == "South_view"
    assert diagnostics[0].source_entity_handles == [insert.dxf.handle]


def test_sm24_legacy_translation_is_observable_must_red(tmp_path, monkeypatch):
    _request, green = _run_sm24(tmp_path / "green")
    assert len(green.elevation_records) == 14
    assert next(gate for gate in green.gates if gate.id == "G9").passed

    monkeypatch.setattr(
        tn, "_translate_legacy_opening_carrier_rules", lambda _request, _view: [])
    _request, red = _run_sm24(tmp_path / "translation-off")
    assert red.elevation_records == []
    assert not next(gate for gate in red.gates if gate.id == "G9").passed
    assert any(diag.code == "tarch_v3_precondition" for diag in red.diagnostics)


def _legacy_sm24_carrier_reference(view, rules, msp, tols):
    """Test-only reference for the removed LINE + closed-door-block extraction."""
    carriers, diagnostics = [], []
    for rule in rules:
        if rule.outline.kind == "connected_line_group_rect":
            found, found_diagnostics = tn._resolve_connected_line_group_rect(
                view, rule, msp, tols)
            carriers.extend(found)
            diagnostics.extend(found_diagnostics)
            continue
        for insert in [entity for entity in msp
                       if entity.dxftype() == "INSERT"
                       and entity.dxf.layer in rule.match.layers
                       and entity.dxf.name == rule.match.block_name_exact
                       and tn._inside(entity, view.clip_box_dxf)]:
            block_entities = list(insert.doc.blocks.get(insert.dxf.name))
            roles = {item.entity_handle: item.role
                     for item in (rule.outline.block_entity_roles or [])}
            assert tn.elevation_block_definition_sha256(
                insert.doc, insert.dxf.name) == rule.match.block_definition_sha256
            assert set(roles) == {entity.dxf.handle for entity in block_entities}
            structural = [entity for entity in block_entities
                          if roles[entity.dxf.handle] == "structural_outline"]
            assert len(structural) == 1 and structural[0].dxftype() == "LWPOLYLINE"
            points = []
            for point in structural[0].get_points("xyseb"):
                world = insert.matrix44().transform((point[0], point[1], 0.0))
                points.append((float(world.x), float(world.y)))
            lines = [SimpleNamespace(dxf=SimpleNamespace(
                start=SimpleNamespace(x=points[index][0], y=points[index][1]),
                end=SimpleNamespace(
                    x=points[(index + 1) % len(points)][0],
                    y=points[(index + 1) % len(points)][1])))
                for index in range(len(points))]
            rect = tn._rect_from_lines(lines, tols.quant_native)
            assert rect is not None
            carriers.append((
                rule.carrier_id, "door", rect, (insert.dxf.handle,),
                (structural[0].dxf.handle,)))
    return carriers, diagnostics


def _assert_sm24_l1_equivalence(legacy, translated):
    assert len(legacy.elevation_records) == 14
    assert len(translated.elevation_records) == 14
    assert translated.elevation_records == legacy.elevation_records
    assert translated.augmented_dxf_path.read_bytes() \
        == legacy.augmented_dxf_path.read_bytes()


def test_sm24_legacy_translation_preserves_records_and_normalized_dxf_bytes(
        tmp_path, monkeypatch):
    production_resolver = tn._resolve_opening_carriers
    monkeypatch.setattr(
        tn, "_resolve_opening_carriers", _legacy_sm24_carrier_reference)
    _request, legacy = _run_sm24(tmp_path / "legacy-reference")
    monkeypatch.setattr(tn, "_resolve_opening_carriers", production_resolver)
    _request, translated = _run_sm24(tmp_path / "translated")

    _assert_sm24_l1_equivalence(legacy, translated)
