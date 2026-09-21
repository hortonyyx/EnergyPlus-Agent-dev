"""Offline loading and reference-table check for a local observation page."""
import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def check(run):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900}, offline=True)
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto((run / "index.html").as_uri(), wait_until="load")
        await page.locator("details").evaluate_all("xs => xs.forEach(x => x.open = true)")
        result = await page.evaluate("""() => ({title:document.title,
          images:[...document.images].map(i=>({source:i.getAttribute('src'),loaded:i.complete && i.naturalWidth>0})),
          tables:document.querySelectorAll('table').length,
          links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))})""")
        result["missing_local_links"] = [x for x in result["links"] if not (run / x).exists()]
        result["page_errors"] = errors
        comparisons = len(list(run.glob("facade_comparisons/*.json")))
        result["offline_pass"] = (all(x["loaded"] for x in result["images"]) and len(result["images"]) == 2
                                  and result["tables"] == comparisons * 3 and not errors
                                  and not result["missing_local_links"])
        await page.screenshot(path=str(run / "browser_report.png"), full_page=True)
        with (run / "browser_verification.json").open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(json.dumps(result, ensure_ascii=False))
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(check(args.run.resolve()))
