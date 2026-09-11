# 汇报 BIM 恢复楼板与顶面

删除展示构建中的 Ceiling 过滤；源 BIM 不改。sm25 与 Voimatalo 在整体和分层模式均保留楼板与顶面。两张模型静帧、封面/成果展示与 PDF 一并更新，其余页面安排和交互逻辑保持用户已认可的版本。

- `check_and_capture.py` / `report.json`：实际离线加载，源几何一致性、两种模式旋转、页面/控制台错误检查；刷新汇报的两个模型静帧。
- `sm25-{whole,layers}.png`、`voimatalo-{whole,layers}.png`：恢复后的实际模型。
- `slide-{01,05,06}.png`：直接嵌入的封面和两个成果页，已人工查看顶面恢复。
- `slides/`：复用上一轮截图脚本导出的七页与 PDF；报告核对图片加载、文字范围、外网请求与七页打印。交付 PDF 在汇报目录。

运行：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-11_bim_roofs_restore/check_and_capture.py
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-11_research_slides_revision/capture_slides.py --out ../2026-09-11_bim_roofs_restore/slides
```

两模型整体/分层旋转通过；页面错误、控制台错误、外网请求均为 0。sm25 保留 29 个 Floor 和 29 个 Ceiling，Voimatalo 保留 165 / 165；为源空间边界面数量，并非楼层数。未运行模型生成、仿真或产品全量测试。
