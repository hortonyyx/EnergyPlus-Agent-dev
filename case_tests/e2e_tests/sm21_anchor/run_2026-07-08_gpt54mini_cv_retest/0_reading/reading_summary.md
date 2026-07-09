# reading_summary — run_2026-07-08_gpt54mini_cv_retest (sm21_anchor)

**GPT-5.4-mini CV-toolbox CROSS-TEST — 结论 = 阳性满分带（迁移性成立）**

## Scores (J0, gt对账权威 score_reading_vs_gt + elevation_score, judge-side default tol)

| metric | gpt-5.4-mini | Haiku 07-07 | Sonnet 5 base | gpt54mini 06-23 (no toolbox) |
|---|---|---|---|---|
| plan walls | **9/9 · max offset 0.0m** | 9/9 · 0.0m | 9/9 · 0.0m | 2f missing 1 partition (6 zones) |
| plan windows | **6/7** | 7/7 | 7/7 | — |
| elevation windows | **15/15 complete · miss 0 · extra 0** | 15/15 | 15/15 | South-F2 4 windows merged→2 |
| oversplit (extra walls) | **0** | 0 | 0 | + |
| tokens/case (6 imgs) | ~0.90M | 0.4–0.65M | — | — |

Elevation per facade×floor: North 3/3+2/2 · **South 3/3+4/4** · East 1/1+1/1 · West 0/0+1/1 — all complete.
Plan: 1f walls 4/4·0.0m windows 2/3 (one S window centre off 0.53m) · 2f walls 5/5·0.0m windows 4/4 (all Δ+0.0).

## Verdicts

- **Migration holds — the CV-toolbox recipe is NOT Haiku-specific.** gpt-5.4-mini reaches the same
  perfect band as Haiku 4.5 + toolbox and the Sonnet 5 ceiling on walls (9/9·0.0m), elevation
  windows (15/15 complete), and oversplit (0). The only gap is one plan window (6/7 vs 7/7).
- **Both 06-23 no-toolbox failure points FIXED**: (1) South-F2 4-windows-merged-to-2 → now 4/4
  complete; (2) 2f missing partition (6 zones) → now walls 5/5·0.0m (7 zones). The window CC +
  chain-value dual channel hit exactly the points the handoff predicted.
- **E-batch固化 VERIFIED on a new model**: the spawn prompt did NOT contain measure-before-draw;
  gpt-5.4-mini read cv_toolbox.md (self-declared required) and measured everything with cv_probe
  (13 tool calls on the pilot; dozens per image in batch). The prescan-pre-staged + skill-固化
  E3/E1 flow transfers.
- **Efficiency**: ~0.90M tokens/case, ~1.5x the Haiku baseline (0.4–0.65M) — weak model does more
  tool trial-and-error (East 72 tool calls). Prescan pre-staging saved the prescan round-trips but
  gpt-5.4-mini's per-image search cost is higher.

## Provenance / method

- Reading VLM = gpt-5.4-mini via codex CLI (`codex exec -m gpt-5.4-mini -i <png>`, OpenAI provider;
  prompt via stdin — the `-i` variadic flag eats a trailing positional prompt). Vision pre-verified.
- Isolation = clean-room staging (spawn_isolated_reader build) at repo-external /tmp/ep_iso_gpt54mini;
  gt / prior attempts / judge notes / other runs PHYSICALLY EXCLUDED, cwd=staging. Codex-side has NO
  Claude Code guard layer (weaker than a claude -p sub-agent) but gt is physically outside staging.
- E3 prescan pre-staged: 6 candidates.json + overlays computed before spawn, copied into staging.
- Scaffold = HEAD ebddada, 0_reading skill 0e795c74e854e5a5 / reading src cb5c68bf1861d591 — the
  E-batch new baseline (differs from Haiku 07-07's d4c8a9bf/02eecb89 = prescan宏工具+纪律固化).
- pilot(1f) reviewed by orchestrator (Opus) before batch; batch = 5 parallel codex sessions.
- Orchestrator/judge② = Claude Opus 4.8. Authoritative verdict = deterministic gt scorer.

## Residual

- 1f plan window centre off 0.53m (6/7) — single weak-model perception wobble, not a recipe failure.
- Legacy `facade_axis_note`/`scale_origin` fields appear in outputs (copied from the smalloffice_20
  worked-example's legacy format; harmless under extra=allow, plan-irrelevant).
- No downstream / correction / EP (reading-only cross-test per user stamp). No record.
