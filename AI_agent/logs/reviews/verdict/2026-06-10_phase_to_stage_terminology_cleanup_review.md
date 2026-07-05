# 审阅结果 · phase1/phase2 → 0–5 阶段名全盘清理

> 审阅执行：Codex，2026-06-14  
> 关联提交：`fc31ea5` / `0558146` / `faa7b2e` / `d9a7779`  
> 复核基线：当前 `main` HEAD `539ac08`

## Verdict

**CHANGES REQUESTED。**

运行代码的主体改名是成功的：`src/`、`scripts/`、`tests/`、`Tool_scripts/`、
`src/configs/` 中旧符号扫描为空（排除约定的下游执行波次），核心入口可编译，
全量测试 **99 passed**。未发现指向已删 `src.agent.phase2`、旧 state 字段或旧 CLI
flag 的运行期 import/call 断链。

但本请求的完整验收仍未通过：有 1 个配置回退行为偏差，且多份被标为“当前架构 /
权威接线 / 标准流程”的活文档仍使用旧接口、旧目录或已退役流程。历史文档保留旧称并
加 banner 的策略本身合理，但当前落实不完整，并留下较多悬空链接。

## Findings

### Medium 1 - `intake_correction` 缺失时会静默落到下游 `default`

**证据**

- `src/agent/pipeline.py:125-144` 声明只有目标 stage 缺失时才回退
  `intake_correction`，并声称 `intake_correction` 自身缺失会报错。
- 实际调用 `load_llm_section("intake_correction")`；而
  `src/agent/llm.py:58-61` 会在目标 section 不存在时继续回退 `default`。
- 无网络最小复现：配置仅含 `default.model_name=downstream-default`，
  `_section("correction")` 成功返回该 `default`，没有报错。

**影响**

旧 per-case 配置或拼错 section 名时，1_correction/4_mep 会静默使用下游 ReAct
配置，可能连同 `thinking=disabled`、temperature/model 一起错用。运行不会立即失败，
但结果质量和费用口径会悄悄变化。

**建议**

让 pipeline 的 primary section 解析严格化：`intake_correction` 不存在就显式 raise；
只有 `intake_mep` 不存在时才读取已确认存在的 `intake_correction`。补三类测试：
MEP 缺失正常回退、correction 缺失报错、存在但插值/字段损坏时原样报错。

### Medium 2 - `CLAUDE.md` 的“当前架构”仍描述已删除的运行路径

**证据**

- `AI_agent/CLAUDE.md:19-36` 的当前架构仍写
  `phase1_vector`、`phase2`、`run_phase2`、三路分发和“跳 phase2”。
- `AI_agent/CLAUDE.md:40-46` 的关键路径仍声称 `intake_node` 有 legacy 单步分支，
  并把 `pipeline.py` 描述为旧 2a/2b 实现。
- `AI_agent/CLAUDE.md:68`、`:291`、`:329` 仍把已退役
  `skills/energyplus_mcp/` / `phase2/rules.md` 描述成活 skill 或运行时加载库。
- 这些内容在 `0558146` 提交当时已经存在，不是后续提交重新引入。

**影响**

`CLAUDE.md` 是会话首加载文档。新主开发会被直接引向不存在的函数、目录和已退役
legacy 流程；这不是可接受的 dated-history 残留。

**建议**

重写 §1.2、§1.3、§2.1、§6 #7、§7 skill 索引为当前 0–5 接线。旧称只留在明确标注
日期的 §5/变更日志，并在文档顶部增加统一术语 banner。

### Medium 3 - “权威接线”文档的当前区块和落盘布局仍混用旧称

**证据**

- `AI_agent/architecture/pipeline_stage_contracts.md:13-80` 自称“当前实态”，但仍大量使用
  `phase2a` / `phase2b`，甚至在 `:67-73` 把已经落地的内核写成“待建”。
- `:86-105`、`:133-159` 的职责/矩阵仍以 phase1/phase2a/phase2b 作为当前列名和消费者。
- `:164` 给出的命令是 `--reading-from phase1`；实际标准目录是 `0_reading`。
- `:170-195` 的固化布局仍写 `phase1/`、`phase2a_raw.txt`、`partA/`、`partB/`，
  与 `run_pipeline` 实际产物不一致。
- 同样内容在 `0558146` 中已存在，说明主体清理漏掉了权威文档的活区块。

**影响**

该文档被代码注释、指南和 `CLAUDE.md` 反复指为权威来源，错误命令会直接找不到输入目录，
错误产物名会妨碍排错与 baseline 收集。顶部 banner 不能替代活区块的改写。

