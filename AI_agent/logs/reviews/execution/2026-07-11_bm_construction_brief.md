# C2 B-M 施工执行简报 — 受信视图清单 + RunManifest 共同底座

> 执行档：Sonnet 5 子代理。规范来源：`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v6 定稿）+ `c2_b2_detail_spec.md §2.8`。
> 纪律：只施工、不做设计决策；稿内未写死的形态选择在文末"未决/偏离事项"逐条列明，不绕道。

## 1. 改动文件清单（规范章节 → 代码落点）

### 新建文件

| 文件 | 规范章节 | 内容 |
|---|---|---|
| `src/agent/correction/claims.py` | B2 稿 §2.8 | claims 词汇表常量模块（`CLAIM_*`/`WINDOW_CLAIMS`/`CLAIMS_VOCAB_VERSION`/plan·elevation 可观察集合）——内容以 B2 §2.8 为准，B-M 先落创建 |
| `src/agent/execution/view_manifest.py`（808 行） | §3 全量 + §4 全量 | strict typed schema（discriminated union `RequiredViewEntry`/`ExcludedInputEntry`，`OpeningEvidence`/`Coverage`/`CompletenessAssertion` 三 source 判别式联合，§3.6 联动 validator）+ strict generator（`build_view_manifest`）+ provision/verify API（`provision_view_manifest`/`verify_view_manifest`）+ `derive_input_inventory` |
| `src/validator/checks/view_manifest.py`（136 行） | §6 | gate① `reading.view_manifest_coverage`（INVARIANT，恒 BLOCK）+ `check_reading_stage`（"merge 同门"共享 checker：coverage + 逐 view schema lint，flat-flow 与 isolation merge 复用同一函数） |
| `tests/test_view_manifest_schema.py`（27 测） | §8.13 | discriminated union、条件约束、claims 词汇校验、entries canonical 排序/去重、CompletenessAssertion 三 source 正例 + 五负例 + coverage unknown-field 拒 |
| `tests/test_view_manifest_generator.py`（26 测） | §8.1/8.3/8.4/8.6 | 确定性、hash 纪律、sm21/sm20/sm24 三 fixture 全映射、生成期硬门全条、方向三轴、entry 身份负例 |
| `tests/test_run_manifest_v2.py`（22 测） | §8.10 | V1/V2 wire、versioned serializer、显式 migration + commit 协议、artifact_contract 8 例负例、孤儿 view_manifest 处理 |
| `tests/test_check_view_manifest_coverage.py`（5 测函数，17 用例，4 个参数化 × 4 run_profile + 1） | §8.8 | gate① 三态 × 4 个 run_profile 恒 BLOCK/PASS |
| `tests/test_claims_vocab.py`（4 测） | B2 §2.8 | claims 常量/词汇表校验 |

### 修改文件

| 文件 | 规范章节 | 改动 |
|---|---|---|
| `src/agent/execution/manifest.py`（+325 行） | §5.1 | `Hex64`/`Hex32` 类型；`StageRecordV1`/`RunManifestV1` = 现类字面别名（"现类原封"以同一类对象满足）；新 `ArtifactKey`/`ArtifactContract`/`StageRecordV2`/`RunInputs`/`RunManifestV2`；`_CONTRACT_REQUIRED_KEYS`/`_CONTRACT_ALLOWED_KEYS` 双表（必填+许可）；`save_run_manifest`（唯一 versioned serializer，`RunManifest.save()` 改为委托它）；`load_run_manifest`（版本分发，无文件返回 `None`）；`reading_attempt_allowed`（v1 grandfather 判定）；`ensure_run_manifest_v2`（isolation 正式 builder 用）；`migrate_run_to_v2`（显式迁移 + commit 协议：view_manifest 先落→backfill→RunManifestV2 最后落）；`assert_stage_artifact_contracts`（机制通用，具体 per-stage 表留 B2 供给） |
| `src/agent/execution/isolation.py`（+265/−~40 行） | §5.2 + §2 | `build_isolation_workspace`：早期 `build_view_manifest` 分类 case_data；`run_dir=None`→`merge_eligible:false`；`run_dir` 给定→只 `verify_view_manifest`（缺失即拒建，绝不在此处 provision）+ `ensure_run_manifest_v2` 绑定 + 写 `binding.json`/`input_inventory.json`；`_copy_case_data` 只拷 `required_view`，`excluded_input` 记入 `excluded_from_staging` 不拷贝；`merge_isolated_output` 全重写：读 binding→拒绝非 merge_eligible→拒绝 run 不匹配→拒绝 v1 grandfather→拒绝 identity drift（`verify_view_manifest` 比对）→聚合 payload `{"views":{stem:...}}` 解析→`check_reading_stage` 同门校验→`report.blocking()` 非空时 `accept=True` 静默不生效→写 `StageRecordV2(artifact_contract="reading_isolated_v2")`；移除本地 `_atomic_save_manifest`（改用共享 `save_run_manifest`） |
| `src/agent/execution/validation_run.py`（+33 行） | §4.4 | 0_reading 块新增 `view_manifest` 只读比对：磁盘无 view_manifest.json→`NOT_APPLICABLE`（老 anchor 零 BLOCK）；有→`check_view_manifest_coverage(verify 结果)` |
| `scripts/tool_scripts/run_stage.py`（+79 行） | §4.4/§6 | `_draw_reading` 接入 `provision_view_manifest`（自动 provision，0_reading preflight）+ `check_reading_stage`（替换旧 `check_reading_view` 逐 view 手动循环，行为等价 + 新增 coverage 检查）；新 `provision`/`--migrate` CLI verb（`cmd_provision`） |
| `src/agent/reading/legacy.py` + `src/agent/reading/__init__.py`（+16 行） | — | 抽出 `parse_reading_view(dict)`（`load_reading_view` 的路径无关核心），供聚合 payload 无文件路径场景复用 |
| `src/agent/execution/__init__.py`（+52 行） | — | 导出全部新符号 |
| `tests/test_isolation.py`（重写，37 测） | §5.2/§9 | 见下"预期行为变化" |
| `tests/test_check_parity.py`（+5 行） | — | `_EXCLUDED_VALIDATE_CHECKS` 补 `("0_reading","reading.view_manifest_coverage")`：validate_case-only 审计项，`run_pipeline` 本批未接线（见"未决事项"），用既有的 parity 豁免机制登记，非削弱该锁 |

## 2. 测试计数

- **改前基线**（改造前 `pytest -q` 记录）：**570 passed, 9 xfailed**
- **改后终态**：**678 passed, 9 xfailed, 0 failed**（净增 108 条通过，xfailed 数不变，零回归）

全量输出尾部：
```
678 passed, 9 xfailed, 116 warnings in 298.68s (0:04:58)
```

sm20/sm21 golden 目录（`case_tests/e2e_tests/{sm20,sm21}_anchor/run_2026-06-*`）在本轮未做任何写操作核实：`validate_case` 新增的 view_manifest 检查在磁盘无 `_run/view_manifest.json` 时走 `NOT_APPLICABLE` 分支，不产生新 BLOCK；`test_validation_run_baseline.py` 全绿佐证。

## 3. 两处预期行为变化（设计内收紧，非回归）

1. **`tests/test_isolation.py` 空 views 接受断言反转**：旧合同下 `merge_isolated_output` 对 `{"views":[]}` 直接接受（`test_merge_archives_provenance_and_binds_hash` 断言 `rec is not None`）。新合同下同一情形只**归档**（attempt 落盘、可审计）但**不接受**（`load_run_manifest(run_dir).accepted("0_reading") is None`）——见 `test_merge_empty_views_is_filed_but_not_accepted`。
2. **v1 run 上新 0_reading attempt BLOCK**：`reading_attempt_allowed()` 对已持久化 `manifest_version=="1"` 的 run 拒绝新 0_reading attempt，提示走显式 `provision --migrate`。**本批实际接线范围 = isolation merge 路径**（`merge_isolated_output` 调用该 guard，见 `test_merge_refuses_grandfathered_v1_run`）+ 该 guard 函数本身的直接单测（`test_v1_run_blocks_new_reading_attempts`）。**未接线进 `run_stage.py` 的一般 `flow`/`resample` CLI 路径**——原因见"未决/偏离事项 #1"。

## 4. 备份位置

`backup/src_history/2026-07-11_bm_view_manifest/`（改动前原始文件，保持相对路径）：
```
src/agent/execution/{manifest.py, isolation.py, __init__.py, case_metadata.py, validation_run.py}
src/agent/reading/{legacy.py, __init__.py}
src/validator/checks/{__init__.py, reading.py}
scripts/tool_scripts/run_stage.py
tests/test_isolation.py
```
（该目录匹配仓库 `.gitignore` 的 `20*_*/` 规则，不入库——与仓库现有 backup 惯例一致。）

## 5. 验收（B-M 稿 §9）

sm21/sm20/sm24 `build_view_manifest` 干跑全部成功（无 raise）。

**sm21（6 条，2 plan dimensioned + 4 elevation user/building_axis+standard_assumption）**：
```json
{
  "case_id": "sm21_anchor", "content_sha256": "f52ca79c...e493e",
  "entries": [
    {"input_id":"1f_view","view_type":"plan","floor_ref":1,"dimensioned":true,
     "direction_source":"standard_assumption","direction_semantics":"building_axis",
     "expected_output_id":"1f_view","opening_evidence.potentially_observable_claims":["along","existence","host","width"]},
    {"input_id":"2f_view","view_type":"plan","floor_ref":2,"dimensioned":true, "...同上模式..."},
    {"input_id":"East_view","view_type":"elevation","declared_direction_token":"East",
     "direction_source":"user","building_view_direction":"East","dimensioned":true,
     "opening_evidence.potentially_observable_claims":["along","appearance","existence","head","sill","width"]},
    {"input_id":"North_view","...同 East 模式，token=North..."},
    {"input_id":"South_view","...同 East 模式，token=South..."},
    {"input_id":"West_view","...同 East 模式，token=West..."}
  ]
}
```
全部 6 条：`negative_evidence_capable_claims=[]`、`coverage=null`、`completeness_assertion=null`（C2 域无显式受信来源声明）；entries 按 input_id 字典序排列（ASCII 下数字排在字母前），实际输出顺序为 `1f_view, 2f_view, East_view, North_view, South_view, West_view`。

**sm20 supp_plan 条目**（唯一 supplementary/detail 分类实例）：
```json
{
  "input_id": "supp_plan", "kind": "required_view", "view_type": "detail",
  "expected_output_id": "supp_plan_view", "floor_ref": null, "dimensioned": false,
  "direction_source": "standard_assumption", "direction_semantics": "building_axis",
  "source_image": "case_data/supp_plan.png",
  "opening_evidence": {"potentially_observable_claims": [], "negative_evidence_capable_claims": []}
}
```
（sm20 全部 8 条 `dimensioned=false`——该 case 未声明 `dimensioned_views` 顶层键，符合现状对账 §1#1。）

**sm24（5 条，单层无 supplementary）**：`{1f_view(plan,floor_ref=1), East/North/South/West_view(elevation)}` 全部干净生成，无硬门触发。

## 6. 未决 / 偏离事项（稿内未写死的形态选择，逐条列明）

以下各点稿内**没有给出可直接照抄的具体形态**（JSON 键名/CLI 参数形状/生成器触发机制等），我做了工程判断并已在代码/测试中落地并写清注释，但按纪律必须在此列出，供主控核对是否符合意图：

1. **v1 grandfather 拒绝新 0_reading attempt 只接线进 isolation 路径，未接线进 `run_stage.py` 一般 flow/resample CLI**。原因：要让"新建的空 run 首次 attempt 后仍能继续被同一 run 使用"这件事正确，`run_stage.py` 的 `RunManifest.load()`/`StageRunner.record()` 调用点需要**系统性切到 `load_run_manifest`/version-aware StageRecord 构造**（不是加一个 guard 就够——否则任何新建 run 存盘一次 V1 后，第二次调用就会被误判"已存在 v1 grandfathered"而拒绝，破坏全部现有 flow 用法）。这个改动面覆盖 6 个 stage 的通用 attempt 记录路径，风险远超"改一个 check"，且稿内没有明说"本批需要把整条 flow CLI 切到 V2 by-default"。已把 wire（V1/V2 类型、迁移、guard 函数）完整做好并单测覆盖，接线到 isolation（§5.2 明确要求 run_id）这一处无歧义、风险可控的位置；**一般 flow 路径何时/是否切 V2-by-default，留给下一批（大概率是 B2，届时 correction writer 本来就要发 `StageRecordV2`）判断**。
2. **`validate_case` 的 view manifest 检查未接线进 `run_pipeline` 生产路径**（`run_pipeline.py` 属"不碰 B2 领地"红线，本批未改）。这导致新 check_id 在 `validate_case` 端"多出"，与既有 `tests/test_check_parity.py` 的两路 check_id 对称锁冲突——已用该测试**已有的**豁免机制（`_EXCLUDED_VALIDATE_CHECKS`，本就是为这类"validate_case-only 审计项"设计的既有安全阀）登记，注明原因；未削弱、未绕过该锁的核心断言，只是补了一条与既有 8 条同类的登记项。
3. **isolation 聚合 payload 的 JSON 形状** `{"views": {<expected_output_id>: <ReadingView JSON>, ...}}` 是我定的（旧测试原有一个占位 `{"views":[]}`/`{"views":[1]}` 从未被真正解析消费过）。选它的理由：与 flat-flow `_draw_reading` 的 `output_obj`（`{stem: view_dict}`）形状一致、能直接复用同一 `check_reading_stage`，且沿用了既有 `"views"` 外层键名不引入陌生词。
4. **`views{}` 覆盖槽的具体 JSON 键**（`direction_semantics`/`azimuth_deg`/`view_kind`/`dimensioned` 覆盖、`excluded_reason`/`parent_input_id` 排除声明）是我设计的最小可用形状，稿内只给了"存在覆盖槽"的概念（§4.2 表格行），没给键名。已用合成 fixture 单测覆盖其行为。
5. **`views{}.completeness` 驱动 `negative_evidence_capable_claims` 生成（"case metadata 完整性断言"受信来源）未实现**。§3.6 CompletenessAssertion **strict wire 本体**（三 source 判别式 + 五负例 + 联动 validator）已完整实现并测试（`test_view_manifest_schema.py`）——这是 r4 明确"冻结"的部分。但**生成器侧**如何从 `testdata_prompt.json` 的某个 JSON 形状触发"某 view 的某几个 claim 开启负证据能力"这件事，稿内没有给出具体 JSON schema，我没有替它发明；当前 3 个 anchor case 都不需要这条通路（`negative_evidence_capable_claims` 全部合法为 `[]`），测试已验证"默认空"这一半（§8.7 第一分句）。三 source 正例本身已在 schema 层验证。
6. **`Path of the supplementary plan example drawing for the building` → `view_type="detail"`**（而非 `site_plan`）的分类是我的判断：因为 metadata 从不为它提供 `floor`，而 `floor_ref` 对 `plan` 必填、对其余类型禁填，`detail` 是唯一不引入虚假 floor_ref 的选择；`site_plan` 语义上更像"总平面图/含指北针"，与 sm20 supp_plan 实际内容（据以往识图记录，是另一版本的楼层参考图）不完全吻合。
7. **`expected_output_id` 映射规则**用了一条通用确定性规则（stem 已以 `_view` 结尾则原样；否则追加 `_view`），而非稿字面提到的"映射表"（逐 key 硬编码）。用真实反例校验过：sm20 `supp_plan → supp_plan_view` 与稿内举例完全吻合；此规则同时对 sm21/sm24 全部 `*_view` 命名保持恒等，无already-observed 反例。若未来出现不遵守"stem+`_view`"约定的声明 key，需要为它单独在映射表里加例外——当前实现的 `_expected_output_id()` 函数是唯一改动点，改动面很小。
8. **`provision --migrate` CLI 的确切参数形状**（`provision <case> <run> [--migrate]`，无参数=只 provision view manifest；带参数=触发 RunManifestV2 迁移）是我设计的最小接口，稿内只提到"provision --migrate CLI（唯一写盘例外，显式旗标）"这一行字，没给参数表。

无一项属于"无法按稿实现被迫放弃"；均为稿内留白处的最小、可回退工程判断，已在代码注释/测试里可追溯。

## 7. 范围纪律确认

- 未改 `src/agent/correction/{schema.py, deterministic.py, config.py, geometry_validator.py, facade.py}`、`src/agent/pipeline.py`、`src/agent/judge/*`、任何 render 脚本、任何 gt 文件——`claims.py`（B-M 先落创建，内容锁定于 B2 §2.8）为唯一例外，符合"不碰 B2 领地"红线。
- 未执行任何 LLM case 跑测；全部验证走确定性单测 + 干跑 `build_view_manifest`。
- 未 `git commit`/`push`，工作树留待主控审 diff 后统一处理。
