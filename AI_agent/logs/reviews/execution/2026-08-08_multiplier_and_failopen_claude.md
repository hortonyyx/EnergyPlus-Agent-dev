# 摊二 + 摊三 施工日志（2026-08-08，Claude 侧执行档）

> 基线 = 派工单 `AI_agent/logs/reviews/request/2026-08-08_interface_sweep_round1_fixes_design.md`
> 只做「摊二」`create_fenestration(multiplier)` 与「摊三」严格档 fail-open。
> ⛔ 未碰摊一（F-16）、未碰 `src/agent/correction/{schema,parse,window_sources,window_host}.py`（另一席在改）。
> ⛔ 未 `git add`/`commit`（orchestrator 统一提交）。

## 摊二 · `create_fenestration(multiplier)`

### 前置调查结论（我被明确要求先做的部分）

问题：MCP 独立调用路径（无 AgentState 的 standalone 用法）是否有合法的非 1 用法？

**结论：没有。** 调查过程：

1. `src/agent/tools/fenestration_tools.py:9 make_fenestration_tools()` 在**全仓只有一个调用点**——
   `src/agent/nodes/fenestration.py:49`，且该调用点永远在 `AgentState`（`state.config_state`）
   语境内、由 `fenestration_agent` 节点在自动化 correction→geometry kernel→intake 管线里触发。
   `grep -rln "make_fenestration_tools"` 全仓（含 `tests/`、`scripts/`）只命中
   `nodes/fenestration.py` + `tools/__init__.py` + `tools/fenestration_tools.py` 自身，
   **没有任何测试、脚本、或其他生产代码直接调用它**。
2. 项目里**确实存在**一个真正意义上的「standalone MCP 独立调用路径」——
   `src/mcp/api/envelope.py:922 create_fenestration_surface`，用 FastMCP `@mcp.tool` 注册，
   通过仓库根 `.mcp.json` 挂载给任意 MCP 客户端（本会话的 deferred tools 列表里就能看到
   `mcp__EnergyPlus-Agent__create_fenestration_surface`）。**这是一个不同的函数**
   （不同名字、不同注册机制），供人或其他 agent 直接手搓任意 EnergyPlus 模型使用，
   与派工单点名的 `create_fenestration`（`agent/tools/`，仅供 ReAct LLM 在自动管线内调用）
   是两条独立的代码路径，只共享底层 `FenestrationTool`/`FenestrationSurfaceSchema`。
   该独立工具的 `multiplier` 参数（Number of identical fenestrations）在这条路径上**是合法的**——
   直接建模场景下用 EnergyPlus `Multiplier` 字段表示一排相同窗是标准建模手法，
   但**这条路径不是派工单要修的那个函数**，本摊未改动它、也不应该改。
3. `zone_tools.py:21 _frame_policy` 的 docstring 提到「standalone MCP path with no AgentState
   (contract=None)」是**对 `make_zone_tools` 的防御性设计描述**，不是实际存在的调用方——
   `grep` 确认 `make_zone_tools` 同样只有 `nodes/zone.py` 一个调用点。这条 docstring 描述的是
   「万一将来有人不带 contract 调它」的兜底行为，不代表现实中存在这样的调用者；
   对 `create_fenestration` 类比查证后结论相同：不存在。

⇒ **取方案 ①**：把 `multiplier` 从 `create_fenestration`（`agent/tools/fenestration_tools.py`）
的参数表整个摘掉。不退方案 ②。

### 改动

`src/agent/tools/fenestration_tools.py`：
- 从 `create_fenestration` 签名删除 `multiplier: int = 1`；
- docstring 删除 `multiplier: Number of identical copies (>= 1).` 一行，改写为说明「模型没有这个
  参数可传，几何内核逐窗建一个面、从不消费 multiplier」，并注明这是 2026-08-08 A-1 接线摸排发现，
  **结构性风险修复、非已发生缺陷的修复**（如实标注，未实测模型真会填非 1 值）；
