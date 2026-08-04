# 批 C r3 · sol 独立工程质量复核

> **状态：本文最终版**
>
> 日期：2026-08-04 · 复核席：sol（GPT 侧） · 被复核施工：Claude 侧

## 0. 总判定

**REWORK：1 BLOCKER / 1 MAJOR / 0 MINOR / 0 NIT。** B-1 的新判据在施工四格上有效，但在合法 schema 的真实形状上同时存在决定性假阴性与假阳性：整套结构一并落入像素空间时原始 `[360,450]` 可使整个 regression report 通过；普通 10×8 m 闭合 polyline 又会因重复闭合点令 MAD 退化为 0，误杀合法 OCR/尺寸端点。M-2 的旧 fallback 代码虽删除，但“不可解码源图必须 fail-closed 且可区分”的派工要求仍未落，且其独立锁没有绑定不可解码这一前提。

| 严重级别 | 数量 | 条目 |
|---|---:|---|
| BLOCKER | 1 | B-1r：逐轴 median/MAD 围栏可被全结构像素化绕过，并会对普通闭合 polyline、狭长/稀疏/立面形状产生退化误杀 |
| MAJOR | 1 | M-2r：不可解码 `.png` 仍被 manifest/coverage 接受并可让合法产物整门通过；无机器可读 source-decode 原因，M-2 锁是假锁 |
| MINOR | 0 | — |
| NIT | 0 | — |

M-1 冻结修复与 Batch D 的完整文本/rail 隔离修复成立；但在上述 BLOCKER/MAJOR 收口前不能批准。

## 1. 范围、纪律与基线

- 被复核 commit：`bc50aae`（B-1/M-2）、`3b2f469`（M-1）、`4e19ab6`（Batch D 标签）。
- 三份必读已完整读取：r3 派工单、上一轮 sol 报告、施工执行日志 §9。
- 实验克隆：`git clone --local --no-hardlinks /workspaces/EnergyPlus-Agent-dev /tmp/energyplus-sol-r3-20260804.WFtl2C/repo`；所有 Python/pytest 命令均在克隆内先 `export PYTHONPATH=$PWD`。
- 主树未运行 `git status`；未读取 `case_tests/test_baseline/gt/` 答案数字；探针只在 `/tmp` 写合成输入。
- 干净克隆全量基线：退出码 `1`，`4 failed, 2144 passed, 8 skipped, 10 xfailed`；四红分别是缺未跟踪 restore reading、缺 sm21 score 输入、缺 EP end-state 输入、缺 `OPENAI_API_KEY`，与上一轮同类 clone 环境红一致。最终全量只按相对这个基线是否新增红判断。

## 2. T-1：单位异常判据的分辨力与合法产物误伤

**结论：不成立（当前至少 BLOCKER）。** 施工四格锁本身复跑全绿，但固定的逐轴 `median ± max(10×MAD, 5m)` 既可被整套像素空间结构自洽绕过，也会因闭合折线的重复首点使 MAD 退化而误杀普通合法产物。

### 2.1 静态证据

- `src/validator/checks/reading.py:77-82`：固定 10×MAD 与 5 m 下限。
- `src/validator/checks/reading.py:519-557`：对 line/rect/polyline 的所有点分别收集 x/y，取逐轴中位数与 MAD；没有去重、闭合点处理、真实 extent 兜底或统计退化判别。
- `src/validator/checks/reading.py:363-391,423-452`：OCR 与 dimension endpoint 在 regression/golden 直接消费这个围栏。

### 2.2 施工四格与真实量级锁复跑

命令：

```text
export PYTHONPATH=$PWD
pytest -q -n 4 tests/test_checks_reading_correction.py -k 'b1_' > t1_existing.log 2>&1
rc=$?; echo T1_EXISTING_EXIT=$rc; cat t1_existing.log
```

输出：`T1_EXISTING_EXIT=0`，`7 passed in 2.99s`。因此 `[360,450]`/普通合法值/120×90 m 合法值/同比例坏值等施工锁在其 fixture 上成立，但不足以证明判据普适。

### 2.3 独立假阴性与假阳性探针

命令：

