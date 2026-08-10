# 执行日志 · F-20：`validate_case` 接通 v3 accepted proof

- **席位**：Claude 侧 Sonnet（执行档）· 通道 = Agent 子代理
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `efb8080`（施工全程未 commit）
- **派工单**：[`2026-08-10_f20_fix_dispatch_claude.md`](../request/2026-08-10_f20_fix_dispatch_claude.md)
- **设计权威**：[`proposals/f20_validate_case_v3_proof_design.md`](../../../proposals/f20_validate_case_v3_proof_design.md)（sol 出稿，orchestrator 两轮对抗审 APPROVE）

---

## §0 防假验证自检（开工前作答，逐字保留）

**1. 验收路径真的会执行到 `validation_run.py` 里我改的那一段吗？**
会，且已排除假验证温床：Acceptance③直接对一份真实产物调用 `validate_case(run_dir, policy=...)`
（不经 `--intake-from`/`DOWNSTREAM_ONLY`），Acceptance①②④⑤同样都是直调 `validate_case`/`approve_geometry`，
零一处走跳段入口。`DOWNSTREAM_ONLY` early return（`validation_run.py:94-97`）在 resolver 之前，本单未移动。

**2. 我的锁的夹具，`schema_version` 真的是 `"3"` 且 `artifact_contract` 真的是 B5 吗？**
是。`_accepted()`/`_bundle()` 产出 `CorrectedGeometryV3`（`schema_version="3"`），
`record.artifact_contract == "correction_b5_v1"`（L3/L4 里直接断言过）。

**3. 我怎么证明「不加我的修法，每一把新锁都是红的」？**
两条独立证据：① 全部 12 把新锁在生产码改动前跑过一次，`11 failed`（含全部 L1-L8 + NIT-1 两个变体之一，
详见下方"§1 定向红实测"；第 12 把锁——NIT-1 的 legacy-schema 变体——是 neuter 阶段才补的，见 §4）；
② 每把锁自身在断言负向结果前，先断言正向对照 PASS + digest 非空（design §4 硬性要求），
该正向对照本身在修法前也是不可达的（同一个 StopIteration，因为 check_id 根本不存在）。

**4. NIT-2 那块砖我先验了吗？**
验了，且是本单第一个动作（见 §1）：`_bundle()` 本来就有 `include_window` 参数，
`_accepted()` 只需透传即可产出零窗 v3 accepted attempt，`/tmp` 探针实测 `built.windows == []`。
**可行 ⇒ 未触发合法退出口，继续施工。**

---

## §1 NIT-2 验证（本单第一个动作）

在 `/tmp/.../probe_nit2.py` 里手工复刻 `_accepted()` 的写法、把 `include_window=False` 传给
`_bundle()`，验证输出：

```
ACCEPTED ATTEMPT FILES: ['audit.json', 'checks.json', 'feature_states.json', 'output.json', 'window_hosts.json', 'window_resolver_inputs.json']
record.artifact_contract: correction_b5_v1
verified.window_host_proof is not None: True
built.windows: []
ZERO-WINDOW V3 ACCEPTED ATTEMPT: SUCCESS
```

⇒ `_accepted(tmp_path, *, include_elevation=..., include_window=True)` 只需加一个透传参数
（`tests/test_c2_b5_artifact_trust.py:39-40`），不需要改 `_bundle()` 本身。**可行，继续。**

---

## §2 改动清单

### 2.1 `src/agent/execution/validation_run.py`（生产码，唯一功能性改动）

- 模块级新增 import：`ensure_corrected_geometry`、`RunManifestV2`、`load_run_manifest`、
  `load_verified_accepted_correction`（原先都是函数内局部 import 或压根没被 validate_case 用过）。
- 新增 `_TRUST_CHECK_ID = "correction.accepted_artifact_trust"`、
  `_CorrectionSource` dataclass、`_resolve_legacy_stage_root(...)`、`_resolve_correction_source(...)`
  —— 三态 resolver，逐态对应设计稿 §2.2 状态表：
  - 无 manifest / V1 manifest → `_resolve_legacy_stage_root`：schema v1/v2 走原样 stage-root 路径
    （`NOT_APPLICABLE`）；schema v3 → `FAIL`（无信任源）。
  - manifest 存在但 JSON/版本解析失败（`load_run_manifest` 抛 `ValueError`）→ `FAIL`
    （**NIT-1**：显式捕获，不落入"当无 manifest"分支）。
  - V2 manifest → 调 `load_verified_accepted_correction`；`ValueError` → `FAIL`；
    其余异常 → `ERROR`（**L8**）；成功则 `PASS`，`window_host_proof`/`window_evidence`
    取自已验真的 accepted attempt（B5 走 `WindowHostsArtifactV1.evidence`，legacy 走 `None`）。
