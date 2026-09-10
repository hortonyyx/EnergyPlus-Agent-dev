# sm25 汇报展示副本（2026-09-10）

## 目的与范围

为 09-11 课题汇报制作一份可嵌入 HTML 的离线三维展示，不改动产品代码、原始图纸、GT 或 `2026-09-09_source_bim_run04` 的历史成果。展示入口是：

- `showcase/2026-09-11-research-report/demos/sm25/sm25_showcase.html`

查看器可旋转/缩放，按楼层单独查看，并可按楼层或空间分层展开；所有资源已内嵌，适合本地打开或嵌入 slides。

## 来源与演示修订

起点为 `2026-09-09_source_bim_run04/sm25/source_model.json`，原结果为 **29 空间、31 窗、29 门**。该源模型的 `plan_opening_completeness` 仍失败：二层 `L029g3`、`L030g2` 两组门扇观察未建，原因是它们跨越当前多个空间边界片；原始源模型的几何检查仍为 `severe`。

展示副本只做一项人工辅助：二层局部原图显示的是一樘门；`L029g3`（墙一侧面）和 `L030g2`（另一侧面）是同一门洞的两次观察。两者区间重叠 0.8067 m，且此交集完整位于 `2f-c000 ↔ 2f-c006` 的既有共墙内。展示副本以这个交集增加一樘两空间门，并在两侧宿主面实际扣洞。展示结果为 **29 空间、31 窗、30 门**。没有遗漏既有 31 扇窗或原有 29 樘门；窗和门均由确定性显示投影切除宿主墙面，而非贴在实墙上的色块。

这项修订是为了说明可查看 BIM 的展示能力，不是自动还原成绩。门高 2.10 m 沿用该案例既有室内门约定，也不是本次新增量测。展示副本仍保留原始 `unsupported` 两项和 `validation.status = severe`，不会把这个局部辅助修订写成生产验证通过。完整说明写在展示目录的 README 和 `showcase_model.json` 的 `showcase_metadata` 中。

## 构建与核验

`showcase/.../build_showcase.py` 从原始源模型重新生成展示 JSON 和 HTML，复用了既有的确定性 `source_view_geometry` 与离线查看器，不修改其实现。构建前会验证：两空间/两宿主、互为共墙、门洞顶点完整落在两面内、不和已有开口重叠；重建显示投影后再核对两个 partner 互指，并对比修订前后两侧墙面面积，均实际减少门洞面积 1.69407 m²。

离线浏览器核验命令：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-10_showcase_sm25/qa/inspect_showcase.py
```

结果见 [`qa/report.json`](qa/report.json)：29 zones、31 windows、61 源开口（其中 30 门）；人工门保留两条来源、投影到两面宿主墙且 partner 互指，浏览器再次读取构建时面积扣洞证明。画布拖拽改变像素，F2 过滤和 0.46 的按楼层/按空间分层展开均通过；`page_errors`、`failed_requests`、`external_requests` 均为空。此前三宿主的错误 QA 保留在 [`qa/previous_triple_host_report.json`](qa/previous_triple_host_report.json)。

截图：`qa/initial.png`、`qa/rotated.png`、`qa/floor_2.png`、`qa/exploded.png`、`qa/zones_exploded.png`。这些只验证离线显示和交互，不评价原图保真、自动生成能力或下游 EnergyPlus 可用性。
