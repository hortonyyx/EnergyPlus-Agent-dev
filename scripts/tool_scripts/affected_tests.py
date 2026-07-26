#!/usr/bin/env python3
"""Print the deterministic pytest subset affected by repository Python changes.

``--since REF`` compares ``REF...HEAD`` only.  It deliberately does not include
staged or unstaged working-tree changes; pass those paths explicitly with
``--changed``.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "scripts/tool_scripts/affected_tests_rules.yaml"
FIRST_CLASS_ROOTS = ("src", "scripts", "tests")
EXCLUDED_PREFIXES = ("scripts/tool_scripts/vendor/",)


class MappingError(Exception):
    """A condition for which selecting a subset would be unsafe."""


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class MappingResult:
    scope: str
    tests: tuple[str, ...]
    reasons: tuple[str, ...]
    explanations: dict[str, tuple[str, ...]]


def repository_path(path: str | Path) -> str:
    """Return a normalized repository-relative path without resolving symlinks."""
    raw = Path(path)
    if raw.is_absolute():
        try:
            raw = raw.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise MappingError(f"path outside repository: {path}") from exc
    normalized = PurePosixPath(raw.as_posix())
    if normalized.is_absolute() or ".." in normalized.parts:
        raise MappingError(f"path escapes repository: {path}")
    return normalized.as_posix()


def first_class_files(root: Path = REPO_ROOT) -> tuple[str, ...]:
    files: list[str] = []
    for directory in FIRST_CLASS_ROOTS:
        base = root / directory
        if not base.exists():
            continue
        for candidate in base.rglob("*.py"):
            relative = candidate.relative_to(root).as_posix()
            if "__pycache__" in candidate.parts or relative.startswith(EXCLUDED_PREFIXES):
                continue
            files.append(relative)
    # Repository entry points are part of the project dependency graph too:
    # tests commonly launch them by relative path instead of importing them.
    for candidate in root.glob("*.py"):
        if "__pycache__" not in candidate.parts:
            files.append(candidate.relative_to(root).as_posix())
    return tuple(sorted(files))


def load_rules(path: Path | None = None) -> dict[str, tuple[str, ...]]:
    path = RULES_PATH if path is None else path
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MappingError(f"rules table cannot be parsed: {exc}") from exc
    if not isinstance(raw, dict):
        raise MappingError("rules table must be a mapping")
    expected = {"full_scope", "uncovered_allowlist"}
    if set(raw) != expected:
        raise MappingError("rules table must contain only full_scope and uncovered_allowlist")
    full_scope = raw["full_scope"]
    allowlist = raw["uncovered_allowlist"]
    if not isinstance(full_scope, list) or not all(isinstance(item, str) for item in full_scope):
        raise MappingError("rules table full_scope must be a list of strings")
    if not isinstance(allowlist, dict) or not all(
        isinstance(item, str) and isinstance(reason, str)
        for item, reason in allowlist.items()
    ):
        raise MappingError("rules table uncovered_allowlist must map paths to reasons")
    return {
        "full_scope": tuple(sorted(full_scope)),
        "uncovered_allowlist": tuple(sorted(allowlist)),
    }


def module_for_path(path: str) -> str:
    candidate = PurePosixPath(path)
    parts = list(candidate.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def module_paths(files: tuple[str, ...]) -> dict[str, str]:
    return {module_for_path(path): path for path in files}


def resolve_module(module: str, modules: dict[str, str]) -> tuple[str, ...]:
    """Resolve a repository module, including package ``__init__.py`` files."""
    if not module:
        return ()
    top_level = module.split(".", 1)[0]
    if top_level not in FIRST_CLASS_ROOTS and top_level not in modules:
        return ()
    resolved: list[str] = []
    exact = modules.get(module)
    if exact is not None:
        resolved.append(exact)
    parts = module.split(".")
    for index in range(1, len(parts)):
        package = modules.get(".".join(parts[:index]))
        if package is not None:
            resolved.append(package)
    return tuple(sorted(set(resolved)))


def package_for_path(path: str) -> tuple[str, ...]:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    parts.pop()
    return tuple(parts)


def import_targets(node: ast.Import | ast.ImportFrom, source: str, modules: dict[str, str]) -> tuple[str, ...]:
    targets: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.update(resolve_module(alias.name, modules))
        return tuple(sorted(targets))

    if node.level:
        package = list(package_for_path(source))
        keep = len(package) - (node.level - 1)
        if keep < 1:
            return ()
        base_parts = package[:keep]
        if node.module:
            base_parts.extend(node.module.split("."))
        base = ".".join(base_parts)
    else:
        base = node.module or ""
    targets.update(resolve_module(base, modules))
    for alias in node.names:
        if alias.name != "*":
            targets.update(resolve_module(f"{base}.{alias.name}", modules))
    return tuple(sorted(targets))


def build_edges(files: tuple[str, ...]) -> tuple[Edge, ...]:
    modules = module_paths(files)
    edges: set[Edge] = set()
    for source in files:
        try:
            tree = ast.parse((REPO_ROOT / source).read_text(encoding="utf-8"), filename=source)
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            raise MappingError(f"import graph cannot parse {source}: {exc}") from exc
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for target in import_targets(node, source, modules):
                    edges.add(Edge(source, target, "import"))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for target in files:
                    if (
                        target in node.value
                        and not (target.startswith("tests/") and not source.startswith("tests/"))
                    ):
                        edges.add(Edge(source, target, "string-path"))
    return tuple(sorted(edges))


def is_full_scope_path(path: str, rules: dict[str, tuple[str, ...]]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in rules["full_scope"])


def find_path(edges: tuple[Edge, ...], start: str, goal: str) -> tuple[Edge, ...] | None:
    outgoing: dict[str, list[Edge]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source, []).append(edge)
    queue: deque[tuple[str, tuple[Edge, ...]]] = deque([(start, ())])
    visited = {start}
    while queue:
        current, chain = queue.popleft()
        if current == goal:
            return chain
        for edge in outgoing.get(current, []):
            if edge.target not in visited:
                visited.add(edge.target)
                queue.append((edge.target, (*chain, edge)))
    return None


def format_chain(test: str, changed: str, chain: tuple[Edge, ...] | None) -> str:
    if test == changed:
        return f"{test}: changed test file"
    assert chain is not None
    labels = []
    for edge in chain:
        labels.append(f"{edge.source} --{edge.kind}--> {edge.target}")
    return f"{test}: " + " ; ".join(labels)


def affected_tests(changed_paths: list[str]) -> MappingResult:
    try:
        rules = load_rules()
        normalized = tuple(sorted({repository_path(path) for path in changed_paths}))
        if not normalized:
            raise MappingError("no changed paths supplied")
        for path in normalized:
            if not (REPO_ROOT / path).is_file():
                raise MappingError(f"changed path is deleted or absent: {path}")
            if is_full_scope_path(path, rules):
                raise MappingError(f"full-scope trigger matched: {path}")
        files = first_class_files()
        file_set = set(files)
        for path in normalized:
            if path not in file_set:
                raise MappingError(f"path is not a first-class Python file: {path}")
        edges = build_edges(files)
    except MappingError as exc:
        return MappingResult("FULL", (), (str(exc),), {})

    selected: set[str] = set()
    explanations: dict[str, list[str]] = {}
    test_nodes = tuple(path for path in files if path.startswith("tests/"))
    runnable_tests = tuple(
        path
        for path in test_nodes
        if PurePosixPath(path).name.startswith("test_")
    )
    for test in runnable_tests:
        for changed in normalized:
            chain = find_path(edges, test, changed)
            if chain is not None:
                selected.add(test)
                explanations.setdefault(test, []).append(format_chain(test, changed, chain))
    if not selected:
        return MappingResult(
            "FULL",
            (),
            (f"changed first-class module has no covering test: {', '.join(normalized)}",),
            {},
        )
    return MappingResult(
        "SUBSET",
        tuple(sorted(selected)),
        (),
        {test: tuple(sorted(lines)) for test, lines in sorted(explanations.items())},
    )


def changed_since(ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{ref}...HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or f"cannot diff against {ref}")
    return [line for line in completed.stdout.splitlines() if line]


def render(result: MappingResult, provenance: str, explain: bool) -> str:
    lines = [f"SCOPE: {result.scope}"]
    if result.scope == "FULL":
        lines.append("python -m pytest -p no:cacheprovider -q")
        reason = "; ".join(result.reasons)
        lines.append(f"跑测声明：受影响子集 = 全仓（依据 {provenance}；原因：{reason}）")
        return "\n".join(lines)
    command = "python -m pytest -p no:cacheprovider -q " + " ".join(result.tests)
    lines.append(command)
    subset = " ".join(result.tests)
    lines.append(f"跑测声明：受影响子集 = {subset}（依据 {provenance}）")
    if explain:
        for test in result.tests:
            for detail in result.explanations[test]:
                lines.append(f"EXPLAIN: {detail}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", nargs="+", metavar="PATH", help="explicit changed paths")
    group.add_argument("--since", metavar="GIT_REF", help="paths from git diff --name-only GIT_REF...HEAD; ignores uncommitted changes")
    parser.add_argument("--explain", action="store_true", help="show import/string-path chains for each selected test")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.since:
        try:
            changed = changed_since(args.since)
        except ValueError as exc:
            print(f"usage error: {exc}", file=sys.stderr)
            return 2
        provenance = f"affected_tests.py --since {args.since}"
    else:
        changed = args.changed
        provenance = "affected_tests.py --changed " + " ".join(changed)
    print(render(affected_tests(changed), provenance, args.explain))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
