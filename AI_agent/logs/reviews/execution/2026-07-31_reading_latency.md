# 执行日志 · Reading latency（批量探针 + prescan 信噪比）

> 施工席：sol（GPT，construction）· 主控：Opus 5 · 2026-07-31
> 基线：`cd074a9`，控制器已确认 **1951 passed / 10 xfailed / 0 failed**
> 用户优先级：wall-clock latency 高于 token cost；降低顺序往返，绝不减少测量。

---

## 0. 当前状态

| Item | 状态 | 交付 |
|---|---|---|
| Item 1 · bounded batch probing | 已完成 | `ef45bda` `7.31_BoundedBatchProbing` |
| Item 2 · prescan split presentation | 已实现、受影响子集与 10 个 neuter 均通过 | 待本 item 边界提交 |
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

### 2.1 输出布局与不丢数据证明

`prescan/cv_evidence/<image_stem>/prescan/` 现在写八个文件：

| 文件 | 内容 |
|---|---|
| `structural_candidates.json` | 仅 `line_band_candidate`（默认给 reader） |
| `cc_box_candidates.json` | 仅 `cc_box_candidate` |
| `tick_candidates.json` | 仅 `tick_candidate` |
| `candidates.json` | 原有 lossless 全候选 master，保留兼容与审计 |
| `combined_overlay.png` | **仅 structural line bands**（默认 overlay） |
| `cc_box_overlay.png` | boxes 单独可视化 |
| `tick_overlay.png` | ticks 单独可视化 |
| `all_candidates_overlay.png` | 原 combined-overlay 的全候选呈现仍可达 |

master 新增 relative `candidate_files` / `overlay_paths` index；每个 kind view 带 stable candidate
objects 原样子集、`candidate_count`、relative overlay pointer。`overlay_path` 从 caller-dependent path
改成 `combined_overlay.png`，所有 presentation pointers 均相对同目录，因此相同 image/config 在不同
output roots 下所有 4 JSON + 4 PNG 均 byte-identical。

不丢数据不是只比 split 与 master：测试同时把 master 各 kind 实际数与 detector diagnostics 的
`line_band_candidate_count` / `cc_box_candidate_count` / `tick_candidate_count` 对死，再断言三份 view
顺序拼接后与 master `results` object-for-object 完全相等且 candidate ID 无重复。这样 upstream 在
形成 master 前丢一个 kind 也会红（见 §2.4 抓到的假锁）。

真实 sm24 `1f_view.png` 实跑：

```text
TOTAL       803
structural  348   structural_candidates.json = 271553 bytes
cc_boxes    189   cc_box_candidates.json      = 123799 bytes
ticks       266   tick_candidates.json        = 206416 bytes
all               candidates.json             = 628093 bytes
```

即默认 reader JSON 从约 628 KB 降到约 272 KB（约 -57%），但 803 项全部仍可达。default
`combined_overlay.png` = 140111 bytes；lossless `all_candidates_overlay.png` = 162611 bytes。

### 2.2 staging copy guard 与 directive

`src/agent/execution/isolation.py` **无需生产改动**：既有
`src.glob("*/prescan/**/*")` 与 `_is_run_prescan_path` 已接受 prescan leaf 下任意文件。锁把真实八文件
全部放进 formal run 的 prescan leaf，production build 后逐文件 byte compare，实证八个都进入
`staging/prescan/cv_evidence/<stem>/prescan/`。neuter 把 glob 收窄成只复制 `candidates.json` 后该锁真红。

`reader_directive.md` §3 已同步：先读 `structural_candidates.json` + `combined_overlay.png`；boxes/ticks
按需读各自 JSON/overlay；`candidates.json` + `all_candidates_overlay.png` 是 lossless fallback。并明确
“structural”只是 line-band presentation bucket，不是 wall 语义，任何 stroke 仍须 §2 probe measurement。

### 2.3 受影响子集

路由命令：

`python scripts/tool_scripts/affected_tests.py --changed src/agent/reading/cv_toolbox/recipes.py tests/test_cv_toolbox.py tests/test_isolation.py`

输出：`SCOPE: SUBSET`，选择
`tests/test_affected_tests_map.py tests/test_cv_toolbox.py tests/test_gt_discipline.py tests/test_isolation.py`。

执行命令：

`python -m pytest -p no:cacheprovider -q tests/test_affected_tests_map.py tests/test_cv_toolbox.py tests/test_gt_discipline.py tests/test_isolation.py`

追加 anti-false-lock count assertion 后的最终结果：**215 passed in 58.98s**。prescan targeted subset：
`python -m pytest -q tests/test_cv_toolbox.py -k 'prescan' tests/test_isolation.py::test_build_copies_run_prescan_and_kickoff_mentions_it`
→ **16 passed in 13.35s**。

### 2.4 Item 2 neuter 自查（10 个定点；抓到并修复 1 把假锁）

| # | 定点破坏 | 实际结果 / 红测试 |
|---|---|---|
| P1 | `line_band_candidate` kind bucket 改为全 candidates | `test_prescan_kind_views_are_lossless_and_separately_addressable`、`test_prescan_default_overlay_is_structural_only_and_other_kinds_remain_visible`（2 red） |
| P2 | default `combined_overlay.png` 改画全 candidates | `test_prescan_default_overlay_is_structural_only_and_other_kinds_remain_visible` |
| P3 | `all_candidates_overlay.png` 改画 structural only | 同上（all/default 实际 byte-equal） |
| P4 | 不生成 `cc_box_overlay.png` / `tick_overlay.png` | 同上（文件缺失） |
| P5 | master `overlay_path` 从 relative name 退回 `str(overlay_path)` | `test_prescan_same_image_is_byte_identical_across_output_roots`（仅 `candidates.json` bytes 不同） |
| P6 | `tick_candidates.json` 的 `results` 静默置空 | `test_prescan_kind_views_are_lossless_and_separately_addressable` |
| P7 | `_write_reproducible_json` 在 existing-path 比较前多加一字节 | `test_prescan_idempotent_candidates_json` |
| P8 | isolation copy glob 从 `*/prescan/**/*` 收窄为 `*/prescan/candidates.json` | `test_build_copies_run_prescan_and_kickoff_mentions_it` |
| P9 | master 的 `structural` address 错指 `candidates.json` | `test_prescan_plan_schema_and_combined_overlay`、`test_prescan_kind_views_are_lossless_and_separately_addressable`（2 red） |
| P10 | upstream `raw_candidates` 删除 `cc_candidates` | **初轮 2 passed（假锁）**；修锁后 `test_prescan_kind_views_are_lossless_and_separately_addressable` 真红，实际差异 `cc_box_candidate: 0 != diagnostics: 1` |

**假锁说明**：初版“lossless”只证明 `split == master`。若 production 在 master 形成前就丢 boxes，
两边会一起少，断言仍绿；default-overlay 夹具还有 ticks，所以 all/default 仍不同，也绿。这正是本批
已多次出现的“夹具同时满足另一条断言”族。修法是增加 detector diagnostics → emitted master →
split views 的两段守恒；P10 同一破坏复跑后已真红。

## 3. 最终安全差分、全仓与受保护资产

待两 item 完成后填写。

## 4. Review-ask

待最终填写。
