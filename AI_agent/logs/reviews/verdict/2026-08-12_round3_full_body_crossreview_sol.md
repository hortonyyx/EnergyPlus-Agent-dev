# 第三轮跨家族主体全量复审裁决 — sol

- 日期：2026-08-12
- 审阅席：GPT 侧交叉审（sol）
- 审阅范围：`a17ed0f` + `552f5942d8d6`（本轮 HEAD）
- 总判定：**CHANGES REQUIRED**
- 主体审阅状态：**五项均已完成实审；本轮未因外围前提错误停单**
- 未关闭计数：**1 BLOCKER / 6 MAJOR / 5 MINOR / 1 NIT**
- 落库意见：**不能把这两笔提交签为主体复审通过。** `BLOCKER-1` 必须先闭合；MAJOR-1/2、B2/B3 是 S3/S4 的硬前置，C1 必须纠正观测语义，F-24 必须在首次产生可复用 schema-10 cache 前闭合。

## 1. 结论先行

机械绿门属实：我独立复现了请求书给出的 `2557 passed / 10 xfailed / 0 failed`，全量 rc=0。但绿门没有覆盖我实际复现出的 hostile 路径。

五项主体的结论是：

1. **F-22 印章写入机制修对了，但印章方案本身没有形成可信 provenance，原 `BLOCKER-1` 仍未关闭。** 核确实无条件覆盖写 `version=1`；然而 scorer 把产品自己携带的同名字段当证明，writer replay 又没有把 replay core geometry 与候选 geometry 对等绑定。我把一个 `[0,4]²` producer 重签成 `[0.12,3.88]²` 的自洽候选，保留印章并重算 feature/host/evidence，真实 `StageRunner.record` 仍接受并持久化了伪造几何。
2. **F-9 S2 的两条指定生产入口接线为真，上一轮 `MAJOR-B1` 点名的条件 2/3/4 已按行为补上；但完整 S2 仍不能签收。** condition 5 实际未实现却被声明为 evaluated；coverage 又来自手写常量而不是执行结果。另有 `not_declared` z 的错误归因与 `validate_case` 的第三入口未接线。
3. **标注法观测的纯观察接线和四个机器状态均存在，但“按外包标注”的核心语义不成立。** 实现把整个 `(0.01, 0.30] m` 区间都命名为 `outer_skin_annotation`，没有读取墙厚，也没有验证“约半墙厚”；`0.02`、`0.12`、`0.29` 三者被同样解释。该摊的目的就是让人看到正确解释，因此裁 `MAJOR-C1`。
4. **F-23 从 ambient git 状态改成运行时副作用检查的定性与方向成立；实现仍不等于测试名所称的 byte-for-byte。** 同尺寸内容改写后恢复 `mtime_ns`，内容 SHA 改变而 metadata fingerprint 完全不变，裁 `MINOR-D1`。
5. 上一轮 7 条中：**MAJOR-1、MAJOR-2 仍开；MAJOR-3、MINOR-1、MINOR-2、NIT-1 关闭；MINOR-3 保留为有明确 cutover 截止点的 compatibility debt。**

## 2. 测试、探针与纪律

### 2.1 绿色基线

| 项目 | 结果 | 日志 / rc |
|---|---|---|
| 全仓 `pytest -q -n auto` | `2557 passed, 10 xfailed, 211 warnings in 420.22s` | `/tmp/sol_round3_fullsuite_20260812_T7mfCe.log` · `.rc`=`0` |
| 本轮定向集合（F-22、F-9 S0/S1/S2、annotation、F-23、judge）`-n0` | `251 passed, 2 warnings in 39.38s` | `/tmp/sol_round3_targeted_20260812_tp3kYo.log` · `.rc`=`0` |
| `compileall -q src scripts tests` | rc=0 | `/tmp/sol_round3_compileall_20260812_xDOrnI.log` · `.rc` |
| `git diff --check a17ed0f^ HEAD` | 0 行输出，rc=0 | `/tmp/sol_round3_diffcheck_20260812_VGESlr.log` · `.rc` |

### 2.2 `/tmp` 反事实锁

