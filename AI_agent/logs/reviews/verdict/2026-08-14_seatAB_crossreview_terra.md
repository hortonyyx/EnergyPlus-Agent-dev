# 跨家族复审裁决书：摊 A（确定性设备段）+ 摊 B（IDD 对齐门）

- **复审席位**：GPT / terra
- **复审基线**：`9700684`（含 A、B 与 B 返工）
- **结论日期**：2026-08-14

## 裁决

| 摊位 | 裁决 | 范围与条件 |
|---|---|---|
| 摊 A | **暂不签收** | 确定性覆写、双入口有序接缝和引用闭合本身成立；但“代码拥有三张保留时间表”尚非无条件成立，存在可由模型文本制造、且当前门全部放过的同名时间表重复输入。完成下述最小闭合后可签。 |
| 摊 B | **签收，但仅作为报告型 IDD 缺必填字段门** | 缺必填字段的通用 IDD 发现、历史产物不改阻断集、B2 对已跟踪夹具的枚举口径，以及 disease cross-reference 均可接受。不得把它表述为已实现“确定性设备对象的阻断防线”或“超字段检出”。 |

### A 的新发现（本裁决的阻塞项）

`_merge_hvac_det_schedules()` 只避免重复 `ScheduleTypeLimits`，不处理模型在 `schedule_specs` 中已经写出的三个保留 `Schedule:Compact` 名。模型虽被提示不要写 HVAC 时间表，但该提示不是约束；函数随后仍会无条件追加同名的代码版本。

我以三个精确保留名（`Sch_HVACDet_HeatingSetpoint`、`Sch_HVACDet_CoolingSetpoint`、`Sch_HVACDet_Availability`）预置模型时间表后调用该函数：解析成功，三个名称均出现 **2** 次，`mep.idf_parse=pass`，整份 `check_mep` 仍 `passed=True`。因此现有检查不能把此类模型影响拦在 4_mep 外。按 §1 的真实链路，这些 specs 不会直接成为最终 IDF；风险是 schedule ReAct agent 收到矛盾的源文本而重建/重试不稳定，不是已经证实的静默物理计算错误。

**A 的最小闭合口径：**

1. 对三张保留 `Schedule:Compact` 名实施真正的代码所有权：模型同名定义须在进入下游前被排除或明确 fail-closed/resample；比较须按 EnergyPlus 名称语义处理大小写，而不能只做精确字符串比较。
2. 增加锁：模型提供三个同名定义（再加至少一个大小写变体）时，交给 schedule agent 的 `schedule_specs` 中每个保留名恰有一个、且值为代码的 20/24/1 定义；或该结果在 4_mep 被明确阻断。不能只断言 eppy 能解析。
3. 闭合后复跑现有 A 定向锁及该新增锁；不要求在本席位重跑 §6 的权威全量。

## 对已登记未闭合项的裁定

### §4.1：阻塞档结构上恒绿

**下轮补，不要求为本轮 B 回退或临时造一个伪阻断。** IDD 事实支持该结论：名单中两类对象的 required-field 只分别覆盖 Name / Zone Name，而真实 eppy 路径又已将超字段支路消掉。当前把它叫“阻断档”会造成错误安全感，但它没有改变历史阻断集，也没有引入放行风险。

下一轮应按已登记方向改为“渲染器的期望形状 ↔ 已解析对象的往返断言”：验证每个区恰一条 IdealLoads、共享 thermostat 的全部目标字段及三个引用，不以 IDD required-field 数量代替渲染器合同。该项完成前，B 的 blocker 集不得用作 A 正确性的证据。

### §4.2 / F-29：超字段判据死代码

维持登记，不能把 monkeypatch B1 当作真实路径覆盖。它应随解析器保留原始 token 数或在 eppy 前做保真词法检查时一并关闭；本轮不要求补，因为现有代码对这一支路没有真实可达性。

### §4.4：People offender 去重

