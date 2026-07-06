# M1 · 生产路径口径收口 + parity 锁(执行简报,待 Codex 方案审)

> 缘起:Fable5 体检(`AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md` A2-1/A2-2/A1-2)。
> 分工:Claude 出本简报 → Codex 方案审(xhigh)→ Claude 裁决 → Codex 执行 → Claude 复核(pytest+diff)。
> 纪律:改 src/tests 前按 CLAUDE.md §5#4 备份到 `backup/src_history/2026-07-06_m1_parity/`;零 golden 改动;零契约改动。

## 1. 要修的三件事

### 1a. run_pipeline 静默丢弃 0_reading 结构化不变量(体检 A2-1,HIGH 活跃)
- 现状:`check_reading_view`(`src/validator/checks/reading.py:87-152`)产 ~15 个 check_id;`validate_case` 全量跑(`src/agent/execution/validation_run.py:128-140`);但 `run_pipeline` 只经 `compute_evidence_debt_from_vector_dir`(`src/agent/pipeline.py:821-826`)间接跑,`project_evidence_debt` 只保留 `EVIDENCE_CHECK_IDS` 6 个 id(`src/agent/execution/evidence_preflight.py:96-99`),其余含多个 INVARIANT 被静默丢弃(不 raise/不 warn/不落盘)。
- 修法:run_pipeline 在 reading 输入读取处对每个 `*_view.json` 跑完整 `check_reading_view`,产 `0_reading/reading_checks.json`(这正是 contracts §1 登记的"应补"产物),经 `_gate_self_check_report(stage="0_reading", ...)` 走与 1/2/4 段**相同的 run_profile 分档**(exploratory=写产物+warn 续行;golden/regression=fail-closed raise)。
- **避免双算**:evidence preflight 内部已经调了同一个 `check_reading_view`——重构为"先算 reports,一份喂 gate、同一份喂 `project_evidence_debt`"(或让 `compute_evidence_debt_from_vector_dir` 把完整 reports 一并返回)。`evidence_debt.json` 的形状尽量字节兼容;若必须变,列出所有消费者并说明。

### 1b. S5 `check_assembly` 报告从未被门禁消费(体检 A2-2,结构性死门)
- 现状:`run_pipeline` 算并写盘 `assembly_report`(`pipeline.py:1011-1017`)但不送 `_gate_self_check_report`(全文件仅 correction/kernel/mep 三处调用,行 917/953/994);真正 raise 的是旁路裸 `validate_contract`(`pipeline.py:1018-1028`)。当前行为等价,但未来给 check_assembly 加新 check_id 会静默失去强制力。
- 修法:assembly_report 接入 `_gate_self_check_report("5_intakeoutput", ...)`;**硬约束**:
  - contract 违规必须**保持全 profile 硬 raise**(S5 特例,现有语义零回退,相关既有测试必须原样绿);
  - `validate_contract` 不得跑两次(共享同一次结果;check_assembly 本就是它的包装);
  - `assembly_checks.json` 内容/路径不变。

### 1c. parity 锁(体检 A1-2 的最小可行形态)
- 目的:防止两路(run_pipeline inline vs validate_case)检查清单再次静默漂移——本次体检抓到的 1a/1b 就是漂移实例。
- 修法(**最小档,非全量 registry 重构**):新增 parity 测试(如 `tests/test_check_parity.py`):对同一个合成 run 产物,分别收集 run_pipeline 门禁消费的 check_id 全集与 validate_case 报告的 check_id 全集,断言相等,**豁免表显式登记**(`kernel.artifact_consistency`、S3 specs 文本相等、`check_ep_baseline`、A8 pre-core evidence sidecar 双份并存)。实现方式(共享常量表/轻量 registry 模块)由执行者选最小侵入方案;**全量 check registry 重构显式 out of scope**(另立 initiative)。

## 2. 验收
- 新增测试:① golden profile 下 reading INVARIANT 违规(如非法 pen)→ run_pipeline raise;② exploratory 下同输入 → warn+续行且 `0_reading/reading_checks.json` 落盘;③ monkeypatch check_assembly 注入假 blocking id → golden raise(证明死门已接活);④ parity 测试本体。
- 全量 pytest 通过;**零 golden 改动**(现有 anchors 在 validate_case 口径下本就全过这些检查,预期无回归——执行时验证此假设,若有 anchor 意外挂,停下来报告而不是改 anchor)。
- `intake_node` 默认 exploratory 零新硬失败(向后兼容)。

## 2b. 裁决(2026-07-06,Codex 审 APPROVE-WITH-CHANGES,6 findings 全采纳,本节为定案)

1. **S0 时序定案(finding 1/3)**:compute S0 full reports 一次 → 建 `_stage("0_reading")` 目录并写聚合 `0_reading/reading_checks.json` → `project_evidence_debt`(同一份 reports)→ 写 `1_correction/evidence_debt.json`(**字节形状不变**,extra=forbid 模型不动)→ **既有 A8 evidence raise 原样保留**(消息/测试不动)→ 新 S0 gate(`_gate_self_check_report`,profile 分档)放在 A8 raise 之后。两个 sidecar 都是 write-before-raise。
2. **S5 定案(finding 2/4)**:`check_assembly` 加 `run_profile` 参数、两路调用方线程化;单次计算;contract 违规从 report 提取→**保持全 profile 硬 raise**(现消息+`contract_issues.json` 原样)→其余(未来)blocker 走 `_gate_self_check_report`。`assembly_checks.json` 路径/内容不变、不双写。
3. **parity 定案(finding 5)**:测试侧 collector 读 run_pipeline 实际落盘的 `*_checks.json` vs `validate_case(...).reports`,归一 S0 per-view 键(validate_case 是 `0_reading::{stem}` per-view、生产是聚合),豁免表显式登记:`kernel.artifact_consistency`、S3 specs 文本相等、`check_ep_baseline`、A8 pre-core sidecar。不建生产 registry。
4. 执行时只跑目标测试(全量 suite 由主控在 M1+M2 合流后统一跑一次,避免并行批次互踩)。

## 3. 审阅需求(Codex 方案审重点)
1. 1a 的 gate 位置与时序(reading gate 在 correction 之前;与 evidence preflight 的先后关系)是否有隐患;
2. `evidence_debt.json` 形状兼容性——找出全部消费者;
3. `reading_checks.json` 写入点与 validate_case 是否有写冲突(validate_case 现在写不写这个文件?);
4. parity 测试的实现路线(常量表 vs 轻量 registry)哪个更不易烂;
5. 1b 改法有没有破坏 S5"全 profile 硬 raise"的既有测试;
6. 有无我漏掉的行为变化面。
