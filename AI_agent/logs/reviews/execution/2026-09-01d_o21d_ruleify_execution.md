# 执行档 · ②-1d exclusion 锁「规则化」（题错 #58 的处置）

- **日期**：2026-09-01 · **席位**：Claude 家族施工席 · **基线**：`e955254`（工作树干净）
- **派工单**：`AI_agent/logs/reviews/request/2026-09-01_o21d_rework2_exclusion_gap.md` **§九**
- **写面**：`tests/test_o21d_exclusion_gap.py` · 本执行档 · `AI_agent/logs/experiments/2026-09-01d_o21d_ruleify/`
- **⛔ 未改任何生产代码**，未 `git add` / `git commit`

---

## ⭐⭐⭐ 零、先说一件派工单说错的事（**第 65 次停报级发现，但我没停，理由在 §六**）

派工单说：**「这 5 条红的根源是【判据写法错了】，不是代码错了」**，
且 §九 结尾说其余各条「**本来就是规则式，⛔ 不受 F-156 影响、不用改**」。

**实测：这话对 5 条里的 1 条成立，对另外 4 条不成立。**

F-156 v3 之后，`reconcile_boundary_basis` 在**真实 sm25 底料上返回 `passed=False`**：

```
=== audit (min_room_area_m2=None) ===
  passed=False paired_edges=100 converter_zones=29 accounted=29 rows=100
  structural_failures (2):
    facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
    facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel
```

那 4 条不是死在「腔的名单对不上」，是死在**绿锚 `assert audit.passed` 本身**
（`:111` / `:138` / `:219`）。**换句话说：把名单改成规则，这 4 条一条都不会变绿。**
只有 `test_three_live_cavities_...` 是派工单描述的那个病，而且它**也是先死在 `:92` 的 `assert audit.passed`**，
根本没走到那三个面积断言。

⭐ **真正的病族比派工单写的更普遍**：`assert audit.passed` 本身就是一个**现状读数**
——「今天整份 sm25 审计全绿」。它让本文件的每条锁都成为**审计里任何其它条件**的人质。
这跟 §九 要治的是**同一个病**，只是派工单只认出了「名单」那一种形态。

**它是谁的红**：`tests/test_f156_ring_from_intersection.py:48-51` 把
`facts_projected_ring_unavailable` 与 `facts_projected_ring_is_not_the_converter_zone`
并列命名为 **`DEFERRED_PROJECTION_CODES` = 「F-157 owns」**，并在自己的断言里把它们**滤掉**。
⇒ 这是 F-156 v3 自己**已具名、已交办**的遗留条件，树内已有先例口径。

---

## 一、改了什么（逐条锁：原来钉的是什么 / 现在量的是什么）

改写后 **7 条 → 11 条**。每条都自报是 **RULE** 还是 **READING**。

