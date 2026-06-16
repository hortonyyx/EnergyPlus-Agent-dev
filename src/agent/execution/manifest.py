"""Run manifest + append-only attempt layout (M0 audit foundation).

Two guarantees this module exists to provide (施工方案 M0 / contracts §3.1):

1. **Append-only attempts.** Every time a stage produces a draw we file it under
   ``<case>/<stage>/attempts/NNN/`` — a fresh, zero-padded, monotonically
   increasing directory. A rejected draw is NEVER overwritten; it stays on disk
   for audit / hard-sample mining. The "accepted" attempt is recorded by pointer
   in ``run_manifest.json``, not by clobbering files.

2. **Content addressing.** Artifacts and attempts are hashed (canonical-JSON or
   raw-bytes sha256) so a manifest entry binds an accepted attempt to the exact
   bytes it accepted, and so the geometry-approval digest (approval.py) and the
   resume cache (invalidation.py) can detect drift.

The manifest is deliberately small and JSON-serializable: it indexes stages →
accepted attempt + input artifact hashes + stage/check version, nothing more.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

MANIFEST_NAME = "run_manifest.json"
ATTEMPTS_DIRNAME = "attempts"


# --------------------------------------------------------------------------- #
# hashing
# --------------------------------------------------------------------------- #
def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))


def hash_obj(obj) -> str:
    """Hash any JSON-able object by its canonical (sorted-key, compact) form, so
    semantically-equal objects with different key order hash identically."""
    return hash_text(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def hash_file(path: Path) -> str:
    return hash_bytes(Path(path).read_bytes())


def combined_digest(parts: list[str]) -> str:
    """Order-independent digest of a set of hashes (used for checkpoint digests)."""
    return hash_text("\n".join(sorted(parts)))


# --------------------------------------------------------------------------- #
# append-only attempts
# --------------------------------------------------------------------------- #
def _attempts_root(stage_dir: Path) -> Path:
    return stage_dir / ATTEMPTS_DIRNAME


def next_attempt_index(stage_dir: Path) -> int:
    """Smallest unused 1-based attempt index under ``<stage>/attempts/``."""
    root = _attempts_root(stage_dir)
    if not root.exists():
        return 1
    used = []
    for p in root.iterdir():
        if p.is_dir() and p.name.isdigit():
            used.append(int(p.name))
    return (max(used) + 1) if used else 1


def new_attempt_dir(stage_dir: Path) -> Path:
    """Create and return a fresh ``<stage>/attempts/NNN/`` directory.

    Never reuses or overwrites an existing index — the append-only guarantee.
    """
    idx = next_attempt_index(stage_dir)
    d = _attempts_root(stage_dir) / f"{idx:03d}"
    if d.exists():  # defensive: a race or manual tampering
        raise FileExistsError(f"attempt dir already exists: {d}")
    d.mkdir(parents=True, exist_ok=False)
    return d


def attempt_index_of(attempt_dir: Path) -> int:
    return int(Path(attempt_dir).name)


# --------------------------------------------------------------------------- #
# manifest model
# --------------------------------------------------------------------------- #
class StageRecord(BaseModel):
    """One stage's accepted-attempt pointer + provenance."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    accepted_attempt: int           # 1-based index under attempts/
    output_hash: str                # hash of the accepted output artifact
    input_hashes: dict[str, str] = Field(default_factory=dict)  # name -> hash
    stage_version: str = "1"
    check_version: str = "1"
    capability: str = "deterministic"
    check_passed: bool = True


class RunManifest(BaseModel):
    """Indexes each stage to its accepted attempt. Persisted as run_manifest.json
    at the case root. Append-only attempts live beside it under each stage dir."""

    model_config = ConfigDict(extra="forbid")

    case: str = ""
    manifest_version: str = "1"
    stages: dict[str, StageRecord] = Field(default_factory=dict)

    # ---- io ----
    @classmethod
    def load(cls, case_dir: Path) -> "RunManifest":
        p = Path(case_dir) / MANIFEST_NAME
        if not p.exists():
            return cls(case=Path(case_dir).name)
        return cls.model_validate_json(p.read_text(encoding="utf-8"))

    def save(self, case_dir: Path, *, filename: str = MANIFEST_NAME) -> Path:
        p = Path(case_dir) / filename
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return p

    # ---- mutation ----
    def accept(self, record: StageRecord) -> None:
        """Record (or replace the pointer to) a stage's accepted attempt. This
        only moves the pointer; it never touches prior attempt directories."""
        self.stages[record.stage] = record

    def accepted(self, stage: str) -> StageRecord | None:
        return self.stages.get(stage)
