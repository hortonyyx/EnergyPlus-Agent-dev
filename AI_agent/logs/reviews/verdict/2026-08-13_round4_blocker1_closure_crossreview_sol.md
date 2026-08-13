# 第四轮跨家族复审裁决 —— BLOCKER-1 闭合 + C1 + A′

- 日期：2026-08-13
- 审阅席：GPT 侧交叉审（sol）
- 审阅范围：`da2245d` 相对其父提交 `bddec5794b656560476ba5a957a23d9ec476d52f`
- 总判定：**CHANGES REQUIRED**
- 未关闭计数：**1 BLOCKER / 5 MAJOR / 4 MINOR / 1 NIT**
- 核心裁定：**`BLOCKER-1` 不能关闭。** writer-side replay/projection 修法在“候选产物不能自己伪造 proof”的窄威胁模型下成立；但当前所谓 proof 只是无签名 JSON，其唯一授权者是同一 run 目录内可重写的 manifest。按本项目已由用户拍板的 `decision_log.md §5.14` 两问判据，它不是合格的外部信任根。同一提交还存在一条独立的 cache 绕行：proof 删除后，已经缓存的 `trusted=True` 仍直接命中，scorer 不再验 proof。

## 1. 结论先行

本轮四组裁定如下：

1. **`BLOCKER-1` 仍开。** `StageRunner.record` 现在会重放 core、比较投影、签发 sidecar，裸产物印章也确实只能得到 `declared`；这些工程步骤不是装饰。但 accepted manifest 既不是 append-only ledger，也没有签名/MAC/外部锚。它与 proof 同属一个可写目录，proof 字节与 `artifact_hashes` 可一起改写，正是 §5.14 明确否定的“改记录的人把指纹一并重算”。此外，cache hit 发生在 proof 解析之前；我用真实 writer-backed accepted fixture 实测，删掉 proof 后 resolver 已返回 `None`，旧 cache 仍给 `trusted=True`。
2. **从未出现真实 run 的正向 `trusted=True` 不构成第二条代码 finding，但它是关闭出口，不是可延期观察项。** 负向门/夹具正向不能替代生产 happy path。即使信任根与 cache 缝补完，仍须在一条真实 orientation B5 链上观察 writer→manifest→proof resolver→judge→cache 首写/复读全程，才可无条件关闭 `BLOCKER-1`。
3. **`MAJOR-C1` 关闭。** 当前生产侧没有可信墙厚事实，又不能越过不变量 #4 读取 judge/gt；把中间档改成 `reconcilable_nonzero_displacement` 并明确“标注法未知、需人工判读”正是我上一轮给出的可接受修法 ①。它不再把整个容差带冒充半墙厚。
4. **`MAJOR-F24` 仍开。** 我上一轮的最低口径是三项：core stamp version、output convention/trust policy、scorer implementation identity。当前自动绑定前两项，第三项仍靠人工 bump `LEGACY_SCORE_CACHE_SCHEMA`，不满足“至少三项”，且行为探针实际复现了 implementation 被替换后旧 cache 继续命中。新 proof 的当前有效性也没有进入 cache predicate。
5. **`MINOR-A1` 关闭。** 既有三档词表下用 `severe` 拒绝 no-data 是足够的；`evidence` 与逐层 `boundary_no_data` 已明确区分“没验到数据”和“实测 miss”，本 finding 不要求另开 `unavailable` 枚举。
6. **`NIT-F25` 生产代码的同名冲突已消除，但文档尾巴未收完，故按同一 NIT 保留。** 两份仍有约束力的非 Python 文档还把已删除的 `SCORER_SCHEMA` 当现役符号使用。

## 2. 我做的验证

### 2.1 定向行为门

我没有重复 orchestrator 已独立跑过三次的全仓 `pytest -n auto`。按请求书“不要重复已测量项”的要求，只跑本轮裁量点与新攻击面：

