---
name: /context token accounting in Claude Code
description: Which categories in /context actually count toward Tokens used vs which are display-only — corrects the earlier "harness ~100k" assumption used in test_baseline notes.
type: project
originSessionId: dd657860-f2c8-418e-b4cc-230f2fcb7814
---
Claude Code's `/context` panel splits context into multiple categories, but **not all of them count toward the `Tokens: X / 1m` total**. Verified empirically on 2026-04-29 by adding both `2026-04-27_sm_15_post_p0` and `2026-04-29_sm_16_multifloor_v1` runs:

| Category | Counts toward `Tokens used`? |
|---|---|
| System prompt | ✅ yes |
| System tools | ✅ yes |
| MCP tools (loaded) | ✅ yes |
| Memory files | ✅ yes |
| Skills | ✅ yes |
| Messages | ✅ yes |
| **MCP tools (deferred)** | ❌ no — display only |
| **System tools (deferred)** | ❌ no — display only |
| **Autocompact buffer** | ❌ no — reserved area |
| Free space | ❌ no — remaining 1M budget |

**Why:** Claude Code switched to dynamic MCP schema search. Deferred tools' schemas are not preloaded; they're surfaced via system-reminder by name, callable only after `ToolSearch select:<name>`. The "deferred" lines in `/context` show what *could* be loaded, not what's currently charged.

**Why this matters for test_baseline:**

- The previous 2026-04-27 notes claimed `harness ~100k` and "关掉无关 MCP server 能省 20-36k". Both are **wrong** — the unrelated MCP servers (Notion / HF / GoogleDrive) sat in the deferred bucket and never charged the Total.
- True calculable harness (counted in Total) is **~24k**, not ~100k.
- Token Δ comparison across runs must subtract only the loaded-MCP-tools line, not the deferred line.

**How to apply:** When recording or comparing runs:
1. `tokens.total` = the headline `Tokens: X / 1m` value, which equals `system_prompt + system_tools + mcp_tools(loaded) + memory + skills + messages` (≈, ±1%).
2. To estimate "where did the budget go", only sum loaded categories. Treat autocompact + deferred + free space as informational.
3. Optimization headroom is dominated by **Messages** (~14% × 1M = 140k for sm_15/16 cases). Don't waste effort on disabling unused MCP servers — that gain doesn't exist.
4. If a future Claude Code release re-bundles deferred schemas into Total (regression), re-check by adding the categories listed above against the headline number; the discrepancy will show up immediately.
