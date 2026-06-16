# baseline 注册表

> 当前规范 baseline anchor 一览。每个 anchor 自包含成绩单（`<case>/baseline.json`）+ 人读反馈
> （`<case>/RUN_REPORT.md`）+ golden 测试。新增/更新 baseline 后在此登记一行。

| anchor / run | 楼层/区 | golden 计数 (区/面/窗) | gate① | EP | 状态 | 记录 |
|---|---|---|---|---|---|---|
| `sm20_anchor/run_2026-06-15_baseline` | 3 层 (7/8/4) | 19 / 135 / 16 | 0 block | Completed, 0 severe | ✅ golden（`tests/test_validation_run_baseline.py`）| `run_.../baseline.json` + `RUN_REPORT.md` |
| `sm21_anchor/run_2026-06-16_opus_e2e` | 2 层 (7/7) | 14 / 100 / 15 | 0 block | Completed, 0 severe | ✅ golden（`tests/test_validation_run_baseline.py`）| `run_.../baseline.json` + `RUN_REPORT.md`；gt `test_baseline/gt/sm21_anchor.json`（**verified**）|

> **图例**：✅=干净入库的金标准；⏳=待跑；❌=有 block/severe，不可作 baseline。
> golden 计数即回归断言锚点；变更需在 PR 说明原因。

_2026-06-16 — 建注册表（旧 `runs/` 已挪 backup）。sm20_anchor 已是 golden（计数被测试钉住）。_
_2026-06-16 — **sm21_anchor 首份自包含 baseline 入库**（opus-4.8 编排 + 冷启子 Agent 重识图，全程不复用
旧 reading）：14 区 / 100 面 / 15 窗，对 gt 逐立面精确命中，gate① 全绿，EP 0 severe / 6 warn。本轮发现并
修了 4_mep 系统性缺陷（全 NoMass + 缺 ScheduleTypeLimits → authoring.md 加两条硬规则）。J1 一条 minor：
F1 东南房用途标 office、gt 为 meeting（仅负荷档位、不动几何）。_
