# 派工单：v3 提取器「多房间共用外墙 → 窗无法归属房间」缺口修复（terra）

**日期**：2026-07-24 · **主控**：Opus 4.8 · **施工方**：terra（GPT 侧，续转换器 thread）
**审**：Opus 子代理升一档（Claude 侧·探索性对抗审·谁写谁不批）→ 主控轻门
**验收总标准（用户定）**：**sm24 的 gt 做成和 `case_tests/test_baseline/gt/sm21_anchor` 一模一样的交付形态（`gt.json` + `renders/`），用户检查通过即锁定为答案。**

---

## 0. 背景 / 根因（已由主控 trace 定死）

上一轮转换器返工已 CLOSED（GLM APPROVE-WITH-CHANGES）。但把 sm24 转换器输出喂进 v3 提取器产标准 gt 时**失败**：
`extract_gt_v3` 抛 `opening_host_zone_ambiguous`（`src/agent/judge/gt_extraction.py:686`）。

**根因**：v3 边界段从 **footprint 外轮廓**按 N/S/E/W 方向切（`gt_extraction.py:612-617`，`vg_for_direction(footprint.exterior, ...)`），所以「东立面 = 一整条段」。`_host_zones(floor, segment)`（`:454`）返回**所有多边形边与该段共线重叠的区**——sm24 东边 5 个房间（z3–z7）都贴着这条段 → 5 个宿主 → `len(hosts)!=1` fail。

**这是 v3 提取器本身的潜伏设计缺口（B4a 建的·非转换器错）**：过去测试案例都「一面墙=一个房间」，sm24 是**第一个多房间共用一面外墙**的案例才暴露。**转换器 G9 只做 preflight、没跑到窗挂载**，所以审时（sol/GLM/主控轻门）漏了。

主控实测 trace：`host-count 分布 {1:2, 5:2}`，失败段 `F1:boundary:… fam=East hosts=['z3','z4','z5','z6','z7']`。

---

## 1. 修复（主控推荐 option b：按窗位置定位房间）

**不要求「整条段只属一个房间」**，改为**看窗那一小段背后是哪个房间**：

- 在洞口挂载循环（`gt_extraction.py:669-690`）：选出最佳边界段 `legal[0][2]` 后，现在是 `hosts=_host_zones(segment); if len!=1 fail`。
- 改为：在候选宿主区里，找**其多边形边覆盖该洞口 `[interval.lo, interval.hi]` 区间**的区（即 `_positive_collinear_overlap` 用**洞口区间**而非整条段来判、且该区边覆盖洞口全跨度）。
  - 恰 1 个区覆盖洞口区间 → 挂它。
  - 0 个 或 ≥2 个（洞口真跨在两区交界上）→ **保持 fail-closed**，发**可定位诊断**（`opening_host_zone_ambiguous` 或更精确的新码），不猜。
- 你可以自行判断 option b 是否最优；若你论证 option a（把边界段按区切开）更对，**在简报里说明理由**再走——但优先局部、不动 gt v3 schema、不破坏既有 v3 提取行为。

**约束**：这是**共享 v3 提取核心 + gt 铁律敏感区**。既有 v3 提取/schema/render 测试（`test_gt_from_dxf` / `test_gt_schema` / `test_gt_overlay` / `test_gt_render` 等）**必须全绿零回归**。不动 v2 legacy 路径、不动 gt.json 铁律路径的语义。

---

## 2. 补验收缺口（本轮必做）

这个漏网的教训 = **G9 preflight ≠ 完整 extract_gt_v3**。补一个**端到端测试**：拿 sm24 转换器输出（normalized.dxf + manifest）真跑 `extract_gt_v3`（带洞口挂载）→ 断言成功、8 区、14 洞口各挂到唯一房间。以后这类「预检过但全提取崩」不再漏。可复用主控已产的 bundle：`logs/experiments/2026-07-24_sm24_gt_review/`（normalized.dxf + manifest.json + source_map.json + conversion_report.json，转换器 reworked HEAD=cef0de9 产）。

---

## 3. 产出 sm24 gt（对齐 sm21 交付形态）

提取跑通后，把 sm24 gt 做成 sm21 那样：
- `gt.json`（v3 schema——sm24 是 v3、sm21 是 v2 legacy，**schema 结构本就不同**，判卷系统 dual-read 两者；对齐的是**交付形态**不是 schema 内部）。
- `renders/`：用 `render_gt.py` / `render_gt_overlay.py` 产 PNG（plan + overlay），对齐 sm21 的 `renders/` 那一套（sm21 有 gt_plan/gt_elev/overlay_{1f,2f,East,North,South,West}）。
- **诚实报告 sm24 与 sm21 的真实差异**：sm24 是**转换器 plan-only**（无立面 view）——窗**没有 z 高度/立面证据**，所以立面类 render（gt_elev/overlay_East…）可能产不出或只有轮廓；如实说明哪些能对齐、哪些因 plan-only 天生缺（别硬造 z）。
- 产到**审查位置**（如 `logs/experiments/2026-07-24_sm24_gt_review/gt/` 或临时 review 目录）**先给用户检查、不要直接写进 `case_tests/test_baseline/gt/sm24_anchor/`**（那是签字锁定后的事）。**不写受保护 gt/gt_sources 目录**（转换器 work_dir guard 会拦；gt 提取输出走 review 目录）。

---

## 4. 纪律

- 动 `src/` 前 `cp` 备份到 `backup/src_history/2026-07-24_v3_opening_host/`。
- **不动** gate①、执行器、reading/correction、golden、`gt.json` 铁律路径语义、v2 legacy 路径。
- **诚实披露**：做不完/部分/残留（尤其 plan-only 立面缺口）明写简报，别把未竟说成完成。
- 简报落 `AI_agent/logs/reviews/execution/2026-07-24_v3_opening_host_fix_terra.md`：根因确认 / 修法（含 a-vs-b 选择理由）/ 多房间测试 / e2e 验收测试 / sm24 gt+renders 产出结果 + 与 sm21 差异 / 全仓结果（现基线 1539 passed, 10 xfailed）。
- 完成 `git commit`（`7.24_V3OpeningHostByPosition` 之类·body 三段·`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`）。别 push。
- 审 = Opus 子代理升一档（活体探针·探索性），之后主控轻门。全程中文。
