# 嵌入式查看器

运行 `python3 build.py` 可从项目内的三份完整离线查看器重建 `sm25.html`、`voimatalo.html` 和 `voimatalo-input.html`。副本保留原 Three.js renderer、几何和内嵌 UV 贴图；构建只添加汇报用的小控件、统一背景和键盘转发。两份 BIM 的整体与分层显示均保留楼板、屋顶/顶面，不再隐藏 ceiling 面。

三页均可直接以 `file://` 打开。`?bare=1` 隐藏叠在画面上的小控件，适合封面；拖动、滚轮缩放继续由原 OrbitControls 处理。

键盘转发只发送 `ArrowLeft`、`ArrowRight`、`PageUp`、`PageDown`、`Home`、`End`、`F`、`O`（`F/O` 支持大小写），且焦点在输入/选择控件时不发送：`{type:'bim-slide-key', key:event.key}`。父页面应校验消息来源确为目标 iframe 的 `contentWindow`。
