# 执行档 · **B2：多楼层装配**

- **日期**：2026-09-03（第三程）· **施工方**：Claude 家族施工席
- **工作目录**：`/tmp/b2_claude` · **分支**：`wt/09.03ai_b2`
- **任务书**：[2026-09-03ai_B2_multifloor_assembly_dispatch.md](../request/2026-09-03ai_B2_multifloor_assembly_dispatch.md)
- **审**：GPT 或 GLM 家族（⛔ 不得 Claude）

---

## 一、交付概览（三段提交）

| 提交 | 内容 |
|---|---|
| step 1 | `src/agent/correction/multifloor.py`（纯模块）：`derive_floor_ladder`（T1）· `assemble_multifloor_geometry`（T2/T3/T4）· `DerivedFloorLevel` · `MultiFloorAssemblyError` |
| step 2 | `pipeline.run_multifloor_correction` + `MultiFloorPlanRun`（接线，把派生 z 喂进 `evidence_chain_z_floor_m`/`evidence_chain_ceiling_height_m`，⛔ 本入口无 z 参数）+ `PER_FLOOR_FOOTPRINT_MISMATCH` 具名守卫 |
| step 3 | `tests/test_b2_multifloor_assembly.py`（17 条，覆盖 §六 八条规则） |

**架构定位**（先复现 §一 表，⛔ 不因为是派工方量的就信 —— §七A④要求）：
- `EvidenceChainProjection.z_floor_m`/`ceiling_height_m` **必填无默认** —— ✅ 实测 `EvidenceChainProjection()` 抛 `missing 2 required positional arguments`（`pipeline.py:830-831`）。
- B1 docstring「the bridge never mints a z (B2 owns sourcing)」—— ✅ `pipeline.py:824-825` / `1387`。
- B3 落地 `floor_level_claims`（z_m + z_ref 字节出处）—— ✅ `evidence_contract.py:587-602`；实测合成三层立面派生梯子 `[0.0, 2.9, 6.2, 10.4]`。
- 连续性校验 `pipeline.py:661-668` —— ✅ 存在。

⇒ **起点确实近**：B2 = 从 `floor_level_claims` 梯子**派生** z_floor/ceiling_height，**逐层装出 `floors[]`**。⛔ 没有重新设计层模型。

**核心设计（T5 的最强形态）**：`run_multifloor_correction` 与 `assemble_multifloor_geometry` **都不设 z 参数** —— 手填那条路在类型层不存在（[[gate-measures-right-but-carrier-gets-swapped]] 首选解=让那条路在类型层不存在）。z 的**唯一**来源是 `derive_floor_ladder`；装配处把每层 z **从派生梯子重新 stamp**，即使有人喂来带手填 z 的几何也被覆盖。

---

## 二、逐条对 §六 验收报（命令原文 + 输出原文）

### #1 层高来自证据，不是手填 — ✅

`test_derived_z_dereferences_back_to_the_frozen_bytes`：抽每个派生 `z_floor` / `ceiling_height`，把 `z_floor_ref` / `z_top_ref` 解引用回**冻结字节**里的原值。`ceiling_height` 是**派生差值**，故携带**两个**操作数的字节 ref（下 rung + 上 rung），⛔ 不是裸值。

```
$ python -m pytest -q -n 6 tests/test_b2_multifloor_assembly.py::test_derived_z_dereferences_back_to_the_frozen_bytes
1 passed
```

实测梯子（合成三层 2900/3300/4200）：`z_floor=[0.0, 2.9, 6.2]`，`ceiling=[2.9, 3.3, 4.2]`，每个 z 均 `== resolve_json_pointer(frozen_doc, ref.json_pointer)`。

### #2 新链不再走手填 — ✅

两半：
- **结构半**（`test_run_multifloor_has_no_z_parameter`）：`run_multifloor_correction` 签名与 `MultiFloorPlanRun._fields` 都**不含** `z_floor`/`ceiling_height` —— 无从手填。
- **行为半**（`test_neutered_derivation_fails_loud_never_falls_back`）：monkeypatch `derive_floor_ladder → ()`（摘掉 T1 派生）⇒ `run_multifloor_correction` 抛 `MultiFloorAssemblyError(FLOOR_PLAN_COUNT_MISMATCH)`，⛔ **不静默退回任何调用方 z**。

### #3 两层 case 装出 floors[] 且过层连续性校验 — ✅

