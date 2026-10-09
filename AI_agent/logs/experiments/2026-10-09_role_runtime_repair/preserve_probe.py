"""Pin, copy, and archive the completed sm25 F1 role probe evidence."""

from __future__ import annotations

import gzip
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import tarfile


REPO = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev")
EXPERIMENT = REPO / "AI_agent/logs/experiments/2026-10-09_role_runtime_repair"
WORKTREE = Path(r"D:\EnergyPlus-Agent-worktrees\role-kernel-20261009")
RUN = WORKTREE / "AI_agent/archive/local_backup/role_runtime_repair/sm25_f1"
RUN_PARENT = RUN.parent
DEST = REPO / "AI_agent/archive/local_backup/role_runtime_repair/sm25_f1"
STAGING = REPO / "AI_agent/archive/local_backup/role_runtime_repair/evidence_staging"
CHECKS = REPO / "AI_agent/archive/local_backup/role_runtime_repair_checks"
EVALUATION = REPO / "AI_agent/archive/local_backup/role_runtime_repair/f1_evaluation"
EXPECTED_COMMIT = "30085ccefdd50ee742ecea2fecf65941ad70f941"
EXPECTED_RUNTIME = "runtime-v2-20261009"
EXPECTED_DOMAIN = "domain-v56-20261009"

