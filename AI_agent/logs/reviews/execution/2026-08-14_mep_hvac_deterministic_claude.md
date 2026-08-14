# 摊 A 执行报告 —— hvac_specs 由代码确定性生成（2026-08-14）

派工单：[`AI_agent/logs/reviews/request/2026-08-14_mep_hvac_deterministic_dispatch_claude.md`](../request/2026-08-14_mep_hvac_deterministic_dispatch_claude.md)

## 0. 结论先行

- `hvac_specs` 不再由 4_mep 的 LLM 撰写；`run_mep`（`src/agent/pipeline.py`）在拿到模型返回值之后、写盘之前，**无条件**用代码渲染覆盖它，并把渲染引用的 3 张时间表并入 `schedule_specs`。
- A1–A5 全部实测通过（逐条证据见 §4）；A6 全仓跑出 `rc=1`，但 **3 条红全部是 worktree 环境假红，与本摊改动零关联**（已逐条独立核实，非转述 orchestrator 结论——见 §4 A6）；A7 未放宽任何门。
- §2.1 的 `run_stage.py:703` `set(...)` 确实改了（改成 `list(...)`），但**这不是本轮 A3 唯一一次失败的真实原因**——中途 orchestrator 转达的一次诊断（"A3 红是因为这处还是 set"）与我自己重跑后看到的真实 traceback 不符，已独立复核见 §4 A3 与 §5。

---

## 1. 改动清单

| 文件 | 改动 |
|---|---|
| `src/agent/pipeline.py` | 新增 `_render_hvac_specs` / `_hvac_det_schedule_block` / `_merge_hvac_det_schedules` / 4 个 `_HVAC_DET_*` 常量；`run_mep` 签名新增必填关键字参数 `zone_names: Sequence[str]`，函数体在 `MepOutput.model_validate` 之后、写盘之前无条件覆盖 `result.hvac_specs` / `result.schedule_specs`；flow 调用点（原 `pipeline.py:1389`，现约 1558 行）传入 `zone_names=list(dict.fromkeys(bg.zones))`；`_build_mep_messages` 的 system prompt / human 消息更新，告知模型 `hvac_specs` 已改为代码生成、不必撰写 |
| `scripts/tool_scripts/run_stage.py` | `_geometry_zone_meta`（原 703 行）的 `zone_names` 从 `set(dict.fromkeys(bg.zones))` 改为 `list(dict.fromkeys(bg.zones))`；`_draw_mep` 调用 `run_mep` 时新增 `zone_names=zone_names` |
| `src/agent/intakeoutput.py` | `MepOutput.hvac_specs` 从必填 `str` 改为 `str = ""`（防御性：模型响应整个漏掉这个 key 时仍能通过校验，覆盖逻辑照常执行） |
| `skills/intake_pipeline/4_mep/authoring.md` | "What you output" 从 8 字段改为 7+1（点名 `hvac_specs` 代码生成）；schedule_specs 的 "Required checklist" 删掉 3 条 hvac 相关时间表、补充"不要再写"的说明；`people_specs / lights_specs / hvac_specs (per zone)` 一节改名去掉 hvac；Naming 一节的交叉引用规则同步更新 |
| `skills/intake_pipeline/4_mep/mep.md` | HVAC 一节加注"代码生成，不再从本文档撰写"，并把示例对象类型从 `IdealLoadsAirSystem` 改成实际的 `HVACTemplate:Zone:IdealLoadsAirSystem`（原文字面上就不精确，顺手订正） |
| `tests/test_mep_hvac_deterministic.py` | 新增，15 条测试，覆盖 A1–A5（见 §4） |

未改动、且刻意不改动的：`src/validator/checks/mep.py`（`_HVAC_SCHEDULE_REF_FIELDS` 是摊 B 的接缝锚点，§3 明令不许碰）、`pipeline.py` 里 `check_mep(...)` 的 `zone_names=set(dict.fromkeys(bg.zones)) or None` 调用（保持原样，见 §2.1）。

---

## 2. 关键判断

### 2.1 §2.1 的 `run_stage.py` `set(...)` 怎么改的

`_geometry_zone_meta` 原来只有一个消费者需要 `zone_names`（`check_mep`，做成员测试/`sorted()`/真值判断，从不做集合运算），所以原作者写成 `set(...)` 没问题。`run_mep` 现在也要消费同一个值来渲染 hvac_specs，而渲染必须有序，`set` 就不够用了。

