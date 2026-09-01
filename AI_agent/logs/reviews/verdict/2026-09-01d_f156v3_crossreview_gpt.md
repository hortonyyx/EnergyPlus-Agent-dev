# 跨家族复核裁决 · F-156 v3（GPT）

- 日期：2026-09-01
- 被审 commit：`85b96d6`
- 开工 HEAD：`8fac179 09.01s_Error68_RunTheExactCommandYouWrite_AndAssertTheNarrowestThing`
- 复核方：GPT 家族
- 裁决：**REWORK**
- 计数：**阻断 2 / 不阻断 5**

## 1. 裁决与阻断项

### 阻断 1：`merged_span_has_no_supporting_witness` 已成为无界 exclusion 豁口

这不是理论风险。真实 sm24 已经有一个本来会触发 merge witness 响亮失败的腔；v3 把它记成 loss 后，`reconcile_boundary_basis()` 自动把答案区 `z5` 记为合法 exclusion，最终 **`passed=True`、`structural=[]`**。更直接的数量攻击中，均衡地让 sm25 的 25 个本应成环的腔走同一 loss 分支，仍得到 **`passed=True / paired_edges=8 / exclusions=27 / accounted=29`**。

根因位于 `answer_compiler.py` 的 exclusion 消费端：只要 `loss_by_id[cavity_id]` 存在，任何 loss reason 都获准 exclusion；没有 reason 准入表、数量上限、覆盖率下限或独立于 producer 的证明。这里所谓“独立 evidence”实际仍由刚刚失败的同一个 producer 写出，不能把 bug 自报等同于合法排除。

原来的 `raise` 还保护了三件事：整份 facts 不会在少房间的情况下继续存在；另一个 view 不会把局部失败掩成完整文档；答案区不会仅凭同源 loss 自动进入 `accounted_converter_zones`。局部 blast radius 的正当性成立，但当前落点把“局部可观测”错误地升级成“局部自动免责”。

### 阻断 2：`_projected_facts_ring()` 没有复刻 `tarch_normalize._offset_for`

生产者原式是：

```python
def _offset_for(basis: EdgeBasis, thickness: float) -> float:
    return thickness if basis == "outer_skin" else thickness / 2.0
```

被审门却是：

```python
"interzone": lambda thickness: thickness // 2
```

奇数厚度 `1201` 时，生产者偏移 `600.5`，门重算 `600`；人工四边环的对称差为 `85801.0 units²`。把 `// 2` 改成真正的 `/ 2.0` 后，新增 12 项仍 **`12 passed`**，说明现有锁没有覆盖这条已由施工方自报的盲区。

这违反派工单明确要求的 `recompute-gate-must-mirror-producer-definition`，不是“差不多的算法”。当前 sm25 墙厚全为偶数只能说明没有活体存货，不能证明实现等价。

### 不阻断项

1. `side` 改成环绕向判是正确修复：矩形、L 形凹腔的 CW/CCW 四种构造均 `wrong=[]`；真实 sm25 当前 `self_adjacent=0`，旧全局代表点与正确 side 在两个走廊腔共有 9 条 edge 记录不一致。反转新公式时新增套件 `1 failed, 11 passed`，但失败是间接的 loss-reason 锁；建议补“局部内侧 + 不得 self-adjacent”的直接语义锁。
2. 细分 cell 随父段方向反转是正确修复；删除 `cells.reverse()` 后走廊环变 invalid，新增套件 `1 failed, 11 passed`。有牙，但仍建议把“降序父段产生降序 child 序列”直接断言出来。
3. 自由端墙判断成立：真实 sm25 按形态扫描为 16 个 admissible endcap、1 个 rejected endcap；摘掉准入规则后该腔仍转成 `adjacent_support_lines_parallel`，所以这份活体上的端到端分辨力确为 0，形态应另立单。
4. `_boundary_parallel_measured_faces()` 只查全局 `(axis, const)`，不查 wall run 是否在端头处接触；把唯一匹配 wall 的 coverage 平移到远处后它仍返回匹配。这是规则/锁的未来假阳性盲区。真实 16 个 accepted endcap 经另一种检查形态确认都在端点局部相接，因此本件暂记不阻断。
5. F-157 与 F-153 继续排除在本件范围外是可分阶段的；但复核单 §三第②格“投影后对称差按新门过”与已声明的生产读数冲突，见 §7。

