# F-17 调查：envelope 变换在**跨轴组件**下把直角切成 45° 斜边

> **2026-08-09 · orchestrator 亲跑 · 零 LLM 成本 · 只读 · 零生产码改动**
> 观测钩子只在复现进程内 monkeypatch，不落生产码。三个可复跑脚本在本目录 `tools/`。
>
> **起因**：F-16 修法经真链路证实解开后（run `run_2026-08-08_f16_e2e_verify`），
> 崩溃位置从 parse 层后移到确定性核，当场撞出本条：
> `ValueError: cell RM1F_01: polygon edge 3 is not orthogonal`。

---

## 0. 一句话结论

**`_apply_components` 顺序就地改写同一份几何，但四个 envelope 组件的 `intervals`
全部是在【变换前】的坐标系里算好的。当第二个组件与第一个正交时，
公共角点已被前一个组件挪出后一个组件的区间判定 ⇒ 角点漏移；
同时 `_materialize_axis_splits` 又在原位插了一个新点补上 ⇒
一个直角裂成两个点、连线成 45° 斜边。**

⛔ **这推翻了立项时登记的推断**（plan.md 六之十一）：
~~「`_materialize_axis_splits` 插中间点后只移动落在 component 上的点 ⇒ 共线三点中间被移出斜边」~~
—— 实测**单个组件永远不产生斜边**，斜边**必须两个正交组件**才出现。原推断描述的是单组件内部的部分移动，
不是实际机理。⇒ 呼应既有纪律：**归因假设未验证不得成修法依据。**

---

## 1. 复现（官方入口，非夹具）

输入 = 那次真链路落盘的 `1_correction/correction_geometry.json`（模型真实产物），
经 `parse_correction_draw` → `build_verified_window_inputs_from_run` → `finalize_correction_draw`
官方三步，**不绕过任何门**。

```
[setup] 剥掉派生 floor 的窗数 = 15/15        ← 见 §7「重放姿势」
[setup] parse OK · schema_version=3 · floors=2 · windows=15
[setup] envelope_axis_attach_tol_m = 0.01
[run]   ValueError: cell RM1F_01: polygon edge 3 is not orthogonal
```

脚本：`tools/f17_repro.py`

### 实测事实（与推断严格分开）

- 模型输出 **14 个 cell 全部 `polygon: None`**（合法：用矩形 `x`/`y` 边界）；
  `RM1F_01 = x[0.12, 5.0] × y[5.0, 7.88]` 是**标准轴对齐矩形**。
  ⇒ **模型没画非正交多边形，重抽多少次都没用。**
- 那次 envelope 证据产生 **4 个 intent**（footprint `[0.12,14.88]×[0.12,7.88]` **四条边全要动**）：

| 组件 | 轴 | old → new | intervals（另一轴的范围） |
|---|---|---|---|
| 1 | x | 0.12 → 0.0 | y ∈ [0.12, 7.88] |
| 2 | x | 14.88 → 15.0 | y ∈ [0.12, 7.88] |
| 3 | y | 0.12 → 0.0 | x ∈ [0.12, 14.88] |
| 4 | y | 7.88 → 8.0 | x ∈ [0.12, 14.88] |

---

## 2. 逐步坐实：斜边诞生在**第一个正交组件**那一步

`tools/f17_stepwise.py` —— 用官方 `_apply_components` 一次只喂一个组件：

```
step 1: x 0.12 → 0.0     footprint = [(0.0,0.12),(14.88,0.12),(14.88,7.88),(0.0,7.88)]   斜边: 无
step 2: x 14.88 → 15.0   footprint = [(0.0,0.12),(15.0,0.12),(15.0,7.88),(0.0,7.88)]     斜边: 无
step 3: y 0.12 → 0.0     footprint = [(0.0,0.12),(0.12,0.0),(14.88,0.0),(15.0,0.12),
                                      (15.0,7.88),(0.0,7.88)]                            斜边: 2 条 ⇐ 就是这一步
                         ⇒ ValueError: cell RM1F_04: polygon edge 0 is not orthogonal
```

### 机理（逐行）

以左下角 `(0.12, 0.12)` 为例：

1. **step 1**（x 组件）把它挪到 `(0.0, 0.12)`。
2. **step 3**（y 组件，区间是 x ∈ [0.12, 14.88]）判定它：
   `_on_component` 要求 `point[0]` 落在区间内，而它的 x 已经是 **0.0 < 0.12 − 0.01** ⇒
   **判为「不在组件上」，不移动。**
3. 同时 `_materialize_axis_splits` 在那条已被拉长的底边 `(0.0,0.12) → (15.0,0.12)` 上
   插入区间端点 `0.12`（**现在才严格落在边内部**）⇒ 新点 `(0.12, 0.12)`；该新点在区间内 ⇒ 被移到 `(0.12, 0.0)`。
4. ⇒ `(0.0, 0.12) → (0.12, 0.0)`，**dx = dy = 0.12 的 45° 切角**。

