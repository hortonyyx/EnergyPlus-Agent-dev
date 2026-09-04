# B2 多楼层装配 · GPT 跨家族复核裁决

- 日期：2026-09-03
- 施工方：Claude 家族；复核方：GPT 家族
- 审对象：`git diff c13e1ec..82f9ce3`
- 工作树：`/tmp/b2_review_gpt`，detached `82f9ce3`

## 裁决

**REWORK / 阻断 3 / 不阻断 1**

正常输入下的三层混排、两层连续性、具名坏输入和 17 条新增测试都能通过；全量也确为 `3773 passed`。但本单的两根承重柱没有闭合：z 来源的可信 carrier 在 B2 入口被拆掉，且公开装配器可直接接收手造 z；另外 `PER_FLOOR_FOOTPRINT_MISMATCH` 的 message 子串重贴标签已被独立造例证实会吞掉别的 schema 错误。

## 阻断项

### B-1 · T1 在 B2 入口丢掉了 B3 的冻结字节校验 carrier

`run_multifloor_correction`（`src/agent/pipeline.py:1586-1612`）只接收脱离 artifact 的 `Sequence[FloorLevelClaimV1]`，随后直接按其中的 `z_m` 派生。它既拿不到 `frozen_sources`，也不调用 `validate_evidence_bundle`，所以无法执行 B3 已有的值↔冻结字节门（`src/agent/correction/evidence_contract.py:1674-1758`）。`FloorLevelClaimV1` 单体本身也没有这道交叉校验。

独立造例保留三条 claim 的原 `z_ref`，只把 `z_m` 手改为 `12.34 / 15.24 / 18.54`。正式 B2 入口接受并产出：

```text
OFFICIAL_ENTRY_OUTPUT_Z [(12.34, 2.9000000000000004), (15.24, 3.299999999999999)]
FULL_B3_CARRIER_WOULD_REJECT FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE
```

后一行来自把同一批伪造 claims 放回完整 B3 artifact 后调用权威 validator。也就是说，B3 的门本来能抓住，但 B2 的接口形状绕过了它。因此现有正例只证明“诚实 B3 输出能解引用”，没有证明“B2 只接受这种输出”。

返工判据：B2 的正式入口必须消费并验证能携带冻结字节的完整/封印 carrier，或在边界上等价地重验每个 `z_m == dereference(z_ref)` 及 selection-rule 完整性；常驻负例须保留 ref、只改值，并在任何 per-floor chain 执行前具名变红。

### B-2 · T5 的“无 z 参数”只有入口签名外观，存在公开手填旁路，旧生产面也未迁移

`DerivedFloorLevel` 直接暴露 `z_floor_m` / `ceiling_height_m`（`src/agent/correction/multifloor.py:55-72`）；`assemble_multifloor_geometry(levels, ...)` 又公开接收它（`:133-146`），并在 `__all__` 中导出（`:274-279`）。这正是一条入口签名之外的旁路。

独立造例没有调用 `derive_floor_ladder`，手造 `DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)` 后直接装配，得到：

```text
T5_DIRECT_ASSEMBLER_BYPASS 12.34 5.67
```

产物通过 schema 与 `check_zstack`。因此模块 docstring 所称“there is no z parameter anywhere in this module”不成立。

调用图也没有完成生产迁移：排除本单测试后，`run_multifloor_correction` 只有自身定义/内部引用，零外部生产调用；原公开 `run_correction` 仍保留 `evidence_chain_z_floor_m` / `evidence_chain_ceiling_height_m`（`src/agent/pipeline.py:1363-1364`），其文档与错误仍要求调用方声明（`:1386-1388`、`:1416-1420`）。施工档把“无人消费新多层几何”当作无碰撞结论，恰好也说明新路尚未替换旧路。

返工判据：正式可达路径上不能存在接收裸 `DerivedFloorLevel`/裸 z 的装配边界；若保留低层 helper，应使其不能成为生产能力入口，并用调用图/变异锁证明实际生产消费者已走受验证的派生 carrier。删除或绕过派生实现时必须红，直接手造 level/claim 也必须红。

### B-3 · `PER_FLOOR_FOOTPRINT_MISMATCH` 已复现吞掉别的 ValidationError

`assemble_multifloor_geometry` 在 `src/agent/correction/multifloor.py:239-264` 捕获整个 `CorrectedGeometryV3` 的 `ValidationError`，再以 `str(exc)` 是否包含固定英文句子决定重贴标签。这不是错误身份，而是无界消息文本。

独立造例让待验证 floor 同时具有：必填 `name` 缺失、`cells[0].x[0]` 字段类型错误，并额外放入一个键名恰为该 needle；两层 footprint 并不存在不一致。结果：

```text
RELABELLED_AS PER_FLOOR_FOOTPRINT_MISMATCH
ORIGINAL_ERROR_TYPES ['missing', 'float_parsing', 'extra_forbidden']
ORIGINAL_ERROR_LOCS [('floors', 0, 'name'),
                     ('floors', 0, 'cells', 0, 'x', 0),
                     ('floors', 0, 'per-floor footprints must have identical geometry')]
HAS_REAL_FOOTPRINT_MISMATCH False
```

这正面复现了复核单要求攻击的“别的 ValidationError 被吞”。此外，若失败项是普通 dict，进入重贴分支后 `floor_ids = [f.id for f in floors]` 还会再抛 `AttributeError`，把原 schema 错进一步遮掉。

