#!/usr/bin/env python3
"""PreToolUse guard for isolated reading workspaces.

This file is copied into the staging root as ``guard.py``. It is intentionally
stdlib-only because it runs before tool execution.
"""

from __future__ import annotations

import hashlib
import json
import re
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
# R2-2: request parameters the CV helper uses as an OUTPUT LANDING POINT.
# Enumerated by auditing every tool in run_cv_probe.ALLOWED_TOOLS:
#   crop_zoom / wall_line_profiler / storey_line_profiler / px_m_calibrator /
#   window_cc_detector / overlay_logger -> allocate_sidecar_path(out_dir, ...)
#   prescan-plan / prescan-elevation    -> evidence_dir(out_dir, ...)/label
# `out_dir` is therefore the ONLY output-role parameter; every other file the
# helper writes (crop png, overlay png, candidates.json, sidecar json) is derived
# from it. The two name components that also shape the landing path are pinned to
# non-traversing tokens by their own regexes and cannot escape out_dir:
# `sidecar_name` (sidecar.py `_SIDECAR_NAME_RE`) and `label` (recipes.py
# `_PRESCAN_LABEL_RE`). `image` / `anchors_json` / `candidates_json` are inputs
# and keep the existing "inside staging" rule.
REQUEST_OUTPUT_ROLE_KEYS = ("out_dir",)
# P1-1: cv_probe parameters whose value is a FILE PATH INPUT, classified BY NAME.
# Mirrors run_cv_probe.PATH_KEYS minus its output-role member. Name-based, not
# shape-based, for the R2-1 reason: `--image escape` (a bare, slash-less,
# extension-less symlink to /etc/passwd) IS a path, and `_looks_like_path` says
# it is not. Before this batch that value never reached `_path_arg` on either
# invocation form; it now does on both, since they share `_validate_probe_params`.
# The `_looks_like_path` fallback survives only for keys nobody enumerated, which
# is all the request JSON's free-form nesting can offer.
PROBE_PATH_ROLE_KEYS = ("image", "anchors_json", "candidates_json")
# P1-1: the parameter allowlist for the DIRECT (one-call) probe form
#   python tools/run_cv_probe.py --tool <name> --image <path> [--key value ...]
# which exists so a measurement costs ONE tool call instead of two (Write the
# request JSON, then Bash it). The 07-30 run paid that 2x tax on exactly the
# action this project's reading methodology depends on: probe invocations fell
# 19 -> 8 and reading quality collapsed with them.
#
# The list is ENUMERATED FROM scripts/tool_scripts/cv_probe.py (staged as
# tools/cv_probe.py) — every subparser's options, read off the file, not guessed:
#   _common() on all eight tools     --image --out-dir --recipe --bbox --scale
#                                    --sidecar-name
#   wall_line_profiler               --axis
#   px_m_calibrator                  --anchors-json --residual-warn-px
#                                    --residual-warn-m
#   window_cc_detector               --min-area --min-width --min-height
#                                    --max-width --max-height --min-aspect
#                                    --max-aspect --merge-gap
#                                    --merge-overlap-ratio --merge-iou
#   overlay_logger                   --candidates-json
#   prescan-plan / prescan-elevation --capability-profile --no-cc
#                                    --min-strength --min-line-len-px --label
# plus `--tool`, which selects the subparser (it is the request JSON's top-level
# "tool" field).
#
# Keys are canonicalized to the request JSON's underscore spelling before the
# lookup, so `--out-dir` and `--out_dir` are the SAME enumerated key and get the
# identical role treatment — there is no spelling under which a key escapes its
# role. An unlisted key is DENIED (fail-closed), which is what makes an
# enumeration safe: this list never has to anticipate anything, and a future
# cv_probe option is simply refused until it is added here on purpose.
#
# `--no-cc` is a store_true flag in cv_probe. The direct form still spells it as
# a PAIR (`--no-cc true`) because "strictly paired" is what makes the parser
# unambiguous; tools/run_cv_probe.py converts the pair back into the flag.
PROBE_DIRECT_PARAM_KEYS = (
    "tool",
    "image",
    "out_dir",
    "recipe",
    "bbox",
    "scale",
    "sidecar_name",
    "axis",
    "anchors_json",
    "residual_warn_px",
    "residual_warn_m",
    "min_area",
    "min_width",
    "min_height",
    "max_width",
    "max_height",
    "min_aspect",
    "max_aspect",
    "merge_gap",
    "merge_overlap_ratio",
    "merge_iou",
    "candidates_json",
    "capability_profile",
    "no_cc",
    "min_strength",
    "min_line_len_px",
    "label",
)
# The direct form is not optional about WHAT it runs and WHAT it runs on; both
# are required by cv_probe itself (`--tool` selects the subparser, `--image` is
# `required=True` in `_common`). Requiring them here also keeps the degenerate
# `python tools/run_cv_probe.py` (denied before this batch by the length rule)
# denied afterwards, so the deny->allow surface is exactly the authorized form.
PROBE_DIRECT_REQUIRED_KEYS = ("tool", "image")
# This is not an authorization list (the wrapper's ALLOWED_TOOLS remains that
# policy owner); it lets a bare, known tool name receive the exact mechanical
# repair instead of a generic pairing lecture.
# 2026-08-15: prescan-plan / prescan-elevation dropped in step with
# run_cv_probe.ALLOWED_TOOLS. Leaving them here would keep advertising a tool the
# wrapper now refuses, which is the "mechanical repair" hint working against the
# withdrawal.
PROBE_TOOL_NAMES = frozenset(
    {
        "crop_zoom",
        "wall_line_profiler",
        "storey_line_profiler",
        "px_m_calibrator",
        "window_cc_detector",
        "overlay_logger",
    }
)
# L1: one batch covers a normal measurement sweep (the good reference run used
# 19 probes) while refusing unbounded work.  The wrapper imports the batch
# envelope parser below from this module, so the hook and the executable cannot
# drift on the bound, request-id syntax, or envelope shape.
MAX_PROBE_BATCH_SIZE = 32
_BATCH_TEMPLATE = (
    '{"requests":[{"id":"calibrate_x","tool":"px_m_calibrator","args":'
    '{"image":"case_data/<image>.png","out_dir":"out/cv","anchors_json":'
    '[{"axis":"x","px_a":12345,"px_b":67890,"value_m":12.345,'
    '"dimension_ref":"example_span"}]}}]}'
)
PROBE_BATCH_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
# Helper output must resolve into the WRITABLE ROOT, not merely "somewhere inside
# staging" — the latter let a legal-looking request make the one allowlisted
# executable write real files under `tools/**` (sol MAJOR-1, reproduced by the
# controller). `requests/` holds the request file itself and is never an output
# root. run_cv_probe.py enforces the identical rule so there is no guard/wrapper
# policy gap.
OUTPUT_ROOT_DIR = "out"
# S2b r2 (R2-1): the parameter-role classifier is a TOTAL function over keys.
# Exactly two roles exist and every key lands in one of them — there is no third
# "guess by string shape" branch:
#
#   content role  -> not one character is scanned (CONTENT_ROLE_KEYS below, plus
#                    TOOL_FREE_TEXT_KEYS for names that are free text under one
#                    tool and a path under another)
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
# Content role = parameters that carry FREE TEXT rather than a path. Where a
# write lands is governed by _sole_write_target (the real file_path), so scanning
# free text adds zero security value while the false-positive cost is repeatedly
# demonstrated live (text containing any '/' — a date like 2026/07/31 is enough —
# plus a domain term such as 'grade line'). See evaluate().
#
# R3-1: r2 shipped only the four Write/Edit/NotebookEdit text BODIES here, so the
# fail-closed default relocated the very friction this batch exists to remove:
# `TodoWrite {"activeForm": "Marking the grade line"}` and
# `Grep {"pattern": "z ~ 0.0"}` were both refused, with zero safety value. The
# enumeration below is derived, not guessed:
#
#   (a) isolation._write_settings permits exactly Read / Write / Edit / Bash
#       (plus the always-available no-permission tools Glob / Grep / TodoWrite;
#       WebFetch / WebSearch / Agent / Task / mcp__* are denied outright).
#   (b) The 07-30 run's access_log.jsonl (attempt 003, 82 entries) shows the
#       reader really used Read (37) / Bash (26) / Write (18) / Edit (1); the log
#       records parameter names only on deny entries, where `command` and
#       `content` appear. Both of that run's non-Bash refusal reasons
#       ("forbidden token: grade", "home token is forbidden") were free-text
#       parameters, never paths.
#
# Union of (a) and (b), keeping only parameters that are free text under EVERY
# tool that uses the name — so exempting the name can never unscan a path:
#   activeForm  TodoWrite       description  Bash / Agent
#   prompt      Agent/WebFetch  query        WebSearch
# Bash `command` is deliberately absent: it stays under the full strict check.
# A name that is free text under one tool but a path under another (Grep's regex
# `pattern` vs Glob's path `pattern`) does NOT belong here — see
# TOOL_FREE_TEXT_KEYS.
CONTENT_ROLE_KEYS = (
    "content",
    "old_string",
    "new_string",
    "new_source",
    "activeForm",
    "description",
    "prompt",
    "query",
)
# R3-1: exemptions that hold for ONE tool only. `pattern` is a regex for Grep
# (free text: `wall_..[0-9]`, `z ~ 0.0`) but a path glob for Glob, where
# a `**/`-prefixed answer-file name must stay denied. Classifying by key name
# alone cannot separate
# them, so the tool name participates in the decision. Fail-closed as before: an
# unlisted tool gets no tool-scoped exemption at all, only the global table
# above, so an unanticipated tool that happens to take a `pattern` is scanned.
TOOL_FREE_TEXT_KEYS = {
    "Grep": ("pattern",),
}
# Documentation-only enumeration of the keys that are *known* to carry paths
# (Read/Write/Edit/NotebookEdit/Glob/Grep). It is NOT the gate: _param_role
# returns "path" for anything outside CONTENT_ROLE_KEYS, so this tuple can never
# be the reason a value goes unchecked. It exists so the role table is readable
# and so a test can pin that every listed key really classifies as "path".
# (Glob also takes `pattern`; it reaches the same treatment via the fail-closed
# default — R3-1 exempts `pattern` for Grep only — which is why this tuple does
# not have to be exhaustive.)
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