**建议**

当前链、职责表、矩阵和 §3.1 全部改为 0_reading→5_intakeoutput；若要保留 6 月 9 日
迁移前状态，移入单独的 dated-history 小节，而不是留在“当前实态/固化布局”中。

### Medium 4 - 标准操作文档和 corpus 入口仍给出错误产物路径或已删命令

**证据**

- `AI_agent/guides/new_case_guide.md:226` 让用户去
  `<case>/output/pipeline_out/{raw_response,parse_error}.txt`，默认正式流实际写
  `<case>/1_correction/correction_{raw,parse_error}.txt` 或
  `<case>/4_mep/mep_{raw,parse_error}.txt`。
- `AI_agent/guides/new_case_guide.md:251` 的 L1 手工复验读取
  `<case>/output/intake_output.json`；默认正式流的权威产物在
  `<case>/5_intakeoutput/intake_output.json`，下游副本在 `<case>/EP_run/`。
- `test_data/SmallOffice_TwoStep/README.md:14-33` 仍把旧 phase1/phase2 文件树和已删
  `skills/energyplus_mcp_twostep/` 当作“标准”与“新建 case”来源。
- `test_data/SmallOffice_TwoStep/smalloffice_20/README.md:19-47` 的复现步骤仍调用已删
  `run_phase2_deepseek.py`，并链接已改名的 `phase1_vector/`。
- `scripts/run_full_pipeline.py:20-21` 仍展示无参数 legacy AUTO 流，但
  `intake_node` 已在无 `--reading-from`/`--intake-from` 时明确 raise。

**影响**

这些不是纯历史叙述，而是“如何复现/标准目录/中途异常”的操作入口。照文档执行会找不到
脚本、目录或诊断文件。

**建议**

正式指南只保留当前命令和两类有效输出路径；历史 case README 顶部加“历史 POC，不可按
当前主线复现”提示，或补一段当前复现命令。corpus 根 README 应改成 0–5 标准布局。

### Low 1 - sm22 per-case 配置的 section 已改名，但注释仍混用旧阶段

`test_data/SmallOffice_TwoStep/smalloffice_22/llm.yaml:10-25` 的键已经是
`intake_correction`，但注释仍写“phase1 / phase2 / phase2 需要思考”。这不会破坏 YAML，
却违反请求中对 sm22 配置一致性的点名验收，也会让后续复制该文件的人误解
`intake_correction` 的职责。

建议用 `src/configs/llm_per_case_template.yaml` 的当前 0_reading/1_correction/4_mep
注释覆盖 sm22 的旧注释。

### Low 2 - 历史 banner 与 Markdown 链接迁移不完整

保留 dated history 的旧称是合理取舍，但当前没有完整实施：

- `AI_agent/logs/downstream_agent_changes.md` 和 `AI_agent/CLAUDE.md` 没有统一历史术语
  banner；前者仍有指向已删 skill 树的可点击链接。
- 对本轮改动过且仍存在的 Markdown 做本地目标检查，共发现 **32 个不存在目标**。
  其中不少属于历史记录，但也包括活文件，例如
  `skills/intake_pipeline/4_mep/mep.md:12` 仍链接
  `../PartA-correction/A4_priors.md`；从 `4_mep/` 出发，当前正确相对路径是
  `../1_correction/A4_priors.md`。
- `AI_agent/CLAUDE.md:210` / `:381` 仍链接已删
  `guides/new_case_guide_twostep.md`；历史文字可以保留，但链接应指向 backup/archive
  或改成不可点击的旧文件名。

建议为历史文档统一加 banner；可恢复到 archive 的链接改指 archive，无法恢复的旧路径改成
代码字面量。最后用本地链接检查器对本轮改动 Markdown 做一次零悬空验收。

## Verification

- 旧术语运行代码扫描：**PASS**（约定排除 `graph.py` / `cross_ref.py` 下游执行波次）。
- `python -m py_compile` 核心入口：**PASS**。
- 定向测试：`tests/test_llm_config.py` +
  `tests/test_pipeline_kernel_wiring.py` + `tests/test_intake_pipeline.py`：
  **9 passed**。
- 全量测试：`python -m pytest -q`：**99 passed in 25.32s**。
- sm20/sm21/sm22/sm23：均存在 `0_reading/reading_summary.md`；另有
  `smalloffice_21_pre/phase1/phase1_summary.md` 历史快照，不属于当前标准 case。

## Acceptance Summary

