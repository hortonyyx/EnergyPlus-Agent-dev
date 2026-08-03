# R1 批 B · r1 交叉对抗审（路 2）· 被审 = R1-1…R1-4 / R1-6 / R1-7（GLM 产出）+ 补完 P-3…P-9

> **✅ 本文最终版**（骨架阶段的暂定结论已全部被本版覆盖）

- **日期**：2026-08-03
- **审阅席**：Claude 侧子代理（Opus 档）· 跨家族对抗审（施工 = GLM）
- **被审 commit**：`63a41b9`(R1-1) / `2daf846`(R1-1 context·J-1) / `3e3ac1e`(R1-2+J-2) /
  `6d38f0c`(R1-3) / `c9b1aae`(R1-4) / `472c844`(R1-6) / `1e3be7f`(R1-7)
- **⛔ 不在范围**：`c56cbe1`（R1-5，terra 产出 = 路 1）· 批 C · 批 D · R1.5
- **工作树**：主仓库零改动（唯一写入 = 本报告）；全部破坏性探针在
  `/tmp/.../scratchpad/probe`（`git clone --local --no-hardlinks`，HEAD `48e41b6`）内进行，
  探针后 `git status --porcelain` 仅剩我自己的未跟踪探针文件、被审文件逐字节恢复。
  主仓库全程只跑只读 git（`log`/`show`/`diff`/`rev-parse`），**未跑 `git status`**。

---

## 0. 总判定

> **REWORK（窄 r2）** —— **0 BLOCKER / 2 MAJOR / 3 MINOR / 2 NIT**

**先说好的一面（这批的质量高于本项目近几批平均，且高于 r0）**：

- **G-1（本单权重最高）成立**。11 个实现钩子逐一 neuter，**每次恰好红对应的锁、零假锁**；
  R1-1 / R1-2 / R1-7 三条的锁**真的走 `cmd_flow` 命令函数**（不再是 r0 L-13 那种「把 `None` 喂内部函数」），
  断言落在 **`checks.json` 头部字段 + 具体 check-id 行**上；R1-4 断言「失败后盘上无产物」、
  R1-6 断言「伪造 `image_sha256` 被拒」，两条都按派工单 §3.3/§3.4 的形状写。
- **P-3 成立且是真跑的**：真实 `load_score_view_bindings` + 两个 validator 在 sm24 签字 GT 上通过，
  `content_sha256` 仍是 `459513f1…`，往返后逐字节与 wire 类型均不变。**上一轮「三方都验了机制、没人真跑」的坑没有复发。**
- **G-4 / P-6 我主动证伪失败**（见 §5），是反向坐实。

**判 REWORK 的理由（两条 MAJOR 都是「同一形状还活着」，不是新病）**：

| # | 一句话 | 为什么是 MAJOR |
|---|---|---|
| **F-1** | `capability_profile` 拼错一个字母仍然静默降档 | **这正是批 B 立项要根除的那条分叉**，活体探针复现；按审阅单 §4A G-2 判据「找到一条即不成立」 |
| **F-2** | 冻结记录的 `source` 字段是硬编码常量，与真实来源无关 | 派工单 §2.1 #4 逐字要求「记录 source，而不是两个没有来源的字符串」；且它让 R1-1b 的一句断言恒真 |

**两条的修复面都很窄**（各约数行 + 一条锁），**不需要重做架构** ——
若 orchestrator 认定 F-1 属「施工席已在执行日志 §6.5 主动上报、且明确请示过是否要对称、orchestrator 未答复」
的**已披露欠规格边界**（施工席**没有**自行降级为假设，形态是对的），则本判定降为
**APPROVE-WITH-CHANGES**。**这个选择权在 orchestrator，不在我。**

---

## 1. G-1…G-7 逐条

### G-1（最高权重）六条的锁全部真绑、走真实入口、断言落具体 check-id 行 —— **成立**

**neuter 台账见 §3**（11 个钩子 / 11 次独立摘除 / 每次恰好红目标锁 / 零假锁 / POST-RESTORE 51 全绿）。

- **真实入口**：R1-1a/b/c、R1-1 context、R1-2 typo、R1-2 absent、R1-7 conflict、R1-7 same-value
  **全部调用 `rs.cmd_flow(...)`**（`tests/test_run_stage_flow.py:700-950`），
  且 `run_profile` 传的是 argparse 的**真实默认值** `"exploratory"`（不是 `None`）
  ⇒ **r0 L-13 那条「绕过 argparse 默认值」的形状在 R1-1/2/7 上确实被修掉了**。
  ⚠️ 但入口是 `SimpleNamespace` 手搓的 args、不是 `main()` 的 argparse（见 **F-6 NIT**），
  且 **L-13 自己那条锁一字未改**（见 **F-3 MINOR**）。
- **断言形态**：R1-1c 落 `report.run_profile` / `report.capability_profile` / `report.run_policy_sha256` /
  `report.run_policy_source` **四个头部字段** + `1f_view.reading.dimension_chain_closure` 这一具体 check-id 行的
  `status is FAIL` 且在 `report.blocking()` 里（`tests/test_run_stage_flow.py:800-806`）。
  **没有「返回值存在 / 总数变了 / 字段非空」这种形状** —— 唯一的例外是 `assert record.source == "structured_config"`，
  它在该路径上**恒真**（见 **F-2**）。
