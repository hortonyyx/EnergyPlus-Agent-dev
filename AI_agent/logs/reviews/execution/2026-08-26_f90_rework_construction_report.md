# F-90 四阻断返工施工报告（GPT 施工席）

**状态：STOPPED-BY-DISPATCH-GUARD。** F-102、F-103、F-90 第 6 处、F-100、F-101 均已落地并通过各自红绿锁；更正后的判据 A 通过；判据 B 触发派工单 §五第 5 条，未伪造十判据读数。工作树未提交、未推送。

## 〇、起点、范围与当前 diff

- 本轮起点：`b735db4673d28891005eec7acf3d81450533287c`（第 1/1b/2 项检查点）。
- 当前分支：`08.23_AsDrawnReading`。
- 未执行 `commit` / `push` / `reset` / `stash` / 切分支；未运行 `pip install -e`；未修改 `/opt/venv/**`、GT、容差、pipeline/state/validator/correction 实现。
- 本文件是用户唯一授权写入的 `AI_agent/**` 文件。

本轮第 3/4 项代码 diff（报告文件除外）：

```text
 src/agent/judge/reading_typed_score.py  |  10 +-
 src/agent/judge/score_inputs.py         |  10 ++
 src/agent/judge/score_schema.py         |   4 +-
 src/agent/judge/score_service.py        |  42 ++++++++-
 tests/test_c2_b5_parent_and_verts.py    | 158 +++++++++++++++++++++++++++++++-
 tests/test_f102_score_cache_identity.py |  68 +++++++-------
 6 files changed, 246 insertions(+), 46 deletions(-)
```

`git diff --check`：退出码 0，无输出。

## 一、第 1 项 · F-102 缓存 identity（检查点 `b735db4`）

第 1 项已在前一轮完成并由 orchestrator 审过：reading/correction helper identity 分离，两处 `HelperIdentityV9` 构造收敛为单一工厂；真实 R0 的 pre-F-102 sidecar 通过官方 `run_stage._grade_typed_attempt_artifacts` 必须 cache miss。

本轮按用户更正的逐轮升版要求扩展锁：

- 第 2 项 plan-floor normalization：`correction_opening_global_assignment_v3`；
- 第 3 项 F-100 source-view bridge：`correction_opening_global_assignment_v4`；
- 第 4 项 F-101 locator catalog resolution：`correction_opening_global_assignment_v5`。

最终常量：`src/agent/judge/score_schema.py:54`；旧 v4/v5 读线：`:1024-1025`。真实官方入口缓存锁：`tests/test_f102_score_cache_identity.py:20-124`。

绿锁：

```bash
python -m pytest -q \
  tests/test_c2_b5_parent_and_verts.py::test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces \
  tests/test_c2_b5_parent_and_verts.py::test_correction_floor_plan_bridge_fails_closed_with_named_reason \
  tests/test_f102_score_cache_identity.py
```

```text
..........                                                               [100%]
10 passed in 14.25s
```

sidecar 读数由锁显式断言：

```text
v1(real pre-F-102), v2, v3, v4
cache_hits == [False, False, False, False]
after helper == correction_opening_global_assignment_v5
```

把最终版本运行时改回 v4 的摘除实验：

```text
NEUTER helper correction_opening_global_assignment_v4
E assert [False, False, False, True] == [False, False, False, False]
1 failed in 6.12s
```

变红方向正确：轮间产生的 v4 sidecar 被错误命中，正是 F-102 的复发路径。

## 二、第 1b 项 · F-103 官方口子区分 NA 原因（检查点 `b735db4`）

第 1b 项已在检查点完成：粗粒度 `reason` 集合未变；`NotApplicablePayloadV9.detail` 保留原 `ScoreContractError.code`，`run_stage` 暴露 `score_payload_detail`。三种 code 的官方入口分辨锁位于 `tests/test_f103_score_not_applicable_detail.py:9`。

实测矩阵：

```text
score_product_segment_unresolved -> unsupported_view_contract -> score_product_segment_unresolved
score_match_ambiguous             -> unsupported_view_contract -> score_match_ambiguous
score_unsupported_combination     -> unsupported_view_contract -> score_unsupported_combination
distinct_official_details 3
```

摘除 `detail=error.code` 后：