**佐证（强）**：在**干净的原始几何**上，四个组件的 materialize 插点数**都是 0**
（脚本实测）。⇒ **插点本身就是顺序污染的产物，不是设计意图。**

---

## 3. 组合矩阵（四格实测精神，15 个组合全跑，零例外）

`tools/f17_matrix.py`：

| 组件组合 | 跨轴 | 斜边总数 | 结果 |
|---|---|---|---|
| 任意单个（4 种） | 否 | **0** | OK |
| `x-lo + x-hi` | 否 | **0** | OK |
| `y-lo + y-hi` | 否 | **0** | OK |
| 任意 x + 任意 y（4 种） | **是** | **4** | ValueError |
| 任意三个（4 种） | **是** | **8** | ValueError |
| 四个全上 | **是** | **16** | ValueError |

**⇒ 跨轴 ⇔ 斜边，判据完全干净。斜边数 = 4 × (x 组件数 × y 组件数)。**

**中招判据 = cell 碰不碰 footprint 的角**（F1 实测）：

| cell | 边界 | 碰角 | 结果 |
|---|---|---|---|
| `RM1F_01` `RM1F_03` `RM1F_04` `RM1F_06` | 各占一个角 | ✅ | **全部出斜边** |
| `RM1F_02` `RM1F_05` | 只贴一条边 | ❌ | 正常 |
| `CORR_1F` | 贴左右两条边、不碰角 | ❌ | 正常 |

---

## 4. 为什么单测全绿 —— 且 legacy 路径**本来是对的**

### 4.1 v3 测试夹具的形态分布挡住了这个场景

全仓走 `apply_v3_envelope_transaction` 的夹具（`test_c2_b2b_envelope_transform.py` 的 `_geom()`/`_u_geom()`、
`test_c2_b5_host_resolution.py` 的 `RECT`/`U_RING`/`L_RING`/`PARTIAL_EAST_RING`）
**footprint 环全部以 `[0.0, 0.0]` 起** ⇒ lo 侧本就在 0、不产生 lo 侧 intent
⇒ **结构上凑不出「一个 x 组件 + 一个 y 组件」这一对**。

⇒ **F-5 那族的又一次现形**：夹具的**形态分布**与真实产出不同（真实产物四条边全偏移 0.12），
实现与夹具自洽、测试永远绿，而任何真实产物必崩。
与「墙 3」那条（夹具全是人手写的 IDD-correct 顺序，真实 LLM 从不产出该形态）同型。

### 4.2 ⭐ legacy 路径用**同一组真实数字**测过，而且是对的

`tests/test_deterministic_core.py::test_authoritative_envelope_accepts_bounds_and_moves_only_perimeter_edges`
的夹具 `_three_bay_inset()` 用的**正是** `footprint_x=[0.12, 14.88]`、`footprint_y=[0.12, 7.88]`，
且**同时声明 x 与 y 两个轴**，断言：

```python
assert cells["A"].x == [0.0, 5.0]
assert cells["A"].y == [0.0, 8.0]      # ← 跨轴角点两个方向都移对了
```

**它是 v1/v2 几何，走 `_apply_legacy_envelope_reconcile`。**

### 4.3 ⇒ 根因的架构级表述

| | 表示 | 「改哪个坐标」怎么决定 | 跨轴独立性 |
|---|---|---|---|
| **legacy** | cell 的 **bbox**（`cell.x` / `cell.y`） | **索引**：`values[edge_idx] = new_value` | ✅ 天然独立 |
| **v3** | cell 的**顶点环** | **坐标匹配谓词**：`_on_component(point, …)` | ❌ 谓词在第一次移动后失效 |

**⇒ v3 重写把表示从 bbox 换成顶点环，「改哪个坐标」从索引变成了坐标匹配；
而匹配用的尺子锚在变换前的坐标系，用来量已经被前序组件挪过的点 ⇒ 跨轴耦合。**
**legacy 的正确性来自表示本身，不是来自额外的防护 —— 所以换表示时它被静默丢掉了。**

### 4.4 为什么潜伏了近一个月才炸

代码出生 `4e3cb49`（**2026-07-12** `7.12_B2b_EnvelopeAtomicTransformClosure`）。
走到这段需要**两个条件同时成立**：① 产物是 `schema_version=3`；② envelope 证据产生 ≥2 个**正交**轴的 intent。

08-07 那次「后半条链跑通」用的是 **legacy 形态**的 correction 产物（`schema_version=None`）⇒ 整段跳过。
**F-16 修好之后，模型的 draw 第一次通过 parse 层全部门 ⇒ 第一次真正走到 v3 envelope transaction ⇒ 当场炸。**

⇒ 属 **B 类潜伏「一直是坏的，但没东西跑到那一段」**，与 F-10（`check_mep` 签名漂移断一个月）同型。

---

