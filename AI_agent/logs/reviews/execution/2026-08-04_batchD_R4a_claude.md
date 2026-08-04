# 批 D（判卷图恢复）+ R4-a（成绩分账）执行日志（施工 = Claude 侧执行档，独立 worktree）

派工单：[2026-08-04_batchD_and_R4a_dispatch.md](../request/2026-08-04_batchD_and_R4a_dispatch.md)
顺序：R4-a（先）→ 批 D（后）。

---

## 环境笔记（开工前）

本 worktree（`agent-a03990d733f96334f`）开工时 checked out 在一个陈旧、无关的本地分支
（`worktree-agent-a03990d733f96334f` @ `52698e3`，2026-06-10 era），与派工单声明的前置
`HEAD f254c56` 完全对不上。working tree 干净、`52698e3` 及其祖先在其它地方仍可达
（非丢失），故 `git reset --hard f254c56` 把本 worktree 的分支指针拨到派工单声明的
起点。**如实披露**：这是一次非常规的 worktree 状态修正，不在派工单纪律条款覆盖范围内，
但属于"不修就无法开工"的前置动作，未见其它更安全路径。

---

## R4-a · 成绩分账（`reading_mode` 溯源块）

### 设计

**记账口径**：逐字照抄 `AI_agent/CLAUDE.md` §1.5 #7——两条正式 lane
（`autonomous` / `controlled`），另有一个 dev 期职能（`dev_function`，不是第三条 lane，
不产生正式成绩）。

**挂载位置**（派工单授权由施工方判断，理由记录于此）：

- `reading_mode` 声明为 `run_config.yaml` 的可选 `reading_mode:` 段（与既有的
  `run_profile`/`capability_profile`/`models` 同层，操作员已经在编辑的同一份文件）。
- 冻结写入 `<run>/_run/reading_mode.json`，唯一写者 `provision_reading_mode()`；
  唯一只读消费者 `resolve_reading_mode()`（永不 raise，缺失 ⇒ `legacy_unknown`）。
  两者的"声明 → 冻结 → 解析"结构逐字仿照既有的
  `src/agent/execution/run_policy_freeze.py`（`provision_run_policy` /
  `resolve_frozen_run_policy`），这是本仓库已确立的同类先例
  （另一个是 `GeometryApproval` 的 `run_profile`/`capability_profile`/`source`/
  `legacy_defaulted` 四字段，R1-5 批次加的）。

**L-R2 fail-closed 的挂载点 —— 本轮最大的一处设计取舍，如实披露**：

派工单原文"新 run 若产不出 reading_mode ⇒ 不得静默按 autonomous 记"字面读像是要求
**每一个**新 run 都必须声明 reading_mode，否则拒绝。但全仓 `_draw_reading`/
`provision_run`/`record_baseline()` 这几条路径被 **数百个既有测试** 直接或间接调用
（`record_baseline()` 本身就有 27 处直接调用，`_draw_reading` 是几乎所有 gate①
测试的必经路径），没有一个声明过 `reading_mode:`。把 fail-closed 焊死在这些路径上
会大面积打红 2115 基线，明显超出 R4-a"小、prerequisite"的定位，且派工单纪律
明令"基线须保持 2115 passed + 10 xfailed 零红"。

**裁定**（施工方自行判断，供审阅方复核）：fail-closed 只焊在
`record_baseline()`——这是本仓库唯一的"这个 run 的分数从此成为正式记录"的时刻
（对应 CLAUDE.md §6 #12"记录这次跑 <case> <tag>"仪式），与 R4-a 自己写的动机
"决定后面所有实验的成绩记在谁头上"精确对应。`record_baseline()` 新增
`require_reading_mode: bool = False` 参数，**默认 False**（保 27 个既有直接调用零改动）；
唯一把它设为 `True` 的调用点是 `run_stage.py` 的 `flow --record` CLI 分支——
经 `grep -rn "cmd_flow(" tests/` + 逐个检查 `args.record`/`--record` 用法确认
**该分支在改动前零测试覆盖**（`tests/test_run_stage_flow.py` 24 处 `cmd_flow(` 调用
无一传 `record=True`），故把它焊死为 strict 对 2115 基线零风险，同时是
**真实存在、此后每个新 run 都会经过**的入口。

检查落在 `record_baseline()` 函数体最开头（`validate_case` 等重活之前），
使 L-R2 的锁与"其余产物是否是一次完整可跑的真实 run"完全解耦——锁只需要
`cmd_flow` 的阶段循环跑到 `--record` 分支即可，不需要构造一次端到端全绿的
真实仿真。

`lane` 与 `reading_agent` 一致性另加一条 `model_validator`：`autonomous`
按定义"零 reading-agent"，`controlled` 按定义"reading-agent 在场"——
两者不一致的声明本身就不合法，在 pydantic 校验层直接拒绝。

### 改动清单

- `src/agent/execution/reading_mode.py`（新文件，296 行）——
  `ReadingAgentInfo` / `ReadingWorkerAgentInfo` / `ReadingModeRecord` /
  `ReadingModeResolution` 四个 pydantic 模型 + `provision_reading_mode` /
  `resolve_reading_mode` / `require_reading_mode` 三个函数。
