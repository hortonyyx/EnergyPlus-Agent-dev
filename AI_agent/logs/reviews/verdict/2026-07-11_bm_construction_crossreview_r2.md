# B-M 施工交叉复核 r2（terra，中档）

**结论：REWORK（五项返修中 4 CLOSED / 1 PARTIAL；CR-02 的跨批处置不接受为 B-M 完结）**

本复核仅依据 B-M v6 定稿、B2 §2.8、当前工作树相对 `b14af01` 的代码 diff 与测试执行；未以执行简报作为结论依据。

| 原 finding | 结论 | 复核结论 |
|---|---|---|
| CR-01 | CLOSED | payload 自校验、版本冻结与生成器严格 parse 均已闭合。 |
| CR-03 | PARTIAL | 缺 artifact 与 backfill 前零最终写入已闭合；但未先 fsync 两个 temp 再按序提交，仍偏离冻结 commit 协议。 |
| CR-04 | CLOSED | `views.<stem>.completeness` 已形成受信 metadata → strict wire 的生成闭环。 |
| CR-05 | CLOSED | 三个声明家族已有受控 output-id transform，overlay 不会再发明输入。 |
| CR-06 | CLOSED | canonical serializer 与 judge-only 只读 verify 已接入。 |
| CR-02 | **OPEN / BLOCKER** | 仍未满足 B-M v6 的 grandfather/通用 V2 writer 要求；登记到 B2 不能使当前 B-M 施工完结。 |

## CR-01 — CLOSED

**证据**：

- `src/agent/execution/view_manifest.py:417-452` 将所有 schema/version 冻结为 `Literal["1"]`，并在 model validator 中对排除 `content_sha256` 的 canonical payload 重算 hash；不一致直接拒绝。
- `:843-857` 改为 plain payload → hash → `ViewManifest.model_validate()` 的一次严格 parse，已消除上轮 `model_copy(update=...)` 绕过 validator 的路径。
- `:877-899` 的 provision reuse、`:910-936` 的 verify 都先经严格 JSON parse；isolation/migration 仍经这些入口或同一 model parse。

新增回归覆盖 stale-hash 的 dict/JSON parse、磁盘字段篡改后 verify/provision 拒绝、以及未知 claims vocab 拒绝（`tests/test_view_manifest_schema.py` 与 `tests/test_view_manifest_generator.py`）。这闭合了上轮可把 `expected_output_id` 改为 forged 值但保留旧 hash 仍通过的漏洞。

## CR-03 — PARTIAL

**已闭合部分**：

- `src/agent/execution/manifest.py:387-434` 在任何最终文件写入前完成 view manifest 构建、所有 accepted pointer 的 backfill、run_id/V2 构建；`:393-415` 对缺失 `output.json` 或 `checks.json` fail closed，`:401-407` 重算并核对 output hash。
- 对应负例断言失败时没有 `view_manifest.json`，见 `tests/test_run_manifest_v2.py` 的 `test_migration_rejects_pointer_whose_output_changed_since_accept`、`test_migration_missing_output_fails_before_any_write`、`test_migration_missing_checks_fails_before_any_write`。

**未闭合部分（MEDIUM）**：v6 §5.1 冻结为“两个新文件先各写同目录 temp + fsync，再按 `view_manifest.json`、`RunManifestV2` 的次序提交”。实现 `src/agent/execution/manifest.py:436-458` 先完成 VM temp+fsync+replace，随后才调用 `save_run_manifest()` 生成 V2 manifest 的 temp。若后一步 temp 写入失败，虽遗留的 VM orphan 按 V1 语义确实无害，但仍未执行所规定的“两个 temp 均已完成后再 commit”协议。

**建议修法**：在内存阶段预先序列化两份最终文本；分别创建、写入、fsync VM 与 V2-manifest temp，只有两者均成功后才先 replace VM、再 replace V2 manifest。增加“第二份 temp 写入失败时 VM 尚未 replace”的故障注入测试。

## CR-04 — CLOSED

`src/agent/execution/view_manifest.py:244-306` 已实现受控 metadata shape：`views.<stem>.completeness={assertion_id, claims}`；它校验 claims 非空、类型和 observable 子集，按 plan/elevation 构造 coverage，并写入 `CaseMetadataSourceRef(json_pointer, case_metadata_sha256)`。

