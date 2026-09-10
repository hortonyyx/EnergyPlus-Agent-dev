# 七页 HTML 汇报制作与查看证据

交付：[slides](../../../../showcase/2026-09-11-research-report/index.html)。本目录记录静帧采集、浏览器检查及最终排版；不包含新产品 Agent 或仿真运行。

| 文件 | 范围 |
|---|---|
| `assets_capture/capture_assets.py`、`capture_report.json` | Terra 子助手从三份现有离线查看器取初版静帧，隐藏 HTML 控件 |
| `assets_capture/candidate_*.png` | 原始候选，仍保留网格与坐标基准，不是最终 slides 所用静帧 |
| `clean_stills.py`、`clean_stills_report.json` | 主助手在临时 HTML 副本中仅暴露截图用 scene/root，隐藏显示辅助物，设统一浅底；sm25 展开楼层、隐藏顶面。最终 PNG 在 slides 的 `assets/` |
| `navigation_qa.py`、`navigation_qa/report.json` | file:// 1440×900、1920×1080 导航与真实 iframe 交互；另测本地 HTTP 的 iframe Esc |
| `capture_slides.py`、`layout_qa/slide-*.png`、`layout_qa/report.json` | 最终七页实际浏览器截图、主要文字边界、图片加载检查 |
| `layout_qa/research-report.pdf` | 最终浏览器打印的七页 PDF，原字节复制到汇报目录作为备用 |

运行环境：`PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python <script>`；截图静帧与交互检查使用 SwiftShader。排版/素材检查无外网依赖。三份原始查看器、源 JSON 与产品代码未改。

导航检查覆盖左右/数字/Home/End、#1–#7、目录选择与焦点、三个演示按钮、sm25 与 Voimatalo 旋转/楼层/展开、Voimatalo 三版切换与返回原页。控制台错误、失败请求与外网请求为空。

主助手人工核对全部七页；已修正第 3、7 页底部留白，sm25 改成能看见内部的楼层展开静帧。最后只改排版与 PNG，没有改已验证的导航逻辑。PDF 对象页数 7、MediaBox 为 1152×648 pt；没有把静态 PDF 当成交互演示。
