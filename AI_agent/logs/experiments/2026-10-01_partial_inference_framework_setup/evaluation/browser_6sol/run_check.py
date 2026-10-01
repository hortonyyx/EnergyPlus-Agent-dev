"""Browser QA for the archived 6 Sol candidate_11 viewer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("EP_PARTIAL_REPO", "/workspaces/EnergyPlus-Agent-dev"))
VIEWER = REPO / (
    "AI_agent/logs/experiments/2026-10-01_partial_inference_developer_tests/"
    "run_6sol/candidate_11/viewer.html"
)
CHROMIUM = Path(
    "/tmp/ep-bim-browser-qa/browsers/chromium-1234/chrome-linux64/chrome"
)


def main() -> None:
    if not VIEWER.is_file():
        raise FileNotFoundError(VIEWER)

    HERE.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    result: dict[str, object] = {
        "scope": "Browser behavior of archived run_6sol candidate_11; no model edits or architectural acceptance",
        "viewer": str(VIEWER.relative_to(REPO)),
        "original_viewer_modified": False,
        "errors": errors,
    }

    original = VIEWER.read_text()
    hook = """window.QA={camera,controls,renderer,pick,handleClick,allPickables,
      surfMeshes,winMeshes,openingMeshes,AX,root,BASES,floorName,zoneFloor,SOURCE_MAP};"""
    if "(function loop(){" not in original:
        raise RuntimeError("viewer animation-loop insertion point not found")
    instrumented = original.replace("(function loop(){", hook + "\n(function loop(){", 1)

    with tempfile.TemporaryDirectory(prefix="viewer_6sol_qa_") as temp_dir:
        instrumented_path = Path(temp_dir) / "viewer_instrumented.html"
        instrumented_path.write_text(instrumented)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(CHROMIUM),
                headless=True,
                args=[
                    "--no-sandbox",
                    "--enable-webgl",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            page = browser.new_page(viewport={"width": 1600, "height": 1050})
            phase = {"name": "original"}
            page.on(
                "pageerror",
                lambda error: errors.append(
                    {"phase": phase["name"], "kind": "pageerror", "message": str(error)}
                ),
            )
            page.on(
                "console",
                lambda message: errors.append(
                    {
                        "phase": phase["name"],
                        "kind": "console.error",
                        "message": message.text,
                    }
                )
                if message.type == "error"
                else None,
            )

            # Load and capture the exact archived viewer first.
            page.goto(VIEWER.as_uri(), wait_until="load")
            page.wait_for_function(
                "document.querySelector('canvas') && "
                "document.querySelectorAll('#floorSel option').length > 10"
            )
            page.wait_for_timeout(750)
            full_state = page.evaluate(
                """()=>({
                  canvas:{width:document.querySelector('canvas').width,
                          height:document.querySelector('canvas').height},
                  floorOptionCount:document.querySelector('#floorSel').options.length,
                  firstFloorOptions:[...document.querySelector('#floorSel').options]
                    .slice(0,9).map(o=>o.textContent),
                  selectedFloor:document.querySelector('#floorSel').selectedOptions[0].textContent,
                  canvasVisible:getComputedStyle(document.querySelector('canvas')).display!=='none'
                })"""
            )
            page.screenshot(path=str(HERE / "whole_building.png"))

            # An external temporary copy exposes closure-local viewer helpers for a
            # deterministic real canvas click; the archived viewer remains untouched.
            phase["name"] = "instrumented_f3"
            page.goto(instrumented_path.as_uri(), wait_until="load")
            page.wait_for_function("window.QA && QA.allPickables().length > 0")
            page.wait_for_timeout(500)

            f3_mapping = page.evaluate(
                """()=>{
                  const entry=Object.entries(QA.SOURCE_MAP.zones||{})
                    .find(([,sourceId])=>sourceId==='F3:west_4');
                  if(!entry) throw new Error('source F3:west_4 map missing');
                  const index=QA.zoneFloor[entry[0]];
                  const option=document.querySelector('#floorSel').options[index+1];
                  if(!option) throw new Error('mapped F3 floor option missing');
                  return {value:option.value,label:option.textContent,index,zone:entry[0]};
                }"""
            )
            page.select_option("#floorSel", f3_mapping["value"])
            page.select_option("#colorBy", "zone")
            for index in range(page.locator("aside details summary").count()):
                page.locator("aside details summary").nth(index).click()
            page.check("#enZ")
            page.locator("#posZ").evaluate(
                """e=>{
                  e.value='8.4';
                  e.dispatchEvent(new Event('input',{bubbles:true}));
                }"""
            )
            page.locator("#opacity").evaluate(
                """e=>{
                  e.value='0.8';
                  e.dispatchEvent(new Event('input',{bubbles:true}));
                }"""
            )

            point = page.evaluate(
                """()=>{
                  const target=new THREE.Vector3(-14,-4.5,7.5);
                  QA.controls.target.set(-10.8,-4.5,7.5);
                  QA.camera.up.set(0,0,1);
                  QA.camera.position.set(-65,-4.5,20);
                  QA.controls.update(); QA.camera.updateProjectionMatrix();
                  QA.camera.updateMatrixWorld();
                  const p=target.clone().project(QA.camera);
                  const r=QA.renderer.domElement.getBoundingClientRect();
                  return {x:r.left+(p.x+1)*r.width/2,
                          y:r.top+(1-p.y)*r.height/2};
                }"""
            )
            click_hit = page.evaluate(
                """p=>{
                  const u=QA.pick({clientX:p.x,clientY:p.y})?.object?.userData;
                  return u&&{zone:u.zone,floor:u.floor,kind:u.kind,type:u.type};
                }""",
                point,
            )
            page.mouse.click(point["x"], point["y"])
            page.wait_for_function(
                "document.querySelector('#sel').innerText.includes('F3:west_4')"
            )
            page.evaluate(
                """()=>{
                  QA.controls.target.set(-1.5,-3.5,6.7);
                  QA.camera.up.set(0,1,0);
                  QA.camera.position.set(-1.5,-3.5,78);
                  QA.controls.update(); QA.camera.updateProjectionMatrix();
                  QA.camera.updateMatrixWorld();
                }"""
            )
            page.wait_for_timeout(500)

            f3_state = page.evaluate(
                """p=>({
                  floor:document.querySelector('#floorSel').selectedOptions[0].textContent,
                  colorBy:document.querySelector('#colorBy').value,
                  asideDetailsCollapsed:[...document.querySelectorAll('aside details')]
                    .every(x=>!x.open),
                  cutZ:{enabled:document.querySelector('#enZ').checked,
                        position:Number(document.querySelector('#posZ').value)},
                  visible:{surfaces:QA.surfMeshes.filter(x=>x.visible).length,
                           windows:QA.winMeshes.filter(x=>x.visible).length,
                           openings:QA.openingMeshes.filter(x=>x.visible).length},
                  selection:document.querySelector('#sel').innerText.split('\\n').slice(0,8),
                  selectedSourceF3:document.querySelector('#sel').innerText
                    .includes('F3:west_4')
                })""",
                point,
            )
            f3_state["clickHit"] = click_hit
            page.screenshot(path=str(HERE / "f3_section_room_selected.png"))
            browser.close()

    if errors:
        result["status"] = "fail"
    elif f3_mapping["label"].startswith("F3 "):
        result["status"] = "pass"
    else:
        result["status"] = "partial"
        result["finding"] = (
            "The source F3 geometry at z=6.70 is selectable and sectionable, but the "
            f"floor menu labels it {f3_mapping['label']}; earlier duplicate-z entries "
            "create empty/misleading floor choices."
        )
    result["whole_building"] = full_state
    result["source_f3_floor_mapping"] = f3_mapping
    result["f3_section_selection"] = f3_state
    result["screenshots"] = ["whole_building.png", "f3_section_room_selected.png"]
    (HERE / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    if errors:
        raise AssertionError(errors)
    print(json.dumps({"status": result["status"], "errors": errors}))


if __name__ == "__main__":
    main()