- **R1-4**：`tests/test_reading_ruler_r1_batchB.py:240-244` 断言
  `not (run_dir/"_run/view_manifest.json").exists()` **且** `not (…/"run_policy.json").exists()`
  ⇒ 断的是「盘上没有可用产物」，不是只断 raise。**neuter N9（把校验移回写盘后）恰好红它一条、零连带。**
- **R1-6**：`"0"*64` 占位 fixture 的语义**已经反过来**了 —— `_set_structured_dim`
  （`tests/test_reading_ruler_r1_batchB.py:71-88`）现在把每条声明的 `source.image_sha256`
  **覆写成该 view 的真实 image hash**，另有一条 `test_R1_6_forged_image_hash_rejected` 用 `"f"*64`
  期望 **raise**。派工单 §3.4 的要求满足。

### G-2 病灶在所有真实路径上都关上了 —— **⛔ 不成立**（F-1）

**证伪成功。** 探针 A（`/tmp/.../probe/tests/test_zz_claude_probe.py`，走真实 `cmd_flow`）：

```
run_config.yaml:  run_profile: regression
                  capability_profile: orthogonal_polygone      ← 拼错一个字母
PROBE-A header:   regression / rectangular                     ← checks.json 头部
PROBE-A frozen:   {"capability_profile": "rectangular",
                   "legacy_defaulted": false,
                   "source": "structured_config", ...}
```

- 根因：`src/agent/execution/run_config.py:194-203` `_parse_capability_profile` 对
  present-but-invalid 值仍是 **warn + return None**（R1-2 只把 `_parse_run_profile` 改成 raise）；
  `scripts/tool_scripts/run_stage.py:1623` 的 `cfg_cap or cli_cap or _CAPABILITY_PROFILE_CLI_DEFAULT`
  于是回落到 `rectangular`。
- **为什么这不是「无所谓的另一个字段」**：批 B 的立项事实原文就是
  *「`run_config.yaml` 声明 `regression` + `orthogonal_polygon`，实际落盘 `checks.json` 头部却是
  `exploratory` + `rectangular`」* —— r1 关上了 `exploratory` 那一半，**`rectangular` 这一半仍然开着**。
  且 `capability_profile` 不只是头部字符串：`src/agent/correction/parse.py:36` 用它选
  CorrectedGeometry 的 v2/v3 schema ⇒ 一个拼写错误会让整条 correction 走另一套几何契约。
- **比 r0 更糟的一点**：R1-1 让 capability 也走 config-authoritative，R1-1 的冻结又把结果写成
  `source="structured_config"` / `legacy_defaulted=false` ⇒ **冻结记录正面声称「这个 rectangular 是结构化声明来的」**，
  事后审计分不出它其实是个拼写错误造成的降档。
- **⚖️ 施工席已披露**：执行日志 §6.5 末尾「登记同族债……若 orchestrator 要求对称，r1 后续可扩到 capability」。
  **形态正确（没有自行降级为假设）**，但**债没还，路还通着**。
- **出口**：`_parse_capability_profile` 与 `_parse_run_profile` 对称化（present-but-invalid ⇒ raise）；
  锁走真实 `cmd_flow`、断言 `pytest.raises` + 冻结件不落盘（照抄 R1-2 那两条的形状即可）。

**同族扫描的其余结果（均未再命中）**：`cmd_run` / `cmd_flow` / `cmd_resample` / `cmd_provision` 四个建 attempt/冻结的入口
**全部**走 `_resolve_run_profiles` + `_run_policy_context`（`run_stage.py:1932/2005/2127/2370`）；
`cmd_judge`(`:2046`) / `cmd_run`(`:1946`) / `cmd_flow`(`:2143`) 走 `_policy_with_frozen_tier`；
全仓 `RunPolicy(` 的构造点只剩 `step_orchestrator.py:358/378`（内部 helper 的 `policy or RunPolicy()` 兜底）
与 `validation_run.py:89`（同型），**均为「调用方没传就用默认」的形状，且 R1-5 已把两个人工几何调用方改成传冻结件**
（R1-5 属路 1，我不判其质量，只登记它确实覆盖了这两处）。

### G-3 R1-2 的 fail-closed 没打死历史 replay、没给非法值留后门 —— **成立**

- **非法**：`_parse_run_profile` raise，且 `load_run_config` 的 `try/except` 只包 `yaml.safe_load`
  （`run_config.py:148-156`），`_parse_run_config` 在其**之外**调用 ⇒ **raise 不会被吞**。
  探针 B（真实 `cmd_flow` + `regresion`）⇒ `ValueError: run_profile_invalid`，
  且锁另断言 `_run/run_policy.json` 与 `run_manifest.json` **均未落盘**。
- **缺失**：absent 仍返回 `None` ⇒ CLI 权威（对照锁 `test_R1_2_absent_run_profile_still_cli_authoritative` 绿，
  neuter N4 下**保持绿** ⇒ 该对照锁不空转）。
- **历史 replay**：`resolve_frozen_run_policy` 走的是 `_declared_policy`
  （`run_policy_freeze.py:160-183`，自己读 YAML、对非法值容忍为 `None`），**不经 `_parse_run_profile`**
  ⇒ 老 run 不会被新 raise 打死。
