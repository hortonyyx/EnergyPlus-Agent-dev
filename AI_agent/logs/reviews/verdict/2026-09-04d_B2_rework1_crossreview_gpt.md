# B2 返工 1 · GPT 跨家族复核裁决

- 日期：2026-09-04
- 施工方：Claude 家族；复核方：GPT 家族
- 审对象：`git diff 82f9ce32..a45f778c`
- 工作树：`/tmp/b2rw_review_gpt`，detached `a45f778c`
- 主线 B4 参照：合并提交 `5804ae4b`

## 裁决

**REWORK / 阻断 2 / 不阻断 1**

B-1 的正式入口字节门已闭合，施工方自报的 `3777 = 3773 + 4` 也完整复现。但 B-2 要求的“手填 z 的路在类型层不存在”仍未成立：把裸 z 字段移进 `FloorLevelClaimV1.z_m`、把载体改成私有类和只读 property，并没有产生“已验证 claim”这一不同类型；两个仍公开导出的 helper 可直接把手改 claim 装配成功。旧 `run_correction` 裸 z 面也仍在，且新入口仍无生产调用者。

B-3 的上轮指定造例已经修好，但新结构判据把所有 empty-loc `value_error` 都当 footprint；我在今天的构造点造出“空 floor id”这一同结构、非 footprint 错，仍被误贴为 `PER_FLOOR_FOOTPRINT_MISMATCH`。因此三条上轮阻断中 B-1 关闭，B-2 未关闭，B-3 只修了原样本而未修判据。

## 阻断项

### B-2 · “无裸字段”不等于“已验证类型”：公开 helper 仍可把手填 z 装配成功；旧面也未迁移

返工把原 `DerivedFloorLevel(z_floor_m=..., ceiling_height_m=...)` 改成私有 `_DerivedFloorLevel(lower, upper)`，并让 z 从 `lower.z_m` / `upper.z_m` 的 property 计算（`src/agent/correction/multifloor.py:72-122`）。这确实封住了**上轮那一种构造语法**，但没有封住那项能力：

- `FloorLevelClaimV1` 同时承载 `z_m` 和 `z_ref`；“未验证 claim”与“已通过冻结字节门的 claim”在类型上仍是同一个类。
- `derive_floor_ladder(claims)` 不验 carrier，接收该裸 claim 类型（`:147-200`）。
- `derive_floor_ladder` 与 `assemble_multifloor_geometry` 仍同时列在 `__all__`（`:348-352`）；Python 的下划线也不是访问控制。

我没有复用施工测试里的 `12.34/5.67` 私有类构造，而是保留两个诚实 claim 的原 `z_ref`，仅以 Pydantic 的公开 `model_copy` 把 `z_m` 改成 `12.34/17.91`，再只走两个公开 helper：

```text
B2_RESULT=ASSEMBLED [(12.34, 5.57)]
B2_REFS_UNCHANGED True True
B2_EXPORTS True True
```

这条路甚至不必直接 import `_DerivedFloorLevel`：公开 `derive_floor_ladder` 会替调用方铸造它。也就是说，改动不是简单“加一句检查”，但它仍只改变了手填位置和表面签名，没有在类型层区分 validated/unvalidated carrier；返工门不通过。

旧生产面也没有完成迁移：`run_correction` 仍公开接收 `evidence_chain_z_floor_m` / `evidence_chain_ceiling_height_m`（`src/agent/pipeline.py:1366-1367`），仍要求 caller 声明并直接构造 projection（`:1389-1422`、`:1437-1440`）。全仓排除测试后，`run_multifloor_correction(` 仍只有自身定义，零生产调用者；所以“旧消费者已改走受验证入口”也没有证据。此项并入同一个 B-2 阻断，不重复计数。

返工判据不变：装配边界必须消费类型上不可与未验证 claims 混淆的封印/validated carrier，或只让验证入口拥有装配能力；低层 helper 的组合不能重新获得生产装配能力。旧生产消费者须真实迁移，不能以“新入口存在但无人调用”代替。

