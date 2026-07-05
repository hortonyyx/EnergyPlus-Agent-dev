# Review — 天正合并 CAD → 满配 gt 方案 + 前置工具链

- **Date**: 2026-06-20
- **Reviewer**: Codex (默认模型，ChatGPT 账户；`gpt-5.2-codex` 该账户不支持)，via MCP
- **Author**: Opus 4.8
- **Request**: [request/2026-06-20_cad_to_gt_extraction_plan_request.md](../request/2026-06-20_cad_to_gt_extraction_plan_request.md)
- **Verdict**: **CHANGES REQUESTED**（4 High / 6 Medium / 5 Low）

## 环境注记
Codex 自带 bwrap 沙箱在本容器内无法嵌套（`bwrap: No permissions to create new namespace`），
read-only/workspace-write 均读不了本地文件；绕开它的 `danger-full-access` 被 Claude Code 自动分类器拦
（不安全自主 agent）。→ **改为把全部产物内联进 prompt 让 Codex 审**（它支持"粘文件"模式）。首次盲审
方向已对，第二次贴全文得到下列文件/章节级 findings。

## Findings 与处置

### High（全部已在方案内处置）
- **H1 §3 源 DXF 隔离不足**：放 `gt/source/` 仍在 gt 根下，`rglob`/打包会顺手吃进去。
  → **改**：移到 gt loader 根**之外** `case_tests/test_baseline/gt_sources/<case>.dxf`。✅ 方案 §3 已改。
- **H2 discipline 测试扩法错**：`_scan` 扫 Python 子串，塞 `.dxf`(二进制) 会崩；把离线工具塞禁扫又自相矛盾。
  → **改**：拆三个目的测试（runtime import 面递归 AST 扫 / 离线工具不被 runtime import / 文件系统隔离）。✅ §3(b)。
- **H3 "PNG 同源 CAD" 仅口诀**：陈旧 PNG + 新 CAD 会生成貌似合理的假 gt。
  → **改**：机械指纹 `_cad_sha256`/`_png_sha256_by_view`/视图 bbox·origin·scale，生成时校验对不上 fail-fast。✅ §3(a)+§5。
- **H4 §6 "x_m 仅参考非阈值"是空愿景**：没东西拦后人把 openings 接进 gate①。
  → **改**：靠 §3(b)(1) runtime AST 扫机械守 + openings=judge-only 写进 gt/README+schema 注释。✅ §6。

### Medium（全部已在方案内处置）
- **M1 §4-S2 视图分割最脆**：标注/引线/图框跨视图会误并误分，S2 错则后续确定性地全错。
  → **改**：S2 降为"提案"，先滤标注/轴线/引线/图框层再聚，须图名/图框证据+确认坐实，歧义报出。✅ §4。
- **M2 inspect `_cluster_views` 全局 gap=2%span 脆**：大视图/远详图改全局阈值、标注串桥接、小详图被吞。
  → **记**：方案 §7 inspector P1 硬化（分阶段聚类/滤标注/自适应阈值/报歧义）。本轮先放宽图名正则。
- **M3 §4-S5 计数硬相等过严**：背立面省略/详图重画/内窗等合法情况会触发。
  → **改**：分级核（必备规范立面 exact，缺/偏/重复=warning，残留不一致须人确认才出答案级 gt）。✅ §4。
- **M4 §5 与 README"精确坐标故意不精确"不契约兼容**：结构兼容但语义未定义。
  → **改**：加 `schema_version:2` + openings 语义显式（facade-local 坐标系/具名角原点/单位 m/`count==len(openings)`/容差意图=参考非阈值）。✅ §5。
- **M5 §2/§7/§8 "看报告再定 S3/S4"是规划洞**：最难处恰是未知 CAD 编码。
  → **改**：加 **P1 出口规格**（gate）：每个 gt 必填字段须有 解析规则|人工 override|fail-fast 之一，不达不进 P2。✅ §8。
- **M6 §5 schema 版本化**（同 M4）→ ✅ schema_version:2。

### Low（已处置 1 / 其余记入 inspector P1 硬化）
- **L1 proxy=0≠几何可用**（匿名块）→ 记 §7：逐构件可用性核（块展开后数 usable 图元）。
- **L2 `_entity_bbox` 对嵌套 INSERT/XREF 不全** → 记 §7：递归解块+报未解析/xref。
- **L3 图名正则窄**（漏 一层平面/南立面/1-1剖面）→ **已修** `inspect_dxf._TITLE_RE`（图字可选；测试验证认无"图"标题、不误伤"办公室"）。✅
- **L4 结构-only bbox 不分桶** → 记 §7：分桶 bbox（几何/标注/图框/全部）让坏分割可见。
- **L5 render_gt openings 需 facade 方向/原点/缩放约定 + 逐 facade 测试** → ✅ 并入 §5 openings 语义 + render overlay 要求。

## 结论
本轮是**方案审**：High/Medium 全部已落进方案文档（§3/§4/§5/§6/§8 改写），Low 一条改代码（图名正则）、
其余归 inspector P1 硬化清单。代码改动 = `inspect_dxf._TITLE_RE` 放宽（测试通过，11 测绿）。
**未 re-verify**（Codex 内联审耗 ChatGPT 额度；方案性改动不涉可执行回归，留待 P2 实现期连同 gt_from_dxf 一起审）。