- **能不能冒充 regression**：不能。无冻结件 ⇒ 合成记录 `source="legacy_defaulted"` + `legacy_defaulted=True`
  （`:255-262`）；盘上已有 legacy 记录时 `provision_run_policy` **拒绝原地覆盖**（`:217-222`）。
- ⚠️ **我尝试的证伪（失败但值得记）**：先按 config 冻结 regression，再把 config 改成 `regresion`
  ⇒ `_declared_policy` 返回 `None` ⇒ 漂移复验**不触发**。这正是 sol 那条**从未被 r1 派工单裁定**的
  候选 MAJOR #3（「L-12 只挡另一个合法值」）。**方向是 fail-safe 的**（冻结件权威、档位不降），
  故我判 **NIT（F-7b）**，不判 MAJOR —— 但它至今**没有被任何一方正式裁过**。

### G-4 四态一路保留到 `checks.json`、没有任何一层折回 bool —— **成立（我证伪失败）**

**要求的证伪形式我照做了**：构造同一个 sm24 同构 case，A = 五图全 `declared_false`，
B = `1f_view` **从声明里删掉**（⇒ wire 上是 `unknown`）、其余 `declared_false`，
走**完整 `check_reading_stage`**（不是 `check_reading_view` 单元），逐行比对
`(status, message, evidence)`：

```
G4 rows compared: 19
G4 differing rows: 1f_view.{dimension_chain_closure, dimension_derived_refs,
                   dimension_p1a_fields, dimensions_present, raw_field_presence,
                   stroke_provenance_coverage}
  dimensions_present   declared_false: "view is declared not dimensioned"
                       unknown       : "view dimensioned applicability is unknown (not declared)"
G4 control South_view identical: True
```

⇒ **19 行里 6 行不同**（2 行 message 不同、4 行 evidence 里的 `dimensioned_state` 不同），
对照 view 逐字相同。`src/validator/checks/reading.py:204` 那个
`meta["dimensioned"] = dimensioned_state == "declared_true"` 确实是个 bool，
**但它只是派生便利值**：每一行 evidence 都经 `_evidence_meta`（`:212`）带上原始四态，
`:739/743/759` 消费该 bool 的三处 chain-closure 逻辑，其 evidence 同样带四态 ⇒ 不构成折叠。

**关于 `pipeline.py` 为什么被改（审阅单点名）**：`6d38f0c` 只在
`src/agent/pipeline.py:574,895` 两处把 `dimensioned_view_names_from_testdata_text(...)`
换成 `dimensioned_states_from_data(parse_testdata_text(...))` 并删掉随之无用的 import ——
**是 R1-3 新参数的必要接线（否则「谁真的传它」又会落空），未超范围。**

**⚠️ 但有一条残留（F-4 MINOR）**：R1-3 修的那个**离线审计面根本表达不出 `unknown`**。探针 G5：

```
MANIFEST wire  : {'1f_view': 'unknown', 'East_view': 'declared_false', ...}
OFFLINE states : {'South_view': 'declared_false', ...}          ← 1f_view 缺项
1f_view -> wire='unknown'  offline=None  ⇒ 调用方补 'legacy_default'
```

`case_metadata.py:dimensioned_states_from_data` 只产 `declared_true` / `declared_false`，
缺项由 `validation_run.py:146` / `evidence_preflight.py:235` 的 `.get(stem,"legacy_default")` 补齐
⇒ **同一份输入，gate① 上是「问了但没答」，离线审计面上是「从来没问过」。**
裁定追加约束 #2 要分开的正是这两者。
（严重度只判 MINOR：strict 档 provisioning 对 `unknown` fail-closed，所以严格 run 到不了这里；
exploratory 档 `validate_case` 本就是 advisory。）

### G-5 J-1 的处置真的落地了 —— **成立，但来源标签失真（F-5 MINOR）**

- **裁定怎么判的**：J-1 采纳 (b)「保持 hash 收窄 + 把 `context` 真接上」，并要求
  「至少含 `validation_scope` / `require_ep` / `confirmation_policy` / `judge_enabled` 的**实际取值 + 来源**」
  + 一条锁断言「落盘且不进 hash」。
- **施工怎么落的**：`_run_policy_context`（`run_stage.py:1627-1660`）+ **四个入口全部传参**
  （`:1944 / :2009 / :2141 / :2375`）。**这不是 r0 那条「参数在、全仓零传参」的形状了。**
- **有没有消费者读它**：**有** —— `run_policy_freeze.py:285+` 的 `effective_run_policy` 从冻结 record 的
  `context` 重建 `RunPolicy`，被 `step_orchestrator.py:483/506`（人工几何确认门）与
  `record_baseline.py:499` 消费。⚠️ **如实登记：这个消费者是 `c56cbe1`（R1-5 / terra）加的，不在本单被审范围内**
  —— 也就是说**在 GLM 的六条里 `context` 仍是只写不读的**，是路 1 那条把它接上的。
  **合起来看 G-5 成立；单看被审的六条，它是「记录了、还没有人读」。**
- **不进 hash**：`_run_policy_hash` 只含 `(capability_profile, run_profile)`（`:53-57`），
  drift 只比 `policy_hash`（`:226`）。锁 `test_R1_1_context_not_in_hash_no_drift` 走真实
  `provision_run_policy`，**neuter B（把 context 塞进 drift 判据）恰好红它一条**。