- `ft.create({...})` 调用体里删除 `"Multiplier": multiplier` 这一键，让
  `FenestrationSurfaceSchema.multiplier`（`ge=1`，默认 `1`）自己兜底默认值。

未改 `src/mcp/api/envelope.py`（那是不同函数、权属外也不该动）、未改
`FenestrationSurfaceSchema`（`data_model.py:966`，schema 本身仍保留 `multiplier` 字段——
下游/独立 MCP 路径仍要用；`create_fenestration` 只是不再暴露这一个入口）。

### 锁

新文件 `tests/test_a1_fenestration_multiplier_not_exposed.py`，三条：

1. `test_create_fenestration_tool_schema_has_no_multiplier_field` ——
   直接内省 LangChain `@tool` 的 `.args`（不是手抄的字段清单，是工具自己声明的 schema），
   断言 `"multiplier" not in create.args`。**这条是「摘掉即红」的接口锁**。
2. `test_create_fenestration_call_site_cannot_pass_multiplier` ——
   故意在 `.invoke()` payload 里塞 `"multiplier": 5`，验证即使调用方想夹带，
   最终落盘的记录 `multiplier` 仍是 1（LangChain 对函数签名之外的键会静默丢弃，不会传进
   `ft.create()`）。**这条是「摘掉即红」的调用路径锁**。
3. `test_created_fenestration_multiplier_always_one` —— 行为锁，正常调用（不传 multiplier）后
   落盘记录 `multiplier == 1`。这条不专门验证「摘掉」，是基线正确性锁（neuter 后仍绿，见下）。

三条独立全量：`3 passed`（详见文末全仓跑测）。

## 摊三 · 严格档 fail-open

两处都在 `src/validator/checks/schema.py`。

### 第 1 条：默认档 = 最宽松（`:182` `disposition()` 与 `:253` `CheckReport.run_profile`）

**没有照字面「去掉默认值改必传」做，退到派工方预授权的更小改法：把默认值从 `"exploratory"`
（最宽松）改成 `"regression"`（最严档），而不是删默认值。**

**为什么退档（先做了调用点普查，普查结果决定了退档，不是先拍脑袋）**：

`grep` 全仓统计 `disposition(` 与 `CheckReport(` 的调用点，发现真实情况和最初设想的
「调用点多到有风险」略有出入，值得如实记：

- **生产代码里，`src/validator/checks/{correction,kernel,mep,reading}.py` 与 `assembly.py:33`
  的 6 个 `check_*()` 函数，其实各自已经有自己的一份 `run_profile: RunProfile = "exploratory"`
  参数，并且都显式把它转发进 `CheckReport(...)`**——也就是说，这些生产调用点从来不吃
  `schema.py` 里这两个默认值，它们吃的是**另一份重复声明的默认值**（同族但不在本摊范围内，
  按派工单「两处都在 schema.py」的边界，本轮未动它们，如实登记为跟进债）。
- 生产代码里**真正会吃到 `schema.py` 默认值**的只有一处：`src/validator/checks/assembly.py:60
  check_ep_baseline`（EP 结束态断言：`ep.end_present`/`ep.completed`/`ep.zero_severe` 三个都是
  `CheckStatus.ERROR` 或 `CheckLayer.INVARIANT` 且直接失败即挡，`disposition()` 对这三者的判定
  **完全不看 `run_profile`**；第四个 `ep.warning_threshold` 是 `CROSS_CHECK` 层，落到
  `disposition()` 末尾的通用 `return Disposition.FLAG`，同样不看 `run_profile`）。
  ⇒ **改默认值对这个调用点是零行为变化**（逐条验证：它产出的四个 check_id 没有一个落进
  `is_plan_frame_check_id` / `is_ocr_anchor_check_id` / `is_dimension_endpoint_bounds_check_id` /
  `is_evidence_check_id` / `_CORRECTION_EVIDENCE_DEBT_COVERAGE` 任何一个 run_profile 敏感分支）。
