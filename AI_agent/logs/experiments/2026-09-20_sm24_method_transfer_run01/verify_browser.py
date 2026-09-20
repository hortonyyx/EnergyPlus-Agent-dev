"""Open the selected saved source offline after the generation has ended."""
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

RUN = Path(__file__).resolve().parent


def main():
    if not (RUN / 'summary.json').is_file():
        raise RuntimeError('Wait until generation finishes')
    delivery = json.loads((RUN / 'delivery.json').read_text())
    candidate = delivery['candidate']
    folder = RUN / candidate
    source = json.loads((folder / 'source_model.json').read_text())
    errors, external, failed = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=[
            '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
            '--enable-unsafe-swiftshader'])
        context = browser.new_context(viewport={'width': 1500, 'height': 1000}, offline=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url)
                if request.url.startswith(('http:', 'https:')) else None)
        page.on('requestfailed', lambda request: failed.append(request.url))
        page.goto((folder / 'viewer.html').as_uri())
        page.wait_for_function("window.GEO && document.querySelector('canvas')")
        assert page.evaluate('GEO.source_model.source_model_sha256') == source['source_model_sha256']
        page.locator('#opacity').fill('0.45')
        page.locator('#opacity').dispatch_event('input')
        page.wait_for_timeout(300)
        canvas = page.locator('#app canvas')
        before = canvas.screenshot()
        page.mouse.move(850, 370)
        page.mouse.down()
        page.mouse.move(990, 435, steps=12)
        page.mouse.up()
        page.wait_for_timeout(300)
        after = canvas.screenshot()
        assert before != after, 'rotation did not change canvas'
        page.screenshot(path=str(RUN / 'viewer_verified.png'))
        page.goto((RUN / 'delivery.html').as_uri())
        assert page.locator('body').inner_text().strip()
        browser.close()
    assert not errors and not external and not failed, (errors, external, failed)
    report = {
        'candidate': candidate,
        'source_model_sha256': source['source_model_sha256'],
        'embedded_source_matches': True, 'rotation_changes_canvas': True,
        'canvas_sha256_before': hashlib.sha256(before).hexdigest(),
        'canvas_sha256_after': hashlib.sha256(after).hexdigest(),
        'delivery_opened': True, 'offline': True,
        'page_errors': errors, 'external_requests': external, 'failed_requests': failed,
        'scope': 'Actual offline viewing, not drawing fidelity or user acceptance',
    }
    (RUN / 'browser_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
