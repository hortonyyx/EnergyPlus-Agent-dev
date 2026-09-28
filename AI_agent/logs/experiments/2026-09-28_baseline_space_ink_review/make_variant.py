"""Build one review-feedback package on the isolated historical baseline."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TREE = ROOT.parent / "EnergyPlus-Agent-dev-worktrees/baseline-ink-review-20260928"
BASE = "468d83f7626e5af630fb3f4de47d2af904d9a834"


def build():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TREE, text=True).strip() == BASE
    relative = "scripts/tool_scripts/run_bim_agent.py"
    original = subprocess.check_output(["git", "show", f"{BASE}:{relative}"], cwd=ROOT, text=True)
    changed = original
    replacements = [
        ('        if index > 6:\n', '        if index > self.manifest.get("max_candidates", 24):\n'),
        ('Six immutable candidates maximum.', 'Up to 24 immutable candidates; the run input records its budget.'),
        ('    manifest = {"images":images,"scope":args.scope,"provider":provider,',
         '    manifest = {"images":images,"scope":args.scope,"provider":provider,\n                             "max_candidates":24,"continuation_rounds":0,'),
        ('                                 "src/agent/geometry/pixel_region_overview.py":digest(ROOT/"src/agent/geometry/pixel_region_overview.py")},',
         '                                 "src/agent/geometry/pixel_region_overview.py":digest(ROOT/"src/agent/geometry/pixel_region_overview.py"),\n                                 "src/agent/geometry/space_ink_support.py":digest(ROOT/"src/agent/geometry/space_ink_support.py"),\n                                 "scripts/tool_scripts/bim_space_ink_feedback.py":digest(ROOT/"scripts/tool_scripts/bim_space_ink_feedback.py")},'),
        ('        dump(draft / "result.json", result)\n        return result\n',
         '        if result.get("source_geometry_ready"):\n            try:\n                from scripts.tool_scripts.bim_space_ink_feedback import add_space_ink_feedback\n                add_space_ink_feedback(self, result)\n            except Exception as error:\n                result["space_ink_review"] = {"status":"unavailable", "error":str(error), "drawing_fidelity":"not_evaluated"}\n        dump(draft / "result.json", result)\n        return result\n'),
        ('        content = []\n        draft_view = result.get("plan_input", {}).get("draft_view")',
         '        result = {**{k:result[k] for k in ("space_ink_review",) if k in result}, **result}\n        content = []\n        for view in result.get("space_ink_views", []):\n            try:\n                content.append(Image(data=(toolkit.run / view["file"]).read_bytes(), format="png").to_image_content())\n            except Exception as error:\n                result.setdefault("space_ink_image_errors", []).append(str(error))\n        draft_view = result.get("plan_input", {}).get("draft_view")'),
    ]
    for before, after in replacements:
        assert changed.count(before) == 1, before
        changed = changed.replace(before, after)
    ast.parse(changed)
    target = TREE / relative
    assert target.read_text() in (original, changed), "Unrecognized worktree changes"
    target.write_text(changed)
    copies = {
        "src/agent/geometry/space_ink_support.py": ROOT / "src/agent/geometry/space_ink_support.py",
        "scripts/tool_scripts/bim_space_ink_feedback.py": HERE / "feedback.py",
    }
    for name, source in copies.items():
        dest = TREE / name
        if dest.exists():
            assert dest.read_bytes() == source.read_bytes(), "Do not overwrite unexpected experimental code"
        dest.write_bytes(source.read_bytes())
    patch = subprocess.check_output(["git", "diff", "--", relative], cwd=TREE, text=True)
    (HERE / "runtime.patch").write_text(patch)
    record = dict(base=BASE, tree=str(TREE), changed_existing_files=[relative], added_files=list(copies),
        support_sha256=hashlib.sha256(copies["src/agent/geometry/space_ink_support.py"].read_bytes()).hexdigest(),
        feature="Automatic raw interior-ink feedback after successful saved plan build/revision; no geometry changes.",
        mechanical_delta="Candidate budget6 to24 retained from the current harness to permit review-driven edits; guidance/tool description budget agrees.",
        excluded="No later reconstruction references, claims/view changes, role/name changes, units/measurement feedback, continuation or multi-model work is ported into this baseline experiment. Those remain on main.",
        model_calls=0)
    (HERE / "variant.json").write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(record))


if __name__ == "__main__":
    build()