```text
export PYTHONPATH=$PWD
python sol_r3_structural_probe.py > sol_r3_structural_probe_v2.log 2>&1
rc=$?; echo STRUCTURAL_PROBE_V2_EXIT=$rc; cat sol_r3_structural_probe_v2.log
```

退出码 `0`。关键原始输出：

```text
{"case":"metric_rectangle_bad_360_450","passed":false,"reference":[-45.0,55.0,-36.0,44.0],"blocking":["reading.dimension_parseable","reading.ocr_anchors_in_bounds","reading.dimension_endpoints_in_bounds"]}
{"case":"uniform_pixel_space_structure_and_anchor","passed":true,"reference":[-3555.0,4345.0,-4999.5,6110.5],"blocking":[]}
{"case":"small_pixel_coordinate_inside_fence","passed":true,"reference":[-45.0,55.0,-36.0,44.0],"blocking":[]}
{"case":"legitimate_closed_10x8_polyline","passed":false,"reference":[-5.0,5.0,-5.0,5.0],"blocking":["reading.ocr_anchors_in_bounds","reading.dimension_endpoints_in_bounds"]}
{"case":"legitimate_closed_slender_polyline","passed":false,"reference":[-5.0,5.0,-5.0,5.0],"blocking":["reading.ocr_anchors_in_bounds","reading.dimension_endpoints_in_bounds"]}
{"case":"legitimate_single_long_wall_offset_dimension","passed":false,"reference":[-900.0,1100.0,-5.0,5.0],"blocking":["reading.ocr_anchors_in_bounds","reading.dimension_endpoints_in_bounds"]}
```

判读：

1. **系统性假阴性**：四边完整矩形若 strokes 与 anchor 一并采用 790×1111 像素坐标，`[360,450]` 落入被自写结构撑到 `[-3555,4345]×[-4999.5,6110.5]` 的围栏，且整份 regression report `passed=true`。实现 docstring 所称“其他尺寸链很可能触发”在这个合法 schema、无 dimensions 的完整产物上没有发生。
2. **局部假阴性**：10×8 m 四边完整矩形的围栏本来就扩到 `[-45,55]×[-36,44]`，所以数值恰为 `[40,40]` 的像素 anchor 可通过；内部一致性无法识别数值碰巧不离群的单位错误。
3. **普通尺度假阳性**：10×8 m 合法闭合 polyline `[[0,0],[10,0],[10,8],[0,8],[0,0]]` 因首点重复使 x/y 中位数与 MAD 均为 0，围栏退化为 `[-5,5]²`，合法 OCR `[9,4]` 和 dimension endpoint `[10,0]` 同时 BLOCK。不是“两堵墙”探针。
4. **清单点名边界也失败**：200×2 m 狭长闭合轮廓、单段 200 m 墙且尺寸线合法偏移 10 m，均只因新两项检查被 BLOCK。

## 3. T-2：reading_mode 冻结点

**结论：成立。**

- `scripts/tool_scripts/run_stage.py:121-218`：`_manifest_for_attempts` 在任何 attempt 创建前调用 `provision_run`，随后对已声明 mode 调 `provision_reading_mode`，drift 转成 `SystemExit`。
- `scripts/tool_scripts/run_stage.py:2426-2434`：真实 `cmd_flow` 入口把 `run_config.reading_mode` 传入 choke point；record 位于 `:2588-2618`，因此冻结早于 reading 与 record。

独立命令：

```text
export PYTHONPATH=$PWD
python sol_r3_lane_probe.py > sol_r3_lane_probe.log 2>&1
rc=$?; echo LANE_PROBE_EXIT=$rc; cat sol_r3_lane_probe.log
```

关键输出：

```text
LANE_PROBE_EXIT=0
{"baseline_exists":false,"first_exit":0,"first_frozen_lane":"controlled","second_exit":null,"second_error":"✗ reading_mode_drift: ...","still_frozen_lane":"controlled"}
```

同一入口锁另跑：`pytest -q -n 4 tests/test_reading_mode.py::test_M1_late_edit_after_reading_executed_fails_closed_not_recorded_as_autonomous` ⇒ `1 passed`，退出码 `0`。

## 4. T-3：M-2 解码/manifest/stem fail-closed

