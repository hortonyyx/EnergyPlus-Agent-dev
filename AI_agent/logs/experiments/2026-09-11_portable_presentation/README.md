# 跨设备离线汇报包

用户要求一个可直接复制到其他设备的文件夹。交付 `showcase/BIM-Agent-Presentation/`，并附同名 ZIP；入口为目录里的 `index.html`。包含恢复楼板/顶面后的七页汇报、样式和导航、实际引用的图片、三份完整内嵌模型、七页 PDF、打开说明与素材/模型说明，共 21 个文件，目录约 24.3 MB、ZIP 约 19.2 MB。

页面、脚本、样式、模型、图片和 PDF 均从 `showcase/2026-09-11-research-report/` 原字节复制。资源按 `index.html` 的 `src` / `data-src` 相对引用收集，URL 去掉查询参数；补充两份独立 TXT 说明。没有复制历史实验、原始瓦片或生产环境，不需要仓库、服务器、账号或在线依赖。正常放映使用本地资产，点选外部来源/官网链接才需网络。

浏览器验证见 `check_portable.py` / `report.json`：将交付 ZIP 解压到仓库之外、含中文与空格的临时路径，逐字节核对全部文件后通过 `file://` 打开，在 HTTP/HTTPS 被拦截的条件下检查七页图片及全部 5 处模型的实际加载/旋转；同时监测是否读取包外文件。七页 PDF 页数核对；报告保存 ZIP 的 SHA-256。实际浏览器是离线 Chromium + SwiftShader，未宣称在用户其他设备实测。

结果通过：七页图片齐全、五处模型均可旋转，页面/控制台错误、失败请求、外网请求和包外文件读取均为 0，PDF 为 7 页。

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-11_portable_presentation/check_portable.py
```

后续汇报有改稿时，需要把同名页面、样式、脚本、引用图片、三份 embeds HTML 和 PDF 同步到交付目录，再从该目录重新压缩 ZIP；交付目录不通过符号链接依赖源项目。