```text
E assert 'unsupported_view_contract' == 'score_product_segment_unresolved'
1 failed in 3.14s
```

## 三、第 2 项 · plan segment floor bridge（检查点 `b735db4`）

第 2 项已在检查点完成：从已复验 resolver-input plan `floor_ref` 总契约重建 `product floor -> plan input -> GT floor`，只在 judge normalization boundary 重建 `PlanSegment.floor_id`，未改 matcher、未做名字/大小写猜测。

异名 fixture：product `f1`，GT `F1`：

```text
boundary_complete eligible=True verdict=pass
denominator_units=16.0 passing_units=16.0 failing_units=0.0
```

摘除重键：

```text
E AssertionError: assert 'fail' == 'pass'
1 failed in 2.08s
```

## 四、第 3 项 · F-100 correction source-view bridge

### 4.1 实现

reading 原先在 `reading_typed_score.py:512-518` 内联构造：

```python
{item.input_id: tuple(item.gt_source_view_ids) for item in score_bindings.bindings}
```

为避免第二套实现，将该既有逻辑原样抽为共享 helper：

- `src/agent/judge/score_inputs.py:137`：`source_view_to_gt_view_ids`；
- `src/agent/judge/reading_typed_score.py:515,533`：reading 调同一 helper；
- `src/agent/judge/score_service.py:652`：correction 将同一映射传给 `assign_openings`。

### 4.2 锁确实行使 GT source_refs

锁使用真实 schema 对象而非空元组：

```text
tests/test_c2_b5_parent_and_verts.py:1480
GtEntityRefV3(
  source_id="gt-source",
  view_id="gt-plan",
  entity_handle="A",
  role="opening_plan",
)
```

同一个 end-to-end 锁断言：

```text
boundary_complete: eligible/pass, 16/16 complete
windows_placed: eligible/pass
window_plan_geometry: eligible/pass
existence/host/along/width:
  eligible_units > 0
  result == complete
```

reading 与 correction 定向回归：

```bash
python -m pytest -q \
  tests/test_c2_b5_parent_and_verts.py::test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces \
  tests/test_reading_typed_scoring_slice0.py \
  tests/test_reading_typed_scoring_slice1.py
```

```text
35 passed in 24.23s
```

### 4.3 摘除实验

运行时将共享桥改为返回 `{}`：

```text
NEUTER source_view_to_gt_view_ids -> {}
E AssertionError: ExtraObservationV8(observation_id='w1', ...) != ()
1 failed in 2.58s
```

变红方向正确：带 `gt-plan` source_ref 的 GT opening 不再信任 product input `plan`，真实 observation 变成 unmatched extra；过滤器确实被行使。

## 五、第 4 项 · F-101 两种合法 locator

### 5.1 实现

旧代码对 raw provenance 一律执行 `split('/', 1)[0]`。新实现不在 judge 复制 locator 翻译逻辑，而消费已复验 catalog 的：

```text
claim_link(window_id, claim=host, source_locator)
  -> source_window(source_locator, source_input_id)
  -> registered plan input
```

位置：`src/agent/judge/score_service.py:186-252`。上游 verifier 已把 `<view>/<obs>` 与 `src:<64hex>` 两种形式统一成 canonical claim link；judge 不把 hash 当 input id，缺失/多义/未注册均响亮抛 `ScoreContractError`。

### 5.2 两种合法形式绿锁

`tests/test_c2_b5_parent_and_verts.py:1507-1558` 参数化：

```text
test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces[view_observation] PASSED
test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces[locator] PASSED
```

锁分别先断言原始 provenance 为：

```text
plan/W-01
src:<64hex>  (startswith src:, length 68)
```

随后两者都走完整 verified proof 与 scorer，并断言 F-90/F-100 的 opening 与 plan criteria 全 pass。

### 5.3 摘回旧 split 的红锁

运行时替换成旧逻辑后只跑 `[locator]`：

```text
NEUTER old_split candidates
['src:d2cf0d1805783ea1c036db07da8890313a17106f6bdfb31e3f13dcd1deb93009']
ScoreContractError: score_view_binding_invalid at scoring.view_bindings
1 failed in 2.11s
```

变红方向正确：hash 再次被误当 input id 并遭未注册拒绝。

