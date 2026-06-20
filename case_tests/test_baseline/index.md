# baseline 注册表

> 当前规范 baseline anchor 一览。每个 anchor 自包含成绩单（`<case>/baseline.json`）+ 人读反馈
> （`<case>/RUN_REPORT.md`）+ golden 测试。新增/更新 baseline 后在此登记一行。

| anchor / run | 楼层/区 | golden 计数 (区/面/窗) | gate① | EP | 状态 | 记录 |
|---|---|---|---|---|---|---|
| `sm20_anchor/run_2026-06-15_baseline` | 3 层 (7/8/4) | 19 / 135 / 16 | 0 block | Completed, 0 severe | ✅ golden（`tests/test_validation_run_baseline.py`）| `run_.../baseline.json` + `RUN_REPORT.md` |
| `sm21_anchor/run_2026-06-16_opus_e2e` | 2 层 (7/7) | 14 / 100 / 15 | 0 block | Completed, 0 severe | ✅ golden（`tests/test_validation_run_baseline.py`）| `run_.../baseline.json` + `RUN_REPORT.md`；gt `gt/sm21_anchor/gt.json`（计数/立面/层高 verified）|

> **图例**：✅=干净入库的金标准；⏳=待跑；❌=有 block/severe，不可作 baseline。
> golden 计数即回归断言锚点；变更需在 PR 说明原因。
>
> **未结项**：sm21 **South 2F 窗 along-facade x** 仍是真 bug（gt 计数/立面已 verified，差异定位在 1_correction，见 [plan.md N2](../../AI_agent/plan.md)）。
> **gt 来源演进**：当前 gt 由人读原图得出、故意不含窗 x；**CAD→gt 满配答案方向**（精确窗 x+宽+区划+门）见
> [proposals/cad_to_gt_extraction_plan.md](../../AI_agent/proposals/cad_to_gt_extraction_plan.md)（待 DXF）。gt 渲染核验用 `scripts/tool_scripts/render_gt.py`，逐 case bundle 见 [gt/README.md](gt/README.md)。
> **下一份**：sm21_anchor judge-in-the-loop run（`run_stage.py` 逐段真驱动，[plan.md N1](../../AI_agent/plan.md)）。

_2026-06-16 — 建注册表（旧 `runs/` 已挪 backup）。sm20_anchor 已是 golden（计数被测试钉住）。_
_2026-06-16 — **sm21_anchor 首份自包含 baseline 入库**（opus-4.8 编排 + 冷启子 Agent 重识图，全程不复用
旧 reading）：14 区 / 100 面 / 15 窗，对 gt 逐立面精确命中，gate① 全绿，EP 0 severe / 6 warn。本轮发现并
修了 4_mep 系统性缺陷（全 NoMass + 缺 ScheduleTypeLimits → authoring.md 加两条硬规则）。J1 一条 minor：
F1 东南房用途标 office、gt 为 meeting（仅负荷档位、不动几何）。_
_2026-06-20 — 同步：gt 转逐 case bundle `gt/<case>/`（+ `render_gt.py` 渲染核验、CAD→gt 满配方向）；
标注 sm21 South 2F 窗 x 未结；指向新管理文档结构（CLAUDE/plan/decision_log 三分）。注册表本身不变。_