**改法**：把 `_geometry_zone_meta` 返回的第 5 个值从 `set(dict.fromkeys(bg.zones))` 改成 `list(dict.fromkeys(bg.zones))`——同一个变量喂给两个消费者，不新增返回值。这样改的依据：
1. 先读了 `check_mep`（`src/validator/checks/mep.py`）里 `zone_names` 的全部 3 处用法（`_load_refs` 的 `in`、`_per_zone_coverage` 的 `sorted()`/`in`/真值），确认换成 `list` 语义不变。
2. 又读了 `src/agent/geometry/build.py:228-229`：`out.zones = [zv.zone for zv in zvs]` 与 `out.zone_volumes = zvs` 同一次赋值、同一个 `zvs`——这证明 `bg.zones` 的顺序和 `bg.zone_volumes`（`specs.py` 里更"权威"的 `_zone_order` 助手取的就是这个）逐位相同，所以 `pipeline.py` 侧沿用现成的 `list(dict.fromkeys(bg.zones))`（就是 flow 调用点上两行就在用的同一个表达式，日志那行本来就在算它）跟 `run_stage.py` 侧改的这行，产出顺序在数学上保证一致，不是巧合。
3. `pipeline.py` 里喂给 `check_mep` 的那处 `set(dict.fromkeys(bg.zones)) or None` **没有动**——那是另一条独立表达式，改 `run_mep` 的新参数不需要碰它，维持"没坏的东西不动"。

### 2.2 §2.2 输出形态：没有发现问题，未改判断

按派工单渲染成 `HVACTemplate:Thermostat` + 每区一个 `HVACTemplate:Zone:IdealLoadsAirSystem`。落地前用仓里真实的 `check_mep` 对着这个形态跑过（见 §4 的 A5 实测），`mep.hvac_schedule_refs` PASS，18 道检查零回归。共享一个 thermostat（不按区分）参照了下游 `src/agent/nodes/hvac.py` 的 system prompt 原文："If the spec gives one thermostat for all zones, reuse the same template_thermostat_name across all zones."——这不是我瞎猜的简化,下游自己的提示词就预期这个形态。

### 2.3 §2.3 时间表归属：选了 (a)，孤儿时间表实测数量

选 **(a)**：代码同时拥有 3 张时间表（`Sch_HVACDet_HeatingSetpoint` / `Sch_HVACDet_CoolingSetpoint` / `Sch_HVACDet_Availability`），随 `hvac_specs` 一起确定性并入 `schedule_specs`，不去猜模型写的哪张是"供暖设定点"。

**孤儿时间表实测**（用 5 份派工单点名的历史产物、真实 `mep_output.json`，逐个跑"覆盖前 vs 覆盖后"的引用扫描，不是估算）：

| 产物 | 覆盖前引用的时间表名 | 覆盖后变孤儿的（=正好是覆盖前那几个） |
|---|---|---|
| `run_2026-08-13_accept_C` | `Sch_Avail` / `Sch_ClgSetpoint` / `Sch_HtgSetpoint` | 3 |
| `run_2026-08-13_post_blocker1_e2e` | `Sch_Availability` / `Sch_CLG_Setpoint` / `Sch_HTG_Setpoint` | 3 |
| `run_2026-08-13_batchI_accept_02` | `Sch_Availability` / `Sch_Heating_SP` / `Sch_Cooling_SP` | 3 |
| `run_2026-08-13_accept_B` | `Sch_IdealLoads_Availability` / `Sch_Cooling_Setpoint` / `Sch_Heating_Setpoint` | 3 |
| `run_2026-08-09_f18_e2e_verify` | `Sch_Avail_On` / `Sch_Cooling_Setpoint` / `Sch_Heating_Setpoint` | 3 |

**5 份产物里恒定是 3 个孤儿**，且这 3 个恰好就是模型过去为 hvac 写的那 3 类时间表（供暖/供冷设定点 + 可用性）——符合预期，没有意外的额外孤儿。这些时间表本身合法（day-type 完整、type limits 齐全，因为它们本来就是通过历史门槛的产物），只是不再被任何字段引用；仓里没有孤儿检测门（`grep -i "unused|orphan|unreferenced"` 在 `checks/mep.py` / `schedules.py` 仍是 0 命中，本轮复核过一次），所以不会被任何检查标红，但也确实是本改动引入的、我如实记录的副作用。§2.4 的提示词更新预期会让这个数字在新产物里趋向 0（模型不再被要求写这 3 类），但这是行为预期，我没有拿一次真实 LLM 调用验证过（见 §5 未验证项）。

