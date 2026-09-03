# B4 洞口合成（跨视图身份配对）· 执行档

- **日期**：2026-09-03（第三程）· **施工方**：GLM 家族施工席
- **任务书**：[`2026-09-03ag`](../request/2026-09-03ag_B4_opening_synthesis_dispatch.md)
- **权威口径**：[B4 实测方案](../../experiments/2026-09-02b_b4_cross_view_identity/README.md)（主控探针，零参数方案）
- **工作目录**：`/tmp/b4_glm` · **分支**：`wt/09.03ag_b4` · **基点**：`afa467e` → **本轮终态**：`85fb915`（+ 全量/执行档收尾提交）
- **新增**：`src/agent/correction/opening_synthesis.py`（687 行）+ `tests/test_b4_opening_synthesis.py`（20 项锁）。**未改任何既有文件。**

**开工自证**（任务书「开工自检」，原文输出）：

```text
$ cd /tmp/b4_glm && pwd && git log --oneline -1 && git status --porcelain
/tmp/b4_glm
afa467e 09.03ag_dispatch_B4_opening_synthesis
（空）
$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)"
/tmp/b4_glm/src/agent/correction/evidence_contract.py
```

**分段提交**：本轮一个工作 commit（模块+锁同体、变异实测后才提交）`85fb915`；
执行档随收尾提交。

---

## §五 A-③ 自查：主控闭合表**独立复现**（⛔ 没有因为是主控量的就信）

```text
$ python - <<'PY'
import json
d=json.load(open("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json"))
UPM=d["units_per_metre"]
from shapely.geometry import Polygon
v=d["views"][0]
ext=[r for r in v["footprint"]["rings"] if r["kind"]=="exterior"][0]
print("外皮 bbox:", [round(c/UPM,3) for c in Polygon(ext["points"]).bounds])
for f in ["east","north","south","west"]:
    e=json.load(open(f"AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_{f}_as_drawn.json"))
    print(e["facade_label"], "链总长 m =", e["calibration"]["x"]["cum_mm"][-1]/1000,
          "| world_zero_source =", e["calibration"]["world_zero_source"])
PY
外皮 bbox: [0.0, 0.0, 25.0, 20.0]
East 链总长 m = 20.0 | world_zero_source = chain_fit
North 链总长 m = 25.0 | world_zero_source = chain_fit
South 链总长 m = 25.0 | world_zero_source = chain_fit
West 链总长 m = 20.0 | world_zero_source = chain_fit
```

⇒ **闭合表在本树逐位成立**（与主控读数一致）⇒ A-③ **不触发**。派生侧读数
（中轴 24.760/19.760 + 两侧各 0.120）见 §四 #1 的锁
（`test_gate_passes_bit_exact_on_the_real_four_facades`：派生外皮 ==
事实层 exterior ring bbox == 链总长，三位一体逐位断言）。

---

## §四 逐条验收

### #1 T2 是等式不是阈值

**实现形态**：全部比较搬进**0.1 mm 网格整数域**（`DECLARED_GRID_UNITS_PER_M
= 10_000`，gt-revision-ledger 签字口径「坐标 0.1 mm 整数」）。`grid_units()`
的入网检查是 **round-trip 浮点相等**（`u / 10_000 == value_m`，⛔ 无 epsilon），
离网格值即 `VALUE_OFF_DECLARED_GRID` 响亮；等式门 `chain_u != span_u` 是
**整数 `!=`**。代码内**不存在任何容差常数**——由 AST 锁机械强制：
`test_module_compares_no_float_literals` 遍历模块 AST，任何「float 字面量
参与 Compare」即 fail（`abs(a-b) < 0.001` 形状正中枪口）。

**0.1 mm 已红的读数**（`test_gate_is_zero_threshold_one_grid_unit_already_fails`）：

