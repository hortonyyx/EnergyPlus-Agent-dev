# 跨家族复核裁决 · F-156 第六轮 / ②-1d 第四轮（GPT）

- 日期：2026-09-02
- 被审 commit：`2a5aec4`（当前 HEAD `e57ba1d` 已含被审四笔落地提交）
- 复核方：GPT 家族
- 裁决：**REWORK**
- 计数：**阻断 3 / 不阻断 1**

## 一、核心机制：1:1 阈值确实被拿掉；类型分离本身成立

结论：旧 `excluded > paired` 聚合门及 `paired_per_view` / `excluded_per_view`
计数实现已删除，没有迁移成另一处比例或数量阈值。`BoundaryBasisExclusionV1.evidence`
现在只有 `Literal["below_request_area_threshold"]`；被 converter zone 命中的
producer-authored loss 走具名 structural failure。这里的 request 面积阈值是业务定义本身，
不是替代 1:1 的“灌证配额”。因此请求书 §一的主问题回答是：**原 1:1 阈值真的消失了**。

H1：单值 `Literal` 会让将来新增第二类合法豁免时必须显式改 schema/type、实现和锁；
这是闭集收紧的有意代价，不是当前缺陷。它避免新种类未经独立可证性审查就自动获得豁免。

命令原文：

```bash
git diff --unified=0 d6b946e..2a5aec4 -- src/agent/judge/answer_compiler.py | rg '^[-+].*(exclusions_exceed|excluded|paired_per_view|Literal\[|registered_ring_loss|below_request_area_threshold)' || true
rg -n "boundary_exclusions_exceed_pairings_in_view|paired_per_view|excluded_per_view|excluded.*paired|paired.*excluded" src/agent/judge/answer_compiler.py tests/test_o21d_exclusion_gap.py || true
nl -ba src/agent/judge/answer_compiler.py | sed -n '145,180p;1211,1244p;1431,1450p'
```

输出原文：

