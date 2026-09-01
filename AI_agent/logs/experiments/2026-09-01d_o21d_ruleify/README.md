# 2026-09-01d · ②-1d exclusion 锁「规则化」的分辨力实测

配套执行档：`AI_agent/logs/reviews/execution/2026-09-01d_o21d_ruleify_execution.md`

## 文件
- `before.txt` / `after.txt` — 改写前 / 改写后 `pytest -n 6 tests/test_o21d_exclusion_gap.py` 原文
- `probe_state.py` — F-156 v3 落树后 sm25 真实读数（台账 3→1 条；两个走廊腔已成环）
- `probe_fixture.py` — 「按规则挑一个腔 → 摘掉它的环 → 发/不发登记」夹具原型
- `probe_shared.py` — 「一个已登记腔里放两个 zone，重叠/不重叠」夹具原型
- `mutation_plugin.py` — ⭐ 变异矩阵。⛔ **不改任何生产文件**，只替换**测试模块自己**的
  `read_facts_for_compilation` 属性，让每条锁走**真实入口**读一份有病的底料。

## ⚠️ 先踩后填：变异矩阵第一版是**假全绿**
第一版用 `pytest_configure` + `import tests.test_o21d_exclusion_gap`。
`tests/` **没有 `__init__.py`** ⇒ pytest 把它作为顶层模块 `test_o21d_exclusion_gap` 导入，
我那句 import 造了**第二个模块对象**，补丁打在没人用的对象上 ⇒ 五种变异**全 11 passed**，
读起来像「锁很稳」，其实是**一次变异都没生效**。[[shadow-module-swap-must-touch-parent-attr]]

改法：挪到 `pytest_collection_modifyitems`，patch `item.module`（pytest 真正导入的那个），
并让补丁**自证**（`assert module.read_facts_for_compilation is _patched` + 打印 patched 模块名）。

## 变异矩阵读数（修好接线之后，`-n 0`）

| 注入 | 含义 | 结果 |
|---|---|---|
| `none` | 未扰动 | **11 passed** |
| `unlicensed_gap` | ⭐ ②-1d 缺陷本体：真实底料上摘掉一个大腔的环、**不发登记** | **5 failed** |
| `ledger_disagreement` | `as_signed` 台账 ≠ `as_measured` 台账 | **1 failed**（正是【读数】那条） |
| `undeclared_code` | 造一个既不属本文件分支、也不属他锁的结构失败码 | **1 failed**（正是收口那条） |
| `forged_licence` | 一个腔**同时**有环和登记 | **10 errors**：文档 schema 直接拒绝构造 |

逐条红的是谁：

```
-- unlicensed_gap
FAILED ...::test_every_exclusion_is_licensed_by_evidence_it_actually_points_at
FAILED ...::test_honest_substrate_raises_no_unaccounted_structural_failure
FAILED ...::test_removing_the_licence_from_an_excluded_cavity_reddens
FAILED ...::test_disjoint_rooms_may_share_one_licensed_cavity
FAILED ...::test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold
-- ledger_disagreement
FAILED ...::test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores
-- undeclared_code
FAILED ...::test_honest_substrate_raises_no_unaccounted_structural_failure
```

## 两条结论
1. **收窄绿锚不是放水**：`unlicensed_gap` 把 ②-1d 缺陷本体注回真实底料，
   收窄后的绿锚**照样红**（5 条）；而 `undeclared_code` 证明**收窄留下的口子被收口锁堵住了**
   —— 那条锁对一个**不同的**码变红。
2. **`forged_licence` 是一条【没有牙】的锁**：`as_measured_boundary_cavity_has_edges_and_loss`
   这个 schema 校验器让该底料**根本构造不出来** ⇒
   `test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` 走真实入口**恒绿**。
   已在该测试的 docstring 里**如实标注**，⛔ 不计入 exclusion 分支的覆盖。

## 复跑
```bash
for m in none unlicensed_gap ledger_disagreement undeclared_code forged_licence; do
  O21D_MUTATION=$m PYTHONPATH=/workspaces/EnergyPlus-Agent-dev python -m pytest -n 0 -q \
    -p AI_agent.logs.experiments.2026-09-01d_o21d_ruleify.mutation_plugin \
    tests/test_o21d_exclusion_gap.py
done
```

## 附：`reconcile_boundary_basis` 全部结构失败码的机械枚举与分类

```
BRANCH     converter_zone_facts_cavity_pairing_not_unique
BRANCH     converter_zone_polygon_invalid
BRANCH     converter_zone_unclaimed_by_facts
BRANCH     converter_zones_overlap_in_shared_exclusion_cavity
BRANCH     facts_boundary_footprint_unusable
BRANCH     facts_boundary_ring_missing
OTHERLOCK  facts_projected_ring_is_not_the_converter_zone
OTHERLOCK  facts_projected_ring_unavailable
  --       boundary_edge_count_mismatch
  --       boundary_geometry_and_ancestry_pairing_disagree
  --       boundary_pairing_direction_not_unique
  --       boundary_pairing_residual_exceeds_hard_limit
  --       converter_zone_claimed_by_multiple_facts_cavities
  --       converter_zone_identity_not_unique
  --       converter_zone_pairing_not_unique
  --       converter_zones_empty
  --       facts_boundary_edges_empty
  --       facts_boundary_ring_invalid
  --       facts_boundary_sequence_not_contiguous
  --       facts_cavity_occupies_multiple_converter_zones
```

⭐ 枚举当场抓到第一版 `EXCLUSION_BRANCH_CODES` **漏了 `converter_zone_unclaimed_by_facts`**
（本分支自己的完备性声明），已补。
⭐ `--` 那 12 条属配对段，由别的锁负责；它们只要出现在诚实底料上，
就会红在 `test_honest_substrate_raises_no_unaccounted_structural_failure` 上
（`undeclared_code` 变异用的就是其中的 `facts_boundary_sequence_not_contiguous`）。
