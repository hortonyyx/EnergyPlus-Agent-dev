#!/usr/bin/env bash
# Launch a Claude-family SEAT (construction or review) as a headless background
# session in its own git worktree — the sibling of scripts/glm_code.sh for the
# Claude family, which until 2026-09-02 had no launcher of its own.
#
# Why it exists: the orchestrator must dispatch seats through ONE stable command
# prefix so the host can allowlist exactly that (`Bash(scripts/seat_claude.sh:*)`)
# instead of an ad-hoc `cd … && nohup claude -p …` line that the permission
# classifier cannot tell apart from anything else.
#
#   scripts/seat_claude.sh <worktree-dir> <prompt-file> [log-file]
#
# Contract:
#   * cwd for the seat = <worktree-dir>  (⛔ NEVER the main tree)
#   * the prompt is read from a FILE, never inlined, so it survives quoting
#   * runs detached; headless `-p` prints only when the whole turn ends, so an
#     empty log mid-run means "still working", ⛔ not "dead"
#     (AI_agent/guides/codex_execution_protocol.md §7)
#   * prints the pid and the log path, then returns immediately
#
# ⚠️ Known side effect (CLAUDE.md §5#8.6, NOT a violation by the seat): a
# claude-family session started with a worktree as cwd repoints the shared
# editable install (.pth) at that worktree, because .mcp.json starts its MCP
# server with `uv run` under a global UV_PROJECT_ENVIRONMENT. Restore before any
# authoritative full-suite run in the main tree:
#     (cd <main tree> && uv run python -c "pass")
# The load-bearing invariant is NOT the .pth hash but that the seat's own
# `python -c "import <module> as m; print(m.__file__)"` lands inside its worktree.
set -euo pipefail

WORKTREE="${1:?usage: seat_claude.sh <worktree-dir> <prompt-file> [log-file]}"
PROMPT_FILE="${2:?usage: seat_claude.sh <worktree-dir> <prompt-file> [log-file]}"
LOG_FILE="${3:-${WORKTREE}/.seat/seat.log}"

[[ -d "$WORKTREE" ]]    || { echo "no such worktree dir: $WORKTREE" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 2; }
mkdir -p "$(dirname "$LOG_FILE")"

# ⛔ NOT --dangerously-skip-permissions: this dev container runs as root and the
# CLI refuses that flag under root ("cannot be used with root/sudo privileges").
# Measured 2026-09-02: the seat dies at startup after writing exactly that one
# line — i.e. a DEAD seat and a WORKING seat both leave a near-empty log, so
# ⛔ never infer liveness from log size (hence the kill -0 check below).
# A seat therefore runs on an EXPLICIT tool allowlist instead of a blanket
# bypass. Tools a seat legitimately needs: shell, file edits, search, notes.
cd "$WORKTREE"
nohup claude -p "$(cat "$PROMPT_FILE")" \
    --permission-mode acceptEdits \
    --allowedTools Bash Edit Write Read Grep Glob TodoWrite \
    > "$LOG_FILE" 2>&1 &
PID=$!
sleep 3
if ! kill -0 "$PID" 2>/dev/null; then
    echo "⛔ seat died within 3s — log says:" >&2
    cat "$LOG_FILE" >&2
    exit 1
fi
echo "seat launched: pid=${PID}  cwd=${WORKTREE}  log=${LOG_FILE}"
