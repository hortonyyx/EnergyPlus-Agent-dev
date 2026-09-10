# 部分推理产物：离线浏览器验证

已实际打开 Voimatalo 完整 UV 贴图页、sm24 简化源 BIM 页和逐立面交付页。最终有效记录为 [run03/report.json](run03/report.json)：Chromium 151.0.7922.34 / Playwright 1.62.0，1400×1000，离线运行，没有网络请求、加载失败或页面脚本异常。两份三维页均实际拖动旋转，已打开前后截图确认视角变化。

- [真实楼体初始图](run03/voimatalo.png) 与 [旋转图](run03/voimatalo_rotated.png)：12,520三角面/8,242顶点，8192×4096 UV 图集实际加载。窗带和屋顶纹理可见；未证明每个像素与原图相同，也未验证裁剪表面完整性或 BIM 生成。原输入网格不闭合，边缘有缺口。
- [简化 BIM](run03/sm24_partial.png) 与 [旋转图](run03/sm24_partial_rotated.png)：一个整层空间和外部开口可显示。保存页的默认长假设面板遮住部分模型，先通过正常折叠控件收起后查看；[初始界面](run03/sm24_partial_initial.png) 留存这一限制，没有改写实验原查看页。
- [交付页截图](run03/sm24_delivery.png)：逐立面范围表实际显示，窗/门各面有引用，空的西面门也有记录。该页对供给观察一致的显示不替代独立评价，仍须结合 [run02的窗位错误](../2026-09-10_partial_inference_sm24_run02/README.md)。

首次浏览器启动因缺 `libglib-2.0.so.0` 失败，补齐系统运行库后可启动。第一次脚本运行 [run01](run01/report.json) 的 sm24 拖动落在展开的说明面板上，发生文字选中，不能据其截图差异宣称旋转成功。改进脚本为折叠说明、确认起止点命中canvas后再拖动，保存新run03，不覆盖原记录。真实楼体在各次运行均正常旋转。run02在折叠面板时因动态定位索引变化而超时，见 [失败说明](run02/failure.json)；修正脚本逐个收起面板后，run03完整通过。

验证环境位于 `/tmp/ep-bim-browser-qa`，浏览器位于该目录的 `browsers/`，没有改项目Python依赖或共享 editable 安装。系统补装Chromium运行库与字体，无已有包升级/移除。

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-10_parallel_modelling_browser_qa/inspect_viewers.py \
  --out /tmp/parallel-modelling-browser-recheck
```

输出目录必须不存在。脚本校验HTML哈希、离线请求/错误、贴图状态、canvas命中/变化及立面表，再由开发助手看截图确认实际形态；此处仅验证查看能力，非建筑还原精度、原图门窗保真或真实内部布局。
