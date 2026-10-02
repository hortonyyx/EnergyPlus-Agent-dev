"""Stage 0 package boundary checks; no providers or frozen tools are invoked."""

import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "harness_contracts"


def test_core_imports_no_building_or_tool_modules():
    """All core files must remain usable without the building application."""
    files = sorted(CORE.glob("*.py"))
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] if not node.level else []
                assert node.level <= 1, (path.name, "core cannot import its parent")
            else:
                continue
            for name in names:
                assert not name.startswith(("src.agent", "scripts")), (path.name, name)
                assert name not in {"src", "agent"}, (path.name, name)


def test_contract_imports_resolve_inside_this_worktree():
    """The shared editable installation must not silently select the main tree."""
    for name in ("src.harness_contracts", "src.agent.contracts"):
        module = importlib.import_module(name)
        assert Path(module.__file__).resolve().is_relative_to(ROOT)