```text
$ python -m pytest tests/test_b4_opening_synthesis.py -q -p no:cacheprovider -n 6
20 passed in 2.78s
（锁内：chain 25_000.0 - 0.1 mm ⇒ ELEVATION_CHAIN_SPAN_MISMATCH，
 difference_grid_units == -1）
```

**变异实测**（备份-变异-跑-还原；M1 = 等式门失牙 `if False and chain_u != span_u`）：

```text
=== M1: neuter 等式门（不等也放行）===
4 failed, 16 passed in 2.80s
```

4 红含 `test_gate_is_zero_threshold…`、`test_one_bay_elevation_fails_naming_the_premise`、
`test_retirement_requires_the_gate_to_have_passed`、`test_gate_passes_bit_exact…`。
任何 ≥0.1 mm 的容差实现都无法让 M1 下的这四把锁同时绿。

### #2 外皮跨度逐边取该边自己那堵墙的厚度

**实现**（`_skin_envelope`）：沿轴跨度由「midline 在该轴上的墙」决定（⚠️ 轴
词汇转置：East/West 跨 y ⇒ 由跑 x 的墙的 `pos_m` 决定，docstring 明写并引
`projection_bridge._run_axis` 的教训）；**每端**取「把 midline bbox 顶到该端
极值的那组墙」的**它们自己的** half-thickness（多墙且厚度不一致 ⇒
`SKIN_END_WALL_THICKNESS_AMBIGUOUS` 响亮）；另加一道**算术前提检查**：端墙
推算的外皮必须等于全墙集外皮包络，否则 `SKIN_NOT_FROM_END_WALLS`
（「外皮 = 中轴 + 两侧各 t/2」这个叙述本身成为受检前提，⛔ 不默认成立）。
**无 `+0.240`、无 `+2*half_t` 全局量。**

**四边不同厚夹具**（0.37 / 0.30 / 0.24 / 0.20，⛔ 不是 240）：`test_each_edge_
takes_its_own_wall_thickness` —— South 链 25.000 = 24.665 + 0.185(西) +
0.150(东) 关门，East 链 20.000 = 19.660 + 0.120(南) + 0.100(北) 关门；
且两个**全局偏移变体**（`mid + 2×185`、`mid + 2×150`）被同夹具证伪为必红。

**变异实测**（M2 = hi 端改用 lo 端墙的厚度，即「一个全局 half」）：

```text
=== M2: 全局偏移（两端都用 lo 端墙的厚度）===
FAILED tests/test_b4_opening_synthesis.py::test_each_edge_takes_its_own_wall_thickness
1 failed, 19 passed in 2.78s
```

### #3 配对无启发式

**实现**：两侧先各自按**世界区间**（0.1 mm 网格整数）分桶，再逐桶对账——
桶内两侧各恰 1 个 ⇒ 唯一配对；否则（一侧空 = 无对 / 任一侧 >1 = 1:1 不可判定）
**整桶拒配、具名**（`unmatched_*` + `same_interval_groups`）。⛔ 无最近距离、
无顺序兜底、无容差内即配；同 id 重复（全体唯一性，⛔ 非桶内）与离网格值响亮。

**grep 自查**（任务书原文要求，输出原文）：

```text
$ grep -n -i "nearest\|closest\|proximity\|nearest_tick\|threshold\|tolerance\|epsilon\|按顺序\|最近" src/agent/correction/opening_synthesis.py
（30/31/37/38/61/68/112/135/140/144/182/188/295/584 行——全部位于 docstring/注释
 的「⛔ 不许」叙述里，生产逻辑零命中）
$ grep -n "sorted(.*)\[" src/agent/correction/opening_synthesis.py
（无输出，exit 1 —— 「排序后按下标取」形态零命中）
```

`sorted()` 仅用于错误上下文显示、产物确定性输出、桶遍历顺序（每桶独立处理、
无跨桶状态，遍历顺序不影响结果）。

