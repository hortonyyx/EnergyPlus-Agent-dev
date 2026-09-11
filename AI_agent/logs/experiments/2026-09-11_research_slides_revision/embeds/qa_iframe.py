#!/usr/bin/env python3
"""Offline browser QA for the presentation embed copies."""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[5]
EMBEDS = ROOT / "showcase/2026-09-11-research-report/embeds"
OUT = Path(__file__).resolve().parent
CASES = [
    ("cover", "voimatalo.html", 885, 564, True),
    ("voimatalo-input-page3", "voimatalo-input.html", 418, 197, False),
    ("sm25", "sm25.html", 876, 475, True),
    ("voimatalo-input-page6", "voimatalo-input.html", 610, 475, False),
    ("voimatalo", "voimatalo.html", 748, 475, True),
]


async def mount(page, url: str, width: int, height: int):
    await page.set_viewport_size({"width": width + 20, "height": height + 20})
    await page.goto("file://" + quote(str(OUT / "qa_frame.html")))
    await page.evaluate(
        "([url,width,height]) => { const iframe=document.createElement('iframe'); iframe.id='embed'; iframe.src=url; "
        "iframe.style.width=width+'px'; iframe.style.height=height+'px'; document.body.append(iframe); }",
        [url, width, height],
    )
    iframe = page.locator("#embed")
    await iframe.wait_for()
    frame = page.frames[-1]
    await frame.locator("canvas").wait_for(state="visible", timeout=30_000)
    await frame.wait_for_timeout(120)
    return iframe, frame


async def drag(frame):
    canvas = frame.locator("canvas")
    box = await canvas.bounding_box()
    if not box:
        raise RuntimeError("canvas has no box")
    x, y = box["width"] * .52, box["height"] * .5
    await canvas.dispatch_event("pointerdown", {"button": 0, "buttons": 1, "clientX": x, "clientY": y, "pointerId": 1, "pointerType": "mouse"})
    await canvas.dispatch_event("pointermove", {"button": 0, "buttons": 1, "clientX": x + min(115, box["width"] * .26), "clientY": y - min(42, box["height"] * .18), "pointerId": 1, "pointerType": "mouse"})
    await canvas.dispatch_event("pointerup", {"button": 0, "buttons": 0, "clientX": x + min(115, box["width"] * .26), "clientY": y - min(42, box["height"] * .18), "pointerId": 1, "pointerType": "mouse"})
    await frame.wait_for_timeout(80)


async def capture(canvas, path: Path):
    data_url = await canvas.evaluate("node => node.toDataURL('image/png')")
    prefix, encoded = data_url.split(",", 1)
    if prefix != "data:image/png;base64":
        raise RuntimeError(f"unexpected canvas screenshot prefix: {prefix}")
    path.write_bytes(base64.b64decode(encoded))


async def main():
    results = []
    selected = set(sys.argv[1:])
    async with async_playwright() as pw:
        print("launch", flush=True)
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        for name, filename, width, height, has_layers in CASES:
            if selected and name not in selected:
                continue
            page = await browser.new_page()
            print(f"mount {name}", flush=True)
            errors = []
            console_errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            uri = "file://" + quote(str(EMBEDS / filename))
            if name == "cover":
                uri += "?bare=1"
            iframe, frame = await mount(page, uri, width, height)
            print(f"loaded {name}", flush=True)
            controls = await frame.locator("#embed-controls").count()
            canvas = frame.locator("canvas")
            default_explode = await frame.locator("#explode").input_value() if has_layers else None
            old_aside_hidden = None
            if filename == "voimatalo-input.html":
                old_aside = frame.locator("aside")
                old_aside_hidden = (
                    await old_aside.evaluate("node => getComputedStyle(node).display === 'none'")
                    if await old_aside.count() else True
                )
            if name == "voimatalo-input-page3":
                await capture(canvas, OUT / "voimatalo-input-page3_initial.png")
            await drag(frame)
            print(f"dragged {name}", flush=True)
            await capture(canvas, OUT / f"{name}_rotated.png")
            layer_changed = None
            if has_layers and name != "cover":
                await frame.locator("#embed-layers").click()
                await frame.wait_for_timeout(80)
                layer_changed = await frame.locator("#explode").input_value()
                await capture(canvas, OUT / f"{name}_layers.png")
            key_results = await frame.evaluate("""() => ['ArrowRight', 'f', 'o'].map(key => {
                const event = new KeyboardEvent('keydown', {key, bubbles:true, cancelable:true});
                const dispatchResult = document.dispatchEvent(event);
                return {key, prevented:event.defaultPrevented, dispatchResult};
            })""")
            await frame.wait_for_timeout(100)
            messages = await page.evaluate("embedMessages")
            # Cover is already mounted in bare mode. Avoid a second heavyweight
            # BIM initialization solely to assert the same CSS state.
            if name == "cover":
                bare_frame = frame
            else:
                _, bare_frame = await mount(page, uri + ("&" if "?" in uri else "?") + "bare=1", width, height)
            bare_controls_hidden = await bare_frame.locator("#embed-controls").evaluate("node => getComputedStyle(node).display === 'none'")
            results.append({
                "case": name, "iframe": [width, height], "controls": controls,
                "rotation_drag_completed": True, "default_explode_value": default_explode, "layer_explode_value": layer_changed,
                "keyboard_forwarded": all({"type": "bim-slide-key", "key": key} in messages for key in ["ArrowRight", "f", "o"]),
                "keyboard_prevented": all(item["prevented"] and not item["dispatchResult"] for item in key_results),
                "bare_controls_hidden": bare_controls_hidden,
                "old_input_aside_hidden": old_aside_hidden,
                "page_errors": errors,
                "console_errors": console_errors,
            })
            await page.close()
        await browser.close()
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
