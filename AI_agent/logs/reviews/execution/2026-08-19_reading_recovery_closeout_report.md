# Reading Recovery 本轮收口报告

> 日期：2026-08-19
>
> 分支：`6.15_ValidationArchM0toM4`
>
> 基线：`d353a04`（`08.18_GovernanceShift_P0Speed_ReadingRegressionGate_SourceTreeRepro`）
>
> 范围：reading 恢复脚手架 N1–N3b、N4 Haiku 单图诊断、07-07 历史树证据复核
>
> 状态：实现已提交；N4 未批准、未合并为正式 reading；根因边界已收窄但尚未归因到单一模型或单一代码改动

## 一、执行摘要

本轮完成了四个实现节点和一个诊断节点：

1. 用隔离包内的中性 worked example 替代对其他 case 历史 reading 的引用；
2. 将 pilot 审批改成外部、持久化状态机，阻止 reader 自批后进入 batch；
3. 为 reader 启动补齐模型、运行器、prompt、输入、设置、会话形态和反馈的可复算 provenance；
4. 将实验 directive 绑定进 experiment spec，避免实际 prompt 与记录口径分叉；
5. 在硬隔离、单图、同会话、精确 Haiku model ID 下执行 pilot r1 + 一轮纯过程反馈 r2。

N4 没有恢复 reading：r1、r2 离线重判均为 **墙 0/4、窗 0/3**。reader 调用了 CV 工具，也读取了正确的线峰证据，但把错误的绿色标记当作标定锚，得到互相不一致的 `78 px/m` 与 `91.25 px/m`，再用这些数写出错误墙位 `x=5.71/8.00`、`y=4.16`。反馈后核心几何没有改变，pilot 始终未批准。

本轮同时复核了此前“在 07-07 好 reading 历史树上也无法复现”的说法。严谨结论是：

> 在正确历史代码、逐字节相同输入、相同 model ID 下，一次高度近似复现失败；但它使用当前 Claude CLI 而非原 Agent-tool 子代理，主控模型、反馈文本、上下文压缩和审批过程也不相同，因此不能称为完整历史重放，不能据此把根因定为 Haiku 模型本体漂移。

当前最稳妥的工程判断是：**失败发生在“证据 → 几何应用”的受控执行层**。模型可以获得并调用测量能力，却仍会选错锚、忽略交叉校验、用自述替代验收。恢复路线应把关键步骤改为机器状态机和硬门，而不是继续依赖模型自觉遵守长提示词。

## 二、本轮提交节点

### N1 — Neutral Worked Example

- commit：`159ada5dec8027be1b6133f98744d6fa3cb8242f`
- 标题：`08.18_ReadingRecovery_N1_NeutralWorkedExample`
- 主要内容：
  - 新增隔离模板 `src/agent/execution/isolation_templates/worked_example_plan.json`；
  - 隔离构建时投放中性示例，不再要求 reader 读取其他 case 的历史 reading；
  - kickoff 改为使用隔离包内示例；
  - 增加模板存在性、内容和隔离边界测试。

### N2 — External Pilot Approval Gate

- commit：`0eefa6f93551881f8c645146c6b1124de968ad8a`
- 标题：`08.18_ReadingRecovery_N2_ExternalPilotApprovalGate`
- 主要内容：
  - 新增持久化 `pilot_review_state.json`；
  - pilot、feedback、approval、batch 放行由外部控制；
  - 未批准时禁止 batch；
  - 审批绑定已审 pilot 的路径与哈希；
  - reader 不能靠回复中的“complete/approved”自批；
  - CLI 增加相应实验控制入口和回归测试。

### N3 — Reproducible Reader Runs

- commit：`7d0fce385d5c6f9391fbb0f10267ccf540197830`
- 标题：`08.18_ReadingRecovery_N3_ReproducibleReaderRuns`
- 主要内容：
  - 新增 `reading_experiment_spec.json`；
  - 固定并记录 model ID、运行器路径与版本、输入清单、manifest、settings、guard、prompt、feedback、session form；
  - 新增 append-only `reader_invocations.jsonl`；
  - prompt 与敏感参数按哈希记录，避免把原文或密钥写入 provenance；
  - 支持 start → resume same session 的可审计运行。

### N3b — Bind Experiment Directive

- commit：`34645430d23d1f7ce518e11bfa72bd64de36bb12`
- 标题：`08.18_ReadingRecovery_N3b_BindExperimentDirective`
- 主要内容：
  - directive 内容进入 experiment spec 绑定哈希；
  - 启动前验证 directive、run config 和 spec 一致；
  - 避免“记录说一种实验，实际 prompt 发出另一种要求”。

