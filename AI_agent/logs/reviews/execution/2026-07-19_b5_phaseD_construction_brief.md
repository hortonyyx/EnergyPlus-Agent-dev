# C2 B5 Phase D 施工简报

日期：2026-07-19  
施工者：sol  
结论：**Fable r1 REWORK 已返工 COMPLETE；生产码零改动，缺失的安全拒绝锁及同轮 MINOR 已补齐，送 Fable r2 对抗复审。最终 CLOSED 仍以 Fable APPROVE + 主控轻门为准。**

首轮诚实标出的五项未竟已在主控裁决后全部续作：writer 从嵌入原始 sources replay producer→core/audit、v3→B2 后门硬删、integrated 在冻结签名内重验内嵌 raw sources、report 读取 rejected typed conflict、legacy 与 #4/#11/#16/#17 锁补齐。六件套、accepted/build proof、E4 rebind、双路径 proof、legacy versioned-byte 与原 6 个 Phase D xfail 保持全绿。

## 1. Gate 状态

### B5-D1 writer-recompute — 完全交付

已交付：

- `src/agent/execution/stage_runner.py:185-197` 对任意 v3（含零窗）要求四个 B5 字段全非空；全 None/部分携带均在 attempt 创建前拒绝。
- `src/agent/execution/stage_runner.py:259-382` 对 output/prepared bytes、raw-source resolver、Vg、feature artifact、host claims、audit replay、Va evidence 做 writer-boundary 重验；内部 module-qualified `window_host_module` 调真复算核。
- `src/agent/correction/window_sources.py:157-255,628-676` 的 self-contained resolver artifact 嵌 producer/manifest/readings；writer 只从这些 raw bytes fresh 派生 direction facts与 source catalog，不复用 marker 自带 facts。
- `src/agent/execution/stage_runner.py:318-382` 从 producer raw 重跑 structural/window core（含同 raw readings 导出的 authoritative envelope），逐窗校验 `original_room/original_span`，再把 resolved room/ref/span/source/branch/digest 与 fresh claim 逐项对齐；endpoints/vertices/t/digest 由 fresh claim 全对象比较覆盖。
- `tests/test_c2_b5_artifact_trust.py:95-238` 锁 record digest #16、真实 patched-finalize #17、零窗 v3 后门、原始 room/span audit；`tests/test_c2_b2_v3.py:61-84` 历史零窗 fixture 已迁为生产 builder 真 marker + B5 六件套。

### B5-D2 accepted-chain — 完全交付

已交付：

- `src/agent/execution/manifest.py:169-228` 增加两个 artifact key、两个 B5 contract，并把 required/allowed 精确固定为六键。
- `src/agent/output_coordinates.py:277-348` 全验 output/feature/resolver/hosts、Vg、host relation、Va evidence 后才签发 immutable proof。
- `src/agent/output_coordinates.py:367-516` manifest loader 只读 accepted attempt，核六个 StageRecord hash，重新读取 `_run/view_manifest.json` 与 `0_reading` 原件并重验 source identity；不从 stage-root convenience copy 取 proof。
- `src/agent/output_coordinates.py:519-585` integrated loader 接两份 raw sidecar，缺一或 v3 全缺均拒绝，并做 artifact/关系全验。
- `src/agent/output_coordinates.py:440-455` accepted loader 的 v3 contract 只接受 B5/B5-orientation；攻击者把六件套降级成 `correction_b2_v1` 并删 proof 仍在 accepted boundary 硬拒。
- `src/agent/geometry/build.py:41-151` proof 只能由 verifier token seam 签发，消费时 fresh parse/recompute；`src/agent/geometry/build.py:154-176` v3 缺 proof 拒绝。

- `WindowResolverInputsArtifactV1` 在 `raw_window_resolver_inputs_bytes` 内嵌 producer draw、raw view manifest 与 keyed raw readings；`verify_window_resolver_inputs_artifact` 从内嵌 bytes 重算 manifest/reading/locator/direction facts。integrated 按 §12.3 冻结签名补齐两参、未超出冻结签名；签名冻结与 tampered embedded reading 负锁见 `tests/test_c2_b5_artifact_trust.py`。
- `src/agent/output_coordinates.py:552-557` 明确禁止 integrated v3 无完整 B5 proof 构造 accepted marker。

