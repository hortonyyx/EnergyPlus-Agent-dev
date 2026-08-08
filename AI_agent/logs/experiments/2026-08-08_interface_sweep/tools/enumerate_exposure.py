"""Step 1 of the interface sweep: mechanically enumerate what each LLM
interface actually shows the model.

Two different exposure shapes exist in this project and they must not be
conflated:

  * downstream 9 nodes  -> ReAct agents; the model sees TOOL PARAMETER
    schemas (name + annotation + default + docstring), plus the node's
    system prompt and the specs string.
  * correction draw     -> structured output; the model sees a JSON Schema
    derived from pydantic models.

This script only reports; it makes no judgement about what SHOULD be
visible. Step 3 does the subtraction.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

REPO = pathlib.Path("/workspaces/EnergyPlus-Agent-dev")
if not (REPO / "pyproject.toml").exists():
    sys.exit(f"repo root not found at {REPO}")

TOOLS_DIR = REPO / "src" / "agent" / "tools"
NODES_DIR = REPO / "src" / "agent" / "nodes"


def _decorated_with_tool(fn: ast.FunctionDef) -> bool:
    for d in fn.decorator_list:
        if isinstance(d, ast.Name) and d.id == "tool":
            return True
        if isinstance(d, ast.Attribute) and d.attr == "tool":
            return True
        if isinstance(d, ast.Call):
            f = d.func
            if isinstance(f, ast.Name) and f.id == "tool":
                return True
            if isinstance(f, ast.Attribute) and f.attr == "tool":
                return True
    return False


def _ann(node: ast.expr | None) -> str:
    return ast.unparse(node) if node is not None else "<none>"


def collect_tool_params() -> dict[str, list[dict]]:
    """factory name -> list of {tool, params:[{name, annotation, has_default}]}"""
    out: dict[str, list[dict]] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for top in tree.body:
            if not isinstance(top, ast.FunctionDef) or not top.name.startswith("make_"):
                continue
            tools: list[dict] = []
            for sub in ast.walk(top):
                if not isinstance(sub, ast.FunctionDef) or not _decorated_with_tool(sub):
                    continue
                a = sub.args
                positional = a.posonlyargs + a.args
                ndef = len(a.defaults)
                params = []
                for i, arg in enumerate(positional):
                    if arg.arg == "self":
                        continue
                    has_default = i >= len(positional) - ndef
                    params.append(
                        {
                            "name": arg.arg,
                            "annotation": _ann(arg.annotation),
                            "has_default": has_default,
                        }
                    )
                for arg, d in zip(a.kwonlyargs, a.kw_defaults):
                    params.append(
                        {
                            "name": arg.arg,
                            "annotation": _ann(arg.annotation),
                            "has_default": d is not None,
                        }
                    )
                tools.append(
                    {
                        "tool": sub.name,
                        "params": params,
                        "doc_lines": len((ast.get_docstring(sub) or "").splitlines()),
                    }
                )
            out[f"{path.name}::{top.name}"] = tools
    return out


def collect_node_prompts() -> dict[str, dict]:
    """node file -> {prompts: [names], specs_sources: [attr chains]}"""
    out: dict[str, dict] = {}
    for path in sorted(NODES_DIR.glob("*.py")):
        if path.name in {"__init__.py", "_share.py"}:
            continue
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        prompts = [
            t.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for t in node.targets
            if isinstance(t, ast.Name) and "PROMPT" in t.id
        ]
        specs: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                chain = ast.unparse(node)
                if "intake_output." in chain:
                    specs.append(chain)
        out[path.name] = {
            "prompts": prompts,
            "intake_fields_read": sorted(set(specs)),
        }
    return out


if __name__ == "__main__":
    report = {
        "tool_exposure": collect_tool_params(),
        "node_prompts": collect_node_prompts(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
