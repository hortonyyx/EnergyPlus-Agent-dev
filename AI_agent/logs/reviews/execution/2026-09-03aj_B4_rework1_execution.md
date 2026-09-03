# B4 返工 1 · 执行档（GLM 施工席）

- **单**：[`2026-09-03aj_B4_rework1`](../request/2026-09-03aj_B4_rework1.md) · **裁决**：[`2026-09-03ah`](../verdict/2026-09-03ah_B4_crossreview_gpt.md)（REWORK / 阻断 2 / 不阻断 3）
- **工作目录**：`/tmp/b4_glm` · 分支 `wt/09.03ag_b4` · 施工前 HEAD = `4ea103d`
- **提交**：`5b1b0c4`（B-1）→ `b15ee62`（B-2），分段提交
- **改动的文件**：`src/agent/correction/opening_synthesis.py` · `tests/test_b4_opening_synthesis.py`，仅此两个
- ⛔ **未动**：`EvidenceDebtV1` schema（验收 #4 证据见 §四）· 本体四项（等式门/逐边厚度/区间配对/前提命名，一字未改）· B3 适配器 · 任何对齐/吸附/阈值（本轮零新增阈值）

> **提交内容说明**：第一笔提交（`5b1b0c4`）因主控预置并已暂存的返工单与裁决两份管理文件（`reviews/request/2026-09-03aj_*.md`、`reviews/verdict/2026-09-03ah_*.md`）随提交入库（git 已暂存项随 `git commit` 一起进入），内容一字未动；两笔代码提交本身只含上列两个代码文件。

---

## §一 · B-1：注册表 handler 承重（阻断 1）

**修法**（`5b1b0c4`）：注册表从「前缀 → handler 名字字符串」改为「前缀 → `DebtRedemption(premise, gate)` 行对象」，且

1. **执行侧经注册表**：`synthesize_openings` 删除对 `span_equality_gate` 的硬调用，改为 `redemption_row_for_premise(ELEVATION_CHAIN_SPANS_WHOLE_BUILDING)` 按**前提**查注册表行、调用行的 gate 对象——注册表成为执行接线的**单一来源**。行被删 ⇒ `PREMISE_GATE_UNWIRED` 响亮；两行同前提 ⇒ `PREMISE_GATE_AMBIGUOUS` 响亮。
2. **import 自检升级**（治「名字存在且 callable」）：gate 必须是**本模块具名函数**（`globals()[gate.__name__] is gate`，拦 lambda/内建/外部函数）；且签名必须能以执行侧的关键字形态绑定（`inspect.signature(gate).bind(chain_total_mm=…, skin_lo_u=…, skin_hi_u=…)`，拦签名不相干的现存 callable）。
3. **运行时兜底**（出口检）：运行时注册表被换（import 自检已过）⇒ 真实调用点炸 `TypeError` ⇒ 转译为具名 `DEBT_GATE_CALL_FAILED` 响亮失败 ⇒ 无产品 ⇒ 无销账。

**证据**（定向，`-n 6`）：

```
$ python -m pytest tests/test_b4_opening_synthesis.py -q -n 6 -p no:cacheprovider
....................                                                     [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. ...
20 passed in 2.83s
```

锁（`test_registry_rows_are_wiring_not_decoration`，重写）覆盖的变异，全部响亮：

| 变异 | 结果码 |
|---|---|
| 行的 gate 换成 **`grid_units`**（复核方原反例：现存、callable、签名语义都不相干） | import 自检 `DEBT_REGISTRY_GATE_SIGNATURE_MISMATCH`；运行时注入 `DEBT_GATE_CALL_FAILED`，无产品、无销账 |
| gate 换成 lambda | `DEBT_REGISTRY_GATE_NOT_MODULE_FUNCTION` |
| gate 为 `None` | `DEBT_REGISTRY_HANDLER_MISSING`（旧牙保留） |
| 两行同 premise | `DEBT_REGISTRY_PREMISE_AMBIGUOUS` |
| 整行删除 | `PREMISE_GATE_UNWIRED`（synthesize 响亮） |
| 两前缀互为前缀 | `DEBT_REGISTRY_PREFIX_AMBIGUOUS`（旧牙保留） |

**摘修法验牙**（文件级变异 → 备份/改/跑/还原）：

```
$ cp src/agent/correction/opening_synthesis.py /tmp/b4_glm_b1_backup.py && python - <<'EOF'
...（把 span_row.gate(...) 调用改回硬调用 span_equality_gate(...)，其余保留）
EOF
MUTATED: gate hard-called again (old B-1 defect shape)
$ python -m pytest tests/test_b4_opening_synthesis.py::test_registry_rows_are_wiring_not_decoration -q -n 0 -p no:cacheprovider
tests/test_b4_opening_synthesis.py:745: Failed
=========================== short test summary info ============================
FAILED tests/test_b4_opening_synthesis.py::test_registry_rows_are_wiring_not_decoration
1 failed in 0.84s
$ cp /tmp/b4_glm_b1_backup.py src/agent/correction/opening_synthesis.py && rm /tmp/b4_glm_b1_backup.py
（还原后定向 20 passed，见上）
```

