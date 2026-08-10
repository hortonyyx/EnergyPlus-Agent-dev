# F-21 调查：`approve_geometry` 在 `res.blocked` 时的行为

**结论：不是已证实的缺陷；现有证据更支持“几何检查点”的有意局部作用域。**
`approve_geometry` 的确会在 `geometry_digest != None && res.blocked` 时签发；但唯一真实命中的
run 是明确声明“只重跑 2→5、刻意不重跑 0_reading”的 F-13 局部验收。它已有 `flow:auto` 批准、
4_mep/5_intakeoutput 已接受。把闸门改成 `res.blocked` 会阻断该真实工作流的**未来/重新**批准，
却不会撤销已存批准。没有证据表明这条作用域在当初被设计为“任何全 run 问题都不得签几何”。

范围：只读调查；没有修改生产码或测试。基线为 `HEAD 78194f8a57b6114f67e0ffd6c141bae74cee6ea4`。
初查时工作树只有未跟踪的派工单；调查后 F-20 施工席开始修改
`src/agent/execution/validation_run.py` 和两份测试文件。因此本报告所有源码判断、历史与实测数字
均来自该文件仍与 HEAD 相同的初查时；没有把 F-20 在途修改计为 F-21 事实或缺陷。

## Q1｜引入历史与设计理由

命令（在 HEAD 基线上执行）：

```bash
git log --all --oneline -S 'if res.geometry_digest is None:' -- src/agent/execution/step_orchestrator.py
git blame -L 480,492 -- src/agent/execution/step_orchestrator.py
git show -s --format=fuller 525091ba
```

输出锁定引入提交为 `525091ba897da9f6318035d9cca3e3de1a365cf4`
(`6.19_StepwiseJudgeLoopAndOfflineGeometryViewer`，2026-06-19)，blame 对第 487–488 行也是
该提交。其 commit message 的相关原文为：

> 新增 `src/agent/execution/step_orchestrator.py`（…`approve_geometry` +
> `orchestration_state.json`）+ CLI `scripts/tool_scripts/run_stage.py`
> （run/judge/resample/approve-geometry/status，**几何阻塞门：未 approve 拒 4_mep**）。

该 message **没有说明**为何本函数用 `geometry_digest is None` 而非 `res.blocked`/`all_passed()`；
故不能据此断言“当初疏忽”，也不能把当前注释冒充提交理由。

相关但不是该判据引入提交的 `06d01a0`（`6.15_ValidationFixReverify`）message 原文说：

> The geometry digest is computed ONLY after the on-disk 2/3 artifacts pass
> consistency and 2_modelling passes, so an approval can never bind to
> stale/garbage bytes.

这说明 digest 的已记录语义是“可绑定的 2/3 几何检查点”，不是整个 run 的清关；但它没有填补
`525091ba` 对“为何忽略其他 stage 的 BLOCK”的缺失理由。

现有消费者中，能被收紧而“按旧行为算错”的具体真实对象是 F-13（Q2/Q5）：它今后若需要重新/自动
签发会失败。未找到能把“某人/某外部消费者依赖该忽略行为”写入引入 commit message 的证据。

## Q2｜可达性（真实语料 + 隔离落盘证明）

可复跑脚本为 [`repro.py`](repro.py)。其候选定义是 `case_tests/e2e_tests/` 下直接含有
`validate_case` 原生 stage 目录（0_reading 或 1..5）的目录；不读取
`case_tests/test_baseline/gt/`。它对每个候选执行：

```bash
python AI_agent/logs/experiments/2026-08-10_f21_approve_geometry_blocked/repro.py --prove
```

实际初查命令等价于：

```python
validate_case(run_dir, case_dir=case_for(run_dir),
              policy=effective_run_policy(run_dir), write_reports=False)
```

结果：46 个候选均执行成功（0 error）；46 个 `blocked=True`；仅 1 个 digest 非空，且正好也是
唯一的 `digest != None && blocked=True`：

```text
case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f13_e2e_verify
geometry_digest = bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8
blocked = True
blocking check_id = 0_reading:0_reading.build
summary = required artifact missing: 0_reading/*_view.json
```