**区间对不上 ⇒ 拒绝的读数**：`test_one_grid_unit_off_is_refused_not_nearest_
matched`（差 1 个网格单位 ⇒ `pairings == ()`，两侧各进 unmatched）；
`test_two_plan_openings_near_one_elevation_opening_pair_only_the_equal`
（一个相等 + 一个差 1u ⇒ 只配相等的，差 1u 的被拒——最近邻会被这条抓住）；
`test_same_interval_stack_is_refused_as_a_named_group`（同区间栈 ⇒ 整组拒配具名，
⛔ 不按顺序挑）。

**变异实测**（M3b = 无对时顺序兜底「配第一个键」）：

```text
=== M3b: 顺序兜底配对（无对时配第一个键）===
FAILED tests/test_b4_opening_synthesis.py::test_one_grid_unit_off_is_refused_not_nearest_matched
FAILED tests/test_b4_opening_synthesis.py::test_gate_passes_bit_exact_on_the_real_four_facades
2 failed, 18 passed in 2.77s
```

### #4 债的接线是结构不是字样

**实现**（T4-b）：`DEBT_REDEMPTION_REGISTRY` 的键 = **debt_id 的类型前缀**
（`debt_elevation_chain_span_unchecked_`，B3 生产者 mint 进 id 的结构身份，
受 bundle `content_sha256` 覆盖），⛔⛔ `description` 从不被读。注册表自带
两道 import 期牙：值必须是本模块真实 callable（`DEBT_REGISTRY_HANDLER_MISSING`）；
键之间互为前缀即歧义（`DEBT_REGISTRY_PREFIX_AMBIGUOUS`；债侧对应
`DEBT_TYPE_AMBIGUOUS`）。

**验收原文的两半**：

- `test_debt_wiring_survives_removal_of_every_b4_word`：description **完全不含
  "B4"** 的 span 债 ⇒ 照常接线 + 销账（复核方 `OWNER_TEXT_REMOVED=GREEN` 缺陷的反面）；
  并在**真字节**上复刻：`test_b3s_real_span_debt_is_redeemed_on_real_bytes` 用
  B3 真适配器跑真 East 字节 mint 出真债、把 description 改写成无 "B4" 文本 ⇒
  仍被认出并销账。
- `test_description_full_of_b4_wires_nothing`：description 满篇 "Owner: B4."
  但 debt_id 前缀未注册 ⇒ **零接线**（字样路径反方向也锁死）。

**变异实测**（M4 = 接线判据加回 `"B4" in description`）：

```text
=== M4: 接线改成 description 匹配 ===
FAILED tests/test_b4_opening_synthesis.py::test_description_full_of_b4_wires_nothing
1 failed, 19 passed in 2.70s
```

### #5 债被兑现后销账

**实现**（T4-c）：`synthesize_openings` 在**等式门通过之后**才调
`redeemable_debt_ids`，销账随产物走 `retired_debt_ids`（per product、per
facade——不是「该类型全局已清」的断言）；门失败 ⇒ raise ⇒ 无产物 ⇒ 债
原样挂着（义务仍开着，与 B3 交来时一字不差）。

**读数**：真字节端到端（见 #4）`retired_debt_ids == ("debt_elevation_chain_span_
unchecked_input_east",)`；`test_retirement_requires_the_gate_to_have_passed`
锁「门失败时销账不发生、债可再喂」。

**变异实测**（M5 = `retired = ()` 永不销账）：

```text
=== M5: 销账变异（永远不销账）===
FAILED tests/test_b4_opening_synthesis.py::test_b3s_real_span_debt_is_redeemed_on_real_bytes
2 failed, 18 passed in 2.79s
（另一红 = test_debt_wiring_survives_removal_of_every_b4_word）
```

### #6 前提有名字且不成立时响亮

