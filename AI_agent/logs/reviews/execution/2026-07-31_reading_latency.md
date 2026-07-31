# 执行日志 · Reading latency（批量探针 + prescan 信噪比）

> 施工席：sol（GPT，construction）· 主控：Opus 5 · 2026-07-31
> 基线：`cd074a9`，控制器已确认 **1951 passed / 10 xfailed / 0 failed**
> 用户优先级：wall-clock latency 高于 token cost；降低顺序往返，绝不减少测量。

---

## 0. 当前状态

| Item | 状态 | 交付 |
|---|---|---|
| Item 1 · bounded batch probing | 已实现、受影响子集与 12 个 neuter 均通过 | 待本 item 边界提交 |
| Item 2 · prescan split presentation | 待施工 | — |
| 70-shape DENY/ALLOW differential | 待两 item 完成后执行 | — |
| 全仓 | 待交付前唯一一次全仓 | — |

## 1. Item 1 · bounded batch probing

### 1.1 接口与不变量

新增第三种、严格四 token 的调用形状：

`python tools/run_cv_probe.py --batch requests/<name>.json`

batch envelope 恰为 `{"requests": [...]}`；每项恰含 `id` / `tool` / `args`。`id` 必须匹配
`^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$` 且 batch 内唯一。`MAX_PROBE_BATCH_SIZE = 32`，空 batch
与 33 项以上均拒绝。20-probe sweep 因而被覆盖，但工作量有硬上界。

安全关键点没有另写 batch validator：

- legacy `--request` 调 `_validate_probe_request_data(data, root)`；
- `--batch` 先由 `parse_probe_batch(data)` 验 envelope，再对每个普通 request 调**同一个**
  `_validate_probe_request_data(request, root)`；
- 该函数唯一委托 `_validate_probe_params(_walk_items(data), root)`，所以 lexical check、
  path-role-by-key-name、`out/` output-root 三条与单请求完全同源；
- guard 读完整 batch、验完整 batch 后才 ALLOW。任一 inner request 失败，wrapper 根本不启动。

wrapper 侧同样从 staged `guard.py` import `parse_probe_batch`，不复制 size/id/envelope policy。
随后先把所有 request 走 `_request_to_argv`，再把所有 argv 走 `cv_probe.parse_probe_args`，两轮
均为 eager list；只有全体 preflight 成功才进入 `execute_probe` 循环。因此绕过 hook 直跑 wrapper
时，第二项 output-root 错误、未知 tool option、缺 `crop_zoom --bbox` 均不会让第一项先落盘。

`scripts/tool_scripts/cv_probe.py` 把原 `main()` 拆成共享的 `build_parser()`、
`parse_probe_args()`、`execute_probe()`；single 与 batch 调的是同一个 executor。旧 single 行为保留：
非 prescan 不打印路径，prescan 仍打印 copy-guard 可识别的 absolute landing path。

成功 batch 的 stdout 是一个 JSON 文档：`batch_schema=1`、`request_count=N`、按请求顺序排列的
`results`。每项带稳定 `id`、`tool`、staging-relative `sidecar` 和该 sidecar 的完整 JSON `result`。
所以 Bash 一次返回即可消费 N 个结果；同时 N 个普通 append-only sidecar 照旧落盘。测试实证
batch sidecar 与逐个 legacy `--request` 生成的 sidecar byte-identical。

### 1.2 directive 同步

`reader_directive.md` §2 已加入 up-to-32 batch schema、命令和失败原子性；明写正常 20-probe
sweep 是一次 `Write` + 一次 `Bash`，且 batching 只降 latency、不降 logical probe 数。§6 effort
log 改为分别报 logical probes、batch Bash calls、one-off Bash calls，防止把 20 项 batch 误记成
“只测了一次”。§7 shell allowlist 同步为三种 form。single direct 与 legacy request 说明均保留。

### 1.3 受影响子集

路由命令：

`python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/isolation_templates/guard.py src/agent/execution/isolation_templates/run_cv_probe.py scripts/tool_scripts/cv_probe.py tests/test_isolation.py`

输出：`SCOPE: SUBSET`，选择
`tests/test_affected_tests_map.py tests/test_cv_toolbox.py tests/test_gt_discipline.py tests/test_isolation.py`。

执行命令：

`python -m pytest -p no:cacheprovider -q tests/test_affected_tests_map.py tests/test_cv_toolbox.py tests/test_gt_discipline.py tests/test_isolation.py`

结果：**212 passed in 62.29s**。

### 1.4 Item 1 neuter 自查（全部实际定点破坏、实际跑红、随后逐项恢复）

| # | 定点破坏 | 实际红测试 |
|---|---|---|
| B1 | `_validate_batch_file` 不再调用 `_validate_probe_request_data` | `test_guard_refuses_whole_batch_when_any_request_fails_single_request_validator[lexical-bad_entry0]`、`[output_role-bad_entry1]`、`[path_role_bare_symlink-bad_entry2]`（3 red） |
| B2 | batch-size 分支改 `if False` | `test_guard_enforces_finite_probe_batch_bound` |
| B3 | empty-batch 分支改 `if False` | `test_guard_rejects_ambiguous_probe_batch_envelopes[empty]` |
| B4 | duplicate-id 分支改 `if False` | `test_guard_rejects_ambiguous_probe_batch_envelopes[duplicate_ids]` |
| B5 | id regex/type 分支改 `if False` | `test_guard_rejects_ambiguous_probe_batch_envelopes[invalid_id]` |
| B6 | `_check_bash` 的 `--batch` form 分支改 `if False` | `test_guard_allows_bounded_probe_batch_and_logs_every_request_path` |
| B7 | wrapper 的 `cv_argvs` 与 `planned` 两个 eager list 均改 lazy generator | `test_wrapper_preflights_entire_batch_before_first_probe_executes[outside_output-bad_entry0]`、`[tool_specific_unknown_option-bad_entry1]`（2 red；第一项 sidecar 实际出现） |
| B8 | aggregate 的 `id` key 改名 | `test_probe_batch_returns_one_document_with_stable_ids_and_own_sidecars` |
| B9 | aggregate 不读 sidecar、固定 `result={}` | `test_probe_batch_returns_one_document_with_stable_ids_and_own_sidecars` |
| B10 | execution loop 静默截成 `planned[:1]` | `test_probe_batch_returns_one_document_with_stable_ids_and_own_sidecars`（`request_count` 实际 1） |
| B11 | wrapper 不 import shared `parse_probe_batch`，改成本地无界 list comprehension | `test_wrapper_independently_enforces_shared_probe_batch_bound`（实际执行 33 probes） |
| B12 | `parse_probe_args` 移除 crop 的 preflight `--bbox` required check | `test_wrapper_preflights_entire_batch_before_first_probe_executes[tool_specific_missing_bbox-bad_entry2]`（第一项 sidecar 实际出现） |

假锁专项检查：刻意选“合法项在前、非法项在后”，防止“根本没进入第一项”让 atomicity 断言空绿；
aggregate 夹具用两个不同 tool 与两个非 auto 可碰巧产生的 explicit sidecar names；bound 夹具从生产
constant 派生 `maximum + 1`。本轮 12 个 neuter 首轮均真红，**未发现假锁**。

---

## 2. Item 2 · prescan signal-to-noise

待施工。

## 3. 最终安全差分、全仓与受保护资产

待两 item 完成后填写。

## 4. Review-ask

待最终填写。
