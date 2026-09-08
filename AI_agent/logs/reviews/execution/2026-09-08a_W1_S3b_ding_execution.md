# 交件 · W-1 收尾：S3b + 丁 + S7（GLM 施工 / Claude 审）

> **施工 = GLM**（`glm-5.3`）· 工作树 `/tmp/w1_flow_glm`（分支 `wt/09.07h_w1_flow`，基点 `6225b420`）
> 派工单：[`reviews/request/2026-09-08a_W1_S3b_ding_dispatch.md`](../request/2026-09-08a_W1_S3b_ding_dispatch.md)
> 题面 = 裁决 [`verdict/2026-09-07x_T2_3_ladder_ruling.md`](../verdict/2026-09-07x_T2_3_ladder_ruling.md)（§一 = 丁 · §二 = S3b）
> ⚠️ **本轮含一条 B 类停报**（§四）：S3b 清掉 min-edge 墙后，真链在 **snap 换环 × B3 覆盖守恒门**
> 上撞出第二堵墙 ⇒ **S7 端到端被挡，等裁决**。全量部分照跑（读数见 §五）。

## 自检（§五）

```
$ git log --oneline -1        # 开工基点
6225b420 09.08b_sync: 并入裁决书 + 收尾派工单
$ PYTHONPATH=/tmp/w1_flow_glm uv run python -c "import src.agent.pipeline as m; print(m.__file__)"
/tmp/w1_flow_glm/src/agent/pipeline.py        ✅ 落在工作树
```

分段清单：S3b = `fb13f108` · 丁 = `81a7e239` · S7/交件 = 本 commit。

---

## 一 · S3b —— corner-only 降维从「例子」提到「那一类」（commit `fb13f108`）

**修法 = 生产者不变量**：降维不再是 `project_cut_lines` 的消费侧行为，而是
`partition_lines` 自己的出厂属性 —— **faces 与 footprint_ring 出厂即 corner-only**
（`_corner_only_ring` 兼任开环/CCW/退化守卫；守卫具名 `FOOTPRINT_RING_DEGENERATE` →
`RING_DEGENERATE_ALL_COLLINEAR`，因它现在也可能在 face 上触发；无任何测试/调用方引旧名）。
消费侧 `:892` 的第二次降维删除（幂等，见下），注释指向生产者。

**幂等性论证**（docstring 已写）：单趟充分 —— 角点的邻居被删不会使它变共线
（被删邻居落在其旧邻居连线 ±0 上 ⇒ 幸存对仍张角）；合成夹具 + 真产物均实测幂等。

**锁×5**（`tests/test_w1_s3b_partition_corner_only.py`）：
① 合成 T 形夹具钉生产者不变量（pre-fix 红：右 face 带 5 顶点/footprint 7 顶点）——
**变异自检实测**：把 `faces.append` neuter 回旧形态 ⇒ ①②两把生产者锁红、真产物锁不红
（分工正确：真产物锁测 helper，生产者锁测接线）；② envelope cells 逐字继承不变量；
③ 非边长过滤器锁（13mm 真 jog 角点保留、`1e-18` 近平角点也保留——零容差的确证）；
④⑤ 真链产物无损锁（曲线对称差 `length == 0.0` 零阈值 + 幂等 + min-edge 过阈）。

**真链读数**（`experiments/2026-09-08a_w1_s3b_probe`，两层 32 cell 全量，与裁决书逐位一致）：

| | 降维前 | 降维后 | 裁决书 |
|---|---|---|---|
| floor_1/2 最短 cell 边 | 1.62 / 0.55 cm | **111.93 / 194.13 cm** | ✅ 逐位同 |
| <5cm / <10cm | 16/16 · 16/16 | **0/16 · 0/16** | ✅ |
| cell 顶点数 | 69/39/23… · 65/49/15… | 8/6/4/4… · 6/4/4/4… | ✅ |
| footprint | 94/86 顶点（最短边 2.16/0.55 cm） | **8/8 角点（最短边 5.008/5.004 m）** | （裁决书未列） |

⚠️ 存储产物是 S3 **之前**的链产的（footprint 也未被旧 `:892` 处理过），probe 对两族环都过
生产 helper —— 即提升后生产者对同一输入会输出的字节。

