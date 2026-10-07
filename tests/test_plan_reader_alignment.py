import asyncio
import copy
import hashlib
import json

from PIL import Image, ImageDraw

from src.agent.geometry.plan_dimension_alignment import align_plan_to_dimensions
from src.agent.geometry.plan_ink_alignment import align_plan_to_ink, move_straight_wall
from src.agent.runtime_roles.plan_format import plan_format_errors
from src.agent.runtime_roles import trial as trial_module
from src.agent.runtime_roles.trial import PlanTrial


def _plan():
    return {
        "floor_id": "F1",
        "z_floor": 0.0,
        "ceiling_height": 3.0,
        "x_anchors": [[20, 0.0], [200, 18.0]],
        "y_anchors": [[20, 14.0], [160, 0.0]],
        "basis": "synthetic reader alignment fixture",
        "footprint_pixels": [[22, 22], [198, 22], [198, 158], [22, 158]],
        "partitions": [
            {"id": "P1", "points": [[109, 22], [109, 158]], "source_refs": ["plan.png: divider"]},
            {"id": "P2", "points": [[22, 89], [109, 89]], "source_refs": ["plan.png: junction"]},
        ],
        "openings": [
            {"id": "D1", "kind": "door", "p1": [109, 74], "p2": [109, 106],
             "z": [0.0, 2.1], "source_refs": ["plan.png: door"], "state": "unknown"},
            {"id": "PASS1", "kind": "open", "p1": [109, 89], "p2": [109, 120],
             "z": [0.0, 3.0], "source_refs": ["plan.png: open passage"]},
        ],
        "space_seeds": [],
        "assumptions": [],
        "unresolved": [],
    }


def _drawing(with_ink=True):
    image = Image.new("RGB", (220, 180), "white")
    if with_ink:
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 200, 160), outline="black", width=2)
        draw.line((108, 20, 108, 75), fill="black")
        draw.line((108, 105, 108, 160), fill="black")
        draw.line((112, 20, 112, 75), fill="black")
        draw.line((112, 105, 112, 160), fill="black")
        draw.line((100, 75, 120, 75), fill="black")
        draw.line((100, 105, 120, 105), fill="black")
        draw.line((20, 88, 110, 88), fill="black")
        draw.line((20, 92, 110, 92), fill="black")
    return image


def test_ink_alignment_moves_wall_attached_opening_and_junction_to_supported_lines():
    aligned, report = align_plan_to_ink(_drawing(), _plan())

    assert aligned["footprint_pixels"] == [[20.0, 20.0], [200.0, 20.0],
                                            [200.0, 160.0], [20.0, 160.0]]
    assert aligned["partitions"][0]["points"] == [[110.0, 20.0], [110.0, 160.0]]
    assert aligned["partitions"][1]["points"][-1] == [110.0, 90.0]
    assert aligned["openings"][0]["p1"] == [110.0, 75.0]
    assert aligned["openings"][0]["p2"] == [110.0, 105.0]
    assert aligned["openings"][1]["p1"] == [110.0, 90.0]
    assert aligned["openings"][1]["p2"] == [110.0, 120.0]
    passage_item = next(row for row in report["items"] if row["object"] == "opening:PASS1")
    assert passage_item["action"] == "not_moved" and "passages" in passage_item["reason"]
    assert report["search"]["world_radius_m"] == 0.30
    assert report["summary"]["rejected"] == 0
    assert any(row["object"] == "partition:P1" and row["action"] == "moved"
               for row in report["items"])
    assert aligned["regularization_inputs"]["line_references"][0]["basis"] == "ink"


def test_wall_move_assigns_one_exact_coordinate_to_every_attached_endpoint():
    value = _plan()
    old_cross = value["partitions"][0]["points"][0][0]
    target = 0.1

    moved = move_straight_wall(
        value,
        collection="partitions",
        identity="P1",
        along_axis="y",
        old_cross=old_cross,
        new_cross=target,
        span=[22, 158],
    )

    coordinates = [
        *(point[0] for point in value["partitions"][0]["points"]),
        value["partitions"][1]["points"][-1][0],
        *(opening[field][0] for opening in value["openings"] for field in ("p1", "p2")),
    ]
    assert coordinates and all(coordinate == target for coordinate in coordinates)
    assert moved["junctions"] == ["P2:1"]
    assert moved["openings"] == ["D1", "PASS1"]