**实现**（T5）：前提引用 B3 定义的**单一源**
`ELEVATION_CHAIN_SPANS_WHOLE_BUILDING`（`evidence_adapters.py`，⛔ 未复制第二份），
健康产物的 `premise` 字段具名携带；等式门失败时错误 context 带
`premise` + **两侧读数**（`chain_total_mm` / `skin_span_mm` / 差值）——
不带两侧读数的失配报告是在邀请下游用容差「修」它。

**「只画一跨」读数**（`test_one_bay_elevation_fails_naming_the_premise`）：
链 12_500.0（半跨）⇒ `ELEVATION_CHAIN_SPAN_MISMATCH`，context
`premise == ELEVATION_CHAIN_SPANS_WHOLE_BUILDING`、`chain_total_mm == 12500.0`、
`skin_span_mm == 25000.0`。⛔ 不静默按整栋处理（M1 变异下此锁红）。

### #7 全量绿（`-n 6`）· 逐位闭合

（见文末「全量读数」——跑毕补入。）

---

## ⚠️ §五 A-② 停报：T4-a 的 schema 方案（⛔ 本单未改 schema，未动 `EvidenceDebtV1`）

**现状**：`EvidenceDebtV1` 无 owner/义务字段，「归 B4」只落在自由文本
`description`。复核方原话：「owner/义务类型的 schema 升级会影响所有已有债，
不应由适配器单方发明」——本席照办：**未改 schema 一个字节**，T4-b/c 以
debt_id 类型前缀注册表交付（上文 #4/#5）。

**方案（供派工方拍板，⛔ 本席不执行）**：

| 案 | 内容 | 强弱 | 代价 |
|---|---|---|---|
| **A（建议）** | `EvidenceDebtV1` 加 `obligation: str \| None = None`（或 Literal 枚举，`None`=无下游义务）；生产者 mint 债时必填；B4 注册表键从 id 前缀换成该字段 | 最强：类型身份升为一等字段，validator 可校验「有 obligation 的债必须能被某个注册处理器解析」 | **改所有既有债**：债在 bundle `content_sha256` 覆盖面内 ⇒ 带债产物的哈希全变（B3 执行档已核：仓库无 golden bundle 哈希，同字节双跑一致性锁两侧同变仍绿——但主控须重核已落库/已签字产物面）；`evidence_adapters`/`evidence_contract` validator/`opening_synthesis` 注册表三处同步，跨 B3/B4/validator ⇒ **应由主控出独立单** |
| B | 加 `owner: str \| None`（自由字符串） | 弱：owner 又是字样，复核方指出的缺陷换了个字段复刻 | 同 A 的哈希面 |
| C | 不改 schema，把「debt_id 前缀命名空间」升为正式契约（注册表 + validator 校验注册前缀可解析） | 本单已实现形态的正式化；仍欠「谁能 mint 哪个前缀」的强制 | 零哈希影响 |

**停报结论**：等派工方拍板。拍板前 B4 的接线 = 案 C 形态（debt_id 类型前缀 +
注册表 + 防歧义牙），验收 #4/#5 已在此形态下全绿。

---

## B 层记录（不停，记四条）

1. **T1「外皮沿轴起点」的「起点」与已签朝向表的关系**：实测（本档自查 +
   四立面洞口对账数据）West/North 立面的链 `x=0` 对应沿轴**最大**端——
   即观察者面对立面的左手惯例，仓里 `facade_convention.FACADE_BASE_SIGN`
   （North/West = -1）已签字且带 Convention-truth 锁。本单的锚按该表实现
   （`origin = skin_lo if sign > 0 else skin_hi`），⛔ 未发明新前提。若派工方
   「起点」本意是「恒轴最小端」，则与 West/North 的配对实测冲突（镜像后才对得上）。