- `src/agent/execution/run_config.py:120-127`（`RunConfig.reading_mode: dict | None = None`
  字段）+ `:178-190`（`_parse_run_config` 里新增
  `reading_mode = raw.get("reading_mode") if isinstance(...) else None`）。
- `scripts/tool_scripts/record_baseline.py:32`（新增 import）+
  `:490`（`record_baseline(..., require_reading_mode: bool = False)`）+
  `:505-513`（函数体最前的 fail-closed 调用）+ `:565`（`resolve_reading_mode` 只读解析）+
  `:567`（`baseline["reading_mode"] = ...`）。
- `scripts/tool_scripts/run_stage.py:2561-2568`（`cmd_flow` 的 `--record` 分支
  新增 `require_reading_mode=True`）。
- `scripts/tool_scripts/report_assembly.py:765-798`（新增 `_format_reading_mode()`）+
  `:838`（`_render_model_config` 里插入调用）。
- `tests/test_reading_mode.py`（新文件，15 个测试，覆盖 L-R1..L-R4 + 底层事务）。

### neuter 自查（全部在 `/tmp/r4a_neuter` 隔离 clone 里跑，`PYTHONPATH=$PWD`）

| # | 摘掉的实现 | 预期变红 | 实测变红 | 连带 |
|---|---|---|---|---|
| 1 | `cmd_flow` 里 `require_reading_mode=True` 那一行 | `test_L_R2_flow_record_fails_closed_without_declared_reading_mode` | 该条 + `test_L_R2_flow_record_succeeds_with_declared_reading_mode`（同一改动的正反两面，均属预期） | 0（其余 13 条绿） |
| 2 | `ReadingModeRecord._lane_reading_agent_consistent` 整个 validator | `test_lane_reading_agent_contract_autonomous_rejects_reading_agent` + `test_lane_reading_agent_contract_controlled_requires_reading_agent` | 恰好这 2 条 | 0（其余 13 条绿） |
| 3 | `_format_reading_mode` 函数体换成 `return []` | `test_L_R1_report_lane_label_changes_with_declared_lane` + `test_L_R3_report_legacy_unknown_does_not_crash_and_does_not_impersonate_lane` + `test_L_R4_report_flags_dev_function_as_not_official` | 恰好这 3 条 | 0（其余 12 条绿） |
| 4 | `provision_reading_mode` 的 `declared is None: raise` 改成静默填 `lane=autonomous` 默认值（= 派工单点名的最危险失败形态"静默按 autonomous 记"） | `test_provision_reading_mode_fails_closed_on_absence` + `test_L_R2_flow_record_fails_closed_without_declared_reading_mode` | 恰好这 2 条 | 0（其余 13 条绿） |

四次 neuter 均在同一份隔离 clone（`git clone` 本 worktree 到 `/tmp/r4a_neuter`，
`git log --oneline -1` 确认落在 `794b47a`）上做，每次 `git checkout -- <file>` 复原后
复跑确认回到 15 passed 才做下一条。**第 4 条尤其值得记**：它精确复现了派工单原文
点名的失败形态（"缺失即 fail-closed，不得静默按 autonomous 记"），证明这条锁不是
在测"函数存在"，而是在测"这个具体的失败模式真的被挡住"。

### 受影响子集结果

```
tests/test_reading_mode.py tests/test_run_stage_flow.py tests/test_orchestrate_baseline.py \
tests/test_provenance_baseline.py tests/test_run_config.py tests/test_report_assembly.py
—— 100 passed, 1 xfailed, 0 failed
```

### 缺口 / 披露

1. **L-R2 的 fail-closed 范围是"opt-in 但真实"，不是"全局无条件"**（见上文"设计"节的
   详细论证）。如果审阅方判定派工单原意就是要在 `_draw_reading`/`provision_run`
   这类 gate① 通用路径上无条件焊死，那需要另外一轮设计（波及面会远超 R4-a
   "小、prerequisite"的定位，且会打红当前 2115 基线中大量不关心 reading_mode 的
   既有测试）——这是本轮唯一一处认为"值得升级为欠规格边界上报"但仍选择先做出
   一个可论证、可回退的具体实现、把决策权交还审阅方的地方。
2. **未接 gate①**：`src/validator/checks/reading.py` 未新增任何检查项去消费
   `reading_mode`（派工单没有要求，判卷/gate①层未触碰，属故意不做）。
3. **`toolbox_version`/`isolation_profile` 目前是自由字符串**，未与仓库里实际的
   工具箱版本号/隔离档位标识符做枚举绑定（派工单没有给出这两个字段的合法取值集合，
   保持自由字符串以免虚构一个不存在的枚举）。
4. 未触碰任何 `AI_agent/` 下的管理文档（除本执行日志）、未碰 sm24 testdata、未 push。

---

## 批 D · 判卷图恢复

（见下方——本节将在批 D 施工过程中持续追加。）
