# 09-09 纠偏：定性优先、容差规整与自动评价

## 用户要求与本轮结果

用户要求回看 sm21/sm24/sm25 的历史成功案例和 0–5 pipeline/gate。judge + GT 原为减少人工核对、自动看到运行效果，也为 CAD 模态接入积累资产；不应因 CAD 制图/数值细微误差长期陷入 GT 精修。pipeline、CAD 输入产物和 GT 都不要求逐点严丝合缝，核心是正确的丐版 BIM，定性大于定量。

本轮基于 `e5f686c1` 定向回看代码和历史产物，修订目标、评价、共同模型、架构、实现边界、计划与 case 指南；将新增原则同步到 Agent 入口和决策表。初稿中的人工逐房对账、误差统计优先安排已改为三案例自动定性基线、小扰动/真实错误对照及实际消费者修正。未改业务代码/容差配置，未调用模型、未执行新 EP 仿真。

## 已核对的历史产物

| 案例与路径 | 直接读取的证据 | 可复用的经验 |
|---|---|---|
| [sm21 07-02 run](../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e) | `2_modelling/building_geometry.json`：14 区/100 面/15 窗；`EP/EP_run/eplusout.end`：成功、6 warning/0 severe；J0/J1 清单均 pass | 0–5、judge、报告与 EP 链曾实际贯通，能复用；报告记录人工确认与证据 flags，不等于本次无人值守成绩 |
| [sm24 06-24 run](../../../case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading) | 几何：11 区/76 面/11 窗；EP 完成文件：成功、6 warning/0 severe；J0 的 L 形坐标及 J1 区数项为 minor | 历史报告把 11 区相对声明 8 区归因为非矩形空间的矩形分解。定性 judge 允许轻微表示差异继续；源房间身份仍应保留 |
| [sm25 run_win_e2e](../../../case_tests/e2e_tests/sm25-L_anchor/run_win_e2e) | 状态：J0/J1 `judge_pass`，2_modelling `deterministic_defect`；已有 27 区/208 面/31 窗 | 不能把本次直接停止归因于 judge 的逐点 GT 比较。复用现有可视/诊断产物，针对实际 gate 消费者处理 |

本轮在 `sm25-L_anchor` 下未找到 `eplusout.end`，也在本地 `backup`/`data` 中按 sm25/smalloffice_25 目录名查找，未补定位到 EP 成功记录；不据此否认用户提及的其他成功产物。已定位的 sm25 reading/correction/modelling 仍纳入三案例资产，后续遇到其他旧路径再补索引，不因此阻塞推进。

## 设计与源码核对

- 历史 [识图建模设计 §1/§3](../../archive/2026-09-08_management_rebuild/original/AI_agent/capability/recognition_modeling_capability.md) 明确“定性 > 定量”“容差内重生成”；历史 [阶段合同](../../archive/2026-09-08_pre_takeover/architecture/pipeline_stage_contracts.md) 规定结构化清单，轻微 flag、严重/致命打回。本轮只采用用户重申的产品原则，不恢复历史审批或旧的两腿定义。
- `stage_runner.py` 定义阶段依赖，`step_orchestrator.py` 消费 gate/judge 决策；`CheckReport` 已有 BLOCK/FLAG 区分；`StageVerdict` 已按 pass/minor/severe/fatal 而非总分决定放行，J0 存在 correction-recoverable 例外。
- `judge/executor.py` 当前启用 J0/J1，J4 停用；`run_stage._draw_reading` 仍只检查已有观测，故不能把历史受驱动的端到端成功等同于当前无人值守入口。
- legacy/typed 评分存在 0.30 m 墙位、0.40 m 窗位置等容差；as-drawn 平面为 0.08 m 位置带，并考虑量化带。`judge_gt.yaml` 节点连接/轴对齐则为 0.001 m，as-drawn 分母从签字源 DXF 生成。不同数值属于不同消费者，不能断言整个 judge 都在要求毫米级吻合。
- `validator/interzone.py` 的 `_MIN_EDGE=0.10` 被 `checks/kernel.py` 升为 invariant；当前 sm25 的 0.065 m 面因此停止。代码引用历史 sm21 崩溃作依据；本轮未复现，未确认此阈值是当前 EP 的普遍需求。

执行原则与当前实现分别维护于 [评价](../../design/evaluation.md) 和 [实现](../../design/implementation.md)。下一步是有界离线对照及最短消费者改动，不是逐锁清理、全量 GT 重做或扩大所有容差。

## 验证

本轮为文档变更，`git diff --check` 通过，13 份变更文档的 130 个本地链接均可解析；检查 diff 和 Git 状态，不运行 pytest 全量。历史 `.end`、几何和 judge JSON 为本轮只读核对，未写作新实验成绩。