| 变异 | 实际结果 | 裁定用途 |
|---|---|---|
| 把 v3 印章恢复成“只有发生 correction/conflict/unsupported 才盖” | 两把零位移锁 **2 failed** | 证明当前无条件写入是承重实现，不是装饰 |
| `_is_unique_nearest` 恒 `True` | **8 failed / 55 passed** | 语义锁能抓到该错误；不支持请求书所述“18 红”精确数字 |
| 直接省略两处 unique-nearest 判定、coverage 常量不动 | condition-2 语义锁红；两条 coverage/report 锁仍绿，即 **1 failed / 2 passed** | 直接坐实 coverage 声明不由行为推导 |
| 恢复 annotation 的旧“从 intents 推状态”口径 | axis、exceeds、no-evidence 三格红，**3 failed / 1 passed** | 证明当前 observer 接线和前三格可观测性承重 |

对应日志：

```text
/tmp/sol_round3_conditional_stamp_mutant_20260812_5PiGKq.log
/tmp/sol_round3_unique_true_mutant_20260812_6Ra5ET.log
/tmp/sol_round3_unique_omitted_mutant_20260812_Y3KNUU.log
/tmp/sol_round3_annotation_old_semantics_mutant_20260812_MQJthb.log
```

所有源码变异都只发生在 `/tmp` 隔离副本；工作区没有 neuter 残留。我没有对工作区执行 `checkout`、`stash`、`clean`、`commit`、`reset`、`add` 等 git 写操作。F-23 的仓内测试本身会在 pytest 的 `tmp_path` 下创建隔离 git 仓并提交自证夹具；它没有触碰本工作区 git 状态。

### 2.3 关键行为探针

```text
/tmp/sol_round3_writer_forge_20260812_JaikP2.log        rc=0
/tmp/sol_round3_contract_probes_20260812_eiFwLk.log     rc=0
/tmp/sol_round3_s2_behavior_probes_20260812_rx5YRj.log  rc=0
/tmp/sol_round3_annotation_report_probe_20260812_k6oE60.log rc=0
```

这些探针均先输出目标存在的 premise，再输出 mutation 后结果；没有用“零输出”推断目标不存在。

## 3. §1 五项主体逐项裁定

### 3.1 主体 1 — F-22 `BLOCKER-1` 无条件印章 + 判卷验印

#### 成立的部分

- `src/agent/correction/deterministic.py:85,1117-1118`：v3 正常完成路径在唯一 return 前无条件覆盖写 `DeterministicCoreStampV1(version="1")`；传入的伪值也会被覆盖。
- schema 将 v3 stamp 建模为严格对象；缺失、显式 `None`、未知版本均不会取得 trust，畸形对象在 parse 层直接报 schema 错。
- `src/agent/judge/correction_score.py:140-183` 的 trust 判据实际读取 live core version，而不是仅有注释。
- 两份真实历史产物均无 stamp：F-17 翻转前 `[0.12,14.88]×[0.12,7.88]` 与翻转后、盖章前的 continuous e2e 都被拒判。这个用户已接受的历史代价真实发生。
- 条件盖章 mutant 使两把零位移锁转红，说明“没有改动也必须盖章”已锁住。

#### `BLOCKER-1` 仍开的原因：字段是自报，不是 provenance

公共 scorer 探针在同一份 F-17 翻转前真实产物上只增加：

```json
"deterministic_core_stamp": {"version": "1"}
```

结果从 `trusted=False` 变成 `trusted=True`，两层 boundary 都变成 `4/4`。这不是“核跑过”的证明，只是“对象声称核跑过”。现有 `test_neuter_restoring_stamp_flips_judge_back_to_accept` 事实上把这种行为写成了正向预期。

更关键的是，accepted writer 边界同样可绕：

```text
producer_bounds [0.0, 4.0] [0.0, 4.0]
forged_bounds   [0.12, 3.88] [0.12, 3.88]
outputs_differ  True
stamp           {'version': '1'}
writer_accepted True [0.12, 3.88] [0.12, 3.88]
```