### 实现规模

相对基线 `d353a04`：

- 9 个文件变更；
- 1,338 行新增；
- 54 行删除。

## 三、测试与验证

实现节点完成后执行的验证：

- 全量测试：`2923 passed, 14 xfailed, 212 warnings`；
- N3b 相关测试：`335 passed`；
- 四个实现节点均独立提交，便于回滚和逐节点比较。

N4 归档前再次执行离线 scorer，未向 reader 暴露 GT：

| 快照 | 墙 | 平面窗 | 结论 |
|---|---:|---:|---|
| pilot r1 | 0/4 | 0/3 | 失败 |
| pilot r2 | 0/4 | 0/3 | 反馈后核心几何未改善 |

## 四、N4 诊断运行

运行目录：

`case_tests/e2e_tests/sm21_anchor/run_2026-08-18_recovery_N4_single_plan/`

### 4.1 固定配置

- case：`sm21_anchor`；
- 唯一输入：`1f_view`；
- model：`claude-haiku-4-5-20251001`；
- runner：Claude Code `2.1.198`；
- session policy：`start_then_resume_same_session`；
- session：`8e5c881d-1ab5-4b7f-a38b-69ae29a454c0`；
- guard：`observe`；
- staging：`/tmp/ep_isolation/sm21_recovery_n4_single_plan`；
- experiment kind：`single_plan_same_session`；
- pilot gate：启用；
- GT：仅在两轮停止后由主控离线评分，未进入 reader staging 或反馈。

### 4.2 r1

- 产出 9 个 wall strokes、9 个 window strokes、15 条 dimensions；
- 自报 `all_dimensions_transcribed=true`、`all_visible_strokes_captured=true`；
- 读取 CV 证据，但采用错误绿色标记标定：
  - x：`78 px/m`；
  - y：`91.25 px/m`；
  - 两轴差异约 15.6%；
- 写出的主要内墙位置为 `x=5.71`、`x=8.00`、`y=4.16`，与目标墙位不符；
- scorer：墙 0/4、窗 0/3；
- pilot 未批准。

### 4.3 一轮外部反馈与 r2

反馈只指出过程问题和自相矛盾，不包含 GT 坐标或正确答案。反馈要求重新校准、解释两轴分歧、按证据重建墙/窗并保持自检诚实。

r2：

- 使用同一 session resume；
- 产出 8 个 wall strokes、9 个 window strokes、15 条 dimensions；
- 核心错误坐标仍为 `x=5.71`、`x=8.00`、`y=4.16`；
- scorer 仍为墙 0/4、窗 0/3；
- `pilot_review_state.phase=feedback_issued`；
- `approved_at=null`、`approved_pilot_path=null`；
- 没有进入 batch，没有覆盖正式 reading，没有合并为正式成绩。

### 4.4 N4 说明了什么

已经证实：

1. 不是单纯“看不到图片”：reader 能读取图和 CV sidecar；
2. 不是单纯“没有工具”：reader 能调用并引用工具输出；
3. 不是单纯“缺一句 measure-before-draw”：directive 已绑定并进入同一实验；
4. 主要断点在证据选择、标定交叉校验及证据到几何的应用；
5. 自报完成度不能作为审批依据；
6. 单轮自然语言反馈不足以强制模型推翻已经形成的错误几何解释。

尚未证实：

1. Haiku 模型权重或服务端本体发生漂移；
2. C2 建筑复杂度升级直接破坏 reading；
3. 硬隔离本身直接破坏视觉能力；
4. 某一个 repository diff 是唯一元凶。

## 五、07-07 历史树复核

### 5.1 已确认的等价项

历史 worktree：`/workspaces/ep_707_tree`，detached HEAD：

`723b0f98ed37285b66cb3d1d30caa8e42eb01a74`

已核对：

- tracked tree 位于正确历史 commit；
- 六张源图和 `testdata_prompt.json` 与当前 case 逐字节一致；
- 复现 model ID 为 `claude-haiku-4-5-20251001`；
- 五轮反馈使用同一 session；
- 保存的 376 行 transcript 含 64 次工具调用；
- 工具调用审计未发现读取 `gt.json`、`test_baseline`、历史 run 或 verdict；
- 该次高度近似复现最终为墙 2/9、窗 0/7。

### 5.2 未复原的关键变量

原 07-07 成功运行：

- `cold-start Agent-tool sub-agent (model="haiku")`；
- Fable 5 主控；
- 一次 pilot-review 返工；
- 6/6 图片被测量；
- 92 次 CV 调用，其中 55 次 `crop_zoom`；
- 最终墙 9/9、平面窗 7/7、立面窗 15/15。