## 2. 四个攻击面的实测结论

### 攻击面 1：局部 loss 是否成为无界豁口

真实 sm24：

```text
$ python - <<'PY'  # build_as_measured(sm24) -> derive_as_signed -> reconcile
SM24_AUDIT passed True paired_edges 30 converter_zones 8 accounted 8 exclusions 1
EXCLUSION plan-F1 cavity:78c72977c3b7e2c2 z5 merged_span_has_no_supporting_witness
STRUCTURAL []
```

人为让 merge 后的第一次复分类返回 `logical=False`，即精准命中被审分支：

```text
BASE passed False paired_edges 100 losses 1 exclusions 2 structural ['facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']
DROP 1 forced 1 merge_losses 1 all_losses 2 passed False paired_edges 100 exclusions 3 accounted 29 structural ['facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']
DROP 10 forced 10 merge_losses 10 all_losses 11 passed False paired_edges 64 exclusions 12 accounted 29 structural ['facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']
DROP 25 forced 25 merge_losses 25 all_losses 26 passed False paired_edges 8 exclusions 27 accounted 29 structural ['facts_boundary_edges_empty:plan-F1']
```

上面顺序丢 25 个时只因恰好清空整个 plan-F1 而红；把 25 个平衡为 F1 丢 11、F2 丢 14，保留每 view 一个腔：

```text
VIEW plan-F1 forced 11 edges_left 4 ring_cavities_left 1 losses 12
VIEW plan-F2 forced 14 edges_left 4 ring_cavities_left 1 losses 14
DROP_25_BALANCED passed True paired_edges 8 exclusions 27 accounted 29 converter_zones 29 structural []
```

结论：丢 1/10 个没有新增数量门；丢 25 个只要不把某 view 清零也不红。**阻断。**

### 攻击面 2：`test_boundary_condition_facts.py` 的 85 行改动

逐 hunk 结论见 §5。数字变化均能由 facts diff 对账；没有发现把 100→171、exclusion 4→2 等真结果改错。但新增 `_failures_not_from_deferred_cavities(audit)` 从“同一次受扰 audit”动态生成豁免集合，会在数个旧测试里过滤掉任意新出现的 projected failure；这是回归掩盖通道，记不阻断弱锁，需改为与未扰 baseline 的 deferred 集合做精确比较。

### 攻击面 3：端头规则活体分辨力

换成“扫描每个无 owner 且恰有一个 perpendicular endcap 的 ring segment”后：

```text
ENDCAP_STOCK plan-F1 accepted 10 rejected 1
REJECTED_FREE_END_SHAPE ('cavity:04e1293098b1a95a', 'y', 52401, 99430, 100630, ('x', 99430, 100630))
ENDCAP_STOCK plan-F2 accepted 6 rejected 0
```

16 个 accepted endcap 全都与匹配 parallel wall 的 run 在端点局部接触；所以 predicate 在活体上不是 0 存货。可是摘掉规则后 rejected cavity 的结果是：

```text
RULE_REMOVED_LIVE cavity:04e1293098b1a95a adjacent_support_lines_parallel x 99430 52401 88800
```

结论：规则本身在活体有 16/1 的输入分辨力；但对目标 rejected cavity 的最终“有环/无环”分辨力为 0。施工方“自由端墙当前根本走不通”成立，另立单合理。其测试夹具是可达同形扰动，不是纯假夹具，但不能替代真实自由端形态锁。

### 攻击面 4：三条超范围承重改动

| 改动 | 真缺陷？ | 改法是否正确？ | 锁 |
|---|---:|---:|---|
| 全局代表点 side → 绕向局部 side | 是；真实两个凹走廊 9 条记录与全局判法不一致，当前 self-adjacent=0 | 是；RECT/L × CW/CCW 均无错误 | 有间接变异牙；缺直接 self-adjacent/局部内侧锁 |
| 细分 cell 按父段方向发出 | 是；删反转后走廊 Polygon invalid | 是 | 有牙：`1 failed, 11 passed` |
| merge `raise` → per-cavity loss | merge witness 缺陷真实，sm24 活体命中 | **不正确**；局部 loss 被下游自动免责 | 新锁反而固定了弱化行为；缺数量/覆盖/独立证据锁，阻断 1 |