```text
+    ``below_request_area_threshold`` -- an INDEPENDENTLY provable, by-design drop
+    producer-authored ``registered_ring_loss`` is ⛔ no longer a licence: it is
-    #: Which independent artifact licenses this exclusion.  ``registered_ring_loss``
-    #: ``below_request_area_threshold`` is a by-design sub-threshold drop.
-    evidence: Literal["registered_ring_loss", "below_request_area_threshold"]
-    #: Populated from the ledger loss when ``evidence == "registered_ring_loss"``.
+    #: independently provable and by design unlimited.  ⛔ ``registered_ring_loss``
+    evidence: Literal["below_request_area_threshold"]
+    * ``registered_ring_loss`` (``view.boundary_ring_losses``) is
+    * ``below_request_area_threshold`` (when ``min_room_area_m2`` is the
+    The old F-156 v4 per-view ``excluded > paired`` aggregate quota is GONE: the
+            # * a PRODUCER-written ``registered_ring_loss`` is FAIL-LOUD -- a
+            # * a ``below_request_area_threshold`` drop is INDEPENDENTLY provable
-                    evidence="registered_ring_loss",
-                excluded_zone_polys.setdefault(cavity_id, []).append(
+                    f"converter_zone_excluded_by_producer_written_ring_loss:"
-    # excluded (waived).  When a view WAIVES more zones than it VALIDATES the
-    paired_per_view: dict[str, int] = {}
-    excluded_per_view: dict[str, int] = {}
-        paired_per_view[proof.view_id] = paired_per_view.get(proof.view_id, 0) + 1
-        excluded_per_view[exclusion.view_id] = (
-            excluded_per_view.get(exclusion.view_id, 0) + 1)
-    for view_id in sorted(set(paired_per_view) | set(excluded_per_view)):
-        paired = paired_per_view.get(view_id, 0)
-        excluded = excluded_per_view.get(view_id, 0)
-        if excluded > paired:
-                f"boundary_exclusions_exceed_pairings_in_view:{view_id}:"
-                f"paired={paired}:excluded={excluded}")
+    # not per-view.  A producer-written ``registered_ring_loss`` is fail-loud
+    # the only exclusions that survive are ``below_request_area_threshold`` ones,
+    # aggregate ``excluded > paired`` cut would false-red an honest building with
tests/test_o21d_exclusion_gap.py:10:An earlier per-view ``excluded > paired`` aggregate tooth tried to catch that,
tests/test_o21d_exclusion_gap.py:11:but it leaked at the balanced ``excluded == paired`` point, and it also counted
tests/test_o21d_exclusion_gap.py:99:#: ⛔ ``boundary_exclusions_exceed_pairings_in_view`` is gone: rework3 catches the
tests/test_o21d_exclusion_gap.py:529:    have beaten the old ``excluded > paired`` quota) and assert none of them
tests/test_o21d_exclusion_gap.py:539:    # per-view ``excluded > paired`` quota would definitely have fired here --
tests/test_o21d_exclusion_gap.py:567:                if item.startswith("boundary_exclusions_exceed_pairings_in_view")]
tests/test_o21d_exclusion_gap.py:718:    """§五#2, the exact point the old quota leaked: ``excluded == paired``.
tests/test_o21d_exclusion_gap.py:721:    The rework2 per-view cut only fired on ``excluded > paired`` and so waved
src/agent/judge/answer_compiler.py:1115:    The old F-156 v4 per-view ``excluded > paired`` aggregate quota is GONE: the
src/agent/judge/answer_compiler.py:1439:    # aggregate ``excluded > paired`` cut would false-red an honest building with
   166 class BoundaryBasisExclusionV1(_StrictModel):
   169     ②-1d rework3: an exclusion is only ever licensed by
   170     ``below_request_area_threshold`` -- an INDEPENDENTLY provable, by-design drop
   173     producer-authored ``registered_ring_loss`` is ⛔ no longer a licence: it is
  1214             # * a PRODUCER-written ``registered_ring_loss`` is FAIL-LOUD -- a
  1224             loss = loss_by_id.get(cavity_id)
  1225             if loss is not None:
  1226                 structural.append(
  1227                     f"converter_zone_excluded_by_producer_written_ring_loss:"
  1228                     f"{view.view_id}:{cavity_id}:{zone.zone_id}:"
  1229                     f"reason={loss.reason}:area_units2={loss.area_units2}")
  1230             elif (area_threshold_units2 is not None
  1231                     and raw_by_id[cavity_id].area <= area_threshold_units2):
  1232                 exclusions.append(BoundaryBasisExclusionV1(
  1236                     evidence="below_request_area_threshold"))
  1431     # ⭐ ②-1d rework3: the FLOODING ('灌证') direction is now caught PER-LOSS,
  1434     # true-looking losses reddens loss-by-loss and there is no aggregate quota
  1435     # left to tune.  ⛔ We deliberately do NOT count exclusions against pairings:
```

## 二、阻断 1：H2 的“ledger 到 0 自动变绿”被两条库存断言钉死

`test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion` 与
`test_deregistering_each_live_loss_clears_exactly_its_own_red` 分别断言 live ledger
非空。临时探针把所有 `boundary_ring_losses` 清空，再直接调用这两条锁；两条均在库存断言处红。
这与文件注释“stays true as the ledger shrinks toward 0”及“neither reddens nor needs editing when
stock reaches 0”直接相反。即使 F-153 形态 B 修复同时补出 ring，这两个断言仍会先失败。
因此 H2 **证伪**，且会在上游缺陷修复后制造无来由常态红，属阻断。

## 三、阻断 2：未被 converter zone 命中的 producer loss 可完全静默