### B5-D3 E4 rebind — 完全交付（生产链）

- `src/agent/correction/orientation.py:378-402` 接受 verified B5 base 并保留历史 B2 replay 分支；`src/agent/correction/orientation.py:471-529` 保证仅 north-axis/audit 改变，fresh rerun host claims 且 host relation 逐值不变；`src/agent/correction/orientation.py:530-558` 重建 output、feature、Va evidence，禁止沿用 base host artifact bytes。
- writer 输出 `correction_b5_orientation_v1`；`src/agent/output_coordinates.py:608-638` output-coordinate contract 只按 schema v3 + populated north axis + orientation contract 放行，并要求 B5 proof 全链。
- `tests/test_c2_b5_artifact_trust.py:267-283` 锁 base `window_hosts` bytes 重用必拒；`tests/test_output_coordinate_identity.py:308-492` 锁 stepwise→writer→loader→build→assembly 与 integrated projection。

### §10.3 audit/report — 完全交付

- `src/agent/execution/correction_audit.py:16-78` manifest-first 读取 accepted audit，并经完整 accepted loader 验同 attempt hosts/evidence；branch/clamped span 来自 geometry proof，corroboration 来自 evidence ledger；坏 resolution hash 直接阻断。
- `scripts/tool_scripts/record_baseline.py:379-421` 与 `scripts/tool_scripts/report_assembly.py:375-410` 接入统一 reader；测试见 `tests/test_c2_b5_artifact_trust.py:326-349`。
- `src/agent/execution/correction_audit.py:17-64` 只扫描非 accepted 且 checks blocking 的 attempts，strict parse `WindowHostConflictV1` 后输出 reason/branch/gate/fallback；`record_baseline.py:422-425` 与 `report_assembly.py:411-422` 消费该 typed 行。root convenience copy 不参与；锁见 `tests/test_c2_b5_artifact_trust.py:569-624`。

### B5-D4 legacy-semantic — 完全交付

- `tests/test_c2_b5_legacy.py:85-143` 分别锁 v1 rectangle/v2 polygon 的 finalize→build→building/spec/audit、structural snap 后原位 window clamp、B5-only extras 无影响、`window_clamp_to_parent=False`。
- `src/agent/correction/artifact_serialization.py:7-30` 以 versioned serializer 排除 legacy output 中的 B5-only keys；没有改 v1/v2 schema 字段。
- `tests/test_c2_b5_legacy.py:152-176` 分别冻结 v1/v2 missing-room 与 no-parent 的当前失败/skip note；`:179-198` 对 integrated/stepwise 同输入比较 final geom、None proof、built geometry、output/build/spec/audit 全项语义。

### B5-D5 versioned-byte — 完全交付

- `tests/fixtures/c2_b5_legacy_window_byte_sha256.json` 冻结带窗 v1/v2 output/build/spec/audit 的预计算 SHA-256。
- `tests/test_c2_b5_legacy.py:85-100` 对实际完整 bytes 做 SHA-256 后与冻结字面量比较；fixture 不调用被测 hash helper生成 expected。
- `src/agent/correction/artifact_serialization.py:7-25` 是 version gate；finalize/writer/loader/pipeline 共用该 output serializer。

### B5-D6 protected-assets-clean — 完全交付（回归与资产面）

- B2b 回归由既有 `tests/test_c2_b5_host_resolution.py:637-919` 覆盖 rollback、room ownership、pre/post/final current-ring binding；E4 0/90/270 与 World/Relative 语义由 `tests/test_e4_relative_north_axis_e2e.py:120-186` 覆盖；本批 E4 host rebind 由 `tests/test_c2_b5_artifact_trust.py:267-283` 覆盖。
- `git diff -- case_tests tests/golden` 无输出；未改 GT、golden、verified overlay、face construction、Va wire/version、B5b、v1/v2 schema 或 C2 FacadeSegment validator。新增的 `tests/fixtures/c2_b5_legacy_window_byte_sha256.json` 是本批合成 byte-lock fixture，不是既有 protected golden。

## 2. 五笔必接债

