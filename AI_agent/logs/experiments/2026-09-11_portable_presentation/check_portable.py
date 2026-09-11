"""Open the distributed ZIP outside the repository with networking blocked."""
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
FOLDER = ROOT / 'showcase/BIM-Agent-Presentation'
ARCHIVE = FOLDER.with_suffix('.zip')
report = {'slides': [], 'errors': [], 'console_errors': [], 'failed_requests': [],
          'external_requests': [], 'out_of_bundle_requests': []}
with tempfile.TemporaryDirectory(prefix='汇报复制测试 ') as tmp, sync_playwright() as p:
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        archive.extractall(tmp)
    bundle = Path(tmp) / FOLDER.name
    copied = [f for f in bundle.rglob('*') if f.is_file()]
    assert {f.relative_to(bundle) for f in copied} == {f.relative_to(FOLDER) for f in FOLDER.rglob('*') if f.is_file()}
    assert all(f.read_bytes() == (FOLDER / f.relative_to(bundle)).read_bytes() for f in copied)
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    page.on('pageerror', lambda e: report['errors'].append(str(e)))
    page.on('console', lambda m: report['console_errors'].append(m.text) if m.type == 'error' else None)
    page.on('requestfailed', lambda r: report['failed_requests'].append(r.url))

    def requested(req):
        url = urlsplit(req.url)
        if url.scheme in ('http', 'https'):
            report['external_requests'].append(req.url)
        if url.scheme == 'file' and not Path(unquote(url.path)).is_relative_to(bundle):
            report['out_of_bundle_requests'].append(req.url)

    page.on('request', requested)
    page.route('http://**/*', lambda r: r.abort())
    page.route('https://**/*', lambda r: r.abort())
    page.goto((bundle / 'index.html').as_uri())
    for n, expected in enumerate((1, 0, 1, 0, 1, 2, 0), 1):
        page.evaluate('(n) => location.hash=String(n)', n)
        page.wait_for_function('(n) => document.querySelector(".slide.active").id === `slide-${n}`', arg=n)
        page.wait_for_timeout(300)
        frames = page.locator('.slide.active iframe[src]').all()
        assert len(frames) == expected
        rotations = []
        for frame in frames:
            canvas = frame.content_frame.locator('canvas').first
            canvas.wait_for(state='visible')
            page.wait_for_timeout(400)
            before = canvas.screenshot()
            box = canvas.bounding_box()
            x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + min(85, box['width']/4), y + 30, steps=8)
            page.mouse.up()
            page.wait_for_timeout(200)
            rotated = before != canvas.screenshot()
            assert rotated
            rotations.append(rotated)
        images_ok = page.locator('.slide.active img').evaluate_all('(els) => els.every(e => e.complete && e.naturalWidth > 0)')
        assert images_ok
        report['slides'].append({'page': n, 'images_loaded': images_ok, 'frames': len(frames), 'rotations': rotations})
    browser.close()
    report['files'] = len(copied)
    report['pdf_pages'] = len(re.findall(rb'/Type /Page\b', (bundle / 'research-report.pdf').read_bytes()))
    assert report['pdf_pages'] == 7
report['zip_bytes'] = ARCHIVE.stat().st_size
report['zip_sha256'] = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
(HERE / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
assert not any(report[k] for k in ('errors','console_errors','failed_requests','external_requests','out_of_bundle_requests'))