### B-3 · `loc == () / type == value_error` 不是 footprint 的稳定身份，已复现再次误贴

新 `_is_footprint_mismatch_error` 的全部判据是：每条错误均为 `loc == ()` 且 `type == "value_error"`（`src/agent/correction/multifloor.py:125-144`）。但 Pydantic 对 `CorrectedGeometryV3._v3_integrity` 中**所有** model-level `ValueError` 都给这个结构；schema 在 footprint 之前还有 floor id 非空/全局唯一规则（`src/agent/correction/schema.py:487-490`），以后若带入 windows/segments 还会有更多同结构规则（`:492-534`）。

我先确认上轮指定攻击已修复：用一个 proxy 让 assembler 的最终构造收到“`name` 缺失 + `cells[0].x[0]` 类型错 + 键名撞 needle”，结果是原始错误，不再重贴：

```text
B3_ORIGINAL_RESULT=RAW_VALIDATION_ERROR
B3_ORIGINAL_TYPES ['missing', 'float_parsing', 'extra_forbidden']
B3_ORIGINAL_LOCS [('floors', 0, 'name'),
                  ('floors', 0, 'cells', 0, 'x', 0),
                  ('floors', 0, 'per-floor footprints must have identical geometry')]
```

随后独立重造当前“唯一可达”推理：从合法 `CorrectedGeometryV3` 取得 `FloorV3`，用 Pydantic 公开但免重验的 `model_copy(update={"id": ""})` 形成仍具 `FloorV3` 类型的输入，footprint 保持不变。assembler 的最终 schema 构造实际报的是空 id，却被现判据重贴：

```text
B3_EMPTY_LOC_RESULT=RELABELLED PER_FLOOR_FOOTPRINT_MISMATCH
B3_EMPTY_LOC_CAUSE [('value_error', (),
  'Value error, v3 floor ids must be non-empty and globally unique')]
```

因此“本构造点唯一可达的 empty-loc value_error 是 footprint”今天已经为假；docstring/注释只记录假设，不能阻止错误身份漂移。应现在改为显式 common-footprint 前置比较，或让 schema 抛可稳定辨认的专用 error code/子类；不能继续用所有 model-validator 共用的 `loc/type` 二元组代替错误身份。

## B-3 最薄弱处三问正面回答

1. **“唯一可达”今天成立吗？不成立。** 上述空 floor id 是今天即可达的另一条 empty-loc `value_error`，且现场已被误贴；不依赖 B4。
2. **“将来 B4 若往这里装 windows/segments”已经到了吗？条件本身尚未到。** B4 确已由 `5804ae4b` 合并进主线，但该合并的实际代码 diff 只有独立的 `src/agent/correction/opening_synthesis.py` 与其测试；B4 派工还明确禁止多层装配。最终 B4 模块产出独立 `OpeningSynthesisV1` 配对产品，不 import/构造 `CorrectedGeometryV3`、`WindowV3` 或 `FacadeSegment`，也未接入 `run_multifloor_correction`。本复核 HEAD 也在该主线合并的旁支，尚不包含 `5804ae4b`。当前 B2 构造仍写死 `windows=[]` / `facade_segments=[]`（`multifloor.py:310-318`）。所以是“B4 已在主线”，但不是“B4 已把 windows/segments 装到这个构造点”。
3. **留档够不够？不够，应现在补。** 不是因为 B4 已把字段带进来，而是因为 B4 之前就已有 floor-id 反例。即使 B4 永远不接这里，现判据也已经误报；若未来真的携入 windows/segments，只会扩大同结构错误集合。

## 不阻断项

### N-1 · B4 主线合并与本返工树尚未组合验证，但不是本次误标成立的前提