⭐ **牙的方向正确**：变异精确还原了「gate 列不承重」的旧缺陷形状（注册表仍在、名字仍在，只是执行不再经它）⇒ 锁红。

## §二 · B-2：销账绑定本次核过的那一个源实例（阻断 2）

**修法**（`b15ee62`，按派工方签字：**用现有 `affected_refs`，零 schema 改动**）：

1. 新增 `ElevationSourceIdentity(input_id, source_contract_id, source_output_sha256)`——与 `ArtifactPointerV1` 同一身份词汇，减去源内指针；`synthesize_openings` 新增可选参数 `elevation_source`（调用方声明的本次立面源身份）。声明了非立面契约 ⇒ `ELEVATION_SOURCE_CONTRACT_MISMATCH` 响亮。
2. 新增 `ExecutedRedemption(prefix, row, source)`——本次运行**实际执行**的注册表行（对象身份）+ 所核源实例；`redeemable_debt_ids` 的 `executed` 改为**必填**（旧签名「只看前缀」正是缺陷形状，不再作为公开形态存在）。
3. 销账三重绑定，缺一不销：**类型**（前缀恰命中一行）+ **执行**（命中行 `is` 本次执行的行）+ **源**（债的 `affected_refs` 中存在一张 ref 三元组等于本次 `elevation_source`）。未声明源 ⇒ 一张不销（保守）；refs 为空 ⇒ 不可绑定 ⇒ 不销。

**常驻锁**（`test_retirement_binds_to_the_source_instance_real_bytes`，**B3 真实字节**，⛔ 非合成）：east/west/south 三份真实立面字节各自过 `adapt_as_drawn_elevation` 铸成三张**合法**债（各带指向自己源 `/calibration` 的 `affected_refs`），三张一起进一次 South 运行（声明 South 源身份）：

```
retired_debt_ids == (south 自己那张,)
east / west 两张 ∉ retired，且随后以 East 源身份跑 East 门时仍可正常赎回（未被消费）
不声明 elevation_source 的运行 ⇒ retired == ()
```

——复核方反例（`CURRENT_FACADE= South / RETIRED= ('…_input_east','…_input_west')`）逐字反转。

**摘修法验牙**：

```
$ cp src/agent/correction/opening_synthesis.py /tmp/b4_glm_b2_backup.py && python - <<'EOF'
...（把 redeemable_debt_ids 里 executed.source 绑定检查整段删除，回到纯前缀销账）
EOF
MUTATED: source binding removed (old B-2 defect shape: prefix-only retirement)
$ python -m pytest tests/test_b4_opening_synthesis.py::test_retirement_binds_to_the_source_instance_real_bytes -q -n 0 -p no:cacheprovider
tests/test_b4_opening_synthesis.py:994: AssertionError
=========================== short test summary info ============================
FAILED tests/test_b4_opening_synthesis.py::test_retirement_binds_to_the_source_instance_real_bytes
1 failed in 0.82s
$ cp /tmp/b4_glm_b2_backup.py src/agent/correction/opening_synthesis.py && rm /tmp/b4_glm_b2_backup.py
（还原后定向 22 passed，见下）
```

**B3 定向不受影响**（适配器零改动）：

```
$ python -m pytest tests/test_b3_elevation_leg.py -q -n 6 -p no:cacheprovider
34 passed in 3.07s
```

**修法后定向**（两段叠加，`-n 6`）：

```
$ python -m pytest tests/test_b4_opening_synthesis.py -q -n 6 -p no:cacheprovider
......................                                                   [100%]
22 passed in 2.65s
```

（20 → 22：`test_retirement_binds_to_the_source_instance_real_bytes` + `test_source_identity_declared_with_a_foreign_contract_is_loud`；既有 20 个里 5 个债类测试按新语义升级夹具——合成债从「无 refs」升级为「带指向本源的 refs」，规则断言不变。）

## §三 · 验收 #3：锁常驻且有牙

两把锁都进 `tests/test_b4_opening_synthesis.py`（常驻收集内，全量必跑）。摘修法实测见 §一/§二（各自红一次）。还原后：

```
$ git status --porcelain
（空）
```

## §四 · 验收 #4：schema 一个字节没动

```
$ git diff --exit-code afa467e..HEAD -- src/agent/correction/evidence_contract.py && echo "(empty = untouched)"
== schema diff afa467e..HEAD ==
(empty = untouched)
== schema diff 4ea103d..HEAD ==
(empty = untouched)
$ sha256sum src/agent/correction/evidence_contract.py
a5550ab6affb04e56b2788db2a0fc78a37e23541ca9c77de23979db5013319e2  src/agent/correction/evidence_contract.py
```

与裁决 P-4 记录的基点/终态 SHA-256 **完全一致**。

## §五 · 验收 #5：上一轮已过审五项不退化

五项的锁全部原样通过（本轮对 `span_equality_gate`/`_skin_envelope`/配对分桶/前提字段**零改动**，仅改了**谁调用**门）：

