# v3 洞口宿主按位置定位施工简报（terra）

日期：2026-07-24  
BASE：`a8c8d1c`（含转换器返工 CLOSED 文档；功能基线为 `cef0de9`）  
施工 HEAD：本提交（`git rev-parse HEAD`）

## 根因确认与方案选择

sm24 转换器输出已能通过 G9 preflight，但完整 `extract_gt_v3` 在洞口挂载时报
`opening_host_zone_ambiguous`。根因与派工单 trace 一致：Vg 按 footprint 外轮廓
生成 East 整段，`_host_zones` 因此列出贴该段的 z3–z7；旧代码把“整段有几个邻区”
错误等同为“这个窗口有几个宿主”。

采用 **option b（按窗位置定位）**，未采用 option a。原因是 Vg 的整段仍是正确、稳定的
外立面/可见性投影原语；为洞口宿主而拆段会扩大 boundary ID、elevation scope 与既有 GT
wire 语义的影响面。option b 只在洞口绑定处增加一个必要判断，不修改 v3 schema wire、v2
legacy 或 gt.json 铁律路径语义。

## 修复

- `gt_extraction._host_zones_for_opening`：保留 `_host_zones` 作为候选段过滤；在最佳 segment
  已选定后，只接受 **zone polygon 的共线外边完整覆盖 opening `[lo,hi]`** 的 zone。恰 1 个
  才挂载；0（真跨区）或多个（重叠/损坏 zone）保持 `opening_host_zone_ambiguous` fail-closed。
  无 tolerance 扩张，端点接触不被猜成跨区。
- `gt_schema.validate_gt_v3` 的宿主边界自校验使用同一“opening 全跨度覆盖”语义。否则提取器
  已正确产出 sm24，schema 又会以旧“整段”假设把它拒绝；wire/model 字段均未改变。

## 测试与验收缺口

- `test_opening_host_uses_its_interval_not_the_entire_shared_facade_segment`：共享段有 Z1/Z2 时，
  窗 `[1,2]` 唯一落 Z1；真跨分界 `[4.5,5.5]` 为 0；重叠损坏边为多个，均不猜。
- `test_opening_host_uses_its_span_and_true_crossing_is_rejected`：schema 层确认端点接触相邻区
  可通过，而 `[1,3]` 真跨两区仍报 `gt_opening_host_zone_boundary_mismatch`。
- `test_sm24_converter_output_runs_full_v3_opening_attachment`：从 sm24 源 DXF 临时运行转换器，
  取实际 normalized DXF + manifest 执行 **完整** `extract_gt_v3`（不是 G9 preflight），断言
  1 floor / 8 zones / 14 openings，且 14 个 `host_zone_id` 全部唯一且属于该 floor。该测试堵住
  “preflight 过、洞口全提取崩”的缺口。
- v3 定向回归：`tests/test_gt_from_dxf.py tests/test_gt_schema.py tests/test_gt_overlay.py
  tests/test_gt_render.py` → `86 passed`。

## sm24 审查交付物

已用主控提供的 review bundle 生成候选（未写 `case_tests/.../gt/sm24_anchor/`）：

- `logs/experiments/2026-07-24_sm24_gt_review/gt/gt.json`
  - v3 candidate，content SHA `45595e1a1573cc876694ad2da9d9c9f05514355324dcb27b7e2cb34de7d487d9`；
    1 floor、8 zones、14 openings，14/14 唯一宿主。
- `logs/experiments/2026-07-24_sm24_gt_review/gt/renders/gt_plan.png`
  - 已目视确认包含 8 区和外墙 14 洞口标记，带 candidate 水印。
- `logs/experiments/2026-07-24_sm24_gt_review/gt/renders/gt_elev.png`
  - 合法的 `NO ELEVATION SOURCE BINDING` candidate 占位；不是伪造立面。

与 sm21 的差异是输入事实而非漏产：sm21 legacy v2 有立面 view/raster 和窗 sill/head，故有
`overlay_{facade}` 与正常 elevation 图；sm24 是转换器 plan-only，manifest 有 0 elevation view、
0 raster overlay、14/14 opening `z_interval=None`。因此本次交付对齐 `gt.json + renders/` 的形态，
但不生成不存在证据的 facade overlay 或窗 z 高度。

已实际调用 v3 `render_gt_overlay.py`；它按空 `raster_overlays` 合法生成空
`gt/overlays/` 目录、未生成 PNG。这确认“没有 overlay PNG”来自 manifest 无 raster binding，而不是
跳过该渲染流程。

## 全仓结果与残留

- 全仓最终结果：在本轮 v3 开口宿主变更完成、派工单作为合法未跟踪输入文档仅由本地 `.git/info/exclude` 排除的条件下运行 `pytest -q`：`1541 passed, 10 xfailed, 0 failed`（552.87s，146 warnings）。
- 残留：sm24 仍是候选、待用户检查/签字后方可进入 baseline；plan-only 的立面/raster/z 证据未实现且
  不应由提取器推测。除为一致性必需的 v3 schema validator 外，本轮未改 v2 legacy、gt.json
  路径语义、转换器 gate①、执行器、reading/correction 或 golden。
