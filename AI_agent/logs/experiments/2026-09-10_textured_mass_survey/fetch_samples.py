"""Reacquire the surveyed public assets; preserve existing files and check hashes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile

import requests

REPO = Path(__file__).resolve().parents[4]
ASSETS = REPO / "case_tests/textured_mass"


def fetch(record):
    target = (REPO / record["path"]).resolve()
    if not target.is_relative_to(ASSETS / "raw"):
        raise ValueError("Acquisition destination must be inside case raw/")
    expected = record["sha256"]
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Existing asset differs; preserved: {target}")
        return f"verified existing {target.relative_to(REPO)}"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with requests.get(record["url"], stream=True, timeout=(10, 35)) as response:
            response.raise_for_status()
            digest = hashlib.sha256()
            size = 0
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                temporary = Path(output.name)
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > record["bytes"]:
                        raise ValueError("Remote asset is larger than recorded")
                    digest.update(chunk)
                    output.write(chunk)
            if size != record["bytes"] or digest.hexdigest() != expected:
                raise ValueError(f"Remote asset changed: {record['url']}")
            temporary.rename(target)
        return f"downloaded {target.relative_to(REPO)}"
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    manifest = json.loads((ASSETS / "acquisition.json").read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(fetch, manifest["files"]):
            print(result, flush=True)
