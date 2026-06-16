# 审阅请求：0–5 校验架构 M0–M4 实现（设计→代码落地）

> **类型**：代码实现审阅（实现先前已 CLOSEABLE 的设计/施工方案）。
> **发起**：主开发 Agent（Opus 4.8），2026-06-16。
> **commit**：`0d267bf` `6.15_ValidationArchM0toM4`（分支 `6.15_ValidationArchM0toM4`，基于 `971b852`）。
> **规模**：44 files changed, +5063 / −128；测试 103 → **191 全绿**。

## 1. 背景

先前三轮 Codex 审阅已把**设计**（[pipeline_stage_contracts.md](../../../architecture/pipeline_stage_contracts.md)）+ **施工方案**（[pipeline_validation_build_plan.md](../../../architecture/pipeline_validation_build_plan.md)）判为 CLOSEABLE、可直接开工 M0。本轮是**按那份施工方案把 M0→M1→M2a/b/c→M3→M4 全部实现成代码 + 单测**。请审实现是否忠实于设计、有无引入硬伤/回归风险。

施工进度总表见 [build_plan §5](../../../architecture/pipeline_validation_build_plan.md#5-施工进度)。

## 2. 审阅范围（本次 commit 的新增/改动）

### 新增代码
- **M0 执行/审计地基**
  - [src/validator/checks/schema.py](../../../../src/validator/checks/schema.py) — CheckReport v2 + `disposition()` 纯函数（policy≠fact）
  - [src/agent/execution/](../../../../src/agent/execution) — `manifest.py`（append-only attempts + 内容寻址 hash + run_manifest）/ `stage_runner.py`（registry + capability + StageRunner）/ `invalidation.py`（失效 DAG + resume + RunBudget）/ `approval.py`（geometry checkpoint digest）/ `policy.py`（confirmation_policy + validation_scope）/ `routing.py`（失败分类）/ `validation_run.py`（M4 capstone `validate_case`）
- **M1**
  - [src/agent/reading/](../../../../src/agent/reading) — `schema.py`（P1a dimension chain + P1b facade image-local）/ `legacy.py`（迁移 adapter）
  - [src/validator/idf_fragments.py](../../../../src/validator/idf_fragments.py) — 统一 eppy parser
- **M2 逐段确定性 check**
  - [src/validator/checks/](../../../../src/validator/checks) — `reading.py` / `correction.py` / `kernel.py` / `mep.py` / `assembly.py`
  - [src/agent/correction/geometry_validator.py](../../../../src/agent/correction/geometry_validator.py)（A0§7）+ [facade.py](../../../../src/agent/correction/facade.py)（image-local→world）
- **M3 judge harness**
  - [src/agent/judge/](../../../../src/agent/judge) — `verdict.py`（schema v2）/ `retry.py`（单阶段盲抽）/ `executor.py`（J0/J1 + J4 stub）
  - [skills/intake_pipeline/0_reading/judge_rubric.md](../../../../skills/intake_pipeline/0_reading/judge_rubric.md) + [1_correction/judge_rubric.md](../../../../skills/intake_pipeline/1_correction/judge_rubric.md)
- **视觉件**：`scripts/tool_scripts/render_elevation_windows.py` + `render_building_3d.py`
- **测试**：`tests/test_{execution_foundation,reading_schema,idf_fragments,checks_reading_correction,checks_kernel,checks_mep_assembly,judge_harness,validation_run_baseline}.py`（88 新测）
- **fixtures**：`tests/fixtures/validation/{bad_2f_corridor_split,self_consistent_wrong_dimension,wrong_facade_window,bad_mep_semantics}.json`

### 改动文档（非代码）
- CLAUDE.md 顶 banner / pipeline_stage_contracts.md §3.2 实现状态 / pipeline_validation_build_plan.md §5。

### 明确未动（请确认确实零影响）
- `src/agent/pipeline.py:run_pipeline`、`IntakeOutput` 11 字段契约、下游 9 subagent / cross_ref / validate / interzone.py / schedules.py（仅被复用，未改）。

## 3. 重点关注（请优先核这些）

1. **policy ≠ fact 是否真分离**（[schema.py](../../../../src/validator/checks/schema.py) `disposition()`）：check 只报 fact（status），block/flag 由纯函数定；profile 差异靠 check 自报 `not_applicable`（如矩形 coverage 在非矩形 profile）。有无地方把 policy 逻辑混进 check？
2. **失效 DAG + resume 正确性**（[invalidation.py](../../../../src/agent/execution/invalidation.py)）：`downstream_of` 传递闭包；`stages_to_run` 的「输入 hash 漂移 + 上游污染」逻辑;批准 geometry 后 resume **不重抽 1_correction** 是否真成立。
3. **append-only 不覆盖坏 draw**（[manifest.py](../../../../src/agent/execution/manifest.py) `new_attempt_dir`）：拒绝的 attempt 是否绝不被覆盖、accepted 仅移指针。
4. **judge 两入口不串线**（[retry.py](../../../../src/agent/judge/retry.py)）：`repair_feedback` 注入 prompt、`judge_retry_context` **只进带外 sink 绝不注入**。这是不变量 6，重点核。
5. **矩形 coverage completeness 的面积对账**（[kernel.py](../../../../src/validator/checks/kernel.py) `_coverage_completeness`）：expected internal interface area（同层共享边墙 + 跨层楼板重叠）vs realised 互逆面积/2 的算法是否正确、容差是否合理、负例（互逆墙改 Outdoors）是否真被逮。**这是抓「两侧都 Outdoors 洞」的关键 block，最值得挑刺。**
6. **zone closure by-sums**（[kernel.py](../../../../src/validator/checks/kernel.py) `_zone_closure`）：split-pairing 把面切碎，故用 summed floor/ceiling 面积 + summed wall 宽对账 zone 多边形——有无漏判/误判？
7. **MEP 引用图 + 对象语义**（[mep.py](../../../../src/validator/checks/mep.py)）：load→zone/schedule 用**字段索引**（field[1]=zone、field[2]=schedule）取，是否对当前 authoring 格式稳健、换格式会不会静默失效？SimpleGlazing standalone / NoMass 正热阻判定是否正确。
8. **facade image-local→world**（[facade.py](../../../../src/agent/correction/facade.py)）：约定表 + mirror 翻 sign 是否自洽；sm20 East 立面 legacy note 把 local-x 映射到 +world_y（与我实现的「标准约定」相反）——我靠 window-on-wall + 跨图 reconcile 兜底而非信 VLM 自声明，这个取舍是否站得住？
9. **fail-closed 边界**：parse 失败（[mep.py](../../../../src/validator/checks/mep.py)）→ ERROR→block；EP `.end` 缺失（[assembly.py](../../../../src/validator/checks/assembly.py)）→ ERROR 非 PASS（H3 类）；deterministic check 自身抛错是否都 fail-closed。
10. **validate_case 非侵入性**（[validation_run.py](../../../../src/agent/execution/validation_run.py)）：是否真没改 run_pipeline、是否会因读不到某产物而误判 PASS（漏跑某段=静默放行的风险）。

## 4. 验收标准

- 实现忠实施工方案 M0–M4 各条；无对 `IntakeOutput`/`run_pipeline`/下游的隐藏改动。
- 确定性 check 每条有正反单测；真坏 fixture 确实触发对应 block/flag。
- 无 fail-open 路径（失败/异常/缺产物不得静默 PASS）。
- policy≠fact / append-only / judge 不串线 / 失效 DAG 四条机制无破绽。
- 分级 findings（High/Medium/Low）+ 证据 + 建议修复；判 verdict（APPROVE / CHANGES REQUESTED）。

## 5. 如何跑

```bash
python -m pytest -q                      # 全量 191 绿
python -m pytest tests/test_execution_foundation.py tests/test_checks_kernel.py -q
python -c "from src.agent.execution import validate_case; \
  r=validate_case('case_tests/e2e_tests/sm20_anchor'); \
  print('blocked', r.blocked, r.blocking_summary)"   # sm20_anchor 正 baseline
```

> 容器内 deepseek MCP 不可达；如需本地跑审阅脚本见 `tests_scripts/deepseek_review.py`。审阅文档请落 `AI_agent/logs/review/review/2026-06-16_pipeline_0-5_validation_implementation_review.md`。
