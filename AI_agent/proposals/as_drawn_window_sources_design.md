> **技术参考 / 非当前管理入口（2026-09-08）**：保留既有技术细节供按需复用；正文的历史状态、模型席位、审批/全量要求和旧批次“必须”不自动生效。开发按 [AGENTS.md](../../AGENTS.md)，进度按 [当前计划](../plan.md)；实施事实需对照当前源码和产物。

# 设计稿 · as_drawn 腿的窗（迁移到既有契约，⛔ 不新建机制）

> **起因**：用户 2026-09-08「先补窗，得跑出来一个完整的，别跑缺胳膊少腿的」＋「这部分 Claude 来修」。
> **前置认知更正**（用户两次纠正主控）：
> ① 立面「直接匹配、脱离四立面/正南正北」**早已立项 = C2.1**（`proposals/c2_1_facade_matching_plan.md`）；
> ② 立面的**前后纵深拆分 C2 已经解决**，本批**是迁移不是新建**。

## 〇 · 现状（实测，⛔ 非转引）

`projection_bridge.py:920` 是一句硬写的 `windows=[]` ⇒ **新腿产出一栋没有窗的楼**。
平面 85/87 个洞口候选**只用来切墙**（变成 `CutLineV1`），一个都没成为窗。
⇒ gt 有洞口而模型没有 ⇒ 洞口通道零分；能耗上无窗围护结构没有物理意义。

## 一 ⭐ · C2 已经给的（⛔ 全部复用，不重写）

| 能力 | 载体 | 实测证据 |
|---|---|---|
| 立面按**深度**拆成多个墙面 | `facade_visibility`（Vg）`_compute_depth` + 1D skyline | sm25 上 **16 段 = 8 墙面 × 2 层**，depth 0/10.006/5.008/14.000/14.005 与足迹逐个吻合 |
| 「这个沿面位置属于哪堵墙」 | `visible_intervals` | ⭐ **按构造是沿面轴的不重叠划分**（skyline 定义即「每处只有最近面可见」）⇒ 任意形状唯一可答 |
| 同深度歧义 | `_assert_no_depth_tie` → `visibility_same_depth_overlap` | 拒绝，⛔ 不猜 |
| 父墙歧义 | `modelling._find_parent_wall` → `ambiguous parent wall` | 拒绝 |
| 窗→段绑定 | `window_host.resolve_window_hosts`（`:1037` 写 `facade_segment_id`）| `opening_claim_score.py:60` 明写「**B5 remains the host resolver owner**」|
| 朝向符号与投影 | `facade_convention.FACADE_BASE_SIGN` + `project_affine_interval` | 四个符号与主控实测**逐条吻合**（east/south 原样、north/west 镜像）|

⇒ **深度、遮挡、绑段、歧义拒绝、朝向——一个都不用我写。**

## 二 ⭐⭐⭐ · 契约里的通道权限矩阵，与实测的「两边各有一半」完全吻合

`window_sources._claim_links:1016-1017`：

```python
plan      → existence, host, along, width
elevation → existence, along, width, sill, head, appearance
```

主控实测（`logs/experiments/2026-09-08c_window_investigation`）：
- 平面**有** `hypotheses.opening_types`（window/door/not_opening）与沿面 `span_m`，⛔ **无高度**
- 立面**有** `z_range_m`（= sill/head），⛔ **无门窗分类**（`ledger.door_window_classified: false`）

⇒ **`sill`/`head` 只准立面声称、`host` 只准平面声称** —— 契约把「谁能观测到什么」写死了，
与实测逐项对上。⇒ **窗必须带 provenance 同时引用两个通道**，⛔ 单通道造不出合法窗。

## 三 · 要做的三件事（⛔ 就这三件）

### S1 · as_drawn 的**窗源目录**（替换 T2-⑤ 的「合法空集」）

