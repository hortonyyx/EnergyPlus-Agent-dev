# sm25：汇报用三维展示副本

打开 `sm25_showcase.html` 即可离线查看。它支持旋转、缩放、按楼层过滤、透明墙、剖切和按楼层/空间分层展开；HTML 已内嵌查看器与几何，不会请求网络资源。

展示基于 `AI_agent/logs/experiments/2026-09-09_source_bim_run04/sm25/source_model.json`：原始结果为 **29 个空间、31 扇窗、29 樘门**，并仍明确记录二层 `L029g3`、`L030g2` 两组门观察未建，源模型检查为 severe。

本副本的唯一人工修订是：重新核对二层局部原图后，把 `L029g3` 与 `L030g2` 识别为同一樘门在 120 mm 墙两侧面上的观察，而不是两扇门或一樘跨三空间的门。取两侧观察区间的交集，得到 0.8067 m 的门洞；它完整落在既有 `2f-c000 ↔ 2f-c006` 共墙上，并在这两个宿主面实际扣洞、正确互为 partner。门高沿用该案例已建室内门的 2.10 m 约定，非新量测。

因此本页显示 **29 个空间、31 扇窗、30 樘门**。原始 `unsupported` 和 `validation.status = severe` 在展示副本中仍保留；本页只能用于展示“原图到可查看轻量 BIM”的成果和查看交互，不能作为产品自动还原的成功成绩。原始输入、原实验、GT 与核心代码均未改写。

重建：

```bash
python showcase/2026-09-11-research-report/demos/sm25/build_showcase.py
```

生成的 `showcase_model.json` 保存演示模型和修订说明；`display_geometry.json` 是其显示投影；`manifest.json` 保存数目与来源校验。
