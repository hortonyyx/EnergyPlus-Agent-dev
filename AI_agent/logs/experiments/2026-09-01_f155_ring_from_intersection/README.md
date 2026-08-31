# F-155 支撑线求交判别实验

运行：

```bash
python AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection/probe.py
```

`probe.py` 有两个互相独立的读数：

1. `F154_ENDPOINT_CONTROL` 在内存中临时替换事实层的 owner/classifier，按重新实现的
   精确端头判据复现旧的端点拼接环；`finally` 会恢复两个 callable，不写生产树。
2. `SUPPORT_INTERSECTION_EXPERIMENT` 从事实层的 wall/opening/footprint 生成有限支撑线
   目录。腔 polygon 只给循环拓扑次序；每条入选线的 `axis/const/interval` 必须被目录
   完整覆盖，角点一律由相邻异轴支撑线求交产生。

主读数：F1/F2 两个走廊腔分别为 24/16 顶点，均 `Valid Geometry`，与事实源腔的
对称差均为 0；25 个既有健康腔仍全部为 4 顶点 valid；28.68 m² 的 0.1 mm 错位腔
也能重建为 8 顶点 valid 环。

