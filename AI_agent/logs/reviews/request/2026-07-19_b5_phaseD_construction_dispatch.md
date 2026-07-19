# B5 Phase D 施工派工单（sol，全升一档）

> 主控 = Opus 4.8。档位 = **全升一档**：sol（最高档）施工 → Fable 对抗审 → 主控轻门（独立全量 + 亲核 diff/探针）。
> 权威细稿 = [`AI_agent/proposals/c2_b5_detail_spec.md`](../../proposals/c2_b5_detail_spec.md) v3 定稿（1612 行）。**本单只界定范围/必接清单/审阅需求/验收 gate；实质条款一律以细稿为准，冲突以细稿为准。**
> 日期 = 2026-07-19。前置状态 = B5 Phase A/B/C 已 CLOSED，树 1360 绿 + 15 xfail（9 legacy golden + **6 个 Phase C 延后到本批**）。

---

## 0. 定位

Phase D 是 B5 的**最后一个施工批**，做完 B5 整个 CLOSED。它是「封口批」：把窗-墙解析结果写成带防篡改指纹的信任根产物、把真北出口在窗链上接通、把 legacy 三层验收锁死、并复原 Phase C 为上新门临时挂起的 6 个 E4 坐标链测试。

四 Phase 顺序执行，Phase A/B/C 的地基（`window_sources.py` / `window_host.py` / `SegmentLine2D`+`window_verts_on_line` / proof-aware `build_geometry`+`attach_windows_v3` / `check_window_host_resolution` + `kernel.window_parent_binding` / versioned `geometry_contract` / B4b official dispatch）**已在树上**，本批在其上封口，不得回退或平行重写。

---

## 1. 施工范围（gates B5-D1..D6）

严格按细稿 **§9（信任根/attempt artifact/E4 接缝）+ §10.3（audit/report）+ §10.4/10.5 收尾 + §13.6/13.7/13.8（测试锁）** 施工：

1. **B5-D1 writer-recompute** — §9.1 十步 writer 独立重算：`FinalizeResult` 累加 `PreparedCandidateIdentity`（v1/v2 四 B5 字段必 None、v3 必非空）；StageRunner 写 accepted 前对 runtime geom 再 versioned serialize 逐字节比对、从 verified raw resolver inputs fresh 重算、fresh 重跑 Vg materialization、fresh derive feature claims、**writer 内部 `from src.agent.correction import window_host as window_host_module` module-qualified 调 `recompute_window_host_claims`/`derive_window_evidence_ledger`（禁复用 `finalize` 模块绑定）**、逐字段比对、六件套写临时 dir 回读 strict validate 再整体 rename、仅 checks 不 block 才移 manifest accepted pointer。**严禁**用传入 `resolution_sha256`/direction binding/Va ledger identity 当重算输入；严禁 `try/except` 后只丢 sidecar 仍接受 output。
2. **B5-D2 accepted-chain** — §9.2 artifact contract（`ArtifactKey += window_resolver_inputs | window_hosts`；`ArtifactContract += correction_b5_v1 | correction_b5_orientation_v1`，各六键 required/allowed；v1/v2 新 attempt 仍 `correction_b2_v1`；`StageRecord output_hash == artifact_hashes["output"]` 继续成立、六键任一缺失/多余/不匹配拒绝）+ §9.3 `load_verified_accepted_correction` / `verify_integrated_gate1_correction` 六件套全验（`window_hosts.output_sha256 == output hash`、resolver inputs hash 重算、final geom fresh parse + Vg 重验 + current-ring bindings + host claims 重算、feature-state fresh derive、以真实 output/feature hash 重建 Va visibility 与 evidence ledger 逐字段一致；**不得从 stage-root convenience copy 取 proof**；v3 缺 proof 不得构造 accepted marker）。
3. **B5-D3 e4-rebind** — §9.4 `finalize_orientation_enrichment` B5 化：新生产 v3 base 只接受 verified `correction_b5_v1`；enrichment 只改 north_axis 与 orientation audit（room/ref/span/host audit 逐值保持）；**携 verified resolver-input raw bytes、ring-free direction facts 逐值保持、按 orientation-enriched geom 的 current ring 重派生 ring-dependent bindings 并 rerun host claims（不得把 base 的 13 字段 binding 带过来）**；north axis 改了 output hash → 重新预序列化 output/feature、重建 Va evidence 与 `window_hosts.json` 绑新 hash（不复制 base bytes）；writer 标 `correction_b5_orientation_v1`；`AcceptedCorrectionRef`/`OutputCoordinateContract`/assembly loader 放行新 orientation contract；relative contract 仍只由 schema v3 + populated north axis + orientation contract 触发（不按 theta 数值猜）；**output-coordinate 不消费 host 数值，但必须先验完整六件套**。
4. **B5-D4 legacy-semantic** — §13.7：v1 矩形 / v2 polygon fixture 全链（raw→finalize→build→building JSON→zone/surface/fenestration specs→audit）与改造前 frozen snapshot **语义**逐项相等；v1/v2 各一个 cell 边界被 structural snap 移动、window 恰需按移动后边界 clamp 的 fixture（锁「入口只决策、原位后执行」）；v1/v2 window extra 加合法/非法 `facade_segment_id`+fake host digest 行为与无 extra 相等；`window_clamp_to_parent=False` legacy 语义不变；missing room/no parent/notes 语义不偷修；integrated/stepwise 同输入语义相等。
5. **B5-D5 versioned-byte** — §15.1 第 2 层：**只有** version-gated serializer 明确排除 legacy defaults/new keys 且有 frozen byte fixtures 后，才承诺 v1/v2 artifact byte equality；**否则简报/判词/测试名/文案只能写 semantic/geometry equality，不得写 byte equality**。本批须落 **NIT-4 带窗 legacy frozen-byte fixture**（§13.7 版本门落地后那条），把带窗 v1/v2 的 output/build/spec/audit 字节冻结；未落地就明写「未落、仅 semantic」并留门。
6. **B5-D6 protected-assets-clean** — §13.8 B2b/E4 回归全绿 + 全仓 protected GT/golden **零 diff**：B2b intent + elevation-only room 空（transient Vg dry resolver 补 room、变形后 final 唯一）/ B2b 变 visibility 归属（post-sim gate 拒/回滚不带 pre id）/ 无 intent 只跑 final Vg 不多写临时 audit / B2b 入口仍无 persistent facade segment/ref / B5 base→orientation host 关系逐值不变 window_hosts 重绑新 hash / theta 0/90/270 existing E4 geometry+EP 语义不变 / legacy World contract 不要求 B5 sidecar。

