"""The offline reading fixtures and the metrics computed over them.

What is worth locking here is not the metric arithmetic but the ACCEPTANCE RULE
the fixtures exist to serve: a reading gate is only worth having if every known-
good reading stays green under it and at least one known-bad reading goes red.
A gate that greens everything has no discriminating power; a gate that reds a
good fixture is a regression against a reading already known to be correct.

Each flag also gets a red-on-demand test, because a flag that has never been
observed firing is indistinguishable from one that is wired up wrong.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.tool_scripts import reading_process_metrics as rpm

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "case_tests" / "test_baseline" / "reading_fixtures.json"


def _fixtures() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))["fixtures"]


def _measure(fixture: dict) -> dict:
    paths = sorted((REPO / fixture["run"] / "0_reading").glob("*_view.json"))
    assert paths, f"fixture {fixture['id']} has no reading artifacts at {fixture['run']}"
    return rpm.measure(paths)


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda f: f["id"])
def test_fixture_artifacts_are_present(fixture):
    """A moved or deleted run must fail by name, not shrink the sample silently."""
    assert (REPO / fixture["run"]).is_dir(), fixture["run"]
    assert fixture["label"] in {"good", "bad"}
    assert fixture["why"].strip()


@pytest.mark.parametrize("fixture", [f for f in _fixtures() if f["label"] == "good"],
                         ids=lambda f: f["id"])
def test_no_good_reading_is_flagged_beyond_its_known_defects(fixture):
    """A good fixture may only red for a defect it declares.

    'good' turned out to be too coarse: 07-08 is 9/9 walls but 6/7 windows, and
    the chain-placement gate reds it for exactly the defect that cost it that
    window. Recording the defect keeps the fixture usable as a green baseline
    for every other gate without pretending the reading was flawless.
    """
    unexpected = rpm.unexpected_flags(rpm.flags(_measure(fixture)),
                                      fixture.get("known_defects"))
    assert unexpected == []


def test_declared_known_defects_actually_still_fire():
    """A known_defects entry that no longer fires is stale bookkeeping — it would
    silently widen what a good fixture is allowed to red for."""
    for fixture in _fixtures():
        declared = set(fixture.get("known_defects") or ())
        if not declared:
            continue
        raised = {rpm.flag_code(f) for f in rpm.flags(_measure(fixture))}
        assert declared <= raised, (
            f"{fixture['id']} declares {declared - raised} which no longer fires")


def test_at_least_one_bad_reading_is_flagged():
    """Discriminating power. Without this the flag set could be all-green."""
    reds = [f["id"] for f in _fixtures()
            if f["label"] == "bad" and rpm.flags(_measure(f))]
    assert reds, "no bad fixture goes red — the flag set has no discriminating power"


def test_known_bad_fixtures_stay_red():
    """The six that red today, pinned by name so a later change cannot quietly
    green one of them and still satisfy the 'at least one' rule above."""
    expected = {
        "sm21_2026-07-05_haiku_downgrade",   # zero windows on both plans
        "sm21_2026-08-15_A2",                # 0.24 m openings + inverted polarity
        "sm21_2026-08-15_D1_noprescan",      # 21 openings under 0.6 m
        "sm21_2026-08-16_F1_repro",          # zero windows on both plans
        "sm21_2026-08-18_J3",                # 0.20 m openings + a blank plan
        "sm21_2026-08-20_G1_gpt54mini",      # four chains that do not reach their overall
        "sm25_2026-08-21_T1_sonnet",         # F-69 polarity on the east wall
    }
    reds = {f["id"] for f in _fixtures()
            if f["label"] == "bad" and rpm.flags(_measure(f))}
    assert expected <= reds


def test_uncaught_bad_fixtures_are_declared_not_forgotten():
    """B1/E1/G1 are a known coverage gap. Keeping them listed here means the gap
    is registered rather than mistaken for 'nothing left to catch'."""
    known_gap = {
        "sm21_2026-08-15_B1_reviewring",
        "sm21_2026-08-16_E1_uncapped",
    }
    # Closing the gap is welcome — only the reverse, a bad fixture quietly
    # falling out of coverage, is a regression.
    unflagged = {f["id"] for f in _fixtures()
                 if f["label"] == "bad" and not rpm.flags(_measure(f))}
    assert unflagged <= known_gap, (
        f"a bad fixture stopped being caught without being declared: {unflagged - known_gap}"
    )


def _plan(strokes, dimensions=()):
    return {"image_kind": "plan", "strokes": list(strokes), "dimensions": list(dimensions)}


def _wall(x0, y0, x1, y1):
    return {"pen": "wall", "provenance": "seen", "note": "",
            "geometry": {"kind": "line", "p1": [x0, y0], "p2": [x1, y1]}}


def _window(lo, hi, at_y=0.0):
    return {"pen": "window", "provenance": "seen", "note": "",
            "geometry": {"kind": "rect", "x_range_m": [lo, hi], "y_range_m": [at_y, at_y + 0.24]}}


def test_polarity_flag_fires_on_an_inverted_wall():
    """Openings of wildly varying width separated by identical gaps: the shape a
    reader produces when it reports the piers instead of the openings."""
    view = _plan([_wall(0, 0, 20, 0),
                  _window(1.0, 2.4), _window(3.4, 6.2), _window(7.2, 8.0),
                  _window(9.0, 11.6)])
    findings = rpm._polarity_findings(view)
    assert len(findings) == 1 and findings[0]["openings"] == 4


def test_polarity_flag_silent_on_a_regular_wall():
    """Equal openings on a regular rhythm — the normal case — must not fire."""
    view = _plan([_wall(0, 0, 20, 0),
                  _window(1.0, 2.2), _window(5.0, 6.2), _window(9.0, 10.2),
                  _window(13.0, 14.2)])
    assert rpm._polarity_findings(view) == []


def test_narrow_opening_flag_fires_below_the_declared_floor():
    below = rpm.MIN_PLAUSIBLE_OPENING_M - 0.05
    view = _plan([_wall(0, 0, 20, 0), _window(1.0, 1.0 + below)])
    assert any("NARROW-OPENING" in f for f in rpm.flags(rpm.measure_views([view])))


def test_narrow_opening_flag_silent_at_the_declared_floor():
    at = rpm.MIN_PLAUSIBLE_OPENING_M + 0.05
    view = _plan([_wall(0, 0, 20, 0), _window(1.0, 1.0 + at)])
    assert not any("NARROW-OPENING" in f for f in rpm.flags(rpm.measure_views([view])))


def _chain(chain_id, overall_m, segments, axis="x"):
    """One transcribed chain: an overall plus placed segments."""
    dims = [{"chain_id": chain_id, "axis": axis, "role": "overall", "value_m": overall_m,
             "from": [0.0, 0.0], "to": [overall_m, 0.0]}]
    for order, (lo, hi) in enumerate(segments, start=1):
        dims.append({"chain_id": chain_id, "axis": axis, "role": "segment", "order": order,
                     "value_m": hi - lo, "from": [lo, 0.0], "to": [hi, 0.0]})
    return dims


def test_chain_placement_flag_silent_when_the_residual_is_placed():
    """07-07's shape: segments sum to 14.76 but a declared gap carries the 0.24 m
    residual, so the chain still lands on its declared 15.0 overall."""
    dims = _chain("C_top", 15.0, [(0.0, 5.0), (5.24, 15.0)])
    view = _plan([_wall(0, 0, 15, 0)], dims)
    assert rpm._chain_placement_findings(view) == []


def test_chain_placement_flag_fires_when_the_residual_is_dropped():
    """07-08's shape: same numbers butted end to end, so the chain stops short of
    the overall it declares and everything downstream drifts."""
    dims = _chain("C_top", 15.0, [(0.0, 5.0), (5.0, 14.76)])
    view = _plan([_wall(0, 0, 15, 0)], dims)
    found = rpm._chain_placement_findings(view)
    assert len(found) == 1 and found[0]["gap_m"] == 0.24


def test_chain_placement_flag_is_ordering_agnostic():
    """sm21's left chain is transcribed top-to-bottom and closes perfectly; a
    naive first.from -> last.to reading calls that a 3 m gap."""
    dims = [{"chain_id": "C_left", "axis": "y", "role": "overall", "value_m": 8.0,
             "from": [0.0, 0.0], "to": [0.0, 8.0]},
            {"chain_id": "C_left", "axis": "y", "role": "segment", "order": 1,
             "value_m": 3.0, "from": [0.0, 5.0], "to": [0.0, 8.0]},
            {"chain_id": "C_left", "axis": "y", "role": "segment", "order": 2,
             "value_m": 5.0, "from": [0.0, 0.0], "to": [0.0, 5.0]}]
    view = _plan([_wall(0, 0, 0, 8)], dims)
    assert rpm._chain_placement_findings(view) == []


def test_zero_product_flag_fires_on_a_windowless_plan():
    view = _plan([_wall(0, 0, 20, 0)], dimensions=[{"from": [0, 0], "to": [20, 0]}])
    assert any("ZERO-PRODUCT" in f for f in rpm.flags(rpm.measure_views([view])))