- 测试代码里唯一直接吃 `disposition()` 默认值的是 `tests/test_execution_foundation.py:284
  test_error_status_is_fail_closed`——`CheckStatus.ERROR` 恒 BLOCK，同理零行为变化。
- 但**测试文件里有约 30 处 `CheckReport(stage=...)` 构造不传 `run_profile`**
  （`test_a8_evidence_routing.py`/`test_audit_remediation_accepted_inputs.py`/`test_c2_b2_v3.py`
  ×7/`test_c2_b5_artifact_trust.py`/`test_c2_b5_parent_and_verts.py`/
  `test_checks_reading_correction.py`×4/`test_execution_foundation.py`×5/
  `test_e2e_break_r2_locks.py`×2/`test_f7_observation_reference_translation.py`×2/
  `test_judge_batch_b.py`/`test_judge_harness.py`×2/`test_orchestrate_baseline.py`×4/
  `test_output_coordinate_identity.py`/`test_output_coordinate_contract.py`/
  `test_run_stage_flow.py`/`test_run_pipeline_self_checks.py`×2/`test_step_orchestrator.py`×2）。
  **若把 `run_profile` 改成必传（删默认值），这些构造调用会在 pydantic 校验阶段就直接报错**，
  多数与被测行为本身无关（它们在测别的东西，只是顺手建了个 `CheckReport`）——这正是
  派工方自陈第 3 条预见的「调用点多到有风险」，且风险集中在**测试文件**：必传会把这 30 处
  全部改造成显式传参，改造量大、且要逐条判断「这条测试该传哪个档位」才不会**悄悄改变它原本
  想测的东西**——这个判断成本远高于「顺手加一个参数」。

⇒ **停下、退到预授权的小改法**：只改默认值方向（宽松→最严），不改「有没有默认值」。
这样：① 解决了「传递断点后果是放水」这条核心缺陷（默认从最宽松换成最严，断点后果从放水
变成收紧）；② 30 处测试构造维持原样可继续跑（不必逐条决定该传哪个档位）；③ 已验证对现有
生产/测试调用点是**零行为变化**（见上）。

**代价（如实登记）**：这不如「必传」彻底——若未来某个真正需要读 `run_profile` 的新调用点
又忘了传，它会拿到 `"regression"`（最严）而不是报错。这比拿到 `"exploratory"`（最宽松）安全
得多，但不是「强制显式声明」那么硬。这是我对派工方预授权小改法的理解与选择，如与派工方原意
有出入，请裁定是否要我再往「必传」推进（届时我会先列出全部 30 处该填的档位再动手，而不是
批量机械同一个值糊过去）。

### 第 2 条：阻断集合是白名单（4 处）

**`_EVIDENCE_BLOCK_PROFILES` 与 `_PLAN_FRAME_BLOCK_PROFILES`（各 `{"golden","regression"}`）
——照办，翻成「宽松档白名单」**：

```python
_EVIDENCE_PERMISSIVE_PROFILES = frozenset({"exploratory", "dev"})
_PLAN_FRAME_PERMISSIVE_PROFILES = frozenset({"exploratory", "dev"})
```
判定从 `if run_profile in _XXX_BLOCK_PROFILES: BLOCK` 改成
`if run_profile not in _XXX_PERMISSIVE_PROFILES: BLOCK`。
对现有 4 个档位（exploratory/dev/golden/regression）**逐档验证行为不变**
（`not in {exploratory,dev}` 对 golden/regression 为真=BLOCK，对 exploratory/dev 为假=FLAG，
与翻转前的 `in {golden,regression}` 逐档相同）；改变的只是「未来第 5 个档位」的默认行为——
现在默认 BLOCK，不再默认 FLAG。命中 `test_checks_reading_correction.py` 等既有测试全绿
（见下方全仓结果）。

**`_OCR_ANCHOR_BLOCK_PROFILES` 与 `_DIMENSION_ENDPOINT_BLOCK_PROFILES`（各 `frozenset()`）
——⛔ 我判断不应该照字面翻转，理由写在代码注释里，这里摘要，供裁定**：

