#!/usr/bin/env bash
# Launch a GLM-family SEAT headless in its own worktree — the GLM twin of
# scripts/seat_claude.sh. Credentials come from scripts/glm_code.sh, which
# injects them into the child process ONLY (a global ANTHROPIC_BASE_URL would
# silently hijack the orchestrator's own session).
#
#   scripts/seat_glm.sh <worktree-dir> <prompt-file> [log-file]
#
# Same contract and same caveats as seat_claude.sh:
#   * cwd for the seat = <worktree-dir>
#   * headless `-p` prints only when the turn ends ⇒ an empty log means
#     "still working", ⛔ not "dead" — which is why the kill -0 check below
#     exists: measured 2026-09-02, a seat that dies at startup ALSO leaves a
#     near-empty log, so log size can never tell the two apart.
#   * explicit tool allowlist, ⛔ never --dangerously-skip-permissions (this
#     container runs as root and the CLI refuses that flag under root).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREE="${1:?usage: seat_glm.sh <worktree-dir> <prompt-file> [log-file]}"
PROMPT_FILE="${2:?usage: seat_glm.sh <worktree-dir> <prompt-file> [log-file]}"
LOG_FILE="${3:-${WORKTREE}/.seat/seat.log}"

[[ -d "$WORKTREE" ]]    || { echo "no such worktree dir: $WORKTREE" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 2; }
mkdir -p "$(dirname "$LOG_FILE")"

cd "$WORKTREE"
nohup bash "$REPO_ROOT/scripts/glm_code.sh" \
    -p "$(cat "$PROMPT_FILE")" \
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
echo "glm seat launched: pid=${PID}  cwd=${WORKTREE}  log=${LOG_FILE}"
