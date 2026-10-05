"""A real disposable source tree for legacy clean-room tests.

Those tests require staging OUTSIDE their source repository, whereas the C3
validation keeps all temporary files INSIDE its owning worktree. A separate
source fixture and sibling staging satisfy both requirements. We copy the exact
files the builder consumes and substitute only its source-root dependency;
the production boundary check, manifest verification and mutations stay intact.
"""
import hashlib
from pathlib import Path
import shutil

import pytest

MODULES = {
    "test_automatic_reading", "test_cross_axis_exit", "test_e2e_break_r2_locks",
    "test_f51_single_frame", "test_f51_source_frame_roundtrip", "test_isolation",
    "test_substrate_fix_cleanroom", "test_substrate_fix_tools",
    "test_substrate_sweep_policy", "test_substrate_sweep_tools",
    "test_reading_ruler_r1_batchB",
}


@pytest.fixture(scope="session")
def isolation_source_copy(tmp_path_factory):
    from src.agent.execution import isolation
    original = isolation._repo_root()
    root = tmp_path_factory.mktemp("cleanroom-source")
    paths = [Path("src/agent/execution/isolation.py"),
             Path("src/agent/reading/cv_toolbox"),
             Path("skills/intake_pipeline/0_reading"),
             Path("case_tests/e2e_tests/sm21_anchor/case_data"),
             Path("scripts/tool_scripts/cv_probe.py"),
             Path(isolation.WORKED_EXAMPLE_SOURCE)]
    for relative in paths:
        source = original / relative
        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for file in files:
            if not file.is_file() or "__pycache__" in file.parts:
                continue
            target = root / file.relative_to(original)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
            assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(file.read_bytes()).digest()
    return root


@pytest.fixture(scope="module", autouse=True)
def separate_cleanroom_source(request, tmp_path_factory):
    if request.module.__name__.split(".")[-1] not in MODULES:
        yield
        return
    from src.agent.execution import isolation
    original = isolation._repo_root()
    if not tmp_path_factory.getbasetemp().is_relative_to(original):
        yield  # Standard outside-repository pytest storage needs no adaptation.
        return
    # Prove the real guard rejects the original in-repository location first.
    with pytest.raises(ValueError, match="outside repo"):
        isolation._require_outside_repo(tmp_path_factory.getbasetemp())
    source = request.getfixturevalue("isolation_source_copy")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(isolation, "_repo_root", lambda: source)
        if request.module.__name__.split(".")[-1] == "test_isolation":
            # Its manifest test also requires original-input paths to be
            # repository-relative. Keep that case inside the fixture source.
            patch.setattr(request.module, "CASE_DIR", source / "case_tests/e2e_tests/sm21_anchor")
        with pytest.raises(ValueError, match="outside repo"):
            isolation._require_outside_repo(source / "forbidden-staging")
        isolation._require_outside_repo(tmp_path_factory.getbasetemp())
        yield