**权衡过的备选 (b)**（代码从模型的 `schedule_specs` 里启发式识别哪张是"供暖设定点"）被否掉：那等于把"哪张是供暖设定点"的判断权交回猜测，正是本摊要根治的"靠猜"模式,且派工单本身就倾向 (a)。

---

## 3. §3 接缝：确认未破坏

`checks/mep.py` 的 `_HVAC_SCHEDULE_REF_FIELDS` 表（摊 B 阻塞名单的锚点）我全程没有修改这个文件；渲染出的对象类型（`HVACTemplate:Thermostat` / `HVACTemplate:Zone:IdealLoadsAirSystem`）与该表现有的两个条目逐字一致。摊 B 的阻塞名单不需要因为本摊而失效。（我没有去看摊 B 的工作树/进度——按规矩不该看,也不需要看来完成这条确认。）

---

## 4. 验收条件 A1–A7 逐条实测结果

全部证据在 `tests/test_mep_hvac_deterministic.py`（15 条测试，函数名即用例名，均已跑绿，命令见下）。

### A1（防假验证自检）—— PASS

`test_a1_render_wired_neuter_flips_hvac_specs_content`：真跑一次 `run_mep`（只 stub `pipeline._call_json_llm`，`run_mep` 本体真执行），断言渲染内容存在；然后把 `pipeline._render_hvac_specs` 中和成返回空串，同一组断言反转为失败（实测 `hvac_specs == ""`）。
`test_a1_schedule_merge_wired_neuter_flips_the_real_gate`：同一手法但换一个更硬的判据——中和 `_merge_hvac_det_schedules` 后，**真跑 `check_mep`**，`mep.hvac_schedule_refs` 从 PASS 变 FAIL（因为渲染出的对象仍引用 3 张时间表，但时间表不再被注入)。两把锁都没有 monkeypatch `run_mep` 本体。

### A2（覆盖性锁）—— PASS

`test_a2_model_hvac_specs_content_is_discarded_even_when_broken`：stub 的 LLM 返回逐字复刻 accept_C 缺字段那段文本（4 格 `ZoneControl:Thermostat`），断言这段文本、以及它的组成对象类型名，一个字都不在 `run_mep` 返回值里；且返回值与渲染器直接输出逐字相等。
`test_a2_pure_garbage_string_is_discarded`：非 IDF 的纯垃圾字符串同样验证。

### A3（两条路径一致）—— PASS（过程含一次误诊，已澄清，见 §5）

`test_a3_flow_and_run_stage_paths_render_identical_hvac_specs`：真跑 `pipeline.run_pipeline_artifacts`（flow 路径的真实调用点）产出 `1_correction/correction_geometry_snapped.json`，把这份字节完全相同的产物喂给 `scripts.tool_scripts.run_stage._draw_mep`（run_stage 路径的真实调用点，内部真的调用真实的 `_geometry_zone_meta`），断言两条路径吐出的 `hvac_specs` 逐字相同，并额外用正则单独抽取区名顺序比对（不只是内容集合相同）。

### A4（引用闭合）—— PASS

`test_a4_referenced_schedules_exist_in_merged_schedule_specs`：只用仓里唯一的 IDF 解析器（`idf_fragments.parse_idf_text`，不复用 `check_mep._hvac_schedule_refs` 的实现,避免"用同一份逻辑测自己"）直接抽取渲染出的 `HVACTemplate:Thermostat` / `HVACTemplate:Zone:IdealLoadsAirSystem` 两类对象的时间表字段值,断言全部在合并后的 `schedule_specs` 里能查到同名 `Schedule:Compact`。
`test_merge_hvac_det_schedules_does_not_duplicate_existing_type_limits`：额外验证——如果调用方的 `schedule_specs` 已经定义了 `Temperature` 这个 `ScheduleTypeLimits`，合并后不会产生第二个同名对象（只补没有的 `OnOff`）。

### A5（门实测）—— PASS