```text
python -m pytest -q -n0 \
  tests/test_c2_b5_artifact_trust.py::test_forged_footprint_with_self_consistent_derived_artifacts_is_rejected \
  tests/test_c2_b5_artifact_trust.py::test_genuine_footprint_change_through_real_finalize_is_accepted \
  tests/test_c2_b5_artifact_trust.py::test_resolve_core_proof_for_attempt_real_accepted_write \
  tests/test_f22_blocker1_core_stamp.py::test_neuter_restoring_stamp_flips_declared_not_trusted \
  tests/test_f22_blocker1_core_stamp.py::test_core_proof_from_different_geometry_does_not_grant_trust \
  tests/test_f22_blocker1_core_stamp.py::test_minor_a1_boundary_no_data_does_not_read_as_pass \
  tests/test_f24_scoring_semantics_cache_identity.py \
  tests/test_c1_annotation_semantics.py

13 passed in 7.37s
```

另有：

- `git diff --check bddec579... da2245d`：rc=0，零输出；
- `python -m compileall -q src scripts tests`：rc=0；
- 机械枚举当前 v3 model fields：`CorrectedGeometryV3` 12 个顶层字段、`FloorV3` 6 个、`CellV3` 5 个、`WindowV3` 9 个。此枚举只证明我看了当前 schema 表面，不冒充“穷举所有 replay-divergent 执行路径”。

### 2.2 新行为反例 A：proof 已失效，cache 仍保留 `trusted=True`

该探针没有复跑 light gate 的“改 proof + 改 manifest”攻击；它测的是本提交新增信任事实与既有 cache 的交界：

```text
production_entry=_judge_gt_artifacts
manifest_output_hash_check_passed=True
proof_resolver_after_deletion=None
scorer_calls_after_deletion= []
cached_trusted_after_deletion= True
```

步骤是：用 `tests/test_c2_b5_artifact_trust.py::_accepted` 走真实 `StageRunner.record` 写出 accepted B5 fixture；从生产判卷入口 `_judge_gt_artifacts` 首次计算得到 `trusted=True` cache；删除 `deterministic_core_proof.json`；先直接确认 `_resolve_core_proof_for_attempt(...) is None`；再走同一生产入口（包括 manifest accepted pointer 与 output hash 检查）。结果 scorer 零调用，旧 sidecar 直接复用，仍是 `trusted=True`。

源码时序与行为一致：`run_stage.py:1785-1795` 先 `_load_valid_score_sidecar`，只有 miss 后才在 `:1797-1802` resolve proof。当前 predicate（`:1689-1718`）没有 proof hash/absence/accepted-record identity。因此“scorer 只认外部 proof”在首次计算成立，在 cache hit 不成立。

### 2.3 新行为反例 B：F-24 没有 scorer implementation identity

我先写出合法 cache，再把实际 scorer 函数替换为会记录调用并抛 sentinel 的不同实现；两个 live 常量不变：

```text
premise_cache_seeded= True
premise_scorer_implementation_replaced= True
scoring_semantics_unchanged= True
changed_scorer_calls= []
stale_cache_reused= True
```

这不是“第三项由人记得 bump 也算”的文字争论，而是当前判据的可观察行为：实现身份变化后 cache 仍命中。

## 3. 逐项裁定

### 3.1 `BLOCKER-1` —— 不关闭

#### 已成立的工程部分

- `stage_runner.py:360-392` 在 per-window audit 前比较 replay 与 candidate 的 footprint、floors/cells、window `id/floor_id/z`、conflicts、unsupported、corrections 前缀及 stamp；原 `[0,4]² → [0.12,3.88]²` 攻击现在得到 `writer_core_projection_drift`。
- `stage_runner.py:495-530` 只在上述比较与后续 host/audit/evidence 比较通过后构造 `DeterministicCoreProofV1`；`artifact_hashes` 绑定第七个 sidecar。
- `correction_score.py:171-240` 把 declared/trusted 分开，并在 scorer 内对当前 geometry 重算 projection hash。裸 dict 恢复印章不再取得 trust。
- hostile 与 honest writer 两向锁均通过；这说明 projection gate 不是“恒拒绝”假门。

#### 为什么仍不构成外部信任根

`decision_log.md §5.14` 的用户定案不是“哈过就可信”，而是两问：

1. 冻结记录之外是否有第二处记载；
2. 第二处是否在运行前已固定、且被评判方写不了；新根还须用户拍板登记。

当前方案两问都没有得到满足：

