# B4b Phase A 执行审 r1(Opus 升一档交叉审,2026-07-15)

- 审阅者:Opus(升一档执行审);被审:B4b Phase A 施工批(terra),工作树未 commit,基座 HEAD `526c38e`
- 合同:`AI_agent/proposals/c2_b4b_detail_spec.md` v2(唯一施工合同);派单:`request/2026-07-15_b4b_phaseA_construction_dispatch.md`;简报:`execution/2026-07-15_b4b_phaseA_construction_brief.md`;REC-A:`verdict/2026-07-15_b4b_rec_a.md`
- 审法:五出口 gate 独立验证(不采信简报自报)+ A0 preimage 从零重算逐字节比对 + 活体探针(scratchpad,不入仓)+ 测试族对账表 + 定向测试组自跑核数
- 车道纪律:仅审派单所列文件;B4a Phase B 树内件(inspect_dxf/gt_extraction/gt_schema 及其测试)未审未动,gt_schema 树内状态仅作只读依赖事实

## 裁决

**APPROVE-WITH-CHANGES** — 实现核心(canonical hash、identity 链、fail-closed 边界)经独立探针全部验证正确;但 A4 gate 的测试合同按稿面字义未达成(自指测试 + A0 无固定向量),另有两处冻结签名未登记偏离。2 MAJOR 须修后主控抽查放行,无需二轮全量审。

**Severity 计数:MAJOR 2 / MINOR 4 / NIT 2 / WATCH 1。**

## Findings

### BA-C1(MAJOR)A4 frame-transform hash 无独立锚:A0 缺固定向量,四态测试自指

- 稿 §13 Phase A 测试合同原文:"sign 正负、mirror 两态与 local-x 两态 fixture 的 frame-transform hash **与 A0 固定向量字节相等**"。
- A0 §4.1.1(本批新增)只登记了九键集合、序列化口径与排除清单——`grep -E "[0-9a-f]{64}"` 全文仅一条 Hex64(config hash `ac2c1470…`),**没有任何 frame-transform 固定向量**。
- `tests/test_c2_b4b_score_inputs.py:46-55` 的 `elevation_binding()` 用 `frame_transform_sha256(proto)` 生成 fixture 的 hash 字段,`test_frame_preimage_all_sign_mirror_localx_states`(:94-102)再断言 `frame_transform_sha256(binding) == binding.frame_transform_sha256`——**实现对实现,恒真式**。若 `canonical_json` 口径漂移(如 `ensure_ascii=True`),四态测试照绿。这正是 VA-C7 点名的 tautological 债务类、也是 Va 批 Opus 首轮抓 MAJOR 的同款洞。
- 探针证据(实现本身是对的):我从零按稿 §6.3.8 重算 South/no-flip 向量得 `db2e25cf576ef104bb7cd39afc89026857f9860aba42bbdf2c6c52057e88dade`,与 `frame_transform_sha256()` 输出逐字节相等;并与 Va 私有 `_frame_hash()`(未被 B4b import,见 A4 gate 节)交叉比对相等。缺/多键拒绝(缺 `sign`、多 `extra`)真实 fail(ScoreContractError)。
- 修法:A0 §4.1.1 登记四态(或至少一条 canonical)固定向量 hash;测试硬编码期望值断言,消除自指。

### BA-C2(MAJOR)两处 §6.8 冻结公开签名偏离且未登记(简报"偏离:none")

- `decide_score_capability`(`src/agent/judge/score_schema.py:436-439`):稿冻结签名为 `(*, gt_identity, stage, product_schema, view_manifest: ViewManifest)`;实现以四个**带默认值的字符串参数**(`view_manifest_schema="1"`, `completeness_ruleset="1"`, `reference_va_schema="1"`, `segment_geometry_capability="c2"`)替代 ViewManifest——capability key 的四个成分来自默认值而非实际 manifest 证据,属信任根软化;后续 Phase 落 frozen 签名时必然公开 API 破坏或第二套 dispatch(稿明令禁止)。
- `load_cached_score`(`score_schema.py:476`):稿冻结签名 `(path, *, grade_path, expected_identity)`;实现缺 `grade_path`(§10.2 第 7 项 grade 文件 identity 校验的接缝)。
- 合同阶段的冻结面偏离必须登记(REC-A 对 `wall_thickness_m` 默认值即按此办理),本批简报却报"偏离:none"。修法:改成冻结签名(Phase A 可对 manifest 参数做骨架消费),或补登记偏离 + Phase B/C/D 收敛计划并经主控确认。

