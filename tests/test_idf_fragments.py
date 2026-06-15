"""M1: unified IDF-fragment parser against real sm20_anchor MEP output."""

from __future__ import annotations

import json
from pathlib import Path

from src.validator.idf_fragments import (
    bundle_mep_text,
    parse_idf_text,
    parse_mep_fragments,
)

_MEP = Path("case_tests/e2e_tests/sm20_anchor/4_mep/mep_output.json")


def _load_mep() -> dict:
    return json.loads(_MEP.read_text(encoding="utf-8"))


def test_parse_real_mep_bundle():
    idx = parse_mep_fragments(_load_mep())
    assert idx.ok, idx.parse_error
    # The bundle should contain the canonical object types.
    assert idx.has_name("MATERIAL")
    assert idx.has_name("CONSTRUCTION")
    assert idx.has_name("SCHEDULE:COMPACT")
    # Cross-type name lookup works.
    assert "Default_Ext_Wall" in idx.has_name("CONSTRUCTION")


def test_bundle_text_includes_all_fragments():
    mep = _load_mep()
    text = bundle_mep_text(mep)
    assert "Material," in text
    assert "Construction," in text
    assert "Schedule:Compact," in text


def test_parse_error_is_reported_not_raised():
    idx = parse_idf_text("Construction,\n  Bad,\n  this is not valid idf @@@\n")
    # eppy is lenient; either it parses (ok) or records a parse_error — never raises.
    assert idx.parse_error is None or isinstance(idx.parse_error, str)


def test_extra_idf_folded_in():
    mep = _load_mep()
    geom = "Zone,\n  Z1,\n  0,0,0,0,0,1;\n"
    idx = parse_mep_fragments(mep, extra_idf=geom)
    assert idx.ok
    assert "Z1" in idx.has_name("ZONE")


def test_index_of_type_and_fields():
    idx = parse_mep_fragments(_load_mep())
    cons = idx.of_type("CONSTRUCTION")
    assert cons
    # A Construction's fields after the name are its material-layer references.
    ext = next(c for c in cons if c.name == "Default_Ext_Wall")
    assert len(ext.fields) >= 2  # name + at least one layer
