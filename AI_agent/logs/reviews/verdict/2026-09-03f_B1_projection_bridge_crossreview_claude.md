# 跨家族复核裁决 · **B1：投影桥核心 + 接线**

- **日期**：2026-09-03 · **复核方**：**Claude 家族**（跨家族审 —— 施工方 = GLM 席）
- **被审 commit**：`6f43041`（合并），复核工作树冻结在 `35721ce`（在 6f43041 上仅多一份请求书 md）
- **请求书**：[2026-09-03f](../request/2026-09-03f_B1_projection_bridge_crossreview.md) ·
  **派工单**：[2026-09-02ad](../request/2026-09-02ad_B1_projection_bridge_core_dispatch.md) ·
  **权威口径**：[设计稿 v7](../../proposals/correction_projection_bridge.md) ·
  **交件**：[执行档](../execution/2026-09-02aj_B1_projection_bridge_execution.md)

---

## 裁决：**APPROVE-WITH-FINDINGS** · 阻断 **0** · 不阻断 **6**

**一句话**：桥核心的两条主力机构（轴向映射、端点延伸）咬得死，接线的纪律锁（不许把
provisional 当成品）经我独立变异实测**双向都能变红**；H-a 的「只是在异常旁边多写个文件」
**被证伪** —— success 路径下 `run_correction` 真的返回了 16 个 cell 的 `CorrectedGeometryV3`。
**没有一条阻断**。六条不阻断全部落在两类上：①**生产帧几何零对账**（施工方自报的最薄弱处，
派工单已把它划归 B5，属实、且我坐实了它的边界）②**几处判断锁太薄或缺锁**（含设计稿 §四明写的
一条硬规则**完全没锁**）。

---

## 〇、环境自证（与 pytest 同一条命令承重；`__file__` 落本树）

```
$ pwd && git log --oneline -1 && git status --porcelain
/tmp/b1_review_claude
35721ce 09.03f_B1_crossreview_request
（git status --porcelain 无输出 = 干净）

$ python -c "import src.agent.correction.projection_bridge as m; print(m.__file__)"
/tmp/b1_review_claude/src/agent/correction/projection_bridge.py
```

⭐ **变异实测收尾核对**（全部已 `git checkout --` 还原）：

```
$ git status --porcelain
（空）
```

⭐ **权威全量（合并树，`-n 6`，环境自证同条命令）**：

```
$ python -c "import src.agent.correction.projection_bridge as m; print('FILE',m.__file__)" \
    && python -m pytest tests/ -q -n 6 -p no:cacheprovider
FILE /tmp/b1_review_claude/src/agent/correction/projection_bridge.py
3708 passed, 2 skipped, 13 xfailed, 211 warnings in 590.81s (0:09:50)
```

⇒ **验收 #8（全量绿）独立复现，0 failed**。（施工方在自己树上报 3702；我这棵合并树 3708，
差额来自合并之上的其它已并工作，非本单，0 红即闭合。）

---

## 二、⛔⛔ 第一职责：独立变异实测（「谁写谁不批」缺的半边）

**方法**：每次改 1 处源码 → `import … ; print(m.__file__)` 断言落本树 **＋** 定向 B1 全集
（`acceptance + fixtures + production_loader + o22m7 + prime_failopen + b1_gt_reconciliation` =
基线 **70 passed**）在**同一条命令**里跑 → 记红 → `git checkout --` 还原。⛔ 全程未跑
`pip install -e .`、未 `git add -A`。

### 施工方 M1–M6 的独立重做（结论：主力机构确有牙，两把薄）

| 我的变异 | 摘掉的判断 | 我实测的红数 | 施工方自报 | 判 |
|---|---|---|---|---|
| M1 | `_run_axis` 改恒等（直抄常轴 = 回到 90° 转置） | **5 failed** | 5 | ✅ 复现 |
| M6 | `extend_endpoints` 内层 `for other in lines` → `for other in []`（关掉全部延伸） | **24 failed** | 23 | ✅ 复现（我集多 2 文件故 +1） |
| M5 | `close_collinear_gaps` 的 `zip(ordered, …)` → `zip((),())`（永不补线） | **1 failed** | 1 | ⚠️ 复现，**只此一把锁**（见 F-4） |
| M2 | 宿主唯一性整块 neuter（多主取第一个、不响亮） | **2 failed** | 2 | ⚠️ 复现，**两把都是合成锁**（见 F-5） |
| M3 | 见下方「接线纪律」两条 | 各 1 | 1 | ✅ 复现 |
| M4 | sink（`compilation_sink`）本轮由 M6/其它间接覆盖，未单独重测 | — | 1 | 采信自报 |

