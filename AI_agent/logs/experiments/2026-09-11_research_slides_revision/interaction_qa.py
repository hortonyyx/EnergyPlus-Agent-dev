#!/usr/bin/env python3
"""Offline end-to-end interaction QA for the seven-page research deck."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Page, async_playwright


ROOT = Path(__file__).resolve().parents[4]
DECK = ROOT / "showcase/2026-09-11-research-report/index.html"
OUT = Path(__file__).resolve().parent / "interaction_qa"
VIEWPORTS = [(1440, 900), (1920, 1080)]
EXPECTED_FRAMES = {1: 1, 2: 0, 3: 1, 4: 0, 5: 1, 6: 2, 7: 0}
EXPECTED_DRAWINGS = {
    "sm25-1f.png",
    "sm25-2f.png",
    "sm25-North.png",
    "sm25-South.png",
    "sm25-East.png",
    "sm25-West.png",
}


class QA:
    def __init__(self, width: int, height: int):
        self.viewport = f"{width}x{height}"
        self.checks: list[dict] = []

    def check(self, name: str, passed: bool, detail=None):
        item = {"name": name, "passed": bool(passed)}
        if detail is not None:
            item["detail"] = detail
        self.checks.append(item)
        if not passed:
            raise AssertionError(f"{self.viewport}: {name}: {detail}")


async def current_slide(page: Page) -> int:
    return int(await page.locator("#page-current").inner_text())


async def wait_slide(page: Page, number: int):
    await page.wait_for_function(
        "n => document.querySelector('#page-current')?.textContent === String(n).padStart(2,'0')",
        arg=number,
    )
    await page.locator(f"#slide-{number}.active").wait_for(state="visible")


async def press_and_wait(page: Page, key: str, number: int):
    await page.keyboard.press(key)
    await wait_slide(page, number)


async def active_frames(page: Page):
    frames = []
    for locator in await page.locator(".slide.active iframe[src]").all():
        handle = await locator.element_handle()
        frame = await handle.content_frame() if handle else None
        if frame is None:
            raise AssertionError("active iframe has no content frame")
        await frame.locator("canvas").wait_for(state="visible", timeout=30_000)
        await frame.wait_for_timeout(180)
        frames.append((locator, frame))
    return frames


async def frame_state(page: Page):
    return await page.locator("iframe[data-src]").evaluate_all(
        "els => els.map((e,i) => ({i, src:e.getAttribute('src'), slide:Number(e.closest('.slide').id.slice(6)), loaded:e.parentElement.classList.contains('is-loaded')}))"
    )


async def drag_and_compare(frame):
    canvas = frame.locator("canvas")
    box = await canvas.bounding_box()
    if not box:
        raise AssertionError("canvas has no bounding box")
    before = await canvas.screenshot(type="png")
    x = box["x"] + box["width"] * 0.50
    y = box["y"] + box["height"] * 0.50
    await canvas.hover(position={"x": box["width"] * 0.50, "y": box["height"] * 0.50})
    await frame.page.mouse.move(x, y)
    await frame.page.mouse.down()
    await frame.page.mouse.move(x + min(110, box["width"] * 0.25), y - min(38, box["height"] * 0.16), steps=8)
    await frame.page.mouse.up()
    await frame.wait_for_timeout(160)
    after = await canvas.screenshot(type="png")
    return {
        "canvas": [round(box["width"]), round(box["height"])],
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest(),
        "pixels_changed": before != after,
    }


async def validate_active(page: Page, qa: QA, number: int):
    await wait_slide(page, number)
    frames = await active_frames(page)
    qa.check(
        f"page {number} active iframe count",
        len(frames) == EXPECTED_FRAMES[number],
        len(frames),
    )
    state = await frame_state(page)
    active_src = [item for item in state if item["src"]]
    qa.check(
        f"page {number} only active iframe sources mounted",
        len(active_src) == EXPECTED_FRAMES[number] and all(item["slide"] == number for item in active_src),
        state,
    )
    rotations = []
    for _, frame in frames:
        old_panels = await frame.locator("aside").count()
        visible_old_panels = await frame.locator("aside:visible").count()
        qa.check(
            f"page {number} legacy raw panel hidden",
            visible_old_panels == 0,
            {"present": old_panels, "visible": visible_old_panels},
        )
        rotation = await drag_and_compare(frame)
        rotations.append(rotation)
        qa.check(f"page {number} canvas drag changes rendering", rotation["pixels_changed"], rotation)
    return frames, rotations


async def assert_hidden_unloaded(page: Page, qa: QA, number: int):
    state = await frame_state(page)
    hidden = [item for item in state if item["slide"] == number]
    qa.check(
        f"page {number} iframe unloaded while hidden",
        all(item["src"] is None and not item["loaded"] for item in hidden),
        hidden,
    )


async def postmessage_roundtrip(page: Page, qa: QA, source: int, iframe_index: int = 0):
    frames, _ = await validate_active(page, qa, source)
    frame = frames[iframe_index][1]
    canvas = frame.locator("canvas")
    await canvas.click(position={"x": 25, "y": 25})
    await page.keyboard.press("KeyA")
    qa.check(f"page {source} model unhandled key stays on slide", await current_slide(page) == source)
    await canvas.hover(position={"x": 25, "y": 25})
    await page.mouse.wheel(0, 240)
    await page.wait_for_timeout(100)
    qa.check(f"page {source} model wheel stays on slide", await current_slide(page) == source)
    await page.keyboard.press("ArrowRight")
    await wait_slide(page, source + 1)
    qa.check(f"page {source} iframe ArrowRight advances by postMessage", True, f"{source}->{source + 1}")
    await assert_hidden_unloaded(page, qa, source)
    await press_and_wait(page, str(source), source)
    reloaded = await active_frames(page)
    qa.check(
        f"page {source} iframe reloads after roundtrip",
        len(reloaded) == EXPECTED_FRAMES[source],
        await frame_state(page),
    )


async def lowercase_shortcut_relay(page: Page, qa: QA):
    await press_and_wait(page, "Digit1", 1)
    frames = await active_frames(page)
    canvas = frames[0][1].locator("canvas")
    await page.evaluate(
        "() => { window.__qaFullscreenCalls=0; Object.defineProperty(document.documentElement,'requestFullscreen',{configurable:true,value:()=>{window.__qaFullscreenCalls++; return Promise.resolve();}}); }"
    )
    await canvas.click(position={"x": 25, "y": 25})
    await page.keyboard.press("KeyF")
    await page.wait_for_function("() => window.__qaFullscreenCalls === 1")
    qa.check("iframe lowercase f relays to fullscreen command", True)
    await canvas.click(position={"x": 25, "y": 25})
    await page.keyboard.press("KeyO")
    await page.locator("#overview").wait_for(state="visible")
    qa.check("iframe lowercase o relays to overview command", True)
    await assert_hidden_unloaded(page, qa, 1)
    await page.keyboard.press("Escape")
    await page.locator("#overview").wait_for(state="hidden")
    reloaded = await active_frames(page)
    qa.check("page 1 reloads after iframe overview relay", len(reloaded) == 1)


async def run_viewport(browser, width: int, height: int):
    qa = QA(width, height)
    context = await browser.new_context(viewport={"width": width, "height": height})
    external_requests: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []

    async def block_external(route):
        external_requests.append(route.request.url)
        await route.abort()

    await context.route("http://**/*", block_external)
    await context.route("https://**/*", block_external)
    page = await context.new_page()
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    await page.goto("file://" + quote(str(DECK)), wait_until="load")
    await wait_slide(page, 1)

    qa.check("seven slides present", await page.locator(".slide").count() == 7)
    qa.check("no demo-button", await page.locator(".demo-button").count() == 0)
    qa.check("no HTML dialog element", await page.locator("dialog").count() == 0)
    qa.check("overview begins hidden", await page.locator("#overview").is_hidden())

    await page.locator("#next").click()
    await wait_slide(page, 2)
    await page.locator("#prev").click()
    await wait_slide(page, 1)
    qa.check("footer previous/next buttons navigate", True)

    await press_and_wait(page, "End", 7)
    await press_and_wait(page, "Home", 1)
    await press_and_wait(page, "Digit4", 4)
    qa.check("Home End and numeric navigation", True)
    await page.mouse.wheel(0, 460)
    await page.wait_for_timeout(100)
    qa.check("deck wheel does not change slide", await current_slide(page) == 4)

    await page.keyboard.press("KeyO")
    await page.locator("#overview").wait_for(state="visible")
    overview_buttons = page.locator("#overview-items button")
    qa.check("overview has seven entries", await overview_buttons.count() == 7)
    await overview_buttons.nth(2).click()
    await wait_slide(page, 3)
    qa.check("overview entry navigates and closes", await page.locator("#overview").is_hidden())
    await page.locator("#page-toggle").click()
    await page.locator("#overview").wait_for(state="visible")
    await page.keyboard.press("Escape")
    qa.check("overview closes with Escape", await page.locator("#overview").is_hidden())

    for number in (2, 4, 7):
        await press_and_wait(page, f"Digit{number}", number)
        await validate_active(page, qa, number)

    await press_and_wait(page, "Digit5", 5)
    drawings = await page.locator("#slide-5 .all-drawings img").evaluate_all(
        "imgs => imgs.map(img => ({file:new URL(img.src).pathname.split('/').pop(), complete:img.complete, natural:[img.naturalWidth,img.naturalHeight], rect:[Math.round(img.getBoundingClientRect().width),Math.round(img.getBoundingClientRect().height)]}))"
    )
    qa.check(
        "page 5 six original drawings all render",
        len(drawings) == 6
        and {item["file"] for item in drawings} == EXPECTED_DRAWINGS
        and all(item["complete"] and min(item["natural"]) > 0 and min(item["rect"]) > 0 for item in drawings),
        drawings,
    )
    label5 = " ".join((await page.locator("#slide-5 .result-model > figcaption").inner_text()).split())
    label6 = " ".join((await page.locator("#slide-6 .result-grid > figure").nth(1).locator(":scope > figcaption").inner_text()).split())
    qa.check("page 5 output labelled lightweight BIM", "轻量 BIM" in label5 and "Lightweight BIM" in label5, label5)
    qa.check("page 6 output labelled lightweight BIM", "轻量 BIM" in label6 and "Lightweight BIM" in label6, label6)

    # Every live page: actual canvas, real drag, child keyboard relay, unload and reload.
    for source in (1, 3, 5):
        await press_and_wait(page, f"Digit{source}", source)
        await postmessage_roundtrip(page, qa, source)
    await press_and_wait(page, "Digit6", 6)
    await postmessage_roundtrip(page, qa, 6, 0)
    await press_and_wait(page, "Digit6", 6)
    await postmessage_roundtrip(page, qa, 6, 1)
    await lowercase_shortcut_relay(page, qa)

    qa.check("no external network requests", not external_requests, external_requests)
    qa.check("no page errors", not page_errors, page_errors)
    qa.check("no console errors", not console_errors, console_errors)
    await context.close()
    return {
        "viewport": qa.viewport,
        "passed": all(item["passed"] for item in qa.checks),
        "checks": qa.checks,
        "external_requests": external_requests,
        "page_errors": page_errors,
        "console_errors": console_errors,
    }


def write_report(results: list[dict]):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "deck": str(DECK.relative_to(ROOT)),
        "offline": True,
        "browser_args": ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        "passed": all(result["passed"] for result in results),
        "results": results,
    }
    (OUT / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 整页交互 QA",
        "",
        f"- 时间：{payload['timestamp_utc']}",
        "- 入口：`showcase/2026-09-11-research-report/index.html`（`file://`）",
        "- 网络：HTTP/HTTPS 请求全部拦截；实际外网请求为 0。",
        f"- 总结果：{'通过' if payload['passed'] else '失败'}",
        "",
    ]
    for result in results:
        lines.extend([
            f"## {result['viewport']}",
            "",
            f"- 结果：{'通过' if result['passed'] else '失败'}",
            f"- 检查数：{len(result['checks'])}",
            f"- 页面错误：{len(result['page_errors'])}；控制台错误：{len(result['console_errors'])}",
            "",
        ])
    lines.extend([
        "已覆盖 7 页导航、目录、数字键、Home/End、滚轮不翻页、活跃 iframe 的真实 canvas 加载和拖动、iframe 键盘消息翻页、隐藏页卸载与返回重载、第 5 页六张原图、5/6 页输出标签，以及弹窗残留检查。逐项证据见 `results.json`。",
        "",
    ])
    (OUT / "QA.md").write_text("\n".join(lines), encoding="utf-8")


async def run_console_recheck(browser):
    """Short final regression after an embed-only fix; covers all three final embeds."""
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    external_requests: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []

    async def block_external(route):
        external_requests.append(route.request.url)
        await route.abort()

    await context.route("http://**/*", block_external)
    await context.route("https://**/*", block_external)
    page = await context.new_page()
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    await page.goto("file://" + quote(str(DECK)), wait_until="load")
    cases = []
    # Page 5 supplies sm25; page 6 supplies both Voimatalo texture and BIM embeds.
    for number in (5, 6):
        await page.evaluate("n => { location.hash = '#' + n; }", number)
        await wait_slide(page, number)
        frames = await active_frames(page)
        for index, (locator, frame) in enumerate(frames):
            title = await locator.get_attribute("title")
            panel_visible = await frame.locator("aside:visible").count()
            rotation = await drag_and_compare(frame)
            cases.append({
                "slide": number,
                "index": index,
                "title": title,
                "canvas": rotation["canvas"],
                "rotation_pixels_changed": rotation["pixels_changed"],
                "legacy_raw_panel_visible": panel_visible,
            })
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "viewport": "1440x900",
        "scope": "post-fix shortest load/rotate/console regression for all three final embed files",
        "passed": len(cases) == 3
        and all(case["rotation_pixels_changed"] and case["legacy_raw_panel_visible"] == 0 for case in cases)
        and not external_requests
        and not page_errors
        and not console_errors,
        "cases": cases,
        "external_requests": external_requests,
        "page_errors": page_errors,
        "console_errors": console_errors,
    }
    await context.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "final_console_recheck.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not result["passed"]:
        raise AssertionError(json.dumps(result, ensure_ascii=False))
    print(json.dumps({"final_console_recheck": True, "cases": len(cases)}, ensure_ascii=False))


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        try:
            if "--console-recheck" in sys.argv:
                await run_console_recheck(browser)
                return
            else:
                for width, height in VIEWPORTS:
                    print(f"QA {width}x{height}", flush=True)
                    results.append(await run_viewport(browser, width, height))
        finally:
            await browser.close()
    write_report(results)
    print(json.dumps({"passed": all(result["passed"] for result in results), "viewports": [result["viewport"] for result in results]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