| 原锁 | 原来钉的 | 现在 | 现在量的 |
|---|---|---|---|
| `test_reconcile_never_re_derives_the_ring_it_judges` | （已是规则）源码里不出现生产者重导函数 | **不动** | 同左 |
| `test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger` | ⛔ **那 3 个腔** + 面积 `8826560000/2868321200/7033920000` + `all(reason=="owner_count")` + `(29,29)` | 拆成 3 条 ↓ | |
| — | | **RULE** `test_every_exclusion_is_licensed_by_evidence_it_actually_points_at` | 任何 exclusion 都必须有能**解析得到**的凭据：`registered_ring_loss` 必须在台账里**真有**那条 loss，且 `reason`/`area` **等于台账自己的值**（⇒ 门不能自己编凭据）。⭐ 与是哪几个腔、有几个腔**无关**，0 个也成立 |
| — | | **RULE** `test_honest_substrate_raises_no_unaccounted_structural_failure` | 诚实底料上，结构失败要么属本分支（当前 0 条），要么是**他锁已具名认领**的码；**没申报过的码 = 红** |
| — | | **READING** `test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores` | 门消费的台账 == 事实层存的台账，**两份文档两次解析**（`as_measured.json` vs `as_signed.json`）。⛔ 里面**没有任何字面数字**可改 |
| `test_deregistering_a_live_cavity_reddens...` | ⛔ 写死 `CAVITY_88`；绿锚 `assert audit.passed` | **RULE** `test_removing_the_licence_from_an_excluded_cavity_reddens` | **按规则**挑「今天面积最大的、能配对的腔」→ 摘掉它的环：**发登记 ⇒ 绿**、**不发 ⇒ 具名红**。⭐ 夹具是**造出来的**，存货与上游修不修**无关** |
| — | | **RULE** `test_deregistering_each_live_registered_exclusion_reddens` | 遍历**真实存量** exclusion 逐个撤销登记，各自具名变红。存量归零时自动空转（不红、不用改） |
| `test_two_disjoint_rooms_may_share_one_na_cavity` | ⛔ 写死 `CAVITY_SHARED` / `["F1-z4","F1-z5"]`；绿锚 `passed` | **RULE** `test_disjoint_rooms_may_share_one_licensed_cavity` | 在**造出来的**已登记腔里放两个**内部不相交**的 zone ⇒ 本分支零失败 |
| `test_phantom_zone_parked_on_a_real_excluded_zone_reddens` | ⛔ 写死 `CAVITY_SHARED`；且 `assert not audit.passed` **今天恒真** | **RULE** `test_two_zones_overlapping_inside_one_licensed_cavity_reddens` | 同一夹具，两个 zone **重叠** ⇒ 恰好 1 条具名 `converter_zones_overlap_...`；并**先断言不相交那版没有这条**（先绿后红） |
| `test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold` | 绿锚 `assert aligned.passed`；`assert request.min_room_area_m2 == 5.0`；腔按 `plan-F1` 挑 | **RULE**（同名） | 绿锚收窄到本分支；阈值断言改成 `tiny.area < request.min_room_area_m2`（**自证前提**，⛔ 不比字面 5.0）；最小腔改为**全 view 扫**，⛔ 不再点名 `plan-F1` |
| `test_above_threshold_unregistered_cavity_still_reddens_even_with_threshold` | ⛔ 写死 `CAVITY_88`（而它今天**已经有环了**，所以撤销登记什么也没发生） | **RULE** `test_above_threshold_unlicensed_cavity_still_reddens_even_with_the_threshold` | 用同一造出来的夹具（**断言它确实过阈值**），撤登记 + 给生产阈值 ⇒ 仍具名红 |
| — | | **（保留但如实降级）** `test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` | ⚠️ 实测**恒绿**，见 §三 |

**绿锚的收窄**（本轮唯一一个判断类决定）：
```python
EXCLUSION_BRANCH_CODES = (
    "facts_boundary_ring_missing",
    "converter_zones_overlap_in_shared_exclusion_cavity",
    "converter_zone_facts_cavity_pairing_not_unique",
    "converter_zone_polygon_invalid",
    "converter_zone_unclaimed_by_facts",
    "facts_boundary_footprint_unusable",
)
```
= `reconcile_boundary_basis` 里**属于本分支的完整发射集**。⭐ 我**没有**只凭阅读就下结论，
而是把函数里**每一个 `structural.append`** 机械枚举出来逐个分类（见 §八.1 的表）。
第一版漏了 `converter_zone_unclaimed_by_facts`（本分支自己的**完备性声明**：
「一个 converter zone 要么被配对、要么被具名 exclusion 认领」），枚举时抓到并补上。
收窄留下的口子由 `test_honest_substrate_raises_no_unaccounted_structural_failure` 收口。

---

## 二、`pytest -n 6 tests/test_o21d_exclusion_gap.py` 改前 / 改后**完整输出原文**

