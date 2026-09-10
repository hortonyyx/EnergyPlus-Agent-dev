"""Check final local entry points and preservation of original inputs/assets."""
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
LOG = Path(__file__).resolve().parent
ASSETS = ROOT / 'showcase/2026-09-11-research-report'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out = LOG / 'bundle_qa'
    out.mkdir(exist_ok=False)
    report = {'pages': {}, 'preserved': {}}
    glb = ASSETS / 'demos/textured-mass/input.glb'
    original = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
    assert sha(glb) == sha(original)
    magic, version, size = struct.unpack('<4sII', glb.read_bytes()[:12])
    assert magic == b'glTF' and version == 2 and size == glb.stat().st_size
    report['preserved']['input_glb'] = {'sha256': sha(glb), 'bytes': size, 'version': version}
    sm = json.loads((ASSETS / 'demos/sm25/manifest.json').read_text())
    assert sha(ROOT / sm['source']) == sm['source_sha256']
    report['preserved']['sm25_source_sha256'] = sm['source_sha256']
    # Compare every moved original file with its tracked baseline, including binaries.
    old_prefix = 'AI_agent/archive/showcase_animation/'
    baseline = '289d9771'
    old_files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', baseline, '--', old_prefix], cwd=ROOT, text=True).splitlines()
    line_ending_files = []
    for name in old_files:
        previous = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = ROOT / 'showcase/previous-showcase' / name[len(old_prefix):]
        moved = current.read_bytes()
        if previous != moved:
            # The existing SVG checkout uses CRLF; Git stores its LF form.
            assert current.suffix in {'.svg','.md','.html','.js','.css'}
            assert previous.replace(b'\r\n',b'\n') == moved.replace(b'\r\n',b'\n'), name
            line_ending_files.append(name)
    report['preserved']['old_showcase_unchanged_files'] = len(old_files)
    report['preserved']['git_checkout_line_ending_normalization'] = line_ending_files
    checked_links = 0
    for path in [ASSETS/'demos/textured-mass/README.md', LOG/'README.md', ROOT/'AI_agent/logs/worklog/2026-09-10_research_showcase_assets.md', ROOT/'AI_agent/logs/worklog/2026-09-10_research_presentation_outline.md']:
        for href in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text()):
            parsed = urlsplit(href)
            if parsed.scheme or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            assert target.exists(), (str(path), href)
            checked_links += 1
    report['markdown_local_links_checked'] = checked_links
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = browser.new_context(viewport={'width':1440,'height':950}, offline=True)
        for name, path in [('directory',ROOT/'showcase/index.html'),('assets',ASSETS/'assets.html'),('input',ASSETS/'demos/textured-mass/input_viewer.html')]:
            page = ctx.new_page()
            errors, failed, external = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('requestfailed', lambda r: failed.append(r.url[:160]))
            page.on('request', lambda r: external.append(r.url[:160]) if r.url.startswith(('http:', 'https:')) else None)
            page.goto(path.as_uri(), wait_until='load')
            page.wait_for_timeout(600)
            for href in page.locator('a[href]').evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))'):
                parsed = urlsplit(href)
                if not parsed.scheme and parsed.path:
                    assert (path.parent / unquote(parsed.path)).resolve().exists(), href
            assert page.locator('img').evaluate_all('(els)=>els.every(e=>e.complete && e.naturalWidth>0)')
            if name == 'assets':
                assert page.locator('article').count() == 2
            page.screenshot(path=str(out / (name + '.png')))
            report['pages'][name] = {'file':str(path.relative_to(ROOT)), 'sha256':sha(path), 'page_errors':errors, 'failed_requests':failed, 'external_requests':external}
            assert not errors and not failed and not external
            page.close()
        browser.close()
    original_source = ASSETS/'demos/textured-mass/exterior/source_model.json'
    rebuilt_source = Path('/tmp/voimatalo-exterior-repro-0910/source_model.json')
    if rebuilt_source.exists():
        assert rebuilt_source.read_bytes() == original_source.read_bytes()
        report['exterior_reproduction_byte_identical'] = True
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__':
    main()