### BA-C3(MINOR)HelperIdentityV8 五个 Literal 字段带合同外默认值

- `score_schema.py:293-297`:`scorer_schema: Literal["8"] = "8"` 等五处;稿 §6.5 无默认。dump 字节等价,但与 REC-A PA-R2④ 同类(彼处按"登记偏差+修除"办理)。修法:去默认或登记留痕。

### BA-C4(MINOR)SCORER_SCHEMA "7"→"8" 属稿 §13 Phase D 工项,提前于 Phase A 执行;过渡窗产生"8"标签双形态

- 派单明令"SCORER_SCHEMA 切 '8'",施工方照办并在简报/review-ask 挂出——**非施工方违单**,是派单与稿的排期分歧,登记归主控裁决。
- 语义独立核验(回应主控中断指令):全仓 `scorer_schema` 消费点仅 `run_stage.py:1009`(cache 校验)与 `:1095`(写入)两处 + 新 HelperIdentityV8 Literal;`render_grade.py` 不读该字段。升 8 效果 = 盘上所有 v7 sidecar 一次性 cache miss → 由**未改动的 legacy scorer** 重算,分数逐值不变,仅标签换 "8"。定向回归:`test_judge_batch_b` 11 passed(sidecar 标签断言用动态 `rs.SCORER_SCHEMA`,":484 的 '7'" 是 recompute 触发 fixture,语义仍对)、`test_render_grade` 19、`test_run_stage_flow` 15;主控全量 1135 绿佐证。**判定:不破坏 legacy 路径。**
- 残留风险:Phase D full writer 落地前,run_stage 会写出 **legacy-v7 形态但标签 "8"** 的 sidecar,与 `ScoreSidecarV8` 同标签不同形。仓内安全(探针:伪造全 legacy 形态 "8"/"7" sidecar 喂 `load_cached_score` → strict parse 失败 → None,fail-safe),但同一版本号双形态对人工/外部工具有误读面。修法:在简报或 A0 补一句过渡窗事实登记;或主控改判回 Phase D 再 bump(二选一,倾向前者,改动已被全量回归覆盖)。

### BA-C5(MINOR)边界异常合同泄漏:非 UTF-8 config 泄 raw UnicodeDecodeError

- 稿 §6.8:"所有 public 函数只抛 ScoreContractError"。探针:非 UTF-8 字节喂 `load_judge_score_config` → **raw UnicodeDecodeError 直穿**(`score_config.py:16` 的 except 元组漏 `UnicodeDecodeError`;对照 `score_inputs.py:75` 的 `_load_json` 是捕的)。缺文件路径正常(→ `score_gt_identity_invalid`,符合 §6.2)。同类理论边:`compute_facade_segments_sha256` 收到重复 id 且六键全同时 sorted() 比较 dict 可泄 TypeError(上游 Va 校验唯一 id,实际难触发)。修法:except 元组补 UnicodeDecodeError(一行)。

### BA-C6(MINOR)Phase A 未竟项未逐条列明(派单:"确有未竟逐条列明,不得静默")

- §6.3 校验合同第 3 项(plan floor/elevation floor-facade 需在 **typed GT** 与 manifest 同时存在)与第 4 项(每个 `gt_source_view_id` 须被 GT source refs 实际引用):`validate_score_view_bindings`(`score_inputs.py:92-112`)无 GT 参数,GT 侧交叉验证完全未做;
- §6.4 合并规则第 6 项(dataset declaration 在只读 registry 按四元组+body hash 唯一解析):未实现,builder 只产候选文件。
- 二者依赖 GT-to-Va adapter / registry,归 Phase B/C 合理,但简报应列为未竟而非"偏离:none"。修法:简报补登记清单即可,不要求本批实现。

### BA-C7(NIT)测试族薄弱面(BA-C1 之外)