探针使用 production-builder-backed 的零窗 B5 fixture，改变 footprint、floor ring、cell range/polygon，并重新物化 Vg、重算 feature claims、host claims、candidate identity 与 evidence。`src/agent/execution/stage_runner.py:309-383` 确实从 embedded producer 重跑 core，但只拿 replayed windows 去核 audit/host；它从未比较 replayed footprint/floors/cells 与 `fresh_geom`。因此一个与 replay core 输出不同、却内部自洽的候选可以进入 accepted chain。

这条反例同时回答了“印章方案工程正确性”和“hash/批准链影响”：**当前印章不能证明这份 accepted artifact 是该版本 core 的产物。** 原 BLOCKER 不得关闭。

#### 修法方向

最低要求不是再加一个可由产品填写的 bool/version：

1. writer 从 embedded raw/manifest/readings 重放后，必须对 **core-owned projection** 做 canonical equality/hash equality。至少覆盖 footprint、每层 ring/cells、core 后 window span/floor、corrections/conflicts/unsupported 与 stamp；若后续 host/finalize 会合法改 window 字段，应先定义并比较不含这些 final-owned 字段的 `DeterministicCoreOutputV1`，或在 writer 里重放完整 finalize 后逐字节比较最终产物。
2. 将验证结果绑定到 accepted manifest/sidecar，例如 `deterministic_core_proof={core_version,input_hash,core_projection_hash}`；proof 由 writer 在重放成功后签发，不能由 candidate 自己提供。
3. scorer 只有在得到 accepted manifest + 已验证 proof 时才能把 convention 标为 `trusted`。裸 dict 上的内嵌 stamp 最多叫 `declared`，不能叫 `trusted`；没有外部 proof 时 boundary/wall extent 应保持 unavailable。
4. 新增一把真实 `StageRunner.record` 锁：像上述探针那样构造“内部自洽但与 producer replay 不同”的候选，必须在 accepted pointer 移动前稳定失败。

#### 新的下游 `MINOR-A1`：拒判中的 `boundary_complete` 仍单项显示 PASS

无 stamp 的真实产物整体没有伪装成全对：`walls_complete=severe` 且 `score_evidence_completeness=severe`。但 `src/agent/judge/score_policy.py:249-303` 把 `boundary=None` 计成 `0/0`，再由 `missed_boundary==0` 给：

```text
boundary_complete = pass
boundary_hits=0/0; missed=0; no_data_floors=2
```

所以 fail closed 的总体出口存在，但 boundary criterion 自身仍说反话。裁 **MINOR-A1**，不是第二个 BLOCKER：全局 completeness severe 已防住整体全绿。修法是 `no_data_boundary_floors > 0` 时让 `boundary_complete` 明确 severe/unavailable；不能靠另一条 criterion 替它纠正含义。

### 3.2 主体 2 — F-9 S2 首版 + `MAJOR-B1` 补齐

#### 接线与已补条件

按行为而非形状裁定：

- stepwise `_draw_correction` 与 integrated `run_pipeline_artifacts` 两条设计点名入口都出现唯一 `correction.window_position_evidence_shadow` 行；clean 真实产物为 15/15 accepted，F-9 错引产物按窗拒绝。
- shadow 始终处于 `CROSS_CHECK` / FLAG，不覆盖 model-authored `span`，没有改变现行接受结果。
- authoritative current-ring frame、scope-before-ranking、endpoint tolerance、mutual-nearest、ambiguity epsilon 与 draw-level source reuse 都有独立行为锁。
- 上一轮 `MAJOR-B1` 精确点名的条件 2/3/4 已实现并承重，因此 **`MAJOR-B1` 按其原定义关闭**。

但“完整 S2 六条件均已验”不成立：

| §5.3 条件 | 本轮裁定 |
|---|---|
| 1 distance within tolerance | 已实现 |
| 2 unique mutual nearest | 已实现；恒 True mutant 有语义锁转红 |
| 3 ambiguity margin | 已实现；near-tie 锁承重 |
| 4 source not reused | 已实现；draw-level second pass |
| 5 claim consistency | **未实现，却被声明 evaluated** |
| 6 scope resolution | 主路径有实现；`not_declared` 的稳定码/归因错误 |