### 改前（`e955254`，未动树）
```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /workspaces/EnergyPlus-Agent-dev
configfile: pyproject.toml
plugins: langsmith-0.7.33, xdist-3.8.0, anyio-4.13.0
created: 6/6 workers
6 workers [7 items]

..FFFFF                                                                  [100%]
=================================== FAILURES ===================================
_______________ test_two_disjoint_rooms_may_share_one_na_cavity ________________
[gw3] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_two_disjoint_rooms_may_share_one_na_cavity():
        """Green anchor for the uniqueness lock: sm25 z4 and z5 legitimately share
        one under-segmented NA cavity (disjoint interiors) and must stay green."""
        signed, _request, report = _real_inputs()
        audit = reconcile_boundary_basis(signed, report)
>       assert audit.passed
E       AssertionError: assert False
E        +  where False = BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=29, accounted_converter_zones=29, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']).passed

tests/test_o21d_exclusion_gap.py:138: AssertionError
__ test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger ___
[gw1] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger():
        signed, _request, report = _real_inputs()
        audit = reconcile_boundary_basis(signed, report)
>       assert audit.passed
E       AssertionError: assert False
E        +  where False = BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=29, accounted_converter_zones=29, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']).passed

tests/test_o21d_exclusion_gap.py:92: AssertionError
____ test_deregistering_a_live_cavity_reddens_instead_of_silently_excluding ____
[gw2] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_deregistering_a_live_cavity_reddens_instead_of_silently_excluding():
        """Penetration ② (real-cause form): an above-threshold enclosed room whose
        ring is absent AND whose ledger acknowledgement is missing is a silent gap,
        not a free exclusion.  Removing the evidence must flip green -> red."""
        signed, _request, report = _real_inputs()
        # green anchor: with the ledger entry present, it is a legitimate exclusion.
>       assert reconcile_boundary_basis(signed, report).passed
E       AssertionError: assert False
E        +  where False = BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=29, accounted_converter_zones=29, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']).passed
E        +    where BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=29, accounted_converter_zones=29, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']) = reconcile_boundary_basis(AsSignedV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='4a...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))]), ConversionReportV1(report_version=1, status='PASS', case='sm25-L_anchor', source_dxf_sha256='1251f65153829c9c4502e401b...e_handles': ['1609'], 'structural_source_handles': ['316', '317', '319', '31B']}], review_bundle_inventory_sha256=None))

tests/test_o21d_exclusion_gap.py:111: AssertionError
_ test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold _
[gw5] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold():
        signed, request, report = _real_inputs()
        tiny, tiny_id = _tiny_subthreshold_cavity(signed)
        raw = report.model_dump(mode="python")
        raw["zones"].append(_zone_over(tiny, "F1-shaft-probe").model_dump(mode="python"))
        report_with_shaft = ConversionReportV1.model_validate(raw)
    
        # ⭐ red first: with no threshold the gate is fail-loud -- a no-ring cavity
        # that is not in the ledger reddens (this is the aligned replacement for the
        # old derive(0.0) false alarm, N3').
        fail_loud = reconcile_boundary_basis(signed, report_with_shaft)
        assert not fail_loud.passed
        assert (f"facts_boundary_ring_missing:plan-F1:{tiny_id}:converter=F1-shaft-probe"
                in fail_loud.structural_failures)
    
        # ⭐ green with the production threshold: 0.058 m² < 5.0 m² -> a named
        # below_request_area_threshold exclusion, ⛔ not a red, ⛔ not a threshold
        # tuned to the number.
        assert request.min_room_area_m2 == 5.0
        aligned = reconcile_boundary_basis(
            signed, report_with_shaft, min_room_area_m2=request.min_room_area_m2)
>       assert aligned.passed
E       AssertionError: assert False
E        +  where False = BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=30, accounted_converter_zones=30, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']).passed

tests/test_o21d_exclusion_gap.py:219: AssertionError
__ test_above_threshold_unregistered_cavity_still_reddens_even_with_threshold __
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_above_threshold_unregistered_cavity_still_reddens_even_with_threshold():
        """The threshold exit is ⛔ not a blanket amnesty: an above-threshold cavity
        with no ring and no ledger entry reddens even when the production threshold
        is supplied (guards against 'pass the threshold to make everything green')."""
        signed, request, report = _real_inputs()
        # deregister the 88 m² cavity, keep the ring absent, then supply the threshold.
        raw = signed.model_dump(mode="json")
        for view in raw["views"]:
            view["boundary_ring_losses"] = [
                loss for loss in view["boundary_ring_losses"]
                if loss["cavity_id"] != CAVITY_88]
        audit = reconcile_boundary_basis(
            AsSignedV1.model_validate(raw), report,
            min_room_area_m2=request.min_room_area_m2)
        assert not audit.passed
>       assert (f"facts_boundary_ring_missing:plan-F1:{CAVITY_88}:converter=F1-z0"
                in audit.structural_failures)
E       AssertionError: assert 'facts_boundary_ring_missing:plan-F1:cavity:8bd127719198fd63:converter=F1-z0' in ['facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']
E        +  where ['facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel'] = BoundaryBasisAuditV1(passed=False, paired_edges=100, converter_zones=29, accounted_converter_zones=29, rows=[BoundaryB...el', 'facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel']).structural_failures

tests/test_o21d_exclusion_gap.py:241: AssertionError
=========================== short test summary info ============================
FAILED tests/test_o21d_exclusion_gap.py::test_two_disjoint_rooms_may_share_one_na_cavity
FAILED tests/test_o21d_exclusion_gap.py::test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger
FAILED tests/test_o21d_exclusion_gap.py::test_deregistering_a_live_cavity_reddens_instead_of_silently_excluding
FAILED tests/test_o21d_exclusion_gap.py::test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold
FAILED tests/test_o21d_exclusion_gap.py::test_above_threshold_unregistered_cavity_still_reddens_even_with_threshold
========================= 5 failed, 2 passed in 7.14s ==========================
```

