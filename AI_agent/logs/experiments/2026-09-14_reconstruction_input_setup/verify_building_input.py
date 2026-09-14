"""Exercise the real read-only inputs MCP with sm24's declared building input, offline."""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from scripts.tool_scripts.bim_agent_inputs import freeze_building_input
from scripts.tool_scripts.run_bim_agent import digest, dump


async def main():
    target = Path(__file__).resolve().parent / "input_transport"
    target.mkdir(exist_ok=False)
    (target / "images").mkdir()
    originals = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data"
    images = {}
    for path in sorted(originals.glob("*.png")):
        shutil.copy2(path, target / "images" / path.name)
        with Image.open(path) as picture:
            size = list(picture.size)
        images[path.name] = {"size": size, "sha256": digest(path)}
    declaration_path = originals / "testdata_prompt.json"
    supplied = freeze_building_input(declaration_path, target, images)
    manifest = {"images": images, "building_input": supplied,
                "input_mode": "offline_input_transport_check_no_model_generation"}
    dump(target / "inputs.json", manifest)
    parameters = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(target), "--readonly"],
        cwd=str(ROOT))
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("inputs", {})
            assert not result.isError
            received = result.structuredContent or json.loads(result.content[0].text)
            dump(target / "actual_inputs_response.json", received)
            names = {tool.name for tool in (await session.list_tools()).tools}
    raw = declaration_path.read_bytes()
    checks = {
        "raw_bytes_preserved": (target / "building_input.json").read_bytes() == raw,
        "raw_hash_matches": supplied["raw_sha256"] == hashlib.sha256(raw).hexdigest(),
        "declaration_received_unchanged": received["building_input"]["declaration"] == json.loads(raw),
        "five_original_images_received": received["images"] == images and len(images) == 5,
        "all_declared_views_associated": len(supplied["image_path_associations"]) == 5 and all(
            row["status"] == "associated_by_exact_basename" for row in supplied["image_path_associations"]),
        "thermal_zone_semantics_received": received["building_input"]["field_semantics"] == supplied["field_semantics"],
        "readonly_no_build_or_delegation": not ({"build_bim", "revise_bim", "review_detail"} & names),
    }
    report = {"checks": checks, "all_checks_passed": all(checks.values()),
              "limits": "Real stdio transport with original sm24 declaration and image bytes, no subscription invocation or building generation. Not evidence that a model used the declaration correctly."}
    dump(target / "verification.json", report)
    assert report["all_checks_passed"]
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