这不是“结构上不可能”；是真实盘上组合。为排除“只得到对象、实际保存时另有门”的可能，另在 `/tmp`
复制该 run、排除已有 `_run/geometry_approval.json` 后调用真实 `approve_geometry`（源 case_data 仅读）：

```text
before_digest = bed87c...e8a5c8
before_blocked = True
approve_returned = True
approval_path_exists = True
saved_digest = bed87c...e8a5c8
after_geometry_approved = True
after_blocked = True
after blocking = 0_reading: 0_reading.build — required artifact missing: 0_reading/*_view.json
```

因此“会签发并落盘”已被证明，而不是从 `if` 推演得来。实现依据：
`src/agent/execution/step_orchestrator.py:462-498` 仅在第 487 行检查 digest；
`src/agent/execution/validation_run.py:303-320` 仅以 2_modelling/2-3 一致性计算 digest，
第 438-448 行才独立汇总 `blocked`。

## Q3｜实际后果与调用路径

所有生产调用点由以下命令追到：

```bash
git grep -n -E 'approve_geometry\(|geometry_is_approved\(' HEAD -- ':!case_tests/test_baseline/gt/**'
```

- 人工：`scripts/tool_scripts/run_stage.py:2458-2471` 的
  `cmd_approve_geometry` 调同一函数；成功即 `mark_geometry_approved`，打印“4_mep is now
  unblocked”。无 `res.blocked` 二次检查。
- 自动：`run_stage.py:2648-2666` 在 `AWAITING_GEOMETRY_APPROVAL` 且 `--geometry auto` 时调同一
  函数、标记后 `continue`，故会续跑。
- 续跑谓词：`geometry_is_approved`（`step_orchestrator.py:501-508`）仅返回
  `validate_case(...).geometry_approved`。`run_stage.py:2100-2123`、2334-2338、2592-2601 的
  调用只用这个 digest 匹配结果；没有 `res.blocked` 拦截。
- `cmd_run`（`run_stage.py:2296-2355`）可以直接请求某一 stage；它只把上述
  `geometry_is_approved` 传给 `run_one_stage`，不验证所有更早 stage。`cmd_flow --from auto`
  的 `_auto_start_stage`（2126-2149）查的是 accepted manifest/judge/review/geometry approval，
  也不调用全 scope `res.blocked`。

真实后果有盘上佐证：F-13 的 `run_config.yaml:1-24` 明写“只重跑 2_modelling → … →
5_intakeoutput”及“不重跑 0_reading / 1_correction”；其 `_run/geometry_approval.json` 是
`actor: "flow:auto"`, `note: "flow --geometry auto"`；同一 run 的
`_run/run_manifest.json` 已接受 `4_mep` 和 `5_intakeoutput`，`_run/orchestration_state.json` 也记有
`geometry_approved: true` 及两 stage 的 `deterministic_pass`。故自动路径实际可以、且已经在此
局部重验工作流中继续向下走；人工路径共享签发函数与恢复谓词，后果一致。

没有发现另一道基于 `res.blocked` 的批准/恢复门。它不是“无害的额外拦截”，而是刻意按几何 digest
而非全 run validation 断言的路径。

## Q4｜测试覆盖

静态枚举命令：

```bash
git grep -n -E 'approve_geometry|geometry_is_approved|geometry_digest|AWAITING_GEOMETRY_APPROVAL|confirmation_blocks' HEAD -- tests
```

可执行的局部正向锁包括：

- `tests/test_step_orchestrator.py:398-405`：已批准时 3_split_pairing 前进；
  `:421-428`：已批准时 4_mep 前进。
- `tests/test_run_stage_flow.py:425-463`：auto 路径传 `actor="flow:auto"`、`policy="auto"`，
  但把 `approve_geometry` mock 掉。

`tests/test_validation_run_baseline.py:70-74` 也断言正常 run 产生 digest，但带
`@_RERECORD_XFAIL`，故不能把它计为当前绿态的可观测正向锁。

负向锁包括：

- `tests/test_step_orchestrator.py:390-395` 与 `:407-419`：未批准停止、4_mep 在 draw 前拒绝。
- `tests/test_validation_run_baseline.py:130-156`：2/3 缺失、坏 specs、坏 geometry 时，BLOCK 且
  digest 为 None。
