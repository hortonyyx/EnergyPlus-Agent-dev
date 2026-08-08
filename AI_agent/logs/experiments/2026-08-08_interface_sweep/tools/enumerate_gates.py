"""Step 2 of the interface sweep: mechanically enumerate every point that
can REJECT model-produced content, and record what each one forbids.

Scope note: a "gate" here means a rejection reachable from an LLM's
output. Pure-internal invariants that no model output can trigger are
reported separately so step 3 does not credit them as protection.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

REPO = pathlib.Path("/workspaces/EnergyPlus-Agent-dev")
if not (REPO / "pyproject.toml").exists():
    sys.exit(f"repo root not found at {REPO}")

TARGETS = [
    "src/validator/data_model.py",
    "src/validator/checks",
    "src/agent/correction",
    "src/agent/tools",
    "src/agent/nodes",
    "src/mcp/tools",
]


def enclosing_names(tree: ast.AST) -> dict[int, str]:
    """line number -> dotted enclosing function/class name"""
    mapping: dict[int, str] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                for ln in range(child.lineno, (child.end_lineno or child.lineno) + 1):
                    mapping[ln] = name
                walk(child, name)
            else:
                walk(child, prefix)

    walk(tree, "")
    return mapping


def scan(path: pathlib.Path) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    owners = enclosing_names(tree)
    lines = src.splitlines()
    found: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        exc_type = ""
        first_arg = ""
        if isinstance(exc, ast.Call):
            exc_type = ast.unparse(exc.func)
            if exc.args:
                try:
                    first_arg = ast.unparse(exc.args[0])[:160]
                except Exception:
                    first_arg = ""
            for kw in exc.keywords:
                if kw.arg == "category":
                    first_arg += f"  [category={ast.unparse(kw.value)}]"
        else:
            exc_type = ast.unparse(exc)
        found.append(
            {
                "file": str(path.relative_to(REPO)),
                "line": node.lineno,
                "owner": owners.get(node.lineno, "<module>"),
                "exc": exc_type,
                "detail": first_arg,
                "text": lines[node.lineno - 1].strip()[:180],
            }
        )
    return found


if __name__ == "__main__":
    results: list[dict] = []
    for t in TARGETS:
        p = REPO / t
        if p.is_dir():
            for f in sorted(p.rglob("*.py")):
                results.extend(scan(f))
        elif p.exists():
            results.extend(scan(p))
    print(json.dumps(results, indent=2, ensure_ascii=False))