#### `MAJOR-B3` — condition 5 没有执行

`src/agent/correction/window_position.py:1038-1059` 的 `_window_existence_sources` 只读取 `claim == "existence"`。注释把 condition 5 说成 facade-family filter 的“side effect”，但 family filter只判断候选平面是否落在某个同 family Vg segment 上，既不读取 `along`/`host` links，也不能证明三类 claim 指向同一 plan authority。

我在 clean 真实产物上把 `W1_N1` 的 authenticated `along` 与 `host` 从 `1f_view/S11` 改成另一扇窗的 `S12`，保留 existence 的 `S11 + North/S7`。public builder 接受并生成的 links 是：

```text
existence -> S7, S11
host      -> S12
along     -> S12
```

shadow 仍给该窗 `accepted`、全局 `all_accepted=True`，同时报告 `claim_consistency` 已 evaluated、`unevaluated_conditions=()`。裁 **MAJOR-B3**。修复必须逐窗验证：existence 恰一 plan、along 恰一 plan、host 恰一 plan，三者为同一 authenticated locator；plan `floor_ref`、plane/family/segment 还必须与 window floor/facade/host claim 一致，并分别留下 condition-5 evidence。

#### `MINOR-B4` — z 缺失的 fail-closed 方向正确，错误码/归因错误

施工席点名的行为收紧应保留：没有 z/datum 的 evidence 不得因省略字段绕过条件 2/3，必须 reject。但当前 `not_declared` 没有在 source-scope 处早退，而是等候选域变空后落到：

```text
decision=rejected
reject_code=position_evidence_pair_mismatch
category=model_draw_error
```

设计 §7.3/§9 要求 datum 未声明为 `projection_datum_unresolved`（或具体 scope 缺失时 `projection_scope_unresolved`），类别是 `upstream_evidence_block`。当前 S2 只观测，裁 **MINOR-B4**；若原样进入 S3，它会错误燃烧 correction 重抽预算，届时是 cutover blocker。

#### `MINOR-B5` — `validate_case` 的生产审计入口仍为 NOT_APPLICABLE

两条设计规定入口已接线，所以这不推翻上面的 wiring 裁定。但 `src/agent/execution/validation_run.py:341-352` 从 verified accepted B5 source 调 `check_correction` 时，没有传 `verified_window_inputs`。对 production-backed accepted bundle 真实调用 `validate_case`，唯一 shadow 行为：

```text
not_applicable — no v3 verified_window_inputs supplied — shadow evidence did not run
```

这会让 integrated run 当场有 S2 fact，离线复核同一 accepted artifact 却没有。裁 **MINOR-B5**。accepted loader/proof 应暴露经重验的 resolver marker，`_CorrectionSource` 携带并传给 `check_correction`。

### 3.3 主体 3 — 标注法观测量（纯观测）

#### 接线成立

- observer 在 intents 生成前、直接比较 per-side bbox 与 accepted overall envelope；总是产生四条 side observation。
- `wing_break_endpoint` 不进入这四个数：实现只读 `envelope.axis(axis)`，不读 endpoint resolutions。
- 结果从 transaction 进入 `FinalizeResult`、writer 的 `annotation_basis.json`，再由 `record_baseline` helper 渲染为正常报告中的标题、汇总行与解释规则。
- production-backed writer 探针得到 4 条 `no_authoritative_evidence`、sidecar 存在，human renderer 输出 6 行。
- observer 是纯观察：不进入 geometry 本体，也不改变 committed/geom/transaction/audit。旧语义 mutant 使 axis、exceeds、no-evidence 三格转红。

#### `MAJOR-C1` — `outer_skin_annotation` 分档没有“约半墙厚”判据

`src/agent/correction/envelope_transform.py:163-172` 的实际分支只有：

```text
delta <= 0.01       -> axis_line_annotation
delta <= 0.30       -> outer_skin_annotation
delta >  0.30       -> exceeds_tolerance
```

探针结果：

