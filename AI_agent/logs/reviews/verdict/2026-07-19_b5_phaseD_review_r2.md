# B5 Phase D 对抗审判词 r2(Fable,聚焦复审 sol 返工 delta)

- 日期:2026-07-19
- 审者:Fable 5(同 r1 会话延续;只审不改生产码,全部探针改动已还原,零残留)
- 范围:仅验 r1 REWORK 出口条件的返工 delta;r1 已活体验真的信任根本体(writer 双根独立、三边界后门封口、legacy 字节层 vs HEAD、6 xfail 生产链)**不重跑、结论沿用**
- 判定依据:r1 判词 §7 返工要求 + 细稿 v3

---

## 0. 裁决

**APPROVE**。

r1 的 2 MAJOR / 2 可动作 MINOR 全部闭合,且**逐条经我亲手破坏-变红活体验真**;返工确为纯测试/简报改动,Phase D 生产码与 r1 尾态逐字节/逐计数一致,无新洞。残留两项非阻断登记项(见 §4):AST 扫描对裸 `except:` 的一行缺口(新 NIT,现实为零命中)与 MINOR-3(待首个真实 v3 run 验证,r1 原样登记)。B5 Phase D 施工侧至此达到 §15.2「Fable 对抗审最终 APPROVE」条件。

---

## 1. 返工 delta 核验(无新洞 / 零生产码永久改动)

- **tracked 文件**:`git diff --stat` 19 files / +1240 / -148,**逐文件增删计数与 r1 尾态快照完全一致**(stage_runner 245、orientation 74、window_sources 245、output_coordinates 236……全部逐项对上)。
- **untracked 生产文件**:`artifact_serialization.py` 与我 r1 留存全文 `diff` **逐字节一致**;`correction_audit.py` 144 行、两处 raise 门(`totality mismatch`/`resolution hash mismatch`)行号与字面与 r1 相同。三处安全门 raise 的**精确字面**由我的变异探针 `assert t in s` 命中证实未动。
- **返工 delta 实体**:`tests/test_c2_b5_artifact_trust.py` 640→833 行(+193):两个 helper(`_rebuild_self_consistent_writer_result` / `_forge_both_window_audit_copies`,直接采用我 r1 判词的攻击构造)+ 4 个新安全拒绝 test item + AST 扫描重写 + #1–#10 match 串;简报 §NIT-2 措辞修正。
- **残留检查**:`FABLE_PROBE`/`FABLE_R2` 全仓 0 命中;七个信任链文件 `except:` grep 零命中;`git status` 尾态与开工一致。

## 2. r1 findings 逐条闭合状态

| r1 finding | 返工动作 | 活体探针(我亲手) | 状态 |
|---|---|---|---|
| **MAJOR-1a** writer replay 门无锁 | 新增 `test_d1_writer_replay_rejects_self_consistent_original_field_forgery`(2 参数:`original_room_id`/`original_span`),按我 r1 攻击构造**双侧一致伪造 + 公开 API 全量重签 identity/evidence**,match=`writer_window_audit_replay_drift` | 把该 raise 换 `pass` → **恰好这 2 项红、其余 43 绿**(`2 failed, 43 passed`);红点即 replay 门本身,非上一道 `writer_audit_output_drift`;还原后全绿 | **CLOSED** |
| **MAJOR-1b** writer totality 门无锁 | 新增 `test_d1_writer_totality_rejects_self_consistent_missing_audit_row`(双侧删同一 audit 行 + 重签;pin `recompute_window_host_claims` 至真 claims 以确保探针**唯一到达** StageRunner 自己的 totality 门),match=`writer_window_audit_totality_drift` | 把该 raise 换 `pass` → **恰好 1 红**(`1 failed, 44 passed`);还原后全绿 | **CLOSED** |
| **MAJOR-2** E4 relation 守卫无锁 | 新增 `test_d3_orientation_enrichment_rejects_changed_host_relationship`:call-sequenced patch(第 1 次调用放行真复算=proof 消费边界仍真实认证,第 2 次返回重签伪 claims),match=`changed the host relationship`,并 `assert call_count == 2` 钉时序 | 把 orientation.py 该 raise 换 `pass` → **恰好 1 红**(`1 failed, 44 passed`);还原后全绿 | **CLOSED** |
| **MINOR-1** broad-except 扫描恒真 | 重写为 `ast.walk` ExceptHandler 扫描,覆盖面 3→**7 文件**(含 build/modelling/window_sources/orientation),抓 `Exception`/`BaseException`(含 tuple 形) | 注入 `except Exception: pass` 至 window_sources.py → 扫描测试**红**(报文件+行号);还原后绿 | **CLOSED**(残留一缺口见 §4-NIT-3) |
| **MINOR-2** tamper #1–#10 裸 ValueError | 全部参数项补稳定 match 串,且逐项绑到**真实具名门**:#1 `unknown facade_segment_id`(claims 复算)、#2/#3/#4-visible feature-state 绑定门、#4-p1/p2/normal Vg 校验器、#4-fingerprint fingerprint 门、#5–#8 `resolution_sha256 does not match canonical host resolution`、#9 aggregate 门、#10 artifact output identity 门 | 逐项读验 match 串(此改动同时把 r1 我指出的「究竟哪道门先响」显式钉死,证明各 mutate 确实到达具名关系/身份门,非笼统 canonical 门) | **CLOSED** |
| **MINOR-3** writer replay 可用性前提 | 按 r1 处置:登记,待首个真实 v3 case run 验证 | 无需探针 | **OPEN-BY-DESIGN**(登记项,非阻断) |
| **NIT-1** integrated 两参 `=None` 默认 | 主控裁定维持;v3 缺参 fail-closed 不变(r1 M4 探针已验) | — | **CLOSED(裁定)** |
| **NIT-2** 简报措辞 | 已改为「按 §12.3 冻结签名补齐两参、未超出冻结签名」(简报 :32/:134/:166) | 读验 | **CLOSED** |