这两个判据的空集不是「忘了列严格档」，是 **2026-08-04 用户已拍板的既定政策**：
该启发式判据本身双向不可靠（假阴性=纯像素坐标测不出异常、假阳性=正常 10×8m 房间/60×4m
狭长建筑会被误判），代码注释原文明写「never in blocking(), on any profile, **including
golden/regression**」。它「对所有档位都不阻断」的原因是**判据自己不可靠**，不是「某些档位
恰好宽松」——这和 `_EVIDENCE_BLOCK_PROFILES` 那两个的性质不同（那两个是「档位选择宽松」，
这两个是「判据本身不该被信任来挡任何东西」）。

若照字面翻转成 `{exploratory,dev,golden,regression}` 白名单（保持现有 4 档行为不变），
会产生一个新副作用：**未来新增的第 5 个（更严）档位会默认让这个已知不可靠的判据去挡它**
——即，一栋普通正常建筑，只因为跑在了新档位下，就可能被这条誤报率不为零的判据拦下来。
这正是 2026-08-04 那次降级想根除的效果（假阳性挡正确建筑），只是触发条件从「现有档位」换成
「未来档位」。

⇒ **本轮保持这两个常量原样不动**（仍是 `frozenset()`，语义仍是「任何档位都不阻断」），
只加了注释说明为何没有跟着前两个一起翻，并在此明确标出**这是我的一个判断分歧点**，
请派工方核实是否同意——若不同意，我可以按字面翻转（改动量很小，一行常量），但我认为那样做
会在「新档位默认严格」与「这条判据永不该拦不管什么档位」两条设计初衷之间选错一条。

### 改动汇总

`src/validator/checks/schema.py`：
- `disposition()` 参数默认值 `run_profile: RunProfile = "exploratory"` → `"regression"`；
- `CheckReport.run_profile` 字段默认值同上；
- `_EVIDENCE_BLOCK_PROFILES` → `_EVIDENCE_PERMISSIVE_PROFILES`（含义翻转，判断逻辑同步改
  `not in`）；
- `_PLAN_FRAME_BLOCK_PROFILES` → `_PLAN_FRAME_PERMISSIVE_PROFILES`（同上）；
- `_OCR_ANCHOR_BLOCK_PROFILES` / `_DIMENSION_ENDPOINT_BLOCK_PROFILES`：**未改**（加注释说明
  为何未跟随翻转，见上）。

未改任何 `check_*()` 函数自己的 `run_profile: RunProfile = "exploratory"` 参数默认值
（`correction.py`/`kernel.py`/`mep.py`/`reading.py`/`assembly.py:33`/`evidence_preflight.py`/
`view_manifest.py` 等）——这些不在派工单「两处都在 schema.py」范围内，是**同族但独立的
跟进债**，登记在下方。

### 摊三的锁

新文件 `tests/test_b1_prime_failopen_defaults.py`，七条：

1. `test_disposition_default_run_profile_is_strict_not_lenient` —— `disposition(result)`
   不传 `run_profile` 时对 evidence-check-id 的 FAIL 结果必须是 BLOCK（旧默认下是 FLAG）。
2. `test_checkreport_default_run_profile_is_strict_not_lenient` —— `CheckReport(stage=...)`
   不传 `run_profile` 时，`.blocking()` 必须非空（旧默认下是空）。
3. `test_disposition_default_does_not_change_behavior_for_known_insensitive_callers` ——
   证明默认值改动对 `assembly.check_ep_baseline`/`test_execution_foundation` 那类
   ERROR/纯 INVARIANT/CROSS_CHECK 检查零行为改变（三种状态各测一次）。
4. `test_future_run_profile_defaults_to_block_for_evidence_checks` —— 白名单翻转锁：
   一个假设的「未来更严档位」字符串对 evidence check 必须 BLOCK。