```text
0.020 -> outer_skin_annotation
0.120 -> outer_skin_annotation
0.290 -> outer_skin_annotation
0.301 -> exceeds_tolerance
```

函数没有 wall-thickness 输入，也没有 half-thickness reference/band。因此报告中“按外包标注”的解释对绝大部分中间区间都无证据，违反施工单“位移 ≈ 半墙厚量级且 <= tolerance”语义。由于本摊唯一产品价值就是解释可见性，即使它不阻断，也裁 **MAJOR-C1**。

可接受修法有两种：

1. 若当前拿不到可信墙厚，把中间态改成中性名称（例如 `reconcilable_nonzero_displacement` / “非零且容差内，需人工判读”），只报告数字，不声称标注法；或
2. 给 observer 传入可信、版本化的 wall-thickness fact，冻结“接近 half thickness”的显式 band/epsilon；只有命中才叫 outer-skin，其余中间值另设 `other_requires_review`。

不能继续用整个 reconcile tolerance 充当“约半墙厚”。

### 3.4 主体 4 — F-23

#### 定性与修法方向成立

独立 `git log -S` 只找到原始引入 `6b08ac6` 与本次删除 `a17ed0f`；邻近派工/执行证据支持它原本是 Phase-D 一次性“本施工无 case_tests diff”纪律检查。将永久回归目标重新定义为“judge 路径运行期间不写 case_tests”是合理的，且新测试摆脱了开发者 ambient working tree/index 状态。

#### `MINOR-D1` — metadata fingerprint 不能证明 byte-for-byte

helper 明确只哈希 path + size + `mtime_ns`，测试名和 docstring 却声称 `byte_for_byte_unchanged`。隔离目录反例：

```text
bytes_changed=True
same_size=True
mtime_restored=True
metadata_fingerprint_changed=False
```

普通意外写通常会改 mtime，因此新锁比旧 git diff 明显更好；但 `copy2`、显式 `utime`、保元数据的原子替换等真实写法可漏掉。裁 **MINOR-D1**。若合同继续叫 byte-for-byte，就必须哈内容；可缩窄到真正受保护的 gt/golden/verified-overlay 集合后做 full SHA，或保留全树 metadata 快筛、再对受保护内容做 SHA。若只愿意守普通写入，应把测试名与注释降格为 metadata-change guard，不能继续声称字节不变。

### 3.5 主体 5 — 上一轮 7 条 finding

| Finding | 本轮裁定 | 行为/合同依据 |
|---|---|---|
| **MAJOR-1** resolver artifact / raw context 认证绑定不足 | **仍开，已有局部修复** | raw bytes hash 与 datum bytes hash 的两条直接错配已拦；但 replay 不从 raw bytes 重建 context。原 raw 实际 `z=0/height=3` 时，可提交绑定同一 raw hash、却写 `z=99/height=42` 的自哈希 context并通过。raw manifest/readings 也可换字节、重算外层 hash，而 opaque `resolver_hash` 不变。 |
| **MAJOR-2** decision preimage / accepted 语义过弱 | **仍开，已有局部修复** | 已加入 raw/resolver/context hash、canonical key，以及 accepted 的 elevation/distance/span 基本 invariant；但设计 §8.1 要求的 frame/scope hashes、`z_datum_mode`、source/window resolved scope、projected world-z、plan `floor_ref` 仍不可表达。缺少这些字段的 decision 仍可合法 `accepted`。 |
| **MAJOR-3** facade convention 未完整接线 | **关闭** | 六个真实 consumer 均有动态 monkeypatch/dataflow 锁；尤其原漏点 `derive_facade_frame` 会随 shared resolver 变异。此裁定基于行为，不基于 AST whitelist。 |
| **MINOR-1** 先 round 再比较 0.05 | **关闭** | `_match_lines` 现用 raw delta 判档、只 round 展示值；`0.054` 不再被扩成 complete。 |
| **MINOR-2** 测试标题强于判别力 | **关闭** | context 的 window mutation invariance、known-version hostile shape、S0 “new runs”误名等均已按真实能力改写/补锁。 |
| **MINOR-3** 两套 legacy mirror coercion | **仍开但可延期** | 行为保持选择合理；同一字符串在两个 legacy adapter 仍可能得到不同 bool。必须在 S3/S4 新 v3 live 边界改用 strict/versioned adapter，不能让匿名分叉进入新链。 |
| **NIT-1** 旧语义/旧版本文案 | **关闭** | 本轮搜索未再发现上一轮点名的反义 test id 与 stale v8/v9 说明；历史裁决文本不算生产文案。 |