**顺带改的既有锁（B 类报备，属性未松）**：`test_2_rooms_share_inner_walls_vertex_for_vertex`
的操作化从「共享段每个顶点 ∈ 双方顶点集」改为「落在双方边界折线上（`distance == 0.0`，仍零阈值）」。
corner-only 环下，共享墙端点可以是一方的**真角**、另一方的**共线中点**（邻居直穿 T 落点）——
几何共享逐点精确不变，离散化匹配从未是被钉的属性（09-02 交件的对照物是「整块哈希」）。
21–49 mm 家族的 jog 仍以真实距离红在这条锁上。

### ⭐ S3b 交付物：partition 派生环的**枚举对照表**

生产/测试全仓 grep（`partition_lines|PartitionOutcome|footprint_ring|_corner_only_ring|_cells_from_faces`）逐点核对：

| # | 消费点 | 环族 | S3b 前 | 现在 | 依据 |
|---|---|---|---|---|---|
| 1 | `project_cut_lines` → `_cells_from_faces(faces)` → `CellV3.polygon` | faces | ❌ **未降维（病本身）** | ✅ 生产者出厂已降 | 本次改动；真链读数 |
| 2 | `project_cut_lines` → footprint → `FloorV3.footprint.vertices` | footprint_ring | ✅ 消费侧降（S3 的「例子」） | ✅ 生产者出厂已降，消费侧调用删除（幂等） | 本次改动 |
| 3 | `project_cut_lines` → `footprint_x/y`（bbox） | 两族派生量 | bbox 不受降维影响 | 不变 | 降维无损（锁④⑤钉对称差==0） |
| 4 | `project_cut_lines` → `face_count = len(faces)` | faces 计数 | 不涉几何 | 不变（面数不变） | 读数 16/16 |
| 5 | 测试 `test_b1_projection_bridge_fixtures.py`（410–433 三次 `partition_lines` 对比 · 593–605 monkeypatch 复用 outcome 的环） | 两族 | 测试侧 | 行为不变（全绿） | 本轮全绿 |
| 6 | `multifloor.snap_footprints_to_reference` —— envelope 级消费 **footprint 环**，容差内把上层环**逐位换成**参考环 | footprint（envelope 级） | 不降维时 Hausdorff 已不依赖顶点数 | 降维后两层 8 角点（设计如此：Hausdorff 正是为了不依赖顶点数相等） | ⭐ **撞出停报**：换环后 #1 的 cells 与采纳环分属两张图纸 ⇒ 见 §四 |
| 7 | `multifloor.assemble_multifloor_geometry` → `_footprint_fingerprint` 共底面比对 | footprint（envelope 级） | — | 指纹要求**逐位相同** ⇒ #6 必须换环 | 停报的另一半 |
| 8 | `finalize`/`parse._ring_checks` → floor.footprint + 全部 cells 过 `validate_cell_polygon`（min_edge 0.10） | 两族（envelope 级） | footprint 红（4.33cm 共线细分） | **全过**（真链实测） | probe ② |
| 9 | `geometry_validator.check_coverage` —— cells 铺满 footprint（面积阈 0.05 m²，`coverage_area_tol_m2`） | 两族（**装配级**） | — | ⛔ **与 #6 互斥 ⇒ 停报** | probe ②：hole 0.450054 m² |
| 10 | gt 侧 `tarch_normalize/as_measured/answer_compiler` 里的 `footprint_ring` | **名字相同、家族不同**（gt 提取器，不消费本 partition） | — | 不属本次「那一类」 | grep 佐证：零 import 边 |

⭐ 表的外延说明（[[enumerate-the-class-not-the-example-found-six-more]] 的自警）：
行的边界由我划 —— **「partition 派生」按「`partition_lines` 输出的直接/经 envelope 传递的几何消费者」取**；
#6–#9 是枚举时新发现的 envelope 级/装配级消费者（正是它们撞出停报），不是原单子点名的两处。

---

## 二 · 丁 —— ladder 的 z 改从声明刻度取（commit `81a7e239`）

**单一改动点**：`_DerivedFloorLevel.z_floor_m / ceiling_height_m` 两个 property 从
`_byte_z`（墨的 `pos_m`）改走 `_declared_tick_m`（最近声明刻度 `calibration.z.cum_mm`）。
四面比对、每层链投影的 z（`pipeline.py:1524`）、装配盖章**全部消费这对 property** ⇒ 一处改、全链生效。
识别不动：claim 的 `z_m`/`z_ref` 仍忠实指向 `/structure_lines/{i}/pos_m` 字节，选线规则与穷尽门原样。

