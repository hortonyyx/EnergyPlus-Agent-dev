"""Independent deterministic and offline-browser QA for candidate_03.

The checks intentionally separate source self-consistency, retention from the
09-15 candidate, exact proposal/assembly replay, roof-interface semantics, and
visual transport.  No check treats the inferred interior as observed truth.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent / "2026-09-15_voimatalo_developer_walkthrough"
DEFAULT_BASELINE = OLD / "candidate_02"
DEFAULT_MESH = ROOT / "case_tests/textured_mass/single_buildings/voimatalo/input.glb"
DEFAULT_DIRECTION = OLD / "evidence_01/direction.json"
OLD_VALIDATOR = OLD / "validation/verify_candidate.py"
TOLERANCE_M = 1e-7
TOLERANCE_M2 = 1e-6
sys.path.insert(0, str(ROOT))

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_model import _digest


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_paths(value: Path) -> tuple[Path, Path]:
    value = value.resolve()
    directory = value if value.is_dir() else value.parent
    source_path = directory / "source_model.json" if value.is_dir() else value
    if not source_path.is_file():
        raise FileNotFoundError(f"candidate source_model.json not found: {source_path}")
    return directory, source_path


def check_source_export_replay(candidate_dir: Path, source_path: Path, source: dict) -> dict:
    proposal_path = candidate_dir / "proposal.json"
    report_path = candidate_dir / "report.json"
    if not proposal_path.is_file() or not report_path.is_file():
        return {"status": "fail", "error": "proposal.json or report.json missing"}
    proposal = read_json(proposal_path)
    candidate_report = read_json(report_path)
    provenance = candidate_report.get("provenance")
    stored = source.get("source_model_sha256")
    calculated = _digest({key: value for key, value in source.items()
                          if key != "source_model_sha256"})
    with tempfile.TemporaryDirectory(prefix="voimatalo-source-replay-") as temp:
        replay_dir = Path(temp) / "candidate"
        replay_report = export_source_proposal(proposal, replay_dir, provenance=provenance)
        replay_path = replay_dir / "source_model.json"
        if not replay_path.is_file():
            return {"status": "fail", "error": replay_report.get("error", "source missing")}
        replay = read_json(replay_path)
        exact_json = replay == source
        exact_bytes = replay_path.read_bytes() == source_path.read_bytes()
        replay_digest = replay.get("source_model_sha256")
        return {
            "status": "pass" if (
                stored == calculated == replay_digest and exact_json and exact_bytes
            ) else "fail",
            "stored_digest": stored,
            "calculated_digest": calculated,
            "replayed_digest": replay_digest,
            "exact_json": exact_json,
            "exact_source_model_bytes": exact_bytes,
            "source_file_sha256": sha256(source_path),
            "replayed_source_file_sha256": sha256(replay_path),
            "temporary_directory_removed_after_check": True,
        }


def polygon_for_space(space: dict) -> Polygon:
    polygon = Polygon(space["polygon"])
    if polygon.is_empty or not polygon.is_valid or polygon.area <= TOLERANCE_M2:
        raise ValueError(f"invalid source-space polygon: {space.get('id')}")
    return polygon


def check_no_overlap(source: dict) -> dict:
    spaces = source["spaces"]
    polygons = {space["id"]: polygon_for_space(space) for space in spaces}
    overlaps = []
    for index, first in enumerate(spaces):
        first_top = float(first["z_floor"]) + float(first["height"])
        for second in spaces[index + 1:]:
            second_top = float(second["z_floor"]) + float(second["height"])
            vertical = min(first_top, second_top) - max(
                float(first["z_floor"]), float(second["z_floor"])
            )
            if vertical <= TOLERANCE_M:
                continue
            area = polygons[first["id"]].intersection(polygons[second["id"]]).area
            if area > TOLERANCE_M2:
                overlaps.append({
                    "space_ids": [first["id"], second["id"]],
                    "vertical_overlap_m": float(vertical),
                    "plan_overlap_m2": float(area),
                })
    return {"status": "pass" if not overlaps else "fail", "overlaps": overlaps}


def opening_projection(row: dict) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "vertices": row["vertices"],
        "space_ids": row.get("space_ids", []),
    }


def check_opening_retention(candidate: dict, baseline: dict) -> dict:
    current = {row["id"]: row for row in candidate["openings"]}
    previous = {row["id"]: row for row in baseline["openings"]}
    previous_windows = {key: row for key, row in previous.items() if row["kind"] == "window"}
    missing_windows = sorted(set(previous_windows) - set(current))
    changed_windows = sorted(
        key for key in set(previous_windows) & set(current)
        if opening_projection(previous_windows[key]) != opening_projection(current[key])
    )
    previous_doors = {key: row for key, row in previous.items() if row["kind"] == "door"}
    missing_doors = sorted(set(previous_doors) - set(current))
    changed_doors = sorted(
        key for key in set(previous_doors) & set(current)
        if opening_projection(previous_doors[key]) != opening_projection(current[key])
    )
    door_change_details = []
    for key in changed_doors:
        old_vertices = np.asarray(previous_doors[key]["vertices"], dtype=float)
        new_vertices = np.asarray(current[key]["vertices"], dtype=float)
        door_change_details.append({
            "id": key,
            "xy_changed": not np.array_equal(old_vertices[:, :2], new_vertices[:, :2]),
            "old_z_m": sorted(set(old_vertices[:, 2].tolist())),
            "new_z_m": sorted(set(new_vertices[:, 2].tolist())),
            "old_xy_m": sorted(set(map(tuple, old_vertices[:, :2].tolist()))),
            "new_xy_m": sorted(set(map(tuple, new_vertices[:, :2].tolist()))),
            "old_space_ids": previous_doors[key].get("space_ids", []),
            "new_space_ids": current[key].get("space_ids", []),
        })
    added = sorted(set(current) - set(previous))
    added_windows = [key for key in added if current[key]["kind"] == "window"]
    added_doors = [key for key in added if current[key]["kind"] == "door"]
    return {
        "status": "pass" if not missing_windows and not changed_windows else "fail",
        "comparison_fields": ["id", "kind", "vertices", "space_ids"],
        "baseline_window_count": len(previous_windows),
        "candidate_window_count": sum(row["kind"] == "window" for row in current.values()),
        "preserved_window_count": len(previous_windows) - len(missing_windows) - len(changed_windows),
        "missing_window_ids": missing_windows,
        "changed_window_ids": changed_windows,
        "added_window_ids": added_windows,
        "door_changes_are_reported_but_do_not_fail_window_retention": True,
        "baseline_door_count": len(previous_doors),
        "candidate_door_count": sum(row["kind"] == "door" for row in current.values()),
        "missing_door_ids": missing_doors,
        "changed_door_ids": changed_doors,
        "changed_door_details": door_change_details,
        "added_door_ids": added_doors,
    }


def check_proposal_openings(
    candidate_dir: Path, source: dict, plan_path: Path, apertures_path: Path
) -> dict:
    proposal = read_json(candidate_dir / "proposal.json")
    declared = (
        proposal["geometry"].get("windows", [])
        + proposal["geometry"].get("openings", [])
    )
    declared_ids = {row["id"] for row in declared}
    built_ids = {row["id"] for row in source["openings"]}
    mapping_path = candidate_dir / "opening_mapping.json"
    mappings = read_json(mapping_path) if mapping_path.is_file() else []
    mapping_ids = {row["id"] for row in mappings}
    declared_window_ids = {
        row["id"] for row in proposal["geometry"].get("windows", [])
    }
    observed_document = read_json(apertures_path)
    observed = (
        observed_document.get("openings", [])
        if isinstance(observed_document, dict) else observed_document
    )
    plan = read_json(plan_path)
    expected_observation_ids = {row["id"] for row in observed} | {
        row["id"] for row in plan.get("additional_openings", [])
    }
    return {
        "status": "pass" if (
            not source.get("unbuilt_openings")
            and declared_ids == built_ids
            and expected_observation_ids == mapping_ids == declared_window_ids
            and all(row.get("owner") for row in mappings)
        ) else "fail",
        "input_aperture_observation_count": len(observed),
        "case_plan_additional_opening_count": len(plan.get("additional_openings", [])),
        "declared_count": len(declared_ids),
        "built_count": len(built_ids),
        "mapping_count": len(mapping_ids),
        "declared_but_not_built": sorted(declared_ids - built_ids),
        "built_but_not_declared": sorted(built_ids - declared_ids),
        "declared_windows_without_mapping": sorted(declared_window_ids - mapping_ids),
        "unexpected_mapping_ids": sorted(mapping_ids - declared_window_ids),
        "expected_observations_without_mapping": sorted(expected_observation_ids - mapping_ids),
        "mapping_ids_without_input_observation": sorted(mapping_ids - expected_observation_ids),
        "unbuilt_openings": source.get("unbuilt_openings", []),
    }


def check_door_graph(source: dict) -> dict:
    roof_ids = sorted(
        row["id"] for row in source["spaces"]
        if "roof" in str(row.get("role", "")).lower()
        or str(row.get("floor_id", "")).upper().startswith("ROOF")
    )
    usable = sorted(row["id"] for row in source["spaces"] if row["id"] not in roof_ids)
    outside = "__EXTERIOR__"
    graph: dict[str, set[str]] = {row["id"]: set() for row in source["spaces"]}
    graph[outside] = set()
    doors = []
    for opening in source["openings"]:
        if opening.get("kind") != "door":
            continue
        space_ids = list(opening.get("space_ids", []))
        if opening.get("exterior") and len(space_ids) == 1:
            first, second = space_ids[0], outside
        elif len(space_ids) == 2:
            first, second = space_ids
        else:
            continue
        graph.setdefault(first, set()).add(second)
        graph.setdefault(second, set()).add(first)
        doors.append(opening["id"])
    reachable = {outside}
    pending = [outside]
    while pending:
        node = pending.pop()
        for adjacent in graph.get(node, ()):
            if adjacent not in reachable:
                reachable.add(adjacent)
                pending.append(adjacent)
    unreachable = sorted(set(usable) - reachable)
    return {
        "status": "pass" if not unreachable else "fail",
        "door_opening_ids_used": sorted(doors),
        "usable_space_count": len(usable),
        "unreachable_usable_space_ids": unreachable,
        "roof_spaces_excluded_from_door_requirement": roof_ids,
        "interpretation": "Declared partly inferred door graph only; not real-plan evidence.",
    }


def check_continuous_cores(source: dict, baseline: dict) -> dict:
    baseline_core_ids = sorted(
        row["id"] for row in baseline["spaces"]
        if row["id"].endswith("_continuous")
    )
    spaces = {row["id"]: row for row in source["spaces"]}
    rows = []
    main_floors = [
        row for row in source["floors"]
        if row["id"].startswith("F") and row["id"][1:].isdigit()
    ]
    for core_id in baseline_core_ids:
        space = spaces.get(core_id)
        horizontal = [
            row for row in source["boundaries"]
            if row["space_id"] == core_id
            and row["geometry_type"] in {"floor", "ceiling"}
        ]
        z_values = sorted({
            round(float(vertex[2]), 8)
            for boundary in horizontal for vertex in boundary["vertices"]
        })
        references = sorted(
            row["id"] for row in main_floors
            if core_id in row.get("spanning_space_ids", [])
        )
        storey_doors = {
            floor["id"]: sorted(
                opening["id"] for opening in source["openings"]
                if opening.get("kind") == "door"
                and set(opening.get("space_ids", [])) == {
                    f"{floor['id']}_open", core_id
                }
            )
            for floor in main_floors
        }
        ok = (
            space is not None
            and len(horizontal) == 2
            and len(z_values) == 2
            and len(references) == len(main_floors)
            and all(storey_doors.values())
        )
        rows.append({
            "core_space_id": core_id,
            "space_exists": space is not None,
            "horizontal_boundary_ids": [row["id"] for row in horizontal],
            "horizontal_boundary_z_values_m": z_values,
            "only_bottom_and_top_horizontal_boundaries": len(horizontal) == 2,
            "referenced_by_main_storeys": references,
            "storey_connection_doors": storey_doors,
            "status": "pass" if ok else "fail",
        })
    return {
        "status": "pass" if len(rows) == 2 and all(row["status"] == "pass" for row in rows)
        else "fail",
        "expected_core_ids_from_baseline": baseline_core_ids,
        "cores": rows,
    }


def horizontal_boundary(source: dict, space_id: str, kind: str, z: float) -> dict | None:
    matches = []
    for boundary in source["boundaries"]:
        if boundary["space_id"] != space_id or boundary["geometry_type"] != kind:
            continue
        if all(abs(float(vertex[2]) - z) <= TOLERANCE_M for vertex in boundary["vertices"]):
            matches.append(boundary)
    if len(matches) != 1:
        return None
    return matches[0]


def boundary_polygon(boundary: dict) -> Polygon:
    return Polygon([[float(vertex[0]), float(vertex[1])] for vertex in boundary["vertices"]])


def boundary_open_geometry(boundary: dict):
    if boundary.get("enclosure") == "open":
        return boundary_polygon(boundary)
    regions = [
        Polygon([[float(vertex[0]), float(vertex[1])] for vertex in region["vertices"]])
        for region in boundary.get("enclosure_regions", [])
        if region.get("condition") == "open"
    ]
    return unary_union(regions) if regions else Polygon()


def display_physical_geometry(display: dict, boundary_id: str):
    polygons = []
    for part in display.get("display_surface_parts", {}).get(boundary_id, []):
        if part.get("enclosure_condition", "physical") != "physical":
            continue
        polygon = Polygon([[float(v[0]), float(v[1])] for v in part["verts"]])
        for hole in part.get("holes", []):
            polygon = polygon.difference(
                Polygon([[float(v[0]), float(v[1])] for v in hole])
            )
        polygons.append(polygon)
    return unary_union(polygons) if polygons else Polygon()


def is_roof_space(space: dict) -> bool:
    return (
        "roof" in str(space.get("role", "")).lower()
        or str(space.get("floor_id", "")).upper().startswith("ROOF")
    )


def check_roof_interfaces(source: dict, display: dict) -> dict:
    roof = [row for row in source["spaces"] if is_roof_space(row)]
    polygons = {row["id"]: polygon_for_space(row) for row in roof}
    expected: dict[tuple[str, str, float], list] = {}
    pairs = []
    for lower in roof:
        lower_top = float(lower["z_floor"]) + float(lower["height"])
        for upper in roof:
            upper_bottom = float(upper["z_floor"])
            if lower["id"] == upper["id"] or abs(lower_top - upper_bottom) > TOLERANCE_M:
                continue
            overlap = polygons[lower["id"]].intersection(polygons[upper["id"]])
            if overlap.area <= TOLERANCE_M2:
                continue
            expected.setdefault((lower["id"], "ceiling", lower_top), []).append(overlap)
            expected.setdefault((upper["id"], "floor", upper_bottom), []).append(overlap)
            pairs.append({
                "lower_space_id": lower["id"], "upper_space_id": upper["id"],
                "z_m": lower_top, "shared_area_m2": float(overlap.area),
            })
    sides = []
    for (space_id, kind, z), overlaps in expected.items():
        target = unary_union(overlaps)
        boundary = horizontal_boundary(source, space_id, kind, z)
        if boundary is None:
            sides.append({
                "space_id": space_id, "geometry_type": kind, "z_m": z,
                "status": "fail", "error": "expected exactly one horizontal boundary",
            })
            continue
        opened = boundary_open_geometry(boundary)
        physical_display = display_physical_geometry(display, boundary["id"])
        missing_open = target.difference(opened).area
        extra_open = opened.difference(target).area
        displayed_slab = target.intersection(physical_display).area
        sides.append({
            "space_id": space_id, "boundary_id": boundary["id"],
            "geometry_type": kind, "z_m": z,
            "expected_shared_open_area_m2": float(target.area),
            "declared_open_area_m2": float(opened.area),
            "missing_open_area_m2": float(missing_open),
            "open_area_outside_roof_contact_m2": float(extra_open),
            "physical_display_area_inside_open_contact_m2": float(displayed_slab),
            "boundary_enclosure": boundary.get("enclosure"),
            "status": "pass" if (
                missing_open <= TOLERANCE_M2
                and extra_open <= TOLERANCE_M2
                and displayed_slab <= TOLERANCE_M2
            ) else "fail",
        })

    # The F8-to-roof contact at 27.8 m is deliberately a physical, inferred
    # slab.  Keep this distinct from open interfaces between roof volumes.
    main = [row for row in source["spaces"] if not is_roof_space(row)]
    main_roof_rows = []
    for lower in main:
        lower_top = float(lower["z_floor"]) + float(lower["height"])
        for upper in roof:
            if abs(lower_top - float(upper["z_floor"])) > TOLERANCE_M:
                continue
            overlap = polygon_for_space(lower).intersection(polygons[upper["id"]])
            if overlap.area <= TOLERANCE_M2:
                continue
            low_boundary = horizontal_boundary(source, lower["id"], "ceiling", lower_top)
            high_boundary = horizontal_boundary(source, upper["id"], "floor", lower_top)
            low_open = boundary_open_geometry(low_boundary) if low_boundary else Polygon()
            high_open = boundary_open_geometry(high_boundary) if high_boundary else Polygon()
            physical = bool(low_boundary and high_boundary) and (
                overlap.intersection(low_open).area <= TOLERANCE_M2
                and overlap.intersection(high_open).area <= TOLERANCE_M2
                and overlap.difference(display_physical_geometry(
                    display, low_boundary["id"]
                )).area <= TOLERANCE_M2
                and overlap.difference(display_physical_geometry(
                    display, high_boundary["id"]
                )).area <= TOLERANCE_M2
            )
            main_roof_rows.append({
                "main_space_id": lower["id"], "roof_space_id": upper["id"],
                "z_m": lower_top, "shared_area_m2": float(overlap.area),
                "main_boundary_id": low_boundary["id"] if low_boundary else None,
                "roof_boundary_id": high_boundary["id"] if high_boundary else None,
                "remains_physical_in_source_and_display": physical,
                "status": "pass" if physical else "fail",
            })
    status = (
        bool(pairs) and bool(main_roof_rows)
        and all(row["status"] == "pass" for row in sides)
        and all(row["status"] == "pass" for row in main_roof_rows)
    )
    return {
        "status": "pass" if status else "fail",
        "roof_space_ids": sorted(row["id"] for row in roof),
        "roof_to_roof_shared_pairs": pairs,
        "roof_open_interface_sides": sides,
        "main_to_roof_physical_slab_hypothesis_contacts": main_roof_rows,
        "interpretation": (
            "Roof-volume contacts must be open on both source sides and absent from "
            "physical display parts; exposed roof outside those contacts remains physical. "
            "Main-storey-to-roof contacts remain the explicitly inferred physical slab."
        ),
    }


def parse_assembly_args(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if "=" in value:
            key, item = value.split("=", 1)
            result.extend(["--" + key.lstrip("-").replace("_", "-"), item])
        else:
            result.append("--" + value.lstrip("-").replace("_", "-"))
    return result


def check_assembly_replay(
    candidate_dir: Path, script: Path | None, assembly_args: list[str]
) -> dict:
    if script is None:
        return {"status": "skipped", "reason": "no frozen assembly script supplied"}
    script = script.resolve()
    if not script.is_file():
        return {"status": "fail", "error": f"assembly script missing: {script}"}
    with tempfile.TemporaryDirectory(prefix="voimatalo-assembly-replay-") as temp:
        replay_dir = Path(temp) / "candidate"
        command = [sys.executable, str(script), *parse_assembly_args(assembly_args),
                   "--out", str(replay_dir)]
        process = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, timeout=300, check=False
        )
        filenames = ["source_model.json", "proposal.json", "opening_mapping.json"]
        files = {}
        for filename in filenames:
            expected = candidate_dir / filename
            actual = replay_dir / filename
            files[filename] = {
                "expected_exists": expected.is_file(), "replayed_exists": actual.is_file(),
                "exact_bytes": expected.is_file() and actual.is_file()
                and expected.read_bytes() == actual.read_bytes(),
                "expected_sha256": sha256(expected) if expected.is_file() else None,
                "replayed_sha256": sha256(actual) if actual.is_file() else None,
            }
        status = process.returncode == 0 and all(row["exact_bytes"] for row in files.values())
        return {
            "status": "pass" if status else "fail",
            "command": command[:-1] + ["<temporary-output>"],
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "files": files,
            "temporary_directory_removed_after_check": True,
        }


def check_result_links(result_dir: Path) -> dict:
    from bs4 import BeautifulSoup

    rows = []
    for page_name in ["index.html", "observations.html"]:
        page_path = result_dir / page_name
        soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")
        for element in soup.find_all(["a", "img", "iframe"]):
            attribute = "href" if element.name == "a" else "src"
            raw = element.get(attribute)
            if not raw:
                continue
            parsed = urlparse(raw)
            if parsed.scheme or parsed.netloc:
                exists = False
                resolved = raw
            else:
                resolved_path = (page_path.parent / unquote(parsed.path)).resolve()
                exists = resolved_path.exists()
                resolved = str(resolved_path)
            rows.append({
                "page": page_name, "element": element.name, "target": raw,
                "resolved": resolved, "exists": exists,
            })
    return {"status": "pass" if rows and all(row["exists"] for row in rows) else "fail",
            "links": rows}


def browser_qa(result_dir: Path, qa_dir: Path, source: dict, mesh_path: Path) -> dict:
    import trimesh
    from playwright.sync_api import sync_playwright

    qa_dir.mkdir(parents=True, exist_ok=False)
    frame = source["mesh_frame"]
    mesh = trimesh.load(mesh_path, force="mesh", process=False)
    raw = mesh.vertices
    z_up = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]]
    angle = np.radians(frame["yaw_degrees"])
    cosine, sine = np.cos(angle), np.sin(angle)
    expected = z_up @ np.array(
        [[cosine, sine, 0], [-sine, cosine, 0], [0, 0, 1]]
    ) + np.asarray(frame["translation_m"])
    errors, external = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                  "--enable-unsafe-swiftshader"],
        )
        context = browser.new_context(viewport={"width": 1500, "height": 1000}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: external.append(request.url)
            if request.url.startswith(("http:", "https:")) else None,
        )
        page.goto((result_dir / "overlay.html").as_uri())
        page.wait_for_function("window.TRANSFER && document.body.dataset.texture==='ready'")
        modes = {}
        for mode in ["input", "overlay", "bim"]:
            page.locator(f"[data-transfer-mode={mode}]").click()
            page.wait_for_timeout(300)
            row = page.evaluate(
                """() => ({rawVisible:TRANSFER.rawMesh.visible,
                bimVisible:TRANSFER.root.visible,
                sourceHash:GEO.source_model.source_model_sha256,
                firstInputVertices:[...TRANSFER.rawMesh.geometry.attributes.position.array]})"""
            )
            np.testing.assert_allclose(
                np.asarray(row.pop("firstInputVertices")).reshape(-1, 3),
                expected, atol=3e-6, rtol=0,
            )
            if row["sourceHash"] != source["source_model_sha256"]:
                raise AssertionError("viewer source hash differs")
            modes[mode] = row
            page.screenshot(path=str(qa_dir / f"{mode}.png"))
        if not modes["input"]["rawVisible"] or modes["input"]["bimVisible"]:
            raise AssertionError("input-only mode visibility is wrong")
        if not modes["overlay"]["rawVisible"] or not modes["overlay"]["bimVisible"]:
            raise AssertionError("overlay mode visibility is wrong")
        if modes["bim"]["rawVisible"] or not modes["bim"]["bimVisible"]:
            raise AssertionError("BIM-only mode visibility is wrong")
        before = page.evaluate("TRANSFER.camera.position.toArray()")
        page.mouse.move(1050, 550)
        page.mouse.down()
        page.mouse.move(1210, 650, steps=15)
        page.mouse.up()
        page.wait_for_timeout(300)
        after = page.evaluate("TRANSFER.camera.position.toArray()")
        if np.allclose(before, after):
            raise AssertionError("camera did not rotate")
        options = page.locator("#floorSel option").evaluate_all("xs=>xs.map(x=>x.value)")
        selectable = next((value for value in options if value), "")
        if selectable:
            page.locator("#floorSel").select_option(selectable)
        page.locator("#explode").evaluate("el=>el.value=1")
        page.locator("#explode").dispatch_event("input")
        page.screenshot(path=str(qa_dir / "rotated_floor.png"))
        page.goto((result_dir / "observations.html").as_uri())
        page.wait_for_timeout(300)
        image_count = page.locator("img").count()
        all_images_loaded = page.locator("img").evaluate_all(
            "xs=>xs.every(x=>x.complete && x.naturalWidth>0)"
        )
        page.screenshot(path=str(qa_dir / "observations.png"), full_page=True)
        browser.close()
    packaging = read_json(result_dir / "packaging.json")
    expected_images = (
        packaging["raster_overlays"]
        + packaging["raw_roof_section_images"]
        + len(packaging["height_sections"])
    )
    status = (
        not errors and not external and all_images_loaded
        and image_count == expected_images
    )
    return {
        "status": "pass" if status else "fail",
        "source_hash": source["source_model_sha256"],
        "modes": modes,
        "rotation_verified": not np.allclose(before, after),
        "floor_selection_exercised": bool(selectable),
        "exploded_view_exercised": True,
        "frame_vertex_mapping_verified": True,
        "verified_input_vertices": len(expected),
        "maximum_allowed_absolute_error_m": 3e-6,
        "observation_image_count": image_count,
        "expected_observation_image_count": expected_images,
        "all_observation_images_loaded": all_images_loaded,
        "errors": errors,
        "external_requests": external,
        "screenshots": sorted(path.name for path in qa_dir.glob("*.png")),
    }


def old_mesh_metric(candidate_path: Path, baseline_path: Path, mesh: Path, direction: Path):
    spec = importlib.util.spec_from_file_location("voimatalo_old_validator", OLD_VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    mesh_data, direction_data = module.load_fixed_mesh_faces(mesh, direction)
    baseline_summary, baseline_rows = module.mesh_to_candidate_metric(
        baseline_path, mesh_data, direction_data
    )
    candidate_summary, candidate_rows = module.mesh_to_candidate_metric(
        candidate_path, mesh_data, direction_data
    )
    return {
        "status": "pass",
        "interpretation": (
            "Reused 09-15 one-way diagnostic on the same fixed original faces; "
            "not ground truth and not a completeness metric."
        ),
        "fixed_face_ids": mesh_data["ids"].tolist(),
        "baseline": {"summary": baseline_summary, "faces": baseline_rows},
        "candidate": {"summary": candidate_summary, "faces": candidate_rows},
    }


def markdown_report(report: dict) -> str:
    lines = [
        f"# Voimatalo {Path(report['candidate']).name} validation", "",
        f"Overall required checks: **{report['overall_required_checks']}**", "",
        "| Check | Status |", "|---|---|",
    ]
    labels = {
        "source_export_replay": "Exact source proposal replay",
        "frozen_assembly_replay": "Frozen plan/observation assembly replay",
        "same_height_non_overlap": "No positive-volume source-space overlap",
        "old_window_retention_and_new_openings": "Old 244 windows retained; additions listed",
        "proposal_opening_account": "Declared openings all mapped and built",
        "declared_door_graph": "Non-roof spaces reach exterior in declared door graph",
        "continuous_cores": "Two unchanged continuous cores, no intermediate slabs",
        "roof_horizontal_interfaces": "Roof contacts open; F8-to-roof slab retained",
        "result_links": "Packaged links resolve",
        "offline_browser": "Offline original/BIM/overlay, rotation and images",
        "fixed_mesh_diagnostic": "09-15 fixed-face diagnostic replayed",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {report['checks'][key]['status']} |")
    opening = report["checks"]["old_window_retention_and_new_openings"]
    lines += [
        "", "## Opening comparison", "",
        f"- Baseline windows: {opening['baseline_window_count']}; candidate windows: "
        f"{opening['candidate_window_count']}; added: {len(opening['added_window_ids'])}.",
        f"- Missing old windows: {opening['missing_window_ids'] or 'none'}.",
        f"- Changed old windows: {opening['changed_window_ids'] or 'none'}.",
        f"- Door changes are reported separately: missing {opening['missing_door_ids'] or 'none'}, "
        f"changed {opening['changed_door_ids'] or 'none'}, added {opening['added_door_ids'] or 'none'}.",
        "", "## Limits", "",
        "- Door reachability follows the declared, partly inferred scheme and does not verify the real interior.",
        "- The fixed-face mesh diagnostic is one-way and does not penalise candidate-only perimeter or establish completeness.",
        "- Browser transport and exact replay prove that the saved artifact was shown unchanged; visual fidelity still requires human review of the saved screenshots.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=HERE / "candidate_03")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--result", type=Path, default=HERE / "result_03")
    parser.add_argument("--report-dir", type=Path, default=HERE / "validation")
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument("--direction", type=Path, default=DEFAULT_DIRECTION)
    parser.add_argument("--plan", type=Path, default=HERE / "case_plan.json")
    parser.add_argument(
        "--apertures", type=Path, default=HERE / "assembly_observations.json"
    )
    parser.add_argument(
        "--assembly-script", type=Path,
        help="frozen assembler; omit only for a pre-assembly partial check",
    )
    parser.add_argument(
        "--assembly-arg", action="append", default=[], metavar="KEY=VALUE",
        help="argument passed to the frozen assembler; repeat as needed",
    )
    parser.add_argument("--skip-browser", action="store_true")
    args = parser.parse_args()

    candidate_dir, source_path = candidate_paths(args.candidate)
    baseline_dir, baseline_path = candidate_paths(args.baseline)
    result_dir = args.result.resolve()
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = report_dir / f"{candidate_dir.name}_browser_qa"
    source = read_json(source_path)
    baseline = read_json(baseline_path)
    display = read_json(candidate_dir / "display_geometry.json")

    assembly_script = args.assembly_script
    assembly_args = list(args.assembly_arg)
    auto_script = HERE / "assemble_model.py"
    if assembly_script is None and auto_script.is_file():
        assembly_script = auto_script
    if assembly_script is not None and not assembly_args:
        assembly_args = [
            f"plan={args.plan.resolve()}",
            f"apertures={args.apertures.resolve()}",
        ]

    checks = {
        "source_export_replay": check_source_export_replay(candidate_dir, source_path, source),
        "frozen_assembly_replay": check_assembly_replay(
            candidate_dir, assembly_script, assembly_args
        ),
        "same_height_non_overlap": check_no_overlap(source),
        "old_window_retention_and_new_openings": check_opening_retention(source, baseline),
        "proposal_opening_account": check_proposal_openings(
            candidate_dir, source, args.plan.resolve(), args.apertures.resolve()
        ),
        "declared_door_graph": check_door_graph(source),
        "continuous_cores": check_continuous_cores(source, baseline),
        "roof_horizontal_interfaces": check_roof_interfaces(source, display),
        "result_links": check_result_links(result_dir),
    }
    if args.skip_browser:
        checks["offline_browser"] = {"status": "skipped", "reason": "--skip-browser"}
    else:
        checks["offline_browser"] = browser_qa(
            result_dir, qa_dir, source, args.mesh.resolve()
        )
    metric = old_mesh_metric(
        source_path, baseline_path, args.mesh.resolve(), args.direction.resolve()
    )
    detail_path = report_dir / f"{candidate_dir.name}_mesh_faces.json"
    detail_path.write_text(
        json.dumps({
            "fixed_face_ids": metric.pop("fixed_face_ids"),
            "baseline": metric["baseline"].pop("faces"),
            "candidate": metric["candidate"].pop("faces"),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metric["face_detail_artifact"] = {
        "path": str(detail_path), "sha256": sha256(detail_path)
    }
    checks["fixed_mesh_diagnostic"] = metric

    required = [
        key for key in checks
        if key not in {"fixed_mesh_diagnostic"}
    ]
    overall = "pass" if all(checks[key]["status"] == "pass" for key in required) else "fail"
    report = {
        "schema": "voimatalo_completion_validation_v1",
        "candidate": str(candidate_dir),
        "baseline_for_retention_only": str(baseline_dir),
        "result": str(result_dir),
        "overall_required_checks": overall,
        "checks": checks,
        "claims": {
            "old_candidate_used_only_after_generation_for_comparison": True,
            "interior_scheme_is_inferred_not_measured": True,
            "browser_transport_is_not_visual_fidelity": True,
            "fidelity_pass_claimed": False,
        },
    }
    report_path = report_dir / f"{candidate_dir.name}_validation.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / f"{candidate_dir.name}_validation.md").write_text(
        markdown_report(report), encoding="utf-8"
    )
    print(json.dumps({
        "status": overall, "report": str(report_path),
        "browser_qa": str(qa_dir) if not args.skip_browser else None,
    }, ensure_ascii=False))
    if overall != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
