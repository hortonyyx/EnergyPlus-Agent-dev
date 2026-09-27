# 全构件命名与功能表离线验证

- [已有 sm21 新版查看](sm21/viewer.html)：run58/candidate_04 原始方案离线导出，14 房间、84 边界、29 门窗、14 连接，几何、源 ID、宿主、连接完全保持；原案例 role 全为 unknown，未人为补判功能。
- [多类型人工示例](synthetic/enclosure_viewer.html)：4 房间、2 楼层，检查会议／办公／走廊／卫生间配色，局部未知围护显示片和门窗命名。此示例不是实际建筑，也不用于还原评价。
- [61 类＋未知的完整色表](catalog.html)。运行时源表 `src/agent/data/room_types.json`。
- [导出验证](verification.json)、[浏览器结果](browser_report.json)、[252 项测试](pytest.md)、[实施文件摘要](implementation.json)。无工作模型或仿真调用。

复现导出：从仓库根执行 `python -m AI_agent.logs.experiments.2026-09-27_bim_naming_catalog.verify_export`；已有输出不覆盖，另设新输出目录后再运行。浏览器使用 `PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-27_bim_naming_catalog/browser_check.py`。测试浏览器仅在内存里增加内部状态读取，交付 HTML 无测试接口；检查所有实际 mesh 的层／块／面说明、边命名、真实点击、颜色相等、双层切换、离线加载和零 JS 错误。

验证使用 `/opt/venv/bin/python`。仓库 `.venv` 的 NumPy 不完整，首次收集失败，未修改该环境。早期失败包含新测试夹具缺字段、旧 fixture 的 inferred 类型，以及已有交付回执压缩后测试仍从精简回复取详细字段；夹具改用表内值，保留单独表外拒绝测试，详细交付断言改按返回路径读取完整 delivery.json 并核对源摘要。未取消或放宽业务断言，也未扩大 18k 回执上限。
