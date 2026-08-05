# F-7 执行日志（Claude 侧 Sonnet 子代理）· source_ids 语义改为观测编号

- 状态：IN PROGRESS（骨架，边做边补）

## 已完成

1. `src/agent/correction/window_sources.py`
   - `WindowResolverInputError` 新增必填关键字参数 `category`（`WindowSourceErrorCategory =
     Literal["model_draw_error", "input_integrity_error"]`），无默认值 —— 漏分类的抛出点直接
     `TypeError`，不会静默落进某一类。
   - 全部约 45 处 `raise WindowResolverInputError(...)`（含 `parse.py` 2 处、`finalize.py` 2 处）
     已逐一按抛出点分类（见下方分类表）。
   - 新增 `_translate_observation_reference`：把模型引用 `<expected_output_id>/<observation_id>`
     （如 `1f_view/S11`）翻译成内部 locator；已是合法 `src:<64hex>` 的原样放行（向后兼容）；
     三种翻译失败各给具名错误码：`observation_reference_ambiguous`（裸编号/格式不对）·
     `observation_reference_view_unknown`（图名不存在）· `observation_reference_observation_unknown`
     （编号不存在于该图）——三者均 `category="model_draw_error"`。
   - `_claim_links` 改为先翻译再查 `by_locator`；`_claim_links` 严格校验逻辑本身一个字未改。
   - 新增 `derive_observation_reference_catalog` / `format_observation_reference_catalog` /
     `build_observation_reference_catalog_from_run`：从 `_catalog(...)`（唯一出口）机械导出
     `<view>/<observation_id>: allowed claims=[...]`，不含 locator/hash。
2. `src/agent/correction/parse.py`：两处 `producer_segment_ref_prefilled` /
   `producer_resolver_audit_prefilled` 补 `category="model_draw_error"`。
3. `src/agent/correction/finalize.py`：两处内部一致性检查补 `category="input_integrity_error"`。

## 分类表（抛出点 -> category）

model_draw_error：观测引用翻译三种失败 · `_claim_links` 内 existence 缺失/`source_claim_undeclared`/
`manifest_claim_not_observable`/`claim_permission_invalid`/`multiple_windows`/翻译后仍查无 locator ·
`_check_floor_order` 的 `floor_ref_window_mismatch`(plan)/`elevation_floor_mismatch` ·
`_producer_preflight` 两处 · `parse.py` 两处（同一语义的早期重复检查）。

input_integrity_error：manifest/reading 字节解析失败 · `_catalog` 输入集合不等 ·
`duplicate_source_observation`/`duplicate_source_locator` · `verify_window_resolver_inputs`
及 `_against_raw_artifacts`/`_artifact` 全部（持久化产物再认证，非现抽签路径）·
`derive_manifest_direction_facts`/`_check_direction_facts` 全部 · `verify_reading_stage_root_against_accepted_attempt`
全部 · `_check_floor_order` 的 `manifest_floor_ref_non_contiguous`/末尾防御性 `floor_ref_window_mismatch` ·
`_claim_links` 内 `entry` 非 `RequiredViewEntry` 的防御分支 · `finalize.py` 两处。

## 已完成（续）

4. `src/agent/pipeline.py`：
   - `_build_correction_messages` 新增 `observation_reference_catalog: str | None = None` 入参；
     非空时注入 `===== BEGIN/END WINDOW SOURCE OBSERVATIONS =====` 段落，讲清 `<view>/<observation_id>`
     格式 + 禁编哈希/禁裸编号 + existence 必须至少一条引用。
   - `run_correction` 透传 `observation_reference_catalog` 到 `_build_correction_messages`。
   - `run_pipeline_artifacts`：`target.schema_version=="3"` 且 `out_dir` 给定时，调用
     `build_observation_reference_catalog_from_run(run_dir=out_dir, reading_dir=vector_dir)` 拿到清单再传给
     `run_correction`。
5. `scripts/tool_scripts/run_stage.py::_draw_correction`：
   - draw 前：`target.schema_version=="3"` 时同样调用 `build_observation_reference_catalog_from_run`
     并传给 `run_correction`。
   - `build_verified_window_inputs_from_run(...)` 与 `finalize_correction_draw(...)` 两处调用各包一层
     `try/except WindowResolverInputError`：`category=="model_draw_error"` ⇒ 返回 `(geom, rep)`，`rep`
     是一条 `correction.window_source_reference` FAIL（走 stochastic 外层循环归档+盲重抽，
     与 `correction_draw_issues` 分支同构）；`category=="input_integrity_error"` ⇒ 原样 `raise`（硬崩，
     不重抽）。