1. **6 个 xfail 复原 — 完全交付。** `tests/test_output_coordinate_identity.py:308-492` 六条链改走生产 source→writer→accepted loader→proof→build/assembly，删掉 Phase D xfail；全仓只余 9 个 legacy golden xfail。
2. **MINOR-1 — 完全交付。** 删除 `build.py`/`geometry_validator.py` 的空字节伪 `VerifiedWindowResolverInputs`；改为 `src/agent/geometry/build.py:62-130` 的 proof-authenticated narrow view。`rg 'VerifiedWindowResolverInputs\(' src` 只剩 `window_sources.py` 内真 builder 构造。
3. **MINOR-2 — 完全交付。** `src/agent/pipeline.py:719-748,1172-1200` 将 proof 传入 build/check；`scripts/tool_scripts/run_stage.py:324-411,534-540` stepwise 各 build/assembly 消费同一 accepted proof。
4. **NIT-3 — 完全交付。** 新增 `src/agent/correction/artifact_serialization.py:7-30`，finalize、writer、loader、pipeline 共用 canonical output/feature serializer。
5. **NIT-4 — 完全交付。** 带窗 v1/v2 frozen byte identity fixture 与两版本测试已落。

## 3. 安全拒绝锁矩阵

`tests/test_c2_b5_artifact_trust.py` 的 pytest 参数项均为独立 test item；每项只 mutate 一个规定面。已交付：

| §13.6 项 | 锁 |
|---|---|
| #1 segment ref、#2 room、#3 span | `test_tamper_01_to_04_output_fields_fail_closed` 三个独立参数项 |
| #4 segment | `test_tamper_01_to_04_output_fields_fail_closed` 的 p1/p2/normal/visible/fingerprint 五个独立参数项 |
| #5 endpoint、#6 3D vertex、#7 t、#8 resolution digest、#9 aggregate、#10 output bind | `test_tamper_05_to_10_host_artifact_fields_fail_closed` 六个独立参数项 |
| #11 source identity | reading bytes、locator、manifest hash、direction fact 四个独立测试；攻击 fixture 重签普通 content/StageRecord hash后仍由 raw-source replay拒绝 |
| #12 StageRecord hash | `test_tamper_12_stage_record_artifact_hash_is_rejected` |
| #13 攻击者同步修普通 SHA | `test_tamper_13_self_consistent_output_sha_still_fails_relation_gate`：同步修 output/feature/evidence/hosts/record hash，独立 room/source relation 门仍拒 |
| #14 删除六件套任一件 | `test_tamper_14_each_missing_six_artifact_is_rejected` 六个独立参数项 |
| #15 E4 复用 base hosts | `test_tamper_15_orientation_cannot_reuse_base_window_hosts_bytes` |
| #16 caller forged result | `test_tamper_16_writer_rejects_caller_tampered_record_digest_before_attempt_exists` 只改一条 resolution digest，直喂 writer，attempt 不产生 |
| #17 finalize-symbol 对偶 | `test_tamper_17_finalize_symbol_patch_produces_fake_claims_but_writer_uses_true_root` 只 patch `finalize.resolve_window_hosts`；finalize 完整返回伪 digest，writer 的 module-qualified 真核仍拒 |
| #18 loader parse exception | `test_tamper_18_loader_parse_exception_never_returns_accepted_marker` |
| #19 parent internal exception | `test_tamper_19_parent_internal_exception_never_returns_build_geometry` |
| broad-except fail-open | `test_source_scan_has_no_broad_exception_fail_open_in_trust_boundaries` |

#1-#19 均按规定独立 test item/独立 mutate；#18/#19 均没有返回 accepted marker/build geometry。另有 zero-window v3 no-proof writer、accepted、integrated 三边界后门锁、producer audit room/span 两个 replay 锁及 rejected-root 隔离锁。

其它新增/改动测试：

- `tests/test_c2_b5_legacy.py`：16 个收集项（v1/v2 byte+semantic、snap、extras、clamp false、missing/no-parent、双路径全链）。
- `tests/test_output_coordinate_identity.py`：16 条 E4/output-coordinate 锁全部真绿，含原 6 个 xfail。
- `tests/test_run_pipeline_self_checks.py`：pipeline self-check stub 接受并核对 proof kwarg 接线。

## 4. §16 十条对抗面

