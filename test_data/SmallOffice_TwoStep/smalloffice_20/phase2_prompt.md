# Phase 2 启动 Prompt（Opus 路径用，直接粘进新 Claude Code 会话）

> 用法：在 `EnergyPlus-Agent-dev` 项目根新起 Claude Code 会话（Opus 4.7），把下面 "---" 之间的内容整段粘贴作为首条消息。DeepSeek 路径由脚本 `Tool_scripts/run_phase2_deepseek.py` 自动跑，不用本 prompt。

---

我在做 intake 两步法 POC 的 phase 2。phase 1（识图 → 矢量 JSON）已完成（产物在 `test_data/SmallOffice/smalloffice_20_redraw/phase1_vector/`）。本会话只做 **phase 2：矢量 JSON → IntakeOutput**——不看图，纯文本推理。

## 必读

按顺序读：

1. [test_data/SmallOffice/smalloffice_20_redraw/phase2_rules.md](test_data/SmallOffice/smalloffice_20_redraw/phase2_rules.md) — phase2 完整规则（输入输出 / 坐标翻译公式 / IntakeOutput 字段推导顺序 / 命名规则 / vertex 合成 / 自检）
2. [test_data/SmallOffice/smalloffice_20_redraw/vector_schema_v1.md](test_data/SmallOffice/smalloffice_20_redraw/vector_schema_v1.md) — phase1 输出格式参考（只为理解你拿到的输入长什么样）
3. [test_data/SmallOffice/smalloffice_20_redraw/phase1_vector/phase1_summary.md](test_data/SmallOffice/smalloffice_20_redraw/phase1_vector/phase1_summary.md) — phase1 总结（含 4 立面 local↔world 翻译公式，**直接套用**）
4. 7 份 phase1 矢量 JSON（按需读，不必全读）：
   - `phase1_vector/1f_view.json`、`2f_view.json`、`3f_view.json`
   - `phase1_vector/South_view.json`、`North_view.json`、`East_view.json`、`West_view.json`
5. [test_data/SmallOffice/smalloffice_20_redraw/testdata_prompt.json](test_data/SmallOffice/smalloffice_20_redraw/testdata_prompt.json) — 元信息（楼层数、面积、城市、用途）

## 任务

按 `phase2_rules.md` §3 的字段推导顺序产 IntakeOutput Pydantic JSON，落到：

```
test_data/SmallOffice/smalloffice_20_redraw/phase2_intake/opus/intake_output.json
```

格式参考 IntakeOutput Pydantic 在 [src/agent/state.py](src/agent/state.py) 的定义。11 字段必须齐：building / site_location / zone_specs / material_specs / schedule_specs / construction_specs / surface_specs / fenestration_specs / hvac_specs / people_specs / lights_specs。

9 个 `*_specs` 字段是**自然语言指令**（不是结构化数据），但必须明确、可机械执行、内部一致——下游 9 个 subagent 要靠这些字符串干活。命名规则严格（仅字母/数字/`_`，跨字段字面一致，禁止模板写法）。

## 心智模型

- 你已经"看完图"了——视觉信息全在 phase1 JSON 里。**不要再去翻原 PNG**
- 任何与"图上数值"相关的错都是 phase1 的锅（已 frozen）；你只能引入纯推理错（拓扑、命名、字段格式、坐标翻译）
- phase1 JSON 里 `null` = "phase1 没看见"，**不要当 0 算**；缺失就在你输出里相应标注
- 立面 local 坐标必须按 `phase1_summary.md §3` 的公式翻回世界系，**不要自行推**

## 工作流

1. 通读 5 份必读文档（rules / schema / summary / testdata_prompt + 抽几份 JSON）
2. 按 phase2_rules §3 Step 1→7 顺序在心里推一遍，确认有把握再开写
3. 写 `phase2_intake/opus/intake_output.json`——一次性写完，**不要分多次 append**
4. 写完后跑自检（phase2_rules §7 清单 9 项），把自检结果写在 `phase2_intake/opus/self_check.md`
5. 如果 phase2_rules 哪里覆盖不到、需要你"自由发挥"才能完成的地方，在 `phase2_intake/opus/phase2_followup_notes.md` 记下来，便于后续补 rules 文档

## 边界

- 不要改 phase1_vector/ 任何文件（phase1 产物已 frozen）
- 不要改 phase2_rules.md / vector_schema_v1.md（如有建议放在 phase2_followup_notes.md）
- 不要改 [src/](src/) / [skills/](skills/) / [AI_agent/](AI_agent/) 任何文件
- 不要跑 `run_full_pipeline.py` 或任何 EnergyPlus 工具
- 不要看原 PNG 图（phase2 纪律）

完成后输出三个文件：`intake_output.json` / `self_check.md` / `phase2_followup_notes.md`（如有）。