8 月 16 日历史树复现：

- 当前 Claude CLI `claude -p --resume`；
- Opus 5 主控；
- 原始 07-07 spawn prompt、Fable 完整反馈和原 Haiku transcript 未随 run 保存，本机现存相关 transcript 最早始于 7 月 24 日；
- 连续四次 review 后仍只有 4 次 `crop_zoom`、只测 1/6 图片；
- 主控在两个条件尚未验收时发出条件式放行，后五图零 CV；
- 会话后半段发生 Claude CLI 自动上下文压缩，错误标定和错误尺寸链进入摘要。

因此本轮修正了此前过强表述：

> 可以说“当前 Haiku + 当前 Claude CLI/runtime 在旧树上也失败过”；不能说“原历史执行环境已经被完整复现且确定失败”。

## 六、根因结论边界

### 可以落地的结论

当前故障不是简单的图片、schema 或工具缺失。失败组合表现为：

- 有视觉输入；
- 有 CV 工具；
- 有明确 directive；
- 有同会话反馈；
- 仍然选错标定锚、忽略两轴不一致、把错误证据写入几何并自报完成。

工程根因可以描述为：

> reading 的关键测量、交叉校验和批准仍由同一生成模型自由执行和自我证明；当前 agent runtime 下，这一控制结构不能稳定保证证据被正确应用。

这比“Haiku 不听话”更精确，但仍不是对底层模型变化的单因果归因。

### 不能落地的结论

- 不能把 model ID 相同直接等同为 agent runtime 相同；
- 不能由一轮历史树近似复现排除所有 repository/harness 变量；
- 不能把 hard isolation 或 C2 升级直接定为元凶；
- 不能把一次成功或一次失败当成稳定性证明。

## 七、恢复路线与把握

### 7.1 推荐顺序

1. 先复跑 GPT-5.4-mini 自己的历史成功栈：`ebddada`、Codex CLI 图片输入、clean-room、prescan 预生成、pilot 审批、后五图独立/并行会话；至少两抽；
2. 将 measure-before-draw 改成外部机器状态机：CV 证据存在 → 标定通过 → 尺寸链闭合 → 候选有 accept/reject → 才允许写 geometry；
3. 禁止条件式批准；pilot 只有 pass/rework，两步未验收就不能 batch；
4. 一图一冷会话，批准结果固化为 evidence packet，避免长会话压缩污染；
5. 程序负责标定求解、链求和、坐标换算和 schema 组装，模型只负责语义分类、文字转录和歧义报告；
6. 用 sm21 + sm24 各 2–3 抽验收，报告均值和最差抽，不只保留最好一次。

### 7.2 GPT 判别逻辑

- GPT 历史栈通过：支持 Haiku/Claude runtime 特异问题；
- GPT 历史栈通过、当前栈失败：支持后来 repository/harness 回归；
- GPT 连自己的历史栈也失败：支持模型服务、CLI/runtime 或共享环境变化；
- 两个模型只在统一当前 harness 下失败：共享控制层是更强候选，不能归因于 Haiku 单独退化。

### 7.3 恢复把握

- 恢复“受控、可重复地产出好 reading”：约 **75–85%**；
- 恢复“Haiku 单代理只靠提示词稳定自主完成”：约 **30–40%**。

前者把握较高，因为正确输入、CV 测量能力和历史跨模型成功都仍有证据；需要恢复的是控制结构，而不是从零创造视觉能力。

## 八、归档与工作树纪律

本收口提交只纳入：

- N4 诊断运行目录；
- 本报告。

以下既有未提交内容不属于本轮收口提交，保持原样：

- `AI_agent/CLAUDE.md`；
- `AI_agent/capability/reading/improvement_methodology.md`；
- `AI_agent/guides/codex_execution_protocol.md`；
- `AI_agent/logs/README.md`；
- `AI_agent/plan.md`；
- `AI_agent/logs/reviews/request/2026-08-18_reading_regression_external_investigation.md`；
- `AI_agent/logs/worklog/`。

## 九、本轮最终状态

- N1–N3b：已实现、已测试、已分节点提交；
- N4：已归档，失败，未批准，未进入 batch；
- 历史树：完成证据复核，撤回“完整历史复现失败”的过强说法；
- 根因：收窄到证据应用/执行控制层，模型本体与 runtime 尚未拆分；
- 下一判别实验：GPT-5.4-mini 自身历史成功栈；
- 本轮至此收工。
