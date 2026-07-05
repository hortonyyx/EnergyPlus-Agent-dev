# Review — 离线交互式 3D 几何检视器（backlog #3）

- **Date**: 2026-06-19
- **Reviewer**: Codex via MCP direct (danger-full-access, user-authorized; self-driven read + pytest + node --check)
- **Request**: [2026-06-19_geometry_viewer_request.md](../request/2026-06-19_geometry_viewer_request.md)
- **Author**: Opus 4.8
- **环境注记**: 3D 渲染视觉效果 headless 无法自验，本审聚焦代码正确性 / 离线性 / 安全 / 接线。

---

## VERDICT: CHANGES REQUESTED

**High**
1. Geometry JSON can break out of the inline `<script>`. Evidence: render_geometry_viewer.py embeds
   `window.GEO` directly in a script tag and used raw `json.dumps(...)` without escaping `<`. A zone/surface/
   window string containing `</script><script>...` closes the script before JS parsing (verified the literal
   close-script sequence appeared). Fix: escape `<`/`>`/`&`/U+2028/U+2029 after json.dumps (e.g. `<`→`<`);
   add regression tests for `</script>` and `<!--`; prefer `html.escape()` for title instead of stripping `<>`.

**Medium**
1. Floor clustering counts ceilings and roofs as extra floors. Evidence: floor bases derived from every
   surface's min-Z, then assigned per mesh + used for explode. The kernel geometry includes Floor/Ceiling/Roof/
   Wall; e.g. sm20 all-surface levels `[0.0, 3.6, 7.2, 12.0]` but real floor bases `[0.0, 3.6, 7.2]` — the top
   roof becomes a fake `F4` and explodes away from its story; breaks floor colouring / isolation / explode. Fix:
   derive bases from `type==="Floor"` surfaces or a zone→floor map; assign all surfaces in a zone from that
   zone's floor base; windows inherit parent/zone floor; fall back to wall bottom-Z only if no floor surfaces.

**Low**: none.

**Checks**: `node --check /tmp/app.js` passed. `python -m pytest -q` passed: 252 passed.
(Could not visually verify the 3D render in this headless environment.)

---

## 主开发 Agent 处置（2026-06-19，Opus 4.8）

- **High-1（script breakout / XSS）— 已修**：新增 `render_geometry_viewer._js_embed()`——`json.dumps` 后把
  `<`/`>`/`&`/U+2028/U+2029 转成 `\u00xx`（JS 对象字面量解析回原字符，不会成 `</script>`）；`build_viewer_html`
  用它内嵌 geometry。title 改用 `html.escape`。回归测试：含 `</script><img onerror>` 的 geometry → HTML 仍只有
  4 对合法 script 标签、恶意串被转义为 `</script>`；title `<b>&x` → `&lt;b&gt;&amp;x`。
- **Medium-1（楼层把 ceiling/roof 误算成层）— 已修**：JS 楼层基准改取 `type==='Floor'` 的面（无则回退全面
  min-z）；建 `zoneFloor` 映射，每个面按**其区的 Floor 面**定层（ceiling/roof 随区归本层），窗按自身 sill
  min-z 取最近基准。真数据印证：sm21 Floor 面 z=[0.0, 3.0] → **正确 2 层**（旧全面基准 [0,3,6.6] 会误判 3 层）。
- 顺手清理：删了未用的 `HILITE` 占位 + 其 placeholder replace。

修后：`node --check` 过、`python -m pytest -q` **253 passed**、6 条 viewer 测试（含 breakout/title 转义）。
注：3D 渲染视觉仍需用户浏览器最终确认。

**Re-verify（已闭环）**：Codex 同会话复审判 High-1 = PASS、Medium-1 = PASS（无 findings，node-check + 253 passed），
两 anchor 印证 floor 修复（sm21 [0.0,3.0] 取代旧 [0.0,3.0,6.6]；sm20 [0.0,3.6,7.2] 取代旧 [0.0,3.6,7.2,12.0]）。
**#3 改动集 VERDICT: CLOSEABLE。** 唯一遗留=3D 视觉效果待用户浏览器确认。