**结论：不成立（MAJOR M-2r）。** 旧 `resolve_view_pixel_bounds`、PIL decode 与产品 bounds fallback 的确已被删除；manifest 缺失和 stem 错配也仍由 coverage fail-closed。但“源图不可解码”没有被 fail-closed 或机器可读地区分：manifest 只检查文件存在、`.png` 后缀并 hash 原始字节，垃圾字节照样建 manifest；给同一 stem 一个合法产物时 coverage PASS、总 report PASS。

- `src/agent/execution/view_manifest.py:845-870`：`_normalize_declared_path` 只验路径/后缀/文件存在并 `hash_file`，不验 PNG magic 或可解码性。
- `src/agent/execution/view_manifest.py:941-958,983-988`：`build_view_manifest` 宣称 hard gate fail-closed，但 plan image 路径只经过上述 normalize/hash。
- `src/validator/checks/view_manifest.py:31-42,80-121`：checker 已没有 `case_dir` 或 image decode 输入，只比较 expected/produced stem 后执行结构自洽检查。
- `src/agent/execution/view_manifest.py:1334-1353`：旧 resolver 只剩删除说明；全仓目标调用链 `rg` 无 `resolve_view_pixel_bounds`/`trusted_image_bounds` 消费，故旧的“解码失败后回落产品自算 bounds”确实不存在。

同一 `STRUCTURAL_PROBE_FINAL_EXIT=0` 探针三分支原始输出：

```text
{"case":"undecodable_source_with_legal_product","passed":true,"blocking":[],"results":{"reading.view_manifest_coverage":{"status":"pass","evidence":{"expected_output_ids":["1f_view"]}},"1f_view.reading.ocr_anchors_in_bounds":{"status":"pass",...}}}
{"case":"manifest_missing_with_legal_product","passed":false,"blocking":["reading.view_manifest_coverage"],"results":{"reading.view_manifest_coverage":{"status":"fail","evidence":{}}}}
{"case":"stem_mismatch_with_legal_product","passed":false,"blocking":["reading.view_manifest_coverage"],"results":{"reading.view_manifest_coverage":{"status":"fail","evidence":{"extra_stems":["evil_view"],"missing_expected_output_ids":["1f_view"]}}}}
```

因此三者可区分性为：manifest 缺失与 stem 错配成立；不可解码源图不成立。它不再导致旧 bounds fallback，但仍是静默接受而非派工单要求的 source-integrity fail-closed。

## 5. T-4：新增锁绑定

**结论：不成立。** B-1 的异常正例/合法大建筑反例、M-1、Batch D 两锁均真绑；但 M-2 锁只绑定“坏 anchor 被结构判据 block”，没有绑定“源图不可解码”。逐锁集合见 `tests/test_checks_reading_correction.py:1269-1519`、`tests/test_reading_mode.py:228-306`、`tests/test_batch_d_typed_grade.py:268-347`。

统一纪律：所有 mutation 在 clone 内用 `apply_patch` 做，命令均为 `export PYTHONPATH=$PWD; pytest -q -n 4 ... > log 2>&1; rc=$?; echo ...`，随后用反向 patch 恢复。恢复后目标 7 测 `POST_MUTATION_CLEAN_EXIT=0`、`7 passed`，`git diff --check`/`git diff --stat` 对 tracked 文件均零输出。

| 锁/行为 | mutation | 结果 | 绑定结论 |
|---|---|---|---|
| B-1 坏 `[360,450]`、120×90 同比例坏值、stray stroke、产品 bounds/dimension 撑大、M-2 坏 anchor | `_UNIT_ANOMALY_MAD_FACTOR: 10 → 1e9` | `5 failed, 2 passed`，exit `1` | 5 条异常拒绝锁真绑到围栏强度 |
| B-1 大建筑不误告 | `_UNIT_ANOMALY_MAD_FACTOR: 10 → 0` | 只该锁红：`1 failed, 6 passed`，exit `1` | 真绑相对缩放，不是装饰性反例 |
| `_structural_metric_reference` 整体摘掉 | 函数直接 `return None` | clean 文件为 `1 failed,94 passed`（clone 环境红）；mutation 为 `10 failed,85 passed`，即相对新增 9 红，含合法大建筑/合法 margin；exit `1` | 与 orchestrator 主树“10 红”方向一致；clone 缺 restore reading 使第 10 条本来就环境红，不能把它重复算 mutation 红 |
| M-1 真实 flow 早冻结 | 仅把 `cmd_flow` 的 `reading_mode=run_config.reading_mode` 改为 `None` | 目标锁 `1 failed`，首次 flow 后 `reading_mode.json` 不存在；exit `1` | 真绑真实入口/时序 |
| Batch D 完整 label 文本 | 恢复 `polygon.id[-14:]`/`segment.id[-10:]` | 目标锁 `1 failed`，`'ry:North:0' != 'F1:boundary:North:0'`；exit `1` | 真绑完整 id |
| Batch D rail 保留带 | 删除 scale 公式的 `- rail_reserved` | 目标锁 `1 failed`，保留带检出 `TRUTH (148,148,142)`；exit `1` | 真绑 geometry/rail 隔离 |
| **M-2 不可解码前提** | 把测试中的垃圾字节 `.png` 换为真实 `790×1111` 可解码 PNG，不改实现 | **`1 passed`，exit `0`** | **假锁：图片是否可解码对断言零影响** |