### 改后
```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /workspaces/EnergyPlus-Agent-dev
configfile: pyproject.toml
plugins: langsmith-0.7.33, xdist-3.8.0, anyio-4.13.0
created: 6/6 workers
6 workers [11 items]

...........                                                              [100%]
============================== 11 passed in 5.37s ==============================
```

连跑 3 次（[[one-shot-acceptance-bar-kills-false-claims]]）：`run1 11 passed / run2 11 passed / run3 11 passed`。

邻近子集（**未改动**，只跑读）：
```
python -m pytest -n 6 -q tests/test_boundary_condition_facts.py \
  tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py \
  tests/test_denominator_from_facts.py tests/test_f156_ring_from_intersection.py
=> 96 passed in 19.88s          # 84（四文件基线）+ 12（test_f156）
```

---

## 三、⭐ 反面自查：**逐条**说明 F-157 / F-153 形态 B 修好后为什么不会红

⚠️ 这一节不是推理，是**照着两个修复各自会改变什么**逐条对：
- **F-157** 修的是答案侧 `outer_skin`↔`wall_axis` 在一条支撑线中途切换
  ⇒ 消掉 `facts_projected_ring_unavailable` / `facts_projected_ring_is_not_the_converter_zone`，
  并让那两个走廊腔**进入配对**（`paired_edges` 100 → 更大）。
- **F-153 形态 B** 修 0.1 mm 错位 ⇒ 同样只动上面第二个码。
- 两者都**可能**把台账从 1 条清到 0 条、把 exclusion 清到 0 个。

| 锁 | 它依赖上述哪个量？ | 修好后为什么不红 |
|---|---|---|
| `test_reconcile_never_re_derives_the_ring_it_judges` | 都不依赖（读源码文本） | 与 ring 实现无关 |
| `test_every_exclusion_is_licensed_by_evidence_it_actually_points_at` | 只看 `EXCLUSION_BRANCH_CODES` + 遍历 `audit.exclusions` | 两个码**都不在**本分支集合里；exclusion 清零 ⇒ 循环空转，断言仍成立（⭐ 这正是「0 条也满足」的规则形态）；`accounted == converter_zones` 是**相等关系**不是 29 |
| `test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` | 只看 schema 不变式 | 集合交集变空更容易成立 |
| `test_honest_substrate_raises_no_unaccounted_structural_failure` | 明确**允许**两个 deferred 码出现，但**从不要求**它们出现 | 它们消失 ⇒ `unaccounted` 仍为 `[]` |
| `test_reading_the_ledger_...` | 台账**条数**会变 | 断言的是**两份文档相等**，⛔ 没有字面条数。3→1→0 都成立 |
| `test_removing_the_licence_from_an_excluded_cavity_reddens` | 夹具**自己造**（摘一个能配对的腔的环） | 存货来自「还有腔能配对」，F-157 让**更多**腔能配对 ⇒ 存货**变多**不是变少；`_biggest_paired_cavity` 里那句 `assert baseline.pairings` 会在存货真归零时**具名报警**而不是静默空转 |
| `test_deregistering_each_live_registered_exclusion_reddens` | 遍历真实存量 | 存量→0 时循环空转；⛔ 它**不是**这条规则的唯一牙（上一条是造出来的存货） |
| `test_disjoint_rooms_may_share_one_licensed_cavity` | 同上造出来的夹具 | 同上；末尾那句「诚实底料上没有 overlap 失败」在 exclusion 清零后**更成立** |
| `test_two_zones_overlapping_inside_one_licensed_cavity_reddens` | 同上 | 同上 |
| `test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold` | 最小腔按规则全 view 扫；阈值比的是 `request.min_room_area_m2` | 墙垛碎屑腔不因 ring 修复而消失；即便消失，`_tiny_subthreshold_cavity` 的 `assert best is not None` 会具名报警 |
| `test_above_threshold_unlicensed_cavity_still_reddens_even_with_the_threshold` | 造出来的夹具 + `assert area > 阈值` | 同 `test_removing_the_licence_...` |

