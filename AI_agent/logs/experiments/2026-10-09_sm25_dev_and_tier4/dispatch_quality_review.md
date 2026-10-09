# sm25 手动调度第二轮：初始与最终质量复核

2026-10-09，独立事后评价。Run：`AI_agent/archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1`。最终交付为 `bim/candidate_10`，选择记录与源模型内部内容指纹一致：`8358d52e89fbe2848ccdfe4a3de1f1857a2bc65ccdd20a5e0f86a70a23b49119`。

最终几何未发现漏房间、误拆误并、漏门窗、挂错墙、连通错误或室外凹入假楼板；当前剩余偏差均在用户 5／10／30 cm 汇报口径可接受范围内。但这是 root 目视发现问题并退回 reader 后的辅助完成结果，不能表述为模型自主发现并修复全部问题。

## 同一评价器：介入前基线与辅助后交付

`candidate_05` 是明确指定的介入前基线，不是最终交付，也不是“run 未交付”。初始评价 `summary.json` 的 `candidate_origin` 自动写成 `chosen by the evaluator (run did not deliver)`，属于评价脚本文案不适用于本次显式历史候选选择；原记录保留，本报告作此纠正。

使用同一 `scripts/dev/evaluate_run.py`，初始输出隔离至 `dev_evaluation_initial`；最终结果使用 root 已生成的 `dev_evaluation`。首次裸 Python 缺依赖、虚拟环境默认 GBK 解码失败，改用 `.venv/Scripts/python.exe -X utf8` 后成功，未安装依赖或修改代码。成功评价执行了 run 输入、全部候选源模型、delivery 与 GT 的前后哈希不变断言。评价 API 请求为 0。

| 指标 | 初始 candidate_05 | 最终 candidate_10 |
|---|---:|---:|
| 参考／候选／匹配空间 | 29／29／29 | 29／29／29 |
| 门窗匹配／参考总数 | 60／61 | 61／61 |
| 宿主匹配 | 60 | 61 |
| 门连接匹配／参考总数 | 29／30 | 30／30 |
| 原 evaluator 位置通过数 | 57／60 已匹配 | 58／61 |
| 外墙开口高度：匹配／通过／预期 | 33／32／34 | 34／34／34 |
| 门窗沿墙分档：≤5／5–10／10–30／>30 cm | 56／4／0／0 | 57／4／0／0 |
| 房间边界同口径分档 | 20／2／7／0 | 20／2／7／0 |
| 外墙开口高度同口径分档 | 32／0／1／0 | 34／0／0／0 |
| 超过参考墙线 30 cm 的门窗 | 0 | 0 |
| 实质库存缺陷 | 漏西侧外门 DX_WS | 未发现 |

分档只统计已匹配对象：初始少掉的门不会进入沿墙或高度偏差分档，不能因所有已匹配对象偏差较小就判初始完整。

初始具体缺陷与修复：

1. 一层西侧靠南的外门 `DX_WS` 缺失。初始平面与西立面回叠在原图门的位置没有候选门；最终新增 `F1:D15`，位于 `x=5 m`、沿墙 `y=4.302703–5.102703 m`，高度 `z=0.2–2.3 m`，恢复走廊到室外的第三个出口。漏门属于实质错误，不能用精度分档放宽。
2. 东侧外门 `F1:D14` 初始为 `z=0–2.1 m`，原图／参考为约 `0.2–2.3 m`，整体低约 20 cm；初始东立面回叠可见门底被放到地面线。最终改为 `0.19–2.3 m`，最大高度偏差降至约 1.00 cm。数值上初始落在 10–30 cm 可接受档，但过程上原图已显示的门底间隙被“接地”解释覆盖，仍应保留为读取与证据使用问题。

根据 root 本轮审阅记录，这两项由 root 目视发现并退回 reader 后修复；本复核确认的是改前／改后的产物差异，不把修复归功于自主闭环。

## 为什么最终仍有 3 个 position_match=false

原始独立图面库存 evaluator 的位置条件是两项同时满足：沿墙最大端点偏差 ≤10 cm，且横向偏差在内墙 ≤8 cm／外墙 ≤16 cm。三项均因内墙横向阈值未通过，与沿墙分档没有矛盾。

