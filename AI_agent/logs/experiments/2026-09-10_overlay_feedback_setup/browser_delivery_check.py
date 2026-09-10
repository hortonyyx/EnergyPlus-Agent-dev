"""Check projection links/status and the embedded selected BIM offline."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
run, out = args.run.resolve(), args.out.resolve()
out.mkdir(exist_ok=False)
delivery = json.loads((run / "delivery.json").read_text())
feedback = delivery["source_image_feedback"]
errors, failed, external = [], [], []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--use-gl=angle",
        "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    context = browser.new_context(viewport={"width": 1400, "height": 1000}, offline=True)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed.append(request.url))
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http:", "https:")) else None)
    page.goto((run / "delivery.html").as_uri())
    page.frame_locator("iframe").locator("canvas").wait_for()
    page.get_by_role("heading", name="原图回叠反馈").scroll_into_view_if_needed()
    page.wait_for_timeout(700)
    page.screenshot(path=str(out / "feedback.png"))
    links = page.locator("a").evaluate_all('(items)=>items.map(a=>a.getAttribute("href"))')
    expected = [row["overlay_image"] for row in feedback["current_source_projections"]]
    assert all(link in links and (run / link).is_file() for link in expected)
    text = page.locator("body").inner_text()
    current_count = len(expected)
    old_count = len(feedback["old_source_projections"])
    missing_count = len(feedback["floors_without_registered_views"])
    assert f"当前源投影 {current_count} 份" in text
    assert f"旧源投影 {old_count} 份" in text
    assert f"当前源无登记图面楼层 {missing_count} 个" in text
    page.locator("iframe").scroll_into_view_if_needed()
    page.wait_for_timeout(700)
    page.screenshot(path=str(out / "embedded_viewer.png"))
    report = {"offline": True, "browser": browser.version, "iframe_canvas_loaded": True,
        "current_projection_links": expected, "current_count": current_count, "old_count": old_count,
        "floors_without_registered_views": missing_count, "page_errors": errors,
        "failed_requests": failed, "external_requests": external,
        "scope": "Delivery labels/link targets match its saved JSON; selected BIM iframe loads. No image-fidelity verdict."}
    (out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    browser.close()
assert not errors and not failed and not external, report
print(json.dumps(report, ensure_ascii=False, indent=2))
