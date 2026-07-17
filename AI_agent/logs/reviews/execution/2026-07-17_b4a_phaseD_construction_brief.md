# B4a Phase D 执行简报（terra，2026-07-17）

## 改动映射

| 合同章节 | 施工落点 |
|---|---|
| §11.1 | `src/agent/judge/gt_render_model.py`：frozen render primitives、v3 direct adapter、隔离的 v2 rectangular adapter、typed plan/elevation renderer。 |
| §11.2 | `scripts/tool_scripts/render_gt.py`：v3 typed load/adapt/CLI path；显式 JSON path 必须给 `--out-dir`；v2 raw legacy drawing 保持原入口和像素锁。 |
| §11.3 | `scripts/tool_scripts/render_gt_overlay.py`：v3 manifest-affine overlays、raster SHA/root containment、doc/manifest hash binding、atomic dynamic output；legacy density wrapper 未改。 |
| §14.3/§14.4 | render/overlay/discipline tests：concavity、dynamic panels、north、watermark、absolute-along、floor-z/Vg intervals、affine endpoint、hash/mismatch/atomic/sanitize、legacy pixel sizes、v3 legacy-vocabulary scan。 |
| §15.1 | `tests/b4b_contract_fixture.py`：仅测试可用、self-contained、semantic-valid typed two-floor L/Vg contract fixture。 |

## 稿章节 → 测试映射

| 章节 | 测试 |
|---|---|
| §11.1/§14.3 plan/elevation | `tests/test_gt_render.py` |
| §11.3/§14.3 affine/overlay | `tests/test_gt_overlay.py` |
| §14.4 isolation/fixed-four gate | `tests/test_gt_discipline.py` |
| §15.1 seam | `tests/b4b_contract_fixture.py` 经 `test_gt_render.py` 调用，factory 内 `validate_gt_v3()` |

## 验收与测试

| 命令/组 | 结果 |
|---|---:|
| preflight §14.5 | passed（仅已有依赖；工作树初始仅 dispatch 未跟踪） |
| `test_gt_render.py test_gt_overlay.py test_gt_discipline.py` | 26 passed（9 existing Pydantic serializer warnings） |
| `test_gt_schema.py test_gt_from_dxf.py test_inspect_dxf.py` | 63 passed（13 existing serializer warnings） |
| judge/scorer related：reading/elevation/batch/harness | 62 passed |
| `git diff --check` | passed |
| full `pytest -q` | 主控轻门范围；本执行档的交互时限内未取得完成态，未把部分进度当作通过。 |

独立 Opus 对抗审阅曾发现 absolute-along、elevation z/Vg、manifest binding 与 fixture validity 阻断项；均已针对性修正。最终 seam factory 的两种 observed-elevation 变体均在 factory 内通过 `validate_gt_v3()`。

## 预期行为变化

- v3 render 不再以 v2 W/D 或固定四 facade 解释 schema；plan/elevation panel 随 typed floor/source surface 动态生成。
- v3 openings/visible intervals 使用 canonical absolute world-along，North/West 不会因 p1 方向反转偏移。
- elevation/overlay 以 floor z、visible/hidden pieces 与 manifest affine 投影；candidate watermark 不可关闭。
- v3 overlay 只接受显式 manifest/raster root、匹配的 raster/doc/manifest hashes，并只写到不存在的 atomic output directory。
- v2 sm21 路径仍走原 legacy renderer；关键 plan/elev image size 与 four-panel 行为已锁。

## 未决·偏离

- 未改 `render_grade.py`、score/run-stage/Va/completeness，未改资产/lockfile，未提交。
- 全量 pytest 是主控轻门；本档没有将交互时限内的未完成全量测试标作通过。

## review-ask

none（R1–R5 按派工单既有裁决执行，未重开）。

## 本批改动文件

- `src/agent/judge/gt_render_model.py`
- `scripts/tool_scripts/render_gt.py`
- `scripts/tool_scripts/render_gt_overlay.py`
- `tests/b4b_contract_fixture.py`
- `tests/test_gt_render.py`
- `tests/test_gt_overlay.py`
- `tests/test_gt_discipline.py`
- `AI_agent/logs/reviews/execution/2026-07-17_b4a_phaseD_construction_brief.md`

## 返工 r1（纯测试锁，2026-07-17）

| 项 | 修法与新增/更新测试 |
|---|---|
| M-1 | `test_v3_dynamic_elevation_panels_partial_and_plan_only_legends` 改名并用 test-side PIL text ledger 锁 `PLAN-ONLY / Z UNSET`、无 `NA` 与 partial 标记；新增 `test_v3_null_north_omits_true_north_vector`、`test_v3_no_elevation_binding_has_explicit_panel_text`。 |
| m-1 | 新增 basename/path/symlink、out-of-bounds、competing binding、empty sanitized id、singular affine 的 v3 overlay 负测。 |
| m-2 | 将 v3 dynamic-panel 的纯 width 常量改为非退化断言；v2 sm21 精确 pixel regression lock 保留。 |
| n-2 | discipline forbidden-vocabulary scan 现覆盖 `gt_to_render_model` 及 `render_gt.py` 的 v3 entry branch。 |
| n-1 | verification metadata 字段未动。 |

- 新增 pytest items：8（定向组由 26 增至 34）。
- 活体自证：临时把 `gt_render_model.py` 的 `PLAN-ONLY / Z UNSET` 改为 `PLAN-ONLY / Z BROKEN`；只跑 M-1 测试得到 **1 failed**（断言捕获到 BROKEN、缺 UNSET），随后立即还原；最终 production 文案已恢复。
- 最终定向命令：`pytest -q tests/test_gt_render.py tests/test_gt_overlay.py tests/test_gt_discipline.py`。
- 本轮改动文件：`tests/test_gt_render.py`、`tests/test_gt_overlay.py`、`tests/test_gt_discipline.py`、本执行简报；三份 production render 文件本轮零保留改动。
