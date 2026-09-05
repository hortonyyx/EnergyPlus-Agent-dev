#!/usr/bin/env bash
# Launch a Claude Code session backed by DeepSeek — the 4th model family seat
# alongside Claude / GPT / GLM. Mirrors scripts/glm_code.sh.
#
# Credentials are injected into THIS SUBSHELL ONLY and are never exported
# globally: a global ANTHROPIC_BASE_URL would silently hijack the primary
# Claude Code session onto DeepSeek.
#
#   scripts/deepseek_code.sh                        # interactive session, cwd = here
#   scripts/deepseek_code.sh -p "review this diff"  # one-shot
#
# Roster (probed 2026-08-16 against https://api.deepseek.com/models — these two
# are the ONLY ids the API accepts):
#   deepseek-v4-pro    GA since 2026-08-13. Flagship. Default seat model.
#   deepseek-v4-flash  GA since 2026-07-31. Light tier / small-fast slot.
# The `-preview` ids are RETIRED (the API rejects them by name), and the legacy
# aliases `deepseek-chat` / `deepseek-reasoner` now silently resolve to
# **v4-flash**, not v4-pro — never use them, you would be quietly downgraded.
#
#   DEEPSEEK_MODEL=deepseek-v4-flash scripts/deepseek_code.sh   # light seat
#
# ⛔ BILLING: DeepSeek is pay-as-you-go off the account balance, NOT a
# subscription like the Claude / GPT / GLM seats — every token here spends real
# money and a long session can drain the balance mid-run (the downstream
# pipeline in src/configs/llm.yaml eats the SAME balance, so an exhausted
# balance breaks e2e runs too). Check before dispatching a long batch:
#   curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $DEEPSEEK_API_KEY"
# Off-peak tokens cost half of peak (peak/off-peak pricing effective
# 16:00 UTC 2026-08-16) — schedule long batches off-peak.
#
# Config lives in .env (gitignored): DEEPSEEK_API_KEY (required);
# DEEPSEEK_ANTHROPIC_BASE_URL (optional, defaults below).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
# shellcheck disable=SC1091
. "$REPO_ROOT/.env"
set +a

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY missing from .env}"

exec env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL="${DEEPSEEK_ANTHROPIC_BASE_URL:-https://api.deepseek.com/anthropic}" \
  ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" \
  ANTHROPIC_MODEL="${DEEPSEEK_MODEL:-deepseek-v4-pro}" \
  ANTHROPIC_SMALL_FAST_MODEL="${DEEPSEEK_SMALL_MODEL:-deepseek-v4-flash}" \
  claude "$@"
