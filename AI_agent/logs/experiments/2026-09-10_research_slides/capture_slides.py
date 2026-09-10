"""Capture the actual offline slide pages and check visible content bounds."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
DECK = ROOT / 'showcase/2026-09-11-research-report/index.html'
OUT = Path(__file__).resolve().parent / 'layout_qa'
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('http://**/*', lambda route: route.abort())
    page.route('https://**/*', lambda route: route.abort())
    page.goto(DECK.as_uri())
    report = []
    for n in range(1, 8):
        page.keyboard.press(str(n))
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / f'slide-{n:02}.png'))
        report.append(page.evaluate('''() => {
          const slide=document.querySelector('.slide.active');
          const outer=slide.getBoundingClientRect();
          const text=[...slide.querySelectorAll('h1,h2,h3,p,figcaption,.eyebrow')];
          return {id:slide.id, overflow:text.filter(el=>{
            const r=el.getBoundingClientRect();
            return r.right>outer.right || r.left<outer.left || r.bottom>outer.bottom-70;
          }).map(el=>el.textContent), images:[...slide.querySelectorAll('img')].map(el=>({src:el.getAttribute('src'),loaded:el.complete && el.naturalWidth>0}))};
        }'''))
    page.emulate_media(media='print')
    page.pdf(path=str(OUT / 'research-report.pdf'), prefer_css_page_size=True, print_background=True)
    browser.close()
assert not errors, errors
assert all(not x['overflow'] and all(im['loaded'] for im in x['images']) for x in report), report
(OUT / 'report.json').write_text(json.dumps({'slides':report,'page_errors':errors},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
