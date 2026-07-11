# B-M 施工交叉复核（terra，中档）

**结论：REWORK**

复核范围严格限于 `c2_bm_view_manifest_spec.md` v6、B2 细稿 §2.8、`91fc1d4..b14af01` 的代码 diff 与实际测试；未以执行简报作为判断依据。虽然 claims 词汇、CompletenessAssertion wire 的大部分类型约束、isolation 的 unbound 拒 merge、以及 gate① 的 `INVARIANT` 分型已落地，但以下缺口会直接破坏受信清单或 v1 grandfather 合同，不能放行。

## Findings

### CR-01 — BLOCKER：磁盘 manifest 可在不改 `content_sha256` 的情况下被篡改后通过 verify

**规范依据**：§3.0 要求消费者先验 schema、版本和 content hash；§4.4 要求 verify 对 hash 漂移 fail closed；§8 要求篡改任一字段可检出。

**证据**：

- `src/agent/execution/view_manifest.py:314-322` 的顶层 validator 只校验 entry 排序/重复，未校验 `content_sha256 == compute_content_hash(payload)`；`claims_vocab_version` 还是任意 `str`（:305-312），也未按未知版本拒绝。
- `src/agent/execution/view_manifest.py:711-724` 与 `:743-763` 只把磁盘中自报的 `content_sha256` 同重建结果的 hash 字段比较，不重算磁盘 payload。

独立复现：provision sm21 后仅把一个 required entry 的 `expected_output_id` 改为 `1f_view_forged`，保留原 `content_sha256`；`verify_view_manifest(...).ok` 返回 `True`。这能改变 coverage denominator 和 staging inventory，且 isolation merge 也会把该 manifest 当作已验证的权威对象。

**建议修法**：为磁盘/消费者入口增加 content-hash 自校验（并将 `claims_vocab_version` 冻结为 `Literal["1"]` 或等价版本分发）；provision/verify/isolation 一律只使用校验成功的对象。生成时改为先构造 payload、计算 hash、再进行最终严格 parse，避免用 `model_copy(update=...)` 绕开新 validator。补“改任意字段但保留旧 hash 必拒”和“未知 claims vocab 必拒”的回归。

### CR-02 — BLOCKER：正式 flow/resample 可继续在 V1 run 写入并接受新的 0_reading attempt；普通新 run 也没有落到 V2 writer

**规范依据**：§5.1 规定 grandfather v1 仅可 validation/replay/report，任何 flow reading、resample、isolation merge 的新 0_reading attempt 一律 BLOCK，必须显式 migration；同节要求本批落 RunManifestV2/StageRecordV2 wire，`base_v2` 由 StageRunner 通用 attempt writer 写入。

**证据**：

- `scripts/tool_scripts/run_stage.py:1324-1358` 的 `cmd_run` 直接 `RunManifest.load()` 并创建 `StageRunner`，没有调用 `reading_attempt_allowed()`；`:1385-1393` 的 `cmd_resample` 更在进入 `cmd_run` 前就对 V1 manifest 执行 `invalidate()` 和 `save()`。
- `scripts/tool_scripts/run_stage.py:1508-1540` 的 `flow` 同样未作 grandfather 检查。
- `src/agent/execution/stage_runner.py:120-180` 的类型/写入仍是 `RunManifest`/`StageRecord`（V1）；`src/agent/execution/manifest.py:324-350` 的 V2 ensure 仅被 isolation builder 使用。因此普通 flow 即使预先 provision，仍可产出 V1 accepted record，既没有 `run_id/run_inputs`，也没有 `base_v2` 的 `{output, checks}` artifact hashes。

**建议修法**：在任何可能创建 0_reading attempt 的命令入口、且在 resample 的 invalidate/write 之前执行 V1 拒绝；新 run provisioning 应原子地建立 V2 identity，或要求明确的 V2 provision。把 StageRunner/flow 改为 versioned writer，V2 上写 `StageRecordV2(artifact_contract="base_v2")` 并实算 output/checks hashes；为 run、resample、flow 三入口各加 V1 拒绝测试，另加新 run 正常写 V2 record 的端到端测试。

### CR-03 — HIGH：migration 未按冻结 commit 协议先完成内存 backfill，且接受缺失 accepted artifact 的指针

**规范依据**：§5.1 migration 必须先在内存完成 run_id、view manifest 和全部 accepted-stage backfill（逐 pointer 验文件、重算真实 hash），之后才写两个 temp；仅缺 legacy sidecar 可合法省略，最后才提交 RunManifestV2。

**证据**：

- `src/agent/execution/manifest.py:383-403` 在 backfill 之前已把 `view_manifest.json` replace 到最终路径；backfill 从 :405 才开始，违背“内存完成后再写”的顺序。
- `:410-422` 对不存在的 `output.json`/`checks.json` 只是跳过，仍在 :423-444 生成并提交一个 `migrated_v1` record。独立复现一个 V1 accepted pointer 不建 attempt 文件即可迁移成功，结果该 record 的 `artifact_hashes == {}`。

**建议修法**：先完整读取、验证并转换全部 stage；accepted `output.json`（及既有必须的 checks artifact）缺失或 hash 不一致立即失败，禁止写任一最终文件。两份已完成内容分别 fsync temp，随后按规定先 replace VM、后 replace V2 manifest。补 backfill 失败时 VM 亦不落盘，以及缺 output/checks 的负例。

