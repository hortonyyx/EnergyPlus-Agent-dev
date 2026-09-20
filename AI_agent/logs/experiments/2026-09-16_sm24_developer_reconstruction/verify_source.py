"""Offline source replay, opening provenance, connectivity and browser checks."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import tempfile

from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.execution.source_proposal import export_source_proposal


def main():
    source_path = HERE / "candidate_01/source_model.json"
    source = json.loads(source_path.read_text())
    plan = json.loads((HERE / "plan_final.json").read_text())
    proposal, mapping = compile_plan_partition(plan, image_size=(790, 1111), image_name="1f_view.png")
    assert proposal == json.loads((HERE / "candidate_01/proposal.json").read_text())
    assert mapping == json.loads((HERE / "compilation.json").read_text())
    with tempfile.TemporaryDirectory(prefix="sm24_source_replay_") as temporary:
        out = Path(temporary) / "candidate"
        replay = export_source_proposal(proposal, out, provenance=source["generation"]["provenance"])
        assert replay["source_geometry_ready"]
        assert (out / "source_model.json").read_bytes() == source_path.read_bytes()
        assert (out / "display_geometry.json").read_bytes() == (HERE / "candidate_01/display_geometry.json").read_bytes()
    no_seeds, no_seed_mapping = compile_plan_partition(dict(plan, space_seeds=[]),
        image_size=(790, 1111), image_name="1f_view.png")
    assert no_seed_mapping["space_count"] == mapping["space_count"] == len(source["spaces"])
    faces = [Polygon(space["polygon"]) for space in source["spaces"]]
    area_sum = sum(face.area for face in faces)
    union_area = unary_union(faces).area
    assert abs(area_sum - union_area) < 1e-8 and abs(union_area - 200) < 1e-8
    assert source["validation"]["status"] == "pass"
    assert not source["unbuilt_openings"] and not source["unsupported"]
    by_id = {item["id"]: item for item in source["openings"]}
    opening_checks = []
    sx = 10 / (plan["x_anchors"][1][0] - plan["x_anchors"][0][0])
    sy = -20 / (plan["y_anchors"][1][0] - plan["y_anchors"][0][0])
    for item in plan["openings"]:
        built = by_id[item["id"]]
        assert built["kind"] == item["kind"]
        expected = sorted((round((point[0] - plan["x_anchors"][0][0]) * sx, 9),
                           round(20 + (point[1] - plan["y_anchors"][0][0]) * sy, 9))
                          for point in [item["p1"], item["p2"]])
        actual = sorted(set((round(v[0], 9), round(v[1], 9)) for v in built["vertices"]))
        assert len(expected) == len(actual)
        # The compiler explicitly serializes metric coordinates to six decimals.
        error = max(abs(a - b) for ep, ap in zip(expected, actual) for a, b in zip(ep, ap))
        assert error <= 0.000000501, (item["id"], expected, actual)
        assert sorted(set(v[2] for v in built["vertices"])) == item["z"]
        opening_checks.append({"id": item["id"], "kind": item["kind"],
                               "plan_projection_preserved": True, "height_preserved": True,
                               "metric_serialization_error_m": error,
                               "space_ids": built["space_ids"]})
    graph = {space["id"]: set() for space in source["spaces"]}
    graph["OUTSIDE"] = set()
    for connection in source["connections"]:
        nodes = list(connection["space_ids"])
        if connection["exterior"]:
            nodes.append("OUTSIDE")
        assert len(nodes) == 2
        graph[nodes[0]].add(nodes[1]); graph[nodes[1]].add(nodes[0])
    reached, queue = set(), ["OUTSIDE"]
    while queue:
        node = queue.pop()
        if node not in reached:
            reached.add(node); queue.extend(graph[node] - reached)
    assert reached == set(graph)

    from playwright.sync_api import sync_playwright
    errors, external, failed = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        context = browser.new_context(viewport={"width": 1500, "height": 1000}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        page.on("requestfailed", lambda request: failed.append(request.url))
        page.goto((HERE / "candidate_01/viewer.html").as_uri())
        page.wait_for_function("window.GEO && document.querySelector('canvas')")
        embedded = page.evaluate("GEO.source_model.source_model_sha256")
        assert embedded == source["source_model_sha256"]
        page.locator("#opacity").fill("0.45")
        page.locator("#opacity").dispatch_event("input")
        page.wait_for_timeout(300)
        canvas = page.locator("#app canvas")
        before = canvas.screenshot()
        page.mouse.move(850, 370); page.mouse.down()
        page.mouse.move(990, 435, steps=12); page.mouse.up()
        page.wait_for_timeout(300)
        after = canvas.screenshot()
        assert before != after, "rotation did not change canvas"
        page.screenshot(path=str(HERE / "viewer_verified.png"))
        browser.close()
    assert not errors and not external and not failed, (errors, external, failed)
    report = {"source_model_sha256": source["source_model_sha256"],
        "exact_source_and_display_replay": True, "compiler_replay": True,
        "unseeded_face_count": no_seed_mapping["space_count"],
        "space_seeds_do_not_create_partitions": True,
        "footprint_area_m2": union_area, "overlap_area_m2": area_sum - union_area,
        "opening_counts": dict(Counter(x["kind"] for x in source["openings"])),
        "openings": opening_checks, "all_spaces_reachable_through_declared_doors": True,
        "offline_browser": {"embedded_source_hash_matches": True, "rotation_changes_canvas": True,
                            "page_errors": errors, "external_requests": external, "failed_requests": failed},
        "limits": "Self-consistency, exact observation application and display; these do not establish GT fidelity or target-model autonomy."}
    (HERE / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"openings"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
