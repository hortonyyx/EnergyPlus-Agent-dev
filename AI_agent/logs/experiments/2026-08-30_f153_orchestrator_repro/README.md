# F-153 主控独立复现 + 根因定位（2026-08-30）

- **做的人**：orchestrator（Claude 家族，主控）· **性质**：⭐ **独立复现**，⛔ 不转引复核方数字
- **为什么做**：`AI_agent/plan.md` F-153 行写死「⚠️ 主控本轮【未】独立复现面积数，只复现了缺陷形状
  ⇒ 下轮第一件事」；且本项目记忆条 `citing-someone-elses-fact-does-not-transfer-responsibility`
  要求「写进承重位置前自己量一遍」。
- **被量对象**：`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json`
  （落库的真实产物，`plan-F1` / `plan-F2` 两个 view）
- **生产阈值**：`min_room_area_m2 = 5.0`（取自 `case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json`）
- **代码位置**：`src/agent/judge/as_measured.py` — `derive_boundary_edges`(1314) ·
  `_boundary_owners`(1183) · `_classify_boundary_fact`(1215)
- **HEAD**：`8abd6e0`

---

## 一、复现结论：**三个数与复核方逐位相同**

```
=== plan-F1 ===
  difference 出的多边形共 19 个；过 5.0 m2 阈值的 cavity = 13 个；落库 boundary_edges 覆盖 cavity = 11 个
  未过阈值的碎片面积 top5 (m2) = [0.0576, 0.0576, 0.0576, 0.0576, 0.0576]
  ⛔ EXCLUDED cavity:8bd127719198fd63  area=88.27 m2  贴墙 400/400 (≤0.04 m)  最远采样点距墙带 0.000 m
  ⛔ EXCLUDED cavity:04e1293098b1a95a  area=28.68 m2  贴墙 400/400 (≤0.04 m)  最远采样点距墙带 0.000 m
=== plan-F2 ===
  difference 出的多边形共 21 个；过 5.0 m2 阈值的 cavity = 15 个；落库 boundary_edges 覆盖 cavity = 14 个
  ⛔ EXCLUDED cavity:495501ce9b36f0f3  area=70.34 m2  贴墙 400/400 (≤0.04 m)  最远采样点距墙带 0.000 m
合计被排除的过阈值 cavity = 3
```

⇒ **88.27 / 28.68 / 70.34 m²** 三个数**确认**；贴墙率 400/400，且**最远采样点距墙带 = 0.000 m**
（不是「≤4 cm」，是**贴死**）。未过阈值的碎屑**全部 0.0576 m²**（复核方写 0.058，同一批）。
⇒ **「天然 NA、本就无 ring 可导」的辩解在这三个上不成立** —— 复现无异议。

复现命令：`python AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/probe_1_which_cavities_are_dropped.py`

---

## 二、⭐⭐⭐ 本轮新增：**根因不是一个，是两个，机制完全不同**

上一轮（复核方 + 请求书 + plan.md）只到「exclusion 是无界豁口 / 生产侧根因待查」。
主控本轮把两个形态各自拆到了 file:line。

### 形态 A · **出口射线只走 0.1 mm 就撞进【垂直邻墙】，一条 span 判死整个 88 m² 的 ring**

命中：`plan-F1` 88.27 m² 与 `plan-F2` 70.34 m²，**两层同一处、同一条 span**。

```
span      = axis=x, cavity_const=160000, lo=46400, hi=53600, side=-1
owner     = 墙组 ('x', 160000, 161200)      ← 120 mm 厚的水平墙，cavity 在它下方
raw_near  = 160000   raw_far = 161200
exit_point= [50000, 161201]                ← far face + 【1 个单位 = 0.1 mm】
wall_covers(exit_point) = True             ← ⛔ 还在墙体里
覆盖它的是 = WALL w_y_49400_50600_161200_197600
             axis=y, face=[49400,50600] (120 mm), along=[161200,197600]
             ＝ 一堵【垂直】墙，正好从 y=161200 起向上走
```

⇒ `_classify_boundary_fact` 判 `logical_edge=False`（"A ray still inside wall material is a junction
fragment"），`derive_boundary_edges` 于是 `ring_is_logical = False; break` ⇒ **`continue` 掉整个 cavity**。

**⭐⭐⭐ 这不是运气不好，是结构性的**：
```
plan-F1: span x[46400,53600] 采样 721 点(1mm 步长)，落在墙体并集内 = 121 (16.8%)
         生产代码只采 mid_along=(46400+53600)//2=50000 ⇒ 判死
         中毒区间 x=[49400,50600]  ← 正是那堵垂直墙的两个面
plan-F2: 逐字相同
```
⇒ **span 的两端 (46400 / 53600) 关于那堵垂直墙的中线 (50000) 对称**，
所以 `mid_along` **系统性地**落在 T 形接头上。**83.2% 的采样位置本来会判活。**
⇒ 病灶 = **「单点采样」+「1 单位步长」这两个没人签过字的隐藏参数**
（同族记忆条 `silent-default-threshold-behind-otherwise-conclusions`）。