## 3. 三格读数

| 格 | 输入 | 实测 |
|---|---|---|
| ① 缺陷前 | `85b96d6^` 的 sm25 staging facts | `plan-F1 edges=44`，走廊 `8bd...` 与共享腔 `04e...` 均 `owner_count=0` loss；`plan-F2 edges=56`，走廊 `495...` 为 `owner_count=0` loss。两走廊均无 edge。 |
| ② 被审版 | `85b96d6` / 当前零漂移对象 | `plan-F1 edges=83`，走廊 39 edges、valid；`plan-F2 edges=88`，走廊 32 edges、valid。生产 audit：`passed=False / paired_edges=100 / accounted=29`，两走廊均为 `facts_projected_ring_unavailable:...adjacent_projected_support_lines_are_parallel`。probe 尺仍量得两者 `SYMDIFF=1.800000 / parallel=0`。 |
| ③ 自找同形输入 | 真实 `sm24_anchor` | `edges=30 / ring_cavities=7 / invalid=0 / self_adjacent=0 / discontinuous=0`，另有 1 个 `merged_span_has_no_supporting_witness`；下游将 z5 exclusion 后 `passed=True`。它既验证环/side 在另一建筑成立，也直接打出阻断 1。 |

补充人工凹腔：

```text
SIDE_FIXTURE RECT given ccw True edges 4 wrong []
SIDE_FIXTURE RECT reversed ccw False edges 4 wrong []
SIDE_FIXTURE L given ccw True edges 6 wrong []
SIDE_FIXTURE L reversed ccw False edges 6 wrong []
SM25_SIDE current_self_adjacent 0 global_rep_disagreements 9 by_cavity [('plan-F1', 'cavity:8bd127719198fd63'), ('plan-F2', 'cavity:495501ce9b36f0f3')]
```

## 4. 新锁变异实测（每次均只改一个文件并立即精确还原）

### M1 零阈值门 `!= 0` → `< 0`

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py::test_moving_one_converter_edge_by_a_tenth_of_a_millimetre_reddens
F [100%]
E AssertionError: ['facts_projected_ring_unavailable:plan-F1:...', 'facts_projected_ring_unavailable:plan-F2:...']
E assert 0 == 1
1 failed in 6.29s
```

### M2 多 zone 门禁用

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py::test_cavity_that_covers_two_zones_fails_loudly_instead_of_taking_one
F [100%]
E AssertionError: ["converter_zone_pairing_not_unique:plan-F1:cavity:04b8...:['F1-z8', 'F1-z8-upper']", ...]
E assert False
1 failed in 5.89s
```

### M3 摘掉端头准入规则

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py::test_endcap_admissibility_rule_has_teeth_on_a_one_unit_move
F [100%]
E AssertionError: ['adjacent_support_lines_parallel']
E assert 0 == 1
1 failed in 6.45s
```

### M4 角点改回 span 首点

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py::test_every_ring_turns_exactly_on_its_support_line_intersections
F [100%]
E AssertionError: assert ['cavity:8bd1...19198fd63:38'] == []
E Left contains 5 more items
1 failed in 6.21s
```

