# 跨家族复核裁决 · F-97 契约判别器（GPT 家族 sol）

- **日期**：2026-08-27　**复核席位**：**GPT 家族 sol**（`gpt-5.6-sol`，effort `xhigh`）
- **被审 commit**：`8fda4c10ca3a23f4159f78ff29aebf706d904eae`　**工作目录**：`/tmp/ep_f97`
- **请求单** → [`../request/2026-08-27_f97_contract_discriminator_crossreview_gpt.md`](../request/2026-08-27_f97_contract_discriminator_crossreview_gpt.md)
- **总判：REWORK**（3 条阻断 · 3 条不阻断）

> ⛔ orchestrator 落库说明：以下为复核方回复**逐字**（仅去掉行内文件链接的绝对路径前缀）。
> 本裁决**未**落进施工 worktree（`/tmp/ep_f97` 会被回收），正文以本文件为准。

---

主体方向正确，现仓 371 份 `0_reading/*.json` 的兼容面、四种指定行为、两次 neuter 和全量都得到预期读数；但判别器仍有三条可复现的核心缺口：带未知显式 `schema` 的文件可被误当 legacy 消费、畸形 CheckReport 可被静默排除、真实 `run_correction` 可在写消费对账前先由 reading preflight 崩掉。它们分别破坏 F-a/F-b/F-c，不能以全量绿覆盖，因此须返工而不是附 findings 放行。

## 一、§四六条判据逐条读数

| 判据 | 结论 | 本席实测读数 |
|---|---|---|
| **A1** 全量 | **PASS** | 在 HEAD `8fda4c1`、仅有开工前复核请求单未跟踪的状态运行 `python -m pytest -q -n 4`：**3058 passed / 13 xfailed / 0 failed**，211 warnings，380.08 s。基线 3035 + 新增 23 = 3058。|
| **A2** 四条 affected-tests allowlist | **PASS；题面前提有误** | 四条都**应该删除**。独立调用 selector，`as_drawn/{__init__,_plan_ink,as_drawn_v2,pens}.py` 每个均为 `SCOPE: SUBSET`，各选中 **144 个测试文件**且包含 `tests/test_f97_vector_contract.py`。该表维护的是静态依赖图的“不可达精确集合”，不是行为覆盖清单；继续保留会使 `uncovered == allowlist` 为假。行为覆盖仍弱，但不构成本次删除的阻断项。|
| **A3** B1″ 变化面 | **PASS** | 当前 checkout 内有 69 个名为 `0_reading` 的目录，其中 **56** 个根目录含直接 `*.json`，共 **371** 份候选；**49** 个目录提示词字节不变、**7** 个改变。**新增 0**；移除 **43** 份、全部判为 `stage_check_report`，43/43 也都能按生产 `CheckReport` 类型解析；移除 `*_view.json` **0**；总减少 **170,455 bytes**。|
| **A4** 四行为 + 主动找缝 | **FAIL** | 指定四行为本身可区分：普通未知红且含 `unknown contract`；as-drawn 红且含 `no wire for it`、不含 `unknown contract`；合法 stage report 不红且 ledger 点名；双命中红且含 `AMBIGUOUS`。但主动夹具发现：`schema="future_reading_contract_v99"` + 合法 legacy `strokes` 被判为 `reading_view_legacy/consume`，形成新的静默消费通道；另有畸形 stage report 静默排除。|
| **A5** neuter | **PASS** | neuter① 只把真实入口改回 `discover_vector_files(...)` 后跑全量：**3054 passed / 13 xfailed / 4 failed**，恰为 F-97 自己的 unknown / as-drawn / sidecar / ambiguous 四条入口锁，零附带。还原后，neuter② 把生产者 import 换成字面量，只跑反字面量锁：**0 passed / 1 failed**，目标锁准确变红。两次均已还原。|
| **A6** 两次误替换的后果 | **PASS（另有真实入口覆盖缺口，列阻断项 B-03）** | `git diff --check` 通过；`tests/test_f97_vector_contract.py` 共 347 行，collect 得 **23** 个测试项，23 条均通过；与 affected-tests map 合跑为 **38 passed**。逐行核过 helper、四入口锁、六份无 `dimensions` 参数化断言，没有发现被错误文本替换吞掉的断言或残留语法/字典破坏。施工方旧跑的时间 provenance 无法由提交反推；本席以树冻结后的独立全量和 neuter 读数替代。|

### A3 的 7 个目录逐项字节读数

