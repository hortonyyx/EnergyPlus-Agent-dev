# 摊 A 返工复审裁决书（第二轮）

- **复审席位**：GPT / terra
- **复审基线**：`f81cd3a`（返工内容提交 `c367667`）
- **结论日期**：2026-08-14

## 裁决

**摊 A 暂不签收。**

`c367667` 已实质闭合上一轮的保留 `Schedule:Compact` 同名问题：对三张保留名按 EnergyPlus 的大小写不敏感语义识别，碰撞时从 eppy IDF 对象移除，再追加代码的 canonical 20 / 24 / 1 定义；无碰撞路径不重序列化模型文本。新增的真实 `run_mep` 锁也覆盖了精确名、大小写变体、去除失效时反转为红，以及合并后检查门全绿。这一部分签收。

但施工席刻意保留的 `ScheduleTypeLimits` 不对称处理重新给三张“代码拥有”的 schedule 留下了模型可控制的语义输入，且现有 4_mep 门不会拦住。故 A 的“确定性、代码拥有 HVAC 段”仍未无条件成立。

## 阻塞项：通用 `ScheduleTypeLimits` 仍可使 canonical schedule 失效

三张代码 schedule 仍分别引用 `Temperature` 和 `OnOff`。实现对这两个名称只做“模型已经定义就不添加”，不验证或覆盖其值域与数值类型。于是模型可写：

```idf
ScheduleTypeLimits, Temperature, 30, 40, Continuous;
ScheduleTypeLimits, OnOff, 2, 3, Discrete;
```

随后代码仍写入 20、24、1。它们在所引用的 type limit 范围外；仓内 MCP 工具和数据模型都将 ScheduleTypeLimits 定义为 schedule value 的合法范围。实测该合并产物 `mep.idf_parse`、`mep.schedule_type_refs`、`mep.schedule_completeness` 和 `mep.hvac_schedule_refs` 都 PASS，`check_mep.passed=True`。因此这不是现有门会阻断的“模型写错后重试”，而是代码注入值被模型的通用 type limit 静默约束的遗漏。

同一不对称还制造了一个次级一致性问题：模型若定义小写 `temperature`，合并代码会按大小写不敏感逻辑不添加 `Temperature`，但 canonical schedule 仍拼写 `Temperature`；本仓 `mep.schedule_type_refs` 目前作大小写敏感集合比较，因而给两个 code schedule 报“undefined”。这不是物理放行漏洞，却说明此处的 EnergyPlus 名称语义与本仓 gate 没有闭合。

### 最小闭合口径

不要覆盖模型通用的 `Temperature` / `OnOff`，以免改变无关 schedule；而应让代码 schedule 引用**两个专属、保留的 type-limit 名**（例如 `HVACDet_Temperature` / `HVACDet_OnOff`），并像三张保留 `Schedule:Compact` 一样按大小写不敏感移除同名模型定义后追加 canonical type-limit 定义。相应更新 `_hvac_det_schedule_block()` 的引用。

新增一个驱动真实 `run_mep`、只 stub `_call_json_llm` 的锁，至少同时预置上面的收窄 generic `Temperature` / `OnOff`，并预置专属 type-limit 名的大小写碰撞；断言：

1. 三张 canonical schedule 各唯一，仍为 20 / 24 / 1；
2. 它们只引用专属 canonical type limits，且各自范围/数值类型正确；
3. 模型的 generic type limits（和依赖它们的无关 schedule）不被改写；
4. 合并产物的 `check_mep` 相关门为 PASS。

这是一处局部命名/合并与一条锁的返工，不要求本席位重跑全仓或此前列出的真实下游、EnergyPlus、regression/golden 验收。

## 对施工席自选项的裁定

`ScheduleTypeLimits` 的**不对称动机可以接受，当前实现不可接受**。保留通用名以避免篡改无关模型 schedule 是正确风险判断；把代码 schedule 继续绑定到这两个模型可控制的通用名则不是。以上“专属名 + 同样的 code ownership”能同时保留该动机和确定性合同。

## 零区边界

**不作为本轮阻塞项；此项已满足上一轮给出的“若不支持则渲染前明确拒绝”口径。**

施工席所说的“未反向确认是否可达”不再成立为未知风险：我以仍受支持的 legacy schema v1 分别构造了 `floors=[]` 与一层 `cells=[]` 的 `CorrectedGeometry`。两者都通过 schema，`build_geometry()` 生成零 zone；对前者 `check_kernel()` 仍 `passed=True`（coverage 为 N/A），所以没有更早的通用 guard 会排除它。两条生产调用都从 `bg.zones` 导出 `zone_names`，故该输入会到达 `run_mep`；现有 `run_mep` 锁已证明 `_render_hvac_specs([])` 的 `ValueError` 向上传播、不产生孤立 thermostat。

这恰好证明 reject 是有意义的 fail-closed 行为，而非一个不可能触发的死分支。可选改进是在调用 LLM 前就拒绝，以免零区运行花费一次 LLM 调用；它不影响本轮验收裁定。

## 实际复核与结果

所有命令均在 `/workspaces/ep-wt-R` 执行；没有 editable 安装、没有改动其他 worktree、没有运行全仓。

| 命令 / 检查 | 结果 / 用途 |
|---|---|
| 阅读 `AI_agent/logs/reviews/verdict/2026-08-14_seatAB_crossreview_terra.md`，`git show c367667`，并审阅 `src/agent/pipeline.py` 与新增测试 | 对照上一轮阻塞项、返工实现及锁的真实接线。 |
| `python -m pytest -q tests/test_mep_hvac_deterministic.py` | **19 passed**。包含本轮四条新增锁。 |
| 内联 Python：三张保留 schedule 的大小写碰撞合并与 `check_mep` | 确认返工的 schedule ownership 行为及相关 gate 路径。 |
| 内联 Python：预置 `Temperature=30..40`、`OnOff=2..3` 后合并并运行 `check_mep` | 三个 canonical 值仍为 20 / 24 / 1，且上述 4_mep 门及整体报告均 PASS；形成当前阻塞项的直接证据。 |
| 内联 Python：预置小写 `temperature` | 合并不补 `Temperature`，`mep.schedule_type_refs` 对两条 canonical schedule FAIL，确认大小写契约不一致。 |
| 内联 Python：v1 空 floors / 空 cells → `build_geometry`，以及空 floors → `check_kernel` | 两种均产生零 zone；后者 kernel 报告仍 PASS，确认零区真实可达而明确 reject 会生效。 |
| `git diff --check c367667^..c367667` | 无空白错误。 |

## 未验证范围

未复跑 orchestrator 已复核的碰撞重序列化非目标 schedule 保真轻门，也未跑全仓（其主树结果为 2633 passed / 10 xfailed / 0 failed）。未实跑真实 LLM 的 `schedule_agent → hvac_agent`、未跑 EnergyPlus，未跑 regression/golden 端到端；这些仍是上一轮记录的验收路径验证，非本轮针对性复审所代替。未把本 worktree 已登记 F-30 的三条环境假红当作回归。
