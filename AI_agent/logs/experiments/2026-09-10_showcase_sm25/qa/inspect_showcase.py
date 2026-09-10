"""Offline browser QA for the sm25 research-report showcase."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[5]
VIEWER = ROOT / "showcase/2026-09-11-research-report/demos/sm25/sm25_showcase.html"
OUT = Path(__file__).resolve().parent
MANUAL = "showcase_manual:2f-door-L029g3-L030g2"


def main() -> None:
    errors: list[str] = []
    failed: list[dict] = []
    external: list[str] = []
    report = {
        "scope": "offline rendering, orbit, floor filtering, exploded view, and presentation-door display only",
        "viewer": str(VIEWER.relative_to(ROOT)),
        "sha256": hashlib.sha256(VIEWER.read_bytes()).hexdigest(),
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=[
            "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
        ])
        context = browser.new_context(viewport={"width": 1600, "height": 1050}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("requestfailed", lambda request: failed.append({"url": request.url, "failure": request.failure}))
        page.on("request", lambda request: external.append(request.url) if request.url.startswith(("https:", "http:")) else None)
        page.goto(VIEWER.as_uri(), wait_until="load")
        page.wait_for_function("document.querySelector('canvas') && window.THREE && window.GEO")
        page.wait_for_timeout(900)
        report["geometry"] = page.evaluate(f"""() => {{
          const geo = window.GEO;
          const source = geo.source_model;
          const manual = source.openings.find(o => o.id === '{MANUAL}');
          const hosts = source.opening_hosts['{MANUAL}'];
          const display = geo.openings.filter(o => o.source_opening_id === '{MANUAL}');
          const proof = source.showcase_metadata.manual_geometry_proof;
          return {{
            zones: geo.zones.length, windows: geo.windows.length, source_openings: source.openings.length,
            source_doors: source.openings.filter(o => o.kind === 'door').length,
            validation: source.validation.status,
            manual_source_refs: manual.source_refs, manual_hosts: hosts,
            manual_display_faces: display.length,
            manual_partners_reciprocal: display.every(o => display.some(p => p.name === o.partner && p.partner === o.name)),
            manual_geometry_proof: {{
              door_interval_m: proof.door_interval_m.map(v => Number(v.toFixed(4))),
              door_area_m2: Number(proof.door_area_m2.toFixed(6)),
              cut_areas_m2: Object.fromEntries(Object.entries(proof.cut_areas_m2).map(([k, v]) => [k, Number(v.toFixed(6))])),
            }},
            cut_host_parts: Object.fromEntries(hosts.map(h => [h, (geo.visible_wall_parts[h] || []).length])),
          }};
        }}""")
        assert report["geometry"] == {
            "zones": 29, "windows": 31, "source_openings": 61, "source_doors": 30,
            "validation": "severe",
            "manual_source_refs": ["manual_showcase:2f_view:L029g3", "manual_showcase:2f_view:L030g2"],
            "manual_hosts": ["space/2f-c000/wall/8", "space/2f-c006/wall/0"],
            "manual_display_faces": 2,
            "manual_partners_reciprocal": True,
            "manual_geometry_proof": {
                "door_interval_m": [10.1219, 10.9286],
                "door_area_m2": 1.69407,
                "cut_areas_m2": {
                    "space/2f-c000/wall/8": 1.69407,
                    "space/2f-c006/wall/0": 1.69407,
                },
            },
            "cut_host_parts": {
                "space/2f-c000/wall/8": 1,
                "space/2f-c006/wall/0": 2,
            },
        }
        page.screenshot(path=str(OUT / "initial.png"))
        canvas = page.locator("canvas")
        before = canvas.screenshot()
        page.mouse.move(760, 510)
        page.mouse.down()
        page.mouse.move(1000, 550, steps=12)
        page.mouse.up()
        page.wait_for_timeout(700)
        after = canvas.screenshot()
        report["orbit_changes_canvas"] = before != after
        assert report["orbit_changes_canvas"]
        page.screenshot(path=str(OUT / "rotated.png"))

        page.locator("#floorSel").select_option("1")
        page.wait_for_timeout(400)
        report["floor_2_filter"] = page.evaluate("() => document.getElementById('floorSel').value")
        assert report["floor_2_filter"] == "1"
        page.screenshot(path=str(OUT / "floor_2.png"))

        page.locator("#floorSel").select_option("-1")
        page.locator("#explode").evaluate("node => { node.value = '0.46'; node.dispatchEvent(new Event('input', {bubbles:true})); }")
        page.wait_for_timeout(700)
        report["explode_value"] = page.locator("#explode").input_value()
        assert report["explode_value"] == "0.46"
        page.screenshot(path=str(OUT / "exploded.png"))
        page.locator("#explodeMode").select_option("zone")
        page.wait_for_timeout(700)
        report["zone_explode_mode"] = page.locator("#explodeMode").input_value()
        assert report["zone_explode_mode"] == "zone"
        page.screenshot(path=str(OUT / "zones_exploded.png"))
        report.update(page_errors=errors, failed_requests=failed, external_requests=external)
        browser.close()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert not errors and not failed and not external, report
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
