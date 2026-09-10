#!/usr/bin/env python3
"""Capture clean, offline 16:9 stills from the existing showcase viewers.

This script only changes the live browser DOM. It never writes to the viewers.
"""

from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfile
import struct

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "showcase/2026-09-11-research-report/assets"
LOG = Path(__file__).resolve().parent
PAGES = {
    "sm25-model": ROOT / "showcase/2026-09-11-research-report/demos/sm25/sm25_showcase.html",
    "voimatalo-model": ROOT / "showcase/2026-09-11-research-report/demos/textured-mass/index.html",
    "voimatalo-input": ROOT / "showcase/2026-09-11-research-report/demos/textured-mass/input_viewer.html",
}
FINAL = {
    "sm25-model": OUT / "sm25-model.png",
    "voimatalo-model": OUT / "voimatalo-model.png",
    "voimatalo-input": OUT / "voimatalo-input.png",
}


def hide_ui(page: Page) -> None:
    page.evaluate(
        """() => {
          for (const node of document.body.querySelectorAll('*')) {
            if (node.tagName !== 'CANVAS' && !node.querySelector('canvas')) {
              node.style.setProperty('display', 'none', 'important');
            }
          }
          document.documentElement.style.setProperty('background', '#f4f6f8', 'important');
          document.body.style.setProperty('margin', '0', 'important');
          document.body.style.setProperty('background', '#f4f6f8', 'important');
          for (const canvas of document.querySelectorAll('canvas')) {
            canvas.style.setProperty('display', 'block', 'important');
            canvas.style.setProperty('position', 'fixed', 'important');
            canvas.style.setProperty('inset', '0', 'important');
            canvas.style.setProperty('width', '100vw', 'important');
            canvas.style.setProperty('height', '100vh', 'important');
          }
        }"""
    )


def nudge_view(page: Page, dx: float, dy: float) -> None:
    canvas = page.locator("canvas").last
    box = canvas.bounding_box()
    assert box is not None
    x = box["x"] + box["width"] * 0.50
    y = box["y"] + box["height"] * 0.50
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + box["width"] * dx, y + box["height"] * dy, steps=14)
    page.mouse.up()
    page.wait_for_timeout(450)


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", header[16:24])


def capture(page: Page, name: str, dx: float, dy: float, zoom: float) -> dict:
    page.goto(PAGES[name].as_uri(), wait_until="load")
    page.wait_for_timeout(2400)
    assert page.locator("canvas").count() >= 1, name
    hide_ui(page)
    page.wait_for_timeout(250)
    if dx or dy:
        nudge_view(page, dx, dy)
    if zoom:
        canvas = page.locator("canvas").last
        box = canvas.bounding_box()
        assert box is not None
        page.mouse.move(box["x"] + box["width"] * 0.50, box["y"] + box["height"] * 0.50)
        # OrbitControls consumes one wheel event as one zoom step; its delta magnitude
        # is deliberately ignored, so send a short sequence rather than one giant event.
        for _ in range(zoom):
            page.mouse.wheel(0, -100)
        page.wait_for_timeout(450)
    path = LOG / f"candidate_{name}.png"
    page.screenshot(path=str(path))
    assert png_size(path) == (1600, 900), path
    copyfile(path, FINAL[name])
    return {
        "page": str(PAGES[name]),
        "candidate": str(path),
        "final": str(FINAL[name]),
        "size": list(png_size(path)),
        "canvas_count": page.locator("canvas").count(),
    }


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"offline": True, "candidates": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        requests: list[str] = []
        errors: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        for name, (dx, dy, zoom) in {
            "sm25-model": (-0.075, 0.02, 10),
            "voimatalo-model": (-0.08, 0.02, 11),
            "voimatalo-input": (-0.08, 0.02, 13),
        }.items():
            report["candidates"][name] = capture(page, name, dx, dy, zoom)
        browser.close()
    external = [url for url in requests if url.startswith(("http://", "https://"))]
    assert not external, external
    assert not errors, errors
    report["external_requests"] = external
    report["console_errors"] = errors
    (LOG / "capture_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