### 形态 B · **一堵墙的 `along_min` 比同侧兄弟大 1 个单位（0.1 mm），`_boundary_owners` 要求整数精确相等**

命中：`plan-F1` 28.68 m²。

```
span   = axis=y, cavity_const=52401, lo=99430, hi=100630, side=-1
owners = 0                                  ← ⛔ 没有任何墙组认领它
同轴 |Δ|≤30 单位(3 mm) 的墙面 const = [52400]   ← 差【1 个单位】
near-miss group ('y', 50000, 52400) 的覆盖区间 = [(96399, 103599)]  ← 完全盖住 [99430,100630]
```
⇒ **该墙组本来就该认领这条 span，只因 const 差 0.1 mm 而 `const in (group.face_lo, group.face_hi)`
（`as_measured.py:1186`）不成立** ⇒ owners=0 ⇒ 整个 28.68 m² 房间被丢。

**52401 是哪来的？**（主控实测，`probe_3_detail.py`）
```
cavity 环上的原始坐标是【精确的 52401.0】，不是浮点噪声
全仓 walls/openings 里 face/cross const == 52401 的：【0 个】
造出这条 x=52401 竖直边的是一堵【x 轴】墙的 along_min：
  w_x_99430_100630_52401_88800   face y=[99430,100630]  along x=[52401, 88800]
它的三个同侧兄弟全都是 52400：
  w_x_0_2400_52400_86400 / w_x_38800_40000_52400_110400 / w_x_57600_60000_52400_88800
```
⇒ **一堵墙的端点比同侧全部兄弟多出 0.1 mm**，在 `unary_union` 后留下一条
**0.1 mm 宽 × 0.12 m 高**的缺口，cavity 环因此长出两个 `x=52401` 的顶点。

**⭐ 连带的第二处伤**：这条 0.1 mm 缝还毒化了 `representative_point()` ——
```
cavity area = 28.6832 m2   bounds x=[52400, 88800]
representative_point = (52400.500000, 100030.000000)   ← 落在那条 0.1 mm 缝里
centroid            = (70599.992,  99999.543)
```
而 `derive_boundary_edges:1336` 拿 `representative_point` 定**每一条 span 的 `side`**
⇒ **一个 28.68 m² 房间的「内部代表点」是一条 0.1 mm 宽缝里的点**，整圈 `side` 都建在它上面。

---

## 三、⭐⭐ 方法论收获（可搬进记忆）

1. **复核方的数对了，但根因它没给** —— 「转引不免责」这条这次的收益不是「抓它的错」，
   而是**自己量一遍才拿到了它没拿到的东西**（两个根因 + 结构性而非偶然的证明）。
2. **两个根因共享同一个上位病族**：都是**把连续几何塌缩成整数/单点之后，用「精确相等」或「单点采样」去判**
   —— 同 `representation-collapse-manufactures-unrelated-errors`。
   ⇒ ⛔ **「把容差调大」是错的轴**（形态 A 加容差会开始吞真墙；形态 B 加容差会让 owners>1）。
3. **失败半径是「整个 ring」而不是「这条 span」** —— `break` + `continue` 让
   **一条 0.12 m 的 span 判死一个 88 m² 的房间**，且**不留任何诊断**。
   ⇒ 同 `invalidation-blast-radius-must-be-scoped`（08-21 已记过同形状）。

---

## 四、探针清单（全部可重跑，⛔ 只读，不写任何产物）

| 文件 | 回答什么 |
|---|---|
| `probe_1_which_cavities_are_dropped.py` | 过阈值 cavity 里哪些被丢 + 面积 + 贴墙率 |
| `probe_2_root_cause.py` | 每个被丢的 cavity 死在哪条 span、什么原因、near-miss 墙组是谁 |
| `probe_3_detail.py` | 形态 A 的 exit_point 被谁覆盖；形态 B 的 52401 是谁造的 + rep point |
| `probe_4_single_sample_fragility.py` | 形态 A 的单点采样脆弱度（16.8% 中毒区，mid 正中） |

跑法（仓库根目录）：`python AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/<probe>.py`

---

# 补记（同日晚，主控第二轮）：**形态 B 的真正来源在【图】和【正交吸附】那一头，不在 `_boundary_owners`**

> 起因：GPT 施工席位就本单**强制停报**（见 §五），主控顺着它报的哈希失配去查 `revisions` 台账，
> 撞到一条上一轮完全没人看的东西。**以下每一条都是主控本轮亲手量的。**

## B-1 · `revisions` 台账**早就点名了这两条线**，但**没人签、也没有可签的动作**

