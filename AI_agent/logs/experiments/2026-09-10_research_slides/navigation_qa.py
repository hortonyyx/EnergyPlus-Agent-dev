#!/usr/bin/env python3
"""Offline interaction QA for the 2026-09-11 research-report slide deck."""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[4]
DECK = ROOT / "showcase/2026-09-11-research-report"
ENTRY = DECK / "index.html"
OUT = Path(__file__).resolve().parent / "navigation_qa"


def image_state(page: Page) -> list[dict[str, object]]:
    return page.locator("img").evaluate_all(
        """images => images.map(image => ({src: image.getAttribute('src'), complete: image.complete,
          naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight}))"""
    )


def assert_slide(page: Page, number: int) -> None:
    expect(page.locator(f"#slide-{number}")).to_be_visible()
    assert page.url.endswith(f"#{number}"), page.url
    assert page.locator("#page-current").inner_text() == f"{number:02d}"


def iframe_ready(page: Page, expected_tail: str):
    expect(page.locator("#demo-dialog")).to_be_visible()
    expect(page.locator("#demo-frame")).to_have_attribute("src", expected_tail)
    frame = page.frame_locator("#demo-frame")
    expect(frame.locator("canvas").last).to_be_visible(timeout=12_000)
    if not expected_tail.endswith("input_viewer.html"):
        expect(frame.locator("#floorSel")).to_be_visible(timeout=12_000)
    return frame


def rotate_and_layer(frame) -> None:
    canvas = frame.locator("canvas").last
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    assert box is not None
    page = frame.locator("canvas").last.page
    x, y = box["x"] + box["width"] * 0.52, box["y"] + box["height"] * 0.50
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + box["width"] * 0.08, y - box["height"] * 0.04, steps=10)
    page.mouse.up()
    expect(frame.locator("#floorSel")).to_be_visible()
    option_count = frame.locator("#floorSel option").count()
    assert option_count > 1, option_count
    frame.locator("#floorSel").select_option("1")
    expect(frame.locator("#floorSel")).to_have_value("1")
    frame.locator("#explode").evaluate(
        "node => { node.value = '0.30'; node.dispatchEvent(new Event('input', {bubbles: true})); }"
    )
    expect(frame.locator("#explode")).to_have_value("0.3")
    frame.locator("#reset").click()


def exercise_file(page: Page, report: dict[str, object], viewport: dict[str, int]) -> None:
    page.set_viewport_size(viewport)
    page.goto(f"{ENTRY.as_uri()}#1", wait_until="load")
    page.wait_for_timeout(450)
    assert_slide(page, 1)
    images = image_state(page)
    assert images and all(image["complete"] and image["naturalWidth"] for image in images), images

    # Every hash is independently deep-linkable.
    for number in range(1, 8):
        page.goto(f"{ENTRY.as_uri()}#{number}", wait_until="load")
        assert_slide(page, number)
    page.goto(f"{ENTRY.as_uri()}#1", wait_until="load")
    page.keyboard.press("ArrowRight")
    assert_slide(page, 2)
    page.keyboard.press("5")
    assert_slide(page, 5)
    page.keyboard.press("Home")
    assert_slide(page, 1)
    page.keyboard.press("End")
    assert_slide(page, 7)
    page.keyboard.press("ArrowLeft")
    assert_slide(page, 6)

    page.keyboard.press("o")
    expect(page.locator("#overview")).to_be_visible()
    current_item = page.locator('#overview-items button[aria-current="page"]')
    expect(current_item).to_be_focused()
    page.locator("#overview-items button").nth(2).click()
    expect(page.locator("#overview")).to_be_hidden()
    assert_slide(page, 3)
    expect(page.locator("#page-toggle")).to_be_focused()

    page.keyboard.press("5")
    page.locator('[data-demo="sm25"]').click()
    sm25 = iframe_ready(page, "demos/sm25/sm25_showcase.html")
    rotate_and_layer(sm25)
    page.locator("#demo-close").click()
    expect(page.locator("#demo-dialog")).to_be_hidden()
    assert_slide(page, 5)
    expect(page.locator('[data-demo="sm25"]')).to_be_focused()

    page.keyboard.press("6")
    page.locator('[data-demo="voima-input"]').click()
    source = iframe_ready(page, "demos/textured-mass/input_viewer.html")
    # The textured source viewer is rotatable, but intentionally has no BIM floor controls.
    canvas = source.locator("canvas").last
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] * 0.50, box["y"] + box["height"] * 0.50)
    page.mouse.down(); page.mouse.move(box["x"] + box["width"] * 0.07, box["y"] - box["height"] * 0.03, steps=8); page.mouse.up()
    page.locator("#demo-close").click()
    expect(page.locator("#demo-dialog")).to_be_hidden()
    assert_slide(page, 6)
    expect(page.locator('[data-demo="voima-input"]')).to_be_focused()

    # Open the BIM button directly, then test all three versions from its variant bar.
    page.locator('[data-demo="voima"]').click()
    inferred = iframe_ready(page, "demos/textured-mass/index.html")
    rotate_and_layer(inferred)
    expect(page.locator("#demo-variants button")).to_have_count(3)
    expect(page.locator("#demo-variants button").nth(2)).to_have_attribute("aria-pressed", "true")
    page.locator("#demo-variants button").nth(0).click()
    source = iframe_ready(page, "demos/textured-mass/input_viewer.html")
    page.locator("#demo-variants button").nth(1).click()
    envelope = iframe_ready(page, "demos/textured-mass/envelope.html")
    rotate_and_layer(envelope)
    page.locator("#demo-variants button").nth(2).click()
    inferred = iframe_ready(page, "demos/textured-mass/index.html")
    rotate_and_layer(inferred)
    page.locator("#demo-close").click()
    expect(page.locator("#demo-dialog")).to_be_hidden()
    assert_slide(page, 6)
    expect(page.locator('[data-demo="voima"]')).to_be_focused()
    report["file_viewports"].append({"viewport": viewport, "images": images})


def exercise_http_esc(browser, report: dict[str, object], port: int) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"http://127.0.0.1:{port}/index.html#5", wait_until="load")
    page.locator('[data-demo="sm25"]').click()
    frame = iframe_ready(page, "demos/sm25/sm25_showcase.html")
    frame.locator("canvas").last.focus()
    frame.locator("canvas").last.press("Escape")
    expect(page.locator("#demo-dialog")).to_be_hidden(timeout=3_000)
    assert_slide(page, 5)
    report["http_iframe_escape"] = "pass"
    page.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"file_viewports": [], "console_errors": [], "failed_requests": [], "external_requests": []}
    handler = partial(SimpleHTTPRequestHandler, directory=str(DECK))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
            )
            page = browser.new_page()
            requests: list[str] = []
            page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
            page.on("requestfailed", lambda request: report["failed_requests"].append({"url": request.url, "failure": request.failure}))
            page.on("request", lambda request: requests.append(request.url))
            for viewport in ({"width": 1440, "height": 900}, {"width": 1920, "height": 1080}):
                exercise_file(page, report, viewport)
            page.close()
            exercise_http_esc(browser, report, server.server_address[1])
            browser.close()
            report["external_requests"] = [url for url in requests if url.startswith(("http://", "https://"))]
    finally:
        server.shutdown()
        server.server_close()
    assert not report["console_errors"], report["console_errors"]
    assert not report["failed_requests"], report["failed_requests"]
    assert not report["external_requests"], report["external_requests"]
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