def test_reading_alignment_rolls_back_when_only_original_strictly_compiles(tmp_path, monkeypatch):
    image_path = tmp_path / "plan.png"
    _drawing().save(image_path)
    original = _plan()
    original["openings"] = []
    original["dimension_chains"] = [{
        "id": "X_OVERALL",
        "axis": "x",
        "segments_mm": [9000, 9000],
        "total_mm": 18000,
        "tick_pixels": [20, 110, 200],
        "source_refs": ["plan.png: dimensions"],
    }]

    def break_one_junction(_image, plan):
        aligned = copy.deepcopy(plan)
        aligned["partitions"][1]["points"][-1][0] = 105.0
        return aligned, {
            "schema_version": "test_alignment",
            "status": "applied",
            "summary": {"moved_or_aligned": 1, "not_moved": 0, "rejected": 0},
            "items": [],
            "rejections": [],
        }

    monkeypatch.setattr(trial_module, "align_plan_to_ink", break_one_junction)
    effective, reading, alignment = trial_module._reading_align(
        original, image_path=image_path, image_name="plan.png",
    )

    assert effective["partitions"][1]["points"][-1] == [109, 89]
    assert "dimension_chains" not in effective
    assert reading["ink"]["status"] == "applied"
    assert reading["dimensions"]["summary"]["chains_applied"] == 1
    assert alignment["status"] == "rolled_back_to_original"
    assert alignment["fallback"]["status"] == "applied"
    assert alignment["fallback"]["aligned_compile_error"]
    assert alignment["fallback"]["original_compile_error"] is None
    assert alignment["junction_preparation"]["preflight_only"] is True
    assert alignment["post_alignment_preparation"]["changes_applied_to_returned_plan"] is False


def test_missing_ink_never_moves_geometry_and_is_explicit():
    original = _plan()
    aligned, report = align_plan_to_ink(_drawing(with_ink=False), original)

    assert aligned["footprint_pixels"] == original["footprint_pixels"]
    assert aligned["partitions"] == original["partitions"]
    assert aligned["openings"] == original["openings"]
    assert report["status"] == "unchanged"
    assert any(row["action"] == "not_moved" and "no sufficiently long" in row["reason"]
               for row in report["items"] if row["kind"] in {"perimeter", "partition"})


def test_low_resolution_scan_never_applies_a_candidate_beyond_world_radius():
    image = Image.new("RGB", (12, 8), "black")
    draw = ImageDraw.Draw(image)
    for x in (5, 7):
        draw.line((x, 0, x, 7), fill=(128, 128, 128))
    value = {
        "floor_id": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
        "x_anchors": [[0, 0.0], [10, 6.0]],
        "y_anchors": [[0, 0.0], [6, 4.0]],
        "basis": "low resolution physical-radius regression",
        "footprint_pixels": [[0, 0], [10, 0], [10, 7], [0, 7]],
        "partitions": [{"id": "P1", "points": [[6, 1], [6, 7]],
                        "source_refs": ["plan.png: divider"]}],
        "openings": [], "space_seeds": [], "assumptions": [], "unresolved": [],
    }

    aligned, report = align_plan_to_ink(image, value)

    assert aligned["partitions"][0]["points"] == [[6, 1], [6, 7]]
    assert all(abs(row.get("movement_m", 0.0)) <= 0.30
               for row in report["items"] if row.get("action") == "moved")
    partition = next(row for row in report["items"] if row["object"] == "partition:P1")
    assert partition["action"] == "not_moved" and "physical search radius" in partition["reason"]