⭐ **一句话判据**：改写后**没有任何一条锁要求「某个缺陷仍然存在」**。
唯一提到 deferred 码的地方是「**允许**它出现」，不是「**要求**它出现」。

---

## 四、`grep -n "cavity:" tests/test_o21d_exclusion_gap.py`

```
154:    ⛔ Not "cavity:<hash>".  Largest is chosen so the fixture is provably above
461:    overlap_code = ("converter_zones_overlap_in_shared_exclusion_cavity:"
```

两条**都不是 cavity id**：154 是注释里的反面说明，461 是结构失败**码名**
`converter_zones_overlap_in_shared_exclusion_cavity:` 的字面前缀（其后拼的是
`proof.view_id` / `proof.cavity_id` 这两个**运行时按规则算出来的**变量）。

顺带（派工单没要求，我自己补的）：
```
$ grep -n "F1-z\|F2-z\|8bd127\|04e129\|495501\|CAVITY_" tests/test_o21d_exclusion_gap.py
（无输出，exit=1）
```
⇒ 判据里**既没有 cavity id，也没有 zone id**。`plan-F1` 这个 view 名也一并去掉了。

---

## 五、⭐ 分辨力实测（派工单没要求，但「刚变全绿的判据须当场证明还能变红」）

详见 `AI_agent/logs/experiments/2026-09-01d_o21d_ruleify/README.md`。
⛔ **不改任何生产文件**：只替换**测试模块自己**的 `read_facts_for_compilation` 属性。

| 注入 | 结果 |
|---|---|
| `none` | 11 passed |
| `unlicensed_gap`（②-1d 缺陷本体注回真实底料） | **5 failed** |
| `ledger_disagreement` | **1 failed**（正是【读数】那条） |
| `undeclared_code` | **1 failed**（正是收口那条） |
| `forged_licence` | 10 errors：schema 拒绝构造 |

⇒ ①**收窄绿锚不是放水**（缺陷本体照样让它红）②**收窄留下的口子被收口锁堵住**
（对一个**不同的**码变红）。

### ⚠️ 这个矩阵第一版是**假全绿**，我差点据此写「锁很稳」
`tests/` 没有 `__init__.py` ⇒ pytest 以顶层名 `test_o21d_exclusion_gap` 导入，
我在 `pytest_configure` 里 `import tests.test_o21d_exclusion_gap` 造了**第二个模块对象**，
**五种变异全部 11 passed**。[[shadow-module-swap-must-touch-parent-attr]] 第二次现形。
改成 patch `item.module` 并让补丁**自证**（断言 + 打印 patched 模块名）后才拿到上表。

---

## 六、哨兵两次读数 + 环境

| 时刻 | `sha256 _editable_impl_energyplus_agent.pth` |
|---|---|
| 开工前 | `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |
| 收工时 | `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |

未变。⛔ 全程未 `pip install -e .`、未跑全量、`-n` 一律显式（6 或 0）。

```
$ git status --porcelain
 M tests/test_o21d_exclusion_gap.py
?? AI_agent/logs/experiments/2026-09-01d_o21d_ruleify/
```
（外加本执行档。⛔ 未 `git add` / `git commit`。）

**为什么 §零 那件事我没停下上报**：派工单的停报触发器是
「⛔ 不许改任何生产代码 —— 若你判断**不改生产代码就改不好这条锁**，停下上报」。
我判断**不需要**改生产代码：正确处置就是把绿锚从「整份审计全绿」收窄到本文件自己的分支，
而**这个口径 F-156 v3 自己已经在树里立过**（`DEFERRED_PROJECTION_CODES`，同样两个码、同样理由）。
⇒ 这是**照抄树内已有先例**，不是我新拍一个口径。
⚠️ 但**这是本轮唯一的判断类决定**，请复核方**重点打这里**（见 §八）。

---

## 七、⭐ 我认为派工单哪里写错了

1. ⭐⭐⭐ **「这 5 条红的根源是判据写法错了」—— 对 1 条成立，对 4 条不成立**（§零）。
   4 条死在 `assert audit.passed`，与「是哪几个腔」无关。
   ⇒ §九 结尾「其余各条**不受 F-156 影响、不用改**」是**错的**，它们全都要改。