镜像 legacy `_catalog`，产 `tuple[SourceWindowV1, ...]`：
- **平面行** `PlanSourceWindowV1`：`observation_id` = `opening_candidates[].id`（如 `L001g0`）；
  `world_x/y_interval` 由该候选的 `face_line` 轴 + `span_m` 定；`floor_ref` 取 manifest；
  `positive_claims ⊆ {existence, host, along, width}`
- **立面行** `ElevationSourceWindowV1`：`observation_id` = `openings[].id`（如 `O01`）；
  `local_along_interval` = `x_range_m`、`local_z_interval` = `z_range_m`（⭐ **local，翻转留给下游**）；
  `positive_claims ⊆ {existence, along, width, sill, head}`

⇒ **这一步同时销掉 W#7**（`evidence_debt_coverage` 红的根因就是目录为空）
与 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER` 债。

### S2 · 造窗（确定性，⛔ 不是模型画的）

对每个立面洞口：
1. 沿面 local → world：`facade_convention.resolve_sign` + `project_affine_interval`，
   `W` 取**立面自己声明的** `calibration.x.overall_mm`（实测 east/west 20000、north/south 25000，闭合差全 0）
2. 楼层：`z_range_m` 对 ladder 定（实测四面**零跨层**）
3. 归属墙面：落进哪个 `facade_segment.visible_intervals` ⇒ **深度白送**
4. 类型：平面 `opening_types` 给 window/door
5. 产 `WindowV3(id, floor_id, facade, span, z)` + provenance（existence/along/width 引平面与立面、
   host 引平面、sill/head 引立面）

⛔ **停下上报触发器**：某个立面洞口落不进**唯一**一个 `visible_interval`，或在平面侧找不到唯一候选
⇒ **具名拒绝**，⛔ 不许挑最近的（C2.1 §118「刻意对称 → 必须 conflict 不许猜」同口径）。

### S3 · 接线

`finalize.py` 的 `finalize_as_drawn_chain_geometry`：**第 259 行**（`facade_segments` 填好）
与**第 261 行**（`resolve_window_hosts`）**之间**插入造窗；目录换成 S1 的真目录。
⇒ 之后 `resolve_window_hosts` / `apply_window_host_resolutions` **原样跑**，⛔ 不改。

## 四 · 实测已确认的输入（每一个都是**声明的**或**已有的**，⛔ 零发明常数）

| 量 | 来源 |
|---|---|
| 沿面全长 W | 立面 `calibration.x.overall_mm`（闭合差 0）|
| 朝向符号 | `FACADE_BASE_SIGN` |
| 投影公式 | `project_affine_interval` |
| 归属段/深度 | Vg `visible_intervals` |
| 高度 z | 立面 `openings[].z_range_m` |
| 楼层 | z vs ladder |
| 门/窗类型 | 平面 `hypotheses.opening_types` |

实测对应关系：**34 个立面洞口在正确朝向下 100% 匹配**（31 window + 3 door，1f/2f 各 17，
残差中位 18.4 mm、最大 53.6 mm）。

## 五 ⛔ · 本稿**不做**的

- ⛔ 不做 C2.1（几何绑侧替代命名）—— 本批仍用 manifest 声明的立面身份
- ⛔ 不动 Vg / `resolve_window_hosts` / `_find_parent_wall` 任何一行
- ⛔ 不改 legacy 腿
- ⚠️ **残余风险（登记，不修）**：立面若真是镜像画的/右→左，as_drawn 腿不察觉（只吃默认 flip）

## 六 · 尚未验的（⚠️ 主控**推的不是量的**）

1. **3 个 door 要不要进 `windows[]`** —— EnergyPlus 里外门也是 fenestration，但 legacy 腿怎么做没查
2. **`WindowV3.room`（cell id）怎么定** —— 洞口在墙上，两侧各有一个 cell
3. **`positive_claims` 的具体取值**要按 manifest `opening_evidence.potentially_observable_claims` 对齐
