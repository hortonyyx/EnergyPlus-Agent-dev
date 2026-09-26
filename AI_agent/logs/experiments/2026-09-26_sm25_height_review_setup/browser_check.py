"""Offline viewer check using the existing /tmp/ep-bim-browser-qa environment."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(run):
    delivery = json.loads((run / "delivery.json").read_text())
    output = run / "browser_qa"
    output.mkdir(exist_ok=True)
    errors, external = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--use-angle=swiftshader"])
        context = browser.new_context(viewport={"width": 1400, "height": 960}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external.append(request.url)
                if request.url.startswith(("http:", "https:")) else None)
        page.goto((run / delivery["viewer"]).as_uri())
        page.wait_for_selector("canvas")
        page.wait_for_function("document.querySelector('#floorSel').options.length > 1")
        source_hash = page.evaluate("window.GEO.source_model.source_model_sha256")
        assert source_hash == delivery["source_model_sha256"]
        options = page.locator("#floorSel option").evaluate_all(
            "els => els.filter(e=>e.value !== '-1').map(e=>({value:e.value,text:e.textContent}))")
        floor_hashes = []
        for row in options:
            page.select_option("#floorSel", row["value"])
            page.wait_for_timeout(250)
            data = page.locator("canvas").screenshot(path=str(output / f'floor_{row["value"]}.png'))
            floor_hashes.append(hashlib.sha256(data).hexdigest())
        assert len(set(floor_hashes)) == len(options)
        page.select_option("#floorSel", "-1")
        before = page.locator("canvas").screenshot()
        page.mouse.move(810, 450)
        page.mouse.down()
        page.mouse.move(1000, 530, steps=12)
        page.mouse.up()
        page.wait_for_timeout(500)
        after = page.locator("canvas").screenshot(path=str(output / "rotated.png"))
        assert before != after
        page.goto((run / "delivery.html").as_uri())
        assert page.get_by_role("heading", name="本次原图直接查看记录").count() == 1
        assert page.get_by_role("heading", name="开口高度观察范围").count() == 1
        page.screenshot(path=str(output / "delivery.png"))
        assert not errors and not external
        browser.close()
    result = dict(status="pass", candidate=delivery["candidate"], source_sha256=source_hash,
        floor_options=options, different_floor_images=True, rotation_changed_canvas=True,
        offline=True, external_requests=external, page_errors=errors,
        scope="Display/transport only, not drawing fidelity or human approval.")
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    check(parser.parse_args().run.resolve())
