# 嵌入查看器 QA（2026-09-11）

三份查看器均由 `showcase/2026-09-11-research-report/embeds/build.py` 从完整离线源页重建；没有改动源几何、UV 贴图或 Three renderer。

执行命令（每个 case 独立运行）：

```bash
python3 showcase/2026-09-11-research-report/embeds/build.py
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/qa_iframe.py sm25
```

浏览器为 Chromium，启动参数为 `--no-sandbox --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`。QA 父页和子页均以 `file://` 打开，iframe 真实尺寸如下。

| 页面 | iframe 尺寸 | 结果 |
| --- | --- | --- |
| 封面 Voimatalo BIM | 885 × 564 | `voimatalo.html?bare=1` 完整显示；拖动旋转、键盘转发均通过；无页面错误。 |
| 第 3 页原始贴图 | 418 × 197 | 原始 UV 贴图完整显示，旧信息面板已隐藏；拖动旋转、`bare=1`、键盘转发均通过；无页面错误。 |
| sm25 | 876 × 475 | 拖动旋转、默认分层 `0.26`、`bare=1`、键盘转发均通过；无页面错误。 |
| 第 6 页原始贴图 | 610 × 475 | 原始 UV 贴图完整显示，旧信息面板已隐藏；拖动旋转、`bare=1`、键盘转发均通过；无页面错误。 |
| Voimatalo BIM | 748 × 475 | 默认整体 `0`，点“分层”变为 `0.26`；两种状态均为完全不透明；拖动旋转、`bare=1`、键盘转发均通过；无页面错误。 |

截图均来自实际 iframe 内的 Three canvas：

- [sm25 分层](/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/sm25_layers.png)
- [Voimatalo 整体旋转](/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/voimatalo_rotated.png)
- [Voimatalo 分层](/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/voimatalo_layers.png)
- [第 6 页原始贴图旋转](/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/voimatalo-input-page6_rotated.png)
- [第 3 页原始贴图默认视角](/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-11_research_slides_revision/embeds/voimatalo-input-page3_initial.png)

测试脚本通过 iframe 的 `postMessage` 接收端确认 `ArrowRight`、小写 `f` 和 `o` 可到达父页，且默认键盘行为已取消；生成页面只监听并转发指定的八个键（`F/O` 同时支持大小写），输入、选择和可编辑元素获得焦点时不会转发。最终复测同时收集 `pageerror` 和浏览器 `console.error`，五个尺寸均为空。
