# 2026-09-08i 薄片面溯源：`Z04_Ceiling2` / `Z20_Floor1` 的 0.0650 m 短边

调查树：`/tmp/w1_windows_claude`（worktree，分支 `wt/09.08_windows`，HEAD `0661a53a`）
产物：`case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/`
本轮**只读调查**，未改任何生产代码。

---

## 一句话结论

这条薄片**不是管线造出来的**：sm25 源图上一层与二层的 y≈16 m 走廊墙**本来就错开 60 mm**
（gt：F1 东翼墙轴 16.00 m，F2 同位置墙轴 16.06 m），管线忠实地把两层各自拉伸后，
跨层贴合处必然切出一条 65 mm 宽的条带 —— 65 mm = 图纸上真实的 60 mm 台阶
\+ 4.95 mm 识图残差；候选 (b) 成立（层间错开），且这个错开**在源 DXF 里就有**。

---

## Q1 `Z04` / `Z20` 对应上游哪个 cell

读数来源：`2_modelling/attempts/001/output.json` 的 `zone_meta`（我用脚本全量打印）。

| zone | cell_id | 层 (fi) | cell x 范围 | cell y 范围 |
|---|---|---|---|---|
| `Z04_F1_Office_N` | `1f-c013` | 0 = 1f (z_floor 0.0) | [11.0598, 14.8784] | [15.999650, 18.001150] |
| `Z20_F2_Office_N` | `2f-c007` | 1 = 2f (z_floor 3.6) | [11.0598, 14.8784] | [5.878600, 16.064600] |

cell 坐标读自 `1_correction/attempts/001/output.json`：
- `1f-c013`：`{"id": "1f-c013", "x": [11.0598, 14.8784], "y": [15.999649999999999, 18.001150000000003]}`
- `2f-c007`：`{"id": "2f-c007", "x": [11.0598, 14.8784], "y": [5.8786…, 16.0646]}`

两者在 z=3.6 m 平面上的重叠区 = x∈[11.0598, 14.8784] × y∈[15.99965, 16.0646]。

## Q2 那条 0.0650 m 的边是哪两个顶点

直接读 `2_modelling/attempts/001/output.json` 里两张面的 `verts`（原文照抄）：

```
Z04_Ceiling2  zone=Z04_F1_Office_N  type=Ceiling  obc=Surface  obc_obj=Z20_Floor1
  [11.0598, 16.0646,               3.6]
  [11.0598, 15.999649999999999,    3.6]   <- 这两点之间就是那条短边
  [14.8784, 15.999649999999999,    3.6]
  [14.8784, 16.0646,               3.6]

Z20_Floor1    zone=Z20_F2_Office_N  type=Floor    obc=Surface  obc_obj=Z04_Ceiling2
  [11.0598, 15.999649999999999,    3.6]
  [11.0598, 16.0646,               3.6]
  [14.8784, 16.0646,               3.6]
  [14.8784, 15.999649999999999,    3.6]
```

短边 = `(11.0598, 15.99965, 3.6) → (11.0598, 16.0646, 3.6)`（另一条同长的在 x=14.8784 一侧）。

- 精确长度（JSON 值直算）：`16.0646 - 15.999649999999999 = 0.06494999999999962` m
- 面积：0.24802 m²，长宽比 3.8186 : 0.06495 ≈ 59 : 1
- 门打印的 `0.0650`：坐标进 IDF 时按 4 位小数取整，`round(15.99965, 4) = 15.9996`，
  `16.0646 - 15.9996 = 0.0650`（我实测了这个算术；⚠️ 见「没能确定的」第 3 条）
- 门本身：`src/validator/interzone.py:64` `_MIN_EDGE = 0.10`，
  `src/validator/interzone.py:127-135` 对**每一张面**做 min-edge 检查。

同一个 Z04/Z20 配对的其余分片都是正常尺寸，说明切配本身没错：

```
Z04_Ceiling1  -> Z18_Floor3   y [16.0646, 18.00115]   area 7.395
Z04_Ceiling2  -> Z20_Floor1   y [15.99965, 16.0646]   area 0.248   <-- 薄片
Z20_Floor2    -> Z05_Ceiling  y [13.9982, 15.99965]   area 7.643
Z20_Floor3..6 -> …            均 7.6–8.1 m²
```

## Q3 它是怎么产生的 —— (a) / (b) / (c)

