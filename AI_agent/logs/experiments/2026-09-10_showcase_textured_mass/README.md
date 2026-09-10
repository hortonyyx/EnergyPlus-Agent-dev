# Voimatalo 直接判读与轻量 BIM 展示探索

用户明确选择复杂真实单体 Voimatalo，要求主助手 SOTA 直接尝试，按相对高精度 BIM 的目标制作。本轮读取既有去标签 GLB、完整 UV 贴图及已核实的办公/商业用途和八层信息，主助手判读后写几何方案，由确定性工具生成。没有另行调用产品模型、Claude、GLM、DeepSeek 或 EnergyPlus，未使用历史平面图或内部 GT。

[主展示](../../../../showcase/2026-09-11-research-report/demos/textured-mass/index.html) · [外壳版](../../../../showcase/2026-09-11-research-report/demos/textured-mass/envelope.html) · [详细范围](../../../../showcase/2026-09-11-research-report/demos/textured-mass/README.md)

## 本轮做到的范围

- 外壳版：八层主楼、低层附属体、顶层退台及屋顶体量，共 12 个空间体、316 个窗组和 2 处假设入口。
- 细分版：六个标准层增加假设的办公室/走廊/服务空间，两处连续竖向核心，共 164 个空间体、316 个窗组、165 个门对象。真实内部未知，不把本方案当作真实房间还原。
- 开口依附实际边界并扣洞；内部假设隔墙落在相邻外窗组间，避免切开已观察窗组。竖向核心没有中间封堵楼板，附属体没有补造未知楼板。
- 两个缺失端部的围护状态为 unknown（外壳版 16、细分版 36 片边界），可查看灰色提示；附属体与主楼的分界按抽象边界记录。
- 原网格与 BIM 共用明确的固定米制变换，支持真实贴图、BIM、叠合对照。没有重新缩放每个候选以制造贴合效果。

## 证据链

1. `capture_input.py` 生成 `input_views/` 中整体、街面、内院和各方向的真实完整纹理视图，主助手实际打开判读。
2. `measure_mesh.py` 选择接近各立面平面的真实三角面，按原 UV 投影到有米制映射的正投影视图；`facade_views/*.png` 与 `measurements.json` 保存观察依据。缺失端面的图几乎没有墙面，不能当作无窗的证据。
3. `refine_asset.py` 保存窗组观察区间、轮廓/标高及内部假设，复用已有 source BIM、接触、开口、enclosure 内核；`exterior/`、`inferred/` 保存方案、source JSON、显示投影、几何与覆盖报告。
4. `package_viewers.py` 只修改展示层：加入原始纹理及按钮，修正单层过滤时楼板显示、局部坐标箭头。产品查看器和源 JSON 不变。
5. `inspect_assets.py` 离线驱动实际打包页面。最终证据在 [`qa_run02/report.json`](qa_run02/report.json)：两版纹理加载、旋转、输入/叠合切换、F3 剖切、楼板可见、展开和工具面板通过，无页面异常、失败请求或外部网络请求。`qa_run01/` 保留第一轮展示检查。

## 验证边界与失败记录

两版建成时的 `geometry_check.json` 为 pass，之后明确注入未知端部声明，最终源检查仅有 `source.enclosure_unknown` warning，无 severe。七个标高切片的平面并集与采用的主楼轮廓差值为 0；未与真实房间清单/尺寸做独立保真评价，未验证仿真可用性。屋面曲率、坡地、门槛、精细窗框和实际内部仍未恢复。

`build_asset.py` 是最初规则窗排粗方案，失败记录为 `failed_build.json`、`failed_unbuilt.json`，不是最终构建入口。改为实际量测立面后，内院末端窗组仍曾跨出边角，记录在 `failed_exterior_01/`、`failed_inferred_01/`；复核视图后保留其可见宽度，并明确记录转角遮挡/完整洞口未知，不靠静默裁切放行。

标准层窗列从各面真实视图估计后复用六层，部分底层窗组视线不清且高程仍有规整。316 是本方案保留的窗组对象数，不能当作自动识别准确率；164 个空间体是推理方案细度，不能当作实际房间数量。当前结果只说明主助手加确定性工具可完成一份较细的真实体量 BIM 探索，不能外推生产模型的质量或成本。

## 复现约定

建模命令见资产 README，`--out` 必须是新目录。脚本直接构造带 `FootprintRing` 的旧 v2 类型对象以复用既有多边形内核；通用 JSON 读取不会自动恢复这份额外逐层轮廓，不能据本脚本宣称通用 v3 输入/Agent 适配已经实现。

浏览器检查使用项目外的隔离 Playwright 环境：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-10_showcase_textured_mass/inspect_assets.py --out /tmp/voimatalo-qa-new
```

最终两版源哈希保存在各自 `report.json`，HTML 文件哈希在浏览器报告。本轮不改变生产模型 Sonnet 上限，用户仅为本次展示探索选择主助手 SOTA 直接制作。

最终目录检查见 [`bundle_qa/report.json`](bundle_qa/report.json)：总入口、两张资产卡片和原始贴图页离线打开通过，21 个本地 Markdown 引用和 HTML 导航/预览均可解析。原 GLB 与展示输入哈希一致，sm25 原始源哈希未变；旧展示 20 个文件内容与会话基线一致（一个 SVG 只涉及 Git 的 CRLF/LF 归一化）。外壳版使用新增 `--out` 重建到新目录，源 JSON 与交付版本逐字节一致。