- strict extra/missing/type/NaN/Inf 仅测 JudgeScoreConfigV1 一个模型(共享 StrictWire base,我探针验证 ProductIdentity/RejectedPayload/Sidecar 各 validator 真实 fire,风险低);缺键测试仅摘 `sign` 一键非九键逐一;facade-hash 测试期望值用与实现同一 `canonical_sha256` 计算(共享序列化器,弱锚——本审已用 Va 侧独立实现补交叉);config 缺文件→错误码无测试。均为廉价 parametrize 可补。

### BA-C8(NIT)decide_score_capability 死分支

- `score_schema.py:451` 末行 `return CapabilityDecisionV8(path="rejected", …)` 不可达(stage Literal 两值:correction 非 v3 已被上一分支收走,reading 恒 c2_v3);且其 reason 填的 `score_unsupported_combination` 是错误码词表,不是 NA reason 词表。Phase B/C 重写 dispatch 时一并清理。

### BA-C9(WATCH)candidate GT 门在 Phase A 全面缺席(按稿属后续 Phase,登记防遗忘)

- 探针/代码读:`load_score_gt_identity` 走 `load_gt_file`(B4a 设计:candidate 仅 file-API 可达,case loader `load_gt_document` 拒 candidate),对 candidate v3 返回完整 identity+document,`decide_score_capability` 不看 `verification_status`。§7.1 "candidate 进正式入口为 `score_gt_identity_invalid`" 的正式入口(`score_attempt`/run-stage v3 wiring)本批不存在,不算违规;但**须列入 Phase C/D 具名测试项**,否则该门会静默消失。

## 测试族对账表(稿 §13 Phase A 12 族 → 实测落点)

| # | 稿 §13 测试族 | 落点 | 判定 |
|---|---|---|---|
| 1 | strict extra/missing/type/NaN/Infinity 拒绝 | `test_strict_wire_rejects_extra_missing_type_and_nonfinite` | 覆盖(单模型,见 BA-C7;探针补验其余 validator) |
| 2 | config hash/关系/A0 fixture | `test_config_hash_relationships_and_a0_registration` | 覆盖(冻结 hash `ac2c1470…` 独立重算相符;tie-epsilon 关系违约拒;A0 在档) |
| 3 | schema 7 sidecar 必重算 | `test_schema7_is_not_a_v8_cache_hit` | 覆盖(cache-miss 义;探针加测全形态伪造 v7→None;真重算接线属 Phase D) |
| 4 | base/effective manifest hash 区分 | `test_effective_manifest_is_pure_…` | 覆盖(hash 不等 + base 未变异;`hash_obj`≡`canonical_sha256` 探针相等) |
| 5 | user/dataset 两条真实生成路径与 body hash | `test_user_and_dataset_builder_paths_and_overlay_loader` | 覆盖(subprocess 真跑 builder 两路) |
| 6 | 每 view 单 source、base 冲突、幂等重复 | overlay validator + `test_effective_manifest_…` | 覆盖(冲突拒/幂等过;重复 declaration 探针拒) |
| 7 | standard/true/unknown direction | `test_standard_true_unknown_direction_…` | 覆盖(三态 + true 缺 resolver 拒) |
| 8 | mirrored/local-x 不能来自产品 | 同上("product" not-in-source 扫描) | 覆盖(Phase A 无产品摄入路径,扫描是唯一可行探法,可接受) |
| 9 | GT-to-Va facade hash 与 A0 frozen preimage 字节相等 | `test_facade_hash_is_full_sorted_a0_preimage` | 覆盖但弱锚(共享序列化器,BA-C7;本审独立跨验:B4b vs Va `_segment_payload` 多段乱序 fixture hash `bb3da701…` 逐字节相等) |
| 10 | 四态 frame hash 与 A0 固定向量字节相等 | `test_frame_preimage_all_sign_mirror_localx_states` | **未达成——自指,无 A0 固定向量(BA-C1 MAJOR)**(实现正确性由本审独立重算兜底) |
| 11 | 缺/多任一 preimage 键均失败 | 同上 | 部分(缺 `sign`/多 `extra` 各一例真 fail;非九键逐一,BA-C7) |
| 12 | v3 绝不调用 raw `load_gt()` | `test_typed_capability_dispatch_…` + 本审 grep | 覆盖(新三模块唯一 GT 入口 = `load_gt_file`;`load_gt_file` 内部走 L0/L1/L2 不经 `load_gt()`;源扫描断言在档) |

