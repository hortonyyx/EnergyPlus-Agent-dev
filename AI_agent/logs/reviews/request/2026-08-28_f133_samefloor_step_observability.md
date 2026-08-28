# 派工单 · F-133：同层真实台阶被静默合并 —— **止血 + 记账 + 留夹具**

- **日期**：2026-08-28 · **派工方**：orchestrator · **施工**：Claude 执行档 · **审**：GLM 跨家族
- **档位**：工程档 · **基线**：`653d5f2`（分支 `08.23_AsDrawnReading`）
- **上位**：用户 2026-08-28 授权「按你的推荐统筹排工」；诊断全档 →
  [`logs/experiments/2026-08-28_wall_basis_jog/`](../../experiments/2026-08-28_wall_basis_jog/README.md)

---

## 〇、⛔ 先读

1. **本单只做三件：① 记账 ② 常量合一 ③ 夹具。**
   ⛔ **不许改任何合并/吸附的数值或策略**（`axis_jitter_tol_m` / `min_edge_length_m` /
   `structural_snap_grid_m` 一个都不动）。理由见 §三 —— **今天在 correction 这一层结构上分不开**，
   改了等于用一个说不清的规则替掉另一个。
   ⛔ 不做出模形式 · 不做事实层 · 不碰 `src/agent/judge/`。
2. ⛔ **绝对不许 `pip install -e .` / 任何写 `site-packages` 的命令**（venv 全机器共享）。
3. **停下上报分层**：**承重前提错 ⇒ 停下上报**；外围数值错 ⇒ 记一行继续。
4. ⚠️ **派工方累计题错 41 次**，且**本单题面我自己已经推翻过两版**（见 §五）。
   **请当成「题面可能又错了」来读。**

---

## 一、缺陷（已在**活入口**实测，⛔ 不是推理）

`apply_deterministic_core`（`pipeline.py` 真正调用的那个），单层楼、同一条墙线上的真实台阶：

| 输入台阶 | 输出 y 轴 | 结果 | `conflicts` |
|---|---|---|---|
| **120 mm**（形式 B 基准切换）| `[0.0, 6.0, 6.12, 10.0]` | ✅ 保住 | 0 |
| **60 mm**（240/120 一侧持平）| `[0.0, **6.03**, 10.0]` | ⛔ 合并，**两条线都挪到 6.03** | **0** |
| 30 mm | `[0.0, 6.02, 10.0]` | ⛔ 合并 | **0** |
| **10 mm**（200/180 一侧持平）| `[0.0, 6.0, 10.0]` | ⛔ 合并 | **0** |

⛔⛔ **`conflicts` 全程 0 条 —— 一次真实建筑事实被抹掉，产物上没有任何痕迹。**
**这就是本单要治的东西：不是合并本身，是【合并完全不可观测】。**

**复现脚本**（照抄即可，⛔ 不要改成 `_build_axis_map`，那是死代码）：

```python
from src.agent.correction.schema import CorrectedGeometry
from src.agent.correction.deterministic import apply_deterministic_core
s = 0.060
g = CorrectedGeometry(footprint_x=[0,10], footprint_y=[0,10], floors=[{
    "id":"F1","name":"1F","z_floor":0.0,"ceiling_height":3.0,"cells":[
      {"id":"A","role":"office","x":[0,4],"y":[0,6.0]},
      {"id":"B","role":"office","x":[4,10],"y":[0,6.0+s]},
      {"id":"C","role":"office","x":[0,4],"y":[6.0,10]},
      {"id":"D","role":"office","x":[4,10],"y":[6.0+s,10]}]}])
out = apply_deterministic_core(g)
```

### 两道杀，位置不同（都要覆盖）