- `validate_case(...)` 主体：`1_correction` 块改为先调 resolver 拿 `source`；
  `source.geom is not None` 时才调 `check_correction(..., window_host_proof=, window_evidence=)`，
  否则造一个只含 trust 行的空报告；trust check 结果**总是**追加进该报告；
  `source.trust_status in (FAIL, ERROR)` 时 `geometry_consistent=False` 且**完全跳过**
  `build_geometry`/`check_kernel`/S3 serializer（不写 `2_modelling` report，不产 digest，
  不落入 generic "kernel build failed" 桶）；否则原子性地把 `source.window_host_proof`
  同时传给 `build_geometry` 与 `check_kernel`（两处，一次改动）。
- **未改**：`DOWNSTREAM_ONLY` early return 位置、`stage_runner.py`、`build.py` 的 v3 强制 proof 门、
  `output_coordinates.py` 信任根算法、snapped required-artifact guard、两条历史注释、
  `validation_manifest.json` 独立文件名 —— 逐条核对过派工单 §1 明确禁止清单，零触碰。
- 新检查**只**出现在 `1_correction` 报告里，从未写入 `2_modelling`（design §2.3 铁律，逐字遵守）。

### 2.2 `tests/test_c2_b5_artifact_trust.py`（测试，主体）

- `_accepted()` 加 `include_window: bool = True` 透传给 `_bundle()`（向后兼容，19 处既有调用零改动）。
- 新增 12 把锁（L1 参数化 with/zero-window 算 2 条）：
  `test_f20_l1_v3_accepted_proof_reaches_validate_case[with-window/zero-window]`、
  `test_f20_l2_tampered_accepted_output_is_fail_closed_no_stage_root_fallback`、
  `test_f20_l3_missing_six_artifact_file_is_fail_closed`、
  `test_f20_l4_v3_downgraded_to_non_b5_contract_is_fail_closed`、
  `test_f20_l5_stage_root_convenience_copy_tamper_does_not_affect_v2_authority`、
  `test_f20_l6_legacy_no_manifest_and_v1_manifest_continue_to_be_auditable`、
  `test_f20_l7_v3_geometry_under_legacy_manifest_state_is_fail_closed`、
  `test_f20_l8_unknown_resolver_exception_is_error_not_fail`、
  `test_f20_nit1_unparseable_manifest_is_fail_closed_not_treated_as_no_manifest[invalid-json/unknown-version]`、
  `test_f20_nit1_legacy_schema_manifest_unreadable_is_fail_closed_not_masked`（neuter 阶段补的第 12 把，见 §4）。
- 每把锁开局先调共享 helper `_assert_direct_no_proof_entry_points_still_fail(bundle)`
  （断言直连 `build_geometry`/`check_correction`/`check_kernel` 三个入口在无 proof 时仍照旧拒绝——
  这是修法前就有的 v3/B5 合同，F-20 不碰它），然后用 `_write_canonical_2_3()`
  （**只调用** `building_geometry_json`/`geometry_specs_markdown`/`serialize_geometry`，
  不手写坐标）生成 2/3 产物，再断言干净对照 `trust PASS` + `digest 非空`，最后做单一变异。
- 夹具走 `_accepted()`/`StageRunner.record(...)` 造真实 accepted attempt（F-5 纪律）；
  L6/L7/NIT-1-legacy 用 `_write_legacy_stage_root`/`_write_legacy_v2_accepted` 构造程序化的
  legacy-schema 场景（同样不手写坐标，走 `build_geometry`+canonical serializer）。

### 2.3 `tests/test_check_parity.py`

- `_EXCLUDED_VALIDATE_CHECKS` 具名新增 `("1_correction", "correction.accepted_artifact_trust")`
  （design §3.3 要求的格式，逐条具名解释，未用前缀/整 stage 批量豁免）。

### 2.4 `tests/test_run_pipeline_self_checks.py`（施工中新发现的连带缺口，已修）

- `test_run_pipeline_inline_reports_match_validate_case` 独立维护了一份"inline 报告 vs
  `validate_case(write_reports=True)` 报告"逐状态比对，不经过 `test_check_parity.py` 的豁免表
  ⇒ 加新检查后原样会红。修法 = 在比对前 `pop()` 掉这一个 check_id 并显式断言其值为
  `not_applicable`（同一豁免理由，写在注释里），不改其余比对逻辑。

---

## §3 §0 自证前提：定向红实测（生产码改动前）

```
$ python -m pytest -p no:cacheprovider -q tests/test_c2_b5_artifact_trust.py
11 failed, 45 passed in 17.03s
```