**唯一性【证明】**（`_declared_tick_m`）：
- 噪声界 = `calibration.z.mm_per_px × max|residual_px|`，**残差逐 tick 重算**（⛔ 不读自报
  `max_abs_residual_px`；自报值交叉核对，漂移 = 具名红 `FLOOR_TICK_RESIDUAL_SUMMARY_DRIFT`）—— BLK-1 同形，零发明常数。
- 门 = **次近刻度距离 > 噪声界**（裁决/派工单的字面定义：非唯一 ⇔ 次近 ≤ 界）⇒ 违反 = 具名
  `FLOOR_LINE_TICK_UNPROVEN`；缺声明 = 具名 `FLOOR_TICK_DECLARATION_MISSING`。
  ⛔ 无容差、⛔ 无静默回退墨值 —— 两个停报触发器都落成机器可判的具名拒绝。
- **证明在 `_mint_ladder` 急切执行**：property 是惰性的，只在读时触发 ⇒ 若只在 property 里证，
  一个不读 z 的消费者就跳过门（不可观测的门）。首次实测正是栽在这：两个新锁先 DID-NOT-RAISE，
  把证明搬进 minter 后才红 —— 「唯一 sanctioned minter gates first」的本意。

**四面严格对账（文本未动、零阈值）**：真产物逐面 `((0, 3.6), (3.6, 3.6))` **全等** ——
比的是声明整数（四面 3600/7200 同整数、闭合全 0）。余量复现裁决书：east 356× · north 102× ·
south 547× · west 118×（rung 级最小次近距离/界：356/101/547/118）。

**锁**（`tests/test_w1_flow_routing.py`）：
- S4 停报锁按裁决**翻转**：`test_real_products_do_disagree_strictly` →
  `test_real_products_now_agree_strictly_on_declared_ticks`（严格对账绿 + **四面墨残差仍是四个不同读数**——散布没消失，只是让位）。
- 变异锁：3600 旁插 ±1 mm 刻度（次近 1.0 mm < 界 2.808 mm）⇒ 具名拒 `FLOOR_LINE_TICK_UNPROVEN/second_nearest…`。
- 缺声明锁：`calibration.z` 残缺 ⇒ 具名拒（adapter 侧链闭合红或 ladder 侧 `FLOOR_TICK_DECLARATION_MISSING`）。

### ⚠️ 丁的一处读数发现（请主控过目，未停工）

按裁决公式实测，**south 顶 rung 的墨距最近刻度 6.5 mm > 它自己的界 1.462 mm**（其余四面全部 rung
墨残差 0.0–3.9 mm）。裁决与派工单的**唯一性证明只写了次近方向**（「次近刻度距离 ≤ 噪声界 ⇒ 停下报」），
最近方向的墨残差恰是裁决定性为「像素侧产物」的散布本体 —— 界描述的是尺寸见证的**拟合**残差，
rung 墨是另一族独立像素测量。我按裁决字面实现：**次近方向是门，最近方向降为非阻断读数**
（`ink_snap_residual_mm` / `ink_snap_residual_upper_mm` 双 property，四面读数互不相同、
在翻转锁里被钉为「必须仍是四个不同读数」）。若主控认为最近方向也要门（防「选错线被静默吸走 400 mm」
一类识别错误——但识别不归本裁决碰），界需要换族（例如跨面散布实测值），那要另拍。

---

## 三 · S7（部分）—— 全量 ✅ `0 failed`

```
$ cd /tmp/w1_flow_glm && PYTHONPATH=/tmp/w1_flow_glm uv run pytest -n 6 -q
4036 passed, 2 skipped, 13 xfailed, 211 warnings in 481.74s (0:08:01)
（开跑前 __file__ 自检 ✅ = /tmp/w1_flow_glm/src/agent/pipeline.py）
```

数目对账：主线基线 4009 + 上一轮 S1–S6 落库锁 20（S1×3+S2×4+S3×4+S4×9）+ 本轮净增 7
（S3b 锁×5 · 丁新锁×2，翻转锁净 0）= **4036** ✅；收集闭合 4036+2+13=4051。

## 四 ⛔ 停报（B 类）—— snap 换环 × B3 覆盖守恒门互斥，S7 端到端被挡

### 你以为是 X，实际是 Y