def _validate_probe_params(items, root: Path) -> list[str]:
    """Validate CV-probe parameters *by parameter role* (R2-2).

    THE single implementation, shared by both invocation forms (P1-1): the
    request-JSON path feeds it ``_walk_items(data)``, the direct-argument path
    feeds it the parsed ``--key value`` pairs. Neither form gets its own copy of
    the rule, so the writable-root constraint on output-role parameters cannot
    drift between them — which is the whole reason the direct form is allowed to
    exist at all.

    Three roles, decided by KEY NAME first and only then by string shape:

    * output role (REQUEST_OUTPUT_ROLE_KEYS) — must resolve into the writable
      root via :func:`_check_output_target`. "Still inside staging" is not
      enough, because the helper these parameters drive writes real files
      wherever that parameter points.
    * path role (PROBE_PATH_ROLE_KEYS) — unconditional :func:`_path_arg`,
      whatever the value looks like.
    * everything else — :func:`_looks_like_path` decides whether the value is
      additionally normalized. Only keys nobody enumerated land here.

    Every string, in every role, gets the unconditional lexical scan first.
    """
    normalized = []
    for key, value in items:
        if not isinstance(value, str):
            continue
        ok, reason = _lexical_check(value, root)
        if not ok:
            raise ValueError(f"probe parameters contain a forbidden token: {reason}")
        if key in REQUEST_OUTPUT_ROLE_KEYS:
            resolved = _path_arg(value, root)
            ok, reason = _check_output_target(resolved, root)
            if not ok:
                raise ValueError(f"{reason}: {value}")
            normalized.append(str(resolved))
        elif key in PROBE_PATH_ROLE_KEYS or _looks_like_path(value):
            normalized.append(str(_path_arg(value, root)))
    return normalized