| 减少字节 | 边车份数 | 目录 |
|---:|---:|---|
| 15,230 | 7 | `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading` |
| 13,080 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/0_reading` |
| 13,080 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading` |
| 13,080 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading` |
| 13,080 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading` |
| 42,013 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r1/0_reading` |
| 60,892 | 6 | `case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r2/0_reading` |
| **170,455** | **43** | **合计** |

## 二、请求单 §二四处实测结论

### 2.1 affected-tests 四条删除

**结论：该删，不阻断。**

`affected_tests.py` 的图只回答“改这个模块时应选择哪些 pytest 文件”，其 `uncovered_allowlist` 又被 `test_every_production_module_is_mapped_or_honestly_allowlisted` 锁成静态不可达模块的精确集合。F-97 新链路为：

`test → pipeline → vector_contract → as_drawn_v2 → {_plan_ink, pens}`。

四个模块现在各自都能选中 144 个测试文件，故不再是 uncovered。施工方说“行为没有覆盖”是事实，但那是另一种测试债；保留 allowlist 既不会制造行为断言，也会让规则表撒谎。更重要的是，全量里本来也没有这些函数的行为锁，退回 FULL 并不能抓住其逻辑变更，因此不能把 selector 的 import 边误说成“测试已证明行为正确”，也不能把这一语义错置成当前提交的阻断项。

### 2.2 B1″ 的 170,455 字节变化

三件事独立复核结果：

1. **只减不增**：新增文件数 0；实现也是从同一 `discover_vector_files` 有序列表中过滤，不存在新来源。
2. **移除者全是 gate① 报告**：43/43 均判 `stage_check_report`，且 43/43 能由 `src/validator/checks/schema.py:CheckReport` 解析；没有任何 `*_view.json` 被移除。
3. **口径边界**：56 是当前 checkout 中“根目录直接含 `*.json` 的全部 `0_reading` 目录”，不是抽样；另 13 个同名目录根部没有直接 JSON，故本变更影响为零。仓外、未入库或已回收的历史 run 数量无法从本 worktree 推断，真全集漏网量**不可量化**。施工报告明确称“可测全集”，没有把它冒充真全集，故此项不阻断。

### 2.3 四种行为与主动找缝

指定四种行为均实测成立：

- `{"hello":1}`：`UnconsumableVectorFile`，点名文件并含 `unknown contract`；
- `as_drawn_v2.SCHEMA` + 三个必需层：红，含 `no wire for it` / `NOT unknown`，不含 `unknown contract`；
- 合法 `stage_check_report`：不红、从 prompt 排除，ledger 为 `exclude` 且有 reason；
- 同时满足 as-drawn 与 legacy 的夹具：红，含 `AMBIGUOUS` 且理由点名两个契约。

但主动搜索找到了两条未被施工测试覆盖的缝：

- **未知显式 schema 回落 legacy**：夹具顶层声明 `schema="future_reading_contract_v99"`，其余为可由 `ReadingView` 解析的合法 `strokes`。实测得到 `ContractDecision(contract_id='reading_view_legacy', disposition=CONSUME)`，随后会进入 correction prompt。根因是 `vector_contract.py:100-108` 的 legacy detector 不检查显式声明，而 `:171-173` 对唯一命中直接接受。这违反原派工单“legacy 那种没声明的才退回结构识别”，正是新的静默通道。
- **畸形 stage report 被排除**：夹具 `{"stage":7,"results":"not-a-result-list","report_schema_version":{"not":"a version"}}` 被 `CheckReport.model_validate` 拒绝，却被当前判别器判 `stage_check_report/EXCLUDE`。根因是 `vector_contract.py:140-145` 只看三个键名存在。未知坏文件因此既不红也不进 prompt，和“合法排除”混在一起。

### 2.4 三条施工不确定项的定性

1. **45 份 as-drawn checks 报告未登记：不阻断，但理由需要改。** 本席实测 45 份全部位于 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/`，当前 `0_reading` 为 0；但 `src/validator/checks/as_drawn.py:821-837` 的生产代码接受任意 `out_path`，代码侧确实能写到 `0_reading`。若未来要共置，必须在接线前登记独立契约；当前会 fail-closed、不会静默喂给 correction，故本单安全目标尚未被它破坏，不升阻断。
2. **`stage_check_report` 签名仍是归纳：阻断。** 仓里已有 `CheckReport` 类型，且当前 43 份真实边车 43/43 均可解析。严格更优且不需碰禁区文件的做法是“显式存在三键 + `CheckReport.model_validate` 成功”；当前只认键名会静默排除畸形未知 JSON，已由夹具证伪。
3. **B1″ 可测全集口径：不阻断。** 当前 checkout 的直接输入面已穷尽；仓外历史量不可量化，应继续把读数写成“本 checkout 可测全集”，不能升级为全世界历史 run 的真全集。

## 三、Findings

### 阻断

#### B-01｜未知显式 schema 可被误当 legacy 消费