| 候选门／参考门 | 所在位置 | 沿墙最大端点偏差 | 横向偏差 | 宿主／连通 |
|---|---|---:|---:|---|
| F1:D10／DW1 | 一层西侧上方办公室到走廊 | 2.162 cm | 13.671 cm | 均正确 |
| F1:D11／DW2 | 一层西侧下方办公室到走廊 | 约 0 cm | 13.671 cm | 均正确 |
| F2:D-M／DW | 二层西侧大会议室到走廊 | 6.543 cm | 14.585 cm | 均正确 |

三樘门及其候选宿主墙均位于 `x=9.09 m`；参考代表线分别约为 `x=8.953287 m`（F1）与 `x=8.944154 m`（F2）。这是整条隔墙代表位置的偏差，门本身没有脱离候选宿主墙。原始 `opening_position_host_or_connection_changed` 代码把三类问题合并命名，不能据名称误报挂错墙或连通改变。

按当前口径保留该偏差，不把 13–15 cm 位移升格为实质失败；同时不声称严格位置全部通过。最终门窗沿墙最大误差约 8.73 cm，房间边界最大 Hausdorff 偏差约 15.01 cm。原始 2 cm 分区 `severe` 仅作诊断：最终为 22 条 `partition_boundary_changed`、7 条 `space_geometry_within_tolerance`；不把平行错位所产生的长段 missing/extra 解释为实际漏墙／多墙。

## 凹入、空间与立面独立复核

已查看本 run 六张原始 PNG、最终两层平面、最终全部六张回叠，以及初始两层平面回叠和东／西立面回叠。北立面 8 窗、南立面 7 窗、东立面 12 窗与 1 门、西立面 4 窗与 2 门在最终结果中完整，大小窗与非等距东窗的排布未见实质差异。

两个室外凹入分别位于西侧约 `x=0–5 m, y=0–14 m` 和东侧约 `x=15–25 m, y=6–20 m`。分别采用每个候选自己的精确轮廓折点划定室外区，独立计算如下：

- 初始与最终的 F1、F2 空间并集均为 290 m²，均与各自楼层 footprint 完全相等；空间无重叠（最终 F2 浮点面积差约 6e-14 m²，数值零），所有空间多边形有效。
- 初始与最终两层的空间、源模型楼板／天花板、`display_geometry` 楼板／天花板，其平面投影与两处凹入区域的面积交集全部为 0。此结果与平面可视检查一致，未发现室外凹入被假楼板或假天花板填平。
- 所有非交通空间都有门连接该层交通空间。最终 F1 为 13 个室内连接加 3 个外门；F2 为 14 个室内连接。各房间／交通区分隔与原图一致，未发现误并、误拆或错连。

## 质量边界

- 最终源模型及 viewer 继承的 assumptions 仍含“层高 3.0 m”“窗台 0.9 m”等早期默认值；实际两个楼层高度均为 3.6 m，最终外墙开口高度数据通过 34/34。应作为陈旧说明／来源展示问题记录，不能据旧文字认定最终几何仍是 3.0 m，也不能让使用者误以为旧说明已撤销。
- 空间用途是推断，未纳入这些几何与开口通过数。例如二层北侧沙发房 `F2:S-C` 被标为 `office/enclosed`，F1 整个交通区被标为 `lobby`；这些名称不能当作已核验的功能标签或能耗负荷分类。几何通过不等于语义用途通过。
- 室内门高与开闭状态、图中未给出的垂直交通、热工属性及 EnergyPlus 求解器兼容性不在本次验收范围。本复核未重复浏览器三维操作；root 报告的 Chromium viewer 验收应独立保留。

## 可复核产物

- [初始评价汇总](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation_initial/summary.json)、[最终评价汇总](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/summary.json)。
- [初始逐项质量报告](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation_initial/evaluation/candidate_05_delivery_quality.json)、[最终逐项质量报告](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/evaluation/candidate_10_delivery_quality.json)。
- [初始西立面：漏门](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation_initial/overlays/elevation_West.png)、[最终西立面](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/overlays/elevation_West.png)、[初始东立面：门高下移](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation_initial/overlays/elevation_East.png)、[最终东立面](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/overlays/elevation_East.png)。
- [最终 F1 平面](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/display/plan_F1.png)、[最终 F2 平面](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/display/plan_F2.png)、[全部回叠索引](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/overlays/index.json)。

本次仅写隔离评价产物与本报告；没有网络／模型 API 调用，没有继续生成，没有修改任何候选、delivery、GT 或生产源代码。