11 把新锁全部因 `_trust_row(...)` 的 `StopIteration`（check_id 尚不存在）而红，
45 把既有锁不受影响（`_accepted()` 的 `include_window` 透传是向后兼容的默认参数）。

---

## §4 逐把锁 neuter（`/tmp` 独立副本，未碰工作树；仅 `src/` + `tests/` + `pyproject.toml` + `data/` 最小拷贝）

| 变异 | 恰好红的锁 | 连带 / 该红没红 |
|---|---|---|
| **① 整段回退到修法前的 `validate_case`** | 全部 12 把新锁（与 §3 定向红逐字一致），零连带到 45 把既有锁 | 无 |
| **② fail-open：trust BLOCK 后仍回退读 stage-root 重建** | L2 / L3 / L8（三把都断言 `"2_modelling" not in res.reports`） | **该红没红**：L4/L5/L6/L7/NIT-1 未变红——因为这几把锁的"digest 必须为 None"结论在此变异下**恰好仍然成立**（fallback 重建在无 proof 时自己也会抛 `ValueError`，被外层 `except` 兜成一份新的 `2_modelling ERROR` 报告，digest 计算的 `"2_modelling" in res.reports and ....passed` 门槛照样拦住）——即这几把锁对这个具体变异**不敏感**，不是假锁，是断言粒度只覆盖了"digest 是否为空"没覆盖"是否越权碰了 stage-root"。已如实记录，未回去加固（不在派工单要求范围内，且 L2/L3/L8 已经独立覆盖了这条防线）|
| **③ NIT-2 后门：零窗时不传 proof（`if not geom.windows: proof=None`）** | L1[zero-window] 单独红，L1[with-window] 绿 | 无连带，精准命中防的就是这个后门 |
| **④ 撤掉 `test_check_parity.py` 的具名豁免** | `test_run_pipeline_and_validate_case_check_id_parity` 红 | 无连带；`test_run_pipeline_self_checks.py` 那把独立豁免不受影响（各自维护各自的豁免，互不依赖） |
| **⑤ NIT-1 fail-open：manifest 解析异常时静默当"无 manifest"** | **仅** `test_f20_nit1_legacy_schema_manifest_unreadable_is_fail_closed_not_masked`（新补的第 12 把）红；原有 `test_f20_nit1_unparseable_manifest_is_fail_closed_not_treated_as_no_manifest`（v3 夹具）**保持绿** | **⛔ 该红没红，已现场修复**：v3 夹具下，即使"manifest 解析失败"分支被抹掉、静默当成"无 manifest"，`_resolve_legacy_stage_root` 自己的"v3-under-legacy 必须 FAIL"检查**独立地**也会把结果判成 FAIL——两条独立防线在 v3 夹具上产生了相同的表面结果，把 NIT-1 分支本身有没有被移除这件事**遮住了**。发现后补了一把 legacy-schema（非 v3）变体的锁（`_write_legacy_v2_accepted`），该场景下没有第二条防线兜底，能单独定位到 NIT-1 分支本身。补锁后重跑同一变异 ⇒ 新锁精确变红、其余 57 把不受影响；恢复修法后 58 把全绿。 |
| **⑥ 危险中间态：kernel/build 传 proof，唯独 `check_correction` 传 `None`（design §5 标"最危险"那行）** | L1 两个参数化全红（`res.reports["1_correction"].passed` 断言处），其余锁不受影响 | 无连带，精准命中 |
| **⑦ 危险中间态：`check_kernel` 单独不传 proof** | L1×2 / L2 / L3 / L4 / L5 / L6 / L7 共 8 处红（因为它们共用的"干净基线 digest 非空"前提被打破，先在预检处就红） | **有连带，且是预期内的连带**：这条变异会让"干净基线也拿不到 digest"，属于所有依赖该前提的锁应该一起变红的正确行为，不是假锁；L8 不受影响（它的干净基线不断言 digest） |

**全部 neuter 完成后已确认恢复修法 ⇒ 58 把新锁全绿、45 把既有锁不受影响**（`/tmp` 副本内验证，工作树全程未被 neuter 触碰）。

---

## §5 验收结果（原始汇总行）

### ①独立全量

```
$ python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20_full.log 2>&1; echo $? > /tmp/f20_full.rc
2356 passed, 10 xfailed, 209 warnings in 480.72s (0:08:00)
$ cat /tmp/f20_full.rc
0
```
（2345 基线 + 11 把锁 = 2356，此为补第 12 把锁之前的中间数字；补锁后见下方"补锁后终值"。）

### ②逐把锁 neuter

见 §4 表格。

### ③真实产物验收（`/tmp` 只读副本，未碰真实 run）