**判定：(b)，且错开来自源图本身，不是层间对齐算错。(c) 排除，(a) 部分成立但性质不同。**

### 排除 (c)：2_modelling 只是忠实相交

Z04_Ceiling2 的四个顶点值 **逐个** 等于上游两个 cell 的边界值
（11.0598 / 14.8784 来自两层公用的 x 轴；15.99965 来自 `1f-c013`；16.0646 来自 `2f-c007`）。
没有任何新数字被引入 —— 布尔/拉伸没有制造这条边，它是两层 cell 边界之差的直接结果。

### 上游两层的 y 轴对照（全量比对，脚本实跑）

把两层所有 cell 顶点的 y 值列出来互找最近邻，**只有两处跨层近似错位**：

```
1f 13.99820  vs  2f 14.12260   delta +0.12440   (>= 0.1，切出的条带合法，门放行)
1f 15.99965  vs  2f 16.06460   delta +0.06495   (<  0.1，就是本次薄片)
1f 独有(0.5 m 内无 2f 对应): 7.9937, 9.9995, 11.9967, 18.00115
2f 独有: 无
x 轴：2f 独有 16.90795，其余全部两层一致，无近似错位
```

### 6.5 cm 在上游能直接找到吗 —— 能，一路找到源 DXF

**① 1_correction 的 cut_lines（每层的墙线）**

`1_correction/floor_1/cut_lines.json`：y≈16 处是**两道不同的墙**
```
axis x  pos_m 16.0646            along 0.2215–3.856 / 4.6348–5.392 / 6.1491–10.0216   wall_4aa4fbac856…   (西段)
axis x  pos_m 15.999649999999999 along 11.1033–14.7811                                 wall_d0f2073afba…   (东翼)
```
`1_correction/floor_2/cut_lines.json`：y≈16 处只有**一道贯通墙**
```
axis x  pos_m 16.0651  along 0.2452–3.8645 / 4.6276–5.3907 / 6.1538–10.1219 / 10.9286–14.7877   wall_bc264d4793d…
```
即：1f 的东翼在 y≈16 处是一道**独立的、比西段低 65 mm 的墙**；2f 是一道拉通的墙。

**② 0_reading 的原始面线（像素级，`0_reading/1f_view.json` → `observations.face_lines`）**

1f 在 y≈16 处读到**四条**行线：

| idx | id | pos_px | pos_m | runs_m（沿 x） |
|---|---|---|---|---|
| 26 | L027 | 489.5 | 16.1241 | 0.2215–9.9134（西） |
| 27 | L028 | 492.5 | 16.0592 | 11.1033–14.7811（东翼） |
| 28 | L029 | 495.0 | 16.0051 | 0.2215–10.0216（西） |
| 29 | L030 | 498.0 | 15.9401 | 11.1033–14.7811（东翼） |

配对是被 runs 的 x 范围**强制**的（西 26+28、东 27+29，两组各相距 5.5 px），
中线：西 (489.5+495.0)/2 = 492.25 px、东 (492.5+498.0)/2 = 495.25 px，**差 3.00 px**。
1f 标定 `m_per_px = 0.021637770396994754`（`observations.calibration.y`），
3.00 px × 0.0216378 = **0.06491 m**。

2f（`0_reading/2f_view.json`）在 y≈16 处只有**两条**行线：
L029 pos_px 519.0 / 16.1251、L030 pos_px 524.5 / 16.0051，且两条的 runs **都跨到东翼**
（含 [10.9286, 14.7877] / [11.1248, 14.7877]）。中线 16.0651。

**③ 源 DXF 的 ground truth（决定性证据）**

`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json`
（`source_dxf_label: sm25-L_t3_as_received.dxf`，单位 0.1 mm，`units_per_metre 10000`；
gt 与 reading 共用同一世界原点 —— gt 0 = 外墙外表面，reading 0.12 = 该墙轴线，半厚 0.12）。

axis=x（沿 x 走、常量为 y）且中线落在 15.5–16.5 m 的墙：