- **⚠️ F-5**：`validation_scope` 与 `confirmation_policy` 是**写死的常量**
  （`{"value":"full","source":"default"}` / `{"value":"required","source":"sop"}`），不是「实际取值」；
  `judge_enabled.source` 在「`run_config.yaml` 存在但没有 `judge:` 键」时也报 `structured_config`
  ——探针 A 实测：配置里只有两行 profile，context 却记 `judge_mode:"stop", source:"structured_config"`
  （`stop` 是 `_parse_judge_mode` 的默认值，不是任何人声明的）。**值是对的、来源标签是假的。**

### G-6 J-2 的处置（混合列表）没有误伤合法输入 —— **成立**

- 实现三分（`view_manifest.py:751-760`）：全字符串 ⇒ legacy；全对象 ⇒ 结构化；**混合 ⇒ raise 并指名第一个非对象项**。
- **误伤面核实**：真实 sm24 = **无 `dimensioned_views` 键**（absent）；真实 sm21 = **纯茎字符串列表**
  —— 探针 P3 实测两者 wire 上 `dimensioned` 全是 `bool`
  （sm24 全 False、sm21 全 True），`content_sha256` 分别 `459513f1…` / 与 `SM21_MANIFEST_SHA` 一致
  ⇒ **两个真实 case 都进不了混合分支**。对照锁 `test_J2_pure_string_legacy_not_rejected` 在
  neuter N5 下**保持绿** ⇒ 不空转。
- raise 位置在 `build_view_manifest:971`，**早于任何 entry 构造与 `_atomic_write_text`**
  ⇒ 与 R1-4 同一个「失败不留产物」性质。

### G-7 边界合规 —— **成立（①有一条须由 orchestrator 认领）**

| # | 结论 | 证据 |
|---|---|---|
| ① 未 push | ⚠️ **HEAD == `origin/6.15_ValidationArchM0toM4`**（均为 `48e41b6`）。`.git/logs/refs/remotes/origin/…` 显示最后一次 push 是 `b8f9a8d → 48e41b6`，即**收工 ritual 那一整支推**（CLAUDE.md §5#12 的标准授权），**不是施工席在交付时推的**。仓库状态无法再细分到 commit 级，**请 orchestrator 认领这次 push**。 | `git rev-parse` + remote reflog |
| ② `gt/**` + sm24 `testdata_prompt.json` 零字节 | ✅ 七个 commit 的 `--name-only` 并集**零命中**；`git diff --stat 627efac..48e41b6 -- <两处>` 空 | 只读 git |
| ③ 未读 GT | ✅ 七个 commit 未触 `src/agent/judge/gt.py`；新增测试零 `gt/` 引用；fixture 全自造（`_structured_dim_decl` / `_plan_with_dims`） | `git show --name-only` + grep |
| ④ 未原地改历史 manifest/attempt/GT | ✅ 改动文件全在 `src/agent/execution` `src/agent/pipeline.py` `scripts/tool_scripts/run_stage.py` `src/agent/execution/run_config.py` + 两个测试文件 | 同上 |
| ⑤ 无「当前样例转绿」式验收 | ✅ 每条锁都有摘掉即红的钩子（§3） | neuter 台账 |
| ⑥ 未从产品 `dimensions[]` 反推 | ✅ `build_view_manifest` 的输入只有 `case_data/`，产品从不进 manifest；L-22 反向锁在 | §2 P-6 |
| ⑦ N/A 未一律计 miss | ✅ `_dimensioned_view_evidence` 保留 object-conditional N/A 且每条带机器可读 reason + `dimensioned_state` | `checks/reading.py:501-528` |
| ⑧ `stroke_dimension_consistency` 未升硬门 | ✅ **`src/validator/checks/reading.py` 被七个 commit 完全没碰**；该检查仍是 `CROSS_CHECK` + 自陈 advisory | `git show` 空输出 |
| ⑨ 未顺手做批 C/D/R1.5 | ✅ 无 `render_vector_to_png.py` / `session_kickoff.md` / OCR schema 改动 | 文件清单 |
| ⑩ 欠规格边界未自行降级 | ✅ **两次都停下上报**（J-1/J-2 先回报再动手；capability 对称性写成「登记同族债 + 请示」）。**这是本批最值得记的正面行为** | 执行日志 §6.3 / §6.5 |

---

## 2. P-3…P-6 / P-9 逐条（补完 sol 未跑完的部分）

### P-3 真实 sm24/sm21 manifest 的 `content_sha256` 逐字节不变 —— **成立（真跑，非读码）**

命令：`pytest -q -n0 tests/test_zz_claude_p3.py -s`（在 `/tmp` 克隆内）

```
P3 sm24 content_sha256      = 459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
P3 sm24 case_metadata_sha256= f2efff8614ce6ddce9f975e811435a4936720f37df72cda538e4cd0cf8656701
P3 gt content_sha256        = dd32135d81b0ea6eb34aaaec1675840cc46090b0b8eb99c7b140a7a4afd479f2
P3 typed_gt is None?        = False
P3 bindings loaded, n = 5
P3 validate_score_view_bindings[_against_gt] OK
P3 roundtrip content_sha256 = 459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
P3 sm24 dimensioned wire types: {'1f_view':'bool','East_view':'bool','North_view':'bool',
                                 'South_view':'bool','West_view':'bool'}
P3 sm21 dimensioned wire: 六图全 ('bool', True)
```

