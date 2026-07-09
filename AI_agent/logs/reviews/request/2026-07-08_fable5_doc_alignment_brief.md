# Fable5 期文档对齐施工 brief（2026-07-08，Opus 出方案 → Codex 施工）

**背景**：Fable5 于 2026-07-06/07/08 改了不少代码——C2 B0/B1（`schema_version` v2 + `Cell.polygon` + `capability_profile`）/ 判卷 W1–W6（渲染件改名 + 结构栅格 0.05→0.01 + gt `wall_thickness_m` centerline→outer-skin 换算）/ 污染硬隔离（isolation.py + spawn_isolated_reader）/ facade frame 接线 / M1–M4。**部分管理文档 / guide SOP / 各阶段产物·gate·judge·grade·score 描述滞后**。本批 = **纯文档对齐**（不改任何代码逻辑/契约），把文档描述对齐到实际代码。

**范围文档**：`AI_agent/guides/new_case_guide.md` · `AI_agent/CLAUDE.md` · `AI_agent/architecture/pipeline_stage_contracts.md` · `AI_agent/architecture/judge_grade_model.md` · `AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md`（其余按需）。

## 不对齐点（已初扫，逐条 file:line 核实实际代码后再改）

1. **旧渲染件名**：`zones.png` / `elev.png`（W2 改前）→ 现 `plan_<floor>_render.png` + `roles_<floor>.png` + `elev_<facade>_render.png`（legacy `zones.png`/`elev.png` 仍保留兼容）。以 `scripts/tool_scripts/render_corrected_geometry.py` / `render_elevation_windows.py` / `run_stage._render_stage` / `report_assembly.collect_eyeball_assets` 的实际产出为准。已知 `skills/intake_pipeline/1_correction/judge_rubric.md` 已改新名（可作对齐参照）。在 `new_case_guide.md` + `contracts` 全量对齐（初扫命中这两处有旧名）。

2. **C2 v2 契约描述**：`new_case_guide.md` §2.3 S1 correction 若仍只说「矩形 cell」→ 补 `schema_version` v2 + `Cell.polygon`（一房一 cell、polygon 仅用于非矩形房间、`x`/`y`=polygon bbox 投影）+ `capability_profile`（rectangular / orthogonal_polygon）。以 `src/agent/correction/schema.py` + `skills/intake_pipeline/1_correction/A0_contract.md` + `src/agent/correction/cell_geometry.py` + `src/agent/geometry/capability.py` 为准。contracts 已在 §5.6 有 schema_version 落地记录，核实一致。

3. **判卷对 polygon（grade/score）**：`judge_grade_model.md` 若未记 C2 非矩形判卷现状 → 补一条（现状 = 判卷打分器对非矩形**零 capability 感知**、C2 第一个非矩形 case 判卷是未定义行为、segment/polyline 模型是 C2 硬前置；已在 `contracts §5.7` + `plan backlog` + `capability B1 补` 记录，judge_grade_model §8b 加对应 backlog 条）。W5 的 `correction_score` wall_thickness centerline→outer-skin 换算（只外扩贴边墙段/footprint）描述对齐 `src/agent/judge/correction_score.py`。

4. **测试数**：`CLAUDE.md` 全文残留 `509 绿`/`517 绿`/`489 绿` → `562`（§2 顶已由 Opus 更新，扫全文档其余残留；tests 表 §1.3 也核）。

5. **结构栅格 / 容差**：`A0_contract.md` SNAP_GRID 已 10mm（W4）；核实 `contracts` / `new_case_guide` 若提 50mm 栅格则对齐。`correction.yaml` `structural_snap_grid_m: 0.010` 为准。

6. **附录 A 隔离协议**：`new_case_guide.md` 附录 A 是 `claude -p` 隔离协议；补一段**非 Claude 模型（gpt-5.4-mini 等）经 codex CLI** 的隔离说明——clean-room staging（`spawn_isolated_reader build`）物理裁剪适用、Claude Code PreToolUse guard 层不适用（弱一层、gt 物理排除兜底）、codex `-i` 可变参数吞尾随 prompt 故 prompt 走 stdin。参照 `CLAUDE.md §5` 新增的跑测铁律（2026-07-08 已登记）。

## 纪律 / 验收

- **纯文档对齐**：不改任何代码逻辑、schema、契约、测试。
- 每处改动**先 file:line 核实实际代码**再对齐（别照 brief 字面猜；brief 的产物名/字段名可能不全，以代码为准）。
- 产物名 / gate / judge / grade / score 描述必须与实际代码一致。
- 改完**逐条报告**改了哪个文件哪节、对齐到哪个 file:line；并报告有无发现 brief 未列的新不对齐点（不自行扩改，列出来待 Opus 定）。
- 审阅需求：Opus 复核=抽查产物名对齐 + C2 契约描述 + 附录 A codex 段 + 无代码改动。