当前审树和 B4 合并树是两个旁支；本轮按复核单只核 B2 返工树的 `3777`，没有擅自合并 B4，也没有宣称跑过组合树。B4 当前没有触碰 B2/pipeline，故未发现直接文本碰撞；最终合并后的组合全量与后续把 `OpeningSynthesisV1` 消费进几何的接线仍应由主控/后续批次验证。这不减轻上面的 B-3：反例在当前树已经成立。

## 上轮三条阻断逐条复核

| 上轮项 | 本轮判定 | 独立变异结果 |
|---|---|---|
| B-1 冻结字节 carrier | **通过，未复现旧旁路** | 改中间 rung `2.71 -> 8.7654321`、保留 ref、重封印后，正式入口报 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`；`CHAIN_CALLS 0`。 |
| B-2 类型层无手填 z | **失败，已复现新旁路** | 手改 claims 为 `12.34/17.91`，只走两个公开 helper，成功产出 `z=12.34, h=5.57`；refs 未改。 |
| B-3 footprint 错判 | **原指定造例通过；总体失败** | 缺字段+类型错+撞 needle 不再重贴；但空 floor id 的 empty-loc model error 被重贴，结构判据仍不具错误身份。 |

## 复核单 §四六条验收

| # | 判定 | 结论 |
|---|---|---|
| 1 | **通过** | z 漂移由正式入口机器门拒绝，且在任何 per-floor chain 前触发。 |
| 2 | **失败** | validated/unvalidated claims 没有类型区分；公开 derive+assemble 组合仍接受手填 z，见 B-2。 |
| 3 | **失败（并入 B-2）** | `run_correction` 裸 z 参数仍在；`run_multifloor_correction` 零生产调用者，未证明旧消费者迁移。 |
| 4 | **失败** | 已不读 message 文本，但 `loc/type` 对所有 model-level `ValueError` 同形；空 id 已误贴，见 B-3。 |
| 5 | **通过** | B2 文件 21 条全部通过；三层混排、两层连续性、具名坏输入与原 17 条均未退化。 |
| 6 | **通过** | 全量 `-n 6` exit 0，`3777 passed / 2 skipped / 13 xfailed`；`3773 + 4 = 3777`，局部 `17 + 4 = 21` 均逐位闭合。 |

## 测试与数量核对

开工自检：

```text
/tmp/b2rw_review_gpt
a45f778c B2 rework 1 · execution doc — full suite 3777 passed / 0 failed (3773+4)
/tmp/b2rw_review_gpt/src/agent/correction/multifloor.py
```

B2 局部：

```text
21 tests collected in 1.11s
21 passed in 5.01s
```

以上局部读数来自显式 `-n 6` 的重跑。操作记录据实：第一次辅助局部命令没有显式写 `-n`，随后发现项目 `pyproject.toml` 默认 `addopts` 含 `-n auto`；该次读数已弃用，并立即以显式 `-n 6` 重跑。正式全量从一开始就是显式 `-n 6`。

按复核单指定参数跑全量（未用 `-n auto`，未执行 `pip install -e .`）：

```text
python -m pytest -q -n 6 -p no:cacheprovider
3777 passed, 2 skipped, 13 xfailed, 211 warnings in 577.57s (0:09:37)
exit 0
```

有 summary 且 exit 0，故不是同机竞争假红；施工方自报 `3777（3773+4）` **已复现**。

## GT 与未复现项

- 未重做逐层 gt 对账；接受树内 judge 记录的 z 梯子结论，但它只覆盖 z 维度。
- **F-1 生产帧平面几何零 gt 对账原样挂着**；本裁决不把 z 对账推广成 F-1 已解。
- 未复现 B-1 上轮的正式入口漂移接受。
- 未复现 B-3 上轮那一组“缺字段 + 类型错 + 键名撞 needle”误贴；复现的是同一判据下另一条 today-reachable model-level 错误。
- 未复现全量回归失败、测试数虚报或无 summary 的竞争假红。

复核过程未修改项目代码；只新增本裁决文件。主控预置并暂存的复核单保持原状。
