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
#
# Roster (probed 2026-09-05, AI_agent/logs/experiments/2026-09-05_model_roster_probe/):
#   gpt-6-astra    TOP tier since 2026-09-05 (user ruling). ⛔ NEEDS codex CLI
#                  >= 0.153 — on 0.144.1 the server answers 400 "requires a
#                  newer version of Codex". This box runs 0.153.4, probed OK.
#   gpt-5.6-sol    second tier — execution reviews / engineering specs. DEFAULT
#                  below, because that is what a seat normally does; pass
#                  gpt-6-astra as $4 for top-tier duty (planning / design review).
#   gpt-5.6-terra  mid tier   ·  gpt-5.6-luna  light tier
# ⛔ `gpt-6`, `gpt-6-codex`, `gpt-6-sol` do NOT exist, and the 400 they return is
# word-for-word the one a made-up id returns — never read that message as
# "the model exists but the plan lacks it" (see the protocol doc §1).
set -euo pipefail

WORKTREE="${1:?usage: seat_gpt.sh <worktree-dir> <prompt-file> [log-file] [model]}"
PROMPT_FILE="${2:?usage: seat_gpt.sh <worktree-dir> <prompt-file> [log-file] [model]}"
LOG_FILE="${3:-${WORKTREE}/.seat/seat.log}"
MODEL="${4:-gpt-5.6-sol}"
# ⭐⭐⭐ 2026-09-06: reasoning effort must be passed EXPLICITLY — the default is
# per-model, not global.  Measured that day: the older gpt-5.x seats all banner
# `reasoning effort: high`, but a `gpt-6-astra` seat launched by this very
# script bannered `low`.  A big construction block at `low` is a silently
# degraded seat: it does not error, it just thinks less.  ⛔ Never rely on the
# default.  Same lesson as `codex exec resume` silently resetting effort to
# `low` (AI_agent memory: codex-resume-resets-reasoning-effort).
EFFORT="${CODEX_EFFORT:-xhigh}"

[[ -d "$WORKTREE" ]]    || { echo "no such worktree dir: $WORKTREE" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 2; }
mkdir -p "$(dirname "$LOG_FILE")"

cd "$WORKTREE"
nohup codex exec -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
    --sandbox danger-full-access --skip-git-repo-check \
    < "$PROMPT_FILE" > "$LOG_FILE" 2>&1 &
PID=$!
sleep 8
if ! kill -0 "$PID" 2>/dev/null; then
    echo "⛔ seat died within 8s — log says:" >&2
    cat "$LOG_FILE" >&2
    exit 1
fi
echo "gpt seat launched: pid=${PID}  model=${MODEL}  effort=${EFFORT}  cwd=${WORKTREE}  log=${LOG_FILE}"
# ⭐ Read the banner back — asking for an effort is not the same as getting it.
BANNER="$(grep -m1 -i 'reasoning effort:' "$LOG_FILE" || true)"
echo "banner says: ${BANNER:-(not printed yet)}"
case "$BANNER" in
    *"$EFFORT"*) ;;
    "")          echo "⚠️  banner not out yet — re-check with: grep -i 'reasoning effort:' $LOG_FILE" >&2 ;;
    *)           echo "⛔ EFFORT MISMATCH — asked ${EFFORT}, got: ${BANNER}" >&2 ;;
esac
