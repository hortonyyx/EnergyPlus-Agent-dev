# sm25-L gt 候选包 · 签字前须知（给用户）

> **状态**：候选包已产出，`G1–G5 · G7 · G8 · G9` 全绿、零 BLOCK 诊断。
> **G6 / G10 红是设计上就该人签的两道**（G6 = 近阈值面待人工确认、G10 = 签字本身）。

## 一、签字要看什么

| 文件 | 看什么 |
|---|---|
| `review_bundle/gt/renders/overlay_1f_view.png` | 1F：**14 个分区**标注（`F1-z0…z13`）是否落在正确房间；红色外轮廓是否贴合 Z 形 |
| `review_bundle/gt/renders/overlay_plan-F2.png` | 2F：**15 个分区**（`F2-z0…z14`）同上 |
| `review_bundle/gt/renders/overlay_{North,South,East,West}_view.png` | 四立面：青色窗 / 橙色门是否与图上洞口重合，标注的标高区间是否合理 |
| `review_bundle/overlay_plan.svg` | 矢量版叠图（可放大看细节）|

**应有的数**：立面 **31 窗 + 3 门** = 西 4 窗 2 门 · 南 7 窗 · 北 8 窗 · 东 12 窗 1 门（东立面那樘是 1600 宽双开）。

## 二、⚠️ 签字时必须知道的三件事

### 1. 图纸被改过 5 条线（你 2026-08-21 授权）

`13AD` / `13AE` / `13AF` / `13AC` / `160A` —— 一堵 120 厚墙原本**偏离水平 5.808 mm**，
全 1F 仅此一处非正交；它被判不合格丢弃后两端墙悬空，1F 平面整个出不来。

- **修法**：吸附到**图纸自身已有的精确坐标**（同一墙接头处 `13AA`/`160C` 用的 `y=38213.464`），最大移动 **6.000 mm**
- **量级**：1F 图是 21.6 mm/像素 ⇒ **0.27 个像素**，识图器物理上看不出
- **⚠️ 后果**：**gt 与你给的六张图不再完全同源**，差 0.27 像素（判卷容差差着两个数量级，实务无影响）
- **原件保留**：`case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf`
- **已核实**：916 个图元一个不少 · 句柄集合完全相同 · 块定义 313 个不变 · **恰好那 5 条线变了坐标**

### 2. 房间数是**你**定的，不是量出来的

`testdata_prompt.json` 里你填的 **1F 14 / 2F 15**。转换器的腔体识别与它逐间对上
（2F：走廊 70.25 + 大会议 29.12 + 上部 3 + 下部 5 + 右列 5 = 15；面积账 255.31 + 34.69 = 290.00，差额 0.00）。
**若你签字时发现分区数不对，那是这个数要改，不是转换器错。**

### 3. `min_room_area_m2` 定为 **5.0**（sm24 是 2.0）

这是「多大的封闭区域才算房间」的领域参数。依据：**本楼最小真房间 6.84 m²、最大墙带面 4.93 m²**
⇒ 5.0 落在两者之间。⛔ 不是"调到能过为止"——2.0 时 4 块墙带被当成房间（19 ≠ 15）。

## 三、签完之后

```bash
python scripts/tool_scripts/gt_review_sign.py \
  AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle \
  --reviewer <你的名字> --signed-at <ISO 时间> --confirm-near-threshold

python scripts/tool_scripts/gt_review_rerun.py <同一目录>     # 带签名的强制第二次转换
python scripts/tool_scripts/gt_promote.py ...                # 晋升入 gt/
```

⚠️ `--confirm-near-threshold` 是必须的（G6 会列出近阈值的面让你确认）。
