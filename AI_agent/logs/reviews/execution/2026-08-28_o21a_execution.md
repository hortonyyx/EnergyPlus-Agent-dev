# 施工记录 · ②-1a 事实层 `as_measured` 落库

- **日期**：2026-08-28 · **施工**：Claude 执行档 · **派工单**：[`request/2026-08-28_o21a_as_measured_facts_layer.md`](../request/2026-08-28_o21a_as_measured_facts_layer.md)
- **是否触发「停下上报」**：**否**（有一条 §五.4 命中，判为「可在 P1 内如实记录、不需扩路」⇒ 记账继续，见 §六.1；请派工方**复核这个判断**）

---

## 〇、开工自检五条（实测原文）

```
$ git rev-parse --abbrev-ref HEAD && git log --oneline -1
08.23_AsDrawnReading
c17af4a 08.28j_O21aDispatch_BaselineRebasedOnClosedUnit1

$ git status --porcelain
(空)

$ ls AI_agent/logs/reviews/request/2026-08-28_o21a_as_measured_facts_layer.md
-rw-r--r-- 1 root root 9806 Aug 28 14:33 .../2026-08-28_o21a_as_measured_facts_layer.md

$ grep -c "gt 铁律" AI_agent/CLAUDE.md
2
```

⚠️ **外围数值不符（记一行，不停）**：派工单 §抬头写 **基线 `8a5457a`**，实测 HEAD = **`c17af4a`**
（`08.28j_O21aDispatch_BaselineRebasedOnClosedUnit1`）。提示词明确指定 `c17af4a`，且基线读数一致，故按 `c17af4a` 施工。

**基线全量**（改动前，⛔ 无 `-m`、⛔ 非 `-n auto`）：

```
========== 3208 passed, 13 xfailed, 212 warnings in 940.76s (0:15:40) ==========
```

---

## 一、R1 · as-received 的转换请求书（⛔ 一个哈希都没改）

### 选了哪条路，为什么

取 **甲**（新增一份 request），⛔ 但把甲那条路的代价**用结构堵死**，不是靠纪律：

> **`request_as_measured.json` 不是被维护的，是被【算出来】的。**
> [`derive_as_measured_request()`](../../../../src/agent/judge/as_measured.py) 从签字件 `request.json` 机械派生，
> 测试 `test_r1_the_as_measured_request_is_recomputed_not_authored` **逐字节**比对仓库里的那份与现算的那份。
> ⇒ 两份 request 想漂开，得**两边同时被改**，否则测试红。这正是 F-130 那个形状的封堵。

⛔ **没选乙**（一份 request 声明两个源），理由是可测的不是偏好：`TarchConversionRequestV1` 的每个字段都进
`model_dump` ⇒ 进 `compute_request_sha256`。加两个键要么**打断三个签字哈希**，要么要再往
`REQUEST_VERSIONS_WITHOUT_SPACE_BINDING` 那种「签名故意不覆盖」的清单里加一条 ——
即**为了解一个另开一个文件就能解的问题，往信任根里塞一个没人签字的字段**。

### 允许漂的四个键（每个都因为「源文件不同」而不同）

```
source_dxf_label      sm25-L_t3.dxf      -> sm25-L_t3_as_received.dxf
source_dxf_sha256     1251f651…f8b9      -> 4a949224…3245
normalized_source_id  sm25-l-anchor-normalized -> sm25-l-anchor-normalized.as-received
request_sha256        d738d0ac…a135      -> ae272a73…6c5a
```

`git diff` 式对照（`diff request.json request_as_measured.json`）**只有这 4 行**，原文：