#### MAJOR-1 修复最低口径

`WindowResolverInputsArtifactV2` 的 verifier/loader 必须解析内嵌 raw draw、manifest、reading 与 datum bytes，重新翻译 refs、重新计算 resolver facts，并从解析后的 raw floor geometry重建 `RawProjectionContextV1`，再与 persisted context 作 canonical byte/hash equality。不能只验证“context 声称的 raw hash等于旁边 bytes 的 hash”。每 floor/z-band datum/scope facts 也必须按设计进入 typed context。

#### MAJOR-2 修复最低口径

在 S3/S4 前把 §8.1 全部身份事实放入 decision preimage，并由 projector 生成、validator 交叉验证；不能用外层 evidence hash替代 decision 自身的 frame/scope/z/floor 绑定。

## 4. `MAJOR-B2` 专项裁级与修法

### 4.1 裁级：当前 MAJOR；S3 激活前是硬 BLOCKER

请求书的精确类比需要修正：把 `_is_unique_nearest` 改成恒 `True` 后，该函数仍然“被执行”了；任何 execution receipt 也只能证明调用发生，不能证明算法语义正确。因此“恒 True 但仍写 evaluated”本身不能单独推出 receipt 方案，更不能取代 mutation test。

而且我对该精确 mutant 跑整个 S2 文件，结果是 **8 红 / 55 绿**，不是 18 红。当前语义锁确实能发现它。

但 `MAJOR-B2` 的底层担忧仍然成立，且有两个更直接的行为反例：

1. 在 `/tmp` 源码副本中直接跳过两处 unique-nearest 条件，手写常量不动。condition-2 行为锁转红，但“真实报告 full coverage”和“check evidence 暴露 full coverage”两条测试继续绿；报告仍自称 evaluated。
2. 更强的现成反例就是 condition 5：生产代码根本不读 along/host claim consistency，报告却已经把它列在 evaluated。这不是未来假设，而是当前 artifact 的真实假声明。

所以裁 **MAJOR-B2**。当前 S2 是非阻断 shadow，错误报告还没有决定 acceptance，尚不升 BLOCKER；S3 若要消费这份 coverage 决定是否承重，B2/B3 未闭合就不得激活。

### 4.2 修法

1. 将“required rule ids”与“本次实际产生的 condition evaluations”分离。报告不得从 caller 传入 `CURRENTLY_EVALUATED_*` 常量。
2. 每扇窗产生结构化 `ConditionEvaluationV1`：`condition_id`、`outcome=pass|fail|not_evaluated`、输入/证据 hash 或最小 witness。condition 2 与 3 即使共享排序，也要有独立结果，不能用一个 bool 同时冒充两个判断。
3. condition 4 的 draw-level reuse pass 也产生 draw-level receipt；condition 5 必须先真正实现再产生 receipt。
4. report 从收集到的 receipts 派生 `evaluated_conditions/unevaluated_conditions`；缺任何 required condition 时 `all_accepted` 必须为 false/incomplete。
5. 保留两类不同的锁：
   - omission mutant：删掉执行点后，artifact 必须显示 `not_evaluated`/incomplete；
   - semantic mutant：helper 恒 True/改 epsilon/错 domain 后，结果 oracle 必须转红。receipt 不能替代这类锁。

## 5. §4 两条施工席点名项

### 5.1 facade family 候选域过滤

**批准当前 S2 架构判断。** 它读取已物化、逐 segment 的 Vg，不是 bbox 极值。clean 真实产物基线 `15/15`；将 `_plan_source_consistent_with_family` 恒 True 后只剩 `9/15`，六个对称误拒窗为：

```text
W1_N2 W1_N3 W1_S2 W1_S3 W2_E1 W2_W1
```

