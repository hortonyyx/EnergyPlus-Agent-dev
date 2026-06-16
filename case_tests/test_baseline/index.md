# baseline 注册表

> 当前规范 baseline anchor 一览。每个 anchor 自包含成绩单（`<case>/baseline.json`）+ 人读反馈
> （`<case>/RUN_REPORT.md`）+ golden 测试。新增/更新 baseline 后在此登记一行。

| anchor / run | 楼层/区 | golden 计数 (区/面/窗) | gate① | EP | 状态 | 记录 |
|---|---|---|---|---|---|---|
| `sm20_anchor/run_2026-06-15_baseline` | 3 层 (7/8/4) | 19 / 135 / 16 | 0 block | Completed, 0 severe | ✅ golden（`tests/test_validation_run_baseline.py`）| `run_.../baseline.json` + `RUN_REPORT.md` |
| `sm21_anchor/run_<待跑>` | 2 层 (7/7) | 待跑 (gt: 14/?/15) | 待跑 | 待跑 | ⏳ 待建（gt 已起草待核 → 建 case → 跑）| gt `test_baseline/gt/sm21_anchor.json`（draft）|

> **图例**：✅=干净入库的金标准；⏳=待跑；❌=有 block/severe，不可作 baseline。
> golden 计数即回归断言锚点；变更需在 PR 说明原因。

_2026-06-16 — 建注册表（旧 `runs/` 已挪 backup）。sm20_anchor 已是 golden（计数被测试钉住）；
sm21_anchor 待按新方案跑出首份自包含 baseline。_