### CR-04 — HIGH：`views:{}` 的 completeness/negative-evidence 生成通路没有实现

**规范依据**：§4.2 明定 `views:{}` 是 `direction_semantics/azimuth_deg/view_kind/**completeness 断言**` 的逐 view 覆盖槽；负证据只能由该受信 metadata（或规定的 user/dataset source）逐 claim 开启，并同时生成 coverage/assertion。

**证据**：`src/agent/execution/view_manifest.py:526-549`、`:562-586`、`:595-619` 对 overlay 只消费 semantics、view_kind、dimensioned；每种图最终都固定调用 `_opening_evidence_for()`，而该函数 `:184-191` 只生成 observable claims 和空 negative 集。没有把 metadata assertion 解析/绑定为 `CaseMetadataSourceRef`、`Coverage`、`CompletenessAssertion` 的路径。

**建议修法**：冻结并实现 metadata overlay 的 completeness 结构、JSON pointer 与 metadata hash 绑定，逐 claim 填充 OpeningEvidence；非法 source、非 observable claim、coverage/assertion 不匹配必须在 generator hard-fail。增加一条从真实 `views:{}` metadata 到最终 manifest 的正例，而不只测手工构造 schema。

### CR-05 — HIGH：`expected_output_id` 以通用 stem 后缀猜测，未实行规范要求的显式映射表

**规范依据**：§3.2 与 §4.2 要求它是显式产物对账键；sm20 `supp_plan → supp_plan_view` 是“映射表写死，不猜 stem”的示例，supp/site/detail 必须按该表落 typed required_view。

**证据**：`src/agent/execution/view_manifest.py:388-394` 对所有输入采用“已有 `_view` 就原样，否则追加 `_view`”的通用规则；`:51-59` 的 supplementary 表只保留图种，未包含 output-id mapping；`:616` 仍调用上述通用函数。

**建议修法**：以 metadata key/已声明图类为键建立受控 mapping，表值同时含 `view_type` 和 `expected_output_id`；未知声明不得由文件名推断，必须 hard-fail 或显式扩表。补一个不符合该 suffix 规则的声明 fixture，证明不会静默猜测。

### CR-06 — MEDIUM：序列化未满足“canonical JSON 键排序”，且 judge-only/replay 未接 verify

**规范依据**：§3.0 要求 canonical JSON（键排序）和未知版本 fail closed；§4.4 指定 verify 由 validate_case、judge-only/replay、isolation build/merge 调用。

**证据**：

- `src/agent/execution/view_manifest.py:725` 与 `src/agent/execution/manifest.py:397` 使用 `model_dump_json(indent=2)`，并未 `sort_keys=True`；尽管当前字段声明顺序稳定，输出不是规范规定的键序 canonical JSON。
- 全量引用中 verify 只落在 `src/agent/execution/validation_run.py:164` 与 `src/agent/execution/isolation.py:151,276`；`scripts/tool_scripts/run_stage.py:1396-1429` 的 judge 路径没有调用 verify，replay/flow 也没有等价只读校验入口。

**建议修法**：集中一个 canonical serializer（排序键、固定 separators/UTF-8）供 provision 和 migration 使用，并以其 payload 算 hash；在 judge-only/replay 入口调用纯 verify，失败以 invariant finding/block 返回且绝不 provision/write。补字节键序断言及 judge/replay 缺失/漂移 manifest 的负例。

## 已核对的通过项（不抵消上述问题）

- `src/agent/correction/claims.py` 的七个词汇、`WINDOW_CLAIMS=frozenset` 与版本 `"1"` 和 B2 §2.8 一致。
- `reading.view_manifest_coverage` 以 `CheckLayer.INVARIANT` 产生 fail（`src/validator/checks/view_manifest.py:105-133`）；通用 disposition 对非 evidence 的 invariant fail 在所有 run_profile 均 BLOCK（`src/validator/checks/schema.py:137-145`）。
- isolation 的 preview/unbound workspace 在 merge 时拒绝，正式 build 要求已有 VM，并在 blocking report 下不 accept（`src/agent/execution/isolation.py:150-161,250-280,335-360`）。不过它依赖 CR-01 的失效 verify；另外 binding 中写入的逐图 hash（:170）在 merge 比对 :276-281 中没有逐项直接比较，返工时应按 §5.2 补齐。
- diff 未修改 case anchor/golden 文件；`validate_case` 对未 provision 的旧 run 报 NOT_APPLICABLE，且其默认 read-only 分支未调用 provision（`src/agent/execution/validation_run.py:146-175`）。但 CR-02 仍使同一旧 V1 run 可经 flow/resample 被写入，故“grandfather 只读”整体不成立。

## 测试记录

独立运行的新/改 B-M 测试子集：

```text
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  tests/test_check_view_manifest_coverage.py tests/test_run_manifest_v2.py
39 passed in 4.94s
```

这些测试未覆盖 CR-01 的“payload 篡改而保留旧 hash”、CR-02 的 flow/resample V1 入口、CR-03 的缺 accepted artifact，亦未覆盖 CR-04 的 metadata-to-completeness 生成通路。
