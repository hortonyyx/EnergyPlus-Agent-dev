#!/usr/bin/env python3
"""Final offline browser sweep for the two revision_02 standard-viewer pages."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[4]
SHOWCASE = ROOT / "showcase/2026-09-11-research-report/demos/textured-mass"
OUT = Path(__file__).resolve().parent / "browser_qa_final"


def set_range(page: Page, value: str) -> None:
    page.locator("#explode").evaluate(
        """(node, value) => { node.value=value; node.dispatchEvent(new Event('input', {bubbles:true})); }""", value
    )
    page.wait_for_timeout(300)


def f3_summary(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const d=window.GEO;
          const bases=[...new Set(d.surfaces.filter(s=>s.type==='Floor')
            .map(s=>Math.min(...s.verts.map(v=>v[2])).toFixed(6)))].map(Number).sort((a,b)=>a-b);
          const f=Number(document.querySelector('#floorSel').value), lo=bases[f], hi=bases[f+1];
          const inBand=(item)=>{const z=item.verts.map(v=>v[2]), a=Math.min(...z), b=Math.max(...z); return b>lo && a<hi;};
          const traffic=d.windows.filter(w=>w.name.includes('TRAFFIC'));
          return {selectedFloor:f, band:[lo,hi], trafficWindowsTotal:traffic.length,
            trafficWindowsInBand:traffic.filter(inBand).map(w=>w.name),
            currentFloorFaces:d.surfaces.filter(s=>s.type==='Floor' && Math.abs(Math.min(...s.verts.map(v=>v[2]))-lo)<1e-6).map(s=>s.name),
            trafficSurfaceZ:[...new Set(d.surfaces.filter(s=>s.zone==='TRAFFIC_merged').flatMap(s=>s.verts.map(v=>v[2])))].sort((a,b)=>a-b)};
        }"""
    )


def source_counts(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const d=window.GEO, s=d.source_model;
          const doors=s.openings.filter(o=>o.kind==='door').length;
          return {source_spaces:s.spaces.length, source_windows:s.openings.filter(o=>o.kind==='window').length,
            source_doors:doors, source_openings:s.openings.length, display_windows:d.windows.length,
            display_opening_pieces:d.openings.length, source_validation:s.validation.status,
            main_floor_count:s.floors.filter(f=>/^F\\d+$/.test(f.id)).length};
        }"""
    )


def screenshot(page: Page, name: str) -> None:
    page.screenshot(path=str(OUT / name))


def inspect_inferred(page: Page) -> dict:
    page.goto((SHOWCASE / "index.html").as_uri(), wait_until="load")
    page.wait_for_timeout(1100)
    assert page.locator("canvas").count() == 1
    assert page.locator("#panel").count() == page.locator("#rinfo").count() == 1
    assert page.locator("#showcasebar, #variant-links, #scene-caption").count() == 0
    assert page.locator("#voimatalo-links a").count() == 3
    assert "标高层级" in page.locator("#hud").inner_text()
    assert "主楼层数" in page.locator("#hud").inner_text()
    screenshot(page, "index_whole.png")

    box = page.locator("canvas").bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] * 0.56, box["y"] + box["height"] * 0.52)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.68, box["y"] + box["height"] * 0.43, steps=12)
    page.mouse.up()
    page.wait_for_timeout(350)
    screenshot(page, "index_rotated.png")

    page.locator("#explodeMode").select_option("floor")
    set_range(page, "0.30")
    screenshot(page, "index_explode_floor.png")
    page.locator("#explodeMode").select_option("zone")
    set_range(page, "0.30")
    screenshot(page, "index_explode_zone.png")
    set_range(page, "0")
    page.locator("#reset").click()
    page.wait_for_timeout(300)
    screenshot(page, "index_restored.png")

    page.locator("#floorSel").select_option("2")
    page.wait_for_timeout(350)
    f3 = f3_summary(page)
    screenshot(page, "index_f3.png")
    page.locator("#floorSel").select_option("-1")
    page.locator("#reset").click()
    return {"counts": source_counts(page), "f3": f3}


def inspect_exterior(page: Page) -> dict:
    page.goto((SHOWCASE / "envelope.html").as_uri(), wait_until="load")
    page.wait_for_timeout(1100)
    assert page.locator("canvas").count() == 1
    assert "主楼层数" in page.locator("#hud").inner_text()
    screenshot(page, "envelope_whole.png")
    return {"counts": source_counts(page)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    console: list[dict] = []
    failed: list[dict] = []
    requests: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.on("console", lambda msg: console.append({"type": msg.type, "text": msg.text}))
        page.on("request", lambda request: requests.append(request.url))
        page.on("requestfailed", lambda request: failed.append({"url": request.url, "failure": request.failure}))
        inferred = inspect_inferred(page)
        exterior = inspect_exterior(page)
        browser.close()
    errors = [item for item in console if item["type"] == "error"]
    external = [url for url in requests if url.startswith(("http://", "https://"))]
    assert inferred["counts"] == {"source_spaces": 165, "source_windows": 322, "source_doors": 173,
                                  "source_openings": 495, "display_windows": 322,
                                  "display_opening_pieces": 344, "source_validation": "pass", "main_floor_count": 8}, inferred
    assert exterior["counts"] == {"source_spaces": 13, "source_windows": 322, "source_doors": 10,
                                  "source_openings": 332, "display_windows": 322,
                                  "display_opening_pieces": 18, "source_validation": "pass", "main_floor_count": 8}, exterior
    assert inferred["f3"]["trafficWindowsInBand"] == ["window/TRAFFIC_narrow_2"], inferred
    assert inferred["f3"]["currentFloorFaces"], inferred
    assert inferred["f3"]["trafficSurfaceZ"] == [0.0, 27.6], inferred
    assert not errors and not failed and not external, {"errors": errors, "failed": failed, "external": external}
    report = {"offline": True, "inferred": inferred, "exterior": exterior, "console": console,
              "failed_requests": failed, "external_requests": external, "requests": requests}
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
