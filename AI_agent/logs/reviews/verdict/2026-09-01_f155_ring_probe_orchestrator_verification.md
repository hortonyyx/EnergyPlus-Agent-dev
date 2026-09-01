# F-155 判别实验 · **主控独立核验 + 裁定**

- **日期**：2026-09-01 · **施工方**：GPT 家族 · **核验方**：**Claude 家族 / orchestrator**
- **性质**：⭐ 这是**判别实验的读数核验**，⛔ **不是**实现的跨家族审 —— 实现单另立、另审。
- **产物**：[probe.py](../../experiments/2026-09-01_f155_ring_from_intersection/probe.py)（415 行）·
  [执行档](../execution/2026-09-01_f155_ring_probe_execution.md)

## 裁定：**实验成立，结论【部分】采信**（主控逐位复现）

> ⛔⛔ **2026-09-01 同日修正**：原写「结论采信」**过宽**。
> **采信**的是「求交重建修好了自交环」（形态 A，两个走廊腔）；
> **⛔ 已推翻**的是「28.68 那个也活了 ⇒ F-153『两个病别当一个修』被推翻」（§三.1）。
> **题错 #59（派工方）** ⇒ [裁定全档](2026-09-01_f156_stop_report_orchestrator_ruling.md)。

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

### 1 · ⛔⛔ **本节整段作废（2026-09-01 同日推翻，题错 #59，派工方）**

> ⛔ **下面这段是错的，保留原文只为留痕。裁定见**
> [`2026-09-01_f156_stop_report_orchestrator_ruling.md`](2026-09-01_f156_stop_report_orchestrator_ruling.md)**§一 / §三。**
>
> ~~**一次换表示，治好了 F-153 判定的【两个不同的病】**~~
> ~~F-153 当时的判别实验结论是「这其实是两个病，⛔ 别当一个修」：~~
> ~~形态 A（88.27 + 70.34）= 出口射线撞进垂直邻墙；形态 B（28.68）= 一堵墙 `along_min` 差 1 个单位（0.1 mm）。~~
> ~~**F-155 实测：28.68 那个也活了**（8 顶点、valid）⇒ 求交重建对 0.1 mm 端点错位免疫。~~
> ~~⇒ ⛔ **F-153 那条「两个病别当一个修」的结论，本轮被推翻**（它在旧表示下是对的）。~~

**⛔ 错在哪**：我拿 `alive=True` / `valid=True` / `vertices=8` 当成了「这个环是对的」——
**它们全是代理量**。本体是「**这个腔和答案里的房间是不是同一批房间**」。

**主控当日复量（命令直出）**：
```
REBUILT plan-F1 cavity:04e1293098b1a95a supports=8 vertices=8 valid=True
        area_m2=28.683212 source_symdiff_m2=0.000000 interval_misses=0
```
`source_symdiff_m2=0.000000` ⇒ **重建环与源腔逐点等价，它既没修也没坏那个 0.1 mm 错位。**
而源腔本身跨了**两个**答案 zone（`F1-z4` / `F1-z5`，从已落库的 `review/conversion_report.json` 直读；
`tests/test_o21d_exclusion_gap.py:55` 的注释亦写明 `hosts z4 AND z5`）
⇒ **一个事实腔 ↔ 两个答案 zone，环画得再好也配不上任何一个。**

**⭐ 仍然成立的那一半**（⛔ 别连这半也丢掉）：
换表示**确实**修好了**自交环**这个病 —— 两个走廊腔 88.27 / 70.34 重建后 valid、
`source_symdiff_m2=0.000000`、`interval_misses=0`。
⇒ [[representation-collapse-manufactures-unrelated-errors]] 在**形态 A 上**兑现；
**形态 B（0.1 mm 错位）不在其中，F-153「两个病别当一个修」依然成立。**

### 2 · **`interval_misses=0` ⇒ 答案本来就在事实层里，是推导过程把它扔了**
每个腔的每一段边界区间，**都在事实层墙带里找得到支撑线**（27 个腔全部 `interval_misses=0`），
且重建环与源腔**对称差 0.000000**。
⇒ `derive_boundary_edges` 是**从一份与源腔逐点等价的表示里造出了一个自交的环**。
⇒ ⭐ 这让**自交环**那个病的修法比原先估计的**轻得多**：不是要补数据，是要换角点的算法。

> ⚠️ **2026-09-01 同日收窄**（题错 #59 的连带修正）：原文这里写的是
> ~~「**腔多边形一直是对的**」~~ —— ⛔ **说得太宽**。
> `symdiff=0` 只证明**重建 == 源腔**，⛔ **不证明源腔 == 答案**。
> 实测反例：`cavity:04e1293098b1a95a` 的源腔跨了**两个**答案 zone（0.1 mm 缝没合上）
> ⇒ **那个腔的源腔本身就是错的**，而 `symdiff=0` 对此完全失明。
> ⇒ 本条只对**两个走廊腔 + 25 个健康腔**成立。

## 四、⚠️ 这个实验**没有**回答的（施工方诚实自报，主控确认）
> 「循环拓扑顺序仍取自事实层 cavity component；**尚未证明仅凭无序 supports 可以唯一恢复环序**。」

⭐ **主控判断（供实现单复核，⛔ 不当定论）**：这可能**不需要**回答 ——
腔多边形本身就是事实层产物，拿它定顺序**不是外部信息**。
`boundary_edges` 存在的理由是**逐边语义**（`boundary_condition` / basis），**不是形状**；形状腔自己就有。
⛔ 但这条要由实现单去证，**别在这里拍板**。

## 五、⇒ 下一步：立**实现单**（⛔ 不是再做实验）
1. 把 `derive_boundary_edges` 的角点改成**相邻支撑线求交**；
2. ⭐⭐ **三条非谈判项**：① 25 个健康腔**逐个不变**（4 顶点、面积逐位相同）
   ② 两个走廊腔 + 28.68 那个**都 valid 且面积对得上**（⛔ **2026-09-01 修正：这两个量都是代理量**，见 §三.1）
   ③ `interval_misses` 必须**继续为 0**，任何一条盖不满 ⇒ **响亮失败，⛔ 不许静默补线**；
3. ⚠️ **会改 `content_sha256` ⇒ 必须同时授权重做基线**（题错 #54 的教训：派生逻辑一改哈希必变）；
4. ⚠️ **验收⛔ 不许再用「边数/loss 条数」当判据**（题错 #57）——
   判据必须是**环 valid + 面积对账**。