- **证据**：`schema="future_reading_contract_v99"` + 合法 legacy strokes ⇒ `reading_view_legacy/consume`，真实 prompt 入口不红。
- **影响**：任何未来显式契约只要仍带 `strokes`，就可能绕过 unknown loud-fail；F-97 的静默通道以另一种形态保留。
- **返工要求**：显式声明不能无条件回落 legacy。应保留“已登记显式契约 + legacy 同时命中 ⇒ AMBIGUOUS”，但“存在未登记/畸形显式 schema + legacy 结构”必须判 unknown；补真实 `_build_correction_messages` 入口锁。

#### B-02｜stage report 以键名 proxy 冒充生产契约，畸形 JSON 被静默排除

- **证据**：上述畸形夹具被 `CheckReport` 拒绝，但判别器返回 `stage_check_report/EXCLUDE`。
- **影响**：F-b 的“未知契约响亮红”不成立，ledger 会把坏文件记成合法排除。
- **返工要求**：复用已有 `CheckReport` 类型并保留三键显式存在约束；补“键齐但类型非法 ⇒ unknown loud-fail”的入口锁。当前 43 份历史边车全部能通过该更严格路径，兼容面不需牺牲。

#### B-03｜消费对账在真实入口写得太晚，分类失败可能无 ledger

- **证据**：把合法 JSON 列表写成 `1f_view.json` 并调用真实 `run_correction(..., out_dir=...)`，实测先在 `pipeline.py:720-725` 的 evidence preflight 触发 `AttributeError: 'list' object has no attribute 'get'`；`pipeline.py:738-739` 的 ledger 尚未执行，`_run/reading_vector_contract_ledger.json` 不存在。
- **影响**：既没有 F-97 的点名异常，也没有 F-c 承诺的失败对账。`tests/test_f97_vector_contract.py:263-275` 只直调 `_write_vector_contract_ledger`，其“run that fails”说明是 helper proxy，不是生产入口锁。
- **返工要求**：在任何会解析 `*_view.json` 的 preflight 前完成分类/ledger，或让 preflight 复用同一次分类结果；新增真实 `run_correction` 入口负例，至少覆盖非对象/非法 JSON。

### 不阻断

#### N-01｜as-drawn toolbox 仍无行为测试

四条 allowlist 删除正确，但 `_plan_ink.py` / `pens.py` 的逻辑仍未被行为断言触发。应另开测试债；不要通过向“静态不可达精确集合”塞入已可达模块来伪装修复。

#### N-02｜as-drawn checks 报告需在未来共置前登记

当前 45 份均不在 `0_reading`，进入时会响亮红而非静默消费，故不阻断；但它是仓内生产代码定义的真实形态，未来 harness 若把它与 as-drawn 读图产物共置，必须先增加独立 contract/disposition。

#### N-03｜语料变化面只对当前 checkout 完备

本席确认当前 371 份直接 JSON 已全测；仓外/未入库历史 run 无法给上界。报告应持续保留该限定语。

## 四、我认为 orchestrator 在请求单里题面写错的地方

1. **补充裁定的 as-drawn 数量写错**：题面称 `as_drawn_plan_v2` **132 份**。本席逐份解析全仓 JSON 的顶层 `schema`，实际为 **77 份 = 32 份 reading product + 45 份 checks report**；再加 `as_drawn_plan_v0` 4 份和 `as_drawn_elevation_v0` 4 份，as-drawn 家族合计 **85**，不是施工终报沿用的 140。施工方在停下上报提交 `e08c79b` 中原本也报的是 77，后续把正确读数改成了题面数字。该计数错不改变本单修法，但事实陈述不成立。
2. **A2 把 affected-test 的“静态可达”写成了“行为覆盖”**：`uncovered_allowlist` 和 selector 的实现、元测试都只以 import/string-path 图判可达；四模块现在各有 144 个选测文件，理应删除。题面“只是 import 边 ⇒ 删除必须判阻断”的判定把两个不同问题混为一谈。
3. **补充裁定给 `stage_check_report` 的签名少了一层已有信任根**：只写“无 schema + 含三键”会直接允许 B-02。仓内已有 `CheckReport`，且 43/43 历史边车都能解析；“三键显式存在 + 生产类型解析成功”是严格更优且不扩禁区文件的路径。按请求单停下上报触发器，这一点应由 orchestrator 回写裁定。

## 五、最终测试与工作树纪律

- 干净全量：`python -m pytest -q -n 4` ⇒ **3058 passed / 13 xfailed / 0 failed**。
- neuter① 全量：**3054 passed / 13 xfailed / 4 failed**，四红仅 F-97。
- neuter② 定向：**1 failed**，仅反字面量锁。
- 所有临时探针与两次变异均已删除/还原；被审源码、测试和规则文件相对 HEAD 无工作树 diff。
- 开工前即已有未跟踪复核请求单；本席未修改或删除它。交件新增仅本裁决文件。