- `tests/test_validation_run_baseline.py:112-127`：全 run/单件缺失会 BLOCK。

但**没有**测试同时构造 `geometry_digest is not None` 与 `res.blocked is True`，再断言
`approve_geometry(...) is None` 或不写 approval；也没有相反的显式行为锁。现有 auto-flow 测试把
`approve_geometry` mock 掉，因此不能观察其真正判据。结论是：该特定政策边界零覆盖，正反两种
期望都未被锁住；现有绿测只锁住其周边 stage gate/CLI 参数，未锁住真正的 approval 判据。

已执行的相关小集合（不是全仓）：

```bash
pytest -q \
  tests/test_step_orchestrator.py::test_geometry_checkpoint_blocks_when_unapproved \
  tests/test_step_orchestrator.py::test_geometry_checkpoint_advances_when_approved \
  tests/test_step_orchestrator.py::test_mep_refused_until_geometry_approved \
  tests/test_step_orchestrator.py::test_mep_runs_when_approved_no_enabled_judge \
  tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy \
  tests/test_run_stage_flow.py::test_R1_5_approve_geometry_uses_frozen_policy_check_headers \
  tests/test_run_stage_flow.py::test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers \
  tests/test_validation_run_baseline.py::test_empty_run_blocks_not_silent_pass \
  tests/test_validation_run_baseline.py::test_missing_single_artifact_blocks \
  tests/test_validation_run_baseline.py::test_missing_geometry_artifact_no_bogus_digest \
  tests/test_validation_run_baseline.py::test_bad_geometry_specs_blocks_no_digest \
  tests/test_validation_run_baseline.py::test_bad_building_geometry_blocks_no_digest \
  tests/test_execution_foundation.py::test_confirmation_policy_blocking
```

输出：`13 passed, 1 warning in 12.20s`。

## Q5｜定性、blast radius 与建议

**定性：无害的（且当前有用的）几何检查点作用域选择，非 F-21 真缺陷。**
“digest 非空且 full-scope validation blocked 时仍能批准”这个命题为真，但没有证据证明它违反了
该门的契约；相反，F-13 明确只验证下游 2→5，历史 message 也把 digest 约束到经过 2/3 一致性检查的
几何字节。该批准不是“全 run 清关/发布许可”，而是“绑定当前几何 checkpoint 后让 4_mep 可走”的许可。

建议方向：**不要把现有闸门直接改成 `res.blocked`。**若产品要新增“仅当全 run 无 BLOCK 才能继续”的
要求，应另行决定局部重验/复用上游产物是否仍为合法模式，并建立独立的 full-run readiness 门（及其
正、负锁），而不是改变 geometry approval 的既有语义。

实测 blast radius：46 个真实候选中仅 F-13 当前满足 digest 非空；因此按 `res.blocked` 收紧，
**1 个真实 run** 会从“现在可重新签发”变为“不能签发”：
`sm21_anchor/run_2026-08-07_f13_e2e_verify`（原因 `0_reading.build`）。该 run 当前已有同 digest 的
approval；只改签发谓词不会使已存在的 approval 失效（`geometry_is_approved` 仍只比较 digest），但在
重算 digest、approval 丢失或要求再次批准时会阻断其记录的 F-13 工作流。

## 未能证实（明确留白）

- `525091ba` 的 commit message 没有交代“为何不看 `res.blocked`”；查到引入提交，但**查不到该具体
  理由**。
- 没有在真实语料找到“`1_correction` 的语义 check FAIL、2/3 仍可 digest”的样本；唯一命中是有意
  缺 `0_reading` 的局部重验。因而不能把该样本外推成任意 1_correction 失败都应/不应批准。
- 没有重放 F-13 的完整 LLM flow（会超出只读/零生产调用边界）；盘上 auto-approval、manifest 与 state
  是实际后果证据，但不能单凭无时间戳的 metadata 重建每一条 CLI 命令的精确时序。
- 语料扫描只涵盖上述 46 个原生 `validate_case` 布局；历史的非原生 `output_*` 目录不被当作可传给
  `validate_case` 的 run，且依令未读取任何 `case_tests/test_baseline/gt/`。