简报"A1=14 passed 而 A2/A3/A4 包含于上组"的口径核实:两新测试文件合计恰 14 个测试函数(collect-only 核对),四 gate 共摊属实;薄处已按上表逐族定位,唯一实质缺口是第 10 族。

## 五出口 gate 独立验证

| gate | 判定 | 独立证据 |
|---|---|---|
| B4B-A1-wire-strict | PASS(带 BA-C5/C7 尾巴) | config 五类拒绝测试 + 探针:NaN 藏进 JSON 文本喂 bindings loader → `score_view_binding_invalid`;JSON array→tuple 严格解析往返相等(回应 review-ask①,PA-C7① Va list 偏差不波及 B4b 自有 tuple 模型);sidecar content hash 篡改→拒;RejectedPayload 非冻结码→拒 |
| B4B-A2-identity-total | PASS | ProductIdentity accepted↔record-hash 双向 invariant 探针真 fire;`load_cached_score` identity 全等才 hit(不等→None);v2 GT(sm21 真档)typed 路径出 schema=2 identity 正常 |
| B4B-A3-completeness-owner | PASS(BA-C6 登记欠账) | builder 两路 subprocess 真跑;effective manifest 纯函数(base 不变异)+ 幂等/冲突/未知 input 拒;重复 declaration 拒;`_protected()` 拒 gt/golden/verified 路径;OpeningEvidence claims 排序与现役 manifest 侧 `sorted(set())` 约定一致 |
| B4B-A4-va-preimages | 实现 PASS / 测试合同 **未达标(BA-C1)** | 从零重算 frame hash `db2e25cf…` 与实现逐字节相等;facade hash 多段乱序 fixture `bb3da701…` 与 Va 私有 `_segment_payload`+`_canonical_hash` 逐字节相等;`grep` 证明 B4b 未 import Va 任何私有 helper(仅 public `ElevationViewBindingV1`);`_AXIS/_BASE_SIGN` 常量与 Va 逐值相同;A0 九键登记与稿 §6.3.8 逐键相符(8 字段+schema=9,排除清单在档) |
| B4B-A5-production-import-zero | PASS | 独立 grep `src/agent/{pipeline,correction,reading,execution}` + `src/validator`:新 score 模块零被 production import(仅 tool 脚本 `build_judge_score_inputs.py`);唯二 judge 引用是**既有** `step_orchestrator.py:64/:311`(StageVerdict/惰性 rubric_for,基座原样);`test_gt_discipline` 6 passed;score 模块 import 方向均为 judge←production(合法) |

## 定向测试组自跑核数

| 组 | 结果 |
|---|---|
| tests/test_c2_b4b_contract.py + test_c2_b4b_score_inputs.py | 14 passed |
| tests/test_c2_va_applicability.py | 49 passed |
| tests/test_gt_schema.py / test_gt_discipline.py / test_judge_harness.py | 46 + 6 + 18 = 70 passed |
| tests/test_reading_score.py / test_elevation_score.py / test_judge_batch_b.py | 17 + 16 + 11 = 44 passed |
| tests/test_render_grade.py / test_run_stage_flow.py(schema bump 影响面加测) | 19 + 15 passed |
| `git diff --check` / 受保护 case_tests diff | 干净 / 0 |

简报各组 passed 数(14/49/70/44)与自跑逐组相符,无虚报。mypy/ruff 环境未装(§15.1 静态检查项本机不可执行,主控全量 1135 绿佐证)。

## Review-ask 三项答复