逐锁缺口也被独立探针证明：现有 7 条 B-1 测试不含闭合 polyline、均匀全结构像素化、普通单段/狭长/多层立面的统计退化，所以 mutation 红只能证明当前 fixture 使用了函数，不能排除 T-1 的假阴性/假阳性。

## 6. T-5：边界合规

**结论：成立。** 未发现施工越界。

- 未 push：主仓库 `origin=https://github.com/hortonyyx/EnergyPlus-Agent-dev.git`；实时 `git ls-remote --heads origin` 退出码 `0`，目标分支 tip 为 `6e06ecf46cad30d164beb5a85f6dd98fc41d1f02`。`git merge-base --is-ancestor 4e19ab6 6e06ecf...` 退出 `1`，反向 `6e06ecf... → bc50aae` 退出 `0`，即远端明确停在 r3 之前。
- `git diff --numstat f7cc1ff..4e19ab6 -- case_tests/test_baseline/gt/ case_tests/e2e_tests/sm24_anchor/case_data/testdata_prompt.json` 零输出：GT 与 sm24 testdata 均零字节变更；本复核未打开 GT 文件内容。
- 三 commit 的唯一文件集合为 `reading.py`、两个 `view_manifest.py`、`isolation.py`、`run_stage.py`、`render_grade.py` 与三个对应测试文件；无 `AI_agent/**`、GT、sm24 testdata。施工执行日志 §9 是工作树未提交日志；其余 `AI_agent/` 未提交管理文档按派工上下文归属 orchestrator，本席没有把它们作为施工 commit 内容。
- 本复核所有实验均在 `/tmp/energyplus-sol-r3-20260804.WFtl2C/repo`；主树只新增本 verdict，不运行 `git status`、不提交、不 push。

## 7. T-6：不变量 #6

**结论：不成立；会成为必须推翻的假设。** 不是“未来可能”：当前 schema 下的普通闭合轮廓已经推翻“coordinate-wise MAD 能代表结构 extent”。闭合首点、非方形长宽比、退台/中庭的顶点密度与重复坐标会改变中位数/MAD而不改变真实包络；稀疏单段在正交轴 MAD=0；多层立面若多条楼板共享左右端点，会让 x 轴中位数/MAD退化。

独立多层立面探针采用 60×80 m 闭合 outline + 20/40/60 m 三条楼板线（不是两墙）：`reference=[-5,5,-160,240]`，合法 `[30,70]` OCR 与 x=65 的 80 m 竖向 dimension 同时被新两项检查 BLOCK，且没有其他 blocking check。超大体量本身在施工“两条平行墙”的特定 fixture 上可通过，但这不建立形状不变量；超大闭合 polyline 仍会按顶点 multiplicity 退化。中庭/退台并非必然失败，但判据依赖表示方式而非几何实体，不能作为稳定 gate 假设。

## 8. 清单外自主发现

