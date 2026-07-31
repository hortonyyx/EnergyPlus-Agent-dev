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
    RunManifestV2,
    StageRecordV2,
    ensure_run_manifest_v2,
    hash_file,
    hash_text,
    load_run_manifest,
    reading_attempt_allowed,
    save_run_manifest,
)
from src.agent.execution.view_manifest import (
    ViewManifest,
    build_view_manifest,
    derive_input_inventory,
    verify_view_manifest,
)
from src.validator.checks.schema import CheckLayer
from src.validator.checks.view_manifest import check_reading_stage

ISOLATION_SCHEMA_VERSION = "1"
STAGE = "0_reading"

# The worked-example reading-view JSON the kickoff tells the reader to read as a
# style/format anchor (session_kickoff.md §"First"). It is a *different* building
# (smalloffice_20) containing none of the target case's information, so staging it
# is not contamination — `_assert_source_allowed` passes for it (verified). The
# repo path is denied by the guard (DENY_TOKENS contains `case_tests`) and is not
# copied by default, so build must stage it at a non-denied path and rewrite the
# kickoff pointer to that staging path (F-2). Both sides must agree on this path.
WORKED_EXAMPLE_SOURCE = "case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json"
WORKED_EXAMPLE_STAGED = "reference/worked_example_plan.json"

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
    # §2 reader-visibility ledger: images that were classified `excluded_input`
    # by the view manifest and therefore deliberately NOT copied into staging
    # (not a warning — this is the expected, audited shape of a clean build).
    excluded_from_staging: list[dict] = field(default_factory=list)
    merge_eligible: bool = False

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
            "merge_eligible": self.merge_eligible,
            "files": [entry.__dict__ for entry in sorted(self.files, key=lambda item: item.path)],
            "excluded_from_staging": sorted(
                self.excluded_from_staging, key=lambda item: item["input_id"]
            ),
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
    """Build a clean-room staging tree for an isolated 0_reading executor.

    Two modes (§5.2):

    - **preview/unbound** (``run_dir=None``): no run to bind to yet. The build
      always produces ``merge_eligible: false`` — :func:`merge_isolated_output`
      refuses unconditionally for a workspace built this way, no matter what
      target run_dir is later supplied.
    - **formal** (``run_dir`` given): the caller must have already provisioned
      this run's view manifest (``provision_view_manifest`` / the
      ``provision`` CLI) — this function only *verifies* it and refuses to
      build otherwise (fail closed, never silently provisions here). On
      success it binds/creates the run's v2 identity (:func:`ensure_run_manifest_v2`)
      and records immutable provenance (run_id, case_id, view_manifest_sha256,
      case_metadata_sha256, per-image hashes) that :func:`merge_isolated_output`
      re-checks before ever accepting.

    In both modes, only ``required_view``-classified images are copied into
    ``case_data/`` — an image the view manifest classifies ``excluded_input``
    is never reader-visible (§2); a derived ``input_inventory.json`` projection
    (denominator-free: no negative-evidence/completeness content) tells the
    reader what to read and what to name its output.
    """
    case_dir = Path(case_dir).resolve()
    run_dir = Path(run_dir).resolve() if run_dir else None
    if staging_root is None:
        Path("/tmp/ep_isolation").mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix=f"{case_dir.name}_", dir="/tmp/ep_isolation"))
    else:
        staging_root = Path(staging_root).resolve()
        staging_root.mkdir(parents=True, exist_ok=True)
    _require_outside_repo(staging_root)

    view_manifest = build_view_manifest(case_dir)
    binding: dict = {"merge_eligible": False}

    if run_dir is not None:
        verification = verify_view_manifest(case_dir, run_dir)
        if not verification.ok:
            raise ValueError(
                "cannot build a formal (run-bound) isolation workspace: "
                f"{verification.reason} — provision this run's view manifest first "
                "(`provision_view_manifest` / the `provision` CLI)"
            )
        view_manifest = verification.on_disk  # the committed one is authoritative
        run_manifest_v2 = ensure_run_manifest_v2(
            run_dir, view_manifest_sha256=view_manifest.content_sha256
        )
        binding = {
            "merge_eligible": True,
            "run_id": run_manifest_v2.run_id,
            "case_id": view_manifest.case_id,
            "case_dir": _repo_relative(case_dir),
            "run_dir": _repo_relative(run_dir),
            "view_manifest_sha256": view_manifest.content_sha256,
            "case_metadata_sha256": view_manifest.case_metadata_sha256,
            "image_sha256": {e.input_id: e.image_sha256 for e in view_manifest.required_entries()},
        }

    manifest = WorkspaceManifest(
        staging_root=staging_root, case_dir=case_dir, run_dir=run_dir,
        merge_eligible=bool(binding["merge_eligible"]),
    )
    (staging_root / "out").mkdir(parents=True, exist_ok=True)
    (staging_root / "tools").mkdir(parents=True, exist_ok=True)

    _copy_case_data(case_dir, staging_root, manifest, view_manifest)
    _copy_reading_skill(staging_root, manifest)
    _copy_worked_example(staging_root, manifest)
    _copy_cv_toolbox(staging_root, manifest)
    _copy_prescan(run_dir, staging_root, manifest)
    _write_kickoff(case_dir, staging_root, manifest)
    _write_guard_and_wrappers(staging_root, manifest)
    _write_settings(staging_root, manifest)
    _write_input_inventory(staging_root, manifest, view_manifest)
    _write_binding(staging_root, manifest, binding)
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
    """Merge isolated output into ``<run>/0_reading/attempts`` with provenance.

    §5.2 "merge 同门": before ever touching the manifest, this (1) refuses a
    workspace that was not built ``merge_eligible`` (preview/unbound, or built
    for a different run_dir); (2) refuses a target run whose *current* identity
    (run_id / view_manifest_sha256 / case_metadata_sha256) no longer matches
    what was bound at build time — covers a tampered image, a directly-edited
    view manifest, a run manifest replaced/swapped, or a workspace built for
    run A merged into run B; (3) refuses a v1 (grandfathered) target run
    outright; (4) runs the identical coverage/schema checker the flat-flow
    reader uses against the aggregate payload — ``report.blocking()`` non-empty
    means ``accept=True`` is silently downgraded to a filed-but-not-accepted
    attempt (the caller's ``accept=True`` can never override a blocking gate①).
    """
    staging_root = Path(staging_root).resolve()
    run_dir = Path(run_dir).resolve()
    output_path = Path(output_path) if output_path else staging_root / "out" / "output.json"
    if not output_path.is_absolute():
        output_path = staging_root / output_path
    output_path = output_path.resolve(strict=True)
    _require_under(output_path, staging_root)

    binding = _read_binding(staging_root)
    if not binding.get("merge_eligible"):
        raise ValueError(
            "this staging workspace is not merge-eligible — it was built without a "
            "bound run_dir (preview/unbound mode never merges, §5.2)"
        )
    case_dir = _repo_root() / binding["case_dir"]
    bound_run_dir = _repo_root() / binding["run_dir"]
    if bound_run_dir.resolve() != run_dir.resolve():
        raise ValueError(
            f"this staging workspace was bound to {bound_run_dir}, not {run_dir} — a "
            "workspace built for one run cannot be merged into another (even the same "
            "case/images with only run_id differing)"
        )

    allowed, reason = reading_attempt_allowed(run_dir)
    if not allowed:
        raise ValueError(f"merge refused: {reason}")

    current_manifest = load_run_manifest(run_dir)
    if not isinstance(current_manifest, RunManifestV2) or current_manifest.run_id != binding["run_id"]:
        raise ValueError(
            "merge refused: the target run's identity has changed since this "
            "workspace was built (run_id mismatch, or the run manifest was replaced)"
        )

    verification = verify_view_manifest(case_dir, run_dir)
    if (
        not verification.ok
        or verification.on_disk.content_sha256 != binding["view_manifest_sha256"]
        or verification.on_disk.case_metadata_sha256 != binding["case_metadata_sha256"]
    ):
        raise ValueError(
            "merge refused: the view manifest has drifted since this workspace was "
            "built (case_data image(s) or the committed view manifest changed)"
        )

    out_text = output_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(out_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"aggregate output.json is not valid JSON: {exc}") from exc
    views = payload.get("views") if isinstance(payload, dict) else None
    if not isinstance(views, dict):
        raise ValueError(
            "aggregate output.json must be shaped {'views': {<expected_output_id>: "
            "<ReadingView JSON>, ...}}"
        )

    report = check_reading_stage(verification.on_disk, views)

    with _merge_lock(run_dir):
        stage_dir = run_dir / STAGE
        attempt_dir = _new_attempt_dir_retry(stage_dir)
        (attempt_dir / "output.json").write_text(out_text, encoding="utf-8")
        output_hash = hash_text(out_text)

        provenance = _build_provenance(staging_root, output_hash)
        provenance.update(
            {
                "run_id": binding["run_id"],
                "case_id": binding["case_id"],
                "view_manifest_sha256": binding["view_manifest_sha256"],
            }
        )
        prov_path = attempt_dir / "isolation_provenance.json"
        prov_path.write_text(
            json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        provenance_hash = hash_file(prov_path)
        report.add_pass(
            "reading.isolation_provenance_bound",
            CheckLayer.INVARIANT,
            evidence={"isolation_provenance_hash": provenance_hash},
        )

        report.attempt_hash = output_hash
        report.artifact_hash = output_hash
        checks_path = attempt_dir / "checks.json"
        checks_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        checks_hash = hash_file(checks_path)

        _archive_isolation_artifacts(staging_root, attempt_dir)

        blocking = report.blocking()
        do_accept = bool(accept) and not blocking  # accept=True can never override a block
        if do_accept:
            current_manifest.accept(
                StageRecordV2(
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
                    check_passed=not blocking,
                    artifact_contract="reading_isolated_v2",
                    artifact_hashes={
                        "output": output_hash,
                        "checks": checks_hash,
                        "isolation_provenance": provenance_hash,
                    },
                )
            )
            save_run_manifest(current_manifest, run_dir)
        return attempt_dir


def spawn_command(
    staging_root: Path,
    *,
    model: str | None = None,
    execute: bool = False,
    directive: str | Path | None = None,
) -> list[str]:
    staging_root = Path(staging_root).resolve()
    prompt = (staging_root / "kickoff_prompt.md").read_text(encoding="utf-8")
    if directive is not None:
        text = Path(directive).read_text(encoding="utf-8")
        # Same contamination bar as feedback: the directive is a prompt channel.
        check_feedback_text(text)
        (staging_root / "directive.md").write_text(text, encoding="utf-8")
        prompt += "\n## Per-run directive (binding for this run)\n" + text
    if (staging_root / "feedback.md").exists():
        prompt += (
            "\nIMPORTANT: A review of your previous output exists at feedback.md — "
            "read it FIRST and follow it exactly before doing anything else.\n"
        )
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


def _copy_case_data(
    case_dir: Path, staging_root: Path, manifest: WorkspaceManifest, view_manifest: ViewManifest
) -> None:
    """Copy only what the reader is entitled to see (§2 reader-visibility
    铁律): every ``required_view`` image + ``testdata_prompt.json``. An image
    the view manifest classifies ``excluded_input`` (derived working copy /
    non-drawing asset) is never copied — it is logged in
    ``excluded_from_staging`` instead, not silently dropped."""
    src = case_dir / "case_data"
    if not src.exists():
        src = case_dir
    dest = staging_root / "case_data"
    dest.mkdir(parents=True, exist_ok=True)
    excluded_by_basename = {
        e.source_image.rsplit("/", 1)[-1]: e for e in view_manifest.excluded_entries()
    }
    for path in sorted(src.iterdir()):
        if not path.is_file():
            continue
        if path.name == "testdata_prompt.json":
            _copy_file(path, dest / path.name, "case_data", manifest)
            continue
        if path.suffix.lower() != ".png":
            continue
        excluded = excluded_by_basename.get(path.name)
        if excluded is not None:
            manifest.excluded_from_staging.append(
                {
                    "input_id": excluded.input_id,
                    "source_image": excluded.source_image,
                    "excluded_reason": excluded.excluded_reason,
                }
            )
            continue
        _copy_file(path, dest / path.name, "case_data", manifest)


def _write_input_inventory(
    staging_root: Path, manifest: WorkspaceManifest, view_manifest: ViewManifest
) -> None:
    """§2 staging projection: reader-visible identity only (input_id, file,
    view_type, declared_direction_token, floor_ref, expected_output_id) — no
    denominator/negative-evidence content. Lives at staging ROOT (not under
    ``out/``), so the existing Write-allow list already makes it read-only to
    the reader without any additional guard logic."""
    payload = derive_input_inventory(view_manifest)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    _write_generated(staging_root / "input_inventory.json", text, "input_inventory", manifest)


def _write_binding(staging_root: Path, manifest: WorkspaceManifest, binding: dict) -> None:
    """Immutable staging-provenance binding (§5.2). Never copied from — and
    never visible to — anything but :func:`merge_isolated_output`'s own
    re-verification; lives at staging root so the reader cannot write it."""
    text = json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False)
    _write_generated(staging_root / "binding.json", text, "binding", manifest)


