"""Offline preflight for the six D1b comparison configurations; never launch."""
import json
from pathlib import Path

from src.agent.runtime_configuration import load_configuration
from src.agent_runtime.agent_registry import agent_version_record


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def check():
    version = agent_version_record(ROOT)["version_id"]
    rows = []
    for path in sorted((HERE / "configs").glob("*.json")):
        configuration = load_configuration(path)
        if configuration["agent_version"] != version:
            raise ValueError(f"{path.name} expects {configuration['agent_version']}, registry is {version}")
        for case in configuration["cases"]:
            if case["max_candidates"] != 24:
                raise ValueError("D1b comparison candidate limit must remain 24")
        rows.append({"configuration": path.name, "status": "ready", "agent_version": version})
    return {"configurations": rows, "model_or_service_calls": 0, "launch_authorized": False,
            "version_note": "Run this check before launch. Runtime verifies the current sealed Agent registry."}


if __name__ == "__main__":
    result = check()
    (HERE / "configuration_verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))
