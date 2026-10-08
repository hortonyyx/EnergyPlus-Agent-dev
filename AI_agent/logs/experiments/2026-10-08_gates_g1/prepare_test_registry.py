"""Create an isolated hash snapshot for offline tests, never a release entry."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent_runtime.agent_registry import register_versions


if __name__ == "__main__":
    source = ROOT / "src/agent_runtime/agent_versions.json"
    original = source.read_bytes()
    folder = ROOT / "AI_agent/archive/local_backup/g1/test_registry"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "agent_versions.json"
    target.write_bytes(original)
    result = register_versions(ROOT, registry_path=target)
    assert source.read_bytes() == original, "formal registry changed"
    result.update(
        purpose="offline test hash snapshot only; the project manager owns release registration",
        test_snapshot=str(target),
        shared_registry_unchanged=True,
        shared_registry_sha256=hashlib.sha256(original).hexdigest(),
        model_requests=0,
    )
    evidence = Path(__file__).with_name("test_registry_evidence.json")
    evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))