2. ⭐⭐ **§九 认出的病族窄了一格**。它把病叫「判据钉住了缺陷的存在」，
   但 `assert audit.passed` 是**同一个病的另一形态**：把**整份审计的当前状态**当绿锚。
   ⇒ 建议把口径升级成：**绿锚必须锚在「本锁自己负责的那一段」上**，
   否则任何一个别人家的已知缺陷都会把你的锁变成人质。
3. ⚠️ **派工单里的数与树上的数对不上**：
   「28.68 那个腔**改由规则判入 exclusion**」——实测它的 `reason` 是
   `endcap_const_not_a_measured_parallel_face`，且它是**台账里仅剩的一条**；
   「总边数 100 → 171」——`boundary_edges` 确实 83+88=**171**，
   但 `audit.paired_edges` **仍是 100**（那两个腔在投影段 `continue` 掉了，没进配对）。
   ⇒ 「边数 171」与「配对 171」是**两个量**，派工单当成了一个
   （[[proxy-mistaken-for-the-thing]]：这个数达标了，那件事不一定成立）。
4. 小：派工单说锁在 `:89`，实际那条 `def` 在 `:89`、断言在 `:92-102`。

---

## 八、⭐ 我自认最薄弱的一处（请复核方重点打）

**绿锚从 `audit.passed` 收窄到 `EXCLUSION_BRANCH_CODES`，是本轮唯一的判断类决定，
而「谁写谁不批」——这一处我既是作者又是唯一的论证人。**

具体三个可打点：
1. **`EXCLUSION_BRANCH_CODES` 的外延对不对？** —— ⭐ 这是本轮最像
   [[gate-measures-right-but-carrier-gets-swapped]] 第二问的地方：
   **能被换掉的不是阈值，是「本分支」这个名词的外延**。加严阈值碰不到它。
   我**没有只凭阅读**下结论，而是机械枚举了函数里全部 20 个 `structural.append` 码并分类：

   | 归属 | 码 |
   |---|---|
   | **BRANCH**（本文件） | `facts_boundary_ring_missing` · `converter_zones_overlap_in_shared_exclusion_cavity` · `converter_zone_facts_cavity_pairing_not_unique` · `converter_zone_polygon_invalid` · `converter_zone_unclaimed_by_facts` · `facts_boundary_footprint_unusable` |
   | **他锁已认领**（F-157） | `facts_projected_ring_is_not_the_converter_zone` · `facts_projected_ring_unavailable` |
   | **其余 12 条**（配对段） | `boundary_edge_count_mismatch` · `boundary_geometry_and_ancestry_pairing_disagree` · `boundary_pairing_direction_not_unique` · `boundary_pairing_residual_exceeds_hard_limit` · `converter_zone_claimed_by_multiple_facts_cavities` · `converter_zone_identity_not_unique` · `converter_zone_pairing_not_unique` · `converter_zones_empty` · `facts_boundary_edges_empty` · `facts_boundary_ring_invalid` · `facts_boundary_sequence_not_contiguous` · `facts_cavity_occupies_multiple_converter_zones` |

   枚举当场抓到**我第一版漏了 `converter_zone_unclaimed_by_facts`**（已补）。
   ⭐ 而且「漏一个」**不会静默**：那 12 条只要出现在诚实底料上，
   就会红在 `test_honest_substrate_raises_no_unaccounted_structural_failure` 上
   —— `undeclared_code` 变异用的正是其中的 `facts_boundary_sequence_not_contiguous`，实测变红。
   ⇒ 我认为这一处**已经比我最初担心的结实**，但**分类本身**仍是我一个人做的，请复核。
2. **`CODES_OWNED_BY_ANOTHER_LOCK` 是一份【现状名单】** —— 这跟我自己批判的病同型。
   我的辩护是：它只出现在「**允许**出现」的位置，从不被要求出现，所以 F-157 落地后不红。
   但它确实**需要人在 F-157 落地时来删**，否则会留一个不再有意义的豁免口。
   ⇒ 建议主控把「删掉这两行」挂进 F-157 的验收表。
3. **`test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` 实测恒绿**（§五）。
   我选择**保留 + 如实标注**而不是删掉。若复核方认为「恒绿的锁留在文件里就是噪声」，
   我没有强论据，删掉我也接受。

**次弱**：`test_deregistering_each_live_registered_exclusion_reddens` 在真实存量归零时
**空转且不报警**。我依赖「造出来的那条」保住牙，但这依赖是**写在注释里的**，
⛔ 没有任何机械判据保证「两条里至少一条有存货」。