```
=== plan-F1
  w_x_159400_160600_111200_147600   face 159400/160600  th 1200  along 111200–147600  center 16.00 m   <-- 东翼独有
  w_x_160000_161200_2400_38400      face 160000/161200  th 1200  along   2400– 38400  center 16.06 m
  w_x_160000_161200_46400_53600     face 160000/161200  th 1200  along  46400– 53600  center 16.06 m
  w_x_160000_161200_61600_98800     face 160000/161200  th 1200  along  61600– 98800  center 16.06 m   (西段止于 x=9.88)
=== plan-F2
  w_x_160000_161200_2400_38400      center 16.06 m
  w_x_160000_161200_46400_53600     center 16.06 m
  w_x_160000_161200_61600_101000    center 16.06 m
  w_x_160000_161200_109000_147600   center 16.06 m   <-- 东翼也是 16.06，没有 16.00 那道
```

**结论：源图上，F1 东翼（x 11.12–14.76 m）的这道墙轴在 y = 16.00 m，
F2 同一位置的墙轴在 y = 16.06 m —— 图纸本身就有一个 60 mm 的层间台阶。**
识图把它读对了（1f 平面 C2 长度覆盖 99.2%、C1 100%，`0_reading/attempts/001/score_vs_gt.json`）。

所以：
- (a) 「上游 cell 本身有一条 6.5 cm 的边」—— **不成立**。1f 和 2f 的 cell 自身最短边都远大于 0.1 m
  （`1f-c013` 边长 [2.0015, 3.8186, 2.0015, 3.8186]，最短 2.0015 m；
  `2f-c007` 边长 [3.8186, 10.186, ×2]，最短 3.8186 m；
  **两层 27 个 cell 里最短的一条边是 1.1193 m**（`1f-c000`），全都 ≫ 0.1 m）。
  6.5 cm 只在**跨层求交**时才出现。
- (b) 「两层 cell 边界错开 6.5 cm」—— **成立**，且错开是**真实的**（图纸 60 mm）而非对齐算错。
- (c) 「拉伸/布尔产生」—— **排除**，见上。

### 层间对齐这一步做了什么（为什么 65 而不是 60）

as-drawn 链的跨层调和在
`src/agent/correction/multifloor.py:1023` `reconcile_floors_to_reference`
→ `src/agent/correction/projection_bridge.py:319` `align_wall_lines_to_reference`：
`projection_bridge.py:372-375` 把上层每条 wall 线移到参考层**同轴最近**的 wall 位置，
且**只在 tolerance 之内**移动；超出容差就原样保留。

本次容差（`1_correction/footprint_snap_ledger.json`，2f 记录）：
`tolerance_m = 0.02064349219630876`（`noise_bound` 限支，`cap_m: 0.06`）。

于是 2f 的 16.0651：
- 到 1f 候选 16.0646 距离 0.0005 ≤ 0.02064 → **被吸附成 16.0646**（ledger `action: "snapped"`）
- 到 1f 候选 15.99965 距离 0.06545 > 0.02064 → 不是最近、也超容差

这解释了为什么 2f 的 cut_line 是 16.0651、cell 里却是 16.0646
（`grep -c 16.0646` 在 `floor_2/cut_lines.json` = 0，在 `correction_geometry_snapped.json` = 19）。

## Q4 6.5 cm 的算式

**主算式（管线内部）：**

```
0.06495 m = 16.064600 (2f-c007 的 y 上界)  −  15.999650 (1f-c013 的 y 下界)
```

**拆到「已有量之差」：**

```
16.064600 = 1f 西段走廊墙轴（reading 中线 (16.1241 + 16.0051)/2 = 16.0646）
            └ 2f 自己读到的 16.0651 被 align_wall_lines_to_reference 吸附到这个值（Δ 0.0005 ≤ 容差 0.02064）
15.999650 = 1f 东翼走廊墙轴（reading 中线 (16.0592 + 15.9401)/2 = 15.99965）

像素侧同一条差：(495.25 px − 492.25 px) × 0.021637770396994754 m/px = 0.06491 m
              （1f_view 的 L028/L030 中线 − L027/L029 中线，标定取自 observations.calibration.y）
```

**对照源图，逐项归因（每一项都有 gt 读数）：**

```
0.06495  (管线切出的薄片宽)
= 0.06000  图纸真实层间台阶     gt F2 东翼墙轴 16.0600 − gt F1 东翼墙轴 16.0000
+ 0.00460  1f 西段墙轴识图残差   reading 16.0646 − gt 16.0600   （2f 经吸附继承了这个值）
+ 0.00035  1f 东翼墙轴识图残差   gt 16.0000 − reading 15.99965
———————
  0.06495  ✅ 逐位吻合（0.06000 + 0.00460 + 0.00035 = 0.06495）
```