## 六、fail-closed reason 参数锁

位置：`tests/test_c2_b5_parent_and_verts.py:1560-1675`。

派工要求的 6 个 reason 全覆盖；另外补上实际代码中同轮新增但派工漏列的第 7 个：

```text
window_host_claim_missing_source_ids
window_host_claim_ambiguous_source
window_host_source_not_a_registered_plan_input
floor_id_maps_to_multiple_plan_inputs
verified_plan_floor_catalog_not_total
verified_plan_floor_not_registered_for_scoring
window_host_disagrees_with_verified_plan_floor_catalog
```

绿锁计入前述 `10 passed`。运行时把两个 bridge helper 都替换成直接返回 `{}`：

```text
FFFFFFF
E Failed: DID NOT RAISE <class '...ScoreContractError'>
7 failed in 2.17s
```

变红方向正确：每个案例都不再响亮失败，锁拒绝静默默认/跳过。

## 七、判据 A（按用户更正版）

对象：真实 R0 复制到 `/tmp`；入口仅为 `scripts.tool_scripts.run_stage._grade_typed_attempt_artifacts`。

```text
entry_point scripts.tool_scripts.run_stage._grade_typed_attempt_artifacts
before_helper reading_opening_global_assignment_v1
before_payload rejected / score_view_binding_invalid
cache_hits [False]
after_helper correction_opening_global_assignment_v5
after_payload not_applicable / unsupported_view_contract /
              score_identity_support_ambiguous
official_score_payload_detail score_identity_support_ambiguous
```

原始错误结构化上下文：

```text
raw_error_code score_identity_support_ambiguous
raw_error_gate scoring.input_identity
reason observation_eligible_for_multiple_support_lines
observation floor_1:footprint:0
side product
floor_id F1
support_lines [('F1', 'H', 14.0), ('F1', 'H', 14.120000000000001)]
```

结论：不再落 F-90/F-100/F-101 的 `score_view_binding_invalid` 家族，确实进入 F-99 双 support-line 家族；判据 A 通过。

## 八、判据 B：触发停报，十判据读数不存在

### 8.1 为什么不能把“8 段 facade span”当独立输入量替换

真实 accepted correction 的同一个 exterior support plane 同时被 hash/proof 契约冻结在：

1. producer `footprint_x/y` 与两层 footprint ring；
2. 贴外圈 cell 边；
3. 31 个真实 plan window stroke 的法向窄带；
4. resolver input locator/output hashes；
5. window-host claims/evidence、最终 output hash 与 accepted identity。

只改 ring 的实测：真实 host resolver 大量 `zero_segment_candidates`，响亮拒绝。同步 ring、bbox、cell 端点与 plan 法向窄带后，host proof 可走通，但粗暴移动整条矩形 cell 边制造：

```text
score_error_code score_product_identity_invalid
score_error_gate scoring.input_identity
reason invalid_interior_edge_pair
floor_id floor_2
predicate missing_reverse_owner
owner_ids ('F2_MID',)
```

随后改为只给贴边 cell 加/裁正交薄带、保持内部边不变，生产 validator 继续正确拒绝：

```text
ValueError: cell F2_ML: polygon edge 1 length 0.005000 m
is below min_edge_length_m 0.100000 m
```

当时的只读探针还从归档 `window_resolver_inputs.json` 内嵌的 pre-final
`producer_draw_canonical_bytes` 读到两个 cell gap：

```text
(0.12, 14.12, 5.13, 14.125) area=0.02505
(14.88, 5.88, 24.89, 5.89) area=0.10010
```

该对象不是最终 accepted `output.json`，因此不能把这两个 gap 归因为最终产物的属性。
要继续得到可验证十判据，只剩两条路：

- 绕过真实 proof/host/cell validator；或
- 额外重铺 Floor 2 cell topology，修改 facade span 之外的输入量。

两条都违反判据 B 的“只中和 F-99 一个量 / 其余一切保持真实”。因此按派工单 §五第 5 条停止，没有伪造 `c2_scored`，也没有提供不存在的十判据表。本探针只使用 `/tmp`/内存，已清理；GT、容差、判分代码均未为 B 修改。

