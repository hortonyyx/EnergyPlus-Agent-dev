"""Open the saved viewers offline in isolated Playwright Chromium.

This checks rendering and interaction, not source BIM or texture fidelity.
Run with the environment and browser path described in README.md.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    paths = {
        "voimatalo": "case_tests/textured_mass/single_buildings/voimatalo/viewer.html",
        "sm24_partial": "AI_agent/logs/experiments/2026-09-10_partial_inference_sm24_run02/seed/viewer.html",
        "sm24_delivery": "AI_agent/logs/experiments/2026-09-10_partial_inference_sm24_run02/delivery.html",
    }
    report = {"offline": True, "playwright_version": importlib.metadata.version("playwright"),
              "scope": "browser rendering and orbit interaction only; not geometric or image fidelity", "pages": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=[
            "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        report["chromium_version"] = browser.version
        context = browser.new_context(viewport={"width": 1400, "height": 1000}, offline=True)
        for name, relative in paths.items():
            path = ROOT / relative
            page = context.new_page()
            errors, failed, external = [], [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append({"url": request.url[:200], "failure": request.failure}))
            page.on("request", lambda request: external.append(request.url[:200]) if request.url.startswith(("https:", "http:")) else None)
            page.goto(path.as_uri(), wait_until="load")
            item = {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            if name != "sm24_delivery":
                page.wait_for_function('document.querySelector("canvas") && window.THREE')
                if name == "voimatalo":
                    page.wait_for_function('document.getElementById("state").textContent.includes("已加载完整")')
                    item["texture_state"] = page.locator("#state").inner_text()
                    item["geometry"] = page.evaluate('({vertices:geometry.attributes.position.count, triangles:geometry.index.count/3, texture:[texture.image.width,texture.image.height]})')
                page.wait_for_timeout(1000)
                page.screenshot(path=str(args.out / (name + "_initial.png")))
                # The saved BIM page opens long assumption panels by default.
                # Collapse them using their normal controls before rotating.
                while page.locator("details[open] > summary").count():
                    page.locator("details[open] > summary").first.click()
                canvas = page.locator("canvas").first
                before = canvas.screenshot()
                page.screenshot(path=str(args.out / (name + ".png")))
                item["drag_hits_canvas"] = page.evaluate(
                    '[document.elementFromPoint(700,450), document.elementFromPoint(910,470)].every(node => node.tagName === "CANVAS")')
                assert item["drag_hits_canvas"]
                page.mouse.move(700, 450)
                page.mouse.down()
                page.mouse.move(910, 470, steps=12)
                page.mouse.up()
                page.wait_for_timeout(1000)
                after = canvas.screenshot()
                item["canvas_changed_after_drag"] = before != after
                page.screenshot(path=str(args.out / (name + "_rotated.png")))
            else:
                details = page.locator("details")
                for index in range(details.count()):
                    details.nth(index).evaluate("node => node.open = true")
                item["facade_table_visible"] = "逐立面回查范围" in page.locator("body").inner_text()
                page.screenshot(path=str(args.out / (name + ".png")), full_page=True)
            item.update(page_errors=errors, failed_requests=failed, external_requests=external)
            report["pages"][name] = item
            page.close()
        browser.close()
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert all(not p["page_errors"] and not p["failed_requests"] and not p["external_requests"]
               for p in report["pages"].values())
    assert all(p.get("canvas_changed_after_drag", True) for p in report["pages"].values())
    assert report["pages"]["sm24_delivery"]["facade_table_visible"]


if __name__ == "__main__":
    main()