三类 entry 生成点均把 overlay 与 metadata hash 传入该函数（`:689-692`、`:731-734`、`:769-772`）；`:830-841` 使悬空 overlay stem hard-fail，避免静默无效声明。端到端正例、越界 claim、detail 无 C2 frame、畸形 shape 和 dangling stem 均有测试。该实现满足 strict wire 的受信来源绑定，且 generator 不从产品产物取值。

## CR-05 — CLOSED

`src/agent/execution/view_manifest.py:51-103` 为 floor plan、cardinal elevation、supplementary plan 三个 metadata 声明家族显式定义 `view_type` 与 output-id transform；生成处只从相应家族调用 `_family_expected_output_id`（`:686-688`、`:728-730`、`:766-768`）。不存在“任意 stem 自动补 `_view`”的全局 fallback。

`:830-841` 对不能绑定到已声明家族的 `views` row 拒绝，未分类 PNG 仍由 `:821-828` 硬门拒绝。测试锁定 sm21 identity 与 sm20 `supp_plan → supp_plan_view`，并覆盖无家族 overlay/PNG 不得被猜测为 required view。

## CR-06 — CLOSED

`canonical_view_manifest_json()` 在 `src/agent/execution/view_manifest.py:482-494` 统一使用 sorted keys、固定 separators 和 UTF-8；provision `:898` 与 migration `src/agent/execution/manifest.py:449` 共用它。测试比较 provision/migration 的字节并断言磁盘 JSON 的 canonical 键序。

`scripts/tool_scripts/run_stage.py:1396-1416` 的 judge-only 路径现在只读检查：缺 manifest 输出 NOT_APPLICABLE 且不 provision；已有但 drift/corrupt 时直接 exit 2，且在读取/写入 verdict 之前返回。`tests/test_run_stage_flow.py:361-398` 覆盖两种行为。此仓库的 judge-only replay 入口即该命令，故 §4.4 的该接缝已闭合。

## CR-02 — OPEN / BLOCKER：移交 B2 不可接受为 B-M 完结

B-M v6 §5.1 明确把共同 RunManifestV2/StageRecordV2 wire 的唯一 owner 定为 B-M、要求 B-M 先落，并要求 persisted V1 run 对“flow reading、resample、isolation merge”的任何新 0_reading attempt 一律 BLOCK。当前运行入口仍不满足：

- `scripts/tool_scripts/run_stage.py:1324-1358` 的 `cmd_run` 仍以 `RunManifest.load()` + `StageRunner` 写 V1 record；没有调用 `reading_attempt_allowed()`。
- `:1385-1393` 的 `cmd_resample` 更会先在 persisted V1 上 `invalidate()`、`save()`，之后再进入 run。
- `:1508-1540` 的 flow 同样没有 grandfather gate；`src/agent/execution/stage_runner.py:120-180` 仍只有 V1 `RunManifest`/`StageRecord` writer，普通新 flow 仍不产生 V2 的 `{output, checks}` artifact contract。

`reading_attempt_allowed()` 仅由 isolation merge 调用（`src/agent/execution/isolation.py:265-267`）。因此该保护在命令层并不存在，且 B-M 原本要求的 V2-by-default 通用 writer 也未落地。

将这项登记到 B2 计划并不改变上述唯一规范 owner、施工顺序或 grandfather 硬门。尤其“单加 guard 会砸断新 run resample”不是充分理由：`reading_attempt_allowed()` 对**无 persisted manifest**本就返回允许；正确解决方案是 B-M 规定的 versioned writer / 新 run V2 provision，而非放任已落盘 V1 的新 attempt。除非先正式修订并重新批准 B-M v6 的范围/owner，本复核不能把该移交认定为可接受。

## 测试与盘面

独立运行：

```text
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_view_manifest_schema.py
31 passed in 2.36s

PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  tests/test_view_manifest_generator.py tests/test_run_manifest_v2.py tests/test_run_stage_flow.py
71 passed in 21.56s
```

上述 102 项覆盖本轮五条修复的主要新增路径。`git diff --check b14af01` 无 whitespace 错误，diff 未触及 case anchor/golden 文件；原工作树中已有的首轮 verdict 保留未改。

**提交建议**：CR-01/03/04/05/06 的返修可以作为后续修复提交的组成部分；但当前工作树不能作为“B-M 施工完成”收录提交。至少须完成 CR-03 的双-temp 提交协议和 CR-02 的 B-M 所有权要求（或先以正式定稿修订改变该要求）后，才可给出 APPROVE。
