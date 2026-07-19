# B5 Phase D 对抗审判词 r1(Fable,最高档跨厂商交叉审)

- 日期:2026-07-19
- 审者:Fable 5(冷启、独立上下文;只审不改生产码,全部探针改动已还原,树尾态 = 19 files / +1240 / -148 与开工快照逐字节一致)
- 被审:sol Phase D 施工(working tree 未提交态)
- 判定依据:`AI_agent/proposals/c2_b5_detail_spec.md` v3 定稿(唯一依据)+ 派工单 2026-07-19
- 独立实测:targeted **280 passed**(与 sol 自报一致);全仓 **1423 passed, 9 xfailed**(与 sol 自报一致,9 个均为 legacy golden rerecord 门,`test_output_coordinate_identity.py` 零 xfail)

---

## 0. 裁决

**REWORK**(2 MAJOR / 3 MINOR / 2 NIT)。

定性:**生产码信任根本体全部验真**——writer module-qualified 双根独立、replay 门、三边界 v3→B2 后门封口、legacy 字节层对改造前 HEAD 逐项相等,我全部亲手活体证实,**零生产码 bug**。两个 MAJOR 均为同一类:**生产安全门存在且活体咬合,但对应负锁测试缺失**——把门干掉后全仓/targeted 依旧全绿。按派工单铁律 4 与细稿 §14 尾「任何安全拒绝测试缺失视为 shipped-untested = 未交付」,不得以总绿数代替,故判 REWORK。预期修复面极窄:**纯补测试锁,零生产码改动**;返工后可直接复审通过。

---

## 1. Findings

### MAJOR-1 — writer audit replay 门与 totality 门无锁(shipped-untested)

- **细稿依据**:§5.3(audit `original_span` 冻结口径:「Phase D writer 校验本字段时必须从 `producer_draw_canonical_bytes` fresh parse 并 replay 同一确定性 snap,再与 audit 比较」)+ §9.1 + §14 尾;派工单铁律 4。
- **生产码现状(门是真的)**:`src/agent/execution/stage_runner.py` B5 写者块确实从嵌入 raw sources 重放 producer→`extract_authoritative_envelope`→`apply_deterministic_core`,逐窗比较 `original_room_id/original_span/resolved_*/branch/digest`(`writer_window_audit_replay_drift`),并做 audit/replay/claims 三集合 totality(`writer_window_audit_totality_drift`)。
- **活体探针(攻击侧,证门真)**:我构造了**全自洽伪造攻击**——同时篡改 `geom.corrections` 与 `audit_payload` 的 `original_span`、用公开 API 重建 output bytes + `PreparedCandidateIdentity` + evidence ledger(全部 hash 自洽、audit↔output 一致门可过),直喂 writer → **REJECTED: `writer_window_audit_replay_drift`**。门在生产码里真实咬合(探针脚本存档 scratchpad `probe_replay_gate_attack.py`)。
- **活体探针(锁侧,证无锁)**:
  - 把 `raise ValueError("writer_window_audit_replay_drift")` 换成 `pass` → **targeted 六文件 181 passed 全绿**,无一变红;
  - 把 `raise ValueError("writer_window_audit_totality_drift")` 换成 `pass` → **98 passed 全绿**。
- **简报自证不实处**:简报 §1-D1/§3 称「原始 room/span audit 两个 replay 锁 = `test_d1_writer_rejects_caller_tampered_original_audit_replay_fields`」。实测该测试(只改 audit_payload、不改 geom)在**上一道** `writer_audit_output_drift`(audit↔output 一致性门)就红了,match 串就是 `writer_audit_output_drift`——**从未到达 replay 门**。该测试是真锁,但锁的是另一道门;replay 门本体零覆盖。
- **修法**:补两条负锁(纯测试):① 按我的攻击探针写一条「双侧一致伪造 original_span/original_room + 重建 identity」直喂 writer,断言 match=`writer_window_audit_replay_drift`;② 一条删/增一行 window_host_resolution audit 行(双侧一致 + identity 重建),断言 match=`writer_window_audit_totality_drift`。

### MAJOR-2 — E4「host 关系逐值不变」守卫无锁