1. **BLOCKER B-1r：闭合 polyline 的重复首点会把 MAD 压成 0。** 同一个 10×8 m 矩形，用四条 line 表示时围栏为 `[-45,55]×[-36,44]`，用一个合法闭合 polyline 表示时却变成 `[-5,5]²`；判定取决于序列化表示而不是同一几何实体。
2. **BLOCKER B-1r：全结构像素化是无外部根路线的确定性盲区。** 施工 docstring 只说其他内部检查“very likely”触发；实际无 dimensions 的完整四边 790×1111 payload 所有 gate① 检查全绿。这也说明内部一致性算法不能证明全局单位正确。
3. **MAJOR M-2r：M-2 测试的关键输入是假锁。** 把 undecodable bytes 换成有效 PNG，测试仍绿；其断言只重复 B-1 坏 anchor 正例。
4. **Batch D 肉检疑似叠字的初判被程序化 bbox 证伪，不记 finding。** 完整四立面 fixture 输出 `948×1184`、48 audit entries；进一步按生产位置/font 计算 segment/opening `textbbox` 未发现相交。rail 与 geometry mutation 也精确变红，因此本轮不重开 MINOR。

## 9. 核实失败的尝试

- **M-1 mutation 第一次改错调用点，作废。** 相同文本在 `cmd_run`/`cmd_resample`/`cmd_flow` 三处出现，第一次无上下文 patch 命中 `cmd_run:2195` 而非 `cmd_flow:2433`；`rg` 定位后立即反向恢复，再用 `def cmd_flow` 上下文精确 mutation，得到目标 1 红。错误轮未作为绑定证据。
- **Batch D 图片探针第一次导入失败，作废。** 直接运行脚本缺 `scripts/tool_scripts` 的模块搜索路径，`ModuleNotFoundError: _grade_transform`，退出码 `1`，图片未生成；补入该目录后重跑退出 `0`。
- **Batch D 肉检第一次把相邻文本看成重叠，后续证伪。** 原图视觉上 North/South opening 与 segment label 很近；按生产坐标和实际 `_fit_label_font` 逐项求 `ImageDraw.textbbox`，没有 bbox 相交，故不记 finding。
- **clone 全量环境红不当施工回归。** clean clone 已有固定四红；mutation 与最终全量都只相对此基线判断。没有把缺未跟踪数据或 API key 记到 r3。

## 10. 独立全量测试

命令（clone 内，mutation 已全部反向恢复；无 `-m`、无管道吞码）：

```bash
export PYTHONPATH=$PWD
pwd
python -c 'import src; print(src.__file__)'
pytest -q -n 4 > final_full.log 2>&1
rc=$?
echo FINAL_FULL_EXIT=$rc
tail -n 45 final_full.log
```

路径钉死输出：

```text
/tmp/energyplus-sol-r3-20260804.WFtl2C/repo
/tmp/energyplus-sol-r3-20260804.WFtl2C/repo/src/__init__.py
```

退出码 `FINAL_FULL_EXIT=1`。结果与干净 clone 基线逐项一致：同样四条环境红、`2144 passed + 8 skipped + 10 xfailed`，**相对基线零新增红**。最终 tracked 恢复核对：`FINAL_DIFF_CHECK_EXIT=0`、`FINAL_DIFF_STAT_EXIT=0`，两个日志均 `0` 字节。

尾部原文：

```text
tests/test_run_stage_flow.py::test_flow_judge_block_auto_invalidates_and_force_resamples
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2407: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_flow_judge_block_auto_inv0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_terminal_stop_returns_20
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2407: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_flow_terminal_stop_return0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2407: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_flow_geometry_auto_record0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2180: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_cmd_run_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2407: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_refuses_persisted_v1_before_any_write
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2254: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_cmd_resample_refuses_pers0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_new_run_flow_smoke_produces_v2_base_v2_records
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2407: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_new_run_flow_smoke_produc0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/scripts/tool_scripts/run_stage.py:2180: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6547/popen-gw0/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_render_grade.py::test_render_grade_draws_no_data_for_missing_score_floor
tests/test_render_grade.py::test_render_grade_missing_facade_key_is_no_data
  /tmp/energyplus-sol-r3-20260804.WFtl2C/repo/tests/test_render_grade.py:243: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    return sum(1 for px in view.getdata() if all(abs(int(px[i]) - color[i]) <= tol for i in range(3)))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four
FAILED tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor
FAILED tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean - ass...
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones - openai.O...
4 failed, 2144 passed, 8 skipped, 10 xfailed, 209 warnings in 332.76s (0:05:32)
```