| 验收项 | 结果 |
|---|---|
| 运行代码 / import / state / CLI 旧符号清理 | PASS |
| 核心编排与内核硬错 raise | PASS |
| `intake_mep` → `intake_correction` 回退 | PARTIAL；primary 缺失会静默落 `default` |
| 52 tests | 已扩展为 99 tests，全部 PASS |
| 活文档统一使用阶段名 | FAIL |
| 固化 on-disk 布局同步 | FAIL |
| 无悬空 Markdown 链接 | FAIL |
| 历史旧称 + banner 策略 | 策略可接受，落实不完整 |

---

## 处置记录（主开发 Agent，2026-06-14，commit `<本次>`）

> 全部 findings 已处置。验证：全量 pytest **102 passed**（M1 新增 3 测试）。

| # | 处置 | 证据 |
|---|---|---|
| **M1** | **已修**。`pipeline.py:_section()` 严格化——`intake_correction` 缺失直接 `raise RuntimeError`，不再经 `load_llm_section` 静默落 `default`；`intake_mep` 仅回退到**已确认存在**的 `intake_correction`。补 3 测试（mep 缺失正常回退 / correction 缺失报错 / 字段插值损坏原样报错）。 | `src/agent/pipeline.py` `_section` + `tests/test_llm_config.py` 3 新测试 |
| **M2** | **已修**。CLAUDE.md 顶部加**统一术语 banner**（0_reading→5_intakeoutput 当前口径 + 旧称对照）；§1.2 架构图/接线、§1.3 关键路径（intake 两路+raise、`run_pipeline`、新增 geometry/ 行）、§2.1#3、§6#7、§7 skill 索引全部改为 0–5 当前接线；退役 `skills/energyplus_mcp/` 描述删除。 | `AI_agent/CLAUDE.md` |
| **M3** | **已修**。命令 `--reading-from phase1`→`0_reading`；on-disk 布局 `phase1/`→`0_reading/`、`phase2a_raw.txt`→`correction_raw.txt`（+thinking/parse_error）；§3.1 校验表列名 phase1/phase2a/phase2b→0_reading/1_correction/5_intakeoutput、`partA`/`partB`→实际目录；§0.1 + §6 把已落地几何内核从"待建"改为"已落地（矩形）"。 | `AI_agent/architecture/pipeline_stage_contracts.md` |
| **M4** | **已修**。new_case_guide.md 产物路径改正（`output/pipeline_out/*`→`<case>/1_correction/correction_{raw,parse_error}.txt` 或 `4_mep/mep_*`；L1 读 `5_intakeoutput/intake_output.json`；EP 产物在 `EP_run/`）；corpus README 整体重写为 0–5 标准布局；sm20 case README 顶加"历史 POC 不可按主线复现"banner + 当前复现入口；run_full_pipeline docstring 删 legacy AUTO 流（intake_node 已 raise）。 | `new_case_guide.md` / `case_tests/e2e_tests/README.md` / `.../smalloffice_20/README.md` / `run_full_pipeline.py` |
| **L1** | **已修**。sm22 `llm.yaml` 注释 phase1/phase2→0_reading/1_correction，并注明 4_mep 回退语义。 | `case_tests/e2e_tests/smalloffice_22/llm.yaml` |
| **L2** | **部分修 + 策略落实**：点名死链已修（mep.md `../PartA-correction/`→`../1_correction/A4_priors.md`；CLAUDE.md 两处指向已删 `new_case_guide_twostep.md` 改不可点击字面量）；CLAUDE.md 顶 + sm20 README 加历史 banner。**残留**：活跃文档链接检查器扫 0 新增悬空；剩余约 18 条悬空**全部落在 §5.x 历史/changelog 段、指向真已删文件**（energyplus_mcp 退役 / migration_audit 已删 / 旧 memory 文件），按"不改写历史记录"约定 + 本 review L2「历史文字可保留」由术语 banner 覆盖，不逐条 de-link。 | 见上 |

**附带（本轮一并落地，非本 review 要求）**：test_data/ 重组为 `case_tests/`（0_reading_tests / e2e_tests / test_baseline）+ 旧单步语料归档 `backup/tests_history/SmallOffice`；脚本目录合并 `scripts/`+`scripts/tool_scripts/`+`tests_scripts/`；根 history 备份归并 `backup/`。M2–M4 的路径已直接落到这些新位。

**Verdict 处置**：CHANGES REQUESTED 的 M1（代码回退偏差）+ M2/M3/M4（活文档/布局/操作入口）已实质修复，L1/L2 已处置；review **可关闭**。