5. `test_future_run_profile_defaults_to_block_for_plan_frame_check` —— 同上，plan-frame check。
6. `test_known_lenient_profiles_still_flag_not_block_for_evidence_and_plan_frame` ——
   行为保持锁：现有 4 档（exploratory/dev/golden/regression）翻转前后逐档结果不变。
7. `test_ocr_anchor_and_dimension_endpoint_stay_advisory_on_every_profile_including_future` ——
   记录并锁定我的判断分歧点：OCR 锚点/尺寸端点两个判据在**任何档位（含未来假设档位）**下
   都不阻断，证明我确实没有对这两处做字面翻转。

七条独立跑：`7 passed`（详见下方全仓跑测）。

## 全仓跑测

**基线（本轮开工前，含摊二 3 条新锁、不含摊三 7 条新锁，因为跑的时候摊三测试文件还没写）**：
`2292 passed, 10 xfailed, 0 failed`（326.78s）——与派工单给的基线 `2289 passed / 10 xfailed / 0 failed`
对比，`2292 = 2289 + 3`，恰好是摊二新增的 3 条锁，说明**这次独立全量时另一席（F-16）没有引入
额外的净增/净减测试数**（或者净变化恰好为零——本轮未去核实，如实标注：只核对了总数吻合，
没有逐文件比对另一席改动是否引入了它自己的新测试）。

**最终全仓（含摊二 3 条 + 摊三 7 条，共 10 条新锁）**：

```
2299 passed, 10 xfailed, 0 failed  (379.39s)
```

`2299 = 2289（派工单基线）+ 10（本轮两摊新增的锁：摊二 3 条 + 摊三 7 条）`，逐位吻合，
**零红、零意外增减**。两次全量（含/不含摊三锁）之间的差值也恰好是摊三新增的 7 条
（2299 − 2292 = 7），进一步印证中途没有非本摊改动的测试数变化。

**关于另一席（F-16）**：本轮两次全量期间，F-16 那一席据 CLAUDE.md/plan.md 记录也在同一工作树
并行改 `src/agent/correction/{schema,parse,window_sources,window_host}.py`。本轮两次全仓统计
`passed` 总数变化都精确等于我自己新增的锁数（+3 然后 +7），**没有观察到任何我没引入的净增/净减/
翻转**——这意味着在我两次起跑的时间点上，F-16 那一席要么没有并发写入这些文件，要么写入的
改动本身没有改变测试通过/收集总数（比如只是编辑中间态、还没触发新测试或还没引入失败）。
⛔ 本轮没有专门去 diff `src/agent/correction/` 下这四个文件确认其当前状态（按指令不碰它们，
也不应该去读它们的中间改动状态来对我的结论下判断），如实标注：这个「零意外」的判断只基于
两次全仓测试数字吻合，不是基于逐文件核对。若后续出现红，需要先看是不是 F-16 那一席收尾时
才落地的改动导致，而不是本摊引入。

## neuter 自查表

