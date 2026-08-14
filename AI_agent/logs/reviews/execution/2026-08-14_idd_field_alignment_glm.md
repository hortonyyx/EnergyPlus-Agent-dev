# 执行报告 · 摊 B —— IDD 驱动通用字段对齐门（2026-08-14）

- **席位**：GLM-5.2（执行档施工，摊 B）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-14_idd_field_alignment_gate_dispatch_glm.md`
- **工作树**：`/workspaces/ep-wt-B`（分支 `wt/0814_B_idd_alignment`，基点 `a413e66`）
- **审阅去向**：跨家族（非 GLM 侧）

---

## 0. 承重前提核实（动手前先做）

派工方历史错误率 16/16 全是题错 ⇒ 我逐条证伪了承重前提，结论：

| 派工单声明 | 核实结果 |
|---|---|
| §1 `grep arity\|field_count\|expected_fields src/` 0 命中（10 条误命中） | ✅ 成立。实测 **9 条**误命中（parity/granularity/collinearity），零真命中。外围数字小误（10→9），结论一致：**仓里零字段个数/对齐校验**。 |
| §1 18 道 mep 检查全是语义检查 | ✅ 成立。逐条核实，18 个 check id（派工单 §三已校正）无一做字段个数/对齐校验。 |
| §1 IDD 元数据可用、通用门便宜 | ✅ 成立。`data/dependencies/Energy+.idd` 经 eppy `objidd` 暴露 `\field`/`\required-field`/`\extensible`，零新依赖。 |
| §3 阻塞名单两类 = 摊 A 确定性生成 | ✅ 接缝有效。语料里确有 `HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM ×42` + `HVACTEMPLATE:THERMOSTAT ×2`，但 IDD 只要求 `Name`/`Zone Name`（各 1 必填），**44 个对象零缺必填** ⇒ 今天阻塞名单零触发。 |
| §2.1 判据 2「21 份语料一次没触发」 | ⚠️ **外围论据错，已修正（见 §6.1）**：真因不是「语料没有超字段对象」，而是 **eppy 结构上不允许超字段对象进入检查**（截断/crash 两机制）。判据 2 在真实 parse 路径恒为死代码。主体照做（判据 2 仍实现 + monkeypatch 夹具证明逻辑）。 |

**未触发停止规矩**：承重前提（§1 实测、§3 接缝）全对；唯一错的是 §2.1 的外围论据（判据 2「没触发」的原因），按规矩「外围论据错 ⇒ 报告写明，主体照做」。

---

## 1. 做了什么

### 1.1 新检查 `mep.idd_field_alignment`（`src/validator/checks/mep.py`）
check_mep 现有 **19 个 check id**（原 18 + 新 1）。新检查走现有 `IdfFragmentIndex`（`parse_mep_fragments`），⛔ 零自写正则。

- **判据 1（missing_required）**：IDD 标了 `\required-field` 的格，实际缺失或为空。逻辑与 orchestrator 预扫 `probe_arity.audit_object` 逐位一致（用 `obj.raw.objidd` 读 `\required-field`，`obj.fields` 按索引定位）。
- **判据 2（too_many_fields）**：authored 字段数 > IDD 字段数，且非 extensible。
- **extensible 豁免**（见 §5.1）。
- **按类型缓存 IDD 元数据**（同类型 objidd 相同），避免 extensible 对象（Schedule:Compact 展开 10000 字段）重复读。

### 1.2 分档（用户拍板，§2.2）
- 阻塞名单 `_IDD_ALIGNMENT_BLOCK_TYPES = {"HVACTEMPLATE:THERMOSTAT", "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"}`，**一处具名常量** + 注释指向摊 A + 接缝失效警告。
- **实现方式**：`CheckResult.layer` 运行时定 —— 有阻塞名单 offender ⇒ `INVARIANT`（disposition→BLOCK）；否则 ⇒ `CROSS_CHECK`（disposition→FLAG）。**零改 `schema.py` 的 `disposition()`**（纯函数天然按 layer 走）。

### 1.3 §2.3 病因交叉引用
`_idd_field_findings` 返回 `diseased: {(obj_type, name) → {field, check_id}}`。`_load_refs` / `_hvac_schedule_refs` 收 offender 时查它，命中则给该 offender 加 `disease_ref: {check_id, missing_field}`，并在 check 顶层 evidence 加 `disease_cross_ref` 汇总。样板形状照抄 `mep.people_field_alignment` 的 `disease_vs_symptom`。

### 1.4 §2.4 去重口径（见 §5.3）

### 1.5 测试 `tests/test_mep_idd_field_alignment.py`（11 测试，全绿）
clean/tiering/extensible/B1 两条判据 neuter/去重/两条 disease_ref/B2 预扫复现。

---

## 2. 关键判断与理由

1. **分档用 layer 运行时定，不改 `disposition()`** —— `disposition()` 已有 5 个 check-id-specific 特殊分支，再加一个会让纯函数更臃肿；而 `CheckResult.layer` 本就是运行时传入的字段，一个 check 按情况选 layer 完全在 schema 允许范围内，且语义清晰（「对阻塞名单对象是 invariant，对其余是 cross_check」）。
2. **extensible 判定靠 `objidd[0]` 的 `extensible:N` 键** —— 实测 eppy 不暴露 plain `extensible` 字段（返回 None），而是把 `\extensible:N` 存成键名 `extensible:N`（Schedule:Compact 有 `'extensible:1'`，Material 无）。这是 §2.1「显式处理」的正确入口。
3. **判据 2 保留为防御性死代码 + monkeypatch 夹具** —— 见 §6.1。逻辑写对（authored>idd 且非 extensible ⇒ 报），但因 eppy 不让超字段对象进入检查，真实路径恒不触发；派工单 §2.1 明令「必须为它单独构造夹具锁」，故用 `SimpleNamespace` fake raw 构造 authored>idd 形态证明逻辑 + neuter。

---

## 3. 验收条件 B1–B6 实测

### B1 防假验证自检 ✅（两条判据各 neuter 一次）
- **判据 1**（`test_b1_criterion1_missing_required_lock_and_neuter`）：锁 = 缺必填格的 ZoneControl:Thermostat 必产生 `missing_required` offender（绿）。monkeypatch `_idd_object_meta` 把所有字段标 non-required（中和判据 1）⇒ missing_required offender 消失（若判据 1 是死代码，neuter 不会改变结果，断言会失败 ⇒ 证明锁真绑判据 1）。
- **判据 2**（`test_b1_criterion2_too_many_fields_lock_and_neuter`）：锁 = fake raw（authored=10 > IDD=9，非 extensible）必产生 `too_many_fields`（绿）。monkeypatch 强制 `extensible_group=2`（中和判据 2 的豁免条件）⇒ too_many_fields 消失（证明锁真绑判据 2）。
- 两条 neuter 测试均通过 ⇒ 锁经过被改代码、摘得动。

### B2 预扫复现 ✅（21 份判据逐份一致）
- 20 份 git 跟踪产物：红 14 份 + 绿 6 份，**逐份对象级计数与 `prescan_output.md` 吻合**（`test_b2_prescan_reproduction`）。
- 第 15 份红 `smalloffice_23`：其 `4_mep/` 被 `.gitignore:320` 显式忽略，**不在 git**，只存在于 orchestrator 主树的临时文件 ⇒ 本干净 worktree 没有。**只读主树验证判据吻合**（9 People 缺 Activity Level Schedule Name，对象级 9 = 预扫 9）。
- accept_C 的 14 个恒温器（Control 1 Name 缺）**必须被抓到** ⇒ 抓到（`findings_by_kind.missing_required == 14`）。探针自证兑现。
- 差异逐条见 §5.2。

### B3 零回归 ✅（7 份产物 blocked 集合逐字节一致）
用临时 worktree 跑基线 `a413e66` 的 `check_mep`，对比当前。7 份产物（含 batchI_accept_02 / accept_B / accept_C）的 `blocking()` check-id 集合**改动前后完全相同**：

| 产物 | 基线 blocked | 当前 blocked |
|---|---|---|
| batchI_accept_02 | `[]` | `[]` |
| accept_B | `[]` | `[]` |
| accept_C | `[mep.hvac_schedule_refs]` | `[mep.hvac_schedule_refs]` |
| sm20 baseline | `[]` | `[]` |
| sonnet_e2e_r1 | `[mep.load_to_schedule]` | `[mep.load_to_schedule]` |
| oneshot_acceptance | `[]` | `[]` |
| sm24 opus_reading | `[]` | `[]` |

`mep.idd_field_alignment` 未进入任何一份 blocking（advisory 正确）。

### B4 parity ✅
`mep.idd_field_alignment` 被 `check_mep` 总 emit（PASS/FAIL）。`test_check_parity.py`（46 passed 含本）断言 run_pipeline 与 validate_case 两侧 `(stage, check_id)` 集合相等 ⇒ 新 check id 两侧都出现。

### B5 全仓 pytest（rc=1，2 failed 预先存在、与本摊无关）
`python -m pytest -n 6 -q` ⇒ **`2 failed, 2612 passed, 10 xfailed` in 337.44s**，rc=1（`.rc` 文件名 `/tmp/b5_fullrun_rc.txt`，本轮独有，未复用）。

两个 failed：
- `tests/test_gt_from_dxf.py::test_build_only_cli_round_trips_l_candidate_and_nonzero_north`
- `tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract`

**这 2 个与本摊零关系**：
1. 两个测试文件**零 import** `validator.checks.mep`（grep 确认）；本摊只动 `src/validator/checks/mep.py` + 新增 `tests/test_mep_idd_field_alignment.py`。
2. 失败根因 = `ValueError: gt_vg_config_path_forbidden`（DXF 转换器 vg-config 路径守卫）+ `NorthAxisBindingV1` Pydantic 序列化不匹配 —— 均在 DXF 转换器代码路径，与 mep 检查无关。
3. **基线 `a413e66` 独立 worktree 复现这 2 failed**（串行 `-n0` 同样红）⇒ 预先存在，非本摊引入。

**零回归数字吻合**：当前 2612 passed = 基线 2601 passed（派工单 2603 − 这 2 failed）+ 本摊新增 11 测试。即本摊的 11 个新测试全绿、既有 2601 个 passed 一个不少，2 failed 基线就有。

⚠️ **派工单基线声明 `2603 passed / 0 failed` 不准**（§1 + §4 B5）：基线实际有这 2 个 DXF failed。见 §6.4。

### B6 不放宽/关闭任何现有门 ✅
- 未删/未降档 `mep.people_field_alignment`（仍 INVARIANT/BLOCK，工作正常）。
- 18 个既有 check id 的 `status`/`layer`/`disposition` 全未改；只给 `_load_refs` / `_hvac_schedule_refs` 的 offender **新增**（非修改）可选 `disease_ref` 字段 + 顶层 `disease_cross_ref`，不改它们的阻断结论（B3 已证）。

---

## 4. 你自己判断没做到 / 没验证的事项（必填，如实）

1. **判据 2 在真实链路上零实测**。它结构上不可达（eppy 截断/crash，§6.1），仅有 monkeypatch/fake-raw 夹具证明**逻辑与接线**，没有任何真实产物或真实 parse 路径走过它。若将来换 parser（非 eppy），它才会生效——届时需补真实路径验证。
2. **判据 2 的 `too_many_fields` 今天的语义价值存疑**。eppy 已经用「截断（静默丢字段）」或「crash（idf_parse ERROR/BLOCK）」两种方式处理了超字段，判据 2 在当前架构下是 eppy 之后的第二道防线，但 eppy 的第一道防线（尤其**静默截断**，如 Lights 把第 18 字段悄悄丢了不报错）本身就是一个**未被任何门捕获**的真问题——本摊没有修 eppy 的静默截断（超出派工范围，且 §2 明令「idf_fragments.py 是唯一 parser」不动）。这是比判据 2 更值得登记的隐患。
3. **`smalloffice_23` 第 15 份红无法在本 worktree 回归**（4_mep 被 gitignore）。`test_b2_prescan_reproduction` 只覆盖 git 跟踪的 20 份（红 14）；其 People-缺-A5 形态由其他 4 份纯-People run 覆盖，但 smalloffice_23 本身不在 CI 回归里。
4. **去重口径是「不复述诊断」不是「不报 offender」**（§5.3）。同一个错位 People 对象仍会同时出现在 `mep.idd_field_alignment`（报 A5 缺）和 `mep.people_field_alignment`（报 A4 错位）两个 check 的 offender 里——只是两者报的**格不同**、idd_field_alignment 不复述 misalignment 诊断。若审阅方认为「同一对象出现在两个 check offender 里」仍算重复，需另定口径（但那会破坏 B2 的 run 级红）。
5. **性能**：按类型缓存了 IDD 元数据，但 extensible 对象（Schedule:Compact）的判据 1 仍遍历 eppy 展开的 10000 字段找 required（只有前几个 required）。B2 扫 20 份产物 2.64s，可接受；全仓性能待 B5 确认。
6. **摊 A 接缝只验证了「今天 44 个 HVACTemplate:* 零缺必填」**。摊 A 若改了确定性生成的类型集（§3），我的 `_IDD_ALIGNMENT_BLOCK_TYPES` 当场作废——我无法预判摊 A 的最终形态，只能照派工单初值实现并加注释警告。

---

## 5. 派工单 §5 要求的四条

### 5.1 extensible 对象怎么判定的、豁免了哪些
- **判定**：`_idd_object_meta` 检查 `raw.objidd[0]` 是否有键名匹配 `extensible:<N>`（eppy 把 IDD `\extensible:N` 存成这样的键，**不是** plain `extensible` 字段——这是 dump `objidd[0].keys()` 发现的）。`N` = 扩展组大小。
- **豁免**：extensible 对象**豁免判据 2**（`too_many_fields`），因为字段数本就可变。**判据 1（missing_required）不豁免**——extensible 对象的 required 字段（通常只有前几个，如 Schedule:Compact 只有 Name）仍照常检查。
- 语料里的 extensible 对象：`SCHEDULE:COMPACT`（`\extensible:1`，eppy 展开 10000 字段）、`ZONEHVAC:EQUIPMENTLIST`（`\extensible:2`，110 字段）。两者均按此处理。

### 5.2 B2 差异逐条解释
两处「数字对不上」，均**非判据差异**：
1. **字段级 vs 对象级计数口径**：预扫 `flagged` 是**对象级**（有几个对象带 finding），本检查 `offenders` 是**字段级**（每个缺的必填格一条）。例：sm24 opus_reading 每个 thermostat 缺 3 格 ⇒ 本检查报 33 字段级 + 11 equipmentlist = **44**，但对象级 = 11+11 = **22 = 预扫 flagged**。其余 run 多为每对象 1 finding，字段级 = 对象级。`test_b2_prescan_reproduction` 用**对象级**对比预扫，逐份吻合。
2. **smalloffice_23 在本 worktree 不存在**：`4_mep/` 被 `.gitignore:320` 忽略，是主树临时文件。只读验证判据吻合（9 People 缺 A5）。

### 5.3 §2.4 去重口径
- `mep.people_field_alignment` 拥有 People **错位 disease**（A4 持非 enum 值）。
- `mep.idd_field_alignment` 从**通用 IDD 视角**报同一根因（A5 必填格空），**不复述** misalignment 诊断（不带 `reason`/`field_A4_...`/`diagnostic` 这些 people_field_alignment 专有的键）。
- 两者报**不同的格**（A5 缺 vs A4 错位），所以「字段错位」不会被对同一个 People 计两次。evidence 里 `people_dedup_note` 显式说明这层关系。
- 这保证 B2（People-缺-A5 的 run 仍红）与 §2.4（不重复 misalignment 诊断）同时满足。

---

## 6. 派工方题错的地方（主动证伪）

### 6.1 ⚠️ §2.1 判据 2「没触发」的真因 = 结构性不可观测（外围论据错）
派工单说「第 2 条在 21 份语料上一次没触发 ⇒ 结构上不可观测的一半 ⇒ 必须构造夹具锁」。「必须构造夹具锁」对，但「结构上不可观测」的**真因**派工单没说准：

- **不是**「语料里没有超字段对象」。
- **而是** eppy parser **结构上不允许超字段对象进入检查循环**，两机制：
  - **静默截断**：如 Lights（IDD 17）写 18 字段 ⇒ eppy 解析出 17 字段、悄悄丢第 18 个、不报错 ⇒ `authored(17) == idd(17)` ⇒ 判据 2 恒 False。
  - **crash**：如 Material/Construction 写超 ⇒ eppy 抛 `TypeError: unsupported operand type(s) for //` ⇒ `parse_idf_text` 捕获 ⇒ `mep.idf_parse` ERROR/BLOCK ⇒ `check_mep` fail-closed return，**永远走不到判据 2**。
