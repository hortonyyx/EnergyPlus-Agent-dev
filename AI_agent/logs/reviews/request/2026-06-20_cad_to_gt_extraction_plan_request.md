# Review request — 天正合并 CAD → 满配 gt 方案 + 前置工具链

- **Date**: 2026-06-20
- **Branch**: 6.15_ValidationArchM0toM4
- **Reviewer**: Codex (gpt-5.2-codex), via MCP direct call (read-only/self-driven)
- **Author**: Opus 4.8 (主开发 Agent)
- **审阅类型**: 设计方案（plan doc）+ 前置工具（inspect_dxf.py + test）

## 背景
gt（评测答案）现由人读 PNG 产出，故意不含窗 along-facade x（人读不准，写错→judge 误判正确输出）。
用户要"尽量全的标准答案"，决定换来源：从权威天正 CAD（DWG/DXF）机器级精确抽几何 → 满配 gt。
用户给的约束：①一份**合并 CAD**（平面+立面同一文件）②图层按**构件类型**分（天正图层标准），
不按平面/立面分。用户要求：先做前置工作，写完整方案，交 Codex 审。

## 本次产物（请审）
- **设计文档** `AI_agent/architecture/cad_to_gt_extraction_plan.md` —— **主审对象**。
- **新增** `scripts/tool_scripts/inspect_dxf.py` —— DXF 体检器（单位/图层直方图/proxy 计数/图名/
  视图区空间聚类预览）。读 ezdxf。
- **新增** `tests/test_inspect_dxf.py` —— 在合成天正风格合并 DXF（2 平面+4 立面、构件分层、图名）上
  验证 inspector（2 测）。
- **环境**：装了 ezdxf 1.4.4（uv，纯 Python）。

## 关注点（请重点审）
1. **纪律是否到位**：方案 §3 把源 DXF 定为答案级数据、**不放 case_data/**（否则执行器读到=识图作弊），
   放 `gt/source/`。这个隔离是否充分？有没有泄漏路径（如 render/manifest/工具顺手把 dxf 路径带进
   执行器可见处）？`gt_from_dxf`/`inspect_dxf` 作为离线工具写 gt 目录，gate①/执行器不 import——
   `test_gt_discipline` 扩名单是否覆盖全？
2. **schema 扩展后向兼容**（§5）：windows[] 加 `openings[{x_m,width_m}]`、顶层加 `_source`，
   现有 `load_gt`/judge/`render_gt`/`test_gt_discipline` 读 count/sill/head/rect_m 不受影响？
   有没有哪个消费方会因新字段崩或误判？
3. **与"精确坐标谁判"不冲突**（§6）：gt 的精确 x 是 judge/人的**参考真值**、不是 gate① 阈值；
   gate① 上线无 gt 仍只用容差不变量。这个区分站得住吗？会不会诱导后人把 gt 精确值当 gate① 判据？
4. **抽取管线的确定性与薄弱点**（§4）：S2 视图分割（bbox 聚类→最近图名命名）、S5 plan↔elev
   计数交叉核、S6 坐标归一（footprint SW=原点 §5.1，mm→m）——哪步最可能在真文件上崩？S3 房间
   role 推断兜底是唯一非确定性处，是否该更明确隔离/标注？
5. **天正现实**（§2 P-A/P-B、§7）：proxy 对象需图形导出（inspector `proxy_or_unsupported` 体检）、
   窗的 DXF 表达不定（LINE/LWPOLYLINE/INSERT/洞口）。方案"看 inspector 报告再定 S3/S4 细节"
   是否合理，还是应预先把分支都设计好？
6. **inspect_dxf.py 代码**：proxy 检测（`DXFTagStorage`）、视图聚类（union-find，gap=2% span）、
   图名正则、只对结构实体算 bbox（避开 TEXT 字体依赖）——有无 bug / 误分类 / 边界情况漏？

## 不在本次范围
- `gt_from_dxf.py` 实现（P2，待真 DXF + 本方案过审后写）。
- render_gt overlay 精确模式（P3）。
- CAD 输入模态轨（P5，未来）。

## 如何审
请直接读上述文件（`cad_to_gt_extraction_plan.md` 为主）+ `inspect_dxf.py` + `tests/test_inspect_dxf.py`，
可跑 `python -m pytest tests/test_inspect_dxf.py -q` 验证。给 CHANGES REQUESTED / CLOSEABLE 判定 +
按严重度（High/Medium/Low）列 findings。
