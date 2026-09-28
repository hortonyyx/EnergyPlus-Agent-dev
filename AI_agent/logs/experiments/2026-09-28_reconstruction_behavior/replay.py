"""Developer-selected two-object repair with existing tools, never a model run.

The developer has inspected the original South elevation and upper plan. This
demonstrates that a correct object/extent observation produces the intended local
result; it does not demonstrate autonomous discovery or restored whole-case quality.
"""
import json
import shutil
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.source_elevation_view import render_source_elevation
from .audit import extent

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "2026-09-28_sm21_historical_tree_run81"


def main():
    run = HERE / "developer_replay"
    run.mkdir(exist_ok=False)
    old_proposal_path = OLD / "candidate_04/proposal.json"
    old_source_path = OLD / "candidate_04/source_model.json"
    originals = {p: digest(p) for p in [old_proposal_path, old_source_path, *OLD.glob("images/*.png")]}
    manifest = json.loads((OLD / "inputs.json").read_text())
    shutil.copytree(OLD / "images", run / "images")
    dump(run / "inputs.json", dict(images=manifest["images"], max_candidates=3,
        provider="developer_offline", input_mode="developer_selected_deterministic_trace_replay",
        scope="Developer-selected repair of two known run81 window errors; no autonomous generation.",
        original_proposal_sha256=digest(old_proposal_path), model_calls=0))
    toolkit = Toolkit(run)
    proposal = json.loads(old_proposal_path.read_text())
    built = toolkit.build(proposal, action="developer_replay_existing_proposal")
    assert built.get("source_geometry_ready"), built
    parent = built["candidate"]
    source = json.loads((run / parent / "source_model.json").read_text())
    old_source = json.loads(old_source_path.read_text())
    for kind in ("floors", "boundaries", "openings", "connections"):
        assert source[kind] == old_source[kind], kind
    # Current export retains evidence and canonicalizes the historical role alias.
    # Compare every physical space field; do not mistake these known metadata
    # changes for a repair or suppress a geometric change.
    space_fields = ("id", "floor_id", "polygon", "height", "z_floor")
    assert [{k: s[k] for k in space_fields} for s in source["spaces"]] == [
        {k: s[k] for k in space_fields} for s in old_source["spaces"]]

    # The full original remains available; no old answer or GT drives the tools.
    toolkit.view("South_view.png", coordinate_grid=False)
    toolkit.view("2f_view.png", box=[1750, 560, 1970, 900], coordinate_grid=False)
    profile = json.loads(toolkit.view_profile("2f_view.png", [1780, 600, 1830, 800],
        "y", [0, 224, 224], 35, 0.02)[1])
    dump(run / "observed_profile.json", profile)
    # The developer identifies this whole cyan wall interruption as the window.
    # Profile arithmetic alone cannot identify an aperture or reject a mullion.
    bands = profile["candidates"]
    assert len(bands) == 1, bands
    band = bands[0]
    plan = json.loads((OLD / "plan_drafts/draft_002/plan.json").read_text())
    observations = [dict(candidate=parent, objects=[dict(kind="window", id="F1:W_S1")],
        basis="annotation_and_pixels", observation_mode="candidate_review",
        reason="Developer identifies the small lower South window separately from the two large windows. Its sill/head align with the left 1500/600/900 chain: from the 3 m floor line downward 900 to head, 600 window, 1500 to ground. Whole elevation retains both dimension ticks and frame context.",
        sources=[dict(image="South_view.png")], unresolved=[],
        values={"z": dict(type="dimension_chain", lengths=[900, 600, 1500], unit="mm", origin_m=3, direction=-1, segment=1)}),
        dict(candidate=parent, objects=[dict(kind="window", id="F2:W2F_East")],
        basis="pixels", observation_mode="candidate_review",
        reason="Developer follows the complete cyan interruption in the east wall of the upper-floor corridor. Its lower end continues beyond the old selected halfway point. Use both measured outer ends in the existing common plan frame; the adjacent 1200 label corroborates the full extent. The code does not infer this identity.",
        sources=[dict(image="2f_view.png", box=[1750, 560, 1970, 900])], unresolved=[],
        values={"span": dict(type="image_axis", image="2f_view.png", axis="y", anchors=plan["y_anchors"],
            pixels=[dict(profile=profile["profile_id"], candidate=band["id"], at=end) for end in ("start", "end")])})]
    operations = []
    for observation in observations:
        claim = toolkit.record_claim(json.dumps(observation))
        toolkit.decide_claim(claim["id"], "adopted", "Developer checked complete object and corresponding original evidence.")
        parameter, = observation["values"]
        operations.append(dict(op="update_window", id=observation["objects"][0]["id"],
            changes={parameter: dict(claim=claim["id"], value=parameter)},
            reason="Apply this object's reobserved extent, preserving unrelated geometry."))
    try:
        toolkit.confirm_claims(parent, json.dumps(operations))
    except ValueError as error:
        confirmation = dict(rejected=True, error=str(error))
    else:
        raise AssertionError("New observations differ from old source; confirmation must not pass")
    old_note, = [note for note in proposal["assumptions"] if note.startswith("South/East window heights (W_S1-3")]
    operations.append(dict(op="replace_note", field="assumptions", old=old_note,
        replacement=["Developer replay: F1:W_S1 alone now follows its South elevation 900/600/1500 chain. F1:W_S2, F1:W_S3 and F1:W_East retain their previous values and unchecked status; no whole-facade validation is claimed."],
        reason="The small window no longer shares the regular-family assumption.", source_refs=["claim_0001"]))
    revised = toolkit.revise(parent, json.dumps(operations))
    assert revised.get("source_geometry_ready"), revised
    candidate = revised["candidate"]
    after = json.loads((run / candidate / "source_model.json").read_text())
    changed = {"F1:W_S1", "F2:W2F_East"}
    checks = {}
    for kind in ("floors", "spaces", "boundaries", "connections"):
        checks[kind + "_unchanged"] = source[kind] == after[kind]
        assert checks[kind + "_unchanged"], kind
    before_openings = {o["id"]: o for o in source["openings"]}
    after_openings = {o["id"]: o for o in after["openings"]}
    assert before_openings.keys() == after_openings.keys()
    assert all(before_openings[k] == after_openings[k] for k in before_openings.keys() - changed)
    for identity in changed:
        for field in ("host_boundary_id", "space_ids", "kind", "exterior", "connectivity"):
            assert before_openings[identity].get(field) == after_openings[identity].get(field)
    assert extent(after_openings["F1:W_S1"])["z"] == [1.5, 2.1]
    span = extent(after_openings["F2:W2F_East"])["y"]
    assert abs(span[1] - span[0] - 1.2) < 0.04, span
    for name, src in [(parent, source), (candidate, after)]:
        pic, metadata = render_source_elevation(src, "South")
        pic.save(run / name / "elevation_South.png")
        dump(run / name / "elevation_South.json", metadata)
        toolkit.project_overlay(name, "2f_view.png", "F2", plan["x_anchors"], plan["y_anchors"],
            "Existing run81 calibration retained; developer checks local full opening extent.",
            trigger_action="developer_offline_repair_review")
    assert all(digest(path) == value for path, value in originals.items())
    toolkit.delivery(candidate, selection_origin="developer_selected_deterministic_trace_replay",
        generation_status={"state": "completed", "mode": "developer_offline_repair", "model_calls": 0})
    dump(HERE / "repair_result.json", dict(model_calls=0, mode="developer_selected_deterministic_trace_replay",
        candidate=candidate, confirmation_before_repair=confirmation,
        changes=[dict(id=k, before=extent(before_openings[k]), after=extent(after_openings[k])) for k in sorted(changed)],
        checks={**checks, "other_27_openings_unchanged": True, "all_opening_hosts_and_connections_unchanged": True,
                "historical_inputs_and_sources_unchanged": True},
        source_model_sha256=after["source_model_sha256"], old_source_sha256=digest(old_source_path),
        limits="Developer supplies identities/observations. Two local repairs only, not a new whole-case baseline or evidence of model adoption."))
    print(json.dumps({"candidate": candidate, "changed_openings": sorted(changed), "model_calls": 0}))


if __name__ == "__main__":
    main()