原始输出（节选，命令见 §〇 方法）：

```
M1: return "y" if constant_world_axis=="x" else "x"  →  return constant_world_axis
    5 failed, 65 passed in 5.87s
M6: for other in lines:  →  for other in []:
    24 failed, 46 passed in 6.13s
M5: for left, right in zip(ordered, ordered[1:]):  →  zip((), ())
    1 failed, 69 passed in 5.82s
M2: (len(owners)!=1 → False, owners or [None])
    2 failed, 68 passed in 5.62s
```

### ⭐ 接线纪律锁（H-a #2 的正面回答）：两个方向都独立变红

```
① pipeline.py:1201  if not outcome.success:  →  if False:   （非 success 也去投影 provisional）
   1 failed, 69 passed            ← test_switch_on_without_success_terminates… 红
② pipeline.py:1409  if not outcome.success:  →  if False:   （删掉 EvidenceChainTerminal 抛出）
   1 failed, 69 passed            ← 同一把锁红
```

⇒ **那把被改写的锁【守得住】「⛔ 不许把 provisional 当成品往下游送」** —— 我把「非 success
也落盘投影」与「非 success 不再响亮终止」两个方向分别摘掉，各变红一把。**纪律半边未被删空。**

### ⭐⭐ 另造【三个】施工方没试过的摘法（超过「至少两个」的要求）

| 新变异 | 摘掉的东西 | 实测 | 判 |
|---|---|---|---|
| **N1** | `pipeline.py:1241` 生产侧 `resolution_m=0.0` → `0.0218`（= 它拒用的 `m_per_px`）| ⛔ **70 passed（零红）** | **缺锁**，见 F-2 |
| **N2** | `projection_bridge.py:863` `"degraded" if dangling else "complete"` → 恒 `"complete"` | **2 failed** | ✅ 有牙（completion 诚实性有锁）|
| **N3** | 延伸外向限定 `and other.pos_m < lo` → `and other.pos_m != lo`（允许向内缩） | **1 failed** | ⚠️ 单锁（薄）|
| **N4** | `pipeline.py:1433` 消费侧哈希绑定校验 `!=` → `False and !=`（删掉设计稿 §四那道校验）| ⛔ **70 passed（零红）** | **缺锁**，见 F-3 |

原始输出：

```
N1: resolution_m=0.0  →  resolution_m=0.0218
    70 passed in 5.61s
N4: if envelope.source_resolved_sha256 != outcome.final_provisional_sha256:
      → if False and …:
    70 passed in 5.29s
N2: "degraded" if dangling else "complete"  →  "complete"
    2 failed, 68 passed in 5.38s
```

**N1/N4 各暴露一条【设计稿明写、代码写对、但没有任何锁】的判断** —— 见 F-2 / F-3。

---

## 三、⭐⭐⭐ 第一攻击面：生产链读数对不上夹具（16 vs 15 · 316.70 vs 279.26 · 16 vs 0）

**判定：这【不是桥的算法缺陷】，是「生产侧墙集表示 ≠ gt 事实层墙集」＋「all-KEEP 非真模型
决策」两者叠加，被桥如实透传；⭐ 但验收 #6/#7 的确【只在夹具世界成立】，生产帧几何零对账。**

### 我独立复算的生产帧读数（真 sm25 2f，all-KEEP，z 取 gt；经 `run_correction` success 路径）

```
RETURNED CorrectedGeometryV3  cells=16
envelope: completion=degraded  face_count=16  provenance=derived_from_walls
          resolution_m=0.0  n_dangling=16
outcome:  success=True  exit=success  hashbind=True
```

- **16 面 / 316.70 m² / 16 悬端**：`test_production_chain_on_real_sm25_2f_unrotated`
  （`production_loader.py:359-361`）把它们钉成 `assert face_count==16 / completion=="degraded" /
  len(dangling)==16` —— **这是【特性回归钉】（characterization pin），不是对 gt 的正确性判据**。
  测试自己的注释写明「16 faces vs the gt facts set」= 明知与 gt 不同还钉当前值。