- ⇒ 判据 2 对**任何能被解析的对象**，`authored > idd` 恒不成立。它是真实 parse 路径上的死代码。比派工单说的「没触发」更彻底。

**影响**：判据 2 的夹具无法走真实 parse（eppy 产不出超字段对象），只能用 `SimpleNamespace` fake raw 构造（已在 `test_b1_criterion2` 诚实标注）。这同时暴露一个**更该登记的隐患**：eppy 对 Lights 的**静默截断**（丢字段不报错）本身未被任何门捕获——见 §4.2。

### 6.2 smalloffice_23 的 4_mep 被 gitignore（预扫语料含未跟踪临时文件）
预扫 `probe_arity.py` 在 orchestrator 主树（`/workspaces/EnergyPlus-Agent-dev`）跑，扫到了 `smalloffice_23/4_mep/mep_output.json`——但该路径被 `.gitignore:320`（`case_tests/e2e_tests/smalloffice_23/4_mep/`）忽略，**不在 git**，是主树工作目录的临时文件。我的干净 worktree 没有 ⇒ B2 在本树只能跑 20 份。这是 F-8 族「关键输入不在 git 里」的又一例。

### 6.3 「10 条误命中」实际 9 条（外围数字小误）
§1 说 `grep` 10 条误命中，实测 9 条。结论一致（零真命中），数字小误。

### 6.4 ⚠️ 派工单基线「2603 passed / 0 failed」不准
§1 与 §4 B5 都声明基线 `a413e66`（`-n auto`）是 `2603 passed / 10 xfailed / 0 failed`。实测基线独立 worktree（串行 `-n0`）**这两个 DXF 测试就 failed**（`gt_vg_config_path_forbidden` + NorthAxis 序列化）。即基线真实是 `2601 passed / 2 failed`（或 `-n auto` 时这两个碰巧绿/被并行吞——无论哪种，「0 failed」不成立）。

**不影响本摊结论**：本摊改动零回归（§B5 数字吻合）。但审阅方须知：本摊交付态全仓 rc=1，红线是预先存在的 DXF 问题，**不是本摊引入**，也**不应要求本摊修这 2 个 DXF 测试**（超出派工范围 §2，且 `idf_fragments.py`/DXF 转换器不是本摊的 mep.py）。建议另立项核实这两个 DXF 测试为何在基线就红。