- **真实的 `load_score_view_bindings`** 拿签字侧车 `gt/sm24_anchor/score_inputs/view_bindings.json`
  + 由**当前代码现算**的 manifest 四元组做逐字相等校验 ⇒ **通过、未抛 `score_view_binding_invalid`**；
  随后 `validate_score_view_bindings` 与 `validate_score_view_bindings_against_gt` **也都通过**。
- **⛔ 全程未读 GT 答案数字**：只调 `load_score_gt_identity`（取 identity hash）与两个 contract validator，
  报告里不出现任何答案内容。
- **Pydantic v2 联合序列化往返**：`model_dump_json → model_validate_json` 后 `content_sha256` 逐字相同，
  且 `dimensioned` 在 JSON 上仍是 `bool`（不是被联合类型提升成对象）⇒ 分支保哈希设计成立。
- **有没有输入形态会让真实 case 落进对象分支**：只有 `dimensioned_views` 是**全 dict 的非空 list** 才进
  （`view_manifest.py:742-762`）；sm24 无该键、sm21 是纯字符串列表 ⇒ 不可能。
  J-2 之后混合列表还会直接 raise，比 r0 更窄。

### P-4 L-10 / L-11 真的证明了「disposition 按 profile 走」 —— **成立**

**我试图找「使两者事实行不逐字相同的合法输入」，找不到，而且我认为结构上找不到**：
`grep -n "run_profile" src/validator/checks/reading.py` **只有两处命中**（`:104` 函数签名、`:112` 转发给
`CheckReport(...)` 的 header），**所有检查体对 run_profile 完全无感**；
`check_view_manifest_coverage` 同理（`:118` 只进 header）。档位的唯一出口是
`CheckReport.dispositions()/blocking()`（`checks/schema.py:237-243`）。
⇒ **「事实由检查产生、档位只决定处置」在这一层是结构性成立的，不是靠 fixture 巧合。**

- `_facts_key`（`tests/…batchB.py:507-517`）比的是 `(check_id, status, evidence)` **含 status**，
  不是只比 check_id ⇒ 是真事实键。
- L-10 断言 `len(report.blocking()) == 4` **且四条都是 `…reading.dimension_chain_closure`**
  **且** attempt `not stage.accepted` —— 落在具体 check-id 上。
- **L-13**：⛔ **r1 一字未改**，仍是 `provision_run(case_dir, run_dir, run_profile=None, …)`
  直喂内部函数（`tests/…batchB.py:158`）。更要紧的是**这道门在生产上已经不可达**：
  `_resolve_run_profiles` 恒返回非 `None`（`run_stage.py:1622` 的 `or _RUN_PROFILE_CLI_DEFAULT`），
  而 `provision_run_policy` 的唯一生产上游就是它 ⇒ `run_profile_not_declared` 永远不会从 CLI 触发。
  见 **F-3 MINOR**。
- **L-12**：drift 复验在 `resolve_frozen_run_policy`，且 `provision_run_policy` 在
  `_manifest_for_attempts` 里、早于任何 attempt 创建 ⇒ 「创建 attempt 之前拒绝」成立。
  其**只挡另一个合法值**的缺口见 F-7b。

### P-5 L-21 的 fixture 与真 sm24 同构、锁没有空转 —— **成立**

`_sm24_activation_fixture`（`tests/…batchB.py:414-430`）**直接 `shutil.copytree(SM24, …)`**
⇒ 天然是 5 个 required view（1 plan + 4 elevation），不是「2 个 view / 只有 plan」那种证明不了接线的形状。
锁逐条对应裁定 §2.1：

- (a) 五个 stem **逐个** `dimensions_present` / `dimension_p1a_fields` 由 `NOT_APPLICABLE` → `PASS`（10 行）；
- (b) `others_leg == others_true` —— **其他 check-id 的 status 逐项相同**；
- (c) 四条 closure 在 `declared_true` 侧**仍 block**，并且额外断言 legacy 侧也 block
  ⇒ 「打开尺寸类检查不会顺手洗掉已有阻断」被双向钉住。

### P-6 产品内容不能决定考卷（L-22）—— **成立（我证伪失败）**

我找不到产品可控的输入能改变 `dimensioned` 或分母：`build_view_manifest(case_dir)` 的输入只有
`case_data/`（trusted metadata + 图像），**产品 payload 根本不是它的参数**；
`check_reading_stage` 的 `manifest_state` 完全来自 manifest wire
（`checks/view_manifest.py:71-75`），只有 manifest 缺失时才回落到 `dimensioned_stems`，
而后者在 `validate_case`/`evidence_preflight` 里也来自 case metadata。
L-22 本身另证「空 `dimensions[]` ⇒ `dimensions_present` **FAIL** 而不是 N/A」。

⚠️ **NIT（F-7a）**：L-22 的锁只走 `check_reading_view` 单元，**没有断言裁定文本里的
「manifest / applicability / 分母不变」**。机制成立，但这条锁比它的规格窄。

### P-9 复杂度可扩展性（不变量 #6）—— **成立，未烤死简化假设**

