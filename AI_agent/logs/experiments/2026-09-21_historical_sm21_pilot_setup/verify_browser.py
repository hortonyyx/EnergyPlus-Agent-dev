"""Check all five local report images and evidence links offline."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

RUN = Path(__file__).resolve().parent.parent / "2026-09-21_historical_sm21_pilot_run01"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900}, offline=True)
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto((RUN / "index.html").as_uri(), wait_until="load")
        result = await page.evaluate("""() => ({title:document.title,
          images:[...document.images].map(i=>({source:i.getAttribute('src'),loaded:i.complete && i.naturalWidth>0})),
          links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))})""")
        result["missing_local_links"] = [x for x in result["links"] if not (RUN / x).exists()]
        result["page_errors"] = errors
        result["offline_pass"] = (len(result["images"]) == 5 and all(x["loaded"] for x in result["images"])
                                  and not errors and not result["missing_local_links"])
        await page.screenshot(path=str(RUN / "browser_report.png"), full_page=True)
        with (RUN / "browser_verification.json").open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(json.dumps(result, ensure_ascii=False))
        await browser.close()
        assert result["offline_pass"]

if __name__ == "__main__":
    asyncio.run(main())
