# Review — East/West 立面窗高度 bug 根因 + 修复（Codex 验证）

- **Date**: 2026-06-20
- **Reviewer**: Codex (默认模型，ChatGPT 账户)，via MCP（文件内联，沙箱 bwrap 容器内不可嵌套）
- **Author**: Opus 4.8
- **触发**: 用户发现 gt 东西立面窗对不齐原图，要求查"数据 vs 渲染"并让 Codex 一起查

## 问题 & 根因（Codex: 根因 CONFIRMED）
gt 东西立面窗抽成 1200mm 高（head F1=2.2/F2=5.2），实际 DXF/图纸=1800（head 2.8/5.8）；南北正确。
**根因**：`gt_from_dxf._elevations` 旧公式 `块内 LINE 的 y 跨度 × insert.yscale = 600×2.0 = 1200`——
这是**块空间的局部代理**（只看 LINE、漏 LWPOLYLINE/弧/嵌套块，且未施加完整 INSERT 变换），不是绘制范围。
南北只是其 yscale 凑巧让 LINE 代理=可见范围。**铁证**：`ezdxf.bbox.extents([insert])`（世界空间虚拟化）
给出东窗世界高=1800、z[1000-2800]/[4000-5800]，= 图纸。

## 修复（Codex: fix 对）
`_elevations` 改用 `bbox.extents([e])` 拿真实世界 z：`sill=extmin.y-base, head=extmax.y-base`，
窗中心 x 也用 bbox（plan↔elev 匹配）。默认 `fast=False`（Codex 提示 fast=True 对 Bézier 会偏大；本代码用默认 ✓）。
修后全立面正确（N/S 不变；E/W F1 1.0-2.8、F2 4.0-5.8；South 小窗 1.5-2.1 保留）。
另修 render_gt（TYPE 1）两处脱节：逐窗 sill/head（原用立面级→小窗画错）+ 门改带位置（gt door 现含 x_m/width_m/sill/head，两 renderer 一致）。

## Codex 额外发现 & 处置
- **同类 bug 警告（width/position）**：窗/门宽用 `abs(xscale)`、位置用 `insert` 点，不保证=真实绘制宽/中心。
  **处置**：sm21 的 xscale 宽度**已被 overlay 验证正确**，且是天正块**标称宽度**（比含框 bbox 更合 gt 意图，bbox 会含窗框/门弧而高估）；**保留不动**。门宽用 xscale 正好避开 Codex 指出的"门开启弧撑大 bbox"问题。
- **bbox 几何非语义**：可能含窗框/sill 投影/swing 弧/标注而高估开口。本例 bbox 高度与图纸 dim 一致，OK；记为已知。
- **门滤 `sill<100` 脆**：楼上门/落地窗会误判。本例 sm21 仅地面门，OK；**记为已知限制**，未来多层带阳台门需改。
- **insert 点 ≠ 几何中心**：本例窗/门 insert≈中心（overlay 已验证对齐），保留；未来非对称块需用 bbox 中心。

## 结论
根因 CONFIRMED、修复正确。高度 bug（用户报的真问题）已修，全立面对齐。Codex 健壮性发现（width/门滤/insert）
记为未来多 case 泛化时的硬化项，**不动 sm21 已验证正确的值**。测试 271 绿（含更新的 East head 5.8 断言）。