对派工单 §1 点名的全部 5 份历史产物（`accept_C` / `post_blocker1_e2e` / `batchI_accept_02` / `accept_B` / `f18_e2e_verify`，真实归档文件，不是手搓夹具）逐份跑 `check_mep`：覆盖前后两次，断言零条从 PASS 变成非 PASS，且覆盖后 `mep.hvac_schedule_refs` 恒为 PASS。

`test_a5_accept_c_hvac_schedule_refs_was_broken_and_is_now_fixed` 是本批最具体的证据：先断言 `accept_C` **原始存档**的 `mep.hvac_schedule_refs` 确实是 FAIL（复现 F-28 本尊，不是合成的）,再断言覆盖后变 PASS——这就是派工单第一段讲的那次崩溃,现在直接从根上不会再发生。

### A6（全仓 pytest 绿）—— rc=1，但零回归（3 条环境假红，逐条独立核实）

命令与产物（本轮唯一使用,未复用过往文件名）：
```
python3 -m pytest -q -n 6 \
  > /tmp/.../scratchpad/testruns/full_20260814_070510.log 2>&1
echo "rc=$?" > /tmp/.../scratchpad/testruns/full_20260814_070510.rc
```
汇总行（`full_20260814_070510.log` 末行，原文摘录）：
```
FAILED tests/test_gt_from_dxf.py::test_build_only_cli_round_trips_l_candidate_and_nonzero_north
FAILED tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones - openai.O...
3 failed, 2615 passed, 10 xfailed, 210 warnings in 393.70s (0:06:33)
```
`.rc` 文件内容：`rc=1`。

**三条红逐条独立核实（不是转述 orchestrator,是我自己重新查证据链得到同一结论）**：

1. `test_gt_from_dxf.py` / `test_inspect_dxf.py`：单独重跑（`pytest tests/test_gt_from_dxf.py tests/test_inspect_dxf.py -n 6`）复现,子进程 traceback 里的路径字面是
   `File "/workspaces/EnergyPlus-Agent-dev/src/agent/judge/gt_manifest.py", line 278, in load_gt_tooling_config` ——
   注意这是**主树**路径,而测试跑在 `/workspaces/ep-wt-A`。根因：两条用例用 `subprocess.run([sys.executable, "scripts/tool_scripts/xxx.py", ...])` 起子进程,脚本式启动时 `sys.path[0]` 取脚本所在目录而非 cwd,`import src...` 落到 editable 安装记录的路径（指向主树）,子进程内部算出的 `REPO_ROOT` 因此是主树、和测试传入的 worktree 路径对不上,触发 `gt_vg_config_path_forbidden`。这两个测试文件我从未编辑（`git diff --stat -- tests/test_gt_from_dxf.py tests/test_inspect_dxf.py` 为空,已核）。
2. `test_zone_agent.py::test_zone_agent_creates_two_zones`：从我自己这次全仓跑的日志里摘出完整 traceback,最终异常是
   `openai.OpenAIError: The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable`
   （`openai/_client.py:587`,经 `langchain_openai` → `create_llm(node_name="zone")` → `zone_agent`）。该用例构造 `IntakeOutput` 后直接调用下游 `zone_agent`（9-subagent 图的一员,不归本项目管）,与 `hvac_specs`/`run_mep` 完全无关(该用例自己传的 `hvac_specs` 就是 `""`)。独立核实凭据缺口：`ls -la /workspaces/ep-wt-A/.env` 报 `No such file`,`ls -la /workspaces/EnergyPlus-Agent-dev/.env` 存在,`.gitignore` 第 173 行是 `.env`——三条命令都是我自己现跑的,不是抄结论。该测试文件我也从未编辑。

**账对上**：baseline（主树,`a413e66`）`2603 passed / 10 xfailed / 0 failed`,总计入库 2613 条(不含新增)。我的树 `2615 passed + 3 failed + 10 xfailed` = 2628 条,`2628 − 2613 = 15`,正好是我新增的用例数;且 `2603 − 3(worktree 必红的这三条) + 15(新增全绿) = 2615`,与实测 `2615 passed` 逐位对上。

⛔ 没有为了让这 3 条变绿去改这 3 个测试文件、改 `REPO_ROOT`、或往 worktree 塞 `.env`——原样保留环境差异,如实记录。

### A7（未放宽任何门）—— 确认

