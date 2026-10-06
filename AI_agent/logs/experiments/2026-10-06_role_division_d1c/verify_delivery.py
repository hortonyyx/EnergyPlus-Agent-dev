"""Offline catalog/byte evidence and explicit D1c registration, using scoped temp paths."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TEMP = ROOT / "AI_agent/archive/local_backup/d1c"
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import ep_no_billed_gate  # noqa: E402,F401
from src.agent_runtime.agent_registry import register_agent_version  # noqa: E402
from src.agent_runtime.mcp_tools import McpToolClient  # noqa: E402
from src.agent.runtime_roles.guidance import guidance_catalog  # noqa: E402

VERSION = "t1-20261006-d1c.1"
BASELINE = "814cf268"
REGISTRY = ROOT / "src/agent_runtime/agent_versions.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


async def catalogs():
    result = {}
    for mode in ("coordinator", "readonly", "coordinator_mesh", "readonly_mesh"):
        run = TEMP / "catalogs" / mode
        run.mkdir(parents=True, exist_ok=True)
        manifest = {"images": {}, "scope": "D1c offline catalog verification"}
        if mode.endswith("_mesh"):
            manifest["mesh_input"] = {"sha256": "0" * 64, "frozen_path": "assets/placeholder.glb"}
        write(run / "inputs.json", manifest)
        args = [str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)]
        if mode.startswith("readonly"):
            args.append("--readonly")
        async with McpToolClient(command=sys.executable, args=args, cwd=ROOT, run_directory=run) as client:
            result[mode] = hashlib.sha256(canonical(await client.list_tools())).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", action="store_true", help="write the final registry; otherwise a disposable development registry")
    args = parser.parse_args()
    TEMP.mkdir(parents=True, exist_ok=True)
    old = json.loads(subprocess.check_output(["git", "show", f"{BASELINE}:src/agent_runtime/agent_versions.json"], cwd=ROOT))
    current = old["versions"][old["current_version"]]
    # The only model-facing files allowed to change are role-only files.
    unchanged = {}
    for relative, metadata in current["files"].items():
        if relative.startswith("src/agent/runtime_roles/"):
            continue
        data = (ROOT / relative).read_bytes()
        assert data == subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT), relative
        unchanged[relative] = hashlib.sha256(data).hexdigest()
    guide = guidance_catalog()
    assert guide["single_model"]["sha256"] == "5ac8e4c4c67c4cb9556ab5bba382602f564dd1954290f147e701ea758e116b42"
    assert guide["roles"]["coordinator"]["sha256"] == "aa64908af9d36aa8da10afa60be72e8b28459e973c6f62a7c2cd3bc9e472a52e"
    assert guide["roles"]["elevation_reader"]["sha256"] == "62a73f1a30c819c683e26611748256cf3b0c1c662356c3b5547befc7fc977767"
    prior_evidence = HERE / "version_and_parity.json"
    prior = json.loads(prior_evidence.read_bytes()) if prior_evidence.is_file() else {}
    reuse = prior.get("single_model_file_sha256") == unchanged
    actual = prior["tool_catalog_sha256"] if reuse else asyncio.run(catalogs())
    assert actual == current["tool_catalog_sha256"]
    registry = REGISTRY if args.register else TEMP / "agent_versions.json"
    if not args.register:
        write(registry, old)
    record = register_agent_version(ROOT, VERSION, registry_path=registry, catalog_hashes=actual,
                                    additional_files={"src/agent/runtime_roles/plan_format.py": "tool"})
    new = json.loads(registry.read_bytes())
    assert all(new["versions"][key] == value for key, value in old["versions"].items())
    result = {"model_service_requests": 0, "baseline": BASELINE, "version": VERSION,
              "registered_final": args.register, "registered_files": len(record["files"]),
              "old_versions_preserved": len(old["versions"]), "tool_catalog_sha256": actual,
              "catalog_evidence": "reused live probes of byte-identical files" if reuse else "four real local MCP probes",
              "single_model_file_sha256": unchanged, "guidance": guide,
              "plan_reader_characters_before": 8015,
              "registry": registry.relative_to(ROOT).as_posix()}
    write(HERE / "version_and_parity.json", result)
    print(json.dumps({key: result[key] for key in ("version", "registered_final", "registered_files", "old_versions_preserved")}))
    print("plan_reader_characters:", guide["roles"]["plan_reader"]["character_count"])


if __name__ == "__main__":
    main()