- `DimensionedApplicability` 是 **per-view 的 `{state, authority, source_hash}`**，
  挂在 `RequiredViewEntry` 上、按 `input_id` 索引 ⇒ 非方形 / 退台 / 挑空 / 中庭带来的是
  **更多 view（更多楼层平面、更多立面、剖面）**，只是同一结构的**条目增加**，不需要改 schema 形状。
- 四态 `declared_true|declared_false|unknown|legacy_default` 是**关于「这张图有没有尺寸标注」**的断言，
  与建筑体量正交 —— 没有把「共底面盒子 / 每层满铺 / 固定层高」写进任何字段。
- `run_policy` 的 `(capability_profile, run_profile)` 二元 hash **是可扩展的接缝**：
  `_CAPABILITY_PROFILES` 目前 `("rectangular","orthogonal_polygon")`，将来加档位只需扩元组，
  且 hash 覆盖面变化会自然触发 drift（老 run 因 legacy 分支只读，不会被打死）。
- **唯一要提的一句**：`context` 目前是自由 dict、无 schema、无版本号
  （`RunPolicyRecord.context: dict`）。将来若 `effective_run_policy` 越来越依赖它重建策略，
  这个无契约的 dict 会变成一条**没有版本化的隐式接口**。**只是判断，不给设计。**

---

## 3. 逐锁 neuter 台账

**方法**：`/tmp` 克隆内 11 次精确字符串替换（每次断言 pattern 在文件中**恰好出现一次**）→
跑 `tests/test_run_stage_flow.py + tests/test_reading_ruler_r1_batchB.py`（`-n 4`）→
`git checkout -- .` 恢复 → 下一条。驱动脚本 `scratchpad/neuter.py`，原始输出 `scratchpad/neuter.log`。
**BASELINE = 51 passed / 0 red；POST-RESTORE = 51 passed / 0 red；被审文件全部逐字节恢复。**

| # | 摘掉哪一处实现 | 恰好红了哪几条 | 连带 | 假锁 | **是否经真实 CLI 入口** |
|---|---|---|---|---|---|
| N1 | `run_stage.py:1622` config-wins 退回 CLI-only | `R1_1_flow_config_run_profile_overrides_cli_default`·`R1_1_flow_freezes_run_policy_not_legacy_defaulted`·`R1_1_flow_regression_freezes_to_reading_checks_header`·`R1_1_context_recorded_with_sources` | 4 条共享同一 resolution（预期） | 否 | ✅ `cmd_flow` |
| N2 | `_manifest_for_attempts` 的 `provision_run` → `provision_view_manifest` | 上述 4 条 + `R1_2_absent…`·`R1_7_same_value…` + **4 条既有 capability_profile 回归** | 共 10（冻结是全局承重件，预期） | 否 | ✅ `cmd_flow`/`cmd_run` |
| N3 | `_run_policy_context` 返回 `{}` | `R1_1_context_recorded_with_sources` | 零 | 否 | ✅ `cmd_flow` |
| N4 | `_parse_run_profile` raise → `return None` | `R1_2_flow_typo_run_profile_fails_closed` | 零（`R1_2_absent…` 保持绿 ⇒ 对照锁不空转） | 否 | ✅ `cmd_flow` |
| N5 | J-2 混合列表 raise 短路 | `J2_mixed_dimensioned_views_list_rejected`·`J2_mixed_list_error_names_offender` | 零（`J2_pure_string_legacy…` 保持绿） | 否 | `provision_run`（非 CLI，见注） |
| N6 | `case_metadata` 结构化对象分支短路 | `R1_3_dimensioned_states_from_data_preserves_structured`·`R1_3_validate_case_preserves_structured_declaration` | 端到端锁依赖解析（预期） | 否 | `validate_case` 离线面 |
| N7 | `evidence_preflight` 的 `dimensioned_state` 转发钉死 `legacy_default` | `R1_3_evidence_preflight_carries_declared_false` | 零 | 否 | 离线面 |
| N8 | `validation_run` 的同一转发钉死 | `R1_3_validate_case_preserves_structured_declaration` | 零 | 否 | 离线面 |
| N9 | `provision_run` 把校验移回写盘之后（= r0 顺序） | `R1_4_strict_applicability_refusal_leaves_no_artifact` | 零（L-20 三条保持绿 ⇒ R1-4 唯一绑「前置」） | 否 | `provision_run` |
| N10 | R1-6 的 image-hash 比对循环短路 | `R1_6_forged_image_hash_rejected` | 零（L-20_structured_complete + 保哈希守卫保持绿） | 否 | `build_view_manifest` |
| N11 | R1-7 的 run_profile 冲突 raise 短路 | `R1_7_config_cli_run_profile_conflict_raises` | 零（`R1_7_same_value…`·`R1_1a` 保持绿） | 否 | ✅ `cmd_flow` |

**结论：11 个钩子、11 条独立命中、零假锁。** 施工席执行日志 §6.4–§6.11 自报的 neuter 结果与我独立复跑**逐条吻合、零夸大**。

**⚠️ 关于「真实 CLI 入口」的两点保留**：
1. 入口是 `cmd_flow(SimpleNamespace(...))` —— **是 CLI 命令函数，但不是 `main()` 的 argparse**。
   我核实 `_args` 里 `run_profile="exploratory"` **与真实 argparse `default=` 一致**（`run_stage.py:2396`），
   缺失的 `capability_profile` 由 `_resolve_run_profiles` 的 `or _CAPABILITY_PROFILE_CLI_DEFAULT` 补成
   `"rectangular"`，**与真实 argparse `default="rectangular"`（`:2402`）行为等价** ⇒ 不构成 r0 L-13 那类偏差。
   但这条等价性**只由一行注释维系、无锁**（F-6）。
