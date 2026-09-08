# S3b probe 读数档 · corner-only 降维提升到「那一类」（2026-09-08）

> 施工 = GLM（W-1 收尾单 S3b）· 判据来自裁决 [`reviews/verdict/2026-09-07x_T2_3_ladder_ruling.md`](../../reviews/verdict/2026-09-07x_T2_3_ladder_ruling.md) §二
> 复跑：`cd /tmp/w1_flow_glm && PYTHONPATH=. python AI_agent/logs/experiments/2026-09-08a_w1_s3b_probe/run_probe.py`

## ① 降维读数（真链 T1 probe 产物，两层 32 cell 全量）

| | 降维前（存储字节） | 降维后（生产 helper） | 裁决书读数 |
|---|---|---|---|
| floor_1 最短 cell 边 | 1.62 cm | **111.93 cm** | 111.93 cm ✅ |
| floor_2 最短 cell 边 | 0.55 cm | **194.13 cm** | 194.13 cm ✅ |
| <5cm（gate① `_MIN_EXTENT`） | 16/16 · 16/16 | **0/16 · 0/16** | 0/16 ✅ |
| <10cm（finalize `min_edge`） | 16/16 · 16/16 | **0/16 · 0/16** | 0/16 ✅ |
| cell 顶点数 | 69/39/23/17… · 65/49/15… | 8/6/4/4… · 6/4/4/4… | 8/6/4/4/4… ✅ |

⚠️ 存储产物是 **S3 之前**的链产的（footprint 也还是 94 顶点、未被旧 `:892` 处理过），
所以 probe 对 footprint 和 cells **两族环都**过生产 helper —— 这正是提升后的
`partition_lines` 对同一链输入会输出的字节。

## ② 通路复驱（S3 CASE B 同一路径，降到角点后）

`snap(1f,2f) → assemble → build_verified_window_inputs_as_drawn → finalize → check_correction`：

- min-edge 红**清零**：footprint 环 94/86 顶点（最短边 2.16/0.55 cm）→ **8/8 角点
  （最短边 5.008/5.004 m）**——validate_final 报的那条 4.33 cm 边是共线细分，不是真角。
  ⭐ 两层环都是 **8 角点**（这对停报选项「把采纳环吸进 cells」的可行性是关键输入：
  角点数相等、对应边同轴 ⇒ 逐边正交映射机械可造）。
- gate① 新读数：`passed=False blocking=1`，红在 **`correction.coverage`（INVARIANT）**：
  floor `2f` hole **0.450054 m²** / outside **0.069450 m²** > `coverage_area_tol_m2` 0.05。
- （另一条 `evidence_debt_coverage` FAIL 是 advisory 非阻断，probe 未接生产债接线的形态，
  S4 mock 链测试同款，非第二堵墙。）

**归因（B 类停报，见交件 §停报）**：不是降维引入的。`snap_footprints_to_reference`
把 2f 的环**逐位换成** 1f 的环（共底面指纹比对要求逐位相同），而 2f 的 cells 保留
本层图纸坐标（snap 设计明文「Replacing the ring does NOT touch the floor's cells」，
理由是「schema 不查 cell∈footprint」）——但 gate① B3 覆盖守恒门**不是 schema**，
它用 shapely 量 cells 是否铺满**采纳环**。两把尺子互不知晓：snap 的声明界是
20.6 mm（顶点距离），coverage 的界是 0.05 m²（面积）；真实两层图纸 7–14 mm 的
每边独立残差 ⇒ 0.45 m² 洞，9× 超阈。S3b 清掉上一堵墙后这堵才第一次可见
（[[seed-bypass-exposes-hidden-downstream-blocker]]）。