- **`b1_gt_reconciliation.py` 的双向对账只在夹具世界跑**（验收 #6：`cut_lines_from_as_measured_view`，
  `units_per_metre=10000` 的 gt 事实层）；**生产链走的是另一个 loader**
  （`cut_lines_from_wall_compilation` + `opening_spans_from_artifact`），它的几何**从未与任何 gt 对过账**。
- **成因（采信并复核施工方 §八）**：生产侧 22 墙 / 87 opening 候选 vs gt facts F2 53 墙 / 30 opening
  —— as-drawn 把更多段并进多段墙，opening 候选里混着厘米级量化缺口；且 all-KEEP 是施工方的驱动、
  不是真模型跑出来的墙集。⇒ 桥只是**忠实剖分了喂给它的那份（更粗的）墙集**。

### ⚠️ 这是「门量得准、但载体被换掉」的形族（[[gate-measures-right-but-carrier-gets-swapped]]）

验收把**算法**在 gt-事实-形状的输入上验了（夹具 loader），但**真正会 e2e 跑的那条生产 loader
的几何输出，正确性零验证**。这不是桥算错——**它是派工单自己划的范围边界**（派工单 §五#6
明写「对账按任务书钉在夹具世界完成」、设计稿 §7.2 把生产帧端到端归 **B5**）。

⇒ **登记为 F-1（不阻断，但是收口硬前提）**：⛔ **`face_count==16` 不许被读成「验收 #6 在生产帧通过」**；
B1 之上开 B2/B5 前，「生产帧对 gt 双向对账」必须作为**具名 debt** 带过去，⛔ 不许含糊成「已对账」。

---

## 四、⭐⭐ 第二攻击面：生产侧 `resolution=0.0` 且拒用 `m_per_px` —— 站得住，但没锁

**判定：`0.0` 的选择【站得住】（保守、诚实、有 source 串声明），且它对「16 悬端里 13 个厘米级」
那批【根本不相干】；⭐ 但这个判断【完全没有锁】（N1 实测零红）。**

- **站得住的理由**：
  1. 设计稿 **N-3** 明写生产链是浮点米、无声明量化，⛔ 不许沿用夹具的 1 unit；而生产链**没有**
     任何米空间的粒度来源。`m_per_px`（≈0.0218 m）是**像素标定尺度、不是坐标分辨率声明** ——
     拿它当米空间容差是「拿代理量当成它代表的东西」（[[proxy-mistaken-for-the-thing]] /
     [[cross-representation-mutation-must-be-equivalent]]）。
  2. `0.0` = 精确比较，把 3 个 ulp 级悬端登记成假阳 debt ⇒ 产物 `degraded`。这是**保守且诚实**
     （宁可多报 debt，不静默吸掉真差异），不是静默出错。
  3. ⭐ **关键**：13 个厘米级悬端是**真几何差**（as-drawn 墙集 ≠ gt 墙集），**任何 resolution
     值都修不了它们**（我实测 N1 把生产配线换成 0.0218 后，`len(dangling)==16` 那把钉子仍然过 ——
     2.18 cm 容差没吸掉它们）。所以「0.0 vs m_per_px」之争**只影响那 3 个 ulp 级**，与厘米级无关。
     ⇒ 施工方「m_per_px 会吸掉厘米级真差异」的措辞方向对，但**真正的兜底只能是 B5 对账**。
- **缺陷（不阻断）→ F-2**：`pipeline.py:1241` 的 `resolution_m=0.0` 把它换成 `0.0218`，
  **B1 全集 70 条零红**。这个被设计稿点名、被跨家族审反复讨论的判断，**没有一把锁在守**。
  （生产 loader 测试用的是它**自己**在 `test:342` 硬编码的 `0.0`，与配线那处是两份独立声明，会漂。）

---

## 五、⭐⭐ 主控假说 H-a：接上了，还是异常旁边多写个文件？

**逐条判：**

### ① 保留 terminal + 落盘 envelope 满不满足验收 #7？—— **满足（在其应有的语义下）**

**H-a 的前提「接线之后 `run_correction` 仍然抛 `EvidenceChainTerminal`」被我独立证伪。**
我驱动真 sm25 2f 到 `outcome.success=True` 后（命令 = §三 那段）：

