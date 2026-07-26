"""Contract locks for the deterministic affected-test selector."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from scripts.tool_scripts import affected_tests as affected


def _path(*parts: str) -> str:
    return "/".join(parts)


def _result(*parts: str) -> affected.MappingResult:
    return affected.affected_tests([_path(*parts)])


def test_deterministic_output_and_cli_contract(monkeypatch):
    path = _path("src", "agent", "judge", "tarch_normalize.py")
    first = affected.render(_result(*path.split("/")), "test", explain=True)
    original_files = affected.first_class_files()
    monkeypatch.setattr(affected, "first_class_files", lambda: tuple(reversed(original_files)))
    second = affected.render(_result(*path.split("/")), "test", explain=True)
    assert first == second
    assert first.startswith("SCOPE: SUBSET\npython -m pytest ")
    assert "跑测声明：受影响子集 = " in first
    assert "EXPLAIN: " in first

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/tool_scripts/affected_tests.py",
            "--changed",
            path,
            "--explain",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.startswith("SCOPE: SUBSET\n")
    assert "EXPLAIN: " in completed.stdout


def test_tarch_import_edges_select_the_locked_tests():
    result = _result("src", "agent", "judge", "tarch_normalize.py")
    assert result.scope == "SUBSET"
    assert {
        "tests/test_tarch_converter_p1_geometry.py",
        "tests/test_tarch_converter_p2_geometry.py",
        "tests/test_tarch_converter_gate_mutations.py",
    } <= set(result.tests)


def test_root_entrypoint_string_path_reaches_mcp_server():
    result = _result("src", "mcp", "server.py")
    test = "tests/test_mcp_stdio.py"
    assert result.scope == "SUBSET"
    assert test in result.tests
    files = affected.first_class_files()
    edges = affected.build_edges(files)
    chain = affected.find_path(edges, test, "src/mcp/server.py")
    assert chain is not None
    assert affected.Edge(test, "main.py", "string-path") in chain
    assert affected.Edge("main.py", "src/mcp/server.py", "import") in chain


def test_transitive_import_edge_is_not_a_direct_edge():
    target = _path("src", "agent", "judge", "score_inputs.py")
    result = _result(*target.split("/"))
    test = "tests/test_audit_remediation_accepted_inputs.py"
    assert test in result.tests
    explanation = result.explanations[test]
    assert any("scripts/tool_scripts/run_stage.py" in line for line in explanation)
    files = affected.first_class_files()
    edges = affected.build_edges(files)
    assert not any(edge.source == test and edge.target == target for edge in edges)
    assert len(affected.find_path(edges, test, target) or ()) >= 2


def test_string_path_edge_is_recorded_for_gt_from_dxf():
    edges = affected.build_edges(affected.first_class_files())
    assert any(
        edge.source == "tests/test_gt_from_dxf.py"
        and edge.target == "scripts/tool_scripts/gt_from_dxf.py"
        and edge.kind == "string-path"
        for edge in edges
    )


def test_pure_string_path_subprocess_edge_selects_cv_toolbox():
    source = "tests/test_cv_toolbox.py"
    target = "scripts/tool_scripts/cv_probe.py"
    result = _result(*target.split("/"))
    assert result.scope == "SUBSET"
    assert source in result.tests
    edges = affected.build_edges(affected.first_class_files())
    assert any(
        edge.source == source
        and edge.target == target
        and edge.kind == "string-path"
        for edge in edges
    )
    assert not any(
        edge.source == source and edge.target == target and edge.kind == "import"
        for edge in edges
    )


def test_subset_contains_only_runnable_test_files_and_keeps_helper_transit():
    result = _result("src", "agent", "pipeline.py")
    assert result.scope == "SUBSET"
    assert "tests/b4b_contract_fixture.py" not in result.tests
    assert "tests/b5_test_helpers.py" not in result.tests
    assert all(Path(path).name.startswith("test_") for path in result.tests)

    edges = affected.build_edges(affected.first_class_files())
    assert affected.Edge(
        "tests/test_c2_b4b_phase_b.py",
        "tests/b4b_contract_fixture.py",
        "import",
    ) in edges
    assert affected.Edge(
        "tests/b4b_contract_fixture.py",
        "src/agent/correction/facade_visibility.py",
        "import",
    ) in edges


def test_production_string_paths_cannot_bridge_through_test_nodes():
    changed = "scripts/tool_scripts/cv_probe.py"
    result = _result(*changed.split("/"))
    assert result.scope == "SUBSET"
    assert "tests/test_cv_toolbox.py" in result.tests
    assert "tests/test_gt_from_dxf.py" not in result.tests
    assert len(result.tests) <= 9

    edges = affected.build_edges(affected.first_class_files())
    assert affected.Edge(
        "src/agent/judge/gt.py",
        "tests/test_gt_discipline.py",
        "string-path",
    ) not in edges


def test_fail_closed_for_non_first_class_path():
    result = affected.affected_tests(["README.md"])
    assert result.scope == "FULL"
    assert "not a first-class Python file" in result.reasons[0]


def test_fail_closed_for_full_scope_trigger():
    result = affected.affected_tests(["pyproject.toml"])
    assert result.scope == "FULL"
    assert "full-scope trigger matched" in result.reasons[0]


def test_fail_closed_for_deleted_file():
    result = _result("src", "agent", "does_not_exist.py")
    assert result.scope == "FULL"
    assert "deleted or absent" in result.reasons[0]


def test_fail_closed_for_broken_rules_table(tmp_path, monkeypatch):
    broken = tmp_path / "broken.yaml"
    broken.write_text("full_scope: [", encoding="utf-8")
    monkeypatch.setattr(affected, "RULES_PATH", broken)
    result = _result("src", "agent", "pipeline.py")
    assert result.scope == "FULL"
    assert "rules table cannot be parsed" in result.reasons[0]


def test_every_production_module_is_mapped_or_honestly_allowlisted():
    rules = yaml.safe_load(affected.RULES_PATH.read_text(encoding="utf-8"))
    allowlist = rules["uncovered_allowlist"]
    assert allowlist and all(reason.strip() for reason in allowlist.values())

    files = affected.first_class_files()
    edges = affected.build_edges(files)
    tests = [path for path in files if path.startswith("tests/")]
    production = [path for path in files if path.startswith(("src/", "scripts/"))]
    uncovered = {
        path
        for path in production
        if not any(affected.find_path(edges, test, path) is not None for test in tests)
    }
    assert uncovered == set(allowlist)


def test_uncovered_first_class_module_falls_back_to_full_scope():
    result = _result("scripts", "tool_scripts", "baseline_record.py")
    assert result.scope == "FULL"
    assert "has no covering test" in result.reasons[0]


def test_since_uses_committed_range_only(tmp_path, monkeypatch):
    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout.strip()

    git("init")
    git("config", "user.email", "affected-tests@example.invalid")
    git("config", "user.name", "Affected Tests")
    (tmp_path / "baseline.py").write_text("BASELINE = 1\n", encoding="utf-8")
    git("add", "baseline.py")
    git("commit", "-m", "baseline")
    base = git("rev-parse", "HEAD")
    (tmp_path / "committed.py").write_text("COMMITTED = 1\n", encoding="utf-8")
    git("add", "committed.py")
    git("commit", "-m", "committed change")
    (tmp_path / "baseline.py").write_text("BASELINE = 2\n", encoding="utf-8")

    monkeypatch.setattr(affected, "REPO_ROOT", tmp_path)
    assert affected.changed_since(base) == ["committed.py"]
