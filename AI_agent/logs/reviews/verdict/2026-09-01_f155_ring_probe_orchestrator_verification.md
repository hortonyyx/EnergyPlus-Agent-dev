# F-155 判别实验 · **主控独立核验 + 裁定**

- **日期**：2026-09-01 · **施工方**：GPT 家族 · **核验方**：**Claude 家族 / orchestrator**
- **性质**：⭐ 这是**判别实验的读数核验**，⛔ **不是**实现的跨家族审 —— 实现单另立、另审。
- **产物**：[probe.py](../../experiments/2026-09-01_f155_ring_from_intersection/probe.py)（415 行）·
  [执行档](../execution/2026-09-01_f155_ring_probe_execution.md)

## 裁定：**实验成立，结论采信**（主控逐位复现）

---

## 一、⭐ 先查它有没有抄答案（⛔ 这是本类读数最容易造假的地方）

「重建环与源腔对称差 = 0.000000」如果是**从腔多边形反读**出来的，这个 0 毫无意义
（[[self-consistent-gates-anchor-on-product-chosen-apertures]]）。主控查了探针源码：

| 查什么 | 结果 |
|---|---|
| 角点怎么来 | `intersection_ring()` **由相邻支撑线求交**算出；相邻两条不垂直 ⇒ `adjacent_supports_parallel` **raise** |
| 支撑线怎么来 | `facts_backed_supports()` 逐条到**事实层墙带目录**里找，找不到 ⇒ `support_not_in_facts` **raise**；区间盖不满 ⇒ `support_interval_not_covered` **raise** |
| 腔用在哪 | ⚠️ **只用来定环的循环顺序**（施工方自报，属实）|

⇒ **角点不是抄的**。⭐ 且实验**隔离了正确的变量**：**同一组支撑线**下，
端点首尾接 ⇒ 自交；求交算角点 ⇒ valid。**这正是判别实验该有的形态。**

## 二、主控独立复跑，**逐位对上**

```
TARGET plan-F1  valid=True  vertices=24  area=88.265600  expected=88.27  delta=-0.004400  interval_misses=0
TARGET plan-F2  valid=True  vertices=16  area=70.339200  expected=70.34  delta=-0.000800  interval_misses=0
HEALTHY count=25  all_baseline_edges_4=True  all_rebuilt_vertices_4=True  all_valid=True  all_interval_misses_0=True
MISALIGNED_0P1MM plan-F1 cavity:04e1293098b1a95a  alive=True  vertices=8  valid=True
```
⭐ **双向都过**：治好了两个走廊腔，**25 个健康腔一个没弄坏**（仍 4 顶点、仍 valid）。

## 三、⭐⭐⭐ 比「求交能拼拢」更重要的两件事

### 1 · **一次换表示，治好了 F-153 判定的【两个不同的病】**
F-153 当时的判别实验结论是「**这其实是两个病，⛔ 别当一个修**」：
形态 A（88.27 + 70.34）= 出口射线撞进垂直邻墙；形态 B（28.68）= 一堵墙 `along_min` 差 **1 个单位（0.1 mm）**。
**F-155 实测：28.68 那个也活了**（8 顶点、valid）⇒ **求交重建对 0.1 mm 端点错位免疫。**
⇒ ⭐⭐⭐ [[representation-collapse-manufactures-unrelated-errors]] 又一次兑现：
**多个「不相干」的错常同源于一个有损的表示步骤** —— **换表示 > 加容差 > 加分支**。
⇒ ⛔ **F-153 那条「两个病别当一个修」的结论，本轮被推翻**（它在**旧表示下**是对的）。

### 2 · **`interval_misses=0` ⇒ 答案本来就在事实层里，是推导过程把它扔了**
每个腔的每一段边界区间，**都在事实层墙带里找得到支撑线**（27 个腔全部 `interval_misses=0`），
且重建环与源腔**对称差 0.000000**。
⇒ **腔多边形一直是对的**；`derive_boundary_edges` 是**从一份正确的源头造出了一个自交的环**。
⇒ ⭐ 这让修法比原先估计的**轻得多**：不是要补数据，是要换角点的算法。

## 四、⚠️ 这个实验**没有**回答的（施工方诚实自报，主控确认）
> 「循环拓扑顺序仍取自事实层 cavity component；**尚未证明仅凭无序 supports 可以唯一恢复环序**。」

⭐ **主控判断（供实现单复核，⛔ 不当定论）**：这可能**不需要**回答 ——
腔多边形本身就是事实层产物，拿它定顺序**不是外部信息**。
`boundary_edges` 存在的理由是**逐边语义**（`boundary_condition` / basis），**不是形状**；形状腔自己就有。
⛔ 但这条要由实现单去证，**别在这里拍板**。

## 五、⇒ 下一步：立**实现单**（⛔ 不是再做实验）
1. 把 `derive_boundary_edges` 的角点改成**相邻支撑线求交**；
2. ⭐⭐ **三条非谈判项**：① 25 个健康腔**逐个不变**（4 顶点、面积逐位相同）
   ② 两个走廊腔 + 28.68 那个**都 valid 且面积对得上**
   ③ `interval_misses` 必须**继续为 0**，任何一条盖不满 ⇒ **响亮失败，⛔ 不许静默补线**；
3. ⚠️ **会改 `content_sha256` ⇒ 必须同时授权重做基线**（题错 #54 的教训：派生逻辑一改哈希必变）；
4. ⚠️ **验收⛔ 不许再用「边数/loss 条数」当判据**（题错 #57）——
   判据必须是**环 valid + 面积对账**。