1. **strict JSON tuple 解析**:健康。`model_validate_json` 下 JSON array→tuple 严格解析成立且往返相等;NaN 文本级走私被字段级 `allow_inf_nan=False` 拦下;Va 的 list-vs-tuple 留痕(PA-C7①)不影响 B4b 自有 wire。
2. **A0 九键 preimage 登记**:键集/序列化口径/排除清单与稿 §6.3.8 逐字相符且经独立重算字节验证;**缺固定向量登记**(BA-C1,唯一必修点)。
3. **SCORER_SCHEMA="8" 与 Phase-D writer 接线边界**:见 BA-C4——现在 bump 语义安全(消费点仅 run_stage 两处,legacy 分数不变,回归全绿),代价是过渡窗"8"标签双形态;Phase-D full writer/cache validator 按稿必 strict-parse,届时过渡窗产物自动 cache-miss 重算,无残留毒化路径。

## 必修清单(APPROVE-WITH-CHANGES 附带条件)

1. BA-C1:A0 §4.1.1 登记 frame-transform 固定向量(至少一条,建议四态)+ 测试改硬编码期望 hash 断言(消自指)。
2. BA-C2:`decide_score_capability`/`load_cached_score` 改冻结签名,或在简报/A0 正式登记偏离与收敛 Phase 并经主控确认。
3. BA-C3/C5/C6:去(或登记)HelperIdentity 默认值;score_config except 补 UnicodeDecodeError;简报补 Phase A 未竟清单(§6.3-3/4、§6.4-6、candidate 门 BA-C9)。
4. BA-C4 归主控:过渡窗事实登记或改期 bump,二选一。

修复面全部局部(A0 文档 + 测试锚 + 两签名 + 一行 except),不动架构;修后主控轻门抽查即可,无需二轮全量交叉审。

签字:Opus 执行审(升一档),2026-07-15。

---

# r2 抽查闭环(Opus,2026-07-16)

施工方按 r1 返工后复审。六项抽查全部独立验证,不采信自报;主控合树全量 1146 绿 + 9 xfail 零失败为旁证。

## r2 裁决

**APPROVE** — r1 全部必修项(BA-C1~C5)实锤闭合,BA-C6/C8/C9 按登记路线处置到位,BA-C4 过渡双值按主控"标签必须如实"裁决实现且实现↔登记一致。残留仅登记类,不阻合并。

## 逐项抽查结果

### ① A0 四固定向量 vs 从零重算 — PASS(逐字节)

A0 §4.1.1 新增四态向量表(fixture:`input_id="south"`、South、fingerprint `"a"*64`、axis x、origin 0.0)。我用**纯 stdlib(hashlib+json,零仓内 import)**按稿 §6.3.8 九键 preimage 从零重算:

| sign | mirrored | local_x | 从零重算 vs A0 冻结值 |
|---:|:---:|---|---|
| +1 | false | l2r | `db2e25cf…` MATCH(与 r1 独立值同) |
| -1 | true | l2r | `b2d733be…` MATCH |
| -1 | false | r2l | `741f28f3…` MATCH |
| +1 | true | r2l | `88c1c19d…` MATCH |

四条全部逐字节相同;sign 与 mirrored⊕local-x 翻转规则的四态组合亦与 Va `_BASE_SIGN` 约定自洽。

### ② 冻结签名对齐 — PASS

- `decide_score_capability`(`score_schema.py:437-438`):现为 `(*, gt_identity, stage, product_schema, view_manifest: ViewManifest)`,与稿 §6.8 逐字一致;capability key 四成分改从**实际 manifest 字段**(`view_manifest_schema_version`/`completeness_ruleset_version`)与 **Va 公开常量** `FACADE_APPLICABILITY_SCHEMA_VERSION` 读取(符合 §5.1 "从公开常量读取不得复制"),`segment_geometry_capability` 由 GT profile 派生——r1 的默认值信任根软化消除;BA-C8 死分支同步修除(函数以 c2_v3 return 收尾,无不可达 rejected 分支)。
- `load_cached_score`(`score_schema.py:476-489`):现为 `(path, *, grade_path, expected_identity)`,并真实读 PNG bytes 验 `artifact_contract.grade_png_sha256`。探针:合法 pair→hit;PNG 篡改→miss;缺 grade 文件→miss。

### ③ BA-C1 测试真去自指 — PASS