```
4,6c4,6
<   "source_dxf_label": "sm25-L_t3.dxf",
<   "source_dxf_sha256": "1251f65153829c9c4502e401b7962a22172e3b636732d4ddf91a40a7b049f8b9",
<   "normalized_source_id": "sm25-l-anchor-normalized",
---
>   "source_dxf_label": "sm25-L_t3_as_received.dxf",
>   "source_dxf_sha256": "4a94922489d391692da20a3b081511ab268d707fa7b61ae4413aae5268753245",
>   "normalized_source_id": "sm25-l-anchor-normalized.as-received",
1041c1041
<   "request_sha256": "d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135"
---
>   "request_sha256": "ae272a73f6331e3ac5787019053b3c973da04fcc53ba9bbe42aa10597be26c5a"
```

⭐ 顺带自证：仓库的 `request.json` 用同一个 formatter 重新 dump **逐字节还原**（25909 == 25909）
⇒ 这个「逐字节比对」比的是仓库自己的格式，不是我发明的格式。

⭐ 并且加了一把**证明新 request 在干活**的锁：拿**签字 request** 喂 as-received 图，
必须仍然 `AsMeasuredUnavailable[upstream_identity_block]` 且点名 `tarch_input_source_hash_mismatch`。
⇒ 哈希门一旦被放松，这条立刻红。

---

## 二、R2 · `AsMeasuredV1` schema + 从 P1（S0–S4）截取

新文件 [`src/agent/judge/as_measured.py`](../../../../src/agent/judge/as_measured.py)。

**存了什么**（逐视图）：`face_lines`（handle · layer · 轴向 · 常数位 · 沿墙区间）·
`walls`（两条面线的**引用** + 厚度 + 沿墙区间 + cap handles）· `openings`（位置 · 宽度 · **承载墙引用**）·
`footprint`（环，0.1 mm 整点）· `converter_readouts`（`dangles`/`cuts`/`invalid`/`diagnostics`/`gates` **原样搬**）。

**⛔ 明令不存的三样，实测已不在**（对**序列化后的文本**查，不是对类定义查）：
`"basis"` · `"boundary_condition"` · `"offset_m"` · `"outer_skin"` · `"zone_edges"` 全部 0 次。

**坐标一律 0.1 mm 整数**：唯一换算入口 `to_units(m) = int(round(m * 10000))`。
⚠️ 与「converter_readouts 原样搬」冲突已显式化：转换器自己的 `points_dxf_mm` 是 DXF 原生 mm 浮点，
**四舍五入它就等于重算它**。⇒ 口径定为「`converter_readouts` 是**唯一**允许出现浮点的子树」，
测试遍历整棵 JSON 树断言别处**一个浮点都没有**。

**⛔ 零 S7 依赖**：模块**不 import** `tarch_normalize` 里 S5–S7 的任何东西，只 import `run_p1_plan_view` 与 `P1PlanViewGeometry`。

**不静默丢**：`wall_lines` 里合法地存在既不水平也不垂直的笔画（as-received `plan-F1` 实测 1 条，handle `13AF`）。
它当不了「常数位面线」⇒ 进 `converter_readouts.non_orthogonal_lines` 逐条列名，
并由 model validator 强制台账恒等式：

```
wall_lines_total == len(face_lines) + len(non_orthogonal_lines) + degenerate_in_wall_lines
```

**拒绝口径 ⛔ 不新造**：直接复用 F-126b 跨家族审已通过的 **C-身份** 判据 ——
只在「有 `stage=S0_input` 的 BLOCK」或「零 wall_lines」时响亮拒绝。
⚠️ 而**内容级 BLOCK 必须放行**：as-received 图恰恰因为是原图才会报
`tarch_wall_nonorthogonal`(BLOCK/S1) 与 `tarch_wall_free_end`(BLOCK/S4)。
按「有 BLOCK 就拒」写，这层将**只能测量已经被修干净的图** —— 正是落库方案 §十 否掉的那个结果。

---

## 三、R3 · 逐位可复现门（⛔ 没设 `PYTHONHASHSEED`）

四个**具名的排序缝**（⛔ 不是内联 lambda），因为「反转输入没变化」这句话
**分不开「builder 排了序」与「builder 根本没读输入」**：
`_face_line_sort_key` · `_wall_sort_key` · `_opening_sort_key` · `_sorted_handles`。

