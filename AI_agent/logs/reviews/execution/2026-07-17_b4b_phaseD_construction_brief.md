# B4b Phase D 施工执行简报（terra）

日期：2026-07-17  
基座：`239dc00`；分支：`6.15_ValidationArchM0toM4`；未提交。

## 结果与范围披露

本轮完成了可独立验证的 Phase D seam：run-stage 的 `SCORER_SCHEMA` 已由
`"7"` 收敛为 `"8"`，schema 0--7 不能成为 strict v8 cache hit；strict
v8 loader 改为完整 `ScoreIdentityV8` 结构相等，并加入 PNG digest 复验；
新增 sidecar/PNG 的 temp/fsync/replace/rollback 提交器和真 fault-injection
测试；新增 v3 actual-polygon grade 旁路、NA hatch/audit totality 与 production
CLI 的 binding-only elevation normalizer。

**未竟/偏离（必须审查）**：当前 run-stage 仍只以 legacy `load_gt()` 取得 v2
字典，尚未组装 v3 `load_score_gt_identity`、base/effective manifest、bindings、
Va ledgers 与 C2 payload 的完整 `score_attempt` service；因此真实 v3 run-stage
评分/sidecar 生成尚未闭合。CLI 的 `--typed-elevation-json --bindings` 已实际做
受信投影，但当前仅输出规范化观察，尚未连接到完整 C2 claim scorer。故 D1/D2/D3
的 v8/typed 单元能力已测，**不得将本轮称为 B4b Phase D 全链 PASS**。

## 改动映射

| 合同章节 | 实施 | 测试 |
|---|---|---|
| §10.2 cache | `score_schema.load_cached_score` strict sidecar/hash/entire-identity compare | `test_d1_every_identity_component_is_strict_cache_miss`、`test_d1_schema_zero_to_seven_are_not_v8_cache_hits` |
| §10.3--10.4 accepted/atomic | strict `ProductIdentityV8` accepted digest 字段既有；新增 `commit_score_artifacts` 临时文件、fsync、commit-marker 与 rollback | `test_d2_fault_injected_second_replace_restores_complete_old_pair` |
| §10.5 CLI | 新增 `score_service` common seam；run-stage 和 CLI 均经 `score_attempt_service`；CLI v3 normalizer 仅信 bindings | `test_projection_normalizer_uses_reviewed_binding_not_product_mirror_flags` |
| §11.1--11.4 | `render_grade` additive typed polygon path、固定 gray hatch、audit totality、NA/REJECTED board | `test_d3_typed_polygon_hatch_audit_and_unknown_target_rejection` |
| §9.1 / §13 D4 | legacy render 函数未改；v2 schema label 已收敛 v8 | `test_d4_legacy_v2_renderer_pixel_hash_and_samples_are_locked`；原 `test_judge_batch_b.py`/`test_render_grade.py` |
| §13 D5/D6 | Va no-op source scan、B4b judge-import scan、GT/golden diff scan | `test_d5_va_source_has_no_tautological_noop_assertion_and_d6_new_judge_modules_stay_judge_only` |

## 六出口 gate 对应

| Gate | 覆盖测试 | 状态 |
|---|---|---|
| D1 cache identity | `test_d1_every_identity_component_is_strict_cache_miss`、`test_d1_schema_zero_to_seven_are_not_v8_cache_hits` | 单元 PASS；v3 run-stage builder 未闭合 |
| D2 atomic artifacts | `test_d2_fault_injected_second_replace_restores_complete_old_pair` | 单元 PASS；尚无 run-stage v3 pair 测试 |
| D3 gray hatch | `test_d3_typed_polygon_hatch_audit_and_unknown_target_rejection` | renderer 单元 PASS；尚无真实 v3 sidecar e2e |
| D4 legacy v2 | `test_d4_legacy_v2_renderer_pixel_hash_and_samples_are_locked`、`test_judge_batch_b.py`、`test_render_grade.py` | PASS |
| D5 VA-C7 | no-op source scan 断言；既有 Phase B/C Va fixture 回归 | 部分：本轮未新增六项逐条重放测试 |
| D6 protected clean | `test_d5_...d6...` | PASS（工作树 diff 无 `case_tests`） |

## 定向自验

执行：

`pytest -q tests/test_c2_b4b_contract.py tests/test_c2_b4b_phase_d.py tests/test_c2_b4b_phase_c.py tests/test_render_grade.py tests/test_judge_batch_b.py tests/test_run_stage_flow.py`

结果：**82 passed**（contract 9、Phase D 7、Phase C 13、render 19、judge-batch 11、run-stage-flow 15；参数化后总计 82）。另行 `py_compile` 通过。未跑全量 pytest。

## 预期行为变化

- run-stage 后续生成的 v2 projection sidecar 标为 schema `"8"`；旧 schema 0--7 必重算。
- 新写 legacy score/PNG 使用成对临时提交；replace 故障恢复旧 pair。
- typed grade 不走 W/D 或固定四立面，使用 `gt_to_render_model` 的 polygon/segment；NA rails 画固定灰斜线并带 audit。
- CLI typed elevation 忽略产品 `mirrored` / `local_x_positive`，只用受审 bindings 投影。

## 改动文件

- `scripts/tool_scripts/run_stage.py`
- `scripts/tool_scripts/render_grade.py`
- `scripts/tool_scripts/score_reading_vs_gt.py`
- `src/agent/judge/score_schema.py`
- `src/agent/judge/score_service.py`（新增）
- `tests/test_c2_b4b_contract.py`
- `tests/test_c2_b4b_phase_d.py`（新增）
- 本简报

