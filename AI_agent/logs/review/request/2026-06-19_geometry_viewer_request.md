# Review request — 离线交互式 3D 几何检视器（backlog #3）

- **Date**: 2026-06-19
- **Branch**: 6.15_ValidationArchM0toM4
- **Reviewer**: Codex via MCP direct (danger-full-access, user-authorized; self-driven read + pytest)
- **Author**: Opus 4.8

## 背景
几何确认门（#1 已接成阻塞门）需要一个**真正的交互式 3D 检视**供人工确认几何后才继续。用户拍板：
①three.js **离线内嵌**（非 CDN）；②功能**全上**（orbit/半透明/截面/爆炸/量距/点选高亮/存PNG/按楼层·区·OBC 着色）；
③GLB 从主流程**剥离**（`render_building_3d.py` 工具保留，后续再启）。

## 改动范围（只审这批）
- **新增** `scripts/tool_scripts/render_geometry_viewer.py` — 从 `building_geometry.json` 生成**自包含离线**
  `geometry_viewer.html`：vendor 的 three.js + OrbitControls 内联、几何作 `window.GEO` 内嵌、app JS（全局 THREE）
  逐面建 mesh，控件含 颜色 by floor/zone/OBC、楼层隔离、墙体不透明度、窗/边/墙显隐、X/Y/Z 截面（启用+位置+翻转）、
  爆炸视图、量距（点选两点）、点选高亮区、存 PNG。
- **新增** `scripts/tool_scripts/vendor/{three.min.js, OrbitControls.js, README.md}` — three.js r0.137.5 UMD 全局构建
  （MIT），离线内嵌用。
- **改** `scripts/tool_scripts/run_stage.py` — 几何检查点（stage 2/3 过 gate①）调 `_render_geometry_viewer` 出 viewer；
  删了 `_render_stage` 里已失效的 2/3 GLB 分支（2/3 非 judge stage，原分支根本不会被调用）。
- **改** `scripts/tool_scripts/record_baseline.py` — 🔍 肉视清单第 3 项从 GLB 改为 `geometry_viewer.html`。
- **改** `AI_agent/guides/new_case_guide.md §2 S2+S3` — 写明 viewer + 阻塞确认门。
- **新增** `tests/test_geometry_viewer.py`（5 测，含 node --check app JS）。

## 关注点（请重点审）
1. **离线自包含正确性**：HTML 是否真无任何外网引用？three.js/OrbitControls 内联是否完整可用（全局 THREE +
   THREE.OrbitControls）？file:// 双击是否真能跑（你无法开浏览器，但可从结构 + JS 逻辑判断）。
2. **app JS 正确性**（你读代码判，我无法 headless 渲染）：截面 clipping plane 数学（normal/constant、flip）、
   爆炸（按楼层 z 偏移）、量距（raycaster + 两点距离）、点选高亮（按 zone）、save PNG（preserveDrawingBuffer）、
   楼层聚类 + 着色、resize/loop。有无空引用 / 事件未解绑 / 明显逻辑错？跑 `node --check`（测试里已含）。
3. **安全**：title 走进 HTML，是否有 XSS 注入面（我只 strip 了 <>）？geometry JSON 内嵌是否可能破坏 HTML/JS（`</script>`
   注入等）？
4. **接线**：viewer 只在 stage 2/3 过 gate① 时生成；几何门仍阻塞 4_mep；GLB 确已从主流程剥离但工具仍在。
5. **不越界**：未动 IntakeOutput 契约 / run_pipeline / 下游；vendor 大文件（619KB）是否合理（离线诉求）。
6. 一般 correctness / 资源 / 边界。

## 验收
- High/Medium/Low + 证据(file:line) + 建议修复；`python -m pytest -q`（作者侧 252 绿）；verdict CLOSEABLE / CHANGES REQUESTED。
- 注：3D 渲染的视觉效果需用户浏览器确认，本审聚焦代码正确性 / 离线性 / 安全 / 接线。
