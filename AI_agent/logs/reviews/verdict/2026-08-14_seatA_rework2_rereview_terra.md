# 摊 A 返工二轮复审裁决书（第三轮 / 最终）

- **复审席位**：GPT / terra
- **复审基线**：合并笔 `4df5450`（返工二轮 `8863371`）
- **结论日期**：2026-08-14

## 裁决

**摊 A 就本轮最小闭合口径签收。**

第二轮的阻塞项已被局部且正确地关闭：三张 canonical `Schedule:Compact`
现在只引用专属保留名 `HVACDet_Temperature` / `HVACDet_OnOff`，而不再引用模型可
控制的通用 `Temperature` / `OnOff`。这两个专属 `ScheduleTypeLimits` 与三张保留
schedule 采用同一所有权语义：解析成功时，先按大小写不敏感的 EnergyPlus 名称语义
移除模型同名对象，再无条件追加代码 canonical 定义。因此，模型以
`hvacdet_temperature` 或 `HVACDET_ONOFF` 抢名并收窄，也只能得到代码的
`-60..200 / Continuous` 与 `0..1 / Discrete`。

同时，模型自己的通用 `Temperature` / `OnOff` 以及引用它们的无关
`Sch_SomeOtherSetback` 保持不改。定向锁驱动真实 `run_mep`，仅 stub
`_call_json_llm`；它同时覆盖收窄通用名、专属名大小写碰撞、三张 canonical
schedule 的唯一性和值（20 / 24 / 1）、两条专属 type-limit 的值域/数值类型，以及
`mep.idf_parse`、`mep.schedule_type_refs`、`mep.schedule_completeness`、
`mep.hvac_schedule_refs` 全 PASS。该实现满足我第二轮裁决要求的四项断言，没有发现
新的本轮阻塞项。

这份签收仅表示第二轮指出的 deterministic HVAC / schedule 合并合同已闭合；它不替代
此前记录的真实 `schedule_agent → hvac_agent`、EnergyPlus、regression/golden
端到端验收。

## 对施工席自陈的裁定

**不阻塞。** 施工席本次没有独立重做“零区可达性”的验证，确实使它的施工记录在
这一点上少了一层复现证据；但这不是新的实现断言，也不是本返工改动的依赖。

更关键的是，该可达性已经由本席在第二轮实际复现：legacy schema v1 的
`floors=[]` 和一层 `cells=[]` 都可生成零 zone；空 floors 情形的 `check_kernel()`
仍 PASS，生产调用从 `bg.zones` 导出 `zone_names`，最终会进入
`_render_hvac_specs([])` 的明确 `ValueError`。现有定向测试也持续锁定
`run_mep` 传播该 reject。故施工席未再复现属于证据记录的不一致，而非会推翻既有
结论的验证缺口；不构成本轮签收阻塞。

“专属保留名是否会被下游 `schedule_agent` 当作陌生字符串异常处理”仍在下游边界外，
没有被本轮证明，也没有被本轮改动制造为已知失败；它保留为上述真实链路验收的一部分，
不作为此窄范围返工的 blocker。

## 实际复核与结果

所有命令均在 `/workspaces/ep-wt-R` 执行。未做 editable 安装、未运行全仓、未改动
其他 worktree。

| 命令 / 检查 | 结果 / 用途 |
|---|---|
| 阅读第一轮与第二轮裁决书 | 以已登记 blocker 和最小闭合口径作为唯一复审标准。 |
| `git show --stat 8863371`、`git diff 8863371^..8863371 -- src/agent/pipeline.py tests/test_mep_hvac_deterministic.py` | 确认提交将 canonical schedule 改为两个专属 type-limit，并对其施加同样的大小写不敏感排除 + canonical 追加。 |
| 审阅 `_merge_hvac_det_schedules()`、`_hvac_det_schedule_block()`、`run_mep()` 与新增定向锁 | 确认锁通过真实 `run_mep` 接线，只 stub LLM 边界；并确认 generic type limits / 无关 schedule 保真断言存在。 |
| `python -m pytest -q tests/test_mep_hvac_deterministic.py` | **21 passed in 16.16s**。包含本轮“通用名收窄 + 专属名大小写碰撞”真实 `run_mep` 锁与零区 reject 锁。 |
| `git diff --check 8863371^..8863371` | 通过，无该返工提交引入的空白错误。 |

注：对合并笔运行更宽范围的 `git diff --check 8863371^..HEAD` 时，仅报告第一轮既有裁决书
末尾多余空行；不属于 `8863371` 的实现改动，且不影响本裁决。

## 未验证范围

本轮未重跑 orchestrator 已独立复核的四道轻门；其结果与本席的定向测试没有矛盾。
未在本轮重新构造第二轮的 geometry → kernel → `run_mep` 零区可达性反例，而是依据
第二轮本席的实际复现及持续存在的传播测试作裁定。未实跑真实 LLM 的
`schedule_agent → hvac_agent`、未运行 EnergyPlus、未运行 regression/golden 或任何
全仓测试。未将 `test_gt_from_dxf`、`test_inspect_dxf`、`test_zone_agent` 三条 F-30
环境假红作为回归处理。