**§10.3 audit/report** 同批落：`record_baseline.py`/`report_assembly.py` 从 manifest-accepted audit 与同 attempt 已验 `window_hosts.evidence` 读（branch/clamped 来自 geometry proof、corroboration 来自 evidence ledger、conflict reason 来自 rejected attempt，**不得从 root 旧文件或 audit 猜 corroboration**）；audit record 的 resolution hash 必须在 report 前重验，坏 hash 不能只标 "unreadable" 继续出成功报告。

---

## 2. 必接跟进债（Phase C 收尾精确挂到本批 —— 不接即 Phase D 不算 CLOSED）

1. **6 个 xfail 复原** = [`tests/test_output_coordinate_identity.py`](../../../tests/test_output_coordinate_identity.py) 行 244/275/289/318/331/413 的 E4 stepwise→build→loader→assembly 链。Phase C 令 v3 `build_geometry` 强制 `VerifiedWindowHostProof`（spec §8.1），这些测试走 v3 build 不带 proof 撞门 → 标了 strict xfail 指向本批。**Phase D 接 proof 后必须重写这些测试以构造/传真 proof（走生产接线，非手搓假 proof），删除 xfail 标记**。strict xfail 在接通后会 XPASS 提醒——**收尾时全仓不得再有指向 Phase D 的 xfail**（9 个 legacy golden xfail 保留）。
2. **MINOR-1 伪 marker 收回** = [`build.py:94`](../../../src/agent/geometry/build.py#L94)（`_recheck_marker`/consumption boundary）与 [`geometry_validator.py:323`](../../../src/agent/correction/geometry_validator.py#L323) 两处裸构造 `VerifiedWindowResolverInputs(producer_draw_canonical_bytes=b"", raw_view_manifest_bytes=b"", raw_reading_artifacts=())` 伪 marker，违 §4.4 source link 验证。**收回为从 proof 携带的真 verified marker**（proof 须带足 §4.4 所需真字节），或按细稿把该 boundary 的重算改走 proof-authenticated 路径。**禁保留伪空字节 marker**。
3. **MINOR-2 pipeline C↔D proof 接线** = [`pipeline.py:743`](../../../src/agent/pipeline.py#L743)（`materialize_kernel_geometry`）+ `pipeline.py:1144`（`check_kernel`）把 `window_host_proof` 一路串到 `build_geometry`/`check_kernel`，与 stepwise `run_stage.py` parity（§12.2 "双路径同一 finalize/proof 传递"）。这是 v3 pipeline C↔D 硬断，接通后上面 6 个 xfail 的生产链才真闭合。
4. **NIT-3 candidate output 序列化共享 helper** = candidate output 序列化口径（finalize 预序列化 vs writer 复算 vs loader 重解析）走同一 canonical helper，禁三处各写平行序列化。
5. **NIT-4 带窗 legacy frozen-byte fixture** = 见上 B5-D5，§13.7 版本门那条。

---

## 3. 铁律（违任一即 REWORK）

- **不改** GT/golden/verified overlay / wall·floor·roof face construction / Va public wire·helper·version / B5b HTML·REPORT / v1·v2 schema 类字段 / C2 `FacadeSegment` axis validator（§12.4）。
- **fail-closed 四边界**：resolver/writer/loader/build 全 fail closed；source scan 锁 resolver/writer/loader 无 broad-except fail-open（§13.6 尾）。
- **信任根不自报**：writer 独立重算不得用调用方传入的 identity 当输入；loader 不得从 convenience copy 取 proof；E4 rebind 不得沿用 base bytes 致 output hash stale。
- **测试锁字面量**（§13 头 + §13.6 尾）：期望 record/hash/verts 必须手写字面量或冻结文件；**禁**调用被测 resolver/`window_verts_on_line`/hash helper 生成 expected 再自比；固定 digest 测试把完整 canonical JSON 字面量 + 预冻结 SHA-256 写进 fixture（不先调 `_canonical_hash()` 生成 expected），另加一项改单字节后 hash 必不同；**禁** `x != x` / `assert not (x != x)` 恒真恒假伪检查（Phase C F1 就栽在恒真自检）。
- **安全拒绝分支缺锁 = shipped-untested = 未交付**，不得用现有总绿数代替（§14 尾）。§13.6 十九项 anti-tamper **逐项单独 mutate**，一个大测试改多项不算数；#16/#17 writer 对偶探针（只 patch `finalize.resolve_window_hosts` 使 finalize 产伪 claims、验 writer 内部 module-qualified import 不受 patch 影响仍拒）必须坐实两边无共享可劫持符号；#18/#19 明确不得得到 accepted/build geometry。

---

## 4. 审阅需求（Fable 会照 §16 攻击，请预先扛住）

细稿 §16 十条对抗重点全部适用于本批封口面，尤以：

- §16#6 **output/audit 先冻结、Va evidence 侧车化是否真正解除 hash 环**，ledger 是否只用真实 output/feature artifact hash（信任根本批核心）；
- §16#8 writer 的 **module-qualified 复算是否不受 finalize 符号 patch 影响**（对偶探针 #16/#17）；
- §16#10 **resolver inputs/output/record/evidence/artifact/E4 rebind 是否仍有自报信任或 fail-open**；
- §16#9 legacy 分派是否只在入口决策、window pass 仍在 structure/z-stack 之后原位执行。

请把每条对抗面对应的活体探针/负测写足，简报里逐条自证「改坏即变红」。

---

## 5. 验收 gate

- **Phase D targeted tests 全绿** + **相关全仓 tests 全绿**才算完；§14 尾：任何安全拒绝测试缺失视为 shipped-untested。
- **6 个 Phase D xfail 全部复原为真绿**（生产链接通），全仓不得再有指向 Phase D 的 xfail；9 个 legacy golden xfail 保留。
- **promotion 条件**（§15.2）逐项满足：源两支/mixed/hidden/partial 全绿、pre/post ring 各自重派生 binding 且同 ring 与 judge oracle 逐字节 parity、conflict/negative/legacy/tamper/parent 每拒绝分支独立锁、六类入口拒绝逐项锁、四边界 fail closed、Va ledger identity 零占位、p1→p2 负轴三面全绿、integrated/stepwise parity、B4b sidecar/cache identity 未被 B5 绕过、E4 新 contract 全链、protected assets 零 diff。
- **失败即回滚本 Phase 接线，不更新 golden 追行为**（§15.3）；v1/v2 legacy regression 则 B5 不得 promotion。

---

## 6. 交付格式（施工简报）

交付时写一份施工简报（放 `AI_agent/logs/reviews/execution/2026-07-19_b5_phaseD_construction_brief.md`），含：

1. 逐 gate（D1-D6）+ 5 笔必接债做了什么、落在哪些文件/行；
2. **诚实披露**：哪些完全交付、哪些部分/未交付（**禁藏假绿，禁把「未竟」说成「留给审查」**——这是 07-14 起纪律，Va/Phase A/B4b Phase B 都栽过；B4b Phase D terra 诚实部分交付是正面样板）；
3. 新增/改动测试清单 + 每个安全拒绝分支对应哪条锁；
4. §16 十条对抗面逐条自证「改坏即变红」的探针指针；
5. targeted + 全仓 pytest 的真实运行输出（passed/xfailed 数）；
6. 任何 review-ask（措辞歧义/细稿与现码冲突/裁决请求）单列，供主控裁。