- `DeterministicCoreProofV1` 只有 `core_version/input_hash/core_projection_hash` 三个普通字段；没有数字签名、MAC、signer identity 或外部 receipt。“writer 签发”是 issuance，不是 cryptographic signing。
- 请求书称其为“本地 append-only 账本”不准确：append-only 的是 `attempts/NNN` 目录；`RunManifestV2.accept` 在 `manifest.py:304-305` 直接替换 `stages[stage]`，`save_run_manifest` 在 `:344-356` 用 `os.replace` 重写 manifest 文件。
- proof 与 manifest 位于同一 run 目录，拥有该目录写权的主体可以同时改 proof 与 `artifact_hashes`。manifest 没有更外层的不可伪造锚来指出原值。SHA 只检查两份可一起改的值是否自洽，不证明是谁写的。
- §5.14 的在册清单只有 `run_config.yaml` 档位声明与事先签字/绑图像指纹的 case 身份；accepted manifest 不在册。若项目要把 trusted writer 的 run manifest 明确注册为第三种根，必须先由用户改变/扩充治理判据，审阅者不能默许扩表。

所以，在“候选 payload 不能直接调用 writer/改 manifest”的窄模型下，这个方案确实把攻击挡在 writer 边界；但在本项目现行的外部根判据下，**同一缺陷只是从 artifact 字段上移到另一份可共同改写的本地 JSON。**

#### cache 又绕过了当前 proof

即便暂时把 manifest 当根，§2.2 的反例也独立阻止 closure：当前 proof 已不存在、resolver 明确返回 `None`，cache 仍输出 `trusted=True`。最低修法是：

1. cache lookup 前先解析并验证当前 accepted proof；
2. cache identity 绑定“当前外部根认证过的 proof identity”（至少 proof bytes hash + accepted record identity；若改为签名/外部 receipt，则绑定并复验 receipt identity）；
3. cached sidecar 自称 `trusted=True` 时，proof 缺失/失效必须 miss 并重算为 refused，不能信 cache 自报；
4. 补“先 trusted cache → 删除/篡改 proof → resolver None → cache miss → trusted False”的真实入口锁，同时保留 proof 不变时必须 hit 的正向锁。

#### 外部根的可接受出口

至少需选一种并由用户登记：

- 用 writer 私钥/MAC key 对 attestation 签名，验证公钥/根身份在运行前固定且 evaluated process 无写权；
- 把 accepted receipt 写入 run 目录之外的 WORM/权限隔离/远端 append-only store，run 内只存可验证引用；
- 由已有外部批准/真人签字链签 accepted manifest digest。

若项目明确把威胁模型收窄为“只防候选对象，不防任何拥有 run-dir 写权的主体”，也可以治理改判；但必须明文改 §5.14/登记清单，不能继续把当前普通 JSON 称为“tamper-evident external root”。

### 3.2 正向真实链路 —— 必须完成，且是 closure 条件

“proof 今天才有，所以盘上零份真实产物”不证明实现错误，也不另计 severity；但它阻止无条件签收。修完本裁决的根与 cache 问题后，真实重跑至少要观察：

1. 当前真实 run 使用的 `correction_b5_orientation_v1` writer 生成 proof，并由外部根认证；
2. accepted output/proof/manifest（或外部 receipt）逐字节对账；
3. 正常 judge 首次计算得到 `declared=True, trusted=True`；
4. 第二次身份不变时 cache 命中；
5. 在该 run 的隔离副本中破坏 proof/receipt 后，resolver 失败且旧 trusted cache 不得命中；
6. 不引入历史白名单，旧无 proof 产物继续 fail closed。

在此以前，不能写“BLOCKER 已关闭但以后再验”；准确状态是 **implementation partially verified, closure pending**。

### 3.3 core-owned projection 未穷举限制

我机械枚举了当前 schema 字段，并逐项对照 projection 与 writer 旁路检查；没有把“读过字段表”写成“穷举了所有路径”。当前核心坐标面没有发现第二条 writer bypass：

- top-level footprint、floor ring/z/height、cell id/role/x/y/polygon、window id/floor_id/z、三类 audit list 在 projection；
- final-owned window span/room/facade-segment 由 replay audit + fresh claims + final-field comparison绑定；window facade 参与 fresh host recomputation；
- `facade_segments` 由 writer 从 ring 独立验证；stamp 单独比 live version；schema 类型本身固定 v3；
- `notes` 非几何，`north_axis` 属 orientation enrichment，window provenance 不参与本 finding 的 boundary/wall output-convention trust。