`_sorted_handles` 是真正被种子攻击的那个：`all_wall_handles` / `consumed_wall_handles` 是 `set[str]`，
而 `str` 正是 Python 会按进程随机化哈希的类型。

---

## 四、派工单 §三 八条验收 · 逐条实测读数原文

### 1 ⭐ 签字哈希逐位不变

**改动前**（开工时）与**改动后**（本次施工完成后）两组，原文：

```
（施工后实测）
sm25 request   declared=d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135
               recomputed=d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135  match=True
sm24 request   declared=ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2
               recomputed=ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2  match=True
sm24 manifest  declared=c40cbc8bb566e4d8fc3999ad5ccb07bd27747b9f57f9ad30fe6691c7189bac21
```

⭐ **更强的证据**：`git status --porcelain` 全程只有**三个 `??` 新文件**，⛔ 签字文件**一个字节都没被写过**。
测试另外把**文件字节哈希**也钉住了（规范哈希看不见排版改动，文件哈希看得见）：

```
request.json (sm25)  e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df
request.json (sm24)  34b7d74959e8a8c644d7082d952fddcf9a16bb9407c620ad1dfa303cff1e23b9
manifest.json(sm24)  4daca5539e77fe11521b5f14b45acf7cff321f99c1139457b7f625784ec289bc
sm25-L_t3.dxf        1251f65153829c9c4502e401b7962a22172e3b636732d4ddf91a40a7b049f8b9
..._as_received.dxf  4a94922489d391692da20a3b081511ab268d707fa7b61ae4413aae5268753245
```

### 2 ⭐⭐ as-received 图真的跑通了 + 与签字件对照

**`as_measured` 侧读数**（面线数 / 墙数 / 洞口数）：

| 图 | 视图 | face_lines | walls | openings | wall_lines_total | 非正交 | S4 dangles | 失败的门 | BLOCK 码 |
|---|---|---|---|---|---|---|---|---|---|
| **as-received** | plan-F1 | **222** | **44** | **31** | 223 | **1** | **4** | **G1, G5** | `tarch_wall_free_end`, `tarch_wall_nonorthogonal` |
| **as-received** | plan-F2 | 222 | 39 | 30 | 222 | 0 | 0 | — | — |
| 签字件 | plan-F1 | 225 | 45 | 31 | 225 | 0 | 0 | — | — |
| 签字件 | plan-F2 | 222 | 39 | 30 | 222 | 0 | 0 | — | — |

**分母侧对照（F-129 点名的那组数）原文**：

```
SIGNED       plan-F1: targets= 110 opening_targets= 31 segments= 225 total_len_m=  282.28 faces_after_grouping=44
SIGNED       plan-F2: targets= 106 opening_targets= 30 segments= 222 total_len_m=  289.04 faces_after_grouping=44
AS-RECEIVED  plan-F1: targets= 108 opening_targets= 31 segments= 223 total_len_m=  275.00 faces_after_grouping=44
AS-RECEIVED  plan-F2: targets= 106 opening_targets= 30 segments= 222 total_len_m=  289.04 faces_after_grouping=44
```

✅ **与 F-129 逐数吻合**：F1 **110 → 108**（差 2 目标）· 长度 **282.28 → 275.00**（差 **7.28 m** = 3.64 m × 两面）·
**F2 两侧逐位相同**（106 / 30 / 222 / 289.04 / 44）⇒ 那 5 条手改线全在 1F。✅ 不触发「对不上 ⇒ 停下上报」。

三个 handle 也对上了：`13AD` `13AE` 在 S1 被判非正交**未收进** `wall_lines`；`13AF` 收进来了但是斜的，
本层逐条列出：`p0=[52401, 100659]` `p1=[52399, 99459]`（0.1 mm 世界坐标，x≈5.24 m ⇒ 与 F-129 的 `x∈[5.24, 8.88]` 一致）。