spec = importlib.util.spec_from_file_location(
    "v53_preserve", EXPERIMENT.parent / "2026-10-08_sm25_domain_v53/preserve_run.py"
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load the existing preservation helpers")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    base.require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def jbytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def configure_helpers() -> None:
    base.EXPECTED_COMMIT = EXPECTED_COMMIT
    base.REPOSITORY = REPO
    base.EXPERIMENT = EXPERIMENT
    base.WORKTREE = WORKTREE
    base.SOURCE = RUN
    base.DESTINATION = DEST
    base.STAGING = STAGING
    base.ARCHIVE_NAME = "sm25_f1_run.tar.gz"
    base.ARCHIVE_PREFIX = PurePosixPath(
        "AI_agent/archive/local_backup/role_runtime_repair/sm25_f1"
    )


def terminal_state() -> dict:
    base.require(base.read_detached_head() == EXPECTED_COMMIT, "detached HEAD check failed")
    exit_row = load(RUN_PARENT / "probe_process_exit.json")
    result = load(RUN / "probe_result.json")
    manifest = load(RUN / "probe_manifest.json")
    base.require(exit_row.get("exit_code") == 0, "probe process did not exit zero")
    base.require(result.get("probe_status") == "passed", "probe did not reach passed terminal state")
    checks = result.get("checks")
    base.require(isinstance(checks, dict) and checks and all(v is True for v in checks.values()),
                 "one or more probe checks did not pass")
    base.require(manifest.get("git_commit") == EXPECTED_COMMIT, "probe commit differs")
    versions = manifest.get("versions", {})
    for name, expected in (("runtime", EXPECTED_RUNTIME), ("domain", EXPECTED_DOMAIN)):
        version = versions.get(name, {})
        base.require(version.get("version_id") == expected, f"{name} version differs")
        files = version.get("files")
        base.require(isinstance(files, dict) and files, f"{name} frozen file list is missing")
        for relative, row in files.items():
            path = base.path_from_relative(WORKTREE, relative, must_exist=True)
            actual, _ = base.hash_file(path)
            base.require(actual == row.get("sha256"), f"frozen source changed: {relative}")
    original = RUN / "original_input" / manifest["task"]["image"]
    original_hash, _ = base.hash_file(original)
    base.require(original_hash == manifest.get("original_sha256"), "original image changed")
    runner_hash, _ = base.hash_file(EXPERIMENT / "run_plan_probe.py")
    base.require(runner_hash == manifest.get("runner_sha256"), "probe runner changed")
    evaluation = load(EVALUATION / "summary.json")
    acceptance = evaluation.get("acceptance", {})
    base.require(acceptance.get("status") == "fail"
                 and acceptance.get("assigned_role_score") == "severe",
                 "evaluation is not the recorded severe quality failure")
    return {"exit": exit_row, "probe_status": result["probe_status"],
            "checks": checks, "git_commit": EXPECTED_COMMIT,
            "runtime": EXPECTED_RUNTIME, "domain": EXPECTED_DOMAIN,
            "original_sha256": original_hash, "evaluation": acceptance}


def supplemental_files() -> list[tuple[str, Path]]:
    rows = [
        ("process/probe_process.log", RUN_PARENT / "probe_process.log"),
        ("process/probe_process_exit.json", RUN_PARENT / "probe_process_exit.json"),
        ("offline/manifest.json", CHECKS / "manifest.json"),
        ("offline/exit.json", CHECKS / "exit.json"),
        ("offline/junit.xml", CHECKS / "junit.xml"),
        ("offline/pytest.log", CHECKS / "pytest.log"),
        ("offline/focused_rework/junit.xml", CHECKS / "focused_rework/junit.xml"),
        ("offline/focused_rework/pytest.log", CHECKS / "focused_rework/pytest.log"),
    ]
    for name in ("offline_initial_summary.json", "offline_final_summary.json",
                 "probe_preflight.json", "process_samples.jsonl"):
        rows.append((f"experiment/{name}", EXPERIMENT / name))
    for item in base.scan_tree(EVALUATION):
        rows.append((f"evaluation/f1_evaluation/{item['path']}", EVALUATION / item["path"]))
    return rows


def scan_supplemental(files: list[tuple[str, Path]]) -> list[dict]:
    rows = []
    for archive_path, source in files:
        base.safe_relative_path(archive_path)
        digest, size = base.hash_file(source)
        rows.append({"path": archive_path, "bytes": size, "sha256": digest,
                     "source": str(source)})
    rows.sort(key=lambda row: row["path"])
    base.assert_manifest_rows([{k: row[k] for k in ("path", "bytes", "sha256")}
                               for row in rows], "supplemental")
    return rows


def create_supplemental(path: Path, rows: list[dict]) -> str:
    if path.exists():
        base.checked_stat(path, kind="file")
        return "reused"
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for row in rows:
                    info = tarfile.TarInfo(row["path"])
                    info.size, info.mode, info.mtime = row["bytes"], 0o644, 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with Path(row["source"]).open("rb") as stream:
                        archive.addfile(info, stream)
        raw.flush()
        os.fsync(raw.fileno())
    return "created"


def main() -> None:
    configure_helpers()
    terminal = terminal_state()
    STAGING.mkdir(parents=True, exist_ok=True)
    source1 = base.scan_tree(RUN)
    copy_counts = base.copy_tree_once(source1)
    copy1, source2, copy2 = base.scan_tree(DEST), base.scan_tree(RUN), base.scan_tree(DEST)
    base.require_same_rows(source1, copy1, "source pass 1 vs copy pass 1")
    base.require_same_rows(source1, source2, "source pass 1 vs source pass 2")
    base.require_same_rows(copy1, copy2, "copy pass 1 vs copy pass 2")
    run_manifest = base.archive_manifest(copy2)
    run_archive = STAGING / base.ARCHIVE_NAME
    base.create_archive_once(run_archive, copy2)
    run_record = base.validate_archive(run_archive, run_manifest)
    parts = base.split_archive_if_needed(run_archive, run_record)

    supplemental1 = scan_supplemental(supplemental_files())
    supplemental_archive = STAGING / "sm25_f1_supplemental.tar.gz"
    create_supplemental(supplemental_archive, supplemental1)
    supplemental2 = scan_supplemental(supplemental_files())
    base.require(supplemental1 == supplemental2, "supplemental inputs changed while archiving")
    supplemental_manifest = {"schema_version": "sm25_f1_supplemental_v1",
                             "files": [{k: row[k] for k in ("path", "bytes", "sha256")}
                                       for row in supplemental2]}
    supplemental_record = base.validate_archive(supplemental_archive, supplemental_manifest)
    final_summary = {"schema_version": "sm25_f1_preservation_v1", "terminal": terminal,
                     "source": str(RUN), "destination": str(DEST),
                     "copy_counts": copy_counts, "two_passes_identical": True,
                     "run_archive": run_record, "run_parts": parts,
                     "supplemental_archive": supplemental_record,
                     "probe_execution_included": False}
    outputs = {
        "run_source_manifest_pass1.json": base.manifest_document(RUN, 1, source1),
        "run_source_manifest_pass2.json": base.manifest_document(RUN, 2, source2),
        "run_copy_manifest_pass1.json": base.manifest_document(DEST, 1, copy1),
        "run_copy_manifest_pass2.json": base.manifest_document(DEST, 2, copy2),
        "sm25_f1_run_manifest.json": run_manifest,
        "sm25_f1_supplemental_manifest.json": supplemental_manifest,
        "archive_summary.json": final_summary,
    }
    for name, value in outputs.items():
        base.write_once(STAGING / name, jbytes(value))
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