2. N5–N10 走的是 `provision_run` / `build_view_manifest` 等内部函数 —— 派工单 §3.1 只要求
   R1-1 / R1-2 / R1-7 走 CLI，**这三条确实走了**，其余不违令。

---

## 4. 清单外自主发现

### F-2（MAJOR）冻结记录的 `source` 是硬编码常量，不是来源

`src/agent/execution/run_policy_freeze.py:210` —— `provision_run_policy` 无条件传
`source="structured_config"`；`_build_record` 的另一个调用点（`:257`）是 legacy 合成路径。
⇒ **`source` 只区分「盘上有没有冻结件」，从不区分「这个档位是 config 声明的还是 CLI 兜底的」。**

- 用 `flow --run-profile regression` 且**根本没有 `run_config.yaml` 声明**跑一个新 run
  ⇒ 冻结件写 `source="structured_config"`、`legacy_defaulted=false`、`checks.json` 头部
  `run_policy_source="structured_config"`。**没有任何结构化声明存在过。**
- 与 F-1 叠加后更糟：**拼错的 capability 降档也标 `structured_config`**（探针 A 实测）。
- **直接违反的规格**：批 B/C 派工单 §2.1 #4 逐字 ——
  *「`checks.json` 头部记录 effective profiles + policy hash + **source**（`structured_config` / `legacy_replay`），
  而不是像现在只记两个没有来源的字符串」*。现在它记的是**一个没有来源的字符串 + 一个恒为常量的来源**。
- **连带出一条空断言**：`tests/test_run_stage_flow.py` 的
  `assert record.source == "structured_config"`（R1-1b）在该路径上**恒真**
  —— 这正是审阅单 §4A G-1 要我找的「等于没断言」的形状。
  （该锁整体**不是**假锁：同一函数还断言 `run_profile=="regression"` 与 `not legacy_defaulted`，
  neuter N1/N2 都能把它打红。**只是 `source` 这一句是装饰。**）
- **二阶后果**：`resolve_frozen_run_policy` 的漂移复验只在 `_declared_policy` 返回非 `None` 时比对
  （`:272-283`）⇒ **纯 CLI 冻结的 run 永远不做漂移复验**，而它却被标成 `structured_config`。
- **出口**：`provision_run_policy` 增一个 `source` 入参（`structured_config` / `cli` / `mixed`），
  由 `_resolve_run_profiles` 判定后传入；锁断言「config 声明 ⇒ structured_config」与
  「无声明纯 CLI ⇒ cli」**两侧都断**（只断一侧会再退化成恒真）。

### F-3（MINOR）L-13 的 fail-closed 在生产上不可达，且锁一字未改

`run_policy_freeze.py:202-207` 的 `run_profile_not_declared` 需要 `run_profile is None`，
但两个生产上游 `_manifest_for_attempts`（`run_stage.py:169-175`）与 `cmd_provision`（`:2371-2376`）
拿到的都是 `_resolve_run_profiles` 的返回值，而它以 `or _RUN_PROFILE_CLI_DEFAULT` 收尾（`:1622`）
⇒ **永远非 None**。这道门只有 `tests/test_reading_ruler_r1_batchB.py:158` 那条**直喂 `None`** 的锁在走
—— **与 r0 被判「绕过真实 CLI」的形状完全一致，r1 未动它一个字符**。

派工单 §3.1 点名的是 R1-1/R1-2/R1-7，**所以这不算违令**；但审阅单要我「重点看 L-13 有没有真修」，
诚实的答案是：**没有修，只是被 R1-1 的 config-wins 规则挡在了前面。**
派工单 §2.1 #5 的「**缺失** ⇒ fail-closed」这一档，因此实际上是**由 CLI 默认值兜掉了，而不是被拒掉了**。
**出口**：要么明确裁定「CLI 默认值算合法声明来源」（那 L-13 应改成一条不可达性说明 + 删门），
要么让 `_resolve_run_profiles` 在「config 与 CLI 都没有显式给」时返回 `None` 让 L-13 真的开火。

### F-5（MINOR）`_run_policy_context` 两项写死常量 + 一处来源标签失真

见 §1 G-5。`run_stage.py:1652/1655` 把 `confirmation_policy` / `validation_scope` 写成常量；
`:1641-1646` 在 config 存在但无 `judge:` 键时把 parser 默认值标为 `structured_config`。
由于 R1-5 已让 `effective_run_policy` **消费**这个 context 去重建人工几何确认门的策略，
这些常量现在是**有后果的**，不再只是审计装饰。

### F-6（NIT）具名 CLI 默认常量与 argparse 之间零锁

`run_stage.py:1581-1582` 的两个常量与 `:2396/:2402` 的 argparse `default=` **只由注释绑定**；
`grep -rn "parse_args\|rs.main()" tests/*.py` ⇒ **零命中**（全仓没有任何测试走 argparse）。
改了 argparse 默认值，R1-7 的「算作未传」判据会静默错分类，而所有锁照绿。

