# 项目汇报逐页修订证据

交付：[HTML](../../../../showcase/2026-09-11-research-report/index.html)，配套说明及来源在汇报目录中。只修改展示；没有产品模型/仿真运行。

- `aerial_reference/README.md`：Harria 真实航拍原始链接、CC BY-SA 4.0、文件校验与拍摄信息。
- `embeds/`：精简查看器的实际 iframe 尺寸检查、旋转/控件/键盘转发截图与报告。可复现构建脚本在汇报的 `embeds/build.py`。
- `interaction_qa.py`、`interaction_qa/`：1440×900 / 1920×1080 整页交互，模型内翻页、目录、卸载/重载、六张图纸和统一输出名称等。
- `capture_slides.py`、`layout_qa/`：首次整页截图，已暴露原始贴图旧面板、显示背景等问题；保留为修订前记录。
- `layout_final/`：修正后的最终七页、图片/文字范围检查与七页静态 PDF。以最终截图为交付排版。
- `delivery_check.json`：六张图纸原字节校验、两份 BIM 几何一致性、本地链接、交付 PDF 页数与校验值。

脚本使用 `PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python`，离线 Chromium + SwiftShader。最终重新截图使用 `capture_slides.py --out layout_final`。中途显示封装的空 Scene.add 错误按新增缺陷修复，同范围主流程结果复用，变更部分单独复查；不是源错误的豁免。