⚠️ **对 F-129 措辞的一处更正**：F-129 写「2 条在 `_collect_walls` 里就**静默**没收进来」——
实测它们**各发了一条 `tarch_wall_nonorthogonal` BLOCK 诊断**，⛔ 不是静默的。
静默的是**下游**（F-126 之前分母不透出诊断）。这更正不改 F-129 的结论，只改「谁在静默」。

### 3 ⭐⭐ 逐位可复现（⛔ 未设 `PYTHONHASHSEED`）

```
$ echo "PYTHONHASHSEED=${PYTHONHASHSEED:-<unset>}"     ->  <unset>

CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash=5513204894435921391  bytes=91165 sha256=bdf5938e70b0551629a3d43d17cd22e7414b840e8e21fec9508fbf6e124874ef
CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash=5370530356920914207  bytes=91165 sha256=bdf5938e70b0551629a3d43d17cd22e7414b840e8e21fec9508fbf6e124874ef
CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash=-3332607390474301052 bytes=91165 sha256=bdf5938e70b0551629a3d43d17cd22e7414b840e8e21fec9508fbf6e124874ef
```

⭐ **跑了三次不是两次**，且**每次自报 `str_hash`**：三个值互不相同 ⇒ 证明**随机化真的开着、种子真的不同**。
⛔ 只跑两次而不自证种子，「两次相同」可能只是随机化恰好关着（那门就是恒真的）。
⭐ 且每次自报 `CODE_FROM` ⇒ 不会像上一单复核方那样静默落回主树比自己（§六.1）。

### 4 ⭐ 反空转 —— 造改动实测变红（**三个内容方向 + 四个顺序缝**）

```
baseline                                   sha256=bdf5938e70b0551629a3d43d17cd22e7414b840e8e21fec9508fbf6e124874ef
mutating face line 1379 const 0 -> 1 (i.e. +0.1 mm)
after moving ONE face line by 0.1 mm       sha256=b304fee9cf7acb1a038d10eb22d195ffcc840231b600350d491aa0ccb835f8ec   CHANGED=True
after moving ONE converter readout         sha256=47c71ea8bd5c5c68e507dd340b5b9ceb86ccc5763e5fade98afb9e8005c0232d   CHANGED=True

reversed-input order-independence (NO neuter): identical=True
neuter _face_line_sort_key    -> reversed input now DIFFERS: True  (must be True)
neuter _wall_sort_key         -> reversed input now DIFFERS: True  (must be True)
neuter _opening_sort_key      -> reversed input now DIFFERS: True  (must be True)
neuter _sorted_handles        -> reversed input now DIFFERS: True  (must be True)
```

⭐ **四个缝逐个 neuter，⛔ 不是一个** —— 派工单 §六.2 那条：一个 neuter 只证明**四个里的某一个**在承重，
另外三个可以是死代码。四个都单独变红 ⇒ 四个方向各自有牙。

⚠️ 第一版 neuter 我写错了（在**两次调用里都**反转 ⇒ 两边一样、锁没红）。修法不是调断言，
是把排序键提成**具名可 patch 的对象**，neuter 成常数键（稳定排序 ⇒ 排序变成 no-op ⇒ 输出跟着输入顺序走）。

台账门与引用门也各自证明能红：
`test_r2_the_ledger_identity_has_teeth`（删一条面线 ⇒ `as_measured_wall_line_ledger_broken`）·
`test_r2_a_dangling_reference_is_refused` · R1 三个漂移门（改任一别的键 / 完全没换源 / 增删键）各自红。

### 5 ⭐ 零 S7 依赖 —— grep 原文

```
$ grep -n "ZoneEdgeReportV1\|ZoneExpansion\|s7_expand_zones\|run_p2_conversion\|extract_gt_v3\|ZoneEdge" \
        src/agent/judge/as_measured.py
（无输出）
grep exit=1  （1 = 零命中）
```