| # | 锁 | 摘掉/还原的内容 | 结果 |
|---|---|---|---|
| 1 | `test_create_fenestration_tool_schema_has_no_multiplier_field` | 把 `multiplier` 参数与 `"Multiplier": multiplier` 键还原回 `create_fenestration` | **红**（`assert "multiplier" not in create.args` 失败）|
| 2 | `test_create_fenestration_call_site_cannot_pass_multiplier` | 同上 | **红**（还原后落盘记录 `multiplier==5`，断言失败）|
| 3 | `test_created_fenestration_multiplier_always_one` | 同上 | **绿，如实披露**——这条锁测的是「默认值兜底」，不是「摘除接口」，multiplier 参数还原后只要调用方不传，落盘仍是 1，所以这条不会因这次 neuter 变红。它是行为基线锁，不是「摘掉即红」锁，三条锁合起来才覆盖「接口摘除」这件事的完整证据链。|
| 4 | `test_disposition_default_run_profile_is_strict_not_lenient` | `disposition()` 默认值改回 `"exploratory"` | **红** |
| 5 | `test_checkreport_default_run_profile_is_strict_not_lenient` | `CheckReport.run_profile` 字段默认值改回 `"exploratory"` | **红**（同一次改动触发，见上，两个默认值我是一起改的，neuter 时也一起还原，逐条见下方「补充 neuter」分开验证）|
| 6 | `test_disposition_default_does_not_change_behavior_for_known_insensitive_callers` | 同上还原 | **绿，符合预期**——证明这条锁本来就不是「摘掉即红」锁，是「默认值改动不该影响谁」的不变量锁 |
| 7 | `test_future_run_profile_defaults_to_block_for_evidence_checks` | `_EVIDENCE_PERMISSIVE_PROFILES` 还原回 `_EVIDENCE_BLOCK_PROFILES` 旧形态 | **红** |
| 8 | `test_future_run_profile_defaults_to_block_for_plan_frame_check` | `_PLAN_FRAME_PERMISSIVE_PROFILES` 还原回 `_PLAN_FRAME_BLOCK_PROFILES` 旧形态 | **红** |
| 9 | `test_known_lenient_profiles_still_flag_not_block_for_evidence_and_plan_frame` | 同 7/8 一起还原 | **绿，符合预期**——这是「翻转前后 4 个已知档位行为不变」的不变量锁，不该因翻转还原而红 |
| 10 | `test_ocr_anchor_and_dimension_endpoint_stay_advisory_on_every_profile_including_future` | 未做 neuter（这两处代码本来就没改，没有「摘掉」的动作） | 不适用——见下 |

**逐条 neuter 操作记录**（均在 `/tmp/neuter_a1`、`/tmp/neuter_b1` 全量文件副本里做，非工作树；
每次改完立刻 `rm -rf` 清理，工作树全程未被这些操作触碰）：

- **摊二**：还原 `create_fenestration` 签名与 `ft.create({...})` 调用体，重新加回
  `multiplier: int = 1` 参数与 `"Multiplier": multiplier` 键 → 3 条锁里 2 红 1 绿（绿的原因见上表）。
- **摊三点 1**：把 `disposition()` 参数默认值与 `CheckReport.run_profile` 字段默认值一起
  改回 `"exploratory"` → 7 条锁里 2 红（4、5 号）、其余 5 条不受影响仍绿。
- **摊三点 2**：把 `_EVIDENCE_PERMISSIVE_PROFILES`/`_PLAN_FRAME_PERMISSIVE_PROFILES` 连同判断
  逻辑（`not in` → `in`）一起还原成旧的 `_EVIDENCE_BLOCK_PROFILES`/`_PLAN_FRAME_BLOCK_PROFILES`
  形态 → 7 条锁里 2 红（7、8 号）、其余 5 条不受影响仍绿。
- **点 9（OCR/尺寸端点）未做 neuter**：因为本轮代码本身没有改这两处的判定逻辑（我判断不应该
  照字面翻转，见摊三第 2 条），没有「摘掉」这个动作可做。第 10 号锁的作用不是「摘掉即红」，
  是「如果以后有人机械地把这两处也翻了，这条测试要红」——**我手动模拟了一次「假设有人也把它们
  翻了」**（临时把 `_OCR_ANCHOR_BLOCK_PROFILES`/`_DIMENSION_ENDPOINT_BLOCK_PROFILES` 也改成
  `frozenset({"exploratory","dev","golden","regression"})` 白名单形态并同步改判断逻辑），
  验证第 10 号锁确实会红（见下）。

**补充 neuter：模拟「有人把 OCR/尺寸端点也机械翻了」**：

```
_OCR_ANCHOR_PERMISSIVE_PROFILES = frozenset({"exploratory","dev","golden","regression"})
_DIMENSION_ENDPOINT_PERMISSIVE_PROFILES = frozenset({"exploratory","dev","golden","regression"})
# 判断逻辑同步改 not in
```
在 `/tmp/neuter_b1_ocr` 副本里做此项，跑 `test_ocr_anchor_and_dimension_endpoint_stay_advisory_on_every_profile_including_future`
→ **红**（`hypothetical_stricter_profile` 不在白名单内 ⇒ 变成 BLOCK，与断言的 FLAG 矛盾）。
证明第 10 号锁确实在守护我的判断分歧点，不是摆设。

