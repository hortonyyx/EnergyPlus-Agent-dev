"""Check the selected saved BIM in isolated offline Chromium; no model calls."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
parser.add_argument('--floor-index', default='0')
parser.add_argument('--out', type=Path)
args = parser.parse_args()
run = args.run.resolve()
summary = json.loads((run / 'summary.json').read_text())
candidate = summary['delivery']['candidate']
viewer = run / candidate / 'viewer.html'
out = args.out.resolve() if args.out else run / 'browser_check'
out.mkdir(exist_ok=False)
errors, requests, failed = [], [], []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    context = browser.new_context(viewport={'width': 1400, 'height': 1000}, offline=True)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.on('requestfailed', lambda request: failed.append({'url': request.url, 'failure': request.failure}))
    page.goto(viewer.as_uri())
    page.wait_for_function('window.THREE && document.querySelector("canvas")')
    while page.locator('details[open] > summary').count():
        page.locator('details[open] > summary').first.click()
    page.locator('#floorSel').select_option(args.floor_index)
    page.wait_for_timeout(700)
    before = page.locator('canvas').screenshot()
    page.screenshot(path=str(out / 'floor.png'))
    drag_hits = page.evaluate('[document.elementFromPoint(700,450).tagName, document.elementFromPoint(910,470).tagName]')
    assert drag_hits == ['CANVAS', 'CANVAS'], drag_hits
    page.mouse.move(700, 450)
    page.mouse.down()
    page.mouse.move(910, 470, steps=12)
    page.mouse.up()
    page.wait_for_timeout(700)
    changed = before != page.locator('canvas').screenshot()
    page.screenshot(path=str(out / 'floor_rotated.png'))
    report = {'candidate': candidate, 'floor_index': args.floor_index, 'browser': browser.version, 'offline': True,
              'page_errors': errors, 'external_requests': requests, 'failed_requests': failed,
              'canvas_drag_changed': changed, 'drag_hits': drag_hits,
              'scope': 'Selected saved viewer loads and rotates on the selected floor; not an independent geometry or image-fidelity judgment.'}
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    browser.close()
assert changed and not errors and not requests and not failed, report
print(json.dumps(report, ensure_ascii=False, indent=2))