没有修改 `src/validator/checks/*.py` 任何一个文件。`MepOutput.hvac_specs` 从必填改可选（默认 `""`）是 pydantic 字段校验层面的改动,不是 `CheckReport`/`check_*` 意义上的"门"——覆盖逻辑在任何检查看到 `hvac_specs` 之前就已经跑完,不影响任何检查的判定结果(A5 的 5 份历史产物回归测试已实测覆盖此点：这 5 份产物原本 `hvac_specs` 都非空,不会触发这条防御性改动,但改动本身经过 A1/A2 用真实 `run_mep` 调用验证过不改变覆盖逻辑的行为)。

---

## 5. 我自己判断没做到 / 没验证的事项（如实写,不是自谦）

1. **没有用真实 LLM 调用验证下游 `hvac_agent`（`src/agent/nodes/hvac.py`）能正确消化新形态的 `hvac_specs`。** 这在派工单和项目不变量 #3 里都明确是"下游 9 subagent 消费、不归本项目管"的范围外,我读了它的 system prompt 佐证 §2.2 的判断（"reuse the same template_thermostat_name"）,但没有实跑一次真实 ReAct 调用去看它是否真的能把渲染出的文本正确转成 `create_thermostat`/`create_ideal_loads_system` 工具调用。
2. **没有跑一次真实 EnergyPlus 仿真去看最终 IDF 的 `HVACTemplate:*` 计数和数值是否符合预期。** 同样是下游范围;而且派工单 §1 已经用 `accept_B` 的证据说明 `hvac_specs` 原文本来就不会被逐字复制进最终 IDF,所以这条即使做了也验证不了"渲染器本身对不对",只能验证"下游 agent 今天恰好还能读懂"——价值有限,故未做。
3. **§2.4 提示词更新对孤儿时间表数量的实际影响没有验证。** §2.3 表格里的"3 个孤儿"是**改动前**历史产物的实测,预期新提示词生效后新产物的孤儿数会趋向 0,但这需要一次真实 LLM 调用才能验证,我没做——只是静态读了改后的 prompt 文本确认指令写对了。
4. **零区（`zone_names=[]`）边界情况没有写成 pytest 用例。** 手动跑过一次（`pipeline._render_hvac_specs([])` 产出仍是合法可解析的 IDF 片段,只是 0 个 `HVACTemplate:Zone:IdealLoadsAirSystem`）,行为是安全的,但没有把这次手动验证固化成回归锁。
5. **没有对 `run_profile="regression"` / `"golden"` 显式跑一次端到端。** A3 的端到端测试用的是 `"exploratory"`;A5 直接调 `check_mep` 不经过 `_gate_self_check_report`,所以 profile 分支未被行使到。由于 `mep.hvac_schedule_refs` 在 A5 的 5 份真实产物上稳定 PASS,理论上任何 profile 下都不会因为这条新逻辑被拦,但"理论上"不是"实测过"。
6. **没有去看摊 B（GLM 席位,`/workspaces/ep-wt-B`）的实际改动。** §3 的接缝确认只基于"我没碰 `checks/mep.py`,渲染形态与该文件现有条目一致"这一静态事实,不代表我核实过摊 B 那边此刻的真实实现状态——按规矩这原本也不该由我去看。
7. **A6 的"零回归"结论建立在"3 条失败原因已被日志/文件系统证据独立确认为环境问题"这一判断上,而非"逐条比对主树同一改动集是否同样红/绿"。** 我核实了 `.env` 存在性差异和子进程路径差异这两个具体机制,但没有另起一个不含我改动的干净 worktree 去做纯对照实验（orchestrator 消息提到已经在另一个干净 worktree `ep-wt-C` 上核过第三条,那是 orchestrator 做的,我自己没有独立复现那一步,只是核实了本机 `.env`/`.gitignore` 的状态与 traceback 本身）。

---

## 6. 对派工单本身的判断

没有发现派工单 §2、§3 的事实性前提有错。§2.2 的输出形态判断经 A5 实测成立,未行使"停下上报"。中途 orchestrator 转达的一次诊断（"A3 红是因为 `run_stage.py:703` 还是 `set(...)`"）与我自己独立重跑后看到的真实 `RuntimeError`（`assembly.contract_backstop` 因我的测试夹具缺 `construction_specs` 而非零回退,与区排序无关）不符——我按自己实测的证据链修复并重新验证,过程记在 §4 A3 和上面的自查项里,不代表派工单本身有错,是过程中一次转述/复核口径的分歧,已用可执行证据收敛。
