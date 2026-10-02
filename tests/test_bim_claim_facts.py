from src.agent.execution.bim_claim_facts import claim_facts

PROPOSAL = {"geometry": {
    "floors": [{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
                "cells": [{"id": "F1:A"}, {"id": "F1:B"}]}],
    "windows": [
        # width_m is an optional cache that span edits do not update; facts use span.
        {"id": "F1:WN", "floor": "F1", "facade": "North", "span": [1.0, 3.4], "width_m": 9.9, "z": [1.0, 2.6]},
        {"id": "F1:WS", "floor": "F1", "facade": "South", "span": [2.0, 3.2], "z": [1.0, 2.6]}],
    "openings": [{"id": "F1:D", "kind": "door", "space_id": "F1:A", "other_space_id": None,
                  "p1": [0.0, 0.0], "p2": [0.9, 0.0], "z": [0.0, 2.1]}]}}


def row(values, computations, value_targets=None):
    claim = {"objects": [{"kind": "window", "id": "F1:WN"}, {"kind": "window", "id": "F1:WS"},
                         {"kind": "opening", "id": "F1:D"}], "values": values}
    if value_targets is not None:
        claim["value_targets"] = value_targets
    return {"claim": claim, "computations": computations,
            "resolved_values": {name: [1.0, 2.6] for name in values}}


CHAIN = {"method": "dimension_chain", "segment": 1,
         "chain": {"total_m": 3.6, "origin_m": 0.0, "end_m": 3.6}}


def test_chain_span_and_every_applied_object_are_listed_without_a_verdict():
    facts = claim_facts(row({"height": {}}, {"height": CHAIN}), PROPOSAL)
    value = facts["values"][0]
    assert value["chain_total_m"] == 3.6 and value["chain_range_m"] == [0.0, 3.6]
    assert [a["id"] for a in value["applied_to"]] == ["F1:WN", "F1:WS", "F1:D"]
    assert [a["width_m"] for a in value["applied_to"]] == [2.4, 1.2, 0.9]
    assert value["applied_to"][2]["host"] == "exterior"
    assert value["chain_and_floor_to_ceiling"] == [
        {"floor": "F1", "floor_to_ceiling_m": (0.0, 3.0), "chain_range_m": [0.0, 3.6], "same_range": False}]
    assert len(value["distinct_floor_host_width"]) == 3
    assert "need not span a whole floor" in facts["note"]


def test_width_is_unknown_rather_than_zero_without_geometry():
    proposal = {"geometry": {**PROPOSAL["geometry"], "windows": [
        {"id": "F1:WN", "floor": "F1", "facade": "North", "z": [1.0, 2.6]}]}}
    facts = claim_facts(row({"height": {}}, {"height": CHAIN}, {"height": [{"kind": "window", "id": "F1:WN"}]}), proposal)
    assert facts["values"][0]["applied_to"][0]["width_m"] is None


def test_value_targets_limit_the_listed_objects():
    targets = {"height": [{"kind": "window", "id": "F1:WN"}]}
    facts = claim_facts(row({"height": {}}, {"height": CHAIN}, targets), PROPOSAL)
    assert [a["id"] for a in facts["values"][0]["applied_to"]] == ["F1:WN"]
    literal = claim_facts(row({"z": {}}, {"z": {"method": "explicit_metric_value"}}), PROPOSAL)
    assert "chain_total_m" not in literal["values"][0]