### M5 让 endcap 进入 edge-bearing supports

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py
.....FF.FF.F [100%]
5 failed, 7 passed in 6.11s
```

### M6 反转 side 绕向公式

```text
$ python -m pytest -p no:cacheprovider -q -n 6 --tb=short tests/test_f156_ring_from_intersection.py
..........F. [100%]
E AssertionError: ['endcap_const_not_a_measured_parallel_face']
1 failed, 11 passed in 6.78s
```

### M7 删除降序 cell 的 `cells.reverse()`

```text
$ python -m pytest -p no:cacheprovider -q -n 6 --tb=short tests/test_f156_ring_from_intersection.py
...........F [100%]
E AssertionError: cavity:8bd127719198fd63
E assert (False)  # Polygon.is_valid
1 failed, 11 passed in 6.39s
```

### M8 把 merge loss 改回原来的 `raise`

```text
$ python -m pytest -p no:cacheprovider -q -n 6 --tb=short tests/test_f156_ring_from_intersection.py tests/test_as_measured_facts_layer.py::test_r3_audit_sm24_a_different_building_has_only_real_thicknesses
..........F.F [100%]
E ValueError: as_measured_boundary_merge_changed_logical_status:cavity:8bd127719198fd63
E ValueError: as_measured_boundary_merge_changed_logical_status:cavity:78c72977c3b7e2c2
2 failed, 11 passed in 6.58s
```

这说明 merge 分支确有活体；同时现有新增测试把“必须 loss 而不能 raise”也固定住了，却没有固定 loss 的下游边界。

### M9 `thickness // 2` → 真正复刻生产者的 `/ 2.0`

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py
............ [100%]
12 passed in 5.38s
```

这是缺锁：真实偶数库存让错误实现与正确实现不可区分。

## 5. `test_boundary_condition_facts.py` 85 行逐处结论

`git diff --unified=0 85b96d6^..85b96d6 -- tests/test_boundary_condition_facts.py` 共 11 组行为/期望 hunk：

| # | 改动 | 结论 |
|---:|---|---|
| 1 | 测试名、edge 总数 `100→171`、condition `32/68→44/127` | 合理；与两份 facts 逐字段读数一致。条数只是 readout，另有几何锁。 |
| 2 | 删除 `assert audit.passed`，改断言两条 deferred、其余 structural 为空、`not passed` | 范围澄清后合理；但注释称“residual”不准确，生产门实际是 `unavailable`。 |
| 3 | exclusions 删除 F1-z0/F2-z0，仅保留 F1-z4/z5 | 合理；两走廊已有 ring，配对失败属于 F-157，不再是 exclusion。 |
| 4 | boundary-condition mutation 只挑 `baseline.pairings` 可达 edge | 是加强，避免把变异放进本来 early-continue 的腔。 |
| 5 | mutation structural 从 `[]` 改为 baseline deferred + mutated cavity | 合理，但“允许集合”仍由本次运行解析，建议与 baseline 精确集合比较。 |
| 6 | 新增 `DEFERRED_PROJECTION_CODES`、`_deferred_cavities()`、`_failures_not_from_deferred_cavities()` | 前者用于隔离 F-157 合理；后者对**受扰 audit 自己**产生的任意 projection failure 都自动过滤，属于回归掩盖弱口。 |
| 7 | E3 删除 ring：完整 structural 比较改为过滤 deferred 后比较 | 目标断言合理；但继承 #6 风险。 |
| 8 | 全 boundary facts 清空：missing count `25→27` | 合理；29 zones 中 z4/z5 仍由唯一 registered loss exclusion，余 27 均 missing。 |
| 9 | 50m phantom：完整 structural 比较改为过滤 deferred 后比较 | 预期两条 phantom failure 合理；但继承 #6 风险。 |
| 10 | footprint spike：plan-F2 edges `56→88` | 合理，与新基线一致。 |
| 11 | footprint spike：`all(plan-F2 not in structural)` 改为过滤 deferred 后再查 | 为排除已知 F2 corridor F-157 合理；但继承 #6 风险。 |

旁支 `tests/test_as_measured_facts_layer.py` 的唯一 `100→171` 同样与基线一致。

三份 staging 基线机械对账：

```text
as_measured.json old_sha 0d3aefa229d277b3197b5cf007747df5885641d58c8a1b6e6cdc376236f2548c new_sha ddaaae1585bcb169dcd59c89d7ad60e10718d94b3f471226820e7459de3f0e82
 top_changed ['views']
  plan-F1 view_changed ['boundary_edges', 'boundary_ring_losses'] edges 44 -> 83
  plan-F2 view_changed ['boundary_edges', 'boundary_ring_losses'] edges 56 -> 88