def test_overall_dimension_chain_sets_outer_face_axis_and_overrides_ink_priority():
    ink_aligned, _ = align_plan_to_ink(_drawing(), _plan())
    ink_aligned["dimension_chains"] = [{
        "id": "X_OVERALL", "axis": "x", "segments_mm": [9000, 9000],
        "total_mm": 18000, "tick_pixels": [20, 110, 200],
        "source_refs": ["plan.png: lower overall chain"],
    }]
    assert plan_format_errors(ink_aligned) == []

    aligned, report = align_plan_to_dimensions(ink_aligned)

    assert "dimension_chains" not in aligned
    assert aligned["x_anchors"] == [[20.0, 0.0], [200.0, 18.0]]
    assert aligned["partitions"][0]["points"][0][0] == 110.0
    line_ref = next(row for row in aligned["regularization_inputs"]["line_references"]
                    if row["partition_id"] == "P1")
    assert line_ref["basis"] == "dimension"
    coordinates = aligned["regularization_inputs"]["coordinate_references"]
    assert [row["value_m"] for row in coordinates] == [0.0, 9.0, 18.0]
    assert report["summary"]["chains_supplied"] == 1
    assert report["summary"]["chains_applied"] == 1
    assert report["summary"]["axes_calibrated"] == 1
    assert report["summary"]["partitions_snapped"] == 1
    assert report["summary"]["footprint_edges_snapped"] == 0
    assert report["summary"]["rejected"] == 0
    assert report["items"][0]["origin_basis"] == "legacy_anchor"
    assert report["items"][0]["anchor_cross_check"]["origin_basis"] == "legacy_anchor"
    assert report["items"][0]["anchor_cross_check"]["status"] == "consistent"
    audit = aligned["regularization_inputs"]["reading_alignment"]
    assert set(audit) == {"schema_version", "ink", "dimensions"}
    assert set(audit["dimensions"]) == {"summary", "items", "rejections", "search_or_tolerance"}


def test_dimension_chain_nonzero_origin_sets_both_axis_endpoints_and_audits_old_anchors():
    value = _plan()
    value["dimension_chains"] = [{
        "id": "X_WITH_ORIGIN", "axis": "x", "segments_mm": [9000, 9000],
        "total_mm": 18000, "tick_pixels": [22, 110, 198], "start_world_m": 125.5,
        "source_refs": [
            "plan.png: overall x dimension 9000/9000",
            "task coordinate contract: first west tick is world x=125.5 m",
        ],
    }]

    assert plan_format_errors(value) == []
    aligned, report = align_plan_to_dimensions(value)

    assert aligned["x_anchors"] == [[22.0, 125.5], [198.0, 143.5]]
    assert [row["value_m"] for row in aligned["regularization_inputs"]["coordinate_references"]] == [
        125.5, 134.5, 143.5,
    ]
    item = report["items"][0]
    assert item["origin_basis"] == "dimension_chain"
    cross_check = item["anchor_cross_check"]
    assert cross_check["origin_basis"] == "dimension_chain"
    assert cross_check["old_start_world_m"] == 0.2
    assert cross_check["dimension_start_world_m"] == 125.5
    assert cross_check["old_end_world_m"] == 17.8
    assert cross_check["dimension_end_world_m"] == 143.5
    assert cross_check["start_difference_m"] == 125.3
    assert cross_check["end_difference_m"] == 125.7
    assert cross_check["status"] == "warning"


def test_dimension_chain_origin_follows_first_tick_when_pixels_run_in_reverse():
    value = _plan()
    value["dimension_chains"] = [{
        "id": "Y_SOUTH_TO_NORTH", "axis": "y", "segments_mm": [7000, 7000],
        "total_mm": 14000, "tick_pixels": [158, 90, 22], "start_world_m": 0.0,
        "source_refs": [
            "plan.png: overall y dimension 7000/7000",
            "task coordinate contract: first south tick is world y=0 m and y increases northward",
        ],
    }]

    assert plan_format_errors(value) == []
    aligned, report = align_plan_to_dimensions(value)

    assert aligned["y_anchors"] == [[158.0, 0.0], [22.0, 14.0]]
    coordinates = aligned["regularization_inputs"]["coordinate_references"]
    assert [row["value_m"] for row in coordinates] == [0.0, 7.0, 14.0]
    assert report["items"][0]["outer_face_start"] == {"pixel": 158.0, "world_m": 0.0}
    assert report["items"][0]["origin_basis"] == "dimension_chain"


def test_dimension_chain_rejects_nonfinite_or_wrong_shape_origin_values():
    for invalid in (float("inf"), float("nan"), True, "0", [0.0]):
        value = _plan()
        original_anchors = copy.deepcopy(value["x_anchors"])
        value["dimension_chains"] = [{
            "id": "INVALID_ORIGIN", "axis": "x", "segments_mm": [18000],
            "total_mm": 18000, "tick_pixels": [22, 198], "start_world_m": invalid,
            "source_refs": ["plan.png: overall x dimension", "task coordinate contract"],
        }]

        assert plan_format_errors(value)
        aligned, report = align_plan_to_dimensions(value)

        assert aligned["x_anchors"] == original_anchors
        assert report["summary"]["chains_applied"] == 0
        assert report["summary"]["rejected"] == 1