1. **direction error 窄抛/三轮 fail closed：** `tests/test_c2_b5_host_resolution.py:802-919`；若吞错、沿用旧 ring 或回滚后继续即红。
2. **existence 零交与 Va 属性零交分权：** `tests/test_c2_b5_host_resolution.py:392-450,1078-1136`；错误 code/fallback 漂移即红。
3. **Va direction/identity mapper：** `tests/test_c2_b5_host_resolution.py:1290-1326`；VA-ERR4/5/未知 code 分支改坏即红。
4. **resolver input ring-free、每轮重派生：** `tests/test_c2_b5_source_routing.py:179-277` 与 host-resolution `:802-919`；持久化 ring-dependent 字段或复用 binding 即红。
5. **production helper/judge oracle parity：** `tests/test_c2_b5_source_routing.py:279-296` 使用 mirrored/axis-y 冻结 fixture；自指或 byte drift 即红。
6. **output/feature 真 hash 与 Va sidecar：** `tests/test_c2_b5_host_resolution.py:1192-1289` 加本批 tamper #9/#10/#13；占位/旧 hash 或 hash 环回潮即红。
7. **B2b transient copy 不泄漏 stale id：** `tests/test_c2_b5_host_resolution.py:637-835`；post ownership/parity 与 transaction leak 改坏即红。
8. **writer module-qualified root：** `tests/test_c2_b5_artifact_trust.py:95-183`；改回 finalize binding、相信 caller record 或让 patched finalize 共享 writer 根即红。
9. **legacy 入口分派、window pass 原位：** `tests/test_c2_b5_legacy.py:102-198`；把 window pass 提前、让 B5 extras改变 legacy、偷修 missing/no-parent 或双路径漂移即红。
10. **全链自报/fail-open：** artifact trust #1-#19、zero-window writer/accepted/integrated no-proof、embedded raw reauth、rejected-root 隔离、proof build 与 E4 stale-byte 全部有锁；任一便利 copy、自报 hash或 broad-except 逃逸即红。

## 5. 实测

最终 targeted（当前最终树）：

```text
$ python -m pytest -q tests/test_c2_b5_source_routing.py tests/test_c2_b5_host_resolution.py tests/test_c2_b5_parent_and_verts.py tests/test_c2_b5_artifact_trust.py tests/test_c2_b5_legacy.py tests/test_c2_b2_v3.py tests/test_output_coordinate_contract.py tests/test_output_coordinate_identity.py tests/test_run_pipeline_self_checks.py
284 passed, 1 warning in 9.27s
```

最终全仓（当前最终树）：

```text
$ python -m pytest -q
1427 passed, 9 xfailed, 146 warnings in 332.71s (0:05:32)
```

9 个 xfailed 均来自 `tests/test_validation_run_baseline.py` / `tests/test_orchestrate_baseline.py` 的既有 legacy golden rerecord 门；`tests/test_output_coordinate_identity.py` 已无 xfail。`git diff --check` 无输出。

## 6. 续作（主控退回五项）

1. **D1 writer 独立 replay + 硬禁后门 — 完全交付。** `src/agent/execution/stage_runner.py:185-197,259-382` 对所有 v3 强制真 B5 proof，从嵌入的 producer/manifest/readings 重跑 source helper、authoritative envelope 与 deterministic core，并逐项核 audit/claims；`correction_b2_v1` 仅余 v1/v2 路径。历史 direct v3 fixture 已在 `tests/b5_test_helpers.py`、`tests/test_c2_b2_v3.py:61-84` 迁到生产 builder 生成的空而经验证 marker。
2. **D2 accepted/integrated source reauth — 完全交付。** `src/agent/correction/window_sources.py:157-255,628-676` 的 self-contained artifact 携 raw manifest/readings；`src/agent/output_coordinates.py:440-455,519-585` 在 accepted/integrated 两边界强制 v3 B5 proof，并从 raw bytes 重算 locator/manifest/reading/direction facts。`verify_integrated_gate1_correction` 按 §12.3 冻结签名补齐两参且未超出冻结签名；accepted v3→B2 降级、签名与 raw tamper 独立锁均在 `tests/test_c2_b5_artifact_trust.py`。
3. **§10.3 rejected-report — 完全交付。** `src/agent/execution/correction_audit.py:17-64` 只扫描非 accepted、blocking attempts 并 strict parse typed conflict；两个 report consumer 已接入。`tests/test_c2_b5_artifact_trust.py:569-624` 锁真实 rejected reason、root 假 copy 不提升，以及坏 accepted resolution hash 不产成功报告。
4. **D4 legacy 全链锁 — 完全交付。** `tests/test_c2_b5_legacy.py:152-198` 分别锁 v1/v2 missing-room、no-parent 的当前错误/notes，并锁 integrated/stepwise 的 final geometry、proof、built、spec、audit 全项语义等价。
5. **§13.6 字面拆锁 — 完全交付。** `tests/test_c2_b5_artifact_trust.py` 已将 #4 的 p2/normal/visible/fingerprint、#11 的 locator/manifest hash/direction fact 拆为独立 mutate；#16 仅改一条 record digest 直喂 writer；#17 只 patch `finalize.resolve_window_hosts`，由 finalize 本身产伪 claims，再由 writer 独立 module-qualified 真核拒绝。

