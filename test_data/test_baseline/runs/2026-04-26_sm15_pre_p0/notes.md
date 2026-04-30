# 2026-04-26 sm_15 pre-P0 (anchor backfill)

## 性质
**反填的 anchor run**，不是实时 trace。用于给 P0 优化提供 token 对比基线。

## 数据来源
- `test_data/SmallOffice/smalloffice_15/output/run_log.md` —— 工具调用次数 / 产物 counts / 失败补丁
- `AI_agent/token_optimization.md §1.1` —— token 分布表

## 已知不精确
- `tokens.total ≈ 150000` 来自 token_optimization.md §1.1 的"sm_15 实测"；分项（create_zones / update_surfaces / fenestration / reasoning / skill / reconnect）相加为 165k，与总量 150k 有 ~10% 估算误差，原因是分项里"reasoning_interleaved"和"reconnect_reload_overhead"在原文是粗估并存在重叠。**后续 run 不要把分项总和当 ground truth**，仅作分布参考。
- `by_phase.vision_and_claude_ep = 0`：原文未单列；视觉理解 + claude_ep.md 写作的 token 已混入 `reasoning_interleaved`。
- `by_tool.tokens` 仅填了三个主调用的估算值，其余维护性调用（list / validate / export）token 微小，未单列。
- `session_count = 2`：原文记述"中途掉线 1 次 → history 重灌"，即一次断点续跑 = 2 个会话。

## 几何验收依据
- `run_log.md §3` 的 IDF 对象计数表（zones=14 / surfaces=84 / fenestration=12 全 ✓）
- `run_log.md §2.3` 的尺寸链解读（W=15、D=8、H=3.6×2、窗 x-范围 / sill / head 全部对应 top_view 与 South_view 实测尺寸）
- 当时未截 OpenStudio 三维图，`openstudio_screenshot` 留空。下次重跑应补。

## 流程定位
- `pipeline_version: yaml_to_idf_v1` —— MCP 工具 → ConfigState → `export_yaml` → `ConverterManager.convert_all()` → IDF
- 已含 4 条 export_idf 补丁（RunPeriod None / warmup days / Adiabatic / Schedule None），但补丁仍由 LLM 在会话中 inline 写 Python 执行（**未** externalize）
- Construction 占位（`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`）需在 `convert_all()` 前手工预置，否则 fenestration 静默丢失。本 anchor 当时手工预置成功。

## 下一步对比目标
2026-04-27 起 P0 改动 1（ack_only）+ 改动 2（batch）+ 改动 4（export_idf 外置）全部落地后，预计：
- `total` 150k → 70-80k
- `by_tool.update_surface.calls` 84 → 0（被 `update_surfaces_batch.calls = 1` 取代）
- `by_tool.create_fenestration_surface.calls` 12 → 0（被 `create_fenestration_surfaces_batch.calls = 1` 取代）
- `session_count` 应能从 2 降到 1（不再掉线）
- `mcp_tool_count` 77 → 79
- `p0_flags` `[]` → `["ack_only", "batch", "export_idf_externalized"]`
- counts 必须保持 14/84/12 完全一致，dimensions_check 仍 pass
