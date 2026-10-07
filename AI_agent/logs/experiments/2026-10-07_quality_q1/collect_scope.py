"""Read-only scope and syntax audit for the Q1 handoff; never writes Git metadata."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = "e030b6b0195eea18d2d54261038f8a8f25640518"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "--no-optional-locks", *args], cwd=ROOT)


class HideNestedBodies(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        result = copy.deepcopy(node)
        result.body = [ast.Pass()]
        return result

    visit_AsyncFunctionDef = visit_FunctionDef


def functions(tree):
    result = {}

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + child.name
                if not isinstance(child, ast.ClassDef):
                    value = copy.deepcopy(child)
                    value.body = [HideNestedBodies().visit(row) for row in value.body]
                    result[name] = ast.dump(value, include_attributes=False)
                visit(child, name + ".")
            else:
                visit(child, prefix)

    visit(tree)
    return result


def assignments(tree):
    return {target.id: ast.dump(node.value, include_attributes=False)
            for node in tree.body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)}


def differences(before, after):
    return sorted(key for key in before.keys() | after.keys()
                  if before.get(key) != after.get(key))


def main():
    tracked = git("diff", "--name-only", BASE).decode("utf-8").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").decode("utf-8").splitlines()
    changed = sorted(set(tracked + untracked))
    protected = [name for name in tracked if (
        name.startswith("src/agent_runtime/")
        or name.startswith("src/agent/runtime_roles/height_")
        or name in {
            "src/agent/runtime_roles/elevation.py",
            "src/agent/runtime_roles/assembly.py",
            "src/agent/runtime_roles/assembly_review.py",
            "AI_agent/config/agent_versions.json",
        })]
    python_files = [name for name in changed if name.endswith(".py")]
    for name in python_files:
        compile((ROOT / name).read_bytes(), name, "exec")
    crlf = [name for name in changed
            if Path(name).suffix in {".py", ".md", ".json", ".xml", ".patch"}
            and b"\r\n" in (ROOT / name).read_bytes()]
    function_changes, assignment_changes, import_changes = {}, {}, {}
    for name in (
        "scripts/tool_scripts/run_bim_agent.py",
        "src/agent/runtime_roles/session.py",
        "src/agent/runtime_roles/guidance.py",
    ):
        before = ast.parse(git("show", f"{BASE}:{name}").decode("utf-8"))
        after = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        function_changes[name] = differences(functions(before), functions(after))
        assignment_changes[name] = differences(assignments(before), assignments(after))
        old_imports = {ast.dump(row, include_attributes=False) for row in before.body
                       if isinstance(row, (ast.Import, ast.ImportFrom))}
        new_imports = {ast.dump(row, include_attributes=False) for row in after.body
                       if isinstance(row, (ast.Import, ast.ImportFrom))}
        import_changes[name] = {"added": sorted(new_imports - old_imports),
                                "removed": sorted(old_imports - new_imports)}
    production = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                  for name in changed if name.startswith(("src/", "scripts/"))}
    shared_registry = ROOT / "AI_agent/config/agent_versions.json"
    if not shared_registry.is_file():
        # The baseline registry lives under agent versions, not this package.
        candidates = [name for name in git("ls-files", "*agent_versions.json").decode().splitlines()]
        if len(candidates) != 1:
            raise ValueError(f"Cannot identify the shared registry: {candidates}")
        shared_registry = ROOT / candidates[0]
    registry_name = shared_registry.relative_to(ROOT).as_posix()
    if shared_registry.read_bytes() != git("show", f"{BASE}:{registry_name}"):
        protected.append(registry_name)
    subprocess.run(["git", "--no-optional-locks", "diff", "--check"], cwd=ROOT, check=True)
    result = {
        "schema": "q1-final-scope-check-v2", "base_commit": BASE,
        "changed_python_compiles": len(python_files), "crlf_files": crlf,
        "protected_files_changed": sorted(set(protected)),
        "function_changes": function_changes, "assignment_changes": assignment_changes,
        "import_changes": import_changes, "production_sha256": production,
        "shared_registry_file": registry_name,
        "shared_registry_sha256": hashlib.sha256(shared_registry.read_bytes()).hexdigest(),
        "head_unchanged": git("rev-parse", "HEAD").decode().strip() == BASE,
        "git_diff_check": "pass",
    }
    (HERE / "scope_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: result[key] for key in (
        "changed_python_compiles", "crlf_files", "protected_files_changed",
        "function_changes", "assignment_changes", "head_unchanged", "git_diff_check")},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