- **细稿依据**:§9.4#2(「enrichment 只可改 north_axis 与 orientation audit;room/ref/span/host audit 逐值保持」)+ §13.8(「B5 base→orientation enrichment:host关系逐值不变」)。
- **生产码现状**:`src/agent/correction/orientation.py:529` `if host_claims != base_hosts.claims: raise ValueError("B5 orientation enrichment changed the host relationship")` ——这是唯一一道 vs-BASE 的关系防线。writer 复算不能替代它:writer 只验 result **内部**自洽,若未来 enrichment 代码漂移真改了 relation 并自产一致 claims,writer 照收。
- **活体探针**:把该 raise 换成 `pass` → `test_c2_b5_artifact_trust.py` + `test_output_coordinate_identity.py` + `test_output_coordinate_contract.py` **88 passed 全绿**。`test_tamper_15` 锁的是 hosts **bytes 复用**(#15,output hash stale),不是 relation 变更。
- **修法**:补一条负锁(纯测试):monkeypatch/注入让 enrichment 路径中 `recompute_window_host_claims` 返回与 base 不同的合法 claims(或对 base 构造 room 变体),断言 `finalize_orientation_enrichment` raise match=`changed the host relationship`。

### MINOR-1 — broad-except 源扫描锁近乎恒真

- **依据**:§13.6 尾「source scan 锁定 resolver/writer/loader 无 broad-except fail-open」。
- **事实**:`test_source_scan_has_no_broad_exception_fail_open_in_trust_boundaries` 只断言两个**字面模式**缺席(`"except Exception: pass"`、`"except Exception:\n        return"`)——任何缩进/写法稍异的 broad-except 都逃逸,锁几乎恒真。我独立 grep 证实 `window_host.py / stage_runner.py / output_coordinates.py / build.py / modelling.py / window_sources.py / orientation.py` 现实**零** `except Exception`,底层是干净的(故不判假绿掩真洞)。
- **修法**:改为断言 `"except Exception"` 子串整体缺席(必要时白名单注明行),或 AST 扫描 handler 类型。

### MINOR-2 — §13.6 #1–#10 参数化 tamper 项断言裸 `ValueError` 无 match

- **依据**:§13.6「每项必须断言稳定gate/error」。
- **事实**:`test_tamper_01_to_04_output_fields_fail_closed` 与 `test_tamper_05_to_10_host_artifact_fields_fail_closed` 均 `pytest.raises(ValueError)` 无 match。且 #1–#4(output 面八个 mutate 项)实际统一由 `window_hosts.output_sha256` 绑定门/artifact content 自校验拦截,并非逐字段关系门(逐字段关系门由 #13 再签名攻击真正锁住——#13 本身扎实)。单独-mutate、fail-closed 两点满足细稿,唯断言稳定性欠奉:未来若拒绝理由漂移成别的 ValueError(如误配置),测试无从分辨。
- **修法**:逐参数项补 match 串(至少分组:绑定门/内容自校/关系复算)。

### MINOR-3 — writer replay 的可用性前提未经真实 run 验证(登记项,非本批扣分)

- **事实**:writer replay 只从**嵌入 marker 的 manifest-required readings** 重建 envelope(temp dir 只落 `expected_output_id.json`);而 finalize 生产路径 `extract_authoritative_envelope(vector_dir,...)` 面向整个 reading 目录。若真实 v3 run 的 `0_reading/` 存在 manifest 之外、但参与 envelope 提取的文件,replay 将与 finalize 结果分歧→writer **误拒合法 attempt**(fail-closed 方向,非安全洞)。另 replay 的 `capability_profile` 取自 caller 的 `report.capability_profile`(选错只会拒,不会放)。
- **修法**:首个真实 v3 case run 时验证;若命中,按细稿口径把 envelope 输入并入受信 marker,不得放松 replay。

### NIT-1 — `verify_integrated_gate1_correction` 两个新参带 `=None` 默认

§12.3 冻结签名列出两参但未含默认。v3 忘传 → raise(fail-closed),v1/v2 需 None,安全无虞;但与「pipeline 与 stepwise 不得各包一个默认」精神有微张力。`test_d2_integrated...` 已锁参数名序(inspect.signature)。可保持现状或去默认。

### NIT-2 — 简报措辞「integrated 唯一准签名未增加任何参数」易误读

实际新增了两个参数——它们**在 §12.3 冻结签名之内**,简报实义是「未超出冻结签名」。措辞应改「按 §12.3 冻结签名补齐两参」。无实质问题。

---

## 2. 活体探针清单

### 改坏变红 = 真锁(全部已还原)

| 探针 | 干掉的生产防护 | 结果 |
|---|---|---|
| M1 | writer `writer_window_host_claims_drift` raise | tamper_16 + tamper_17 **双红** ✅ |
| M2 | writer「v3 必带四 B5 字段」raise | `test_d1_writer_rejects_v3_with_all_b5_fields_missing_even_zero_window` **红** ✅ |
| M3 | accepted loader v3 contract B5-only 门(放宽回 B2/E4) | `test_d2_accepted_loader_rejects_v3_record_downgraded_to_b2_without_proof` **红** ✅ |
| M4 | integrated「v3 必带双 sidecar」raise | `test_d2_integrated_reauthenticates...` **红** ✅ |
| M6 | legacy serializer 的 B5-only extras pop | `test_d4_legacy_ignores_v3_only_window_extras` **4 红**(byte fixture 同红)✅ |
| M8 | report `resolution hash mismatch` raise | `test_d3_report_blocks_bad_audit_resolution_hash` **红** ✅ |

### 改坏仍绿 = 无锁(即 MAJOR-1/2)

| 探针 | 干掉的生产防护 | 结果 |
|---|---|---|
| M9 | writer `writer_window_audit_replay_drift` raise | targeted 六文件 **181 passed 全绿** ❌ |
| M9b | writer `writer_window_audit_totality_drift` raise | **98 passed 全绿** ❌ |
| M7 | E4 `changed the host relationship` raise | 三文件 **88 passed 全绿** ❌ |

### 独立攻击/独立性探针(生产码方向,全 PASS)

1. **双根独立(§16#8/§13.6#17 对偶)**:在真结果构造完成后,把 `finalize.resolve_window_hosts` 模块绑定替换为 bomb(`raise AssertionError("hijacked")`),直接跑 StageRunner 写者 → **正常 accepted,bomb 未触发**。writer 的 `from src.agent.correction import window_host as window_host_module` 复算根与 finalize 符号确无共享劫持点。sol 的 test_tamper_17(patched finalize 产伪 claims、writer 真核拒)+ 我的 M1 双红 + 本探针三面互证。
2. **replay 门攻击**:全自洽伪造 original_span(双侧改 + 公开 API 重建 output/identity/evidence)→ writer `writer_window_audit_replay_drift` 拒。门真,缺的只是锁(见 MAJOR-1)。
3. **legacy 字节层 vs 改造前**:`git stash` 切回 HEAD(pre-Phase-D),用 HEAD 自己的 API(`model_dump_json(indent=2)` + Phase C versioned serializer)重算 v1/v2 output/build/spec/audit 四件 SHA-256 → 与 `tests/fixtures/c2_b5_legacy_window_byte_sha256.json` **逐项相等**;Phase D 树重算亦逐项相等。fixture 不是「跑当前代码自冻结」,是真·改造前字节基线。§13.7/§15.1 第 2 层坐实(version gate = `serialize_correction_output` 对 v1/v2 剥 B5-only extras,M6 锁真)。
4. **fail-open 现实核**:grep 七个信任链文件零 `except Exception`(锁本身弱,见 MINOR-1)。`pipeline.materialize_kernel_geometry` 的既有 advisory broad-except 后 `bg is None` → pipeline 硬 `raise RuntimeError`、stepwise 落 INVARIANT fail,不构成 fail-open。
5. **写者原子性**:B5 attempt 先写 `attempts/.NNN.*` 隐藏 temp dir、六件回读 strict validate 后 `os.replace`;`next_attempt_index` 只认纯数字目录名,temp 目录不占号;tamper_16/audit-replay 测试均断言失败后 `attempts/` 不存在。

---

## 3. §16 十条逐条 verdict

| # | 条目 | verdict | 探针/证据指针 |
|---|---|---|---|
| 1 | direction 两 code 窄抛、三处转 typed invariant | PASS | Phase B 锁 `test_c2_b5_host_resolution.py:802-919`,本批未触碰该面,全仓绿 |
| 2 | existence 零交 vs 属性零交分权、漂移升级 va_identity | PASS | Phase B 锁 `:392-450,1078-1136`,未触碰 |
| 3 | VA-ERR4/5 独立锁、identity fallback 恒 invariant | PASS | Phase B 锁 `:1290-1326`,未触碰 |
| 4 | resolver input 排除 ring 五字段、每轮重派生 | PASS | wire 无 ring 字段;本批 loader/writer 每边界经 `verify_window_resolver_inputs_artifact` **fresh 重派生 direction facts**(不信持久化 tuple,`derive_manifest_direction_facts` 对非 building-axis fail closed);tamper_11_direction_fact(re-sign 后仍拒)真锁 |
| 5 | helper/judge parity 冻结 fixture 无自指 | PASS | Phase A 锁 `test_c2_b5_source_routing.py:279-296`,未触碰 |
| 6 | hash 环解除、ledger 只用真实 output/feature hash | PASS | `_verify_b5_bundle` + writer 步骤 1/4 逐字节;tamper #9/#10/#13(再签名攻击仍拒)/#15;evidence 恒侧车不回写 output |
| 7 | B2b transient copy 不回写 stale id/binding | PASS | Phase B 锁 `:637-835`,未触碰 |
| 8 | writer module-qualified 复算不受 finalize patch 影响 | **PASS(亲证)** | 独立 bomb 探针 + tamper_17 + M1 双红 |
| 9 | legacy 只在入口决策、window pass 原位 | PASS | `deterministic.py` 本批零改动;`test_d4_window_pass_stays_after_structural_snap`(snap 后边界 clamp 的手写字面量)+ 字节 fixture 对 HEAD 相等 |
| 10 | 全链无自报信任/fail-open | **PARTIAL** | 三边界后门封口验真(M2/M3/M4 红)、#18/#19 无 accepted/geometry、loader 双重认证(嵌入 bytes 自洽 + 绑 run 真实 `_run/view_manifest.json`/`0_reading` 原件,tamper_11 系列真锁)——但 **writer replay/totality、E4 relation 三门无锁 = MAJOR-1/2**;源扫描锁弱 = MINOR-1 |

---

## 4. 6 xfail 复原核验

**真生产链,无手搓假 proof。** `tests/test_output_coordinate_identity.py` 六条链现:生产 builder `build_verified_window_resolver_inputs`(synthetic manifest+readings)→ `finalize_correction_draw(verified marker)` → StageRunner 写六件套(并落 `_run/view_manifest.json` + `0_reading/` 原件供 loader 重认证)→ `load_verified_accepted_correction` 全验后签发 `window_host_proof` → E4 enrichment(B5 分支)→ 二次写 `correction_b5_orientation_v1` → `build_geometry(proof)` → assembly。v3 build 强制门未被绕过(proof 均来自 verifier token seam,非裸构造;`VerifiedWindowHostProof.__init__` token 门在)。xfail 标记六处全删;全仓仅余 9 个 legacy golden xfail(`test_validation_run_baseline.py`/`test_orchestrate_baseline.py`),无任何指向 Phase D 的 xfail。✅

MINOR-1 债(伪 marker)同步收回:`rg 'VerifiedWindowResolverInputs('` 生产侧仅 `window_sources.py` builder 一处;`build.py`/`geometry_validator.py` 改走 `_ArtifactAuthenticatedResolverInputs` 窄视图,且只能从已验 proof 签发。MINOR-2 债(pipeline/run_stage proof 双路径)接通,`resolve_unique_window_host` 生产侧已灭。NIT-3 债:`artifact_serialization.py` 单一 serializer,finalize/writer/loader/validator/pipeline 五处共用,验证于 M6。

---

## 5. 主控裁决落地核验(v3→B2 后门三边界)

| 边界 | 防护 | 破坏探针 | verdict |
|---|---|---|---|
| writer | v3 FinalizeResult 四 B5 字段全非空,含零窗;缺任一 → raise,attempt 目录不产生 | M2 → 红 | ✅ |
| accepted loader | v3 contract 仅 `correction_b5_v1/correction_b5_orientation_v1`;降级成 B2 + 删双 sidecar → `v3 B5 proof requirement` 拒 | M3 → 红 | ✅ |
| integrated | v3 缺双 sidecar → raise;单缺一份 → raise | M4 → 红 | ✅ |
| 历史 fixture 迁移 | `tests/b5_test_helpers.py` 用**生产 builder** 造零窗真 marker(synthetic manifest 走 `ViewManifest` 正门),`test_c2_b2_v3.py` 全量迁移,断言改为 B5 六件套 | 独立复跑全绿 | ✅ |

注:orientation.py 仍保留 `correction_b2_v1` base 分支(§9.4「历史 replay」),其产物无 B5 字段 → writer 必拒,生产不可达;非逃逸口。accepted loader 现对**历史** v3 B2/E4 attempts 也硬拒——此为裁决口径的直接后果(信任根优先于历史可读),如实登记。

---

## 6. 实测输出

targeted(判词前末轮复跑,探针全还原后):

```text
$ python -m pytest -q tests/test_c2_b5_source_routing.py tests/test_c2_b5_host_resolution.py tests/test_c2_b5_parent_and_verts.py tests/test_c2_b5_artifact_trust.py tests/test_c2_b5_legacy.py tests/test_c2_b2_v3.py tests/test_output_coordinate_contract.py tests/test_output_coordinate_identity.py tests/test_run_pipeline_self_checks.py
280 passed, 1 warning in 8.11s
```

全仓(独立复核,与 sol 自报一致):

```text
$ python -m pytest -q
1423 passed, 9 xfailed, 146 warnings in 307.35s (0:05:07)
```

树尾态:`git status --short` 27 行、`git diff --stat` = 19 files / +1240 / -148,与开工快照一致;无探针残留(`FABLE_PROBE` 零命中)。

---

## 7. 返工要求(REWORK 出口条件)

1. **MAJOR-1**:补 writer replay 门与 totality 门两条负锁(攻击构造见 §1,match 串锁 `writer_window_audit_replay_drift` / `writer_window_audit_totality_drift`);
2. **MAJOR-2**:补 E4 relation 守卫负锁(match `changed the host relationship`);
3. MINOR-1/2 建议同轮顺手落(扫描锁实化 + tamper 参数项 match 串),不强制阻断;
4. 全部为测试新增,**不得改生产码**;若返工中发现需改生产码,须单列 review-ask。
