"""Step 3 of the interface sweep: subtract.

For every WRITE-side tool parameter the model can set, report whether the
owning node's system prompt says anything about it at all, and whether any
gate constrains it beyond bare type/format validity.

This is deliberately mechanical and deliberately dumb: "the prompt mentions
this token" is a *lower bound* on guidance, and "a gate names this field" is
a *lower bound* on protection. A parameter that fails both is a candidate,
not a verdict — F-15 is precisely the shape where the prompt said nothing
and the only gate was a type check.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

REPO = pathlib.Path("/workspaces/EnergyPlus-Agent-dev")
if not (REPO / "pyproject.toml").exists():
    sys.exit(f"repo root not found at {REPO}")

# tool factory file stem -> node module that binds it
FACTORY_TO_NODE = {
    "construction_tools.py": "construction.py",
    "fenestration_tools.py": "fenestration.py",
    "hvac_tools.py": "hvac.py",
    "lights_tools.py": "lights.py",
    "material_tools.py": "material.py",
    "people_tools.py": "people.py",
    "schedule_tools.py": "schedule.py",
    "surface_tools.py": "surface.py",
    "zone_tools.py": "zone.py",
    "output_tools.py": None,  # not bound by any phase node
}

WRITE_PREFIXES = ("create_", "update_", "add_", "delete_")

# Files whose rejections could plausibly constrain a downstream tool write.
GATE_SOURCES = [
    REPO / "src" / "validator" / "data_model.py",
    REPO / "src" / "agent" / "tools",
    REPO / "src" / "validator" / "output_coordinates.py",
    REPO / "src" / "validator" / "interzone.py",
]


def node_prompt_text(node_file: str) -> str:
    path = REPO / "src" / "agent" / "nodes" / node_file
    tree = ast.parse(path.read_text(encoding="utf-8"))
    chunks = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and "PROMPT" in t.id:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        chunks.append(node.value.value)
    return "\n".join(chunks)


def gate_corpus() -> str:
    parts = []
    for src in GATE_SOURCES:
        if src.is_dir():
            for f in sorted(src.rglob("*.py")):
                parts.append(f.read_text(encoding="utf-8"))
        elif src.exists():
            parts.append(src.read_text(encoding="utf-8"))
    return "\n".join(parts)


def mentions(text: str, param: str) -> bool:
    """Token-boundary match on the parameter name, and on its likely
    IDD-style alias (snake_case -> Title Case With Spaces)."""
    alias = " ".join(w.capitalize() for w in param.split("_"))
    for needle in (param, alias):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(needle)}(?![A-Za-z0-9_])", text, re.I):
            return True
    return False


# Beyond-format protection: a gate that names the field AND does something
# other than a pure pydantic Field(...) type/range declaration.
def constrained_beyond_format(corpus: str, param: str) -> bool:
    alias = " ".join(w.capitalize() for w in param.split("_"))
    for needle in (param, alias):
        for m in re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(needle)}(?![A-Za-z0-9_])", corpus, re.I):
            line_start = corpus.rfind("\n", 0, m.start()) + 1
            line_end = corpus.find("\n", m.end())
            line = corpus[line_start : line_end if line_end != -1 else len(corpus)]
            if "Field(" in line or "alias=" in line:
                continue  # bare schema declaration
            return True
    return False


if __name__ == "__main__":
    exposure = json.loads((pathlib.Path(__file__).parent / "exposure.json").read_text())
    corpus = gate_corpus()
    rows = []
    for factory_key, tools in exposure["tool_exposure"].items():
        factory_file = factory_key.split("::")[0]
        node_file = FACTORY_TO_NODE.get(factory_file)
        prompt = node_prompt_text(node_file) if node_file else ""
        for t in tools:
            if not t["tool"].startswith(WRITE_PREFIXES):
                continue
            for p in t["params"]:
                rows.append(
                    {
                        "node": node_file or "(unbound)",
                        "tool": t["tool"],
                        "param": p["name"],
                        "optional": p["has_default"],
                        "in_prompt": mentions(prompt, p["name"]),
                        "gated_beyond_format": constrained_beyond_format(corpus, p["name"]),
                    }
                )
    print(json.dumps(rows, indent=2, ensure_ascii=False))