⚠️ 第一版这条**红了**，原因是我的**文档字符串里**为了解释「为什么不存它」而写了 `ZoneEdgeReportV1`。
按 [[grep-zero-hits-conflates-unused-with-nonexistent]] 我把它拆成**两半**：
（a）**文本 grep**（验收要的那条，也能抓 `getattr` 式字符串引用）·
（b）**AST 引用检查**（走 `ast.Name`/`ast.Attribute`/import，回答「模块有没有真的去够 S5–S7」），
并正向断言 `run_p1_plan_view` 在使用中 ⇒ 证明它够的是 **P1**。

### 6 整数表示

测试遍历**整棵**序列化树找 `float`：`converter_readouts` 子树之外 **0 个**。
⛔ 不是「我记得检查的那几个坐标」，是全树。

### 7 全量 + `.pth` 前后哨兵

见 §五。

### 8 范围 · `git diff --numstat` 原文

见 §五。

---

## 五、全量与哨兵

**`.pth` 哨兵（基线跑前 / 跑后 / 改动后跑前 / 改动后跑后，四次全同）**：

```
5198f6f9bf773d07373faa57a16e9564  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
a47a5925858b447ef52e3461fd6543e8  /opt/venv/lib/python3.12/site-packages/_virtualenv.pth
c767f0a08a993aec12f4a381d492dca2  /opt/venv/lib/python3.12/site-packages/sphinxcontrib_jsmath-1.0.1-py3.7-nspkg.pth
```

**两次全量汇总行原文**：

```
基线（c17af4a，改动前）：
========== 3208 passed, 13 xfailed, 212 warnings in 940.76s (0:15:40) ==========

改动后：
========== 3244 passed, 13 xfailed, 212 warnings in 879.24s (0:14:39) ==========
```

**`git diff --numstat` 原文**：

```
1042	0	case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json
779	0	src/agent/judge/as_measured.py
710	0	tests/test_as_measured_facts_layer.py
```

⛔ 全量跑测期间**没有动树**（执行记录本身是跑完之后才写的）。

---

## 六、我认为题面错 / 不全的地方

### 1 ⚠️⚠️ **§一.2「P1 已带齐事实层要的每一样」对 `walls` 那一行不成立**（§五.4 命中）

派工单 R2 表要求 `walls`「由 `wall_bands` 来：**两条面线的引用** + 厚度 + 沿墙区间」。
**实测：一部分 band 的两个面里有一个【图上根本没有面线】。**

```
                signed plan-F1  signed plan-F2  as-received plan-F1  as-received plan-F2
band 总数            45              39                44                   39
只有一个面有面线      9               7                11                    7
```

**病根已量到，⛔ 不是我的匹配写错了**：`wall_bands` **不是墙的清单**。
转换器判「jamb cap」**只看长度**（落在 `wall_thickness_range_m` = [0.06, 0.50] m 内就算），
所以一条画在 `WALL` 图层上的 **0.36 m** 笔画即使不是 cap，照样产出一条 band。
签字件 `plan-F1` 的实例：

```
BAND w_x_35853.6000_36213.6000 axis=x thick=360.0 along=[-19469.0,-15469.0] caps=['1390','143B']
  face_lo=35853.6000 -> 2 lines
  face_hi=36213.6000 -> 0 lines
  nearest consts to hi 36213.6000: [(36273.6, +60.0), (36153.6, -60.0), ...]
```

⇒ 那个「面」正好落在一堵 **120 mm 墙的正中**（±60），图上当然没有面线。
⭐ **这与分母 D2 条款已经写下的口径是同一件事**：`denominator.py` 明写它**拒绝继承**转换器的 cap 集合，
因为 sm25 走廊墙有**真实的 0.36 m 面线片段**被误判成 cap。

**我为什么没有停下上报**（请派工方复核这个判断）：
1. 信息**没缺** —— band 自己记着两个面的坐标，缺的是「其中一个面有没有被画出来」；
2. 修法**完全在 P1 之内**，⛔ 不需要去 S5–S7 取任何东西（F-122 那个坑没被踩）；
3. **「把这些 band 滤掉」是一次裁定，不该由施工席位做** —— 它等于替口径回答「只有一个面的 band 算不算墙」。