返工判据：不得按 `str(exc)` 子串辨认错误；应使用结构化、稳定的错误 code/location/context，或把 common-footprint 前提做成显式、具名的前置检查。字段类型错、必填缺失、枚举/extra 越界及含同文案的用户值都必须原样保留，不得重贴 footprint 标签。

## 不阻断项

### N-1 · z-stack 连续性确实按当前构造恒真

施工方对此的自评准确：`derive_floor_ladder` 用相邻 rung 的差作高度，装配又从同一组 rung 重贴 z，所以 `z_floor[i] + height[i] == z_floor[i+1]` 按构造成立。代码确实调用了 `geometry_validator.check_zstack`（`src/agent/correction/multifloor.py:266-270`），测试也跑了 `pipeline.correction_draw_issues` 的真实连续性分支，故 T3“不得绕过/放宽”按字面通过；但这个绿读数不能证明 z 来源正确。施工方所说“真正防 z 出错的是 #1 字节引用”只在完整 B3 carrier 被验证时成立，当前被 B-1 否定。

## 复核单 §一三处逐项判断

1. **T5 无 z 参数：失败，已复现旁路。** 入口签名本身没有 z，但公开 assembler 接受手造 `DerivedFloorLevel`，且旧生产面仍在、无新生产消费者，见 B-2。
2. **`derive_floor_ladder` 选层：条件性成立，端到端不成立。** 它按 z 排序 B3 已选出的 `floor_level_claims`，没有 sm25 特化；“选哪些线”继续归 B3 是合理分工。可是 B2 只收脱离 carrier 的 claims，因而不能借用 B3 对 `FLOOR_LEVEL_SELECTION_RULE`、完整性和字节绑定的权威校验。免责只对“已验证完整 artifact”成立，对当前 API 不成立，见 B-1。
3. **footprint 重贴标签：失败，已复现。** 原始错误是 `missing + float_parsing + extra_forbidden`，没有 footprint validator 错，却被贴成 `PER_FLOOR_FOOTPRINT_MISMATCH`，见 B-3。

z-stack 自评：**“按构造恒真”准确；“#1 已能真正防错”不准确。**

## 复核单 §二两条硬约束

1. **未复现“把零洞零重叠写进验收”的违规。** 对新增生产代码和新增测试独立 grep，未见 hole/overlap/零洞/零重叠判据。B2 测试调用的 `pipeline.correction_draw_issues` 只核窗口丢失、cell id/polygon 与 z-stack，不调用 `check_coverage`，所以没有暗中把该恒真读数当分。
2. **未复现 gt 接触。** 对新增 `multifloor.py`、pipeline B2 区块及新增测试 grep `judge.gt`、`judge/gt`、`load_gt`、`case_tests/test_baseline/gt/` 均零命中。测试里的 needle 为拼接构造，不是 import/读取。复核过程也未做逐层 gt 对账。

## 八条验收逐项

| # | 判定 | 独立复核结论 |
|---|---|---|
| 1 | **失败** | 诚实 B3 artifact 的 ref 解引用正例通过；但正式入口接受 ref 不变、`z_m` 手改的 claims，并产出手改 z，见 B-1。 |
| 2 | **失败** | 摘掉派生的既有测试会响亮失败，但公开 assembler 可完全绕过派生手造 z；旧手填面未标 legacy/未迁移，见 B-2。 |
| 3 | 通过 | 两层合成 case 装出 2 个 floors；装配调用 `check_zstack`，测试另走 `pipeline.correction_draw_issues` 真实分支。连续性是构造恒真，见 N-1。 |
| 4 | 通过 | 三层 `2.9 / 3.3 / 4.2` 得到 3 层和正确高度；改形梯子得到 2 层；新增生产代码中 sm25 标高字面量零命中。 |
| 5 | **失败** | 计划数、重复 rung、退化梯子、非正高度、不同 footprint、重复 floor id 的现有负例均具名；但其它 schema 错可被错误重贴/遮蔽，见 B-3。 |
| 6 | **失败（并入 B-2）** | 施工档做了 floors 消费点走查，但没有把“新入口零生产消费者、旧 z 手填面仍可达”判为过时假设，故碰撞结论不成立。 |
| 7 | 通过 | 新增代码与新增测试对四个 gt needle 均零命中；未读 gt。 |
| 8 | 通过 | 全量 `-n 6` exit 0；`3756 + 17 = 3773`，skip/xfail 与基线一致。 |

## 测试与数量核对

开工自检：

```text
/tmp/b2_review_gpt
82f9ce3 B2 step 4: execution doc — full suite 3773 passed / 0 failed (3756+17)
/tmp/b2_review_gpt/src/agent/correction/multifloor.py
```

新增文件独立收集及运行：

```text
17 tests collected
17 passed in 7.25s
```

全量按派工要求执行（未用 `-n auto`，未执行 `pip install -e .`）：

```text
python -m pytest -q -n 6 -p no:cacheprovider
3773 passed, 2 skipped, 13 xfailed, 211 warnings in 540.70s (0:09:00)
exit 0
```

因此施工方自报的 **3773 与净增 +17 均复现**；测试全绿不抵消上述三项承重边界缺口。

## 未复现项

- 未复现 gt 接触。
- 未复现把“零洞零重叠”作为 B2 验收判据。
- 未复现 sm25 标高/层数特化或全量回归失败。

复核过程未修改项目代码；只新增本裁决文件。主控预置并暂存的复核请求单保持原状。