`test_two_storey_assembles_and_passes_pipeline_zstack_check`：合成 3-rung（0/2.9/3.3）→ 2 层 → 装出 `floors[]==2`，z=`[(0.0,2.9),(2.9,3.3)]`。
⭐ **过的是 `pipeline.correction_draw_issues`（661-668 的真校验），⛔ 不是私有副本**。干净装配 `correction_draw_issues == []`（含无 z-stack 断裂）。

⚠️ **诚实声明**：z-stack 连续性**按构造恒真**（`z_floor[i]+ceiling[i]==rung[i+1]==z_floor[i+1]`）—— 这道守卫只对「未来某个从别处 stamp z 的装配器」有牙。它的**通过是护栏,⛔ 不是验收信号**（呼应 §三①：不拿恒真读数当判据）。我按 T3 要求**过它、不绕过、不放宽**，但不把它当分。

### #4 层数不是常数 — ✅

- `test_three_storey_mixed_heights_assemble_three_floors`：合成 2.9/3.3/4.2 立面 → 装出 **3 层**，`ceiling=[2.9,3.3,4.2]` 各正确。
- `test_reshaped_ladder_yields_a_new_floor_count`：同一份代码换 2 层梯子 → 装出 **2 层**（层数从数据数出）。
- `test_no_sm25_elevation_reading_is_hardcoded_in_new_code`：grep 新增 B2 生产源（`multifloor.py` + pipeline B2 区块），`3.6`/`3600`/`7.202`/`7202` **零命中**。
  ⚠️ **踩坑并已修**：我起初在 `multifloor.py` docstring 写了 "3.6 m" 作反例 —— 正是 §8.5 教训（禁止的字面量别写进文件）—— 已删。

### #5 坏输入响亮失败 — ✅（各具名）

| 坏输入 | 具名错误 | 测试 |
|---|---|---|
| 楼层线数与平面份数不符 | `FLOOR_PLAN_COUNT_MISMATCH` | `test_plan_count_mismatch_is_loud` |
| 标高不单调（两 rung 同 z） | `FLOOR_LADDER_NOT_ASCENDING`（`rise_m==0`） | `test_non_ascending_ladder_is_loud` |
| 层数 < 2 | `FLOOR_LADDER_DEGENERATE` | `test_degenerate_ladder_is_loud` |
| 层高 ≤ 0 | `NONPOSITIVE_CEILING_HEIGHT` | `test_nonpositive_ceiling_is_loud` |
| per-floor footprint 不一致（退台） | `PER_FLOOR_FOOTPRINT_MISMATCH` | `test_per_floor_footprint_mismatch_is_loud` |
| 两层同 floor_id | `DUPLICATE_FLOOR_ID` | `test_duplicate_floor_id_is_loud` |

### #6 §五那条规则我自己走了一遍 — ✅（见 §三）

### #7 ⛔ 零 gt 接触 — ✅

`test_new_files_never_touch_gt`：扫 `multifloor.py` + 本测试文件 + pipeline B2 区块，`judge.gt`/`judge/gt`/`load_gt`/`case_tests/test_baseline/gt/` **零命中**。
⭐ needle **拼接构造**（`"judge"+".gt"` 等），使本文件不自匹配自己的扫描（[[proxy-mistaken-for-the-thing]] 反面：先想「我扫的会不会命中我扫描代码本身」）。

### #8 全量绿 — ⏳（见 §四）

---

## 三、§五 单外对撞走查（grep 原文 + 逐处结论）

**规则**：对本单新增/改动的每个名词，全仓 grep，逐处问「这里握着一份【单层】假设吗？我这次改动会不会让它过时？」

我的改动**只新增**多层装配路径（`run_multifloor_correction` 等），**未改** `z_floor`/`ceiling_height`/`floors[]` 既有语义。

### A) `floors[0]` 生产侧消费点

```
$ grep -rn "floors\[0\]" src/ --include="*.py" | grep -v test
src/agent/judge/tarch_normalize.py:3087:    floor = request.floors[0]
src/agent/correction/schema.py:370:    # 注释
src/agent/correction/vocab.py:310:    # 注释
src/agent/correction/multifloor.py:212:        src = geom.floors[0]     ← 本单：单层几何取其唯一层，前面已断言 len==1
src/agent/correction/footprint.py:51:        floor = geom.floors[0]
src/agent/correction/envelope.py:202:  ...footprint.floors[0]
```