```
RETURNED CorrectedGeometryV3  cells=16    ← run_correction 真的【返回了几何】，没有抛异常
```

- **success 路径**：`run_correction(evidence_chain=True)` 返回 `envelope.geometry`
  （`CorrectedGeometryV3`，16 cell），envelope 落盘、`footprint_provenance="derived_from_walls"`、
  哈希绑定 outcome 最终 provisional。⇒ **桥是真被走到、真出几何的**，⛔ **不是「异常旁边多写个文件」**。
- **terminal 只在 non-success 时抛**（我 §二 的两条纪律锁证明它守着「非成功不出成品」）。
  主控观察到的「仍抛 terminal」只在 loop 没到 success 时成立（空响应 / 真模型出 findings/reject）——
  那正是**纪律在起作用**，不是缺陷。
- 验收 #7 = 「单视图产物走到 `CorrectedGeometryV3` 并过 gate①（单层）」：success 路径返回了
  `CorrectedGeometryV3`，gate① 夹具测试逐项 ok ⇒ **#7 达成**。
  ⚠️ 但要点名：**gate① 在新链上按构造恒真**（W3：footprint 自派生自己当分母 ⇒ hole/overlap 恒 0），
  所以 #7 的「过 gate①」在生产帧是**空过**——这一点设计稿已显式声明、`footprint_provenance`
  字段让它在产物里可读，属**已披露的已知形态**，非隐藏缺陷。

### ② 那把锁还守不守得住纪律？—— **守得住**（§二 M3 两方向各变红一把）

### ③ 缺的是什么？—— **envelope → 几何内核的端到端接线，本来就是 B5，已登记，非本单漏做**

我核实：`run_pipeline`（几何内核 2_modelling…→IDF 的入口）**完全没有** wire `evidence_chain`
（`grep evidence_chain` 在 `run_pipeline` 处零命中）。⇒ **桥的产物今天到 `run_correction` 的返回值为止**，
没有任何编排把它喂进内核。**但这正是设计稿 §7.2 批次表里的 B5**（前置 B1–B4），
派工单 §四也把「多层装配 B2」明确划出。⇒ **不是本单漏做，是下一批**，且已具名登记，⛔ 没有含糊过去。

---

## 六、其余逐条

| 请求书 §六 | 结论 | 证据 |
|---|---|---|
| **1a 无长度/厚度常数** | ✅ | 通读 `projection_bridge.py`：数值仅 `/2.0`（取半，从数据派生）、`1.0/units_per_metre`、`%03d`、朝向 `area2<0` —— **零长度/厚度字面量**；生产 loader 全取 `wall.resolved_thickness_m` 等自报值 |
| **1b 墙厚混排 90/150/300/370** | ✅ | `fixtures.py:48-55` 同一张图四厚度；`test_smix_thicknesses_are_the_mandated_mix` 断言 `sorted set == [90,150,300,370]`（⛔ 非 120/240）|
| **1c 正交假设局部化 + 有名字** | ✅ | `ORTHOGONAL_AXES` 一个常量 + `_validated_axis` 一个命名函数；`bridge.py:57-86` 注释写明「一处判定」|
| **2 验收 #3 没拿夹具 #3 验 ✅ 方向** | ✅ | `test_3a/3b/3c` 用 S-mix 合成图（`bottom_t` 增厚 / 一致重画 / 环带占据），夹具 #3（`smix_view(bottom_t=1500)` 报错厚度）只出现在 `test_fixture3_…goes_red_at_reconciliation`，**未进 ✅ 方向** |
| **3 验收 4b③「无主面即红」真落地 + 我造新形攻击** | ✅ | `b1_gt_reconciliation.py:147` `ownerless_faces = set(range(len(faces))) - used_faces`；**我另造攻击**（计数相等 3==3、第三个面瞬移到 (500,500)）⇒ 对账 `green=False`，② `['z2']` + ③ `[2]` 双红，而「①+②单向版」= 会绿 ⇒ ③ 确有牙 |
| **4 §9.1 共线缝选 ①（补线）落地** | ✅ 落地，⚠️ 单锁 | `close_collinear_gaps` 实现「**同一 origin_id（同一堵墙的多段）**内的缝补线」；跨墙缝**不补**（施工方注释：跨墙补会 15≠14 顶穿签字 gt）。M5 证明**只此一把锁**守它（见 F-4）|

---