因此“没有穷举所有未来路径”本身不新增 finding，也不是本轮不关闭的理由；真正阻断项是外部根与 cache。后续宜把 field ownership 做成版本化 allowlist/contract test，schema 新增字段时必须显式归入 core-owned、final-owned、orientation-owned 或 non-semantic，而不是靠审阅者再次人工猜。

### 3.4 `MAJOR-C1` —— 关闭

- 中间态已经是 `reconcilable_nonzero_displacement`；`0.02/0.12/0.29` 三档锁均保留数值但不再声称 outer-skin。
- 人读 label、interpretation 与 report rule 同步说明“没有可信墙厚事实，不能判断标注法，需人工判读”。
- 读取 judge/gt 侧墙厚会违反 `CLAUDE.md §1.5 #4`，所以不采用我上一轮修法 ②是正确裁量，不是漏做。
- 四态与纯观测边界未变。

`MAJOR-C1` 按上一轮定义 **CLOSED**。

### 3.5 `MAJOR-F24` —— 仍开

F-24 的原规格逐字要求“至少”三项。当前 `_current_scoring_semantics_identity()` 只有：

```text
core_stamp_version
output_convention
```

它正确解决了两项 live constant 漂移，但 `LEGACY_SCORE_CACHE_SCHEMA` 仍是手动值，不是 scorer implementation identity。§2.3 已行为证明实现替换不会失效 cache；因此两项不能按“三项里大部分已做”签收。

同时，proof 的当前存在/有效性已经成为 scoring semantics 的真实输入，却也未进入 predicate，§2.2 证明会保留 stale trusted 结果。F-24 修复应至少绑定：

1. live core stamp/proof version；
2. live output-convention/trust-policy identity；
3. scorer implementation identity（例如由实际部署 build revision，或明确列出的 scorer/policy/dependency source digests 派生；不能再靠另一个手写 bump）；
4. 对 correction 分支，当前 externally authenticated proof/receipt identity，或在每次 cache hit 前重新验证它。

保留正向 cache-hit 锁；新增 implementation-only mutation 与 proof-loss 两条反向锁。截止点仍是 **第一份可复用 schema-11 cache / 用户已拍板的真实重跑之前**。

### 3.6 `MINOR-A1` —— 关闭

`score_policy.py:298-309` 现在只要 `no_data_boundary_floors > 0` 就把 `boundary_complete` 设为 `severe`；evidence 同时保留 `boundary_hits=0/0`、`missed=0`、`no_data_floors=N`，每层还有 `boundary_no_data`。在既有 `pass/minor/severe` 词表内，这已经做到“不把拒判说成 pass”，且机器/人均可从 evidence 区分 no-data 与 miss。

另开 `unavailable` 会扩大长期 schema 与消费者词表，不是原 finding 的必要条件。`MINOR-A1` **CLOSED**。

### 3.7 `NIT-F25` —— 代码修正成立，文档尾巴仍开

Python 生产符号已清楚分离：legacy 为 `LEGACY_SCORE_CACHE_SCHEMA`，typed 为 `SCORE_SIDECAR_SCHEMA`，重复别名已删除。独立性锁仍在，运行时无错配。

但我对提交 `da2245d` 的 tracked files 做了 exact-symbol `git grep`；排除历史 review/plan/decision 记录后，至少两份仍有约束力的现役文档仍把删除的名字写成当前合同：

- `AI_agent/architecture/judge_grade_model.md:116`：要求 `SCORER_SCHEMA` 递增；此处实际指 legacy cache label，应改成 `LEGACY_SCORE_CACHE_SCHEMA`；
- `skills/intake_pipeline/1_correction/A0_contract.md:235`：写 `SCORER_SCHEMA="8"`；此处实际指 typed v8 label，应改成 `SCORE_SIDECAR_SCHEMA="8"`。

历史 proposals/logs 的原时点名称不要求回写。因为本 finding 本来就是降低审计认知负担，这两份活文档仍会把读者引回同名歧义，故 `NIT-F25` 保留到两处更正。

### 3.8 上一轮未动 findings

请求书明确未声称处理，commit delta 也未修改其核心 owner；没有新的闭合证据，因此状态不变：