def _validate_probe_request_data(data, root: Path) -> list[str]:
    """Validate one probe request's values through the shared role policy.

    Both legacy ``--request`` and every entry of ``--batch`` call this exact
    function.  Keeping the loop outside the validator is intentional: there is
    one security policy for one request, applied N times before a batch is
    authorized, rather than a second batch-specific approximation.
    """
    return _validate_probe_params(_walk_items(data), root)


def _validate_request_file(path: Path, root: Path) -> list[str]:
    """Form A (`--request <json>`): unchanged behaviour, now expressed on top of
    the shared :func:`_validate_probe_params`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized = [str(path.resolve(strict=True))]
    normalized.extend(_validate_probe_request_data(data, root))
    return sorted(set(normalized))


def parse_probe_batch(data) -> list[tuple[str, dict]]:
    """Parse the bounded batch envelope shared by the hook and wrapper.

    A batch entry is the ordinary single-request object plus a stable ``id``::

        {"requests": [{"id": "north_cols", "tool": "...", "args": {...}}]}

    The envelope is deliberately exact and IDs are unique, short filesystem-
    neutral tokens.  This parser does *not* replace request validation; callers
    must pass every returned request to the same validator/executor used for a
    single request.
    """
    if not isinstance(data, dict) or set(data) != {"requests"}:
        raise ValueError(
            "probe batch must be an object containing only 'requests'; "
            f"use: {_BATCH_TEMPLATE}"
        )
    entries = data["requests"]
    if not isinstance(entries, list):
        raise ValueError(f"probe batch requests must be an array; use: {_BATCH_TEMPLATE}")
    if not entries:
        raise ValueError(f"probe batch must contain at least one request; use: {_BATCH_TEMPLATE}")
    if len(entries) > MAX_PROBE_BATCH_SIZE:
        raise ValueError(
            f"probe batch has {len(entries)} requests; maximum is "
            f"{MAX_PROBE_BATCH_SIZE}; use: {_BATCH_TEMPLATE}"
        )

    parsed = []
    seen_ids = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != {"id", "tool", "args"}:
            raise ValueError(
                f"probe batch request {index} must contain exactly id, tool, args; "
                "use: {\"id\":\"calibrate_x\",\"tool\":\"px_m_calibrator\","
                "\"args\":{\"image\":\"case_data/<image>.png\",\"out_dir\":\"out/cv\","
                "\"anchors_json\":[{\"axis\":\"x\",\"px_a\":12345,\"px_b\":67890,"
                "\"value_m\":12.345,\"dimension_ref\":\"example_span\"}]}}"
            )
        request_id = entry["id"]
        if not isinstance(request_id, str) or not PROBE_BATCH_ID_RE.fullmatch(
            request_id
        ):
            raise ValueError(
                f"probe batch request {index} id must match "
                f"{PROBE_BATCH_ID_RE.pattern}; use id \"calibrate_x\" as in: {_BATCH_TEMPLATE}"
            )
        if request_id in seen_ids:
            raise ValueError(
                f"duplicate probe batch request id: {request_id}; "
                f"use unique IDs as in: {_BATCH_TEMPLATE}"
            )
        seen_ids.add(request_id)
        parsed.append((request_id, {"tool": entry["tool"], "args": entry["args"]}))
    return parsed


def _validate_batch_file(path: Path, root: Path) -> list[str]:
    """Validate an entire batch before the hook authorizes any execution."""
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized = [str(path.resolve(strict=True))]
    for _request_id, request in parse_probe_batch(data):
        # The security-critical reuse: exactly the single-request validator.
        normalized.extend(_validate_probe_request_data(request, root))
    return sorted(set(normalized))


def _parse_direct_probe_args(args: list[str], root: Path) -> list[str]:
    """Form B (P1-1): STRICT parser for the direct one-call probe form.

    ``args`` is everything after ``python tools/run_cv_probe.py``. This REPLACES
    the old "the command must be exactly four tokens" rule; it is not a relaxed
    token count. Rules, in order, all fail-closed:

    * strictly paired ``--key value``. A bare positional argument, a repeated
      key, or a ``--key`` whose value slot is missing (end of argv, or another
      ``--key`` sitting there) is refused. The parser never guesses which token
      was meant as what — ambiguity is a denial, not a heuristic.
    * every key must be in :data:`PROBE_DIRECT_PARAM_KEYS`; unknown keys are
      denied. ``--request`` is called out by name only to give a useful reason.
    * ``--tool`` and ``--image`` must both be present.
    * every value goes through :func:`_validate_probe_params` — the SAME rule
      the request-JSON path applies. So the lexical scan is unconditional and
      ``--out-dir`` still has to land in the writable root.
    """
    pairs = []
    seen = set()
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("--"):
            hint = (
                f"; tool names go after --tool; did you mean --tool {token}?"
                if token in PROBE_TOOL_NAMES
                else "; use only --key value pairs (start with --tool <tool>)"
            )
            raise ValueError(
                "probe arguments must be paired --key value; "
                f"unexpected bare argument: {token}{hint}"
            )
        spelling = token[2:]
        key = spelling.replace("-", "_")
        if not key:
            raise ValueError("probe parameter name is empty")
        if key == "request":
            raise ValueError(
                "the --request form must be exactly: "
                "python tools/run_cv_probe.py --request <json>"
            )
        if key not in PROBE_DIRECT_PARAM_KEYS:
            allowed = " ".join(
                "--" + name.replace("_", "-") for name in PROBE_DIRECT_PARAM_KEYS
            )
            raise ValueError(f"unknown probe parameter --{spelling}; allowed: {allowed}")
        if key in seen:
            raise ValueError(f"repeated probe parameter --{spelling}")
        if index + 1 >= len(args) or args[index + 1].startswith("--"):
            raise ValueError(
                f"probe parameter --{spelling} is missing its value; "
                f"write --{spelling} <value>"
            )
        seen.add(key)
        pairs.append((key, args[index + 1]))
        index += 2
    missing = [key for key in PROBE_DIRECT_REQUIRED_KEYS if key not in seen]
    if missing:
        raise ValueError(
            "direct probe form requires "
            + " ".join("--" + name.replace("_", "-") for name in missing)
        )
    return sorted(set(_validate_probe_params(pairs, root)))


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


def _param_role(key, tool: str) -> str:
    """R2-1: TOTAL classifier over parameter keys — returns ``"content"`` or
    ``"path"``, never anything else and never "undecided".

    ``None`` (a leaf that sits under no dict key at all) and every unknown key
    classify as ``"path"``: the default is the *checked* side, so a parameter
    nobody anticipated is scanned rather than skipped. R3-1 does not touch that
    default; it only moves named free-text parameters onto the exempt side. The
    only two ways to be unscanned are to appear in CONTENT_ROLE_KEYS by name, or
    in TOOL_FREE_TEXT_KEYS under this exact ``tool``.
    """
    if key in CONTENT_ROLE_KEYS:
        return "content"
    if key in TOOL_FREE_TEXT_KEYS.get(tool, ()):
        return "content"
    return "path"


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


def _sole_write_target(tool_input, root: Path) -> Path | None:
    """S2a / R2-5: resolve THE target path of a write tool.

    Returns the single present target key's resolved path (already checked to be
    under staging and symlink-resolved), or ``None`` when no target key is
    present (caller denies, fail-closed).

    R2-5: the previous version returned the FIRST match in WRITE_TARGET_KEYS
    order, so a decoy `file_path: "out/decoy.txt"` masked the real
    `notebook_path: "tools/protected.ipynb"` and the call was allowed. Two
    different target keys in one call is inherently ambiguous about where the
    write lands, so it is refused outright rather than guessed; a single present
    key is validated as before. Raises ValueError, which the caller turns into a
    deny.

    R3-3 NIT-3: r2 returned a list and the caller looped over it, but the raise
    above means the list can never hold more than one element — the loop's
    multi-element branch was unreachable by construction and read as if two rules
    ran at once. The signature now states what the code actually guarantees: at
    most one target, or a refusal.
    """
    if not isinstance(tool_input, dict):
        return None
    present = [
        key
        for key in WRITE_TARGET_KEYS
        if isinstance(tool_input.get(key), str) and tool_input.get(key)
    ]
    if len(present) > 1:
        raise ValueError(
            "ambiguous write target: more than one target key present "
            f"({', '.join(present)}) — refusing rather than guessing which one lands"
        )
    if not present:
        return None
    # raises ValueError on escape / symlink-escape
    return _path_arg(tool_input[present[0]], root)


def _check_write_target(target: Path, root: Path) -> tuple[bool, str]:
    """S2a: a write tool's resolved target may only land under out/ or requests/.
    `tools/**`, `guard.py`, `isolation_settings.json`, `MANIFEST.json`,
    `skills/**`, `src/**`, `case_data/**`, `prescan/**`, `reference/**` and the
    staging root are all denied — closing the F-4/K escape where a reader could
    overwrite tools/run_cv_probe.py and then execute arbitrary code via the one
    Bash-allowlisted executable."""
    for name in WRITE_ALLOWED_DIRS:
        try:
            allowed = writable_root(root, name)
        except ValueError as exc:
            # R2-3 fail-closed: a tampered root refuses the CALL; we do not fall
            # through to the next root and we do not "skip" it.
            return False, str(exc)
        try:
            target.relative_to(allowed)
            return True, f"allowed write under {name}/"
        except ValueError:
            continue
    return False, "write target must be under out/ or requests/"


def writable_root(root: Path, name: str) -> Path:
    """The single definition of "a root the reader may write into".

    PUBLIC ON PURPOSE (R3-2). Three call sites go through this one function: the
    Write/Edit target check, the CV-request output check, and — by importing this
    module — ``tools/run_cv_probe.py``. The wrapper used to carry its own
    ``(root / name).resolve(strict=False)``, i.e. exactly the definition R2-3
    removed from here, so the two enforcement points disagreed: with
    ``out -> tools`` pre-seeded the hook refused while the wrapper, invoked
    directly, really wrote six entries under ``tools/**``. There is now one
    implementation and no second policy to drift.

    R2-3: the root is *pinned*, not resolved. Deriving the authorized set by
    resolving a path the reader could replace is backwards — if ``out`` is itself
    a symlink to ``tools``, ``(root/"out").resolve()`` yields ``tools`` and the
    protected directory becomes the allowed root, so writing ``out/run_cv_probe.py``
    was allowed (sol MAJOR-3). A writable root must therefore be a real directory
    that resolves to its own literal path inside staging; anything else raises and
    the caller denies the whole call.
    """
    path = root / name
    if path.is_symlink() or not path.is_dir():
        raise ValueError(
            f"writable root {name}/ must be a real directory inside staging "
            "(symlinked or missing root: refusing the call)"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or not _under(resolved, root):
        raise ValueError(
            f"writable root {name}/ must resolve to its own path inside staging "
            "(refusing the call)"
        )
    return path


def _assert_writable_roots(root: Path) -> None:
    """R2-3: re-validate every writable root on every decision. Runs before any
    tool is judged, so a tampered root denies even a read — the authorization set
    itself is untrustworthy at that point."""
    for name in WRITE_ALLOWED_DIRS:
        writable_root(root, name)


def _check_output_target(target: Path, root: Path) -> tuple[bool, str]:
    """R2-2: a CV-request output-role parameter must land in the writable root.

    Same bar as a direct Write, minus `requests/` (that dir carries the request
    file, not helper output). Without this, `{"out_dir": "tools"}` passed the
    hook, the helper ran, and three files really appeared under `tools/**`."""
    try:
        allowed = writable_root(root, OUTPUT_ROOT_DIR)
    except ValueError as exc:
        return False, str(exc)  # R2-3 fail-closed
    try:
        target.relative_to(allowed)
        return True, f"allowed output under {OUTPUT_ROOT_DIR}/"
    except ValueError:
        return False, f"request output path must land under {OUTPUT_ROOT_DIR}/"


def _check_bash(command: str, root: Path) -> tuple[bool, str, list[str]]:
    ok, reason = _lexical_check(command, root)
    if not ok:
        return False, reason, []
    for token in COMPOUND_TOKENS:
        if token in command:
            if token == "|":
                return False, (
                    "compound shell token forbidden: |; remove the pipe and rerun "
                    "the same python tools/run_cv_probe.py command directly"
                ), []
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
        if parts[0] == "mkdir":
            return False, (
                "command is not allowlisted: mkdir; out/ and requests/ are already "
                "provisioned — write requests/<name>.json or run the direct --tool form"
            ), []
        if parts[0] == "find":
            return False, (
                "command is not allowlisted: find; use ls case_data to list the "
                "copied input images"
            ), []
        return False, f"command is not allowlisted: {parts[0]}", []
    # P1-1: the "exactly four tokens" rule is gone, replaced by the strict
    # argument parser below. The checks it used to absorb are now explicit and
    # run in their own right, so nothing that used to be denied by the token
    # count is denied only by accident:
    #   `python`            -> no script argument at all
    #   `python -c '...'`   -> named check, kept ahead of the script check so the
    #                          reason stays precise
    #   `python other.py …` -> the argv[1] identity check, unchanged
    if len(parts) < 2:
        return False, "python must run tools/run_cv_probe.py", []
    if parts[1] == "-c":
        return False, "python -c is forbidden", []
    script = Path(parts[1])
    expected = root / "tools" / "run_cv_probe.py"
    if script.is_absolute():
        if script.resolve(strict=False) != expected.resolve(strict=True):
            return False, "only tools/run_cv_probe.py may be executed", []
    elif parts[1] != "tools/run_cv_probe.py":
        return False, "only tools/run_cv_probe.py may be executed", []
    # The help form is explicitly narrow: it runs only the one staged wrapper,
    # receives no file paths or shell syntax, and changes no state.
    if len(parts) == 3 and parts[2] == "--help":
        return True, "allowed run_cv_probe help", []
    # Form A — `--request <json>`, byte-for-byte the previous behaviour.
    if len(parts) == 4 and parts[2] == "--request":
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
    # Form C — a bounded batch file.  The whole file is parsed and every inner
    # request passes the exact Form-A validator before this call is authorized;
    # one bad entry therefore prevents the wrapper from starting at all.
    if len(parts) == 4 and parts[2] == "--batch":
        try:
            batch_path = _path_arg(parts[3], root)
            if batch_path.suffix != ".json":
                return False, "batch must be a JSON file", [str(batch_path)]
            normalized = _validate_batch_file(batch_path, root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return False, str(exc), []
        return True, "allowed run_cv_probe batch", normalized
    # Form B — direct `--key value` arguments (P1-1).
    try:
        normalized = _parse_direct_probe_args(parts[2:], root)
    except (OSError, ValueError) as exc:
        return False, str(exc), []
    return True, "allowed run_cv_probe direct arguments", normalized


def evaluate(payload: dict) -> tuple[str, str, list[str]]:
    root = _staging_root()
    # R2-3: the authorization set must be trustworthy before anything is judged.
    # If a writable root is not a real directory resolving to itself inside
    # staging, refuse this call outright — including reads.
    try:
        _assert_writable_roots(root)
    except ValueError as exc:
        return "deny", str(exc), []
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
            target = _sole_write_target(tool_input, root)
        except ValueError as exc:  # ambiguous target, or escape/symlink-escape
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
    # The write protection above (_sole_write_target / _check_write_target)
    # governs WHERE a write lands, keyed on the real file_path, so skipping free
    # text adds no risk; the false-positive cost of scanning it is repeatedly
    # demonstrated live (any '/' in the content — a date like 2026/07/31 is
    # enough — plus a domain term such as 'grade line').
    # R3-1: the exempt set is now the named free-text parameters of the tools
    # this reader can actually reach, not just Write/Edit bodies — otherwise the
    # fail-closed default simply relocates the F-4 friction onto TodoWrite's
    # activeForm and Grep's pattern. The DEFAULT IS UNCHANGED: every unlisted
    # key, known or unknown, is still scanned unconditionally.
    # Bash `command` is unchanged: it still goes through the full strict check.
    paths = []
    for key, value in _walk_items(tool_input):
        if not isinstance(value, str):
            continue
        if _param_role(key, tool) == "content":
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