## 七、不阻断清单（6 条）

- **F-1（B，最要紧）**：生产帧几何**零 gt 对账**，`face_count==16` 等是特性回归钉、非正确性判据；
  验收 #6/#7 只在夹具世界成立。⇒ 派工单已把生产帧对账划归 B5，属**范围内的合法延后**，
  但**收口时 ⛔ 不许宣称「生产帧已对账」**，须把它作为具名 debt 带进 B2/B5。
  （方法论：[[gate-measures-right-but-carrier-gets-swapped]]）
- **F-2（B）**：生产配线 `resolution_m=0.0`（`pipeline.py:1241`）**无锁**（N1：换 `0.0218` 零红）。
  判断本身站得住，但派工单 §三/设计稿 N-3 明写「生产链粒度来源要重新声明」——这个承重声明**没有测试守**。
  建议补一把「生产配线的 resolution 必须为 0.0 且 source 串声明浮点米」的锁（便宜）。
- **F-3（B）**：设计稿 §四硬规则「envelope 哈希对不上 ⇒ 投影失败」的**消费侧校验**
  （`pipeline.py:1433`）**无锁**（N4：删掉零红）。`test_switch_on_returns…` 只断言哈希**值相等**、
  没断言 run_correction **会在不等时 raise**。建议补一把「篡改 envelope 的 `source_resolved_sha256`
  ⇒ run_correction RuntimeError」的锁。
- **F-4（B）**：§9.1 共线缝补线**只此一把锁**（M5→1 红）；且「分隔两房间的共线缝**永远落在同一
  origin_id 内**」这个前提只被夹具 4 走到。若真实 reading 把一堵被门断开的分隔墙表示成**两个不同
  wall id**，跨墙缝不补 ⇒ 房间静默合并。⛔ 非本单缺陷（施工方按派工单 ① 选项 + 注释披露了此边界），
  但值得在 B2/reading 侧钉一条「分隔墙断口的 id 归属」查证项。
- **F-5（B）**：宿主唯一性（M2b→2 红，**两把都是合成锁，真产物 e2e 恰好全唯一主、测不到**，
  施工方 §八已自陈）与延伸外向限定（N3→1 红）单/薄锁。若后续认为承重，补锁便宜；当前非阻断。
- **F-6（B）**：设计稿 §四「strict profile 交 judge 前拒绝 degraded」这条硬规则，**在 B1 接线处未强制**
  —— `run_correction` success 路径**不看 profile** 就返回 degraded 几何。生产帧恰好 degraded（16 悬端），
  当前无门拦它往下走。可能归 judge/下游（B5），但应**显式登记**，⛔ 别默认「已由某处兜住」。

**A 层停报触发器逐条对照 = 零触发**：本单未动 §四禁令、未改任何已落库/已签字产物的哈希或基线
（`git diff` 仅 3 个 src 文件 + 5 个测试 + md；全量 3708 绿含所有逐字节复现锁未被扰动），
设计稿 §六之三/§四 各条我复核**均成立**（延伸=求交、尺子数据派生、terminal 语义、双向对账③）。

---

## 八、给收口方的话（白话）

投影桥这一单**可以过，但不是「B1 完成 = sm25 能出房间了」**。它做成的是：**给桥一份墙，桥能
确定性地切出互不重叠、并集成 footprint 的房间，并把「不许拿半成品冒充成品」这条纪律焊死在接线上**
—— 这两件我都独立摘了实现来验，锁真的会红。**但它今天只在「喂进来的墙是干净的 gt-形状」时被验过**；
真实生产那条路喂进来的墙更粗（22 堵 vs 53 堵），切出来 16 个面而签字答案是 15 个，**这 16 个面
从没跟标准答案核对过一次**——这一步施工方老实标了「未对账」，设计也把它排到了后面的 B5。

所以下一步**别在 B1 上直接宣布「端到端通了」**：真正的「切得对不对」要等 B5 把生产帧的房间跟
签字答案逐个位置对上，才算数。另外有两处设计写明要有、代码也写对了、但**忘了上锁**（生产侧的
容差取值、产物防篡改的哈希校验），建议顺手补上——很便宜，且防的正是「以后有人手滑改一行没人发现」。

---

*复核方：Claude 家族跨家族席 · 变异实测全部在冻结工作树 `35721ce` 完成并已还原（`git status` 空）。*
