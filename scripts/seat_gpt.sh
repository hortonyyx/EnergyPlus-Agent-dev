#!/usr/bin/env bash
# Launch a GPT-family SEAT headless in its own worktree, via the codex CLI —
# the GPT twin of scripts/seat_claude.sh / scripts/seat_glm.sh.
#
#   scripts/seat_gpt.sh <worktree-dir> <prompt-file> [log-file] [model]
#
# Contract mirrors the other two launchers:
#   * cwd for the seat = <worktree-dir>
#   * the prompt is read from a FILE and fed on STDIN — ⛔ never as a trailing
#     positional argument: codex's `-i` is variadic and swallows trailing
#     positionals (AI_agent/guides/codex_execution_protocol.md §1).
#   * background stdin must reach EOF or codex waits forever, hence `< file`.
#   * sandbox = danger-full-access, because `workspace-write` needs bubblewrap
#     and this dev container cannot create user namespaces. Measured 2026-09-02:
#     a review seat launched with workspace-write had EVERY shell command fail
#     with `bwrap: No permissions to create a new namespace`, so it could run
#     no test, verify nothing, and correctly refused to issue a verdict.
#     The container is itself the sandbox here (same reasoning the MCP codex
#     channel already uses per AI_agent/guides/codex_execution_protocol.md).
#   * an empty log mid-run means "still working", ⛔ not "dead" — which is why
#     the kill -0 check below exists.
set -euo pipefail

WORKTREE="${1:?usage: seat_gpt.sh <worktree-dir> <prompt-file> [log-file] [model]}"
PROMPT_FILE="${2:?usage: seat_gpt.sh <worktree-dir> <prompt-file> [log-file] [model]}"
LOG_FILE="${3:-${WORKTREE}/.seat/seat.log}"
MODEL="${4:-gpt-5.6-sol}"

[[ -d "$WORKTREE" ]]    || { echo "no such worktree dir: $WORKTREE" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 2; }
mkdir -p "$(dirname "$LOG_FILE")"

cd "$WORKTREE"
nohup codex exec -m "$MODEL" --sandbox danger-full-access --skip-git-repo-check \
    < "$PROMPT_FILE" > "$LOG_FILE" 2>&1 &
PID=$!
sleep 5
if ! kill -0 "$PID" 2>/dev/null; then
    echo "⛔ seat died within 5s — log says:" >&2
    cat "$LOG_FILE" >&2
    exit 1
fi
echo "gpt seat launched: pid=${PID}  model=${MODEL}  cwd=${WORKTREE}  log=${LOG_FILE}"