2. **T3「区间相等」在真实数据上的读数**：立面 `x_range_m` 是像素标定外推
   （真实四立面 mm_per_px ≈ 13.6 mm/px），平面是 0.1 mm 网格 ⇒ 真实四立面
   配对 = **0 对、全部进 unmatched**（两侧差 1–3 个网格单位）。这是 reading
   侧精度现状的**读数**，不是配对判据的缺陷；判据按验收 #3 零容差「拒绝不猜」。
   锁只锁完备性（配对+拒绝 == 全部，双侧），⛔ 不锁「必须 0 对」——钉住缺陷
   本身的存在是反模式（reading 精度提升后那把锁会假红）。
3. **跨层同位窗形状**：平面两层同位洞口（如 15B2 的 F1/F2）与立面上下层同位窗
   （East O04/O05，x 完全同、z 不同）共享同一世界区间 ⇒ 1:1 不可判定 ⇒ 整区间
   拒配 + `same_interval_groups` 具名。层身份是 B2 的维度；B2 落地后配对键可升
   `(floor_ref, interval)`。B4 核心显式不做层装配（⛔ §三）。
4. **阶梯体量的可见性归调用方**：sm25 East 立面 y≈6.7–15.3 段的洞口实际位于
   x=14.76 墙带（非外皮墙带 x=24.88）——「该朝向的候选洞口」筛选 = 可见性
   问题，归 `facade_visibility` / 调用方，⛔ 不在 B4 核心里用 bbox 极值捷径
   （会把阶梯体量的洞口静默漏掉——实测 East 13 个立面洞口里 12 个在非外皮
   墙带上）。B5 接线时必须用可见段筛平面侧输入。
5. **方向前提的产物记录缺位**（次弱，见下）：`mirrored` / `local_x_positive`
   由调用方声明、fail-closed；sm25 四立面按 `(False, "image_left_to_right")`
   声明且被配对数据证实。但「CAD 导出未镜像」本身是前提，产物里只有 sign
   读数、没有它的声明记录；若来一张镜像图而调用方声明错 ⇒ 等式门不查方向
   （总长闭合与方向无关）⇒ 全量 unmatched（响亮但归因不直给）。

---

## 全量读数（§四 #7）

**环境自证与 pytest 同一条命令**（`m.__file__` 落本树；对 `85fb915` 的树，
输出原文）：

```text
$ python -c "import src.agent.correction.opening_synthesis as m; print('MODULE_FILE=', m.__file__)" \
  && python -m pytest -q -n 6 -p no:cacheprovider
MODULE_FILE= /tmp/b4_glm/src/agent/correction/opening_synthesis.py
3776 passed, 2 skipped, 13 xfailed, 211 warnings in 442.80s (0:07:22)
```

exit 0，有 summary 行（⇒ 非同机竞争假红）。

**逐位闭合**：

```text
3756  基线（主控 2026-09-03 合并树权威读数 = 3717+31+5+3）
+  20  本单新增（tests/test_b4_opening_synthesis.py：20 def / 20 collected，
        无参数化展开——`--collect-only -q` = 20 tests collected）
= 3776  ✓  skipped 2 + xfailed 13 与基线逐位相同
```

（本树全量为施工席读数；权威全量以主控合并树为准。）

---

## 我自己认为最薄弱的一处

**债注册表的键仍是 debt_id 前缀字符串——比 description 强得多（结构身份、
受 content_sha256 覆盖、类型由生产者 mint 进 id），但它仍是「命名空间约定」，
不是一等字段。** 具体的洞：**没有任何机制强制「谁能 mint 哪个前缀」**——
一个新生产者 mint 出 `debt_elevation_chain_span_unchecked_` 前缀但语义无关的
债，会被 B4 悄悄接走销账。防歧义牙只防「前缀互为前缀」，防不了「前缀被
冒用」。这正是 T4-a 要解决的（案 A 把义务类型升为字段后，validator 可以校验
「带 obligation 的债必须被注册处理器覆盖」），而 T4-a 按 §五 A-② 停报——
所以本单交付物里最接近「字样」的东西就是这个前缀约定，它的正式化等派工方
拍板。次弱一处 = B 层第 5 条（方向前提在产物里无声明记录）。
