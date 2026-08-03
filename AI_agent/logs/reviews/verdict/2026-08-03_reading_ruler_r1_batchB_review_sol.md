# R1 修尺子 · 批 B 交叉对抗审（sol）

- 日期：2026-08-03
- 被审提交：`627efac` + `2bb189e` 中 `run_policy_freeze.py` / `run_config.py` / `isolation.py` / `checks/schema.py` / `checks/view_manifest.py`
- 性质：r1 前状态的跨家族对抗审；只读审阅，破坏性探针仅在 `/tmp`
- 总判定：**调查中（最终结论见完成稿）**

## 0. 结论与计数

待代码审计、活体探针与全仓测试完成后填写。

## 1. P-1…P-9

### P-1 · policy hash 收窄安全性

**暂判不成立，待活体探针补强。** 已穷举执行日志点名的四个 toggle：

- `validation_scope` 会在 `src/agent/execution/validation_run.py:94-97` 直接跳过 0–4 的 gate① validators，改变报告集合/事实行；
- `require_ep` 会在 `validation_run.py:120-125` 增加一个 fail-closed 的 `downstream.build` ERROR；
- `confirmation_policy` 会在 `validation_run.py:432-442` 改变最终 `blocked`；
- `judge_enabled` 只控制 gate② 是否启动（`src/agent/execution/step_orchestrator.py:313-325`），未找到其改变 gate① 事实的路径。

因此至少前两项满足派工单要求的证伪形态：同一 `(capability_profile, run_profile)` hash 下可以改变 gate① 事实/阻断面。更严重的是“非哈希上下文有记录”也没有真正接线：唯一生产调用 `cmd_provision` 在 `scripts/tool_scripts/run_stage.py:2234-2238` 根本不传 `context`，仓内也没有第二个 `provision_run_policy` 生产调用者。

### P-2 · `unknown` / `declared_false` / legacy 全链不折叠

**暂判不成立，待字节级探针补强。** 新的 manifest/checker 主路径确实保留三态（`src/agent/execution/view_manifest.py:383-396`；`src/validator/checks/view_manifest.py:70-100`；`src/validator/checks/reading.py:501-527`），但旧的正式验证/记录路径仍调用 `dimensioned_view_names()`，该函数只接收字符串并静默忽略结构化对象（`src/agent/execution/case_metadata.py:51-73`）。`validate_case` 随即把它折回 `view_metadata={"dimensioned": bool}`（`src/agent/execution/validation_run.py:127-142`）；`compute_reading_report_from_vector_dir` 也同样折叠（`src/agent/execution/evidence_preflight.py:201-227`）。因此 record/report 与 correction evidence-debt 路径上，结构化 `unknown` 与 `declared_false` 可落成相同的 `legacy_default` checks 行。

另有 provenance 断线：manifest 中的 `authority/source_hash` 在 `check_reading_stage` 只被降成一个 state 字符串，`_evidence_meta` 没有 source hash（`checks/view_manifest.py:72-100`；`checks/reading.py:209-216`）。L-23 的测试名声称 `with_source_hash`，实际只断言 state/message（`tests/test_reading_ruler_r1_batchB.py:243-266`）。

### P-3 · 真实 sm24/sm21 manifest 保哈希并可真实评分

调查中。

### P-4 · L-10/L-11 证明 disposition-only 差异

调查中。

### P-5 · L-21 fixture 与真 sm24 同构且不空转

调查中。

### P-6 · 产品不能决定考卷

调查中。

### P-7 · neuter 自查真实性与连带

调查中。

### P-8 · 明令禁止清单

调查中。

### P-9 · 复杂度可扩展性

调查中。

## 2. Findings

以下为新增同族证据；不把 orchestrator 已披露的 MAJOR-1 / MINOR-1 重计为本报告 finding：