def test_dimension_ticks_move_only_nearby_concave_footprint_edge_with_attached_objects():
    value = {
        "floor_id": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
        "x_anchors": [[0, 0.0], [200, 20.0]],
        "y_anchors": [[0, 16.0], [160, 0.0]],
        "basis": "concave dimension alignment fixture",
        "footprint_pixels": [[0, 0], [200, 0], [200, 160], [100.8, 160],
                             [100.8, 80], [0, 80]],
        "partitions": [{
            "id": "P_JUNCTION", "points": [[100.8, 120], [150, 120]],
            "source_refs": ["plan.png: partition meeting notch"],
        }],
        "openings": [{
            "id": "D_NOTCH", "kind": "door", "p1": [100.8, 95], "p2": [100.8, 115],
            "z": [0.0, 2.1], "source_refs": ["plan.png: door on notch wall"],
            "state": "unknown",
        }],
        "space_seeds": [], "assumptions": [], "unresolved": [],
        "dimension_chains": [{
            "id": "X_OVERALL_WITH_NOTCH", "axis": "x",
            "segments_mm": [10000, 10000], "total_mm": 20000,
            "tick_pixels": [0, 100, 200], "start_world_m": 0.0,
            "source_refs": [
                "plan.png: overall x chain 10000/10000",
                "task coordinate contract: first west tick is world x=0 m",
            ],
        }],
    }

    aligned, report = align_plan_to_dimensions(value)

    assert aligned["footprint_pixels"][3:5] == [[100.0, 160], [100.0, 80]]
    assert aligned["openings"][0]["p1"] == [100.0, 95]
    assert aligned["openings"][0]["p2"] == [100.0, 115]
    assert aligned["partitions"][0]["points"] == [[100.0, 120], [150, 120]]
    perimeter = next(row for row in report["changes"] if row["kind"] == "perimeter")
    assert perimeter["object"].startswith("footprint:")
    assert perimeter["chain_id"] == "X_OVERALL_WITH_NOTCH"
    assert perimeter["moved_with_wall"]["openings"] == ["D_NOTCH"]
    assert perimeter["moved_with_wall"]["junctions"] == ["P_JUNCTION:0"]
    assert report["summary"]["footprint_edges_snapped"] == 1
    assert report["summary"]["partitions_snapped"] == 0


def test_consistent_supplemental_overall_chain_adds_ticks_and_conflict_is_rejected():
    value = _plan()
    value["footprint_pixels"] = [[20, 20], [200, 20], [200, 160], [20, 160]]
    value["partitions"][0]["points"] = [[79, 20], [79, 160]]
    value["dimension_chains"] = [
        {
            "id": "X_PRIMARY", "axis": "x", "segments_mm": [9000, 9000],
            "total_mm": 18000, "tick_pixels": [20, 110, 200], "start_world_m": 0.0,
            "source_refs": ["plan.png: primary overall chain", "task origin contract"],
        },
        {
            "id": "X_SUPPLEMENT", "axis": "x", "segments_mm": [6000, 3000, 9000],
            "total_mm": 18000, "tick_pixels": [20, 80, 110, 200], "start_world_m": 0.0,
            "source_refs": ["plan.png: second overall chain", "task origin contract"],
        },
        {
            "id": "X_CONFLICT", "axis": "x", "segments_mm": [6000, 3000, 9000],
            "total_mm": 18000, "tick_pixels": [20, 80, 110, 200], "start_world_m": 1.0,
            "source_refs": ["plan.png: conflicting transcription", "task origin contract"],
        },
    ]

    aligned, report = align_plan_to_dimensions(value)

    assert aligned["x_anchors"] == [[20.0, 0.0], [200.0, 18.0]]
    assert aligned["partitions"][0]["points"] == [[80.0, 20], [80.0, 160]]
    supplement = next(row for row in report["items"] if row["chain_id"] == "X_SUPPLEMENT")
    assert supplement["action"] == "supplemental_ticks_applied"
    assert supplement["axis_cross_check"]["status"] == "consistent"
    conflict = next(row for row in report["rejections"] if row["chain_id"] == "X_CONFLICT")
    assert conflict["axis_cross_check"]["status"] == "conflict"
    assert report["summary"]["chains_applied"] == 2
    assert report["summary"]["axes_calibrated"] == 1
    assert report["summary"]["supplemental_chains_applied"] == 1
    assert report["summary"]["partitions_snapped"] == 1
    assert report["summary"]["rejected"] == 1