**更正（2026-08-26）**：撤回“Floor 2 本来就有两个 cell gap”的表述；上述现象来自归档 resolver input 内嵌的 pre-final producer，不是 accepted output。orchestrator 复核未改动的原始 `output.json` 后确认：两层 cell 覆盖的 gap/overhang 均为 `0.0`。

## 九、判据 C：测试

宽定向回归：

```bash
python -m pytest -q \
  tests/test_c2_b5_parent_and_verts.py \
  tests/test_c2_b4b_phase_d.py \
  tests/test_c2_b4b_contract.py \
  tests/test_reading_typed_scoring_slice0.py \
  tests/test_reading_typed_scoring_slice1.py \
  tests/test_run_stage_flow.py \
  tests/test_f102_score_cache_identity.py \
  tests/test_f103_score_not_applicable_detail.py
```

```text
174 passed, 14 warnings in 35.68s
```

第一次全量发现本轮 docstring 写入单词 `product`，触发 `score_inputs.py` 的源码隔离锁：

```text
FAILED tests/test_c2_b4b_score_inputs.py::
test_standard_true_unknown_direction_and_product_cannot_drive_frame
1 failed, 3028 passed, 13 xfailed
```

这不是环境问题；已只把 helper docstring 改为 `input-id -> GT-view`。该锁单跑：

```text
1 passed in 3.17s
```

最终工作树全量：

```bash
python -m pytest -n auto
```

```text
3029 passed, 13 xfailed, 212 warnings in 948.23s (0:15:48)
```

退出码 0；已知 API key 环境坑未触发。

## 十、停下上报与“派工方错在哪里”

### 10.1 判据 B 再次把施工方逼进“绕过 vs 扩范围”二选一

派工把“8 段 facade span 的 0.12m”写成可独立中和的输入量，但真实 B5 六件套把它与 cell 边、plan source window 窄带、locator hash、host proof 和 output identity 共同冻结。仅调整 facade span 无法同时保持 proof 有效；要使 resolver 输入闭包自洽，又必须重建并重签与该偏差共同冻结的 cell/proof/identity 输入。该前提错误触发 §五第 5 条，建议派工方重写 B：明确授权一个经共同审阅的、proof-valid 的输入变换闭包，或提供已中和 F-99 且重新签发六件套的真实产物。

### 10.2 fail-closed reason 数量写错

派工称“新加的两个 reason”，实际检查点代码新增了三个：除 `verified_plan_floor_catalog_not_total`、`window_host_disagrees_with_verified_plan_floor_catalog` 外，还有 `verified_plan_floor_not_registered_for_scoring`（`score_service.py:278` 附近）。本轮已将它作为第 7 个参数案例补锁。建议验收清单改成 7 个，避免该分支继续无锁。

## 十一、手工 identity 评估的处置

仍按用户命令使用手工 v4/v5，没有顺手实施派生摘要。先前结论不变：人工版本只证明标签被改，不能证明语义实现已改；从实现闭包派生组合摘要应另开独立派工。

## 十二、交给下一位审阅者的已知薄弱点

1. `host_inputs_by_window` 遇到 claim link 的 locator 不在 source catalog 时，现在报 `window_host_claim_ambiguous_source` 且 `candidate_inputs: []`；“查无此源”被命名为“歧义”，会误导分诊和修复方向。该分支应有专属 reason，与“候选多于一个”分开。
2. 窗户已在 catalog 中但一条 host claim link 都没有时，`len(candidate_inputs) == 0` 也落入 `window_host_claim_ambiguous_source`。该分支同样应给专属 reason：它与“locator 不在 catalog”是两个不同的失败谓词，处置方向也不同。
3. 手工 helper 版本字符串（v1→v5）只能证明有人改了标签，不能证明实现真的发生对应语义变化；实现内容派生的组合摘要仍值得独立改造。
4. `tests/test_f102_score_cache_identity.py` 显式依赖归档 R0 sidecar 的 opening matcher 仍是 `reading_opening_global_assignment_v1`；若有人重跑并提交那份 sidecar，这把锁的前提就会消失，需重建一个不依赖可重生归档的 pre-fix identity 信任根。
5. 判据 B 未达成：真实 case 的十判据读数至今不存在，仍挡在 F-99 后面；本报告不把它写成已验收。