对 `case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify` 只读拷贝调 `validate_case`：

```
1_correction trust row: PASS - V2 accepted attempt supplies a verified B5 window host proof
2_modelling passed: True
  kernel.window_parent_binding: PASS
geometry_digest: 3409f90b9b8000092127875e0209767ab559ee818879ddc6af0b406dc704f4be
```

`approve_geometry(run_dir, actor=..., timestamp=...)` 真实签发：

```
GeometryApproval(digest='3409f90b9b8000092127875e0209767ab559ee818879ddc6af0b406dc704f4be', ...)
```

`res.blocked=True` 仍然存在，但原因只剩该 run 本就没跑到 `4_mep`/`5_intakeoutput`
（这份 run 停在 `3_split_pairing`）+ 拷贝副本缺 `case_data`——均与 F-20 无关，非新增。

### ④legacy 不回归

两个 golden 正基线（`sm20_anchor/run_2026-06-15_baseline`、`sm21_anchor/run_2026-06-16_opus_e2e`）：
用 `git archive HEAD`（只读快照，不碰工作树/不抢 git 锁）取修前代码单独验证一次，
再用工作树（修后）代码验证一次，**两者 `blocked`/`blocking_summary`/`geometry_digest` 逐字节相同**
（均 `geometry_digest: null`，阻断原因也完全一致，未新增任何 blocker）。

盘上 11 份 V1 账本 run 全部走 legacy 分支、零异常（其中 4 份因 `1_correction/` 目录本就不存在，
`trust=None` 即整个 1_correction 块未触发——与修前行为一致；其余 7 份得到
`NOT_APPLICABLE / "run manifest is V1 (grandfathered legacy)..."`）。

### ⑤V2 legacy targeted replay

对 4 个有 `1_correction` accepted 记录的 V2 run 做完整 replay 对比（修前 via `git archive`
只读快照 / 修后 via 工作树）：

| run | schema | 修前 digest | 修后 digest | 变化 |
|---|---|---|---|---|
| `run_2026-08-05_probe_a_legacy_snapped` | legacy | `null` | `null` | 无（阻断原因逐字相同） |
| `run_2026-08-06_wall3_a_retest` | legacy | `null` | `null` | 无（阻断原因逐字相同） |
| `run_2026-08-07_f13_e2e_verify` | legacy | `bed87c03e4c9...` | `bed87c03e4c9...` | **逐字节相同** |
| `run_2026-08-09_f18_e2e_verify` | v3 | `null`（kernel build failed） | `3409f90b9b80...` | **预期内变化**（F-20 本身要修的那个缺陷） |

三个 legacy run 零行为变化（含一个有真实 digest 的，逐字节相同），只有 v3 那个按设计变化。

---

## §6 补锁后终值（收尾前最后一次全量，覆盖 12 把锁的最终状态）

```
$ python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20_full_final.log 2>&1; echo $? > /tmp/f20_full_final.rc
2357 passed, 10 xfailed, 209 warnings in 431.43s (0:07:11)
$ cat /tmp/f20_full_final.rc
0
```

（2356 → 2357：补的第 12 把锁——`test_f20_nit1_legacy_schema_manifest_unreadable_is_fail_closed_not_masked`
——未改生产码，只在 `tests/test_c2_b5_artifact_trust.py` 追加一个新测试函数，零回归。）

---

## §7 没能确定 / 未完成的部分

1. **neuter②（fail-open）暴露的锁粒度缺口未回填**：L4/L5/L6/L7/NIT-1 对"trust BLOCK 后是否越权碰了
   stage-root"这个具体维度不敏感（见 §4②）。L2/L3/L8 已经独立覆盖这条防线，我判断**不需要**为
   每把锁重复断言，但如实登记，未擅自决定这就是"够了"——这属于锁粒度设计判断，非派工单要求，
   如需加固应另开小改动。
2. **sol 设计稿 §8 五条"没能确定"中，第 4 条（历史 V2 legacy run 是否都满足 stage-root==accepted
   逐字节相同）本单未重新普查全部 22 份 V2 账本**——只对派工单点名的 4 个有 accepted 记录的做了
   targeted replay（Acceptance⑤），其余 18 个无 `1_correction` accepted 记录的 V2 run 不受
   本次改动影响（resolver 会在无 accepted 记录时经 `load_verified_accepted_correction` 抛
   `ValueError` → FAIL，这是 F-20 明确要的新行为，不是"未变化"）。
3. **F-21 候选（`approve_geometry` 只看 digest 不看 `res.blocked`）严格按派工单 §6.5 未碰**，
   在 Acceptance③ 中亲眼看到它签发了一个 `res.blocked=True` 的 run 的检查点，如实记录、未顺手改。