**X**（裁决书 §二的隐含前提）：「用同一个 helper 处理 cells ⇒ 两层 32 个 cell 全部清零，
余量 20 倍以上」+ 派工单「S3b（先做，它挡通路）」—— 读作 **cells 清零 ⇒ 通路开**。
裁决书量的是 **cell 最短边**，不是 gate①。

**Y**（真链 probe 产物、生产函数原序复驱，`experiments/2026-09-08a_w1_s3b_probe` ②）：
min-edge 全清后，gate① 红在 **`correction.coverage`（INVARIANT，阻断）**：

```
floor '2f': hole 0.450054 m² · outside 0.069450 m²  >  coverage_area_tol_m2 0.05
（floor 1f 全绿：0/0/0；另一条 evidence_debt_coverage FAIL 是 advisory 非阻断，
 probe 未接生产债接线的形态，S4 mock 链测试同款，非第二堵墙）
```

### 证据：这是一个**真实的 fork**，两边都是既有门

同一份真链产物（corner-only 后），**snap 前后各红一边**：

| 路径 | 结果 |
|---|---|
| **不 snap**（各层留自环）| `assemble` 具名红 `PER_FLOOR_FOOTPRINT_MISMATCH`（共底面指纹逐位比对，invariant #6）|
| **snap**（现生产行为：2f 环逐位换成 1f 环）| `gate① correction.coverage` INVARIANT 红（2f 的 cells 铺不满**采纳环**，0.45 m²）|

### 归因

两层图纸**各自独立标定**（T1 实测同一边两层世界坐标差 7–14 mm）。BLK-1 的 snap 设计
（用户 09-07 口径「吸附/分辨率残差机器直接修」）用声明派生的顶点距离容差（本例 20.6 mm）
判定「同一栋楼」，然后**逐位换环**让 assembly 的逐位指纹比对通过；设计注释明写
「Replacing the ring does NOT touch the floor's cells (the schema enforces no
cell-in-footprint containment)」—— **对 Pydantic schema 成立、对 gate① 的 B3 覆盖守恒门不成立**：
那道门用 shapely 量 cells 是否铺满 footprint（面积阈 0.05 m²）。两把尺子互不知晓：
snap 的界是**顶点距离**（mm），coverage 的界是**面积**（m²）；89 m 周长 × ~5 mm 平均错位
≈ 0.45 m² 洞，9× 超阈。legacy 腿不撞这堵墙（模型出一份几何、各层环天然相同）——
**这是新腿「每层独立测量」的结构性后果**，与 S3b 无关（S3b 只是清了上一堵墙让它可见，
[[seed-bypass-exposes-hidden-downstream-blocker]]）。

### 选项与代价（⛔ 不预设，等主控定）

| 选项 | 做法 | 代价/后果 |
|---|---|---|
| **甲 · 把采纳环吸进 cells** | snap 判「同楼」后，上层 cells 的**外边界**沿轴对应滑到参考环上（两层都是 8 角点、对应边同轴 ⇒ 逐边正交映射机械可造，S3b 后这前提恰好成立）；cells 恢复**精确**铺满采纳环 ⇒ coverage 零阈过 | 真几何变换（外圈 cell 边界滑动 ≤ snap 容差），要动 BLK-1 设计文本「does NOT touch cells」；⚠️ **墙语义问题**：外圈墙中线 = 各层自己的面线 ± 各层自己的半厚，两层墙厚声明可以不同 ⇒ 硬滑后「中线—面线—半厚」关系在本层内部失配，需要主控定「滑完的边界归谁解释」 |
| **乙 · 不换环，把指纹比对容差化** | assembly 的共底面比对复用 snap 的声明派生容差（顶点距离界） | 指纹从**逐位**变**容差**——assembly「bitwise-identical ⇒ exact」的设计意图让位；invariant #6「共底面盒子」语义从「同一环」松成「同环±容差」；下游任何依赖逐位相同的消费（fingerprint/渲染对齐）要逐一重问 |
| **丙 · 维持现状** | 不动 | **端到端结构性不可达**（每次真链必红 coverage）—— 裁决书排除 S3-丙的同一逻辑在此同样成立 |
| （丁？） | 我构造不出严格更优的第四条；若主控看到，请裁 | —— |

我的推荐（仅供参考）：**甲**最贴 09-07 用户口径「吸附/分辨率残差 = 机器直接修」，
且 S3b 之后其机械前提（角点对应）恰好成立；但**墙语义**半边超出我能自决的范围，需拍板。