## 3. 新负锁质量评注(无新洞结论的依据)

1. 两个新 helper 是**攻击侧构造**(伪造后经公开 API 重签全部 identity),不调用被测门生成 expected,无自指;match 串精确绑定我 r1 攻击探针实测的生产错误码。
2. totality 锁的 `recompute_window_host_claims` pin 与 E4 锁的 call-sequenced patch 均为**测试隔离手段**:前者为了穿过更浅的 claims-drift 门、唯一命中深层 totality 门(浅门已由 tamper_16/17 独立锁,r1 M1 探针双红验真);后者第 1 次调用放行真复算,保住 proof 消费边界的真实认证(`assert call_count == 2` 钉死)。两者都不削弱生产路径。
3. 探针红点的**专一性**:三次 neuter 各自只红对应新锁(2/1/1),无连带、无误伤,证明锁与门一一对应。

## 4. 残留登记(非阻断)

- **NIT-3(新)**:AST 扫描的 `handler.type is not None` 条件使**裸 `except:`**(type=None,语义上比 `except Exception` 更宽)逃逸——我注入裸 `except: pass` 至 build.py,扫描**仍绿**(缺口实证),已还原。现实七文件裸 except 为**零**(grep 验证),故不阻断;修法一行:`handler.type is None or any(...)` 视为 broad。建议下批顺手落。
- **MINOR-3**(r1 原样):writer replay 依赖「manifest 覆盖全部 envelope 相关 readings」,首个真实 v3 run 时验证;若命中按细稿口径并入受信 marker,不得放松 replay。

## 5. 实测输出

targeted(探针全还原后,新增 4 项:280→284):

```text
$ python -m pytest -q tests/test_c2_b5_source_routing.py tests/test_c2_b5_host_resolution.py tests/test_c2_b5_parent_and_verts.py tests/test_c2_b5_artifact_trust.py tests/test_c2_b5_legacy.py tests/test_c2_b2_v3.py tests/test_output_coordinate_contract.py tests/test_output_coordinate_identity.py tests/test_run_pipeline_self_checks.py
284 passed, 1 warning in 9.59s
```

全仓(独立复核):

```text
$ python -m pytest -q
1427 passed, 9 xfailed, 146 warnings in 311.98s (0:05:11)
```

(1423→1427 = 恰为 4 个新锁项;9 xfailed 仍全为 legacy golden rerecord 门,Phase D xfail 为零。)

树尾态:`git diff --stat` = 19 files / +1240 / -148(与 r1 尾态一致);`FABLE_PROBE`/`FABLE_R2` 零命中;探针改动(stage_runner replay/totality raise、orientation relation raise、window_sources/build 注入)全部还原并逐一复验。

---

## 6. 结论

r1 REWORK 出口条件三条全部达成(两 MAJOR 补锁 + 顺手落了两 MINOR),返工零生产码改动、无新洞。**APPROVE**——B5 Phase D 对抗审通过;NIT-3(裸 except 一行缺口)与 MINOR-3(真实 run 验证)移交主控作跟进债登记。
