"""Step 5 (axis B) of the interface sweep: single-source audit.

Find literal string-set/tuple/list constants that appear in more than one
place. F-15's second wall was exactly this: the b2 gate hardcoded its own
copy of a forbidden-field list that had already drifted from the schema
markers it was supposed to mirror.

Reports two things:
  * duplicate literal collections (same frozen set of strings declared in
    >= 2 distinct locations)
  * facade / direction / day-type style vocabularies, which are the
    project's most-repeated domain enums
"""

from __future__ import annotations

import ast
import collections
import json
import pathlib
import sys

REPO = pathlib.Path("/workspaces/EnergyPlus-Agent-dev")
if not (REPO / "pyproject.toml").exists():
    sys.exit(f"repo root not found at {REPO}")

ROOTS = [REPO / "src"]
MIN_MEMBERS = 2


def literal_str_collection(node: ast.AST) -> tuple[str, ...] | None:
    """Return the sorted string members if node is a literal collection of
    strings (set/list/tuple), else None."""
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        elts = node.elts
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"frozenset", "set"}:
        if not node.args:
            return None
        inner = node.args[0]
        if not isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
            return None
        elts = inner.elts
    else:
        return None
    members = []
    for e in elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            members.append(e.value)
        else:
            return None
    if len(members) < MIN_MEMBERS:
        return None
    return tuple(sorted(members))


def subscript_literals(node: ast.AST) -> tuple[str, ...] | None:
    """Literal[...] annotations — the pydantic way of declaring the same enum."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Literal":
        sl = node.slice
        elts = sl.elts if isinstance(sl, ast.Tuple) else [sl]
        members = []
        for e in elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                members.append(e.value)
            else:
                return None
        if len(members) < MIN_MEMBERS:
            return None
        return tuple(sorted(members))
    return None


if __name__ == "__main__":
    seen: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    for root in ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in str(path):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            rel = str(path.relative_to(REPO))
            for node in ast.walk(tree):
                for extractor in (literal_str_collection, subscript_literals):
                    members = extractor(node)
                    if members:
                        seen[members].append(f"{rel}:{node.lineno}")
                        break

    dupes = {
        k: sorted(set(v))
        for k, v in seen.items()
        if len({loc.split(":")[0] for loc in v}) >= 2
    }
    ordered = sorted(dupes.items(), key=lambda kv: -len(kv[1]))
    print(json.dumps(
        [{"members": list(k), "declared_at": v, "n_sites": len(v)} for k, v in ordered],
        indent=2, ensure_ascii=False,
    ))