6. 新测试 `tests/test_f7_observation_reference_translation.py`（15 个测试，全绿）：
   - 翻译正例（观测引用 -> 与手算 `source_locator(...)` 完全相同）+ 向后兼容合法 locator 原样放行；
   - 三格具名失败（图名不存在/编号不存在/裸引用或畸形，4 种畸形值参数化）+ 每格断言 `.category == "model_draw_error"`；
   - prompt 清单机械一致（两视图两观测，`refs == [...]` 精确相等而非"包含"）+ 与 `build_window_source_offer`
     交叉核对（同一 `_catalog` 出口的另一个公开消费者）+ 断言不含 `src:`/64 位 hex；空目录格；
   - `build_observation_reference_catalog_from_run`：manifest 未落盘时返回 `None`（不崩）、落盘后与
     直接调用结果逐字节相同；
   - **失败分类两格走真实 `run_one_stage` 编排**：model_draw_error 走真实 `build_verified_window_inputs_from_run`
     / `_claim_links`（未 mock），归档 attempt 001 FAIL（`checks.json` 含 `correction.window_source_reference`，
     message 含 `observation_reference_observation_unknown`）+ 盲重抽出 attempt 002 PASS（`calls["n"]==2`
     证明第二抽是独立新抽不是重放）；input_integrity_error（reading 产物内重复 stroke id）走真实
     `_draw_correction` 直接 `raise`，`attempts/` 目录从未创建；
   - 两条分类表代表性抽查（`producer_segment_ref_prefilled` = model / `duplicate_source_observation` = input）。

## 双向 neuter 实跑（原样贴）

**neuter 1（翻译逻辑本身）**：把 `_claim_links` 里 `locator = _translate_observation_reference(...)` 改回
`locator = reference`（禁用翻译）：

```
mutated
8 failed, 7 passed in 9.99s
FAILED tests/test_f7_observation_reference_translation.py::test_f7_observation_reference_translates_to_the_real_locator
FAILED tests/test_f7_observation_reference_translation.py::test_f7_ambiguous_or_malformed_reference_is_rejected_never_guessed[/W-01]
FAILED tests/test_f7_observation_reference_translation.py::test_f7_unknown_view_name_is_a_named_model_draw_error
FAILED tests/test_f7_observation_reference_translation.py::test_f7_ambiguous_or_malformed_reference_is_rejected_never_guessed[W-01]
FAILED tests/test_f7_observation_reference_translation.py::test_f7_ambiguous_or_malformed_reference_is_rejected_never_guessed[plan/]
FAILED tests/test_f7_observation_reference_translation.py::test_f7_ambiguous_or_malformed_reference_is_rejected_never_guessed[]
FAILED tests/test_f7_observation_reference_translation.py::test_f7_unknown_observation_id_is_a_named_model_draw_error
FAILED tests/test_f7_observation_reference_translation.py::test_f7_model_draw_error_is_archived_as_a_failed_attempt_and_blind_resampled
```
恰好翻译相关 8 个测试红（正例+4 畸形参数化+未知图名+未知编号+归档集成测试），其余 7 个（向后兼容 locator、
prompt 清单 3 个、input_integrity 硬崩、两条分类表抽查）保持绿——分辨力沿预期断层精确切开。
还原后 `15 passed`。

**neuter 2（run_stage.py 的分类捕获）**：把 `_draw_correction` 里包 `build_verified_window_inputs_from_run`
的 `try/except WindowResolverInputError` 删掉、恢复直接调用（不捕获、不归类）：

```
mutated
1 failed, 14 passed in 10.69s
FAILED tests/test_f7_observation_reference_translation.py::test_f7_model_draw_error_is_archived_as_a_failed_attempt_and_blind_resampled
```
恰好归档+重抽集成测试红（异常直接穿出 `run_one_stage`，不再归档也不再重抽），其余 14 个不受影响。
还原后 `15 passed`。

## 全仓回归（本文件相关子集）

`tests/test_c2_b5_source_routing.py` `test_c2_b5_parent_and_verts.py` `test_c2_b5_artifact_trust.py`
`test_c2_b5_host_resolution.py` `test_f5_window_source_fields.py` `test_audit_remediation_accepted_inputs.py`
→ 206 passed；另 `test_a8_evidence_routing.py test_e2e_break_r2_locks.py test_correction_stability.py
test_correction_blind_retry_r3.py test_f6_provenance_kind_vocab.py test_output_coordinate_contract.py
test_output_coordinate_identity.py test_reading_renders.py test_c2_b2b_envelope_transform.py` → 140 passed。
全仓总数见下方「全仓测试收尾」小节（跑完即补）。

## 全仓测试收尾（`-n auto`，未加 `-m` 过滤）

`2195 passed, 8 skipped, 10 xfailed, 5 failed`（367s）。

