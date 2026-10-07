# 平面批量分块查看工具说明

范围：domain · tools，只供分工模式的平面读图员使用；立面工具目录、单模型工具、runtime 与几何内核不变。

API：`PLAN_VIEWS_TOOL` 暴露无参数工具 `view_plan_blocks`；`view_plan_blocks(frozen, image_name)` 由 `ReaderTools` 传入本任务已经固定的图名，模型不用重复图名或填写 bbox。函数先以 `inputs.json` 的准入哈希和可选尺寸核对 `frozen.run_directory/images/<image_name>`，再由平面角色专用 renderer 一次生成全部视图，不重复调用共享 MCP。每块从同一份已核验原图裁切，按 3 倍放大并直接复用共享 `coordinate_grid_view`；`structuredContent.views` 给出每块的 `view_id`、核心／含重叠 bbox、实际倍率和网格状态，完整 metadata 按相同顺序放入 `evidence_previews`。

分块规则：保持已复核的布局选择：依次找 4、6、8 块中能把含重叠最长边控制在约 552 原像素内的最少块数；同一块数在 2×2／3×2／4×2、转置布局和必要的单行／单列布局中，选择最长边最小的方向。每块在内部边界外扩核心宽高的 4%，相邻块有少量重叠，核心格仍无缝覆盖完整原图。约 552 用来保持标杆中每块约 500 原像素的可读粒度，不再是共享 `view_image` 的 1600 像素限制。

渲染与签发：角色 renderer 的返回长边保护线为 4096 像素，常见五张图均可按真 3 倍生成；只有极端块触线时才按 `4096 / 原块最长边` 降低倍率，返回实际倍率和明确说明。最终 PNG 生成后才用 `xb` 独占创建新的 `image_views/view_NNNN.json`，记录原图哈希、bbox、返图哈希、倍率、网格及 renderer 版本；已有 view 记录不读取后改写，也不借用旧 `view_id` 替换图像。合并 content 与 `evidence_previews` 顺序一致，因此 `FrozenBimTools.image_origins`、上下文回取与读图回执仍能按返图哈希关联原图。外层 runtime 事件已经记录本次工具调用，不写共享 `tools.jsonl`。

边界：极端长图优先使用单行或单列 4／6／8 块；4096 保护线只降低显示倍率，不裁掉原图内容。少于 4 个像素的图无法产生 4 个非空块，明确拒绝。极小图仍完整覆盖，但共享网格函数会按现有规则省略无意义的坐标标注。

行为测试：确认一次外层调用产生 4／6／8 张图，所有核心 bbox 完整覆盖且视图相邻重叠；2133×1345 代表图返回 8 块、每块真 3 倍；纯函数检查极端块受 4096 保护而不分配大图；原图字节变化被准入哈希拒绝；已有 view 文件不覆盖；每张 content 字节、返图哈希、immutable view record 与 `image_origins` 逐项一致。父级接线检查另确认工具只出现在 `plan_reader`，默认图名来自当前任务，立面目录逐项不变。