因此过滤真实承重，并且确实防止南北/东西对称 plan stroke 只按 along 形成假同分。

但施工席的未来警告同样成立：这个实现只能用于 **finalize 后已有 `geom.facade_segments` 的当前 S2**。S3/S4 若把 evidence gate 挪到 hydration/Vg 之前，必须从 authenticated raw projection context 构造等价的 per-floor/per-segment candidate domain，并把 plan plane、scope 与 segment identity 纳入 decision；不能偷用空 `facade_segments`，也不能退回 bbox family 极值。L/U 同 family 多 segment 的 seam 本轮仍无直接行为验证，列入未验证项。

### 5.2 z `not_declared` 收紧

**拒绝方向正确，现有 reject code/category 不正确。** 省略 z 不能成为跳过 scope/mutual-nearest 的通行证；应保持 fail closed。具体修正见 `MINOR-B4`：在排名前输出 typed datum/scope unresolved，归 upstream evidence，不要等空 domain 后误报 model pair mismatch。

## 6. 新债 F-24 / F-25

### `MAJOR-F24` — cache 缺的是“解释器期望身份”，不是 artifact 字段本身

先修正字面表述：如果同一 artifact 的 stamp 字段从缺失变成存在，`output_hash` 会变化，现有 key 已会 miss。因此缺口不是“内嵌 stamp 状态完全不在 key”。真正缺的是 **scorer 当前接受的 core stamp version / convention trust policy identity**：同一份 output bytes 在 `DETERMINISTIC_CORE_STAMP_VERSION` 从 `1` 变为下一版后，应从 trusted 变 untrusted，但 `_load_valid_score_sidecar` 仍直接复用旧 cache。

动态探针：先构造合法 schema-10 cache，再只改变 live expected stamp version；cache 前后完全相同，sidecar/key 中没有 expected stamp identity。这个结构性 fail-open 裁 **MAJOR-F24**。当前盘上没有 schema-10 sidecar，所以不是已发生的 stale incident；但必须在首次生成 schema-10 cache或再次改变 convention/core version前修。

修法：在 sidecar 与 cache predicate 中显式加入至少 `expected_deterministic_core_stamp_version`、output-convention/trust-policy version、scorer implementation identity；或定义一个由这些量 canonical hash 得到的 `scoring_semantics_sha256`。仅靠工程师记得手动 bump `SCORER_SCHEMA` 不足以绑定跨模块版本。

盘上核对：versioned sidecar 的分布确为 schema 9×20（top-level 14 + typed identity 6）、8×4、7×4、6×1，schema 10×0；另有 1 个更老的无 `scorer_schema` 文件。零 schema-10 这一“当前零影响”前提成立。

### `NIT-F25` — 两个同名常量不表达同一合同

`scripts/tool_scripts/run_stage.py:94` 的 `SCORER_SCHEMA="10"` 是 legacy attempt cache label；`src/agent/judge/score_schema.py:40` 的 `SCORER_SCHEMA="8"` 是 typed contract label。注释和 `test_legacy_scorer_schema_is_independent_of_typed_v8_contract_label` 已明确锁住独立性，没有运行时错配，**不升级**。

保留为 NIT：同名增加审计认知负担，后续可把前者改成 `LEGACY_SCORE_CACHE_SCHEMA`、后者统一使用已有 `SCORE_SIDECAR_SCHEMA`，但不要求本批为此改行为。

## 7. 未关闭 finding 总表

