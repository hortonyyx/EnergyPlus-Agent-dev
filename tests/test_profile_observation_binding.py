"""Saved profile candidates bind to facade slots without coordinate copying."""

import copy

import pytest

from src.agent.geometry.profile_observation_binding import resolve_observations


PLAN_SHA = "a" * 64
ELEVATION_SHA = "b" * 64


def _profile(*, name="plan.png", axis="y", image_sha=PLAN_SHA, candidates=None):
    return {
        "record": {
            "name": name,
            "image_sha256": image_sha,
            "axis": axis,
            "candidates": candidates or [
                {"id": "C01", "pixels": [170, 172], "peak": 171,
                 "max_count": 8},
                {"id": "C02", "pixels": [225, 228], "peak": 226,
                 "max_count": 9},
            ],
        },
        "sha256": "c" * 64,
    }


def _views():
    return {
        "plan": {"image": "plan.png", "axis": "y", "sha256": PLAN_SHA},
        "elevation": {
            "image": "east.png", "axis": "x", "sha256": ELEVATION_SHA,
        },
    }


def _raw():
    return {
        "experiment": {"preserved": [1, 2, 3]},
        "plan": {
            "axis_anchors": [
                [{"profile": "profile_001", "candidate": "C01", "at": "start"}, 0],
                [800, 20],
            ],
            "openings": [{
                "id": "P1",
                "pixels": [
                    {"profile": "profile_001", "candidate": "C01"},
                    {"profile": "profile_001", "candidate": "C02", "at": "end"},
                ],
                "kind": "window",
                "evidence": {"keep": True},
            }],
        },
        "elevation": {
            "axis_anchors": [[10, 0], [900, 20]],
            "openings": [{"id": "E1", "pixels": [100, 200]}],
        },
    }


def test_mixed_numeric_and_candidate_endpoints_bind_exactly_and_cache_once():
    raw = _raw()
    before = copy.deepcopy(raw)
    calls = []

    def load(profile_id):
        calls.append(profile_id)
        return _profile()

    resolved, bindings = resolve_observations(raw, load_profile=load, views=_views())

    assert calls == ["profile_001"]
    assert raw == before
    assert resolved["plan"]["axis_anchors"] == [[170, 0], [800, 20]]
    assert resolved["plan"]["openings"][0]["pixels"] == [171, 228]
    assert resolved["elevation"] == raw["elevation"]
    assert resolved["experiment"] == raw["experiment"]
    assert resolved["plan"]["openings"][0]["evidence"] == {"keep": True}
    assert [item["slot"] for item in bindings] == [
        "plan.axis_anchors[0][0]",
        "plan.openings[0].pixels[0]",
        "plan.openings[0].pixels[1]",
    ]
    assert [item["resolved_pixel"] for item in bindings] == [170, 171, 228]
    assert bindings[1]["reference"] == {
        "profile": "profile_001", "candidate": "C01",
    }
    assert bindings[1]["candidate"] == {
        "id": "C01", "pixels": [170, 172], "peak": 171,
        "selected_at": "peak",
    }
    assert bindings[1]["profile_sha256"] == "c" * 64
    assert bindings[1]["image_sha256"] == PLAN_SHA


def test_profile_can_bind_elevation_against_its_own_view():
    raw = _raw()
    raw["plan"]["axis_anchors"][0][0] = 0
    raw["plan"]["openings"][0]["pixels"] = [100, 200]
    raw["elevation"]["openings"][0]["pixels"][1] = {
        "profile": "profile_004", "candidate": "C02", "at": "end",
    }

    resolved, bindings = resolve_observations(
        raw,
        load_profile=lambda _: _profile(
            name="east.png", axis="x", image_sha=ELEVATION_SHA),
        views=_views(),
    )
    assert resolved["elevation"]["openings"][0]["pixels"] == [100, 228]
    assert bindings[0]["image"] == "east.png"
    assert bindings[0]["axis"] == "x"


@pytest.mark.parametrize(
    ("loaded", "match"),
    [
        (_profile(name="east.png"), "profile image"),
        (_profile(axis="x"), "profile axis"),
        (_profile(image_sha="d" * 64), "image sha256"),
    ],
)
def test_cross_image_axis_or_hash_binding_is_rejected(loaded, match):
    with pytest.raises(ValueError, match=match):
        resolve_observations(
            _raw(), load_profile=lambda _: loaded, views=_views())


def test_missing_or_duplicate_candidate_is_rejected():
    with pytest.raises(ValueError, match="exist exactly once"):
        resolve_observations(
            _raw(), load_profile=lambda _: _profile(candidates=[
                {"id": "other", "pixels": [1, 2], "peak": 1},
            ]), views=_views())
    duplicate = {"id": "C01", "pixels": [170, 172], "peak": 171}
    with pytest.raises(ValueError, match="exist exactly once"):
        resolve_observations(
            _raw(), load_profile=lambda _: _profile(candidates=[duplicate, duplicate]),
            views=_views())


@pytest.mark.parametrize(
    "reference",
    [
        {"profile": "profile_001", "candidate": "C01", "offset": 3},
        {"profile": "profile_001", "candidate": "C01", "pixel": 171},
        {"profile": "profile_001", "candidate": "C01", "at": "middle"},
        {"profile": "profile_001", "candidate": "C01", "at": ["peak"]},
    ],
)
def test_unknown_override_fields_and_unknown_at_are_rejected(reference):
    raw = _raw()
    raw["plan"]["axis_anchors"][0][0] = reference
    with pytest.raises(ValueError):
        resolve_observations(
            raw, load_profile=lambda _: _profile(), views=_views())


@pytest.mark.parametrize(
    "profile_id",
    ["../profile_001", "profile_01", "profile_001.json", "/tmp/profile_001"],
)
def test_profile_id_rejects_paths_and_noncanonical_stems(profile_id):
    raw = _raw()
    raw["plan"]["axis_anchors"][0][0]["profile"] = profile_id
    calls = []
    with pytest.raises(ValueError, match="profile_"):
        resolve_observations(
            raw, load_profile=lambda value: calls.append(value), views=_views())
    assert calls == []


@pytest.mark.parametrize(
    "candidate",
    [
        {"id": "C01", "pixels": [170, 172], "peak": 173},
        {"id": "C01", "pixels": [172, 170], "peak": 171},
        {"id": "C01", "pixels": [170, float("inf")], "peak": 171},
        {"id": "C01", "pixels": [170, 172], "peak": float("nan")},
        {"id": "C01", "pixels": [170, 172], "peak": True},
    ],
)
def test_invalid_candidate_coordinates_or_peak_are_rejected(candidate):
    with pytest.raises(ValueError):
        resolve_observations(
            _raw(), load_profile=lambda _: _profile(candidates=[candidate]),
            views=_views())


def test_legacy_numeric_observations_need_no_profiles_and_are_copied():
    raw = _raw()
    raw["plan"]["axis_anchors"][0][0] = 0
    raw["plan"]["openings"][0]["pixels"] = [170, 228]
    resolved, bindings = resolve_observations(
        raw,
        load_profile=lambda _: pytest.fail("numeric observations must not load profiles"),
        views={},
    )
    assert resolved == raw
    assert resolved is not raw
    assert bindings == []