as_signed.json old_sha e5d4da3aeb27246f93b7fae3f19af3d3396699c517bf278f9ce78cb9ab867541 new_sha daa5ff62ef66a8826156810939af12fa63a8a106e71421a12100ed5495c79478
 top_changed ['derivation', 'views']
revisions.json old_sha 4db9e12690d761581e0c9787515a944fc7606aace969796c3ae24305d9bbbda5 new_sha 55f94cb43b7a8ab1763774fb0b414a5f9137ade2ebc7b6330d9b37e3debb84fa
 changed [('as_measured_content_sha256', '0d3a...f2548c', 'ddaa...0e82')]
```

没有发现 staging 顺手改了别的字段。

## 6. 复现命令、定向回归、哨兵与状态

主要复现命令：

```bash
git log --oneline -1
git diff --stat 85b96d6..HEAD -- src/agent/judge case_tests
sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
python AI_agent/logs/experiments/2026-09-01c_f156v3_structure/probe_b_new_production_readout.py
python AI_agent/logs/experiments/2026-09-01b_f156v2_measurements/probe_3_projected_ring_symdiff.py
python AI_agent/logs/experiments/2026-09-01b_f156v2_measurements/probe_4_where_the_residual_lives.py
python -m pytest -p no:cacheprovider -q -n 6 tests/test_f156_ring_from_intersection.py tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py
python -m pytest -p no:cacheprovider -q -n 6 tests/test_o21d_exclusion_gap.py
```

定向读数：

```text
83 passed in 18.93s
11 passed in 5.27s
```

受影响显式子集：

```text
$ python -m pytest -p no:cacheprovider -q -n 6 tests/test_answer_compiler_closure.py tests/test_answer_compiler_exit_gate.py tests/test_answer_compiler_profiles.py tests/test_as_measured_facts_layer.py tests/test_boundary_condition_facts.py tests/test_c2_vg_visibility.py tests/test_denominator_from_facts.py tests/test_f156_ring_from_intersection.py tests/test_gt_facts_staging_case_admission.py tests/test_gt_facts_staging_gate.py tests/test_gt_facts_staging_sm25.py tests/test_gt_revisions_and_as_signed.py tests/test_o21d_exclusion_gap.py
315 passed in 23.76s
```

`_projected_facts_ring()` grep/AST：

```text
if thickness <= 0
if len(supports) > 1
if len(supports) < 3
if polygon...area <= 0
PROJECTED_FUNCTION_NUMERIC_CONSTANTS [(3, 1039), (0, 1029), (1, 1037), ...]
```

结论：函数内没有面积/距离容差；出现的 0/1/3 是正值、索引和最小支撑数。故“没有阈值常量”按**容差阈值**理解成立；按“没有任何数字常量”的字面理解不成立。

开工哨兵：

```text
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

交件前哨兵与 `git status --porcelain` 见本节末尾（写完本文件后补录）。

## 7. 复核单哪里写错了

1. §三第②格要求两个走廊腔“投影后对称差按新门判法过”，但本单自己 §一/执行档与启动 prompt 的已确认事实是生产门在 `adjacent_projected_support_lines_are_parallel` 处 continue，`paired_edges` 仍为 100。两者不能同时成立。启动 prompt 已事实上把第②格修订为“facts ring 成立；probe 尺保持 1.8；生产门的 unavailable 属 F-157”，所以本次没有停报，但权威复核单文字应改。
2. “`_projected_facts_ring()` 全函数无任何阈值常量”按容差语义成立；若坚持“任何数字常量”字面则不成立（函数有 0/1/3 的结构常量）。建议写成“无非零几何容差/面积容差”。

除以上两处外，无新的派工事实错误。F-157/F-153 的范围切分本身可接受；本裁决的两个阻断均位于 F-156 v3 自己新增或修改的路径内。

### 交件前补录

```text
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth

$ git status --porcelain
?? AI_agent/logs/reviews/verdict/2026-09-01d_f156v3_crossreview_gpt.md

$ git diff --stat 85b96d6..HEAD -- src/agent/judge case_tests
（空）

$ git diff -- src/agent/judge/as_measured.py src/agent/judge/answer_compiler.py
（空）
```