## 对派工方三条薄弱处的判断

1. **「摊二的前置调查是我没做的，查出来有就退方案②」**——查了，**没有**。
   `create_fenestration`（`agent/tools/fenestration_tools.py`）全仓唯一调用点是
   `nodes/fenestration.py`（AgentState 绑定）。真正意义上的「standalone MCP 独立路径」
   是 `src/mcp/api/envelope.py:922 create_fenestration_surface`——**不同的函数**，供人/其他
   agent 直接手搓模型，那条路径上 `multiplier` 合法且本轮未动。派工方这条自陈准确：这确实是
   需要先查的前置项，查完结论落在派工方预设的「无」分支，走方案①。

2. **「摊三改白名单方向可能撞上我没预见的档位语义」**——**命中，但方向和派工方猜的不完全一样**。
   派工方猜的是「某个宽松档其实需要阻断某类检查」；我实际撞上的是**反方向**：
   「某类检查（OCR 锚点/尺寸端点）本身不可靠，不该因为某个新档位更严格就开始阻断它」。
   这是同一类风险（档位与判据的语义耦合被想当然地处理）的镜像形态。我的处理：**没有对这两处
   照字面翻转**，原样保留 `frozenset()`（永远不阻断），只加注释说明原因，并用锁 #10 钉住
   这个判断。**这是本轮最需要派工方复核的一处分歧点**，见下方「停下上报的边界问题」。

3. **「摊三第 1 条『去掉默认值改必传』可能牵出很多调用点，多到有风险就停下上报」**——
   **命中，已按预授权的小改法处理**：`grep` 全仓后发现 ~30 处测试构造 `CheckReport(...)`
   不传 `run_profile`，若改成必传会让这些构造在 pydantic 校验阶段直接报错，且需要逐条判断
   该填哪个档位才不误伤测试原意——判断成本高、收益（相对于"改默认值方向"这个更小的修法）
   不成比例。已退到「默认值方向反转（最宽松→最严）」这个更小的改法，并且验证了对现有生产/
   测试调用点是零行为变化（唯一吃这两个默认值的生产调用点 `assembly.check_ep_baseline`
   与吃 `disposition()` 默认值的测试 `test_execution_foundation.py:284` 都只产生
   run_profile 不敏感的 ERROR/INVARIANT/CROSS_CHECK 检查）。

## 停下上报的边界问题

**唯一一处需要派工方明确表态的分歧点**：摊三第 2 条里，`_OCR_ANCHOR_BLOCK_PROFILES` 与
`_DIMENSION_ENDPOINT_BLOCK_PROFILES` 我**没有**按字面「白名单翻转」处理，理由见上文详述
（这两个检查本身不可靠、不是因为某档位宽松才不阻断——2026-08-04 用户已拍板的既定政策，
注释原文写着「on any profile, including golden/regression」）。

我倾向于认为**不翻转**是更贴合既有设计意图的选择，但这确实是一个**我在派工单字面指示之外
做出的判断**，且派工单原文写的是「同形的白名单在 xxx 共 4 处」，字面意思是要求我处理全部 4 处。
**如果派工方认为这两处也该翻转**（比如认为「新档位默认严格」这条原则应该无条件优先于
「这个判据不可靠」那条原则），改法很小（几行常量 + 判断逻辑，锁 #10 需要同步改写或删除），
可以下一轮直接改。**如果同意我的判断**，锁 #10 已经在守着这个决定不被以后的人不小心改动。

除此之外，本轮没有其他「验收条件不可达」「测试期望本身错」类的停下上报情形——全仓跑测结果见
上，若有非本摊改动范围内的红，会在下方逐条判断是否属于另一席（F-16）的改动，不会去动它。
