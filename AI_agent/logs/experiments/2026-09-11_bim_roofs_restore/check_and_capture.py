"""Check restored presentation surfaces and refresh the two BIM posters offline."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DECK = ROOT / 'showcase/2026-09-11-research-report'


def geometry(path):
    text = path.read_text()
    return json.JSONDecoder().raw_decode(text.split('window.GEO =', 1)[1].lstrip())[0]


report = {'models': [], 'page_errors': [], 'console_errors': [], 'external_requests': []}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900}, device_scale_factor=1)
    page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
    page.on('console', lambda m: report['console_errors'].append(m.text) if m.type == 'error' else None)
    page.on('request', lambda r: report['external_requests'].append(r.url) if r.url.startswith(('http:', 'https:')) else None)
    page.route('http://**/*', lambda r: r.abort())
    page.route('https://**/*', lambda r: r.abort())
    for name, source in [('sm25', 'sm25/sm25_showcase.html'), ('voimatalo', 'textured-mass/index.html')]:
        embed = DECK / 'embeds' / f'{name}.html'
        data = geometry(embed)
        assert data == geometry(DECK / 'demos' / source)
        assert "SURF.filter(s=>s.type !== 'Ceiling')" not in embed.read_text()
        counts = dict(Counter(s['type'] for s in data['surfaces']))
        assert counts['Floor'] > 0 and counts['Ceiling'] > 0
        page.goto(embed.as_uri() + '?bare=1')
        canvas = page.locator('canvas').first
        canvas.wait_for(state='visible')
        page.wait_for_timeout(650)
        canvas.screenshot(path=str(DECK / 'assets' / f'{name}-model.png'))
        captures = []
        for mode in ('whole', 'layers'):
            page.locator(f'#embed-{mode}').evaluate('(el) => el.click()')
            page.wait_for_timeout(300)
            before = canvas.screenshot(path=str(HERE / f'{name}-{mode}.png'))
            page.mouse.move(800, 450)
            page.mouse.down()
            page.mouse.move(960, 510, steps=12)
            page.mouse.up()
            page.wait_for_timeout(300)
            after = canvas.screenshot()
            assert hashlib.sha256(before).digest() != hashlib.sha256(after).digest()
            captures.append({'mode': mode, 'rotation_changes_image': True})
            page.locator('#embed-reset').evaluate('(el) => el.click()')
        report['models'].append({'name': name, 'source_geometry_unchanged': True,
            'surface_counts': counts, 'views': captures})
    page.goto((DECK / 'index.html').as_uri())
    for n in (1, 5, 6):
        page.evaluate('(n) => location.hash=String(n)', n)
        page.wait_for_timeout(300)
        for el in page.locator('.slide.active iframe').all():
            el.content_frame.locator('canvas').wait_for(state='visible')
        page.wait_for_timeout(700)
        page.screenshot(path=str(HERE / f'slide-{n:02}.png'))
    browser.close()
(HERE / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
assert not any(report[key] for key in ('page_errors', 'console_errors', 'external_requests'))