- 整数等式门：`test_gate_is_zero_threshold_one_grid_unit_already_fails` · `test_module_compares_no_float_literals`（AST 锁）· `test_gate_passes_bit_exact_on_the_real_four_facades` ✓
- 逐边厚度：`test_each_edge_takes_its_own_wall_thickness`（四边异厚夹具 + 全局偏移证伪）· `test_end_wall_thickness_disagreement_is_loud` · `test_wall_poking_past_the_end_wall_is_loud` ✓
- 区间配对无启发式：`test_one_grid_unit_off_is_refused_not_nearest_matched` · `test_same_interval_stack_is_refused_as_a_named_group` · `test_two_plan_openings_near_one_elevation_opening_pair_only_the_equal` 等 ✓
- 前提具名响亮：`test_one_bay_elevation_fails_naming_the_premise` · `test_healthy_product_carries_the_premise_by_name` ✓
- 双侧完备性：真实四立面 `paired + unmatched == 全部输入`（`test_gate_passes_bit_exact_on_the_real_four_facades` 内逐立面断言）✓

（定向 22/22 全绿即含以上全部。）

## §六 · 验收 #6：全量

环境自证与 pytest 同一条命令（单号 §五 原文）：

```
$ cd /tmp/b4_glm && \
python -c "import src.agent.correction.opening_synthesis as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
/tmp/b4_glm/src/agent/correction/opening_synthesis.py
3778 passed, 2 skipped, 13 xfailed, 211 warnings in 581.17s (0:09:41)
exit=0
```

（summary 行存在 ⇒ 非同机竞争假红；同机 Claude 席位做 B2 未产生干扰读数。）

## §七 · 我认为最薄弱的一处

**`elevation_source` 是调用方声明的信任边界，绑定链的根是「声明」不是「测量」。**
`elevation_doc` 是已解析的 dict，没有字节可重哈希，所以源身份（input_id + sha）无法被本模块机械重算——`ElevationSourceIdentity` 的 docstring 里已写明「a trust boundary the caller signs, ⛔ not a fact this module re-derives」。含义：若上游（未来的 B5 接线）手填身份而不是从 bundle 的 `SourceArtifactV1` 机械提取，一张「声明为 East、实际内容是 South」的运行仍会按 East 的身份销 East 的债。本单能做的（契约拒非立面 contract、真实字节锁、docstring 声明）都做了；**机械保证要等接线单**——接线时身份必须从 `artifact.bundle.source_artifacts[0]` 提取，⛔ 不许手拼。建议下一单（B5）把这条写进验收。

次弱（B 层，记不阻断）：签名兼容但语义错误的 gate（一个假想的 `(chain_total_mm, skin_lo_u, skin_hi_u) -> int` 恒等函数）会通过全部结构检查并真的驱动「兑现」——结构层无法分辨语义对错，那是注册表维护者的责任；现有防线（具名函数 + 签名绑定 + 真实调用）对复核方实测的 `grid_units` 反例已双响亮。

## 全量读数

| 项 | 数 |
|---|---|
| passed | **3778** |
| skipped / xfailed | 2 / 13（与基线一致） |
| exit | 0 |
| 逐位闭合 | `3756`（主控合并树基线）`+ 20`（上轮 B4 定向）`+ 2`（本轮新增锁：真实字节源绑定锁 + 外来契约响亮锁）`= 3778` |
| 耗时 | 581.17s（`-n 6`，同机有 B2 席位竞争） |

---

## 六条验收对表（§五 → 证据位置）

| # | 规则 | 判 | 证据 |
|---|---|---|---|
| 1 | 处理器那一栏真的承重 | ✅ | §一：`grid_units`（复核方原反例）import 自检与运行时**双响亮**，无产品无销账；§一验牙（硬调用形状 ⇒ 锁红） |
| 2 | 销账绑定本次核过的那个源实例 | ✅ | §二：B3 真实字节 east/west/south 三张合法债进 South 运行 ⇒ 只销 South 自己的，East/West 原样保留且后续可赎；§二验牙（纯前缀形状 ⇒ 锁红） |
| 3 | 两条都有常驻锁且有牙；恢复后 status 空 | ✅ | §一/§二（各自摘修法红一次）+ §三（还原后 `git status --porcelain` 空） |
| 4 | schema 一个字节没动 | ✅ | §四：两个基点 diff 均空，SHA-256 与裁决记录一致 |
| 5 | 上轮五项不退化 | ✅ | §五：五项锁原样绿，门本体零改动 |
| 6 | 全量绿 · 逐位闭合 | ✅ | §六/全量读数：`3778 = 3756 + 20 + 2`，exit 0 |

## 明确不做 · 核对

⛔ 重做本体（未动）· ⛔ 改 `EvidenceDebtV1` schema（未动，见 §四）· ⛔ 为「0 对」加对齐/吸附/阈值（本轮**零新增阈值**，`test_module_compares_no_float_literals` AST 锁照跑）· ⛔ 动 B3 适配器（未动，34 定向绿）· ⛔ 多层装配（未碰）· ⛔ `pip install -e .`（未跑）· ⛔ `git add -A`（两笔提交均逐路径 add）· ⛔ 顺手修别的红（无其他红）。