一句话：**6.0 cm 是图纸给的，0.5 cm 是识图误差，合起来 6.5 cm。**

---

## 附：一条与本题相关、但题面没问的发现

`src/agent/correction/deterministic.py:1-12` 的模块 docstring 明确声称：

> "no two canonical axes are closer than `min_edge_length_m`, so the interzone
> floor/ceiling split cannot produce a degenerate sub-tolerance sliver — the
> EnergyPlus input-processing segfault class is made structurally impossible."

**这条防线不在本次 run 的路径上。** 本次 run 走的是 as-drawn 证据链腿：
- `1_correction/attempts/001/deterministic_core_proof.json`: `"core_version": "as_drawn_chain_1"`
- `1_correction/attempts/001/output.json`: `deterministic_core_stamp.version = "as_drawn_chain_1"`
- `src/agent/correction/finalize.py:248` `finalize_as_drawn_chain_geometry` 全程**不调用**
  `src/agent/correction/deterministic.py:1072` `apply_deterministic_core`
  （`finalize.py:226-246` 的注释自己写明「⛔ never through `apply_deterministic_core`」）
- `1_correction/attempts/001/audit.json` 的 `corrections` 里 **31 条全是**
  `deterministic_core.window_host_resolver_v1`，**零条** `cross_floor_align` / `same_floor_axis_merge`；
  cell 坐标（15.99965 / 5.12155 / 16.90795）**都不是 `structural_snap_grid_m = 0.010` 的整数倍**，
  也证明轴吸附没跑过。

as-drawn 腿的跨层调和 (`align_wall_lines_to_reference`) **没有 min-edge 地板** ——
它只做「最近且在容差内就吸附」，不检查吸附后任意两轴是否 ≥ 0.1 m。
所以 gate① 是这一类薄片在本条路径上的**唯一**拦截点。

⚠️ 离线探针（把本次产物的两层 y 值直接喂给 legacy 核的
`_reconcile_cross_floor(per_floor_axes, footprint, tol, 'y')`）读数：

```
raw 15.99965 -> 16.03
raw 16.0646  -> 16.06
audit: deterministic_core.same_floor_axis_merge  target y.axis[1f:15.9997|16.0646]
       step sliver_merge  resolved 16.03  separation 0.0649  tolerance MIN_EDGE_LENGTH
       reason "two or more distinct axes on ONE floor were collapsed into a single
               canonical axis; if they were a real building step it is gone from the geometry"
```

也就是说：即便 legacy 核跑了，它会把这**两道真实存在的墙**（gt 16.00 / 16.06）合并掉，
并在 audit 里如实记一笔「真实台阶可能被抹掉了」。
`deterministic.py:412` 的注释里恰好点名了同一个量级：
「a real building step (e.g. a 240/120 wall-basis jog, **measured at 60 mm**)」。
⛔ 我没有把这条探针当作「legacy 核会怎样」的定论 —— 见下节第 2 条。

---

## 我没能确定的

1. **1f 东翼那道 16.00 m 墙、跟 1f 西段 16.06 m 墙，在真实建筑里是不是「同一道墙的 240/120 变厚台阶」。**
   gt 给的是两条独立 wall 记录，厚度都是 1200 (0.12 m)，不是 240/120 变厚；
   但 F2 把它拉成一道贯通墙、F1 拆成两道错开 60 mm 的墙，这个设计意图我读不出来。
   这决定了「正确解」是「保留 60 mm 台阶并让下游不产生薄片」还是「本来就该是一道墙、图纸有误」——
   ⭐ 这是需要用户/领域口径拍板的那一格，我不替它选。

2. **legacy 确定性核真跑起来会怎样。** 上面那条探针是我手工调内部函数
   `_reconcile_cross_floor` 得到的，不是生产路径（生产路径是
   `apply_deterministic_core`，前后还有 envelope / connectivity / 校验若干段）。
   而且探针返回的 mapping 是一个**按 raw 值 key 的扁平 dict**，`16.0646` 在两层都出现、
   会互相覆盖，所以「15.99965→16.03 而 16.0646→16.06（仍差 0.03 < 0.1）」这个读数
   到底是核的真实行为、还是我这种调法的产物，我**没有验证**。⛔ 不要拿它当结论。