`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json`：
```
条目总数 = 5     verdict 分布 = {'unsigned': 5}     已签(signed_by 非空) = 0

rev-13ad  target={handle:13AD, view_id:plan-F1}
          finding.check = face_line_multiple_fields_changed
          detail = "2 fields differ ([('const', -31), ('along_min', -1)]); not a single-field translate"
          candidate_action = null      verdict = unsigned
rev-13ae  同上，detail = "... [('const', -31), ('along_min', 1)] ..."
```
⇒ **`13AD` / `13AE` 正是形态 B 那堵墙的两条面线**（§二 形态 B 已实测）。
⇒ ⭐ 台账**看见了**这 ±1，但 `candidate_action = null`（「不是单字段 translate」）
⇒ **今天没有任何机械动作可供签字** ⇒ `as_signed` 与 `as_measured` 在这两条上**逐字相同**（已实测）。

## B-2 · 两份 DXF 直读：**as-received 图里这两条线本来就歪、且起点差 0.1915 mm**

```
=== sm25-L_t3_as_received.dxf ===
 13AD LINE start=(-25228.9258, 38279.4638)  end=(-21589.0215, 38273.6554)   ← 歪 5.8084 mm
 13AE LINE start=(-25229.1173, 38159.4639)  end=(-21589.0215, 38153.6552)   ← 歪 5.8087 mm
=== sm25-L_t3.dxf（修正后的图）===
 13AD LINE start=(-25229.022, 38273.464)    end=(-21589.022, 38273.464)     ← 水平、干净
 13AE LINE start=(-25229.022, 38153.464)    end=(-21589.022, 38153.464)     ← 水平、干净
```
⇒ **两条线的起点 x 相差 `-25228.9258` vs `-25229.1173` = 0.1915 mm** ——
量化到 0.1 mm 后落成 **52401 / 52399**，**恰好跨在干净的 52400 两侧**。
⇒ ⭐ **修正后的图里两条完全一致**（都是 −25229.022）⇒ 这是 as-received 图的**画法瑕疵**，不是转换器造的。

## B-3 · ⭐⭐⭐ 全 view **唯一被正交吸附的两条线，就是这两条**

`as_measured.json` → `converter_readouts.axis_snapped_lines`：
```
--- plan-F1: 恰好 2 条 ---
 id=13AD  snapped_axis=y  angle=0.0914°  minor_leg=58 单位 (5.8 mm)
   before p0=[52401,100659] p1=[88800,100601]   after p0=[52401,100630] p1=[88800,100630]
 id=13AE  snapped_axis=y  angle=0.0914°  minor_leg=58 单位 (5.8 mm)
   before p0=[52399, 99459] p1=[88800, 99401]   after p0=[52399, 99430] p1=[88800, 99430]
--- plan-F2: 0 条 ---
```
⇒ **吸附只扶正了 `const`（y 方向取中），`along` 端点 52401 / 52399 原样穿过**。
⇒ ⚠️ **准确的因果表述（⛔ 别说过头）**：
**正交吸附没有制造这 0.19 mm，但它是这两条线【能进到管线里】的原因** ——
`AXIS_SNAP_MAX_DEVIATION_M = 0.010`（10 mm）· `AXIS_SNAP_MAX_ANGLE_DEG = 1.0`
（`tarch_normalize.py:134,170`，**= 用户 2026-08-30 亲自签的 F-143 阈值**），
而 5.8084 mm / 0.0914° **两项都过**。⭐ 本批指南第 319 行原话：
「sm25 那条线歪 **5.809 mm** ⇒ 超出 ⇒ 被丢」—— **那正是这条线，签字前它是被丢弃的。**

## B-4 · ⇒ 处置轴整个换掉了

| 路 | 是什么 | 评价 |
|---|---|---|
| **甲** | **签 `rev-13ad`/`rev-13ae`**，让 `as_signed` 把端点归到干净值 | ⭐ **最合口径**（as_measured 忠实 · revisions 修正 · as_signed 派生）。⛔ **今天卡死**：`candidate_action=null`，**revisions 的动作词汇表里没有「把两条面线的 along 端点对齐」这种动作** ⇒ 缺的是**动作类型**，不是签名 |
| **乙** | 吸附时把 `along` 端点一并规整 | 需要一个「谁向谁对齐」的依据；⚠️ **有没有参数自由的写法，是要论证的** |
| **丙** | 下游 `_boundary_owners` 容忍 ±N | ⛔ **已被派工单禁掉**，且现在更清楚为什么：**病灶在两层之上** |

⇒ ⭐⭐⭐ **给下一轮的硬结论**：**形态 B 不是 `derive_boundary_edges` 的缺陷**，
它是「**画法瑕疵 → 吸附放行 → 端点未对齐 → 下游精确相等**」这条链的**最末端症状**。
⛔ 在 `_boundary_owners` 上修它，等于在链的末端打补丁。

## B-5 · ⚠️ 这条链上暴露的**第二个洞**（与 F-153 同族但独立）

`revisions` 的 5 条**全部 `unsigned`**、其中 **2 条 `candidate_action=null`**
⇒ **台账能【发现】的形态，比它能【表达】的动作多。** 发现了但表达不了 ⇒ 永远签不了 ⇒ **等于没发现**。
⇒ 这是 [[absence-conflates-causes-in-observables]] 的形状：
「未签字」把「**人还没看**」和「**根本没有可签的动作**」压成了同一个空白。
