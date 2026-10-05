"""Negative controls keep the platform-only ring normalization discriminating."""
import copy
import json
from pathlib import Path

import pytest

from tests.facts_equivalence import canonical_ring_origins


@pytest.fixture
def facts():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("change", ["coordinate", "witness", "classification", "source_hash", "cavity_group_order"])
def test_ring_normalization_keeps_every_fact(facts, change):
    changed = copy.deepcopy(facts)
    edge = changed["views"][0]["boundary_edges"][0]
    if change == "coordinate":
        edge["p1"][0] += 1
    elif change == "witness":
        edge["evidence"]["footprint_edge_id"] = "footprint:wrong:ring:0:edge:0"
    elif change == "classification":
        edge["boundary_condition"] = "changed"
    elif change == "source_hash":
        changed["source_dxf_sha256"] = "0" * 64
    else:
        groups = {}
        for item in changed["views"][0]["boundary_edges"]:
            groups.setdefault(item["cavity_id"], []).append(item)
        rings = list(groups.values())
        rings[0], rings[1] = rings[1], rings[0]
        changed["views"][0]["boundary_edges"] = [item for ring in rings for item in ring]
    assert canonical_ring_origins(changed) != canonical_ring_origins(facts)


@pytest.mark.parametrize("change", ["id", "sequence", "order", "interleaved_groups"])
def test_ring_normalization_rejects_invalid_identity_or_traversal(facts, change):
    edges = facts["views"][0]["boundary_edges"]
    if change == "id":
        edges[0]["id"] = "boundary-edge:0000000000000000"
    elif change == "sequence":
        edges[1]["sequence"] = edges[0]["sequence"]
    elif change == "order":
        edges[0], edges[1] = edges[1], edges[0]
    else:
        first_other = next(i for i, edge in enumerate(edges) if edge["cavity_id"] != edges[0]["cavity_id"])
        edges.insert(1, edges.pop(first_other))
    with pytest.raises(AssertionError):
        canonical_ring_origins(facts)
