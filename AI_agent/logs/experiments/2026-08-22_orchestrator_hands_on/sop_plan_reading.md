# SOP 草稿 · 平面图识图（v0，2026-08-22 orchestrator 亲自跑通 sm25 1f+2f 后写成）

> **验收标准（作业设计 §五#2）**：一个弱模型能照着执行；**每一步都指向一个具体工具调用**；
> ⛔ 全文不得出现「仔细观察」「判断一下」「确认是否」这类不可执行的动词。
>
> ⭐ **这份 SOP 的核心主张**：整条流程里**只有第 2 步需要模型**（读印在图上的数字），
> 而且那一步的产物**立刻被第 3 步的算术验掉**。其余 8 步全是确定性代码。
> 本轮实测：第 2 步我（最强模型）就读错了一处，第 3 步当场拦下。

---

## 步骤表

| # | 做什么 | 调什么 | 通过判据（不满足就停，⛔ 不带着问题往下推） |
|---|---|---|---|
| **0** | **声明这张图的墨迹方言** | `plan_ink.dialect_report(img)` | `mode == "layered"` ⇒ 洞口极性可直接观测，继续。<br>`mode == "monochrome"` ⇒ **停下上报**：这张图没有门窗颜色图层，极性不可直接观测。<br>`families.other.pct_of_ink > 10` ⇒ **停下上报**：有一整类墨迹没被任何规则认领 |
| **1** | **找出每条尺寸链的基线与读取带** | `plan_ink.find_chain_baselines(masks["annotation"])` | 每个方向至少 1 条；⛔ 不手填带位置 |
| **2** | **逐链转录数字**（⭐ 唯一需要模型的一步）| 把该带 crop 放大后读，逐个 verbatim 记下，**保持顺序** | —— |
| **3** | **用算术验掉第 2 步**（⛔ 不通过不许往下）| `plan_ink.fit_chain(ticks, values)` 逐链 | ① `chain_closure_mm == 0`（Σ段 == 总长）<br>② `matched_px` 无 NaN（每个分划点都对上一个刻度）<br>③ `max_abs_residual_px <= 1.0`<br>任一不满足 ⇒ **回第 2 步重读该链**，⛔ 不许改数去凑闭合 |
| **4** | **定标定** | 取各链 `mm_per_px` | 跨轴相对偏差 ≤ 0.3%（`clean_vector_v1.calibration_max_axis_relative_deviation`）。超了 ⇒ 停下上报 |
| **5** | **找墙面线并配成墙带** | `plan_ink.face_lines(structure_mask, axis=…)`<br>→ `plan_ink.pair_bands(lines, thickness_px=图纸自己的厚度 callout)` | 厚度候选**只能来自图纸上印的 callout**，⛔ 不许硬编码猜值。<br>未配上的面线全部进 `unpaired_face_lines` 台账，⛔ 不静默丢 |
| **6** | **逐墙带扫洞口** | `scan_band` → `classify_doors` → `absorb_slivers` → `snap_segments` | ① `assertions.tiles_range == true`（分段必须铺满整条墙，无缝无叠）<br>② 每个洞口两端记 `snapped: true/false`<br>③ `slivers` 台账非空时逐条看过 |
| **7** | **出笔画，代码做全部换算** | `assemble_reading.py <cfg.json>` | ① 每笔都有 `note`（**零笔无证据**）<br>② `dimension_derived` 的笔画 `dimension_refs` 必须解析得到真实 dimension id<br>③ 洞口坐标优先取链上毫米值（`chain_exact`），无刻度可依才 `pixel_fit` 并显式标注 |
| **8** | **离线自查**（不花钱、不用 gt）| `python scripts/tool_scripts/reading_process_metrics.py <run_dir>` | **零硬告警**。有告警 ⇒ 先修再继续 |
| **9** | **叠图人工过一眼 + gate①** | `plan_ink.render_overlay(...)` → `run_stage.py flow <case> <run> --to 0_reading --judge stop` | 叠图上每个红/黄框都压在图纸自己的洞口上；gate① 的每条 flag 逐条在 `reading_summary.md` 里给出解释 |

---

## 三条硬约束（⛔ 违反即整轮作废）

1. **⛔ 不许用「墙线的断口」反推洞口位置。** 本轮实测断口是噪声通道：同一堵墙上量出
   0.930 / 0.974 / 0.995 / 1.017 m 忽大忽小，且到处是 1 px 假断口。极性只能由**墨迹图层**判定。
2. **⛔ 不许「选一条路线走」。** 像素定「哪一段是洞口」，尺寸链定「边界精确在哪」，两者都要产出、由代码对账。
   只走链 = 07-08 丢一扇窗；只走像素 = 边界偏胖、锚点一错全错。
3. **⛔ 不许改转录数去凑闭合。** 闭合不上说明读错了，回去重读那条链。

## 一条软约束

**同一张图内基准必须唯一**（墙与洞口同一基准），并在 `reading_summary.md` 里写明是哪一个。
本轮用的是**墙中线**。（R-2：满分 reading 也犯过墙落中心线、窗落标称链位的混用，而判卷看不见。）

---

## 这份 SOP 覆盖不到的（⛔ 别假装它能）

- **立面图**：完全没试过，本轮只跑了两张平面。
- **无颜色图层的图纸**（sm20 那种 100% 灰度扫描件）：第 0 步会停下上报，之后没有替代路径。
- **墙厚**：第 5 步只用 callout 值做**配对判据**，产出的厚度仍是像素量的（本轮 2f 出现 0.131/0.146
  两个不存在的厚度）⇒ 厚度也该吸附到声明值，尚未做。
- **房间类型 / 分区**：本 SOP 不产出，也不该产出（那是 1_correction 的活，§3 红线）。
