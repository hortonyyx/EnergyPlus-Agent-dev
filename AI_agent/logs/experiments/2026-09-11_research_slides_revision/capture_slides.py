"""Capture the revised deck with its real inline 3D views, offline."""
import argparse
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
DECK = ROOT / 'showcase/2026-09-11-research-report/index.html'
parser = argparse.ArgumentParser()
parser.add_argument('--out', default='layout_qa')
args = parser.parse_args()
OUT = Path(__file__).resolve().parent / args.out
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1600,'height':900}, device_scale_factor=1)
    errors, failed, external, report = [], [], [], []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.on('requestfailed', lambda req: failed.append(req.url))
    page.on('request', lambda req: external.append(req.url) if req.url.startswith(('https:','http:')) else None)
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.goto(DECK.as_uri())
    for n in range(1,8):
        page.evaluate('(n)=>location.hash=String(n)',n)
        page.wait_for_timeout(350)
        for frame_el in page.locator('.slide.active iframe').all():
            frame = frame_el.content_frame
            frame.locator('canvas').wait_for(state='visible',timeout=20000)
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / f'slide-{n:02}.png'))
        report.append(page.evaluate('''() => {
          const slide=document.querySelector('.slide.active'), box=slide.getBoundingClientRect();
          const selectors='h1,h2,h3,h4,p,figcaption,.eyebrow,.result-bottom,.shared-base';
          return {id:slide.id,frames:slide.querySelectorAll('iframe[src]').length,
            overflow:[...slide.querySelectorAll(selectors)].filter(el=>{
              const r=el.getBoundingClientRect();return r.right>box.right||r.left<box.left||r.bottom>box.bottom-70;
            }).map(el=>el.textContent), images:[...slide.querySelectorAll('img')].map(el=>({src:el.getAttribute('src'),loaded:el.complete&&el.naturalWidth>0}))};
        }'''))
    page.emulate_media(media='print')
    page.pdf(path=str(OUT/'research-report.pdf'),prefer_css_page_size=True,print_background=True)
    browser.close()
result={'slides':report,'page_errors':errors,'failed_requests':failed,'external_requests':external,
        'pdf_pages':len(re.findall(rb'/Type /Page\b',(OUT/'research-report.pdf').read_bytes()))}
(OUT/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
assert not errors and not failed and not external,result
assert result['pdf_pages']==7,result
assert all(not row['overflow'] and all(im['loaded'] for im in row['images']) for row in report),result