| 位置 | 握着单层假设? | 我的改动会否让它过时? |
|---|---|---|
| `footprint.py:51` (`footprint_bbox`) | 仅当调用方**不传** `floor` 时默认 `floors[0]`；API 已支持显式传层 | ❌ 不会 —— 我的产物不流经它；多层消费方本就该显式传 floor |
| `envelope.py:202` (`_projection_extent_vertices`) | 注释明写「All floors must be topology-identical before a transaction」= **共底面假设** | ❌ 不会 —— 与我的 `PER_FLOOR_FOOTPRINT_MISMATCH` **同一假设**；共底面下 `floors[0]` 有代表性 |
| `tarch_normalize.py:3087` | judge 侧（gt 消费），非我路径 | ❌ 不会 |
| `multifloor.py:212` | 本单自己：取单层几何的唯一层，**前一行已 `if len(geom.floors)!=1: raise`** | —— |

### B) `len(...floors)` / 遍历 floors 生产侧

```
$ grep -rn "\.floors)" src/agent --include="*.py" | grep -vi test
（关键项）
src/agent/geometry/modelling.py:546:  floors_by_z = sorted(enumerate(geom.floors), ...)   ← 已按 z 排序遍历全部层 + z-stack 守卫
src/agent/correction/geometry_validator.py:219:  total = sum(len(fl.cells) for fl in geom.floors)  ← 遍历全部层
src/agent/correction/window_sources.py:1044:  if len(refs) != len(producer.floors): ...  ← 已按层数对账
```

⇒ **几何内核（modelling.py）与校验器本就遍历全部层**，多层安全。

### C) 谁调用我的新路径

```
$ grep -rn "run_multifloor_correction\|assemble_multifloor_geometry\|derive_floor_ladder" src/ scripts/ --include="*.py" | grep -v "multifloor.py:"
（仅 pipeline.py 内部定义/自调用，无外部生产调用点）
```

⇒ **无任何生产代码消费我的多层几何** —— 它是终端产物。故我的 1→N 改动**当前不使任何消费点过时**。

**§五 第 5 处（B 层）**：`footprint.py:51` 的「不传 floor 则默认 `floors[0]`」缺省，**当 B5 把多层几何接下游时**要在每个调用点确认传了正确的 floor。现在无害（无人喂多层），登记为随 bundle travel 的显式债。

---

## 四、全量绿（#8）

**基线** = `3756 passed / 2 skipped / 13 xfailed / 0 failed`（主控合并树权威读数）。
本单**净增** = 1 模块 + 1 函数 + **17 测试**，⛔ 未改既有测试。预期 = `3773 passed`。

```
$ python -c "import src.agent.pipeline as m; print(m.__file__)"
/tmp/b2_claude/src/agent/pipeline.py     ← 落在本 worktree（cwd 胜过 .pth）

$ python -m pytest -q -n 6 -p no:cacheprovider
3773 passed, 2 skipped, 13 xfailed, 211 warnings in 577.01s (0:09:37)
```

✅ **逐位闭合 `3756 + 17 = 3773`**，`2 skipped` / `13 xfailed` / **`0 failed`** 与基线一致，exit 0，`__file__` 落本 worktree。

⚠️ 同机有 GPT 席位复审 B4，预期竞争；判假红看有无 summary 行（[[repeat-the-run-before-accusing-a-seat]]）。

---

## 五、⭐ 我自己认为最薄弱的一处 + 希望复核方重点打哪里

**最薄弱**：**#3 的 z-stack 连续性按构造恒真**（我在 §二#3 已诚实声明）。这道校验我确实过了、没绕过没放宽，但它的通过对「z 派生对不对」没有分辨力 —— 真正防 z 出错的是 **#1 的字节解引用**和 **#2 的无-z-参数结构**。如果复核方认为 T3「过 661-668」需要一条**有牙**的连续性证据，我这里给不出（因为在本链它恒真，正如 §三① 所警告）。

**希望复核方重点打**：
1. **T5 的无-z-参数是否真的堵死了手填**：能否找到一条路径，让 `run_multifloor_correction` 的产物里某层 z **不来自** `derive_floor_ladder`？（我的断言是：装配处从 `levels` 重新 stamp，且入口无 z 参数 ⇒ 堵死。请攻这个断言。）
2. **`derive_floor_ladder` 的选层是否真跟数据走**：我复用 B3 已落地的 `floor_level_claims`（B3 的 `FLOOR_LEVEL_SELECTION_RULE` 已过审）。如果 B3 的梯子选错，我这里会跟着错 —— 但那是 B3 的账，不是我重造。请确认我**没有**在梯子上再加任何 sm25 特化。
3. **`PER_FLOOR_FOOTPRINT_MISMATCH` 是否掩盖**：我**捕获 schema 自己的裁决**重贴标签（⛔ 没重实现校验）。请确认这个 catch 不会把**别的** ValidationError 也吞成 footprint 错（我按 message 子串判定，非该 message 则 `raise` 原样抛）。