- `MAJOR-1`、`MAJOR-2`、`MAJOR-B2`、`MAJOR-B3`：仍开；其中 B3 的 condition 5 仍是“未实现却声明 evaluated”，B2/B3 仍为 S3 硬前置。
- `MINOR-3`、`MINOR-B4`、`MINOR-B5`、`MINOR-D1`：仍开，截止点沿用上一轮。

这项是 burden-of-proof 状态确认，不冒充本轮重新跑过它们的全部 hostile probes。

## 4. 请求书的外围表述修正

这些不改变审阅方向，按 §0 分层规则记录后继续完成主体：

1. **“append-only ledger”字面不成立。** append-only 是 attempt directory 纪律；accepted manifest 是可替换 pointer 文件。
2. **“writer 签发 proof”不等于“proof 有签名”。** 当前对象无 signature/MAC；应称 writer-issued sidecar，不能据此推出防篡改。
3. **F-24 已做“2/3”不能等价成满足“至少三项”。** 注释诚实披露缺口值得肯定，但披露不会自动关闭 finding。

## 5. 未关闭 finding 总表

| 级别 | ID | 本轮状态 / 摘要 | 截止点 |
|---|---|---|---|
| BLOCKER | BLOCKER-1 | run-local mutable manifest 不是 §5.14 外部根；proof 失效后 trusted cache 仍命中 | 本批复审通过及任何真实 trusted 重跑前 |
| MAJOR | MAJOR-1 | V2 raw/context/manifest/readings 未从 bytes 重建绑定 | S3/S4 前 |
| MAJOR | MAJOR-2 | decision preimage 缺 frame/scope/z/floor 身份 | S3/S4 前 |
| MAJOR | MAJOR-B2 | coverage declaration 不由实际 evaluation receipts 派生 | S3 前 |
| MAJOR | MAJOR-B3 | condition 5 未执行却声明 evaluated | S3 前 |
| MAJOR | MAJOR-F24 | cache 只自动绑 2/3 语义身份；还不绑定当前 proof/receipt identity | 第一份 schema-11 cache / 真实重跑前 |
| MINOR | MINOR-3 | legacy mirror coercion 分叉 | S3/S4 新 live v3 前 |
| MINOR | MINOR-B4 | z datum 缺失误归 model pair mismatch | S3 前 |
| MINOR | MINOR-B5 | `validate_case` 不传 verified resolver inputs | S2 审计一致性收口 |
| MINOR | MINOR-D1 | metadata guard 不等于 byte-for-byte | F-23 收口 |
| NIT | NIT-F25 | 两份现役非 Python 合同文档仍引用已删除的 `SCORER_SCHEMA` | 下次 scorer/schema 文档清理，最迟下次版本变更前 |

关闭项：`MAJOR-C1`、`MINOR-A1`。

## 6. 我没有验证什么

- 没有重复 orchestrator 已完成的三次全量；本轮独立执行的是 13 条裁量相关 targeted tests、两条新行为探针、compileall 与 diff-check。
- 没有跑用户尚未执行的真实 end-to-end rerun，因此没有声称真实 run 已出现 `trusted=True`。
- 没有重复 light gate 已做的 orientation writer compare、旧产物拒判、23 份 V2 历史 manifest 加载或“proof+manifest 同改”探针；我直接裁其治理含义，并另测了未覆盖的 cache seam。
- 没有穷举所有函数级 replay-divergent 路径、未来 schema 字段或复杂体量；只机械枚举当前 v3 schema fields，并审阅当前字段的 owner/旁路检查。
- 没有重跑上一轮 MAJOR-1/2/B2/B3 与 MINOR-3/B4/B5/D1 的 hostile probes；它们因本提交未处理且无新闭合证据而保持 open。
- 没有审阅 orchestrator 全量中的 211 条 warning 是否含新 warning。

## 7. 最终裁决

本提交把 writer replay 与 declared/trusted 分层向正确方向推进，`MAJOR-C1` 与 `MINOR-A1` 可以关闭；但 **hash-bound local JSON 不是本项目既有判据下的外部信任根**，而且 scorer cache 当前可以在 proof 已失效时继续复用 `trusted=True`。F-24 也明确只完成 2/3 身份组件。

因此 `BLOCKER-1` 不得关闭，提交 `da2245d` 的第四轮总判定为 **CHANGES REQUIRED**。