| 级别 | ID | 摘要 | 截止点 |
|---|---|---|---|
| BLOCKER | BLOCKER-1 | stamp 可自报；writer 接受 replay-divergent 几何 | 本批复审通过前 |
| MAJOR | MAJOR-1 | V2 raw/context/manifest/readings 未从 bytes 重建绑定 | S3/S4 前 |
| MAJOR | MAJOR-2 | decision preimage 缺 frame/scope/z/floor 身份 | S3/S4 前 |
| MAJOR | MAJOR-B2 | coverage declaration 不由实际 evaluation 派生 | S3 前 |
| MAJOR | MAJOR-B3 | condition 5 未执行却声明 evaluated | S3 前 |
| MAJOR | MAJOR-C1 | 中间全区间被无依据解释为“按外包标注” | 标注观测摊签收前 |
| MAJOR | MAJOR-F24 | cache 不绑定 expected core/convention trust identity | 首个 schema-10 cache / core version 变化前 |
| MINOR | MINOR-3 | legacy mirror coercion 分叉 | S3/S4 新 live v3 前 |
| MINOR | MINOR-A1 | boundary no-data 单项显示 PASS | 下轮判卷收口 |
| MINOR | MINOR-B4 | z datum 缺失误归 model pair mismatch | S3 前 |
| MINOR | MINOR-B5 | `validate_case` 不传 verified resolver inputs | S2 审计一致性收口 |
| MINOR | MINOR-D1 | metadata guard 不等于 byte-for-byte | F-23 收口 |
| NIT | NIT-F25 | 两个独立 schema 常量同名 | 顺手命名清理 |

## 8. 派工方前提错误 / 需收窄的表述

这些均是外围证据错误，不改变审阅范围，因此按新规记录后继续完成了主体：

1. **“工作树干净”字面不成立。** 我首次只读 `git status --short` 已有：

   ```text
   ?? AI_agent/logs/reviews/request/2026-08-12_round3_full_body_crossreview_sol.md
   ```

   即施工文件无 tracked diff，但请求书自身是 untracked。裁决书写入后自然又多一个用户要求的 untracked verdict。
2. **`_is_unique_nearest=True ⇒ 18 红` 未复现。** 对精确 mutant 跑整个 S2 文件得到 `8 failed, 55 passed`。这不改变“语义锁会红”，但不能继续引用 18 作为证据。
3. **F-24 的“cache key 不含印章状态”表述过宽。** artifact stamp 字节已经由 `output_hash` 间接绑定；真正未绑定的是 scorer 端 expected stamp version/trust policy。风险仍真实，范围裁定不变。
4. **sidecar 分布若被理解为“盘上所有 score 文件”则少算 1 个无版本老文件。** 29 个具名 version 值的 9/8/7/6 分布与请求书一致，另有一个 `scorer_schema` 缺失的 legacy sidecar；“没有 10”仍成立。

## 9. 未验证项

- 没有穷举除本次 forged ring/cell 外的所有 replay-divergent core-owned 字段；一个 accepted 反例已足以保持 BLOCKER，但不能据此声称已列全第 N 类路径。
- 没有实现或运行尚不存在的 S3 active routing、S4 raw→hydrate cutover；本裁决只给它们设前置条件。
- 没有独立跑 L/U 同 family 多 segment、退台 per-floor extent、void/z-band 的 complex-shape behavior fixture；当前 facade filter 只批准到已物化 Vg 的 S2 边界。
- annotation 的 reporter 通过 writer + `_annotation_basis_summary` + human renderer helper 实测；没有在一份真实 sm21/sm24 run 上成功跑完整 `record_baseline.py` CLI 重新生成整份报告。四态机制使用合成、生产类型夹具，writer/report exposure 使用 production-backed B5 夹具。
- F-23 只坐实了一个 metadata-preserving 内容变化反例，没有枚举各平台文件系统时间戳/原子替换行为。
- F-24 因盘上没有 schema-10 cache，使用了合成合法 sidecar 验证 cache hit；没有篡改任何真实 case artifact。
- 没有审阅 211 条 warning 是否含本批特有的新 warning；本轮目标与基线只要求 failed/xfail 对账。

## 10. 最终裁决

本轮成功标准“主体真的被审到”已满足，且五项均有行为证据。结论不是全盘否定：无条件盖章机制、S2 两入口、条件 2/3/4、annotation 纯观察链与 F-23 去 ambient-git 的方向都已成立。

但 **accepted artifact 仍能伪装成当前 deterministic core 产物**，这是单独足以阻止签收的 BLOCKER；同时 F-9 完整条件声明、annotation 核心解释和 cache semantics 还有实质缺口。因此总判定保持 **CHANGES REQUIRED**。