3. **门里打印的 `0.0650` 与 JSON 里 `0.06495` 的 4 位取整发生在哪一行代码。**
   算术我验了（`round(15.99965, 4) = 15.9996`，`16.0646 − 15.9996 = 0.0650`，`'%.4f'` → `0.0650`；
   而不取整时 `'%.4f' % 0.06494999999999962` → `0.0649`），
   但我没在 `src/mcp/api/core.py` / `src/agent/nodes/surface.py` 里定位到那次 round 的具体位置。
   这不影响任何结论（0.06495 与 0.0650 都远小于 0.1）。

4. **2f 识图那 5.1 mm 偏差（16.0651 vs gt 16.0600）是不是也代表 2f 东翼漏读了一道 16.00 的墙。**
   gt 说 F2 东翼没有 16.00 那道墙，所以「漏读」不成立；但 2f 的 grade 有
   `C3_bad_split: 1`（`score_vs_gt.json`），我没有去核那一处 bad_split 落在哪条线上、
   是否与 y≈16 这一带有关。

---

## 复现命令

```bash
cd /tmp/w1_windows_claude
# 面顶点
PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -c "
import json; d=json.load(open('case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/2_modelling/attempts/001/output.json'))
print([s for s in d['surfaces'] if s['name'] in ('Z04_Ceiling2','Z20_Floor1')])"
# zone -> cell
PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -c "
import json; d=json.load(open('case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/2_modelling/attempts/001/output.json'))
print([m for m in d['zone_meta'] if m['name'].startswith(('Z04_','Z20_'))])"
# gt 源图的两层墙轴
PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -c "
import json; d=json.load(open('case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json'))
[print(v['view_id'], w['id'], (w['face_lo']+w['face_hi'])/20000)
 for v in d['views'] for w in v['walls']
 if w['axis']=='x' and 155000<(w['face_lo']+w['face_hi'])/2<165000]"
```

---

## 附录 · ⭐⭐⭐ 用户一问翻出更根本的问题：gt 自身违反 1 mm 量化

**用户原话**：「内墙墙厚都是 120mm」＋「gt 不都是按 1mm 入库了吗？为什么还有那种浮点数？」

**主控实测**（`case_tests/test_baseline/gt/sm25-L_anchor/gt.json`，312 个顶点坐标全扫）：

```
⛔ 非 1 mm 整数倍的坐标 = 8 个，全部在 floors[0]（1f）：
   15.9996 × 4   （zones[2] / zones[3]）
    9.9999 × 4   （zones[8] / zones[9]）
2f 一个都没有。
```

| 值 | 距最近整毫米 | 距最近常见轴位 |
|---|---|---|
| `15.9996` | **0.4 mm** | `16.000` 差 0.4 mm |
| `9.9999` | **0.1 mm** | `10.000` 差 0.1 mm |

⇒ 两处都是「差零点几毫米没落到整数上」的残留 —— **入库量化没盖到的漏网**，⛔ 不是设计值。

### ⇒ 本次薄片的性质改判

原推断：「gt 里有 60 mm 台阶 ⇒ 可能是真实建筑特征」。三条实测合起来推翻它：

1. **用户给的领域事实**：内墙一律 **120 mm** ⇒ 60 mm **恰好是半个墙厚**
2. **主控实测**：gt 用**轴线基准**（墙两侧 zone 共用同一条边界、无墙厚间隙）
3. **主控实测**：`16.0600` 合法；`15.9996` **违反 1 mm 量化**

⇒ **`16.0600` 是合法轴线值；`15.9996` 是一个没被量化住的脏值**，
它离 `16.000` 差 0.4 mm，而 `16.000` 离轴线 `16.060` 差 **60 mm = 半个墙厚**。
⇒ **1f 东翼那两个 zone 的边界记的是墙【面】而不是【轴线】** —— **gt 缺陷，⛔ 不是建筑台阶**。

⚠️ **划界**：第 3 条是实测；「记的是面不是轴」是由「60 = 120/2」+「gt 用轴线基准」
**推出来的**，⛔ **尚无直接读数证实**。要坐实需查 gt 生成器在那两个 zone 上如何取边。

### ⚠️ 为什么这条比薄片本身重要

**gt 是判卷的权威。** 8 个坐标没过 1 mm 量化、其中 4 个还偏了半个墙厚
⇒ **所有拿它当参照的分数都带着这个偏差**，而且**它躲过了 gt 复核**。
⇒ 登记为待办：① gt 入库量化门为何没拦住这 8 个；② 那两处边界基准为何与全局不一致。