**当前可接受，但措辞应降级为“诊断不复述”，不是“对象去重”。** `mep.people_field_alignment` 报 A4 非枚举的根病，通用门报 A5 required 缺失；两个 cell 都有事实价值，且通用结果是 FLAG、不会额外改变阻断集合。若后续把 check 数、offender 数或告警数用于重试/质量指标，必须以 `(object_type, object)` 聚合成一个问题组并以 `related_to` 保留第二证据，避免同一 People 被计为两次独立事故。本轮不阻塞 B。

## 进入验收路径前必须补的验证

以下是发布/验收前置，不等同于要求重跑已完成的 §6 全量：

1. **A 的同名保留时间表最小闭合**（上节三项）。
2. 一次真实下游链路：`schedule_agent → hvac_agent` 必须能消费新形态，并以工具状态确认三张时间表、一个 thermostat、每区一个 IdealLoads 的命名与数量；不能以 `_call_json_llm` stub 代替。
3. 一次实际 EnergyPlus 仿真，输入应来自上述完整链路；这是验证命名 MCP 工具最终物理对象语义的唯一合适位置。
4. 目标 `regression` / `golden` 验收 profile 至少各跑一次端到端，确认新 4_mep 合同被真实验收入口使用。
5. 为零区输入固化行为：若该输入不受支持，应在渲染前明确拒绝；若受支持，应有固定、可通过的输出合同与测试。现在会无条件生成 thermostat 而不生成 zone 系统，不能留作未定义边界。

“提示词更新后孤儿时间表是否趋零”不是验收阻塞项（但应观测）；B 的“criterion ②真实链路”因结构不可达不是独立前置；`smalloffice_23` 既非已跟踪提交夹具，也不是本轮 CI 前置，若将来纳入版本控制再加入固定表即可。

## 实际复核与结果

全部命令均在 `/workspaces/ep-wt-R` 执行；未运行 editable 安装，未跑全仓，也未创建 `.env`。

| 命令 | 输出 / 用途 |
|---|---|
| `sed -n '1,260p' AI_agent/logs/reviews/request/2026-08-14_seatAB_crossreview_gpt.md` | 完整阅读请求书（文件在该范围内结束）。 |
| `git log --oneline --decorate -8` 与对 `41ddbcb`、`1472cfc`、`fb171ec` 的 `git show --stat` | HEAD 为 `9700684`，确认 A、B、B2 均在审阅基线。 |
| `rg -n "\\brun_mep\\(" --glob '*.py'` | 仅发现两处生产调用，均已传入 `zone_names`；另有测试调用。 |
| `git diff 41ddbcb^ 41ddbcb ...`、`git diff 1472cfc^ 1472cfc ...`、`git diff fb171ec^ fb171ec ...` | 审阅覆写、保序接缝、IDD 分档和 B2 从文件系统 glob 改为 `git ls-files` 的实现。 |
| 内联 Python：以三个保留名预置 `Schedule:Compact` 后调用 `_merge_hvac_det_schedules()` | `parse_ok=True`；三个名称计数均为 `2`；`mep_idf_parse=pass`；`mep_passed=True`。这是 A 暂缓签收的直接证据。 |
| `python -m pytest -q tests/test_mep_hvac_deterministic.py tests/test_mep_idd_field_alignment.py` | **26 passed in 12.31s**。 |
| `git diff --check 41ddbcb^..HEAD`、`git status --short` | 无空白错误；审阅结束时工作树无未提交改动（本裁决书除外）。 |

## 未验证范围

我按请求书不重复执行了 orchestrator 的 §3 轻门和 §6 主树权威全量；它们保留其原有证据价值。未实跑真实 LLM 的 schedule/hvac agent、未运行 EnergyPlus、未跑 regression/golden 端到端，也未验证孤儿时间表趋势或零区边界；这些正是上列验收前置或后续观测项。未将 F-30 三条 worktree 环境假红当作回归处理。