def _read_binding(staging_root: Path) -> dict:
    path = Path(staging_root) / "binding.json"
    if not path.exists():
        raise ValueError(
            f"no binding.json under {staging_root} — this staging workspace was not "
            "built by build_isolation_workspace (or predates the isolation run-binding wire)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


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
        if path.name == "session_kickoff.md":
            # F-2: the kickoff names the worked-example by its (denied) repo path.
            # Rewrite the pointer to the staged copy so the reader is never sent at
            # a wall-outside file the guard will refuse. Both sides agree on
            # WORKED_EXAMPLE_STAGED (the consistency lock stats this path in staging).
            _copy_skill_kickoff(path, dest_root / rel, manifest)
            continue
        _copy_file(path, dest_root / rel, "skill", manifest)


def _copy_skill_kickoff(src: Path, dest: Path, manifest: WorkspaceManifest) -> None:
    text = src.read_text(encoding="utf-8")
    if WORKED_EXAMPLE_SOURCE in text:
        text = text.replace(WORKED_EXAMPLE_SOURCE, WORKED_EXAMPLE_STAGED)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    _add_manifest_entry(dest, src, "skill", manifest)


def _copy_worked_example(staging_root: Path, manifest: WorkspaceManifest) -> None:
    """Stage the kickoff's worked-example reading-view JSON (F-2).

    Staged at a path that trips no DENY_TOKEN and registered in MANIFEST — the
    07-30 hand-staged copy was *not* in MANIFEST, so the merge provenance ledger
    missed it. Recording it here is this slice's primary value, not a side effect.
    """
    src = _repo_root() / WORKED_EXAMPLE_SOURCE
    dest = staging_root / WORKED_EXAMPLE_STAGED
    _copy_file(src, dest, "reference", manifest)


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
    # Layout parity with staging-direct generation (--out-dir <staging>/prescan):
    # prescan/cv_evidence/<stem>/prescan/... either way.
    dest_root = staging_root / "prescan" / "cv_evidence"
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
    if (staging_root / "prescan").exists():
        text += (
            "Deterministic prescan candidates are provided under "
            "prescan/cv_evidence/<image_stem>/prescan/ (candidates.json + "
            "combined_overlay.png); consume them per the cv_toolbox discipline.\n"
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


def _is_run_prescan_path(rel: Path) -> bool:
    """Only run-dir subtree readable by the builder: orchestrator-produced
    prescan candidates at run_*/0_reading/cv_evidence/<stem>/prescan/**."""
    parts = rel.parts
    for i, part in enumerate(parts[:-1]):
        if part.startswith("run_"):
            tail = parts[i + 1 :]
            return (
                len(tail) >= 5
                and tail[0] == "0_reading"
                and tail[1] == "cv_evidence"
                and tail[3] == "prescan"
            )
    return False


def _assert_rel_allowed(rel: Path) -> None:
    parts = set(rel.parts)
    name = rel.name
    if name in HARD_BLOCK_FILENAMES:
        raise ValueError(f"forbidden source file: {rel}")
    if "test_baseline" in parts and "gt" in parts:
        raise ValueError(f"forbidden gt source path: {rel}")
    if any(part.startswith("run_") for part in rel.parts[:-1]) and not _is_run_prescan_path(rel):
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
