"""D-1 retirement gate (2026-08-25): the tools/ copy of retired logic is a shim.

命题（派工单 2026-08-25_d1 §二）：「同一段逻辑存在两处可独立漂移的副本」必须消失。

机械判据（不靠肉眼、不靠「我删了文件」的叙述）：
  (a) 函数体指纹零交集 -- 对 tools/*.py 与 src/**/*.py 各收集全部函数的规范化
      AST 哈希（ast.dump 剥 docstring），两集合相交 = 两文件承载同一段逻辑 ⇒ 报
      DUPLICATE。壳不含任何函数定义，指纹为空集，必然零交集。
      边界：v1 平面/立面档案（无 src 对应件的演进前身，见 V1_ARCHIVE）与 v2 的
      残留同体属「现行实现 + 历史快照」，不构成两个可改份，显式点名豁免。
  (b) 壳的转发是 identity -- 用夹具同款 spec_from_file_location 加载每个壳，
      其命名空间里每个非 dunder 名字与 src 件对应名字 `is` 同一对象。
  (c) 壳顶层零 def/class -- 壳文件 AST 顶层没有任何函数/类定义（`__main__`
      委托块除外，块内也只允许一个 raise SystemExit 调用表达式）。

分辨力自证：--baseline HEAD 用 git 里改前版本跑同一判据，必须报出 6 对
DUPLICATE（判据能变红），工作区模式必须全绿（退役生效）。

    python3 AI_agent/logs/experiments/2026-08-25_d1_retirement/verify_no_logic_duplicate.py
    python3 AI_agent/logs/experiments/2026-08-25_d1_retirement/verify_no_logic_duplicate.py --baseline HEAD
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools"

# 退役映射：tools 壳 -> src 权威件（派工单 §一，AST 签名扫描证实恰为 6 对）
RETIRED = {
    "as_drawn_v2.py": "src/agent/reading/as_drawn/as_drawn_v2.py",
    "plan_ink.py": "src/agent/reading/as_drawn/_plan_ink.py",
    "ink_palette.py": "src/agent/reading/as_drawn/pens.py",
    "checks_as_drawn_v2.py": "src/validator/checks/as_drawn.py",
    "reading_grade.py": "src/agent/judge/as_drawn/reading_grade.py",
    "denominator.py": "src/agent/judge/as_drawn/denominator.py",
}

# v1 档案血统（不退役、只点名）：v1 平面/立面链没有 src 对应件（转正只收了 v2 链），
# 其中 _chain_zero_px 与 v2 同体是演进残留。它们是历史快照的一部分（as_drawn.py 里
# 还是嵌套局部函数），没有任何现行链路以它们为源，不存在「改一份忘另一份」的两个
# 可改份。豁免必须显式打印，不许静默。
V1_ARCHIVE = {
    "as_drawn.py": "v1 plan lineage, no src counterpart",
    "as_drawn_elev.py": "v1 elevation lineage, no src counterpart",
}


def _strip_docstrings(node: ast.AST) -> None:
    for child in ast.iter_child_nodes(node):
        _strip_docstrings(child)
    if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        body = node.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]


def logic_fingerprint(source: str) -> set[str]:
    """All function definitions in the file, normalized (docstring-free) AST dumps."""
    tree = ast.parse(source)
    _strip_docstrings(tree)
    ast.fix_missing_locations(tree)
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.add(hashlib.sha256(ast.dump(node).encode()).hexdigest())
    return out


def read_file(path: Path, baseline: str | None) -> str:
    if baseline:
        rel = str(path.relative_to(REPO))
        return subprocess.run(["git", "show", f"{baseline}:{rel}"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout
    return path.read_text()


def check_duplicates(baseline: str | None) -> list[tuple[str, str, int]]:
    """(a): any tools file sharing a function-body hash with any src file."""
    src_files = sorted((REPO / "src").rglob("*.py"))
    src_fps: dict[Path, set[str]] = {}
    for p in src_files:
        try:
            fp = logic_fingerprint(read_file(p, baseline))
        except SyntaxError:
            continue
        if fp:
            src_fps[p] = fp
    dupes = []
    for t in sorted(TOOLS.glob("*.py")):
        tfp = logic_fingerprint(read_file(t, baseline))
        if not tfp:
            continue
        for s, sfp in src_fps.items():
            shared = tfp & sfp
            if shared:
                dupes.append(("/".join(t.parts[-2:]), "/".join(s.parts[3:]), len(shared)))
    return dupes


def split_known_lineage(dupes: list[tuple[str, str, int]]) -> tuple[list, list]:
    """分出「须退役的双份」与「v1 档案血统（点名豁免）」。"""
    real, exempt = [], []
    for t, s, n in dupes:
        (exempt if t.split("/")[-1] in V1_ARCHIVE else real).append((t, s, n))
    return real, exempt


def check_shim_definitions(baseline: str | None) -> list[str]:
    """(c): each retired tools file has zero top-level def/class (shim shape)."""
    problems = []
    for name in RETIRED:
        tree = ast.parse(read_file(TOOLS / name, baseline))
        kinds = [type(n).__name__ for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        if kinds:
            problems.append(f"{name}: top-level definitions {kinds}")
    return problems


def check_identity_forwarding() -> list[str]:
    """(b): every shim namespace entry is the very object from its src module."""
    sys.path.insert(0, str(REPO))
    problems = []
    for shim_name, src_rel in RETIRED.items():
        shim_path = TOOLS / shim_name
        spec = importlib.util.spec_from_file_location(shim_name[:-3], shim_path)
        shim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shim)  # type: ignore[union-attr]
        src_mod = importlib.import_module(src_rel[:-3].replace("/", "."))
        src_names = {k: v for k, v in vars(src_mod).items() if not k.startswith("__")}
        missing = [k for k in src_names if not hasattr(shim, k)]
        not_same = [k for k in src_names if hasattr(shim, k)
                    and getattr(shim, k) is not src_names[k]
                    and not k.endswith(("__module__",))]
        # names holding import machinery (sys/Path/_impl etc.) live only in the shim
        shim_only = [k for k in vars(shim) if not k.startswith("__")
                     and k not in src_names and not k.startswith("_")]
        if missing:
            problems.append(f"{shim_name}: missing forwarded names {missing[:5]}")
        if not_same:
            problems.append(f"{shim_name}: names not identity-forwarded {not_same[:5]}")
        if shim_only:
            problems.append(f"{shim_name}: public names defined by the shim itself {shim_only[:5]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", metavar="REV",
                    help="run the same checks against a git revision (discriminating-power proof)")
    args = ap.parse_args()

    label = f"baseline {args.baseline}" if args.baseline else "working tree"
    print(f"== D-1 no-logic-duplicate gate :: {label} ==")

    dupes = check_duplicates(args.baseline)
    real, exempt = split_known_lineage(dupes)
    print(f"(a) tools<->src shared function-body hashes: {len(dupes)} "
          f"({len(real)} duplicate / {len(exempt)} exempt v1 lineage)")
    for t, s, n in real:
        print(f"    DUPLICATE  {t}  <->  {s}  ({n} shared function bodies)")
    for t, s, n in exempt:
        print(f"    EXEMPT     {t}  <->  {s}  ({n})  -- {V1_ARCHIVE[t.split('/')[-1]]}")

    if args.baseline:
        # 改前必须恰好报出 6 对已知的双份 -- 判据能变红的自证
        known = {t.split("/")[-1] for t, _, _ in real}
        ok = len(real) == len(RETIRED) and known == set(RETIRED)
        print(f"(baseline expectation) exactly the {len(RETIRED)} retired pairs reported: "
              f"{'YES' if ok else 'NO -- gate lacks discriminating power or new dupes exist'}")
        return 0 if ok else 1

    shim_defs = check_shim_definitions(args.baseline)
    print(f"(c) retired shims with top-level def/class: {len(shim_defs)}")
    for p in shim_defs:
        print(f"    NOT-A-SHIM  {p}")

    ident = check_identity_forwarding()
    print(f"(b) shims whose forwarding is not identity: {len(ident)}")
    for p in ident:
        print(f"    NOT-FORWARDED  {p}")

    green = not real and not shim_defs and not ident
    print("VERDICT:", "PASS -- single copy, shims carry no logic" if green
          else "FAIL -- a driftable second copy still exists")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