`tests/test_c2_b4b_score_inputs.py:27-32` 现有 `FRAME_VECTORS` **硬编码字面量**(非计算产物);fixture 构造直接用字面量(:60),测试(:101-111)三重断言:fixture 声明值==字面量、`frame_transform_sha256()` 实现重算==字面量、字面量存在于 A0 文件——实现对冻结字节,自指消除。缺键检查升级为**九键逐一删除**循环(r1 仅摘 `sign` 一键的薄弱面同步闭合)+多键拒绝。

### ④ 过渡双值实现↔登记一致 — PASS

- 实现:`run_stage.py:77` `SCORER_SCHEMA = "7"`(legacy writer/cache 标签回真值,r1 BA-C4 的"8"标签 v7 形态窗口消除);`score_schema.py:30-31` judge skeleton 保持 `"8"`。
- 登记:简报"显式偏离与未竟"节以带日期条目登记双值边界、Phase D 收敛路径、`test_judge_batch_b` 如实断言 legacy=7(动态 `rs.SCORER_SCHEMA` 断言 4 处自动跟随)。实现与登记逐点对得上;`test_render_grade` 19 + `test_run_stage_flow` 15 + `test_judge_batch_b` 11 全绿。
- 残留 R1(NIT):两个同名 `SCORER_SCHEMA` 常量异值并存(run_stage=7 / score_schema=8)至 Phase D,已登记;命名混淆风险自担到收敛日。

### ⑤ Phase C/D 未竟登记完整性 — PASS

简报未竟清单核对:§6.3-3/4 已由 `validate_score_view_bindings_against_gt()`(`score_inputs.py:116`,GT floor/facade/source-ref 交叉验证,B-M floor_ref 1-based 映射到 typed GT floor)实现并有正反测试(:179/:186),**docstring 如实声明"冻结 file loader 无 GT 参、Phase C typed service 必须调 companion"**;§6.4-6 已由 `resolve_dataset_declaration()`(`score_inputs.py:175`,四元组路径+全 body+body_sha256 恰一匹配)实现并有测试(:143);candidate GT 正式入口拒绝 + Phase C 五项具名测试 + Phase D 五项具名测试全部列名(BA-C9 闭合)。R3(WATCH 延续):三件均"已实现未接线",Phase C service 接线是硬门,已具名登记。

### ⑥ r1 活体探针复跑 — 全 PASS

P1 accepted↔record-hash invariant 拒 / P2 非冻结错误码拒 / P3 sidecar content hash 篡改拒 / P4 伪造 v7 全形态→miss、合法 pair→hit、PNG 篡改→miss(新签名三态)/ P5 非 UTF-8 config → `ScoreContractError(score_gt_identity_invalid)`(BA-C5 闭合,回归测试 `test_non_utf8_config_is_a_score_contract_error` 在档)/ NaN 藏 JSON 文本喂 bindings loader→拒(`score_view_binding_invalid`)/ JSON array→tuple 严格解析往返相等 / 重复 declaration→拒。

## 定向组自跑(与简报 217 逐组核对)

| 组 | 自跑 | 简报 |
|---|---:|---:|
| B4b(contract+score_inputs) | 18 | 18 ✓ |
| Va | 49 | 49 ✓ |
| GT schema/discipline/harness | 72 | 72 ✓ |
| legacy(reading/elevation/batch_b) | 44 | 44 ✓ |
| render/run-stage-flow | 34 | 34 ✓ |
| **合计** | **217** | **217 ✓** |

`git diff --check` 干净;受保护 `case_tests` 0 diff。

## 残留登记(均不阻合并)

- R1(NIT):同名 SCORER_SCHEMA 双值并存至 Phase D(已登记,BA-C4 过渡窗)。
- R2(NIT,BA-C7 留痕):facade-segment hash 测试仍与实现共享序列化器,独立 byte anchor 按简报留痕推 Phase B adapter 实体测试补强。
- R3(WATCH):companion validator / registry resolver / candidate 门三件"已实现未接线",Phase C service 必须接线(已具名登记为 Phase C 测试项)。

**r2 裁决:APPROVE。** B4b Phase A 可提交主控轻门(独立全量+抽查+裁决)。

签字:Opus 执行审(升一档)r2,2026-07-16。