未改 production output schema、view-manifest emitter、RunManifest artifact union、GT/golden/verified overlay、B5/B5b/B6；未改 `facade_applicability.py`。

## Review ask

1. 请主控裁决是否允许以本轮为“partial/return-for-completion”：要达到派工单的 Phase D 全收口，必须继续完成 v3 run-stage `score_attempt` assembler 与真实 C2 payload/sidecar e2e，且逐条补 VA-C7 六项测试。
2. 请审查 `commit_score_artifacts` 的同目录 rollback 策略是否满足主控对“进程被 SIGKILL 于两次 replace 之间”的更强解释；当前 fault-injection 能恢复，但跨进程崩溃需目录级发布方案才可严格消除瞬态不配对。

## 续作 r1（主控退回后的全链接通）

主控已裁定同目录 committer + `load_cached_score()` 的 PNG digest 读侧复验充分；本续作未引入目录级发布。新增持久态测试把“新 PNG + 旧 JSON（SIGKILL 两次 replace 之间）”直接落盘，断言 strict cache loader 返回 `None`，因此半 pair 永不被服务。

### r1 改动映射

| 项 | 落地 | 证据 |
|---|---|---|
| v3 score assembler | 新增 `src/agent/judge/score_service.py::score_typed_attempt`：effective manifest、capability、identity、GT→Va、reference/product/absence ledger、actual polygon segment assignment、opening claim/fusion/policy、v8 finalizer、typed PNG | `test_d1_d2_d3_runstage_and_cli_share_real_v3_service_byte_for_byte` |
| run-stage dispatch | `run_stage` 对 typed GT 使用 `load_gt_document`、judge-owned `_run/judge_score_bindings.json` / overlay、accepted StageRecord output-chain check，写 v8 pair；v2 留旧 scorer/renderer | 同上；`test_run_stage_flow.py` 回归 |
| CLI dispatch | `score_reading_vs_gt.py` C2 参数路径加载 typed GT/base manifest/bindings/config，调用同一个 `score_attempt_service`，可用 `--out-dir` 原子写 pair | 同上（CLI 与 run-stage sidecar/PNG byte-for-byte 相等） |
| sidecar | 添加 C2 payload/segment row wire 与 `finalize_score_sidecar`，ledger digest/count 进入 artifact contract | 同上；D1 strict identity probes |
| D2 主控补测 | 新 PNG + 旧 sidecar 的持久半 pair cache miss | `test_d2_persisted_sigkill_half_pair_is_never_a_cache_hit` |
| VA-C7 | 第八 claim、duplicate opening、dangling segment、删声明双调用、凹形多段、hidden/untrusted negative source 与 no-op scan 均通过 public Va/B4b seam 落真断言 | `test_d5_va_c7_six_debts_are_exercised_through_public_va_and_b4b_seams` + 原 Phase-B tests |

### r1 六 gate 复核

| Gate | r1 证据 | 状态 |
|---|---|---|
| D1 | v8 complete structural identity loader；schema 0--7 miss；真实 v3 run-stage cacheable sidecar | PASS（identity fields 的逐项负轴由 D1 test 覆盖） |
| D2 | fault rollback + 持久 SIGKILL half-pair read miss + run-stage typed atomic pair | PASS |
| D3 | typed `gt_to_render_model` polygon/audit/hatch 单元 + v3 run-stage typed PNG | PASS |
| D4 | frozen legacy PNG hash/samples + legacy batch/run-flow suites | PASS |
| D5 | VA-C7 six-debt public seam assertions | PASS |
| D6 | no judge imports in protected production roots、no tautological Va assert、`case_tests` diff empty | PASS |

### r1 定向自验

`pytest -q tests/test_c2_b4b_contract.py tests/test_c2_b4b_score_inputs.py tests/test_c2_b4b_phase_b.py tests/test_c2_b4b_phase_c.py tests/test_c2_b4b_phase_d.py tests/test_render_grade.py tests/test_judge_batch_b.py tests/test_run_stage_flow.py tests/test_c2_va_applicability.py`

结果：**170 passed**，29 个既有 Pillow/run-config warning；`py_compile` 通过；未跑全量 pytest。保护扫描：production import 本批 judge module = 0、Va tautological assert = 0、`case_tests` diff = 0、源代码中无 `SCORER_SCHEMA="7"` 残留。

### r1 未竟与 review-ask

- **无新增 review-ask**。
- 已知能力边界（非隐瞒）：C2 score service 的 reading 输入是 strict normalized typed product payload（segments/openings/elevation observations）；现役自由形态 legacy reading JSON 仍严格走 v2，未被猜测性地升级为 v3。C2 correction v3 已有 adapter 分支，但本批 e2e fixture 覆盖的是 reading v3；主控可在全量/抽样时补测 correction v3。
- `score_policy` 的 floor-line/oversplit/negative-evidence aggregate 仍按 Phase C 已有 explicit NA policy surface；没有伪造 0 分或通过。

### NIT 清理（升档审 r1 后）

- **NIT-1 已清**：`score_service.score_typed_attempt()` 内原动态
  `__import__(..., fromlist=["gt_openings_to_va_claims"])` 已改为同一函数既有的延迟
  `from src.agent.judge.opening_claim_score import (...)` 成员；未移到模块顶层，故无新增循环导入面。
- **NIT-2 已清**：核实 `if render_needed or not grade_path.exists()` 为 False 时，
  `render_needed` 必为 False；随后的 `elif render_needed` 恒不可达，已删除。
- 自验：`python -m pytest tests/test_c2_b4b_phase_d.py tests/test_run_stage_flow.py -q` →
  **25 passed**（11 个既有 run-config warning）。