### 停报期间的代码形态（零放松）

snap（`snap_footprints_to_reference` 语义 + 容差派生）与 coverage 门（`coverage_area_tol_m2`
+ 三守卫）**两侧均零改动**；两侧各有既有锁钉住：snap 语义/容差锁在
`test_b2_multifloor_assembly.py` 与 `test_w1_flow_routing.py`（S4 的 snap_ledger 锁），
coverage 门锁在 `test_b3_coverage_gate.py`。本轮丁/S3b 不触任何一侧。
裁决后按选项改对应侧并同步锁（如 S4 先例）。

### S7 端到端为什么停在这

端到端的 1_correction 新腿必经 `run_multifloor_correction` ⇒ snap ⇒ gate① coverage；
标准入口上跑只会得到上面这条 INVARIANT 红。**命令序列本身已备好**（§五），裁决落地后
首跑即验；本轮不起跑真模型链（省真模型预算；墙的根因是**输入驱动**的——两层图纸独立标定，
与模型轮次的非确定性无关——确定性复驱已给出 gate① 读数）。

## 五 · S7 端到端命令序列（裁决后照抄可跑；本轮停在 §四的墙前）

```bash
cd /tmp/w1_flow_glm

# 0) 环境自检：被测代码必须落在本树
PYTHONPATH=/tmp/w1_flow_glm uv run python -c "import src.agent.pipeline as m; print(m.__file__)"
#    预期 /tmp/w1_flow_glm/src/agent/pipeline.py

# 1) S7 输入已由主控抢救落库（f50646a9）：6 份 as_drawn 产物按 manifest 槽位就位
ls case_tests/e2e_tests/sm25-L_anchor/run_w1_s7_probe/0_reading/
#    实测内容：6 份 *_view.json + run_config.yaml。
#    ⚠️ 缺 _run/view_manifest.json —— flow 的 as_drawn 路由必读它（层序/槽位都从它来）；
#    裁决后起跑前需补（参照 run_t1_probe2/_run/view_manifest.json 的槽位表，
#    input_id/expected_output_id 与这 6 份文件对齐）。

# 2) run_config：judge 必须打开（⛔ 不停在 judge.mode=off —— 「首跑=跑通并且出分」）
#    staged 的 case_tests/e2e_tests/sm25-L_anchor/run_w1_s7_probe/run_config.yaml 里
#    judge.mode=off 是抢救时的权宜，S7 起跑前先改开（具体档位按 flow SOP）

# 3) 标准入口：从 0_reading 到出分，零现场手写脚本（flow SOP 单一入口）
PYTHONPATH=/tmp/w1_flow_glm uv run python scripts/tool_scripts/run_stage.py \
  <case> <run> --judge stop --to intakeoutput   # 以 new_case_guide 的 flow 序列为准

# 4) 判分/报告自动产物：render/grade/score_vs_gt/attempts 由 flow 自动生成
# 5) report：flow --record 出 REPORT.md
```

⚠️ 诚实说明：第 3–5 步的具体参数我没跑过（被 §四 的墙挡在 1_correction gate①）；
上面是按 `guides/new_case_guide.md` 的标准链写的**序列骨架**，不是实测命令记录。
裁决后补实测逐字版。**全量**（§三）不受墙影响，本轮照跑。

## 最薄弱的一处

**枚举对照表 #6–#9 的「外延是我自己划的」**：我按「`partition_lines` 输出的直接/经 envelope
传递的几何消费者」划类，止步于 correction 侧（snap/assemble/finalize/coverage）。但
**2_modelling/3_split_pairing/5_intakeoutput 对 `CorrectedGeometryV3` 的 cells/footprint 还有一整段
下游消费**（interzone 配对、surface_specs 序列化、装配）——它们消费的是**同一批多边形**，
只是隔了 1_correction 的出口。我没枚举那一段：S3b 的降维对它们是「多边形顶点变少」
（无损、理论上无感），但「理论上无感」和「实测无感」之间隔着的，正是我在 S3 上栽过的那类
「读码推断代替产物实测」。若下游有任何按顶点数/顶点序做配对或指纹的逻辑，第一脚就会踩到。
（缓解：全量 4009+ 把锁里下游那段的锁本轮全绿 ⇒ 既有锁覆盖的行为面没变；没锁的行为面我不知道。）