**5 个红与本单无关，已核实是 HEAD `3310ed3`（本 worktree 基点，晚于派工单写的基线 `9fd8a9a` 两个提交）
既有的、与 F-7 零关系的失败**：`git stash -u` 摘掉本单全部改动后单独重跑这 5 条，**逐条同样失败**：
- `tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract`
- `tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four`
- `tests/test_gt_from_dxf.py::test_build_only_cli_round_trips_l_candidate_and_nonzero_north`
  （报错 `ValueError: gt_vg_config_path_forbidden`，`src/agent/judge/gt_manifest.py:277` 的路径校验，与
  correction/window_sources/pipeline 均无关）
- `tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor`
- `tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean`

⇒ **净效果**：本单改动零回归、+15 条新锁全绿；派工单写的「基线 2193/10/0」与本 worktree 实际基点
（`3310ed3`，比 `9fd8a9a` 晚两个提交）不一致——中间的 `e6e66d7`/`3310ed3` 两提交（sm25 素材批 + F7 调查）
已带入这 5 条既有红，**不归本单**，如实上报，未擅自修复（越权）。

## §3.2 真实产物跑通 —— 进行中，中途已有强证据

**orchestrator 澄清（收纳）**：那 5 条红是 F-8（干净 worktree 缺 619 个被 `.gitignore` 挡住的活输入文件），
**不是本单引入、也不是 HEAD 既有**——主树全量 2197/10/0。已用 `git check-ignore -v` 核实：本单 §3.2 用到的
全部输入（`run_2026-08-05_smoke_downstream_r2/0_reading/*.json`+`reading_summary.md`+`run_config.yaml`+
`llm.yaml`，以及拷入新 run 的同名文件）**均不在 619 个 gitignored 文件之列**（`check-ignore` 全部 exit 1）
——本单验收证据与 F-8 无关。

**跑法**：`run_2026-08-05_f7_verify_sonnet/` = 拷贝 `run_2026-08-05_smoke_downstream_r2`（07-07 sm21 识图产物
原样复用，e6e66d7 已提交）的 `0_reading/*.json`+`reading_summary.md`+`run_config.yaml`+`llm.yaml` 到新 run 目录，
标准 `run_stage.py flow sm21_anchor run_2026-08-05_f7_verify_sonnet --to 1_correction`（`exploratory` 档，
`orthogonal_polygon` capability_profile，correction=deepseek-v4-pro/high，judge off/review off——沿用该 smoke
run 已定的配置）。

**第一轮（首次 attempt，已落盘的强证据，`1_correction/attempts/001/`）**：

`output.json`（真实 DeepSeek 回复，`correction_raw.txt`/`correction_thinking.txt` 均落盘）里
**15 扇窗全部使用新格式** `source_ids: ["1f_view/S11", "North_view/S5"]` 这类 `<view>/<observation_id>`
观测引用——**零处**是旧的 `src:<64hex>` 或裸编号——证明 prompt 里新增的 WINDOW SOURCE OBSERVATIONS 段落
真的教会了真实模型这个格式。

`attempts/001/checks.json`：
```json
{
  "check_id": "correction.window_source_reference", "status": "fail", "layer": "invariant",
  "message": "window source reference rejected (source_claim_undeclared): {'window_id': 'win_1F_N_1', 'claim': 'appearance'}"
}
```
——模型把同一对观测引用（一条 plan + 一条 elevation）无差别抄给了每个 claim，但 `appearance` 只允许
elevation 来源声明；`_claim_links` 翻译成功（两条引用都能查到对应 locator）后，**在权限校验层正确拒绝**
——这正是「翻译成功、但声明内容本身违规」的 `model_draw_error`，走 gate① FAIL 归档，**没有崩 flow**
（对照修复前：任何 `source_ids` 一律在翻译前找不到 locator ⇒ `_claim_links` 直接 raise、异常穿透整条 flow）。

`_run/run_manifest.json` 此时 `1_correction` 尚无 `accepted_attempt`（符合预期：gate① 阻塞 ⇒ 盲重抽，
不是"修好了立刻通过"，是"不再崩溃、走正常的重抽流程"）。

**中途卡点**：跑 `flow` 的 shell 命令被外层 `timeout 590` 打断（真实 LLM 链路，attempt 1 本身只花了
~71s，之后 flow 应该是在跑 attempt 2 时被 590s 硬顶到期，`exit 143`）——**不是代码缺陷**，是我起初给的
timeout 太紧。已用 `nohup`（不受 Bash 工具单次调用超时约束）重新以同一条命令续跑（manifest-first 会从
1_correction 已有的 1 个 attempt 继续盲重抽，不会重跑 0_reading），跑测中，完成后续补最终 accepted attempt
路径。

## 待做

- [ ] 等 nohup 续跑完成，确认 `1_correction` 拿到 accepted attempt（或查清楚为何budget耗尽被 quarantine——
      若耗尽，如实报告，不伪造/不降档掩盖）。
- [ ] 提交（分文件 add，禁 `-A`；`run_2026-08-05_f7_verify_sonnet/` 产物目录不进提交)。
