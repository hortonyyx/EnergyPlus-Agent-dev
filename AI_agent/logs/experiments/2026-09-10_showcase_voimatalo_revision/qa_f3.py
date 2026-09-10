#!/usr/bin/env python3
"""Offline browser check for the revision_02 standard-viewer packaging."""

from __future__ import annotations

import argparse,hashlib,json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
SHOWCASE = ROOT / "showcase/2026-09-11-research-report/demos/textured-mass"
OUT = Path(__file__).resolve().parent / "browser_qa"


def floor_summary(page) -> dict:
    return page.evaluate(
        """() => {
          const d=window.GEO;
          const bases=[...new Set(d.surfaces.filter(s=>s.type==='Floor')
            .map(s=>Math.min(...s.verts.map(v=>v[2])).toFixed(6)))].map(Number).sort((a,b)=>a-b);
          const f=Number(document.querySelector('#floorSel').value), lo=bases[f], hi=bases[f+1];
          const inBand=(item)=>{const z=item.verts.map(v=>v[2]), a=Math.min(...z), b=Math.max(...z); return b>lo && a<hi;};
          const traffic=d.windows.filter(w=>w.name.includes('TRAFFIC'));
          return {bases, selectedFloor:f, band:[lo,hi], trafficWindowsTotal:traffic.length,
            trafficWindowsInBand:traffic.filter(inBand).map(w=>w.name),
            currentFloorFaces:d.surfaces.filter(s=>s.type==='Floor' && Math.abs(Math.min(...s.verts.map(v=>v[2]))-lo)<1e-6).map(s=>s.name),
            trafficSurfaceZ:[...new Set(d.surfaces.filter(s=>s.zone==='TRAFFIC_merged').flatMap(s=>s.verts.map(v=>v[2])))].sort((a,b)=>a-b)};
        }"""
    )


def inspect(page, name: str) -> dict:
    page.goto((SHOWCASE / name).as_uri(), wait_until="load")
    page.wait_for_timeout(1200)
    assert page.locator("canvas").count() == 1
    assert page.locator("#panel").count() == page.locator("#rinfo").count() == 1
    assert page.locator("#showcasebar, #variant-links, #scene-caption").count() == 0
    assert page.locator("#voimatalo-links a").count() == 3
    page.locator("#floorSel").select_option("2")  # F3: 8.8–12.0 m in revision_02
    page.wait_for_timeout(350)
    report = floor_summary(page)
    report["native_panel"] = page.locator("#panel").is_visible()
    report["local_axes"] = page.locator("body").evaluate("e => !e.innerText.includes('N = +Y')")
    page.screenshot(path=str(OUT / f"{Path(name).stem}_f3.png"))
    return report


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    console_errors: list[str] = []
    page_errors,failed,external=[],[],[]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1,offline=True)
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on('pageerror',lambda e:page_errors.append(str(e)))
        page.on('requestfailed',lambda r:failed.append(r.url))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
        inferred = inspect(page, "index.html")
        exterior = inspect(page, "envelope.html")
        browser.close()
    assert inferred["trafficWindowsInBand"] == ["window/TRAFFIC_narrow_2"], inferred
    assert inferred["trafficSurfaceZ"] == [0.0, 27.6], inferred
    assert inferred["currentFloorFaces"], inferred
    assert not console_errors and not page_errors and not failed and not external
    report = {"offline": True, "f3": {"inferred": inferred, "exterior": exterior}, "console_errors": console_errors,
        'page_errors':page_errors,'failed_requests':failed,'external_requests':external,
        'html_sha256':{name:hashlib.sha256((SHOWCASE/name).read_bytes()).hexdigest() for name in ['index.html','envelope.html']}}
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();OUT=args.out
    main()
