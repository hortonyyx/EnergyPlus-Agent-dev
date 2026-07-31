#!/usr/bin/env python3
"""PreToolUse guard for isolated reading workspaces.

This file is copied into the staging root as ``guard.py``. It is intentionally
stdlib-only because it runs before tool execution.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

GUARD_VERSION = "1"
# S2: tools that write a file. Their target path may only land under out/ or
# requests/ (write protection, F-4/K); everything else under staging is denied.
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
WRITE_TARGET_KEYS = ("file_path", "notebook_path")
WRITE_ALLOWED_DIRS = ("out", "requests")
# S2b r2 (R2-1): the parameter-role classifier is a TOTAL function over keys.
# Exactly two roles exist and every key lands in one of them — there is no third
# "guess by string shape" branch:
#
#   content role  -> not one character is scanned (CONTENT_ROLE_KEYS below)
#   path role     -> UNCONDITIONAL _lexical_check + _path_arg
#   everything else, INCLUDING UNKNOWN KEYS -> path role (fail-closed default)
#
# Rationale (r1 shipped the third branch and it was a real deny->allow
# regression): r1 kept `_looks_like_path(value)` as a pre-gate for every
# non-content string, so a bare, slash-less, extension-less value slipped
# through even when its key was explicitly `file_path` —
# `Read {"file_path": "case_tests"}` went DENY (pre-batch) -> ALLOW, and a bare
# top-level escaping symlink (`{"file_path": "escape"}`, escape -> /etc/passwd)
# was never handed to _path_arg at all. Security must not depend on what a
# string looks like. Making the default path-role means any parameter added by a
# future tool is safe by default; exempting one requires adding it to
# CONTENT_ROLE_KEYS by name, so this hole cannot come back in a fourth shape.
#
# Content role = text-body parameters. Where a write lands is governed by
# _write_targets (the real file_path), so scanning the body adds zero security
# value while the false-positive cost is twice demonstrated live (content
# containing any '/' — a date like 2026/07/31 is enough — plus a domain term
# such as 'grade line'). See evaluate().
CONTENT_ROLE_KEYS = ("content", "old_string", "new_string", "new_source")
# Documentation-only enumeration of the keys that are *known* to carry paths
# (Read/Write/Edit/NotebookEdit/Glob/Grep). It is NOT the gate: _param_role
# returns "path" for anything outside CONTENT_ROLE_KEYS, so this tuple can never
# be the reason a value goes unchecked. It exists so the role table is readable
# and so a test can pin that every listed key really classifies as "path".
# (Glob/Grep also take `pattern`; it reaches the same treatment via the
# fail-closed default, which is why this tuple does not have to be exhaustive.)
PATH_ROLE_KEYS = ("file_path", "notebook_path", "path", "glob")
DENY_TOKENS = (
    "/workspaces/EnergyPlus-Agent-dev",
    "case_tests",
    "test_baseline",
    "gt" + ".json",
    "attempts",
    "judge.json",
    "judge_rubric.md",
    "verdict",
    "grade",
)
COMPOUND_TOKENS = (";", "|", "&&", "||", "`", "$(", ">", "<")
READ_ONLY_COMMANDS = {"ls", "file"}
TOOL_INPUT_EXCERPT_LIMIT = 500


def _staging_root() -> Path:
    return Path(__file__).resolve().parent


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (FileNotFoundError, ValueError):
        return False


def _path_arg(value: str, root: Path) -> Path:
    if value.startswith("~"):
        raise ValueError("home-relative paths are forbidden")
    p = Path(value)
    if not p.is_absolute():
        p = root / p
    resolved = p.resolve(strict=False)
    if not _under(resolved, root):
        raise ValueError(f"path escapes staging: {value}")
    if p.exists():
        target = p.resolve(strict=True)
        if not _under(target, root):
            raise ValueError(f"symlink target escapes staging: {value}")
    return resolved


def _serialized(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _excerpt(value) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    if len(text) <= TOOL_INPUT_EXCERPT_LIMIT:
        return text
    return text[:TOOL_INPUT_EXCERPT_LIMIT] + "...<truncated>"


def _lexical_check(text: str, root: Path) -> tuple[bool, str]:
    if ".." in text:
        return False, "parent traversal token is forbidden"
    if "~" in text:
        return False, "home token is forbidden"
    for token in DENY_TOKENS:
        if token in text:
            return False, f"forbidden token: {token}"
    for part in text.replace('"', " ").replace("'", " ").split():
        if part.startswith("/") and not _under(Path(part), root):
            return False, f"absolute path outside staging: {part}"
    return True, "ok"


def _validate_request_file(path: Path, root: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized = [str(path.resolve(strict=True))]
    for value in _walk_values(data):
        if isinstance(value, str):
            ok, reason = _lexical_check(value, root)
            if not ok:
                raise ValueError(f"request contains forbidden token: {reason}")
            if _looks_like_path(value):
                normalized.append(str(_path_arg(value, root)))
    return sorted(set(normalized))


def _walk_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _walk_items(value, key=None):
    """Yield (key, value) for every leaf, tracking the dict key each leaf sits
    under. List elements inherit their enclosing dict key, so MultiEdit's `edits`
    list recurses into the per-edit dicts and old_string/new_string are picked up
    by name. Used by evaluate() to identify content-role parameters by NAME
    (CONTENT_ROLE_KEYS) — the F-4 r1 fix: a text-body parameter is excluded from
    the path-token scan regardless of whether its text happens to contain '/'."""
    if isinstance(value, dict):
        for k, item in value.items():
            yield from _walk_items(item, k)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_items(item, key)
    else:
        yield key, value


def _param_role(key) -> str:
    """R2-1: TOTAL classifier over parameter keys — returns ``"content"`` or
    ``"path"``, never anything else and never "undecided".

    ``None`` (a leaf that sits under no dict key at all) and every unknown key
    classify as ``"path"``: the default is the *checked* side, so a parameter
    nobody anticipated is scanned rather than skipped. The only way to be
    unscanned is to appear in CONTENT_ROLE_KEYS by name.
    """
    return "content" if key in CONTENT_ROLE_KEYS else "path"


def _looks_like_path(value: str) -> bool:
    """String-shape heuristic. R2-1: this is NO LONGER a gate for tool
    parameters — ``evaluate`` classifies by key role instead. It survives only
    inside :func:`_validate_request_file`, where the CV-probe request JSON has
    no fixed key schema for its non-output values and a shape test is used to
    decide which values additionally get *normalized* (the lexical scan there is
    already unconditional over every string)."""
    return (
        "/" in value
        or value.startswith(".")
        or value.endswith((".json", ".png", ".jpg", ".jpeg", ".txt", ".md"))
    )


def _write_target(tool_input, root: Path) -> Path | None:
    """S2a: extract + resolve the target path of a write tool. Returns the
    resolved target (already checked to be under staging, symlink-resolved) or
    None if no recognizable target key is present (caller denies, fail-closed)."""
    if not isinstance(tool_input, dict):
        return None
    for key in WRITE_TARGET_KEYS:
        raw = tool_input.get(key)
        if isinstance(raw, str) and raw:
            return _path_arg(raw, root)  # raises ValueError on escape / symlink-escape
    return None


def _check_write_target(target: Path, root: Path) -> tuple[bool, str]:
    """S2a: a write tool's resolved target may only land under out/ or requests/.
    `tools/**`, `guard.py`, `isolation_settings.json`, `MANIFEST.json`,
    `skills/**`, `src/**`, `case_data/**`, `prescan/**`, `reference/**` and the
    staging root are all denied — closing the F-4/K escape where a reader could
    overwrite tools/run_cv_probe.py and then execute arbitrary code via the one
    Bash-allowlisted executable."""
    for name in WRITE_ALLOWED_DIRS:
        allowed_root = (root / name).resolve(strict=False)
        try:
            target.relative_to(allowed_root)
            return True, f"allowed write under {name}/"
        except ValueError:
            continue
    return False, "write target must be under out/ or requests/"


def _check_bash(command: str, root: Path) -> tuple[bool, str, list[str]]:
    ok, reason = _lexical_check(command, root)
    if not ok:
        return False, reason, []
    for token in COMPOUND_TOKENS:
        if token in command:
            return False, f"compound shell token forbidden: {token}", []
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return False, f"invalid shell syntax: {exc}", []
    if not parts:
        return False, "empty command", []
    if parts[0] in {"cd", "env"}:
        return False, f"{parts[0]} is forbidden", []
    if parts[0] in READ_ONLY_COMMANDS:
        normalized = []
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            try:
                normalized.append(str(_path_arg(arg, root)))
            except ValueError as exc:
                return False, str(exc), normalized
        return True, "allowed read-only command", normalized
    if Path(parts[0]).name not in {"python", "python3"}:
        return False, f"command is not allowlisted: {parts[0]}", []
    if len(parts) != 4:
        return False, "python command must be exactly: python tools/run_cv_probe.py --request <json>", []
    script = Path(parts[1])
    expected = root / "tools" / "run_cv_probe.py"
    if script.is_absolute():
        if script.resolve(strict=False) != expected.resolve(strict=True):
            return False, "only tools/run_cv_probe.py may be executed", []
    elif parts[1] != "tools/run_cv_probe.py":
        return False, "only tools/run_cv_probe.py may be executed", []
    if parts[2] != "--request":
        return False, "run_cv_probe must use --request", []
    if parts[3] == "-c":
        return False, "python -c is forbidden", []
    try:
        request_path = _path_arg(parts[3], root)
        if request_path.suffix != ".json":
            return False, "request must be a JSON file", [str(request_path)]
        normalized = _validate_request_file(request_path, root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, str(exc), []
    return True, "allowed run_cv_probe request", normalized


def evaluate(payload: dict) -> tuple[str, str, list[str]]:
    root = _staging_root()
    tool = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or {}
    if tool == "Bash":
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            return "deny", "Bash command missing", []
        ok, reason, paths = _check_bash(command, root)
        return ("allow" if ok else "deny"), reason, paths
    # S2a: write protection — Write/Edit/MultiEdit/NotebookEdit may only target
    # out/** or requests/**; everything else (tools/, guard.py, MANIFEST.json,
    # skills/, src/, case_data/, prescan/, reference/, staging root) is denied.
    if tool in WRITE_TOOLS:
        try:
            target = _write_target(tool_input, root)
        except ValueError as exc:
            return "deny", str(exc), []
        if target is None:
            return "deny", f"{tool} requires a file_path/notebook_path", []
        ok, reason = _check_write_target(target, root)
        if not ok:
            return "deny", reason, []
    # S2b r2 (R2-1): judge by PARAMETER ROLE — a TOTAL function, no third
    # branch. Content-role parameters are skipped entirely (not one character
    # scanned); EVERY other key, known or unknown, is treated as a path and gets
    # the lexical scan plus _path_arg UNCONDITIONALLY. No string-shape test
    # stands between a parameter and its check any more: r1's `_looks_like_path`
    # pre-gate let bare `file_path="case_tests"` and a bare extension-less
    # escaping symlink through, a real deny->allow regression.
    #
    # The write protection above (_write_targets / _check_write_target) governs
    # WHERE a write lands, keyed on the real file_path, so skipping the text
    # body adds no risk; the false-positive cost of scanning it is twice
    # demonstrated live (any '/' in the content — a date like 2026/07/31 is
    # enough — plus a domain term such as 'grade line').
    # Bash `command` is unchanged: it still goes through the full strict check.
    paths = []
    for key, value in _walk_items(tool_input):
        if not isinstance(value, str):
            continue
        if _param_role(key) == "content":
            continue
        ok, reason = _lexical_check(value, root)
        if not ok:
            return "deny", reason, paths
        try:
            paths.append(str(_path_arg(value, root)))
        except ValueError as exc:
            return "deny", str(exc), paths
    return "allow", "allowed", sorted(set(paths))


def _append_log(payload: dict, decision: str, reason: str, paths: list[str]) -> None:
    root = _staging_root()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guard_version": GUARD_VERSION,
        "tool": payload.get("tool_name") or payload.get("tool") or "",
        "input_hash": _hash_text(_serialized(payload)),
        "normalized_paths": paths,
        "decision": decision,
        "reason": reason,
    }
    if decision == "deny":
        entry["tool_input_excerpt"] = _excerpt(payload.get("tool_input") or {})
    log_path = root / "access_log.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        payload = {}
        decision, reason, paths = "deny", f"invalid hook JSON: {exc}", []
    else:
        decision, reason, paths = evaluate(payload)
    _append_log(payload, decision, reason, paths)
    if decision == "deny":
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
