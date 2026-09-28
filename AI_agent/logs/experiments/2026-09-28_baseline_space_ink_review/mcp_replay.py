"""Developer-assisted saved-plan replay through the real MCP server; zero models."""
import asyncio
import base64
import json
import sys

from batch import HERE, TREE, dry_inputs, load, producer, save, sha


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    runner, prior, expected, modules, images = producer()
    folder = HERE / "mcp_replay"
    assert not folder.exists(), "Preserve prior replay"
    dry_inputs(runner, prior, expected, images, folder)
    save(folder / "developer_intervention.json", dict(model_calls=0,
        mode="saved_run86_plan_with_developer_selected_original_supported_revision",
        autonomous_quality_result=False, note="No GT is read. Other known geometry/height errors are intentionally not repaired."))
    source_plan = HERE.parent / "2026-09-28_sm21_evidence_feedback_run86/plan_drafts/draft_004/plan.json"
    old_plan_sha = sha(source_plan)
    # Exercise the mechanical budget port beyond the old sixth-candidate limit.
    for index in range(1, 7):
        (folder / f"candidate_{index:02}").mkdir()
    server = StdioServerParameters(command=sys.executable,
        args=[str(runner.__file__), "serve", str(folder)], cwd=str(TREE))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(name, arguments):
                reply = await session.call_tool(name, arguments)
                assert not reply.isError
                texts = [json.loads(item.text) for item in reply.content if item.type == "text"]
                assert len(texts) == 1
                result = texts[0]
                assert result.get("source_geometry_ready"), result
                assert next(iter(result)) == "space_ink_review"
                views = result["space_ink_views"]
                returned = [base64.b64decode(item.data) for item in reply.content if item.type == "image"]
                assert returned[:len(views)] == [(folder / view["file"]).read_bytes() for view in views]
                assert all(sha(folder / view["file"]) == view["sha256"] for view in views)
                save(folder / f"{name}_reply.json", result)
                return result
            before = await call("build_plan_bim", dict(image="2f_view.png", plan_json=source_plan.read_text()))
            assert before["candidate"] == "candidate_07"
            assert before["space_ink_review"]["stroke_count"] == 2
            assert [s["cross_pixels"] for s in before["space_ink_review"]["strokes"]] == [[1114,1114],[1125,1125]]
            record = before["plan_input"]
            evidence = ["Developer viewed original 2f_view.png full merged room; the vertical double line at x1114/1125 separates two rooms."]
            operations = [
                dict(op="add", collection="partitions", value=dict(id="P_bottom_center_review",
                    points=[[1119.5,790],[1119.5,1072]], source_refs=evidence),
                    reason="Developer-assisted replay: add original-supported missing divider only", source_refs=evidence),
                dict(op="add", collection="space_seeds", value=dict(id="B2e", point=[1300,930]),
                    reason="Name newly separated east room without moving the existing west seed", source_refs=evidence),
            ]
            save(folder / "developer_operations.json", operations)
            after = await call("revise_plan_bim", dict(draft_id="draft_001",
                expected_plan_sha256=record["plan_sha256"], operations_json=json.dumps(operations)))
    validate(folder, source_plan, prior, before, after, old_plan_sha)


def validate(folder, source_plan, prior, before, after, old_plan_sha):
    a = load(folder / before["candidate"] / "source_model.json")
    b = load(folder / after["candidate"] / "source_model.json")
    assert len(a["spaces"]) == 6 and len(b["spaces"]) == 7
    stable_openings = lambda source: [{k:v for k,v in opening.items()
        if k not in {"host_boundary_id", "space_ids"}} for opening in source["openings"]]
    assert stable_openings(a) == stable_openings(b) and len(a["openings"]) == 14
    remapped = [x["id"] for x,y in zip(a["openings"], b["openings"]) if x != y]
    assert remapped == ["D_B2e", "W_S3"]
    spaces_b = {s["id"]: s for s in b["spaces"]}
    preserved = [s["id"] for s in a["spaces"] if s["id"] != "B2"]
    assert all(s == spaces_b[s["id"]] for s in a["spaces"] if s["id"] in preserved)
    revised_plan = load(folder / "plan_drafts/draft_002/plan.json")
    original_plan = load(source_plan)
    assert revised_plan["openings"] == original_plan["openings"]
    assert revised_plan["partitions"][:-1] == original_plan["partitions"]
    assert revised_plan["space_seeds"][:-1] == original_plan["space_seeds"]
    assert after["space_ink_review"]["stroke_count"] == 0
    assert after["space_ink_review"]["drawing_fidelity"] == "not_evaluated"
    for result, source in [(before,a),(after,b)]:
        assert result["space_ink_review"]["source_model_sha256"] == source["source_model_sha256"]
    old_connections = {c["opening_id"]: c for c in a["connections"]}
    new_connections = {c["opening_id"]: c for c in b["connections"]}
    changed = [k for k,v in old_connections.items() if v != new_connections[k]]
    assert changed == ["D_B2e"], changed
    assert set(new_connections["D_B2e"]["space_ids"]) == {"B2e", "corridor2"}
    assert sha(source_plan) == old_plan_sha
    assert all(sha(folder / "images" / name) == entry["sha256"] for name,entry in prior["images"].items())
    report = dict(model_calls=0, real_stdio=True, manual_intervention=True,
        before_candidate=before["candidate"], after_candidate=after["candidate"],
        budget_beyond_six_checked=True, source_spaces_before=6, source_spaces_after=7,
        all_14_aperture_geometries_and_nonhost_fields_exactly_preserved=True,
        remapped_aperture_hosts=remapped, unchanged_spaces=preserved,
        changed_door_connections=changed, ink_strokes_before=2, ink_strokes_after=0,
        source_bound_feedback_and_returned_image_bytes_checked=True,
        original_images_and_saved_input_unchanged=True, drawing_fidelity="not_evaluated",
        conclusion="Feedback and existing local revision work through real MCP; the developer selected the wall, so autonomous adoption and whole-building quality remain untested.")
    save(HERE / "mcp_replay_report.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    if sys.argv[1:] == ["--audit-only"]:
        folder = HERE / "mcp_replay"
        before = load(folder / "build_plan_bim_reply.json")
        validate(folder,
            HERE.parent / "2026-09-28_sm21_evidence_feedback_run86/plan_drafts/draft_004/plan.json",
            load(folder / "inputs.json"), before, load(folder / "revise_plan_bim_reply.json"),
            before["plan_input"]["plan_sha256"])
    else:
        asyncio.run(main())