### F-7（NIT）两处「锁比规格窄」

- **(a)** L-22 只走 `check_reading_view` 单元，未断言裁定要求的「manifest / 分母不变」（§2 P-6）。
- **(b)** L-11 的「事实行逐字相同」按 check_id **排除了 `reading.isolation_provenance_bound` 一行**
  （`_facts_key`，有文档理由：per-merge staging 哈希）。理由成立，但「逐字相同」实为「逐字相同减一行」。
  另：sol 的候选 MAJOR #3（L-12 只挡另一个合法值、删声明/改非法值不触发漂移）
  **在 r1 派工单里没有被裁定过，r1 也没处理**；我核实其方向是 fail-safe（冻结件权威、档位不降），
  故只登记为观察 —— **但它需要一次正式裁定，而不是继续悬着**。

---

## 5. 我证伪失败的尝试（反向坐实）

| 尝试 | 结果 |
|---|---|
| 构造 `unknown` 与 `declared_false` 在**完整 `check_reading_stage`** 上逐字节相同的下游表示 | **失败** —— 19 行里 6 行不同，2 行 message 明确区分，4 行 evidence 带四态（§1 G-4） |
| 找一条产品可控的输入改变 `dimensioned` 或分母 | **失败** —— 产品 payload 结构上不是 `build_view_manifest` 的参数（§2 P-6） |
| 找一条使 L-10 / L-11 事实行不逐字相同的合法输入 | **失败，且我认为结构上不存在** —— `run_profile` 在所有 reading 检查体内零消费，只进 header + `dispositions()`（§2 P-4） |
| 让 R1-2 的 raise 被 `load_run_config` 的 `try/except` 吞掉 | **失败** —— `try` 只包 `yaml.safe_load`，`_parse_run_config` 在其之外（`run_config.py:148-156`） |
| 让 J-2 的新 raise 误伤真实 sm24 / sm21 | **失败** —— 两者分别是 absent 与纯字符串列表，进不了混合分支；`content_sha256` 实测未变 |
| 让签字 GT 侧车在 r1 之后拒绝出分 | **失败** —— 真实 `load_score_view_bindings` + 两个 validator 全过（§2 P-3） |
| 找一条「删除声明 / 改成非法值」使冻结的严格档被降档 | **失败**（方向是 fail-safe：冻结件权威）—— 但漂移门确实只挡「另一个合法值」，登记为 F-7b |
| 找第二处「一个字段认 config、另一个不认」的不对称 | **半失败**：来源规则本身已对称（这是 R1-1 的核心修复），**但非法值处置不对称** ⇒ 变成 F-1 |

---

## 6. 独立全量测试

主工作树、独立执行（未继承施工席或 orchestrator 的任何环境）：

```
$ python -m pytest -q -n 4
...
2089 passed, 10 xfailed, 165 warnings in 484.98s (0:08:04)
```

- **与 orchestrator 轻门基线（2089 passed + 10 xfailed 零红）逐数字一致。**
- 遵纪律：`-n 4`（未用 `-n auto`）、**全程无 `-m` 过滤**。
- neuter 全部在 `/tmp` 克隆内进行；主工作树唯一写入 = 本报告。

---

## 7. 给施工方的 review ask（按修复成本排序）

1. **[MAJOR F-1]** `_parse_capability_profile` 与 `_parse_run_profile` 对称化：present-but-invalid ⇒ raise。
   锁走真实 `cmd_flow`，断言 `pytest.raises` **且** `_run/run_policy.json` 与 `view_manifest.json` 均不落盘
   （照抄 R1-2 那对锁的形状），另补一条「合法 `orthogonal_polygon` 仍正常冻结」的对照锁。
2. **[MAJOR F-2]** `provision_run_policy` 增 `source` 入参并由 `_resolve_run_profiles` 判定；
   锁**两侧都断**（config 声明 ⇒ `structured_config`；无声明纯 CLI ⇒ `cli`），
   顺手把 R1-1b 里那句恒真的 `assert record.source == "structured_config"` 改成有区分力的断言。
3. **[MINOR F-3]** 就「CLI 默认值算不算合法的档位声明来源」出一次裁定；按裁定要么让 L-13 真的可达，
   要么删门并说明不可达理由。**不要让一道够不着的门继续挂着一条直喂 `None` 的锁。**
4. **[MINOR F-4]** `dimensioned_states_from_data` 支持第四态：结构化声明存在但某 required view 缺项 ⇒
   该 stem 显式记 `unknown`（而不是让调用方补 `legacy_default`），使离线审计面与 gate① wire 口径一致。
5. **[MINOR F-5]** `_run_policy_context` 的 `validation_scope` / `confirmation_policy` 改为读实际取值；
   `judge_enabled.source` 只在 YAML 里**真有** `judge:` 键时才标 `structured_config`。
6. **[NIT F-6]** 加一条锁把 `_RUN_PROFILE_CLI_DEFAULT` / `_CAPABILITY_PROFILE_CLI_DEFAULT`
   与 `main()` 的 argparse `default=` 机械绑定（可用 argparse 的 `get_default()`）。
7. **[NIT F-7]** L-22 补 manifest/分母不变的断言；对 sol 候选 MAJOR #3（漂移门只挡合法值）出一次正式裁定。

**⚠️ orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑 neuter，是唯一权威门；本报告不是终裁。**
