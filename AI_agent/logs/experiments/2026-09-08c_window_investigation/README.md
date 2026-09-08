# 补窗前的实测调查（2026-09-08，主控）

> **起因**：用户「先补窗，得跑出来一个完整的，别跑缺胳膊少腿的」＋「这部分 Claude 来修」。
> **前提**：`projection_bridge.py:920` 是一句硬写的 `windows=[]` ⇒ **新腿按设计产出一栋没有窗的楼**；
> 平面产物里 85/87 个洞口候选**只被用来切墙**（变成 `CutLineV1` 雕房间），一个都没变成窗。
> **树** = `/tmp/w1_windows_claude`（分支 `wt/09.08_windows`，⛔ 与 GLM 正在施工的树分开）。

## 1 · 两边各有对方没有的一半

| | 平面产物 `as_drawn_plan_v2` | 立面产物 `as_drawn_elevation_v0` |
|---|---|---|
| 沿面范围 | ✅ `opening_candidates[].span_m` | ✅ `openings[].x_range_m` |
| **高度（窗台/窗顶）** | ⛔ **没有** | ✅ **`z_range_m`** |
| **门/窗分类** | ✅ **`hypotheses.opening_types`**（`window`/`door`/`not_opening`）| ⛔ **没有**（`ledger.door_window_classified: false`）|
| 洞口总数 | 1f 85 · 2f 87（含大量内门）| east 13 · north 8 · south 7 · west 6 = **34** |

⇒ **必须配对**：立面给 z，平面给类型。⛔ 任一边单独都造不出一个合法的 `WindowV3`
（它要 `facade` + `span` + `z` + `floor_id`）。

## 2 ⭐⭐⭐ · 沿面坐标同源，**但每一面的朝向不同**（实测，唯一）

把每个立面洞口的 `x_range_m` 拿去平面的 window/door 候选里找最近的（判据：两端点误差和 < 100 mm）：

| 面 | 沿面全长 | **原样** | **镜像** |
|---|---|---|---|
| east | 20 m | **13/13** | 4/13 |
| north | 25 m | 0/8 | **8/8** |
| south | 25 m | **7/7** | 0/7 |
| west | 20 m | 3/6 | **6/6** |

⇒ **34 个立面洞口在正确朝向下全部匹配**，且每一面的朝向**唯一**（13vs4 · 0vs8 · 7vs0 · 3vs6，⛔ 没有模棱两可的）。
**East/South 原样，North/West 镜像** —— 从建筑外面看，+x 在南立面上是左→右、在北立面上是右→左，几何上本该如此。

### ⛔ 由此发现一个【补窗之前就得先修】的缺陷

as_drawn 腿现在把这个翻转**默认掉了**：
`window_sources.py` 的 `derive_manifest_direction_facts_as_drawn` 用
`_resolve_facade_flip_fields(None)` 的**无声明默认值**。
⇒ **North 和 West 的洞口会被静默放到墙的另一头。**

⭐ 但翻转是**可派生的**，⛔ 不是缺一个声明：manifest 里已经声明了
`building_view_direction`，翻转是「从外面看这一面」的**几何后果**。
⇒ 按 [[symmetric-evidence-cannot-prove-direction]]：**镜像一致 ≠ 无害**，必须逐面定向。

## 3 · 匹配上的 34 个：31 window + 3 door，1f/2f 各 17

残差：**最大 53.6 mm，中位 18.4 mm**（标定量级，与足迹侧 14.4 mm 同量级）。

## 4 ⚠️ · 我第一版匹配器的两个缺陷（如实登记，⛔ 别照抄）

1. **只按沿面范围找最近 ⇒ 会串层**：1f/2f 的窗常常上下对齐，9/34 匹配到了另一层。
   ⇒ **楼层必须先由立面的 `z_range_m` 对 ladder 定**，再在该层内匹配。
2. **没约束到外墙 ⇒ 匹配到内墙线**（east 匹配到 `pos_m=14.755` 的内部线）。
   ⇒ 必须先定「这一面的外墙面线」，再在其上匹配。

⇒ 正确的匹配键 = **（楼层 by z）×（该面的外墙）×（沿面范围）**，⛔ 不是单看沿面范围。

## 5 · 由此定下的设计方向

**窗必须是确定性推导的，⛔ 不是模型画的** —— 与本项目的杠杆一致
（[[reading-lever-is-measurement-enforcement]]：读图器只写像素锚点，代码做唯一换算）。

1. 每份立面：从 manifest 声明的 `building_view_direction` **派生**翻转（⛔ 不默认）
2. 洞口的 `z_range_m` → 对 ladder 定楼层（实测四面**零跨层**，干净）
3. 沿面范围 → 定位到该层该面的外墙面线上的洞口候选
4. 平面的 `opening_types` 给类型；立面的 `z_range_m` 给 `z=[sill, head]`
5. 组装 `WindowV3(id, floor_id, facade, span, z, room=含它的 cell)`

⛔ **尚未验的**（⚠️ 我是推的不是量的）：
- 3 个 door 要不要也进 `windows[]`（EnergyPlus 里外门也是 fenestration）—— 要看 legacy 腿怎么做
- `room`（cell id）怎么定：洞口在墙上，两侧各有一个 cell
