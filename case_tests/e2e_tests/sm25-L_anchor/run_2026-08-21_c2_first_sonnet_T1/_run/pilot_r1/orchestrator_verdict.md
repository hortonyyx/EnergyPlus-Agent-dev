# Pilot 裁定 · sm25-L 1f × Sonnet 5（run_2026-08-21_c2_first_sonnet_T1）

> ⭐ **本文件在判卷之前写成并封存哈希**（2026-08-19 定的执行顺序纪律）。
> ⛔ orchestrator 写本文时**尚未运行 `score_reading_vs_gt`、尚未看到任何分数**。

## 0. 封存

| 项 | 值 |
|---|---|
| 读图产物 | `/tmp/ep_sm25_T1/out/1f_view.json` |
| **sha256** | `8b028d4d6c82f8d69fe192266b1061e62d045911da92ca515163b1ecf166ac89` |
| 大小 | 54853 字节 |
| 模型 | `claude-sonnet-5`，冷启隔离子代理，一次性会话 |
| 成本 | **$9.83**（对照：08-20 sm21 单张平面 $7.32；本图 14 区 Z 形，贵 34%）|
| 隔离 | 专用空 staging `/tmp/ep_sm25_T1`（仓库外）；**实测其中无任何 gt / DXF** |
| 能力档 | `orthogonal_polygon`（⚠️ 与 sm21 各臂的 `rectangular` 不同——本 run 是 C2 首考）|
| 档位 | 探索档（`guard_profile=observe`）· ⛔ 不作成绩 |
| directive | **无**（orchestrator 未写任何自由文本 directive，§1.5#7）|

## 1. 形态判定（只看过程与形式，不看正确性）

**✅ 通过。** 依据四条，均为产物内可查的事实：

1. **标定是自己量出来的，且与 orchestrator 的独立测量吻合**
   读图器 `px_m_calibrator` 锚点 = 列 `282.5` px / 行 `1233.75` px；
   orchestrator 今晚为写转换请求所做的**独立 RANSAC 标定**得外墙 SW 角 = 列 `281` / 行 `1235`
   ⇒ **相差约 1.5 px（≈30 mm）**。两条完全独立的路径量到同一个点。
2. **逐笔挂了两条独立来源**：笔画 `provenance=dimension_derived` + `dimension_refs` 指向尺寸链，
   `note` 里同时写出**像素测量对**（如 S1 的 `wall_line_profiler` 对 `px310.0/321.5`）。
   ⇒ 与 08-20 认定的 07-07 靶子签名（**两条独立来源逐笔对账**）同形。
3. **`scale_origin` 已声明且说明诚实**：note 明写「建筑周界并不经过该点，因为 footprint 被两处凹口切掉」
   —— 这是对 Z 形的**正确**描述，不是套话。
4. **`uncaptured` 装的是拒收台账不是漏画自白**（排除家具、记录被"愈合"的门洞位置），
   `self_check` 四项为真且 `unknowns_noted` 主动声明了一处**中等置信**（S16 只落在单线上）。
   ⇒ 符合 08-20 判据修正 #3。

**产出规模**：37 笔画（wall/window 两种笔）· 79 条尺寸转录 · 0 条 OCR。

## 2. ⛔ 本文**不**下的结论

- ⛔ 不说它"读对了"——那是判卷的事，本文写作时分数未知。
- ⛔ 不拿工具调用次数（crop_zoom 66 / wall_line_profiler 30）当路线判据
  （08-20 已明确：数 crop 次数是代理量，扰动实验才是判据）。

## 3. 放行决定

**批准该 pilot，放行 merge 与判卷。** 理由 = §1 四条形态判据全部满足，且无返工理由：
orchestrator 此刻**没有任何**「哪里画错了」的信息，因此**不存在**可以写进返工要求的内容。
