# 复审请求（re-verify）：0–5 校验架构实现 — Codex CHANGES REQUESTED 处置

> **类型**：re-verify（只核上轮 5 条 findings 是否真修，附带看修复有无引入新硬伤）。
> **发起**：主开发 Agent（Opus 4.8），2026-06-16。
> **上轮 review**：[2026-06-16_pipeline_0-5_validation_implementation_review.md](../review/2026-06-16_pipeline_0-5_validation_implementation_review.md)（CHANGES REQUESTED，2 High + 3 Medium）。
> **处置 commit**：`963d952` `6.15_ValidationFixCodexReview`（在 `0d267bf` 之上；分支 `6.15_ValidationArchM0toM4`）。
> **测试**：191 → **201 全绿**（+10 回归）。

## 1. 逐条处置（diff 锚点）

### High 1 — `validate_case()` 缺必需产物静默放行 / 缺 EP 不验 / 伪 digest
**修复** [src/agent/execution/validation_run.py:77-188](../../../../src/agent/execution/validation_run.py)：
- 新增**必需产物表**（full scope）`0_reading(*_view.json) / 1_correction/correction_geometry_snapped.json / 2_modelling/building_geometry.json / 3_split_pairing/geometry_specs.md / 4_mep/mep_output.json / 5_intakeoutput/intake_output.json`，逐项缺失 → `_error_report()`（CheckStatus.ERROR→BLOCK）写入对应 stage key。
- EP 改由 [policy.py](../../../../src/agent/execution/policy.py) 新增 `require_ep: bool=False` 控：`require_ep=True` 且缺 `EP/EP_run/eplusout.end` → 必需产物 ERROR；`False` → 显式不验（**不再凭缺 `.end` 推断 pre-EP**）。
- geometry digest **只在 `building_geometry.json` AND `geometry_specs.md` 都在时**用真产物算（删 `{}`/`""` 回退），否则 `digest=None`——杜绝伪 digest 被误批准。
- 5_intakeoutput：intake 在但拿不到 `used_constructions`（上游几何缺）→ 记 ERROR、不静默跳。
- **请重点核**：是否还有任何 full-scope 路径能在缺/坏产物时返回 `blocked=False`；ERROR 是否确实经 `disposition()` 映射成 BLOCK 并进 `blocking_summary`。

### High 2 — `write_reports=True` 伪造/覆写 `run_manifest.json`
**修复**：[manifest.py](../../../../src/agent/execution/manifest.py) `save(*, filename=MANIFEST_NAME)` 加文件名参；[validation_run.py:185-188](../../../../src/agent/execution/validation_run.py) 改写独立 `validation_manifest.json`（明确是校验摘要、不冒充 M0 审计 manifest、绝不覆写 `run_manifest.json`）。回归 `test_existing_manifest_not_overwritten_by_validate_case`。

### Medium 1 — 空 layer Construction 空过 4_mep 门
**修复** [mep.py `_construction_to_material`](../../../../src/validator/checks/mep.py)：先剥 eppy 尾部 padding（防误报），零有效 layer → `no layers (empty construction)` block；中间空白 layer → `blank layer field (gap)` block。回归 `test_empty_construction_blocks`。

### Medium 2 — `kernel.spec_self_consistency` 逮不住未声明 zone
**修复** [kernel.py](../../../../src/validator/checks/kernel.py)：声明集改 `set(bg.zones) | {zv.zone for zv in bg.zone_volumes}`（**不再并入 surface 自身 zone**）；`_zone_closure` 对无 `ZoneVolume` 的 surface zone 由 `continue` 改 block。回归 `test_undefined_zone_blocks`。

### Medium 3 — 崩轴 rect 被接受
**修复** [reading.py](../../../../src/validator/checks/reading.py)：rect 退化判定 `and`→`or`（任一轴崩即退化）。回归 `test_reading_collapsed_axis_rect_blocks`。

## 2. 关注点（修复有无引入新问题）
1. 必需产物表是否覆盖全、有无遗漏的 full-scope fail-open 残留（尤其 `DOWNSTREAM_ONLY` scope 不受影响是否仍正确）。
2. eppy padding 剥除逻辑会不会把**合法**多层 construction 误判（注意只剥尾部空、中间空才报 gap）。
3. M2 声明集改动后，正常 case（surface zone 都有 ZoneVolume）是否仍全过（sm20_anchor baseline 未回归）。
4. `validation_manifest.json` 与 `run_manifest.json` 是否彻底分家、无任何路径再写后者。

## 3. 验收标准
- 5 条 findings 全部实修（非掩盖）；无新增 fail-open / 回归。
- 判 verdict：CLOSEABLE / 仍 CHANGES REQUESTED（附剩余项）。

## 4. 如何跑
```bash
python -m pytest -q                                   # 201 绿
python -c "from src.agent.execution import validate_case; \
  r=validate_case('/tmp/empty_case_dir'); print('empty blocked', r.blocked)"   # 应 True
python -c "from src.agent.execution import validate_case; \
  r=validate_case('case_tests/e2e_tests/sm20_anchor'); print('anchor blocked', r.blocked)"  # 应 False
```
> 复审文档请落 `AI_agent/logs/review/review/2026-06-16_pipeline_0-5_validation_reverify_review.md`。