def test_bad_or_internal_dimension_chain_does_not_replace_axis():
    value = _plan()
    original_anchors = copy.deepcopy(value["x_anchors"])
    value["dimension_chains"] = [
        {"id": "BAD", "axis": "x", "segments_mm": [9000, 8000], "total_mm": 18000,
         "tick_pixels": [20, 110, 200], "source_refs": ["plan.png: bad transcription"]},
        {"id": "INTERNAL", "axis": "x", "segments_mm": [3000, 3000], "total_mm": 6000,
         "tick_pixels": [60, 90, 120], "source_refs": ["plan.png: internal chain"]},
    ]

    aligned, report = align_plan_to_dimensions(value)

    assert aligned["x_anchors"] == original_anchors
    assert report["summary"]["chains_applied"] == 0
    assert report["rejections"][0]["chain_id"] == "BAD"
    assert report["rejections"][0]["worst_segment_index"] in {0, 1}
    internal = next(row for row in report["items"] if row["chain_id"] == "INTERNAL")
    assert internal["action"] == "checked_not_applied"
    assert "outer faces" in internal["reason"]


def test_concave_footprint_uses_edge_normal_and_keeps_existing_geometry_inside():
    image = Image.new("RGB", (130, 130), "white")
    draw = ImageDraw.Draw(image)
    ring = [[20, 60], [20, 20], [100, 20], [100, 100], [60, 100], [60, 60]]
    draw.line([*map(tuple, ring), tuple(ring[0])], fill="black", width=1)
    # The notch's two wall faces straddle the declared representative.  For
    # this CCW edge the exterior is downward (+pixel y), even though the edge
    # lies above the footprint's global centroid.
    draw.line((20, 58, 60, 58), fill="black")
    draw.line((20, 62, 60, 62), fill="black")
    value = {
        "floor_id": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
        "x_anchors": [[20, 0.0], [100, 8.0]],
        "y_anchors": [[20, 8.0], [100, 0.0]],
        "basis": "concave regression", "footprint_pixels": copy.deepcopy(ring),
        "partitions": [
            {"id": "near_notch", "points": [[20, 59], [60, 59]],
             "source_refs": ["plan.png: nearby interior wall"]},
            {"id": "notch_continuation", "points": [[60, 60], [90, 60]],
             "source_refs": ["plan.png: continuation from notch"]},
            {"id": "far_branch", "points": [[90, 60], [90, 90]],
             "source_refs": ["plan.png: branch at continuation end"]},
        ],
        "openings": [], "space_seeds": [], "assumptions": [], "unresolved": [],
    }

    aligned, report = align_plan_to_ink(image, value)

    assert aligned["footprint_pixels"][0][1] == 62.0
    assert aligned["footprint_pixels"][5][1] == 62.0
    continuation = next(row for row in aligned["partitions"] if row["id"] == "notch_continuation")
    branch = next(row for row in aligned["partitions"] if row["id"] == "far_branch")
    assert continuation["points"] == [[60, 62.0], [90, 62.0]]
    assert branch["points"] == [[90, 62.0], [90, 90]]
    assert all(first[0] == second[0] or first[1] == second[1]
               for partition in aligned["partitions"]
               for first, second in zip(partition["points"], partition["points"][1:]))
    edge = next(row for row in report["items"] if row["object"] == "footprint:5")
    assert edge["action"] == "moved" and edge["aligned_pixel"] == 62.0
    assert edge["moved_with_wall"]["walls"] == ["notch_continuation"]
    assert not any(row.get("object") == "footprint:5" for row in report["rejections"])