续作诚实状态：上述五项均为**完全交付**，没有部分交付或仍未竟项。

## 7. Promotion 与 review-ask

施工侧 §15.2 promotion 条件已逐项满足：D1-D6、五笔原始必接债、主控退回五项与对应安全拒绝锁均已落地；可以送 Fable 对抗审。**本轮无新的细稿歧义、签名冲突或 review-ask。**

本简报的 `COMPLETE` 指施工完成，不代替 Fable APPROVE 或主控 Opus 最终 `CLOSED` 裁决。

## 8. Fable r1 返工

### MAJOR-1 writer replay / totality 负锁 — 完全交付

- `tests/test_c2_b5_artifact_trust.py:316-339` 对 `original_room_id`、`original_span` 分成两个参数项：同时伪造 geom.corrections 与 audit_payload，并通过正式 serializer、`PreparedCandidateIdentity`、feature sidecar 和 evidence ledger 重建全部身份；攻击越过 `writer_audit_output_drift` 后稳定命中 `writer_window_audit_replay_drift`。
- `tests/test_c2_b5_artifact_trust.py:341-376` 双侧删除 host audit 行并重建身份；测试把上游 recompute helper 固定为已经验证的真 claims，以唯一到达并锁住 StageRunner 自身的 `writer_window_audit_totality_drift`，避免由上游同类 totality 校验代替本门覆盖。
- 活体自验：临时把 replay raise 换成 pass，新锁 **2 failed / DID NOT RAISE**；还原后两项绿。临时把 totality raise 换成 pass，新锁 **1 failed / DID NOT RAISE**；还原后绿。

### MAJOR-2 E4 host relation 守卫负锁 — 完全交付

- `tests/test_c2_b5_artifact_trust.py:643-699` 从 accepted base 构造 room 变体，重新计算 resolution/aggregate digest，形成可通过 Pydantic 严格校验且与 base 不同的 claims；proof 消费首次 recompute 保持真值，仅 enrichment recompute 注入变体，稳定命中 `changed the host relationship`。
- 活体自验：临时把 `orientation.py` relation raise 换成 pass，新锁 **1 failed / DID NOT RAISE**；还原后绿。

### MINOR / NIT 处置

- **MINOR-1 完全交付：** `tests/test_c2_b5_artifact_trust.py:725-754` 改为 AST 扫描七个 trust-boundary 文件，任何 `Exception`/`BaseException` handler（含 tuple/as 变体）均报文件与行号；无字面缩进逃逸。
- **MINOR-2 完全交付：** `tests/test_c2_b5_artifact_trust.py:389-436` 的 #1-#10 每个参数项均断言实际稳定错误串，区分 output/schema binding、resolution content hash、aggregate hash 与 artifact output identity。
- **MINOR-3 登记债：** 首个真实 v3 case run 必须核验 manifest-required readings 是否完整覆盖 `extract_authoritative_envelope` 实际消费的 `0_reading` 输入；若发现 manifest 外文件参与 envelope，须把该输入纳入受信 marker，禁止放松 writer replay。
- **NIT-1：** 按主控裁决维持两个冻结签名参数的 `=None` 默认，不改生产码；v3 缺参仍 fail closed。
- **NIT-2：** 简报措辞已统一改为“按 §12.3 冻结签名补齐两参、未超出冻结签名”。

返工诚实状态：2 MAJOR、2 建议 MINOR 与 NIT-2 均已落地；MINOR-3 已按裁决登记、NIT-1 按裁决维持。返工未修改任何生产码，三处临时 probe 均已原样还原，源码 `R1_PROBE`/`FABLE_PROBE` 零命中。本轮无 review-ask。