1. **候选 MAJOR：冻结政策只接到 reading checker，未成为整个 run 的 EffectiveRunPolicy。** `cmd_run/cmd_flow` 的后续 correction/model/grade 继续消费局部 `policy`（例如 `run_stage.py:254-309,612-627,1303-1323`）；typed scoring 的严格拒绝也由该局部 `run_profile` 决定（`:1413-1420,1455-1473`）。`record_baseline` 更是重新构造 `RunPolicy(require_ep=..., run_profile=...)`，并把 capability 默认为 rectangular（`scripts/tool_scripts/record_baseline.py:485-503`）。所以即使先显式 provision 为 regression，checks、score、record 仍可在同一 run 内各认不同档。
2. **候选 MAJOR：L-20 fail-closed 在写入两件冻结产物之后才 raise。** `provision_run` 顺序是先 `provision_view_manifest`、再 `provision_run_policy`，最后才 `validate_dimensioned_applicability`（`src/agent/execution/run_provision.py:84-93`）。失败 run 已具备 isolation build 所需的 manifest + policy；而 isolation build/merge 不再调用 L-20 gate，故调用者忽略一次失败退出后仍可能继续。
3. **候选 MAJOR：L-12 只挡“另一个合法值”，删声明/改非法值可绕过。** `_declared_policy` 将缺文件、坏 YAML、非法 profile 都归一成 `None`（`run_policy_freeze.py:160-183`），resolver 只在非 `None` 时比对（`:269-280`）。现锁只测 `regression→dev`（`tests/test_reading_ruler_r1_batchB.py:448-476`）。
4. **候选 MAJOR：L-13 锁绕过真实 CLI。** 单测直接把 `None` 传给 `provision_run`，但全局 argparse 默认已经是 `exploratory`（`run_stage.py:2255-2260`）；`cmd_provision` 把该默认当作显式声明（`:2229-2237`），因此“无 config、无显式 CLI”仍会成功冻结 exploratory。
5. **候选 MAJOR：适用性 source provenance 记录了但未守。** `_structured_dimensioned_map` 只检查 `source.reviewer`，不要求 `image_sha256/date/basis`，也不把 `source.image_sha256` 与实际 entry image hash 比对（`view_manifest.py:717-771`）。测试 fixture 固定使用明显不是真图 hash 的 `"0" * 64` 且期望通过（`tests/test_reading_ruler_r1_batchB.py:61-71`）。

r1 锁形态将在完成探针后给出。

## 3. 清单外自主发现与证伪失败尝试

代码扫描额外发现：`dimensioned_views` 的 mixed list（字符串 + 对象）在 `_structured_dimensioned_map` 中被静默当 legacy（`view_manifest.py:736-741`），而不是拒绝畸形输入；对象声明会被忽略。待探针确认其下游表示。

## 4. 独立测试与探针

调查中。

## 5. Review ask

待最终结论。

---

## ⚠️ orchestrator 后记（2026-08-03，sol 会话被中断后补）

**本报告是未完成稿**：sol 在 P-3…P-9 尚未开跑时被其平台的内容策略中断
（`ERROR: This content was flagged for possible cybersecurity risk`，累计 404,474 tokens）。
`## 0 结论与计数`、`## 4 独立测试与探针`、`## 5 Review ask` 均为空。
**⛔ 不得把本文当作完整的交叉对抗审结论。**

**已交付的部分价值很高**：P-1 / P-2 两条承重命题各给出「暂判不成立」的具体路径，
外加 5 条候选 MAJOR + 1 条清单外发现。**但全部是读码推断、零探针。**

**orchestrator 已逐条独立核实 ⇒ 全部属实**，并在核实 F-3 的过程中挖到一条更硬的
（`run_config.yaml` 里把档位拼错一个字母 ⇒ `_parse_run_profile` warn + ignore ⇒ 静默降回 exploratory；
而原派工单 §2.1 #5 逐字要求「非法 ⇒ fail-closed」）。

**⇒ 合并后的必修清单、严重度裁定与锁要求见
[r1 返工派工单](../request/2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md)。**

**P-3…P-9 未完成部分的处置**：不在 r1 之前补跑（那是审一个已知要变的状态），
**改为 r1 落库后连同修复一起重新交叉审**。