def test_trial_compiles_aligned_numeric_plan_and_returns_only_compact_summary(tmp_path):
    workspace = tmp_path / "trial"
    (workspace / "images").mkdir(parents=True)
    _drawing().save(workspace / "images" / "plan.png")

    class Tools:
        async def call_tool(self, name, arguments):
            assert name == "build_plan_bim"
            submitted = json.loads(arguments["plan_json"])
            effective = copy.deepcopy(submitted)
            effective["regularization"] = {
                "rule_version": "plan_regularization_v1", "changes": [], "rejections": [],
            }
            draft = workspace / "plan_drafts" / "draft_001"
            draft.mkdir(parents=True)
            effective_path = draft / "plan.json"
            effective_path.write_text(
                json.dumps(effective, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n",
            )
            raw = effective_path.read_bytes()
            candidate = workspace / "candidate_01"
            candidate.mkdir()
            (candidate / "source_model.json").write_text(
                json.dumps({"spaces": [], "boundaries": []}), encoding="utf-8", newline="\n",
            )
            return {"structuredContent": {
                "source_geometry_ready": True,
                "candidate": "candidate_01",
                "plan_input": {"plan_file": "plan_drafts/draft_001/plan.json",
                               "plan_sha256": hashlib.sha256(raw).hexdigest(),
                               "image": "plan.png",
                               "regularization": {"rule_version": "plan_regularization_v1",
                                                  "status": "passed"}},
                "drawing_differences": {"status": "reported", "total": 0, "items": []},
                "building_precision": {"status": "reported", "items": []},
            }, "content": []}

        def image_origins(self, raw):
            return {}

    value = _plan()
    value["dimension_chains"] = [{
        "id": "X_OVERALL", "axis": "x", "segments_mm": [9000, 9000],
        "total_mm": 18000, "tick_pixels": [20, 110, 200], "source_refs": ["plan.png: dimensions"],
    }]

    async def scenario():
        trial = PlanTrial(Tools(), image_name="plan.png", workspace=workspace,
                          receipt_directory=workspace / "trial_receipts")
        envelope = await trial.call(value)
        receipt = trial.receipts[-1]
        assert receipt["status"] == "passed"
        assert receipt["reading_alignment"]["ink"]["items"]
        assert receipt["reading_alignment"]["dimensions"]["summary"]["chains_applied"] == 1
        visible = envelope["structuredContent"]["reading_alignment"]
        assert "items" not in visible["ink"] and "full_list" in visible
        numeric = trial.numeric_plan(receipt)
        assert receipt["unaligned_numeric_input_file"] != receipt["aligned_numeric_input_file"]
        unaligned = json.loads(
            (workspace / receipt["unaligned_numeric_input_file"]).read_text(encoding="utf-8")
        )
        assert unaligned["partitions"][0]["points"][0][0] == 109
        assert receipt["aligned_numeric_input_file"] != receipt["compiled_numeric_plan_file"]
        aligned_input = json.loads(
            (workspace / receipt["aligned_numeric_input_file"]).read_text(encoding="utf-8")
        )
        assert "regularization" not in aligned_input
        assert receipt["compiled_numeric_plan_sha256"] == receipt["compiled_plan_sha256"]
        assert "dimension_chains" not in numeric
        assert numeric["regularization"]["rule_version"] == "plan_regularization_v1"
        assert numeric["partitions"][0]["points"][0][0] == 110.0
        assert numeric["regularization_inputs"]["reading_alignment"]["dimensions"]["items"]

    asyncio.run(scenario())


def test_trial_rejects_unverified_regularized_toolkit_plan(tmp_path):
    workspace = tmp_path / "trial"
    (workspace / "images").mkdir(parents=True)
    _drawing().save(workspace / "images" / "plan.png")

    class Tools:
        async def call_tool(self, name, arguments):
            draft = workspace / "plan_drafts" / "draft_001"
            draft.mkdir(parents=True)
            (draft / "plan.json").write_text(arguments["plan_json"], encoding="utf-8", newline="\n")
            return {"structuredContent": {
                "source_geometry_ready": True,
                "candidate": "candidate_01",
                "plan_input": {
                    "plan_file": "plan_drafts/draft_001/plan.json",
                    "plan_sha256": "0" * 64,
                    "image": "plan.png",
                    "regularization": {"rule_version": "plan_regularization_v1",
                                       "status": "passed"},
                },
            }, "content": []}

        def image_origins(self, raw):
            return {}

    async def scenario():
        trial = PlanTrial(Tools(), image_name="plan.png", workspace=workspace,
                          receipt_directory=workspace / "trial_receipts")
        receipt = await trial.run(_plan())
        assert receipt["status"] == "failed"
        assert "Toolkit effective plan changed or is missing" in receipt["reason"]
        assert receipt["aligned_numeric_input_file"]
        assert receipt["compiled_numeric_plan_file"] is None
        assert receipt["compiled_numeric_plan_sha256"] is None

    asyncio.run(scenario())
