# 跨家族复核裁决 · F-156 第六轮 / ②-1d 第四轮（GPT）

- 日期：2026-09-02
- 被审 commit：`2a5aec4`（当前 HEAD `e57ba1d` 已含被审四笔落地提交）
- 复核方：GPT 家族
- 裁决与计数：见文末汇总（本文件按复核段落分段提交）

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

