"""Read-only no-follow inventory and integrity checks after the authorized cleanup."""
import hashlib
import json
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev")
REPORT = ROOT / "AI_agent/logs/experiments/2026-10-11_test_cache_cleanup"
before = json.loads((REPORT / "before.json").read_text(encoding="utf-8-sig"))


def inventory(path):
    totals = {"bytes": 0, "files": 0, "reparse_points_skipped": 0, "errors": []}
    if not os.path.lexists(path):
        return totals
    pending = [str(path)]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir("\\\\?\\" + directory) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                            totals["reparse_points_skipped"] += 1
                        elif stat.S_ISDIR(info.st_mode):
                            pending.append(entry.path.removeprefix("\\\\?\\"))
                        elif stat.S_ISREG(info.st_mode):
                            totals["bytes"] += info.st_size
                            totals["files"] += 1
                    except OSError as error:
                        totals["errors"].append({"path": entry.path, "error": str(error)})
        except OSError as error:
            totals["errors"].append({"path": directory, "error": str(error)})
    return totals


candidates = [
    {"name": entry["name"], "exists": os.path.lexists(entry["path"]), **inventory(entry["path"])}
    for entry in before["candidates"]
]
hashes = []
for relative, expected in before["preserved_sha256"].items():
    path = ROOT / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    hashes.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual, "matches": actual == expected})
main_inventory = inventory(ROOT)
free = {letter: shutil.disk_usage(letter + ":\\").free for letter in ("C", "D")}
after = {
    "checked_at": datetime.now().astimezone().isoformat(),
    "measurement": "Regular file logical lengths, no reparse traversal; not NTFS allocated bytes. Free-space change may include other processes.",
    "candidates": candidates,
    "removed_directories": sum(not entry["exists"] for entry in candidates),
    "removed_logical_bytes": before["total_bytes"] - sum(entry["bytes"] for entry in candidates),
    "remaining_candidate_bytes": sum(entry["bytes"] for entry in candidates),
    "preserved_sha256": hashes,
    "all_preserved_hashes_match": all(entry["matches"] for entry in hashes),
    "main_repository": main_inventory,
    "drive_free_bytes": free,
    "drive_free_change_bytes": {letter: free[letter] - before["drive_free_bytes"][letter] for letter in free},
}
(REPORT / "after.json").write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in after.items() if key not in {"candidates", "preserved_sha256"}}, indent=2, ensure_ascii=False))
if not after["all_preserved_hashes_match"] or main_inventory["errors"] or any(entry["exists"] or entry["errors"] for entry in candidates):
    raise SystemExit(1)