实现只在遍历 converter zone 且该 zone 命中一个无 ring cavity 时查询
`loss_by_id.get(cavity_id)`；没有对 ledger 做反向耗尽检查。临时探针按规则选择真实 sm25 中
“无 stored ring、无既有 loss、也无 converter zone 命中”的 raw cavity
`cavity:1bf74ff81b6b39bb`，加入 schema 合法的 producer loss，而不新增 zone。
攻击前后 `structural_failures` 逐字相同，新 loss 的 producer-loss red 为空。

这是与施工方“sub-threshold cavity + converter zone 洗白”不同的攻击形状，也直接推翻
“任何 producer 自写台账都红”：当前只是**任何被 converter zone 消费到的 loss**才红。
需要按 ledger 反向逐条核销/逐条 fail-loud，而不是只在 zone 正向查表。

两条阻断共用命令原文（临时探针已在取证后删除，未提交）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_crossreview_gpt_probe.py
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_crossreview_gpt_probe.py::test_h2_empty_ledger_keeps_two_source_locks_red
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:131: UserWarning: {'fail_loud_source_lock': 'no live ledger entry -- this lock has no stock', 'deregistering_source_lock': 'no registered loss on the substrate -- this lock has no stock'}
    warnings.warn(repr(errors))

tests/test_crossreview_gpt_probe.py::test_unconsumed_producer_loss_is_silently_ignored
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:95: UserWarning: {'view_id': 'plan-F1', 'cavity_id': 'cavity:1bf74ff81b6b39bb', 'forged_loss_area_units2': 5760000, 'baseline_structural_failures': ['converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200', 'converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200', 'facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel'], 'attacked_structural_failures': ['converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200', 'converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200', 'facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel'], 'producer_loss_reds_for_forgery': []}
    warnings.warn(repr({

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 2 warnings in 3.86s
```

## 四、H3 与定向验收：常态全绿，但原锁中仍有一条恒绿

### 4.1 当前实现下的规则锁

重写后的 exclusion 文件 15 条与 odd-thickness NA 合跑，`16 passed`。这覆盖：大量诚实
below-threshold exclusion、单个/大量 producer loss、`excluded == paired` 点、施工方自造的
sub-threshold 洗白攻击、原撤证方向，以及 odd storage-unit NA。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py tests/test_f156_ring_from_intersection.py::test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

................                                                         [100%]
16 passed in 4.16s
```

### 4.2 fail-loud 定向 neuter：6 条相关锁会红

临时把 `loss is not None` 分支的 structural append 替换为 `pass`，其余实现不动；
`test_o21d_exclusion_gap.py` 有 6 条精确转红，说明 fail-loud、来源对账、flood、balanced 点和
施工方自造 seam 攻击的接线都是真牙。变异后已逐字还原并核净工作树。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py
```

输出原文（pytest 的 failure 汇总原文）：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

......FF...FFFF                                                          [100%]
=========================== short test summary info ============================
FAILED tests/test_o21d_exclusion_gap.py::test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion
FAILED tests/test_o21d_exclusion_gap.py::test_honest_substrate_branch_reds_are_exactly_the_known_defect
FAILED tests/test_o21d_exclusion_gap.py::test_flooding_the_loss_ledger_is_fail_loud_per_loss
FAILED tests/test_o21d_exclusion_gap.py::test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion
FAILED tests/test_o21d_exclusion_gap.py::test_a_single_balanced_producer_loss_still_reddens
FAILED tests/test_o21d_exclusion_gap.py::test_own_attack_a_producer_loss_cannot_masquerade_as_a_below_threshold_drop
6 failed, 9 passed in 3.62s
```

### 4.3 阻断 3：原 11 条中的 ring+loss 锁在保护机制被摘掉后仍绿

`test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` 自己承认
“THIS ONE CANNOT CURRENTLY GO RED”，全仓也没有第二条测试覆盖
`as_measured_boundary_cavity_has_edges_and_loss`。我临时把
`AsMeasuredViewV1._ledger_identity` 中对应 raise 摘成 `pass`，只跑该锁，结果仍是
`1 passed`；恢复后工作树净。

所以 H3 不能报“原 11 条每条都活着”：10 条仍有可观察的红/绿或 source mismatch，
这一条没有违规夹具，连它声称的“validator relaxed later”也抓不到。授权重写夹具的验收未完成，
属阻断。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py::test_a_cavity_is_never_both_ringed_and_registered_as_a_loss
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 3.36s
```

## 五、全量与真实 sm25

### 5.1 权威全量

按要求加载主树 `.env`，同一 shell 做模块落点自证，固定 `-n 6` 和
`-p no:cacheprovider`。结果 `3659 passed, 13 xfailed`，F-158 环境红未出现。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

输出原文（首行与 pytest 最终汇总；中间 211 条 warnings 正文不影响结果，未重抄）：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
...
......................................... [100%]
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
3659 passed, 13 xfailed, 211 warnings in 570.85s (0:09:30)
```

### 5.2 真实 sm25 审计读数

真实调用给 `passed=False`、29/29 accounted、四条 red。两条本锁 red 都指向同一个
live ledger loss，分别对应同 cavity 内的 `F1-z4` / `F1-z5`；另两条是 F-157 的
`facts_projected_ring_unavailable`。没有第五条无出处常态红。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python - <<'PY'
from collections import Counter
from src.agent.judge.answer_compiler import read_facts_for_compilation, reconcile_boundary_basis
from src.agent.judge.gt_schema import REPO_ROOT
from src.agent.judge.tarch_converter_schema import ConversionReportV1, TarchConversionRequestV1
case = 'sm25-L_anchor'
_measured, _ledger, signed = read_facts_for_compilation(case)
source = REPO_ROOT / 'case_tests/test_baseline/gt_sources' / case
review = REPO_ROOT / 'case_tests/test_baseline/gt' / case / 'review'
request = TarchConversionRequestV1.model_validate_json((source / 'request_as_measured.json').read_bytes())
report = ConversionReportV1.model_validate_json((review / 'conversion_report.json').read_bytes())
audit = reconcile_boundary_basis(signed, report, min_room_area_m2=request.min_room_area_m2)
print(f'passed={audit.passed}')
print(f'accounted={audit.accounted_converter_zones}/{audit.converter_zones}')
print(f'paired_edges={audit.paired_edges} exclusions={len(audit.exclusions)} reds={len(audit.structural_failures)}')
print('codes=' + repr(Counter(item.split(':', 1)[0] for item in audit.structural_failures)))
for item in audit.structural_failures:
    print(item)
PY
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
passed=False
accounted=29/29
paired_edges=100 exclusions=0 reds=4
codes=Counter({'converter_zone_excluded_by_producer_written_ring_loss': 2, 'facts_projected_ring_unavailable': 2})
converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel
```

### 5.3 F-153 形态 B 三路对账

我没有沿用执行档数字：从 live signed ledger 读 loss；从 live face lines 选取同轴且完整覆盖
loss span 的最近面；再与 `plan.md` 的未闭合登记比。结果为 28.683212 m²、loss
`const=52401/lo=99430/hi=100630`、最近覆盖面 `const=52400`、delta 1，逐项吻合形态 B。

命令原文：

```bash
python - <<'PY'
from src.agent.judge.answer_compiler import read_facts_for_compilation
_m, _l, signed = read_facts_for_compilation('sm25-L_anchor')
for view in signed.views:
    for loss in view.boundary_ring_losses:
        span = loss.span
        candidates = [f for f in view.face_lines
                      if f.axis == span.axis
                      and f.along_min <= span.lo and f.along_max >= span.hi]
        nearest = min(candidates, key=lambda f: abs(f.const - span.const))
        print(f'view={view.view_id} cavity={loss.cavity_id}')
        print(f'area_units2={loss.area_units2} area_m2={loss.area_units2 / 100_000_000:.6f}')
        print(f'loss_span=axis:{span.axis},const:{span.const},lo:{span.lo},hi:{span.hi}')
        print(f'nearest_covering_face=id:{nearest.id},const:{nearest.const},lo:{nearest.along_min},hi:{nearest.along_max},delta:{abs(nearest.const-span.const)}')
        print(f'reason={loss.reason}')
PY
sed -n '392,402p' AI_agent/plan.md
```

输出原文：

```text
view=plan-F1 cavity=cavity:04e1293098b1a95a
area_units2=2868321200 area_m2=28.683212
loss_span=axis:y,const:52401,lo:99430,hi:100630
nearest_covering_face=id:1377,const:52400,lo:96399,hi:103599,delta:1
reason=endcap_const_not_a_measured_parallel_face
**⛔ 主控把那条台账的数字对了一遍 —— 它不合法，它是 F-153 形态 B（已登记未修）**：

| 对的是什么 | 台账 | F-153 形态 B 登记 |
|---|---|---|
| 面积 | `2868321200` units（0.1mm）⇒ **28.683212 m²** | **28.68 m²** |
| 坐标 | `const=52401 lo=99430 hi=100630` | 墙 `w_x_99430_100630_52401_88800` |
| 机制 | `nearest…=52400`，**`delta=1`** | 「`along_min` 比同侧三兄弟大 **1 个单位**」 |

⭐ 数量也对：F-153 原三个腔，F-156 v3 修掉**形态 A** 那两个 ⇒ 台账 3→1，剩的正是形态 B。
而 F-153 登记的实测是它 **贴墙 401/401、最远采样点距墙 0.000 m** = **被墙完全围合的真实房间**。
⇒ **fail-loud 只会判红这一样东西，而它本来就该红。A③ 的前提倒了 ⇒ C/D/E 岔口不存在。**
```

## 六、派工单 §五六条验收汇总

| # | 结论 | 证据 |
|---|---|---|
| 1 | 通过 | 多个诚实 below-threshold exclusions 不红；旧 aggregate 代码已删除；16 条定向绿 |
| 2 | **未完全通过** | zone 命中的单个、balanced、大量 producer loss 均红；但阻断 2 证明未被 zone 命中的 ledger entry 可静默 |
| 3 | **不通过** | 真实红能指名 live ledger；但 H2 的两条锁用非空库存断言钉住缺陷存在 |
| 4 | **不通过** | 常态 11 + odd 均绿，但 H3 neuter 证明其中 ring+loss 锁恒绿 |
| 5 | **不通过** | 施工方自造 seam 攻击会红；复核方不同形状“无 zone 消费的 producer loss”成功骗过判据 |
| 6 | 通过 | 全量 3659 passed / 13 xfailed；真实 sm25 四红、29/29 accounted，四红均有归属 |

## 七、不阻断 1：旧注释仍把 producer ledger 写成 exclusion licence

`answer_compiler.py:1158-1164` 仍写“ONLY boundary_ring_losses ledger ... licenses that
exclusion”，与本轮类型分离及紧接着的 fail-loud 实现相反。运行行为不受影响，因此不阻断；
但它会把下一位维护者重新引回旧语义，应随返工修正。

命令原文：

```bash
nl -ba src/agent/judge/answer_compiler.py | sed -n '1156,1166p'
```

输出原文：

```text
  1156              by_cavity.setdefault(edge.cavity_id, []).append(edge)
  1157
  1158          # Account for the complete converter-zone population before doing the
  1159          # edge-level comparison.  A raw facts cavity may genuinely have no
  1160          # logical ring, but ONLY the ``boundary_ring_losses`` ledger (an
  1161          # above-threshold known defect) or a below-threshold by-design drop
  1162          # licenses that exclusion -- ⛔ never the producer re-deriving its own
  1163          # ring, whose co-cause failure would silently absorb real rooms and
  1164          # hallucinated zones alike ([[gate-measures-right-but-carrier-gets-swapped]]).
  1165          try:
  1166              footprint, _ring_records = _footprint_polygon(view)
```

## 八、对我上一轮 either/or 的复看与修正

上一轮原句是：“对 `registered_ring_loss` 建立逐条独立 applicability 证明或 fail-loud”。
作为**消费端即时安全动作**，未获证明就 fail-loud 没错；但把它写成返工边界的完整二选一，
确实不完整，因为它默认每条 live loss 都是“可能合法的豁免候选”，没有先核这条 loss 本身
是否合法、是否其实对应未闭合上游缺陷。请求方题错 #71 的裁定成立，我上一轮的边界也应修正。

修正后的边界是：

1. 先将每条 live loss 与原始几何及未闭合缺陷登记对账，判它是合法例外、已知上游缺陷，
   还是未证真伪；不得从“ledger 里存在”反推合法。
2. 合法且能由不同作者的证据独立证明，才进入具名 typed exclusion。
3. 已知上游缺陷在消费端 fail-loud 作当前围栏，同时归属到上游修复；未能证明合法的其余 loss
   也 fail-closed。任何有限配额都不能替代这次分类。

命令原文：

```bash
nl -ba AI_agent/logs/reviews/verdict/2026-09-02b_f156r4_o21d_crossreview_gpt.md | sed -n '81,86p;402,409p'
```

输出原文：

```text
    81  ```
    82
    83  修复不能只是继续调比例。对 producer 自写的 `registered_ring_loss`，需要能逐条证明其 applicability
    84  的独立证据，或对未获独立证明的 loss fail-loud；否则任何有限配额内的灌证仍然合法。
    85
    86  ## 二、重点疑点 2：reason 准入表
   402  ## 六、返工验收边界
   403
   404  1. 不把 `below_request_area_threshold` 计入 producer-loss flooding 配额；它已有 raw area + request
   405     threshold 的独立证明。
   406  2. 对 `registered_ring_loss` 建立逐条独立 applicability 证明或 fail-loud，不能再用任意比例代替真伪。
   407  3. 新锁至少覆盖本裁决两种相反形态：诚实 `excluded > paired` 必须绿；`excluded == paired` 的
   408     true-looking ledger flood 必须红。
   409  4. 保留 odd-thickness 响亮 NA、原 11 条撤证锁和全量绿。
```

这项自我修正与被审 diff 无关，**不计入**阻断/不阻断数字。

## 九、最终裁决与最小返工边界

**REWORK · 阻断 3 / 不阻断 1。** 主修法“类型分离 + 去掉 1:1 aggregate + 对被消费到的
producer loss fail-loud”方向成立，全量也绿；但验收 2、3、4、5 尚未同时成立。

最小返工边界：

1. 为 ledger 增加反向耗尽/逐条 fail-loud：每个 `boundary_ring_losses` entry 都必须被观察，
   即使没有 converter zone 命中它，也要以 cavity + reason + area 指纹具名红；补我方
   “unrepresented raw cavity 上的 loss”回归锁。
2. 删除两条 source 锁对 live ledger 非空的依赖；以构造一个 live paired cavity → strip ring +
   write loss 的夹具维持 fail-loud 方向库存，同时实测 ledger=0 时来源锁绿。
3. 把 ring+loss 互斥锁改成真正构造同 cavity 同时有 edge 与 loss，并断言
   `AsSignedV1.model_validate` 抛精确错误；再摘 validator，锁必须红。
4. 修正 §七的陈旧注释；保留现有 16 条定向绿、fail-loud neuter 红集、odd NA、全量与真实
   sm25 四红归属。

H1 的演进代价是有意闭集，不要求本轮预留第二个 Literal 值，也不要求修改 `as_measured.py`
生产逻辑或顺手修 F-153/F-157。
