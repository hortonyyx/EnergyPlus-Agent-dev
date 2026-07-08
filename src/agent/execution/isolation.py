"""Clean-room workspace support for isolated 0_reading reruns."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from src.agent.execution.manifest import (
    MANIFEST_NAME,
    RunManifest,
    StageRecord,
    hash_file,
    hash_text,
)
from src.agent.execution.run_meta import run_meta_path
from src.validator.checks.schema import CheckLayer, CheckReport

ISOLATION_SCHEMA_VERSION = "1"
STAGE = "0_reading"
HARD_BLOCK_FILENAMES = {
    "gt" + ".json",
    "judge.json",
    "judge_rubric.md",
}
HARD_BLOCK_PARTS = {
    "attempts",
    "gt",
}
SEMANTIC_WARNING_TOKENS = (
    "judge",
    "verdict",
    "grade",
    "score",
    "attempt",
)


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    source_path: str
    category: str
    sha256: str


@dataclass
class WorkspaceManifest:
    staging_root: Path
    case_dir: Path
    run_dir: Path | None
    files: list[ManifestEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def manifest_path(self) -> Path:
        return self.staging_root / "MANIFEST.json"

    @property
    def settings_path(self) -> Path:
        return self.staging_root / "isolation_settings.json"

    def to_json_obj(self) -> dict:
        return {
            "schema_version": ISOLATION_SCHEMA_VERSION,
            "staging_root": str(self.staging_root),
            "case_dir": _repo_relative(self.case_dir),
            "run_dir": _repo_relative(self.run_dir) if self.run_dir else None,
            "files": [entry.__dict__ for entry in sorted(self.files, key=lambda item: item.path)],
            "warnings": sorted(set(self.warnings)),
        }

    def save(self) -> Path:
        self.manifest_path.write_text(
            json.dumps(self.to_json_obj(), indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        return self.manifest_path


def build_isolation_workspace(
    case_dir: Path,
    run_dir: Path | None = None,
    staging_root: Path | None = None,
) -> WorkspaceManifest:
    """Build a clean-room staging tree for an isolated 0_reading executor."""
    case_dir = Path(case_dir).resolve()
    run_dir = Path(run_dir).resolve() if run_dir else None
    if staging_root is None:
        Path("/tmp/ep_isolation").mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix=f"{case_dir.name}_", dir="/tmp/ep_isolation"))
    else:
        staging_root = Path(staging_root).resolve()
        staging_root.mkdir(parents=True, exist_ok=True)
    _require_outside_repo(staging_root)

    manifest = WorkspaceManifest(staging_root=staging_root, case_dir=case_dir, run_dir=run_dir)
    (staging_root / "out").mkdir(parents=True, exist_ok=True)
    (staging_root / "tools").mkdir(parents=True, exist_ok=True)

    _copy_case_data(case_dir, staging_root, manifest)
    _copy_reading_skill(staging_root, manifest)
    _copy_cv_toolbox(staging_root, manifest)
    _copy_prescan(run_dir, staging_root, manifest)
    _write_kickoff(case_dir, staging_root, manifest)
    _write_guard_and_wrappers(staging_root, manifest)
    _write_settings(staging_root, manifest)
    manifest.save()
    _assert_manifest_clean(manifest)
    return manifest


def check_feedback_text(text: str) -> None:
    lowered = text.lower()
    for token in (
        "gt" + ".json",
        "test_baseline",
        "case_tests",
        "/workspaces/energyplus-agent-dev",
        "attempts/",
        "judge.json",
        "judge_rubric.md",
        "verdict",
        "grade",
    ):
        if token in lowered:
            raise ValueError(f"feedback contains forbidden token: {token}")


def write_feedback(staging_root: Path, text: str, *, name: str = "feedback.md") -> Path:
    check_feedback_text(text)
    staging_root = Path(staging_root).resolve()
    path = staging_root / name
    if path.name != name:
        raise ValueError(f"feedback name must be a filename: {name!r}")
    path.write_text(text, encoding="utf-8")
    return path


def merge_isolated_output(
    staging_root: Path,
    run_dir: Path,
    *,
    output_path: Path | None = None,
    accept: bool = True,
) -> Path:
    """Merge isolated output into ``<run>/0_reading/attempts`` with provenance."""
    staging_root = Path(staging_root).resolve()
    run_dir = Path(run_dir).resolve()
    output_path = Path(output_path) if output_path else staging_root / "out" / "output.json"
    if not output_path.is_absolute():
        output_path = staging_root / output_path
    output_path = output_path.resolve(strict=True)
    _require_under(output_path, staging_root)

    with _merge_lock(run_dir):
        stage_dir = run_dir / STAGE
        attempt_dir = _new_attempt_dir_retry(stage_dir)
        out_text = output_path.read_text(encoding="utf-8")
        (attempt_dir / "output.json").write_text(out_text, encoding="utf-8")
        output_hash = hash_text(out_text)

        provenance = _build_provenance(staging_root, output_hash)
        prov_path = attempt_dir / "isolation_provenance.json"
        prov_path.write_text(
            json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        provenance_hash = hash_file(prov_path)

        report = CheckReport(stage=STAGE)
        report.add_pass(
            "reading.isolation_provenance_bound",
            CheckLayer.INVARIANT,
            evidence={"isolation_provenance_hash": provenance_hash},
        )
        report.attempt_hash = output_hash
        report.artifact_hash = output_hash
        (attempt_dir / "checks.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        _archive_isolation_artifacts(staging_root, attempt_dir)
        if accept:
            manifest = RunManifest.load(run_dir)
            manifest.accept(
                StageRecord(
                    stage=STAGE,
                    accepted_attempt=int(attempt_dir.name),
                    output_hash=output_hash,
                    input_hashes={
                        "isolation_provenance": provenance_hash,
                        "isolation_manifest": provenance.get("manifest_sha256", ""),
                        "isolation_settings": provenance.get("settings_sha256", ""),
                        "isolation_guard": provenance.get("guard_sha256", ""),
                        "isolation_access_log": provenance.get("access_log_sha256", ""),
                    },
                    capability="manual",
                    check_passed=True,
                )
            )
            _atomic_save_manifest(manifest, run_dir)
        return attempt_dir


def spawn_command(
    staging_root: Path,
    *,
    model: str | None = None,
    execute: bool = False,
) -> list[str]:
    staging_root = Path(staging_root).resolve()
    prompt = (staging_root / "kickoff_prompt.md").read_text(encoding="utf-8")
    cmd = ["claude", "-p", prompt, "--settings", str(staging_root / "isolation_settings.json")]
    if model:
        cmd.extend(["--model", model])
    if execute:
        subprocess.run(cmd, cwd=staging_root, env=clean_spawn_env(staging_root), check=True)
    return cmd


def clean_spawn_env(staging_root: Path) -> dict[str, str]:
    keep = {"PATH", "HOME", "LANG", "LC_ALL", "ANTHROPIC_API_KEY"}
    env = {key: value for key, value in os.environ.items() if key in keep}
    env["PYTHONPATH"] = str(Path(staging_root).resolve())
    return env


def _copy_case_data(case_dir: Path, staging_root: Path, manifest: WorkspaceManifest) -> None:
    src = case_dir / "case_data"
    if not src.exists():
        src = case_dir
    dest = staging_root / "case_data"
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.iterdir()):
        if path.is_file() and (path.suffix.lower() == ".png" or path.name == "testdata_prompt.json"):
            _copy_file(path, dest / path.name, "case_data", manifest)


def _copy_reading_skill(staging_root: Path, manifest: WorkspaceManifest) -> None:
    skill_root = _repo_root() / "skills" / "intake_pipeline" / "0_reading"
    dest_root = staging_root / "skills" / "intake_pipeline" / "0_reading"
    for path in sorted(skill_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "judge_rubric.md":
            continue
        _assert_source_allowed(path)
        rel = path.relative_to(skill_root)
        _copy_file(path, dest_root / rel, "skill", manifest)


def _copy_cv_toolbox(staging_root: Path, manifest: WorkspaceManifest) -> None:
    src_root = _repo_root() / "src" / "agent" / "reading" / "cv_toolbox"
    dest_root = staging_root / "src" / "agent" / "reading" / "cv_toolbox"
    for path in sorted(src_root.rglob("*")):
        if path.is_file():
            _copy_file(path, dest_root / path.relative_to(src_root), "cv_toolbox", manifest)
    for pkg in [
        staging_root / "src" / "__init__.py",
        staging_root / "src" / "agent" / "__init__.py",
        staging_root / "src" / "agent" / "reading" / "__init__.py",
    ]:
        _write_generated(pkg, "", "cv_toolbox", manifest)
    cv_probe_src = (_repo_root() / "scripts" / "tool_scripts" / "cv_probe.py").read_text(encoding="utf-8")
    cv_probe_src = cv_probe_src.replace("Path(__file__).resolve().parents[2]", "Path(__file__).resolve().parents[1]")
    _write_generated(staging_root / "tools" / "cv_probe.py", cv_probe_src, "tool", manifest)


def _copy_prescan(run_dir: Path | None, staging_root: Path, manifest: WorkspaceManifest) -> None:
    if run_dir is None:
        return
    src = run_dir / "0_reading" / "cv_evidence"
    if not src.exists():
        return
    dest_root = staging_root / "prescan"
    for path in sorted(src.glob("*/prescan/**/*")):
        if path.is_file():
            _assert_source_allowed(path)
            _copy_file(path, dest_root / path.relative_to(src), "prescan", manifest)


def _write_kickoff(case_dir: Path, staging_root: Path, manifest: WorkspaceManifest) -> None:
    text = (
        "Read skills/intake_pipeline/0_reading/session_kickoff.md and follow it "
        f"for case {case_dir.name}.\n"
        "The drawings are at case_data/. Write all outputs under out/. "
        "Use tools/run_cv_probe.py only through request JSON files inside this workspace. "
        "Do the pilot first, then stop and wait for review feedback if provided.\n"
    )
    _write_generated(staging_root / "kickoff_prompt.md", text, "kickoff", manifest)


def _write_guard_and_wrappers(staging_root: Path, manifest: WorkspaceManifest) -> None:
    for name, dest in [
        ("guard.py", staging_root / "guard.py"),
        ("run_cv_probe.py", staging_root / "tools" / "run_cv_probe.py"),
    ]:
        text = resources.files("src.agent.execution.isolation_templates").joinpath(name).read_text(encoding="utf-8")
        _write_generated(dest, text, "tool", manifest)
        dest.chmod(0o755)


def _write_settings(staging_root: Path, manifest: WorkspaceManifest) -> None:
    settings = {
        "permissions": {
            "defaultMode": "default",
            "allow": [
                f"Read({_claude_abs(staging_root)}/**)",
                f"Write({_claude_abs(staging_root / 'out')}/**)",
                f"Edit({_claude_abs(staging_root / 'out')}/**)",
                "Bash",
            ],
            "deny": [
                f"Read({_claude_abs(_repo_root())}/**)",
                "Read(//root/**)",
                "Read(//home/**)",
                "WebFetch",
                "WebSearch",
                "Agent",
                "Task",
                "mcp__*",
            ],
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{sys.executable} {staging_root / 'guard.py'}",
                        }
                    ],
                }
            ]
        },
    }
    _write_generated(
        staging_root / "isolation_settings.json",
        json.dumps(settings, indent=2, sort_keys=True),
        "settings",
        manifest,
    )


def _assert_manifest_clean(manifest: WorkspaceManifest) -> None:
    for entry in manifest.files:
        _assert_rel_allowed(Path(entry.source_path))


def _assert_source_allowed(path: Path) -> None:
    rel = Path(_repo_relative(path))
    _assert_rel_allowed(rel)


def _assert_rel_allowed(rel: Path) -> None:
    parts = set(rel.parts)
    name = rel.name
    if name in HARD_BLOCK_FILENAMES:
        raise ValueError(f"forbidden source file: {rel}")
    if "test_baseline" in parts and "gt" in parts:
        raise ValueError(f"forbidden gt source path: {rel}")
    if any(part.startswith("run_") for part in rel.parts[:-1]):
        raise ValueError(f"forbidden run source path: {rel}")
    if parts & HARD_BLOCK_PARTS:
        raise ValueError(f"forbidden source path component: {rel}")
    if name.startswith("verdict") or name.startswith("grade") or name.endswith("_score.json"):
        raise ValueError(f"forbidden generated judgment artifact: {rel}")


def _semantic_warnings(path: Path) -> list[str]:
    text = str(path).lower()
    return [f"semantic token present in allowed source path: {token}:{path}" for token in SEMANTIC_WARNING_TOKENS if token in text]


def _copy_file(src: Path, dest: Path, category: str, manifest: WorkspaceManifest) -> None:
    _assert_source_allowed(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    _add_manifest_entry(dest, src, category, manifest)


def _write_generated(dest: Path, text: str, category: str, manifest: WorkspaceManifest) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    _add_manifest_entry(dest, None, category, manifest)


def _add_manifest_entry(dest: Path, src: Path | None, category: str, manifest: WorkspaceManifest) -> None:
    rel_dest = dest.relative_to(manifest.staging_root).as_posix()
    source = _repo_relative(src) if src else f"<generated>/{rel_dest}"
    manifest.warnings.extend(_semantic_warnings(Path(source)))
    manifest.files.append(
        ManifestEntry(
            path=rel_dest,
            source_path=source,
            category=category,
            sha256=hash_file(dest),
        )
    )


def _build_provenance(staging_root: Path, output_hash: str) -> dict:
    manifest_path = staging_root / "MANIFEST.json"
    settings_path = staging_root / "isolation_settings.json"
    guard_path = staging_root / "guard.py"
    access_log_path = staging_root / "access_log.jsonl"
    denied = 0
    entries = 0
    if access_log_path.exists():
        for line in access_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries += 1
            if json.loads(line).get("decision") == "deny":
                denied += 1
    return {
        "schema_version": ISOLATION_SCHEMA_VERSION,
        "staging_root": str(staging_root),
        "output_hash": output_hash,
        "manifest_sha256": hash_file(manifest_path) if manifest_path.exists() else "",
        "settings_sha256": hash_file(settings_path) if settings_path.exists() else "",
        "guard_sha256": hash_file(guard_path) if guard_path.exists() else "",
        "access_log_sha256": hash_file(access_log_path) if access_log_path.exists() else "",
        "access_log_entries": entries,
        "access_log_denied": denied,
    }


def _archive_isolation_artifacts(staging_root: Path, attempt_dir: Path) -> None:
    archive = attempt_dir / "isolation_archive"
    archive.mkdir(parents=True, exist_ok=True)
    for name in ["MANIFEST.json", "isolation_settings.json", "guard.py", "access_log.jsonl"]:
        src = staging_root / name
        if src.exists():
            shutil.copy2(src, archive / name)


def _new_attempt_dir_retry(stage_dir: Path, retries: int = 5) -> Path:
    root = stage_dir / "attempts"
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(retries):
        used = [int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()]
        idx = (max(used) + 1) if used else 1
        path = root / f"{idx:03d}"
        try:
            path.mkdir(parents=True, exist_ok=False)
            return path
        except FileExistsError:
            time.sleep(0.01)
    raise FileExistsError(f"could not allocate attempt dir under {root}")


@contextmanager
def _merge_lock(run_dir: Path):
    lock_path = run_dir / ".isolation_merge.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _atomic_save_manifest(manifest: RunManifest, run_dir: Path) -> Path:
    path = run_meta_path(run_dir, MANIFEST_NAME, for_write=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{MANIFEST_NAME}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(manifest.model_dump_json(indent=2))
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return path


def _require_under(path: Path, root: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"path escapes staging: {path}") from exc


def _require_outside_repo(path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(_repo_root())
    except ValueError:
        return
    raise ValueError(f"staging root must be outside repo: {path}")


def _claude_abs(path: Path) -> str:
    return "/" + Path(path).resolve().as_posix()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _repo_relative(path: Path | None) -> str:
    if path is None:
        return ""
    path = Path(path).resolve()
    try:
        return path.relative_to(_repo_root()).as_posix()
    except ValueError:
        return path.as_posix()
