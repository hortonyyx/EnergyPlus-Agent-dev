# 分工模式首稿与返工接口修复初稿

状态：实现与离线验证完成，待主助手集成和真实小测；未调用 work model、API 或 DeepSeek。

## 已证问题

- 2026-10-08 的四份平面首稿中，三份写入了不存在的 `printed_segments_mm`；严格格式只接受 `dimension_chains[].segments_mm`。当前 guidance 与 `trial_plan_bim` 工具描述都写成含混的 “printed segments_mm”，和 schema 的实际字段名不一致。
- 首轮 F1 在首次试建前已有较长观察与输出，仍同时出现格式、拓扑理解和开口理解错误；不能用更多首稿前叙述代替结构完整的声明和尽早试建，也不能靠删墙、漏门或改变房间连通来消除错误。
- 调度员重派 F1b/F2b 时只携带失败状态和泛化的“完成完整稿”，没有把上一任务已经落盘的具体试建对象、原因、修订提示和证据引用交给新读图员，导致再次从原图探索。

## 有界改法

1. 统一 guidance、工具描述与格式示例，只把 `segments_mm` 写成字段名；强调理解整图并形成结构完整声明后及时试建，首稿包含真实墙、开口、空间种子和连接关系。
2. 保留原有 `issues` 为调度员可选补充，不增加关键词、长度或对象名校验。re-dispatch 自动从上一任务事件中提取精简结构化 handoff：任务状态、最近失败/未知工具结果、对象路径、原因、建议、事件与完整回执引用。
3. 失败反馈继续保留完整落盘回执；模型侧只显示定位和下一步所需字段，避免重复大段审计内容。
4. 失败任务若已有完整、可解析且产生数值编译产物的声明，后继同图/同角色/同目标任务把最近一份这样的失败声明作为可编辑基线。原图、声明、数值产物、回执和 profile 均按 SHA-256 回读；该基线明确保持失败/未验收状态，必须在新任务中重新试建成功才能提交。

## 预计文件与验证

- 生产代码：`src/agent/runtime_roles/guidance.py`、`readers.py`、`trial.py`、`session.py`；只有现有反馈无法给出精确对象时才触及 `src/agent/geometry/plan_input.py` 或 `plan_feedback.py`。
- 测试：`tests/test_role_guidance.py`、`test_role_readers.py`、`test_role_session.py`、`test_role_trial_feedback.py`，必要时 `test_role_trial.py`。
- 行为检查：复用上一轮保存的格式失败与几何失败回执，确认 `printed_segments_mm` 不再出现在提示，失败对象/动作可进入返工任务，完整证据仍可追溯。

## 边界

本包不改 runtime 循环/预算，不改 geometry 规整算法，不新增角色或固定唯一流水线，不以删墙或省略开口换取编译通过。真实读图质量仍需主助手批准的一层平面读图员小测验证。

## 已实现

- guidance 与 `trial_plan_bim` 工具描述只使用合法字段 `segments_mm`，完整列出首稿顶层字段和尺寸链字段；首稿要求改为理解整图和分块、形成完整结构后及时试建，不鼓励逐线量完或长篇叙述后才动手。
- 试建失败增加 `next_action.objects`，从既有 `repair_hint.path` 与 `format_errors[].path` 确定性生成；长 compiler reason、alignment 重复错误、长 changes 和 junction 列表改为模型侧有界摘要，完整原文继续由 `receipt_file`、JSON pointer 和 SHA-256 引用。
- 已观察的开口高度越层与宿主失败现在分别定位到 `plan.openings[i].z` 或 `plan.openings[i]`，给当前值、楼层高程范围或宿主/点位修订动作；明确保留原图中的墙和开口，不为通过编译而删除或补造。
- re-dispatch 不再要求调度员重复填写 `issues`。新任务会自动收到 `previous_task_handoff`，包含上一任务状态、最近已落盘的失败/unknown 工具结果、对象与建议、事件 ID、完整 raw result 引用、trial receipt 路径和 reader record 哈希；`issues` 仍可补充新的图纸事实。
- 独立审查后的补修使 handoff 同时声明 `editable_draft`：只选择同一原图哈希下最近一份有完整声明和数值编译产物的失败回执。后继 `PlanTrial` 直接以它为 operations 基线，不把它登记为通过或 accepted，也不从 outcome unknown 的调用推断成功。
- 失败基线引用的 measurement profile 会先核验原图与文件哈希，再复制到新 reader 的 `pixel_profiles` 并登记到新任务引用作用域；未改对象的 `source_refs` 原样保留。新改对象仍由新任务的 operation 提供定位来源。旧 view 名称只作为既有来源描述保留，需要新检查时仍查看当前任务的同一原图。
- 精简 handoff 现保留高度错误的 `current`、`allowed_floor_bounds_m`，以及既有 `*_remaining` 计数；不会因摘要丢失当前值、允许楼层范围或尚待修复的对象数。

## 离线验证结果

- 定向与相邻回归：`47 passed`；另组 `48 passed, 1 deselected`。deselect 的真实工具服务用例会按设计检查已登记 domain 版本，工作树改动未登记时拒绝启动；本任务禁止改版本登记，因此未绕过。此前包含同文件的较小定向组为 `36 passed`。
- 上一轮 F1b `trial_002` 原完整回执约 138,198 字符；模型侧投影从旧实现约 48,612 降到 15,538，仍保留 `plan.partitions[0].points[0]`、8 条可执行 junction repair 及完整 reason/repair_hint 引用。
- 上一轮 F2b `trial_005` 原完整回执约 118,363 字符；模型侧投影从约 28,971 降到 12,431，保留 `plan.footprint_pixels` 定位和完整 changes/operations/plan_revision 引用。
- 用上述真实失败回执构造一次离线 re-dispatch handoff：约 6,697 字符，带对象路径、8 条 junction 修订、event、receipt 和 reader record SHA；无模型/API 请求。
- 直接对上一轮 `trial_009`–`011` 的原始声明与原因重算反馈：高度失败定位 `plan.openings[0].z`、允许 `[4.0, 7.6]`；两项宿主失败定位 `plan.openings[13]`、`plan.openings[16]`。
- 补修后的最小真行为测试使用一份含旧 profile 和旧 `source_refs` 的完整失败声明启动新的 reader trial，只更新 `openings:D1.z` 后通过；另一开口、全部 partitions 与旧来源保持逐项相等。错误原图哈希被拒绝，旧失败声明不能通过 `verified_plan`。
- 补修定向回归：`36 passed, 1 deselected`（trial/session/readers；deselect 仍是禁止在未登记工作树启动真实工具服务的版本校验用例），反馈/guidance 相邻组 `7 passed`；测试进程报告 `0 provider calls`。

## 小测入口

历史可复用入口为 `AI_agent/logs/experiments/2026-10-06_plan_reader_probe/run_probe.py`，但它硬编码 sm24 F1、旧 domain 版本和旧评分参照。主助手已另写本轮 `run_plan_probe.py`，真实单层小测由主助手负责。