**我做的处置**：⛔ 不过滤、⛔ 不假装有两个面 ——
引用列表留空 + 在 `converter_readouts.walls_missing_a_face_line` 里**逐条点名** + 测试把 9/7/11/7 这四个数**钉住**
（[[absence-conflates-causes-in-observables]]）。

⇒ **待裁定（建议归 ②-1b / ②-1c）**：只有一条面线的 band，是墙、是噪声、还是 `producer_defect`？

### 2 ✅ §五.4 点名担心的**另外两样，实测都在**

- **面线的 layer 归属**：`wall_line_layers` 覆盖 `wall_lines` **100%**（两图两视图；本例全部是 `WALL`）。
- **洞口与承载墙的引用关系**：**可 100% 解析且唯一**（签字 31/31、30/30；as-received 31/31、30/30，
  `unresolved_opening_carriers` 全为 0）。⇒ 这条担心**没有成真**。

### 3 ⚠️ R2 的两条要求会**互相冲突**，题面没说以哪条为准

「`converter_readouts` **原样搬**，一个几何都不要重算」与「**每一个坐标都是整数**」——
转换器的诊断自带 `points_dxf_mm`（DXF 原生 mm **浮点**）。四舍五入它 = 重算它。
我的裁断：**`converter_readouts` 是唯一允许含浮点的子树**，其余全树零浮点，并把这条写进 schema 文档与测试。
⇒ 若口径要求别的（例如诊断也换算成 0.1 mm），⛔ 这一处要改。

### 4 ⚠️ 验收 3 只要求「跑两次」

两次相同**可能是随机化恰好关着**。我改成**三次 + 每次自报 `hash(str)`**，
并断言三个种子互不相同 —— 否则那道门在本次跑里是恒真的。

### 5 ⚠️ 基线 commit 号

题面写 `8a5457a`，实际 HEAD `c17af4a`（见 §〇）。

---

## 七、我没做到的（如实）

1. ⛔ **`as_measured.json` 没有作为文件落进仓库。** 落库方案 §二 说它该在
   `case_tests/test_baseline/gt/<case>/facts/as_measured.json`，但 `gt/` 是受保护答案根、
   **唯一写者是晋升**（F-117），而晋升接线派工单 §四 明写归 **②-1b**。
   ⇒ 本单交付的是**能逐位复现地产出它的代码 + 门**，⛔ 不是那个文件。
   （产物 sha256 = `bdf5938e70b0551629a3d43d17cd22e7414b840e8e21fec9508fbf6e124874ef`，91165 bytes。）
2. ⛔ **B1 转换器实现指纹没解** —— 派工单 §四 明列归 ②-1b。
   schema 里放的是一个**显式的 `None`**（`converter_implementation_fingerprint`）
   而不是省掉这个字段：省掉会读成「没人想过」，放个值会读成「有人签过字」。
3. ⛔ **落库方案 §四「reading 容差联动」那道门没做** —— 它比的是一条 `revision` 的 `magnitude_mm`，
   没有 `revisions` 就没有可比的量。归 ②-1b。
4. ⛔ **没有把 reading 判分器改读事实层**（F-130 的解药）—— 那是事实层落库之后的下游接线。
5. ⛔ `revisions` / `as_signed` / `AnswerCompiler` / 出模形式 / `boundary_condition` / 一致性检查重接
   —— 全部 §四 明令不做，**未做**。
6. ⚠️ **只在 sm25-L 这一栋楼上验过**。sm24 只用来钉签字哈希不动，⛔ 没有在 sm24 上产过 `as_measured`。

---

## 八、两次全量的差值对账

```
基线   3208 passed, 13 xfailed
改动后 3244 passed, 13 xfailed
差     +36 passed, +0 xfailed, 0 failed
```

`tests/test_as_measured_facts_layer.py` 单跑 = **36 passed** ⇒ **增量逐个对上**，
⛔ 没有「顺手修好了别的红」或「顺手压住了别的红」。
