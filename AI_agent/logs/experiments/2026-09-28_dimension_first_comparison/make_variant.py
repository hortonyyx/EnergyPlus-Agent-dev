"""Replace only one reference in an isolated, uncommitted experiment worktree."""
import ast
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TREE = ROOT / ".worktrees/dimension-first-20260928"
target = TREE / "scripts/tool_scripts/bim_agent_guidance.py"
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TREE, text=True).strip().startswith("c07967d0")
source = target.read_text()
assert source == (ROOT / "scripts/tool_scripts/bim_agent_guidance.py").read_text(), "Start from the unmodified frozen reference"
for node in ast.walk(ast.parse(source)):
    if isinstance(node, ast.Dict):
        matches = [value for key, value in zip(node.keys, node.values)
                   if isinstance(key, ast.Constant) and key.value == "reconstruction"]
        if matches:
            value, = matches
            break
else:
    raise AssertionError("Missing reconstruction reference")
lines = source.splitlines(keepends=True)
start = sum(len(line) for line in lines[:value.lineno-1]) + value.col_offset
end = sum(len(line) for line in lines[:value.end_lineno-1]) + value.end_col_offset
method = (HERE / "method_b.txt").read_text()
updated = source[:start] + json.dumps(method) + source[end:]
ast.parse(updated)
target.write_text(updated)
patch = subprocess.check_output(["git", "diff", "--", "scripts/tool_scripts/bim_agent_guidance.py"], cwd=TREE, text=True)
(HERE / "method_b.patch").write_text(patch)
print(json.dumps(dict(changed_reference="reconstruction", bytes=len(method), worktree=str(TREE))))