## 5. ⛔ 同一个缺陷有**两条出口**，一条炸穿一条背锅

`_apply_components` 末尾的校验循环（`envelope_transform.py:422-424`）在
`run_envelope_hard_gates` **之前**，且**不在任何 try 里**：

| 情形 | 走哪条路 | 后果 |
|---|---|---|
| **cell 碰角 ⇒ cell 出斜边** | `_apply_components` 内**裸 `ValueError`** | **炸穿整个 flow**，`attempts/` 零归档（当前实际发生的） |
| **cell 都不碰角 ⇒ 只有 footprint 出斜边** | `run_envelope_hard_gates` → `validate_final_corrected_geometry` → `_ring_checks` 借 `validate_cell_polygon` 查 footprint 正交 ⇒ `correction.envelope_ring_valid = False` | 结构化拒绝、正常归档**重抽** —— **但重抽永远没用**（斜边是内核造的），静静烧钱到 quarantine |

**⇒ 分类修法的落点很精确**：那三行校验要么并进 gates、要么包成 `EnvelopeTransformRejected`。
**⛔ 但不能只做分类修法** —— 否则第二条出口会把内核 bug 一直记在模型账上（归因错位）。
第一条出口与 **F-15 第二堵墙**同型（裸 ValueError 拿不到重试引导）。

---

## 6. 修法方向（已用反事实探针验证可行，⛔ 非提交实现）

**把「边移边判」改成「先在变换前的几何上一次性定位，再统一移动」** ——
一个顶点可同时命中 x 与 y 组件，各改各的分量（恰好恢复 legacy 的跨轴独立性）。

`tools/f17_matrix.py` §B 实测：

```
斜边总数 = 0
F1 footprint = [(0.0,0.0), (15.0,0.0), (15.0,8.0), (0.0,8.0)]
7 个 cell 全部轴对齐矩形 · validate_cell_polygon 全部通过
```

几何结果也正是应该的：14.76 × 7.76 被 envelope 证据校正成 **15.0 × 8.0**。

### ⛔ 施工必须避开的两个坑

1. **⛔ 不许顺手砍掉 `_materialize_axis_splits`。**
   本探针里它零插点，**只因为这个 case 是简单矩形**；L 形 / U 形的 T-junction 真要靠它
   （`_floor_axis_edges` 的图闭包就是为它设的）。修法只该改「定位用哪套坐标」。
   ⇒ 这正是「删『多余』规范化前先找它服务的对外契约」那条纪律的形状。
2. **⛔ 不许给正交校验加豁免**。斜边是真的斜边，不是编码差异。

### 建议的验收锁（形态）

- **必须有一把锁钉在「跨轴组件对」这个形态上**，且夹具 footprint 的 lo 侧 **≠ 0**
  （否则复现不出来 —— 这正是全仓 2323 绿却漏掉它的原因）。
- 断言**等于手算值**（`(0,0),(15,0),(15,8),(0,8)`），⛔ 不许只断言「没抛异常」。
- **neuter 方向**：把定位改回「边移边判」，锁必须转红。
- **⛔ 防假验证自检**：验收路径必须真的经过 `_apply_components`
  （`--intake-from` 之类跳段入口会绕开它）。

---

## 7. 副产：落盘 `correction_geometry.json` 的**重放姿势**（登记）

落盘产物的 windows 已带**派生填充**的 `floor`（F-16 修法的产物），
重新喂进 `parse_correction_draw` 会被新门 `producer_window_floor_populated` 拒。

**当前可用姿势**（本次复现用的）：解析前逐窗 `payload["windows"][i].pop("floor")`。
15/15 个窗都需要剥。这与施工席在 5 处既有测试里 `pop("floor")` 是同一个原因。

⇒ **建议随 F-17 修法一并给出官方重放入口**（如 `--replay-correction-from` 或一个
`strip_derived_fields()` 帮手），否则每次调试都要手写这段。

---

## 8. 未证实 / 未覆盖（如实登记）

- **多层的行为未单独验证**：F1/F2 两层现象一致（F2 的 `RM2F_01/02/03/06` 同样出斜边），
  但未构造「两层 footprint 不同」的场景 —— 现契约要求 per-floor footprint 相同，故暂不适用。
- **L 形 / U 形 + 跨轴组件**未实测。本 case 是矩形；L/U 形状下 materialize 会真的插点，
  与跨轴耦合叠加后的行为**未知**，修法验收应补一格。
- **历史成绩不受影响**（已核）：07-02 / 08-07 等跑通记录用的都是 legacy 或 v1/v2 形态，
  走的是 `_apply_legacy_envelope_reconcile`，与本条无关。

---

## 附：复跑

```bash
python AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/tools/f17_repro.py
python AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/tools/f17_stepwise.py
python AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/tools/f17_matrix.py
```

全部只读、零 LLM 成本；输入 = `case_tests/e2e_tests/sm21_anchor/run_2026-08-08_f16_e2e_verify/`。