| 台阶 | 被谁杀 | 位置 |
|---|---|---|
| **< 50 mm** | `_identity_clusters`（`axis_jitter_tol_m`）| [`deterministic.py:396`](../../../src/agent/correction/deterministic.py#L396) —— **per-floor 调用** |
| **50–100 mm** | `_reconcile_cross_floor` 的合并（`min_edge_length_m`）| [`deterministic.py:602`](../../../src/agent/correction/deterministic.py#L602) |

---

## 二、要做什么（三件，各自可独立验收）

### R1 · ⭐ 同层合并必须**响亮记账**

**每一次把同一层内两条不同的轴合并成一条**，都要在产物里留下**可定位的一条记录**：
两条原值 · 合并后的值 · 各自挪了多少 · 哪一层 · 哪个轴 · 由哪一步造成（聚类 / 跨层 reconcile 合并）。

⭐ **两处都要覆盖**（`_identity_clusters` 的同层聚类 **和** `_reconcile_cross_floor` 的合并）——
⛔ 只覆盖后者会漏掉 <50 mm 那一整段。

**放哪里由你定**（`corrections` / `conflicts` / 一个新的 audit 列表），但必须满足：
- **可定位**：能指出是哪一层、哪个轴、哪两个原值 —— ⛔ 不许只给计数（[[absence-conflates-causes-in-observables]]）
- ⛔ **不改变几何输出**：加记账前后，产物的坐标必须**逐位相同**。**请贴前后对照。**

⚠️ **判别问题**：「同一层内的两条轴」怎么算？—— 用 `_AxisNode.floor` / `support_by_floor` 判，
仓库已有这两样东西。**跨层合并（本来就是这个参数的立意）⛔ 不要记账**，否则清单会被噪声淹没。

### R2 · `_MIN_EDGE` 与 `min_edge_length_m` 合一（⛔ 值不变）

同一个数今天有**两处独立声明**，且**同一个 `cell_polygon` 被两条路以两个独立常量调用**：

| 声明 | 消费者 |
|---|---|
| [`modelling.py:34`](../../../src/agent/geometry/modelling.py#L34) `_MIN_EDGE = 0.10` | `modelling.py:219` `cell_polygon` · `modelling.py:268` `_iter_segments` |
| [`correction.yaml:61`](../../../src/configs/correction.yaml#L61) `min_edge_length_m: 0.100` | `pipeline.py:598` `validate_cell_polygon` · `envelope_transform.py:640` · 轴合并 |

⇒ **让 `modelling._MIN_EDGE` 从 `CoreTolerances` 取值**（或反向，你判断哪个方向更干净），
**⛔ 值保持 0.100 不变** ⇒ **全仓行为必须逐位不变**。

⚠️ **一处语义挪用要在 docstring 里点名、⛔ 本单不改**：
[`envelope_transform.py:814`](../../../src/agent/correction/envelope_transform.py#L814) 拿 `min_edge_length_m`
当**窗宽/窗高**下限 —— 那是另一种量（[[proxy-mistaken-for-the-thing]]）。
⇒ 只加一行注释说明「此处复用的是数值不是语义，改动 `min_edge_length_m` 会顺带改窗的准入」。

### R3 · ⭐ 夹具：把**当前行为**钉死，并写明它是缺陷的固化

新增一组同层台阶夹具（**120 / 60 / 30 / 10 mm 各一**），断言**今天的实际输出**
（120 保住 · 其余被并到具体的值），并在 docstring 里**逐字写明**：

> ⛔ 本夹具锁的是**当前（有缺陷的）行为**，不是期望行为。
> 期望行为 = 60 mm 的真实台阶原样出来；做不到的原因是 correction 手上没有墙厚
> （R-6 / ②-2）。**②-2 落地时，这组夹具的期望值必须被改成"保住"**，
> 改不动就说明 ②-2 没真的解决问题。

⭐ **同时断言 R1 的记账在这四档上都产出了记录**（120 那档产 0 条 —— 它没被合并）。

---

## 三、⛔ 为什么本单**不**修合并策略（承重前提，请先证伪）

「同层的真实台阶」与「模型自己的抖动」，**在 correction 这一层结构上分不开**：

- correction 手上只有坐标，**没有墙、没有厚度** —— 实测 `correction_geometry.json` 里
  `thickness` / `wall_thickness` / `basis` **各出现 0 次**
- 实测模型自身抖动量级 = **5–10 mm**（sm25 R0 的 80 个坐标里 **30 个**偏 5–10 mm）
- 而 200/180 墙的真实台阶 = **10 mm** —— **同一个数**

⇒ 任何以「多大」为判据的规则在这里都是抛硬币。**分得开的前提是厚度活到这一层（R-6，归 ②-2）。**

⭐ **若你能找到一条【今天就成立】的结构判据把两者分开 ⇒ 停下上报**，那比本单值钱得多。
⛔ 但**不要**用「相邻房间共享边界」之类的推断直接改代码 —— 先上报，让我方与复核方过一遍。

---

## 四、验收（⛔ 每条都要能不通过）

1. ⭐ **几何逐位不变**：R1 加记账、R2 合一常量之后，
   拿 `case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/1_correction/correction_geometry.json`
   跑 `apply_deterministic_core`，**输出坐标与改动前逐位相同**。**贴前后两组原文对照。**
2. ⭐⭐ **记账有牙**：§一 那个 60 mm 复现脚本，改动后必须**产出至少一条可定位记录**；
   ⛔ 且必须证明**不加这处改动它本来是 0 条**（贴两次读数）。
3. ⭐ **两处都覆盖**：10 mm 那档（走 `_identity_clusters`）也必须产出记录 ——
   ⛔ 只在 60 mm 上验过不算（那只走了 `_reconcile_cross_floor`）。
4. **反空转**：给出「不加 R2 时会放过什么」的实测（例如改 `_MIN_EDGE` 而 yaml 未改 ⇒ 两条路读数不一致）。
5. **全量** `pytest -n 6`（⛔ 无 `-m`、⛔ 不用 `-n auto`）+ **`.pth` 前后哨兵**（跑前跑后各记一次 editable
   装机文件哈希，两次相同才算数）。**贴汇总行原文。** 基线 = `653d5f2` 上的读数，请自行先跑一次记下。
6. **范围**：贴 `git diff --numstat` 原文。
7. ⚠️ **若有既存锁因 R2 变红** ⇒ **逐把说明理由**，⛔ **不许为了让全量绿而删锁或放宽断言**。

---

## 五、⚠️ 我方已经错过两版，请主动证伪

1. ⛔ **第一版我拿 `_build_axis_map` 当证据** —— 事后 `grep -rn "_build_axis_map" src/ tests/ scripts/`
   实测**零调用，是死代码**。本单所有读数已换到活入口 `apply_deterministic_core`。
   ⇒ **请你自己再 `grep` 一遍确认**：你要改的每一处，**都在真实调用链上**。
2. ⛔ **第二版我把两件事混成一件** —— 「`_MIN_EDGE` 对齐 EnergyPlus 的 10 mm」。
   实际是两个独立的东西：几何内核的 `_MIN_EDGE`（管多边形边/面段，参照 EP 合理）
   与 correction 的轴合并参数（管坐标身份，参照 EP **不合理**）。
   ⇒ **本单一个数都不改**，把「对齐 EP」留给内核那条线单独排。
3. ⚠️ **`_same_floor_sliver_conflict` 我判它「方向反了」**（名字说同层细缝就冲突，
   实现是同层两值相距 **≥100 mm** 才冲突 ⇒ 对 60 mm 返回 False）。
   ⇒ **这是我的判读，可能错**。⛔ **本单不要改它**；若你认为我读错了，**停下上报**。
4. ⚠️ **「几何逐位不变」这条我没实测过** —— 它是我对「只加记账不改行为」的预期。
   若你实现完发现坐标变了 ⇒ **承重前提错，停下上报**。
