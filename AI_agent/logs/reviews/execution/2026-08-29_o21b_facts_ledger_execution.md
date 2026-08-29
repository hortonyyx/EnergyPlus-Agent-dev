# 施工记录 · ②-1b：`revisions` 台账 + `as_signed` 机械派生 + B1 指纹锚 + F-D 指纹加宽

- **日期**：2026-08-29 · **施工**：Claude 执行档 · **派工单**：[`request/2026-08-29_o21b_revisions_and_as_signed.md`](../request/2026-08-29_o21b_revisions_and_as_signed.md)
- **基线**：`a40d56d`（= `866d518` + 一份纯文档提交 `08.29h_...`）
- **是否触发「停下上报」**：**否**。承重前提四条全部复核成立（§一）；R3/R5 两处「二选一」都判断为**约束下唯一可行**而非真正的二选一（§二/§三），推理写在下面，供审阅方复核我的判断而非替代它。

---

## 〇、开工自检

```
$ git -C /workspaces/EnergyPlus-Agent-dev log --oneline -1
a40d56d 08.29h_TargetStateFlowMap_AndO21bDispatch

$ git status --porcelain
?? AI_agent/logs/reviews/request/2026-08-29_o21c_answer_compiler_DRAFT.md
```

主控随后补了一条环境更正：这一个未跟踪文件是主控写的 ②-1c 派工单草稿，与本单无关；除它之外树是干净的。⛔ 全程未读、未改、未 `git add` 该文件。

四份必读文件均已通读：派工单、`gt_revision_ledger.md`、`gt_and_pipeline_flow_map.md` §1.2–1.4、`reading_correction_split_guide.md` §十二/§五。

---

## 一、承重前提复核（派工单 §一）

| # | 前提 | 复核结果 | 证据 |
|---|---|---|---|
| 1.1 | 事实层今天只有第一截，且不落盘 | ✅ 成立 | 开工前 `case_tests/test_baseline/gt/sm25-L_anchor/` 无 `facts/` 目录；`build_as_measured` 唯一调用方是 `tests/test_as_measured_facts_layer.py`（全仓 grep 确认） |
| 1.2 | B1 指纹锚今天是显式的空 | ✅ 成立 | 编辑前 `src/agent/judge/as_measured.py` 第 449–450 行原文：`#: ⛔ Stated absence, not a missing field: B1 is ②-1b.` / `converter_implementation_fingerprint: None = None` |
| 1.3 | F-D：`converter_sha256()` 只盖一个文件 | ✅ 成立 | 实测 `hashlib.sha256(Path("src/agent/judge/tarch_normalize.py").read_bytes()).hexdigest()` = `539615abee77a636f6b3432394e1abc50f0021dac54af652071cae81aec59696`，与 `case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json` 里 `converter_sha256` 字段逐位相同 |
| 1.4 | F-132：sm24 晋升件已漂移、零测试触达 | ✅ 成立 | 实测 `verify_raw_layer_reproduction("sm24_anchor")`（改动前）已是 `implementation_drift`；全仓 grep 确认没有任何测试对 `gt/sm24_anchor/` 这份真实产物调用过 `verify_raw_layer_reproduction`（唯一调用点 `test_gt_promotion_path.py:349` 用的是当场新建的 `ready_bundle`，不是这份磁盘产物）|

四条全部成立，未发现题错，未停下上报。

---

## 二、五件事逐条兑现

### R1 · `revisions` 台账 schema + sm25 五条线待签清单

新文件 [`src/agent/judge/gt_revisions.py`](../../../src/agent/judge/gt_revisions.py)：
`RevisionTargetV1`（`kind=dxf_entity` + `view_id` + `handle`，⛔ 不是 `face_line`/`wall` —— 因为 3/5 的真实候选在 as_measured 里根本没被分类成面线，用 handle 才能不看分类结果就指对象）·
`RevisionFindingV1` · `TranslateActionV1`（`field ∈ {const,along_min,along_max}` + `delta_0p1mm`，零位移拒绝）·
`RevisionV1`（八字段逐字照派工单：`id/target/finding/verdict/action/reason/signed_by/signed_at`，另加 `candidate_action` —— 见下）·
`RevisionsLedgerV1`（绑定一份 `as_measured_content_sha256` + id 去重）。

**`candidate_action` vs `action` 的分离**（派工单没提这个字段，是本单加的，写明理由）：
派工单要「候选 action 可见」同时要「未签字进不了 as_signed」。若只用一个 `action` 字段，两个要求互斥（要么不可见、要么能派生）。拆成两个字段后由 pydantic 模型验证器结构性绑定：
`verdict == "unsigned"` ⇒ `signed_by/signed_at` 必须为空 **且 `action` 必须为空**（`candidate_action` 不受限）；
`verdict != "unsigned"` ⇒ 必须有签字；`drawing_error` 必须有 `action`；`as_designed`/`producer_defect` 必须没有 `action`。
`derive_as_signed` 只读 `.action`，从不读 `.candidate_action`。

**sm25 五条线的待签清单**（`detect_translate_candidates`，机器算出，不是手填）：

```
$ python AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py
wrote .../case_tests/test_baseline/gt_staging/sm25-L_anchor/facts
  rev-13ac: face_line_field_changed candidate_action=along_min-2
  rev-13ad: face_line_classification_changed candidate_action=none
  rev-13ae: face_line_classification_changed candidate_action=none
  rev-13af: face_line_classification_changed candidate_action=none
  rev-160a: face_line_field_changed candidate_action=along_max-2
```

⭐⭐ **一个偏离派工单例子的真实发现**：ledger §三给的示例 revision 是「整堵墙垂直移动 60mm」这种 `translate`。实测 sm25 真实的 5 条线里，只有 **2 条（13AC/160A）** 是「面线自身某个字段平移 0.2mm」这种真 `translate`；**另外 3 条（13AD/13AE/13AF）在 as-received 图上是非正交斜线**（如 13AD 端点 `(-25228.93,38279.46)→(-21589.02,38273.66)`，斜了约 5.8mm），**在签字图上被拉直成完全轴对齐的面线**——这不是「平移一个字段」，是「把斜线拉直」，是①拍板里明确留白的「遇到再加」的那类操作。本单**没有替这 3 条造一个近似的/错的 translate**，而是如实标 `candidate_action=None` + `finding.detail` 说明原因。这比派工单举的例子更贴近真实情况，也印证了①条「先只 translate、遇到再加」的判断是对的。

### R2 · `as_signed` 机械派生 + 逐位可复现门

同一文件里：`AsSignedV1`（与 `AsMeasuredV1` 字段完全相同 + 一个 `AsSignedDerivationKeyV1` 派生键：`as_measured_content_sha256` + `revisions_content_sha256` + `deriver_version`）·
`derive_as_signed(as_measured, revisions)`（纯函数，只应用 `verdict=="drawing_error"` 的记录，逐字段 `model_validate` 重建面线以触发 `along_min<along_max` 等既有校验）·
`verify_as_signed_reproduction(...)`（不一致就 raise `AsSignedReproductionError`，不返回可被忽略的 verdict 对象）。

⛔ **命名的传播范围限制**（不是疏漏）：`derive_as_signed` 只改被翻译面线自身的字段，**不重跑墙配对、不碰 `walls`/`openings`/`footprint`**。一次移动大到会改变哪两条面线配对成墙的翻译超出本单范围——这是 ②-1c（`AnswerCompiler` + 依赖闭包）该管的事，本单在代码注释里写明，不静默产出一份其实已经和 `face_lines` 对不上的 `walls`。

### R3 · B1：外部指纹锚（⛔ 未触发停下上报，推理见下）

先复核派工单给的两条路是否都可行：

- **乙（指纹存进受签字保护的载体）**：实测 `HumanReviewAckV1`（唯一现有的人工签字载体）签的是 `source_dxf_sha256/request_sha256/overlay_sha256/review_index_sha256`，**没有任何一处能装实现指纹**；本仓库也没有 GPG 签名基础设施（`git config commit.gpgsign` 未设置、`HEAD` 无签名，实测原文见下）。要走乙必须**新增一个签字字段/新走一次签字事件**——但本单没有任何签字事件（R1 的清单本身就要求全 unsigned），也没有license去发明新的签字流程（那是 ledger §五的活，不是本单的）。**判定：乙在本单约束下不可执行，不是「代价大」，是「没有事件驱动它」。**
- **git commit 哈希当外部锚**：我一度考虑用 HEAD 的 commit hash 代替，但实测本仓库提交**没有 GPG 签名**，且提交者与写代码的是同一个 agent 身份——这构不成比「代码自己算哈希」更强的外部性，只是把粒度从"一个文件"换成"一整棵树"，还会把 F-D 明确要求的"改注释不翻转"直接破坏（整树哈希对任何提交都敏感）。**判定：不是更优的第三条，是伪装成第三条的甲的劣化版，放弃。**

```
$ git config --get commit.gpgsign
(空)
$ git log -1 --show-signature
（无签名行，仅作者/日期）
```

⇒ **两条路里只有甲可执行**，不是我在两个同样可行的选项里随便挑了一个——这正是这份报告要交给审阅方复核的判断，不是我替派工方拍板之后才补的理由。

**落地**：`AsMeasuredV1.converter_implementation_fingerprint: Hex64`（原 `None = None`），`build_as_measured` 里填成 `converter_sha256()`（R4 加宽后的那个）。字段自身的 docstring 里逐行写了「谁签谁」（见 §三表格，与派工单验收项 7 对应）。

### R4 · F-D：指纹加宽到转换闭包

**闭包成员资格的出处**（⛔ 不是手挑列表就完事）：`tests/test_tarch_converter_reproducibility.py::test_f_d_closure_membership_matches_a_static_import_walk` 用 AST 静态解析 `tarch_normalize.py` 的**模块级** `from .X import` / `from src.agent....X import` 语句，递归求闭包，并断言与 `CONVERTER_CLOSURE_FILES`（13 个文件）**逐字相符**；唯一一个静态扫描看不见的**函数体内懒加载**成员（`gt_extraction.py`，被 `_run_g9_v3_preflight` 懒加载，而后者在 P2 转换真实调用链上）单独有一条测试核实它真的被那个函数持有、那个函数真的被调用。**两个被排除的懒加载**（`gt_schema.py` 里的 `from .gt import`、`schema.py` 里的 `from ... import window_host`）也各有一条测试用 grep 核实它们在闭包范围内确实无调用点——这两条测试本身就是「以后有人把它们接上却忘了改指纹」的回归锁。

**加宽了什么，不是单纯扩文件列表**：原实现 `sha256(文件原始字节)`；新实现对每个闭包文件先 `ast.parse` + `ast.dump(include_attributes=False)` 再拼接哈希——**AST 归一化摘要**，注释/格式不进 AST、`include_attributes=False` 连行号偏移都不算数。这是让「改注释不翻转」成立的必要条件，光扩大文件范围解决不了这半个方向。

**两个方向各一个真变异**（`tests/test_tarch_converter_reproducibility.py`）：

```
test_f_d_a_comment_only_edit_does_not_flip_the_closure_fingerprint  PASSED
  —— 复制 13 个闭包文件到临时目录，往 tarch_normalize.py 加一行纯注释，加宽后哈希不变；
     且顺带证明"旧定义会翻转"（raw-byte 哈希在同一处编辑前后不同）以证明变异确实生效。
test_f_d_b_a_schema_behaviour_edit_flips_the_closure_fingerprint  PASSED
  —— 往 tarch_converter_schema.py（⛔ 不是 tarch_normalize.py 自己）追加一条真语句，
     加宽后哈希翻转 —— 这正是旧实现的假阴性方向。
```

**「改指纹会让已签字件的复现门集体变红」怎么处理**：选了**「把旧值当 legacy 认」**（三选一里的第二条）。
`tarch_normalize.KNOWN_PRE_F_D_CONVERTER_SHA256` 是一个**冻结常量集合**（不是重新计算的函数——因为这次修复本身就要编辑 `tarch_normalize.py`，任何"重算旧定义"的函数一旦被这次改动本身触碰就会立刻返回一个新值，自证自伪），目前只收了 **sm25-L_anchor 一个值**。**sm24_anchor 的旧值故意不放进去**——F-132 独立测出它在旧定义下就已经漂移，放进豁免集合等于把一个真实的、已知的漂移悄悄洗白成"legacy 正常"。实测改动后：

```
verify_raw_layer_reproduction("sm25-L_anchor")  ->  reproduced      （legacy 豁免生效，未变红）
verify_raw_layer_reproduction("sm24_anchor")     ->  implementation_drift, drifted=(converter_sha256, vg_implementation_sha256)
                                                      （F-132 依旧看得见，加宽后甚至多抓到一项）
```

⇒ **门确实有牙、确实没有静默变绿**：sm25 被豁免是显式、具名、写了理由的一处豁免，sm24 完全没被豁免，两者用同一段代码路径处理却给出不同结果，证明这不是「统一放水」。

⚠️⚠️ **主控点名的攻击面，如实自评（已实测，不是猜）**：`KNOWN_PRE_F_D_CONVERTER_SHA256` 是个裸 `frozenset` 常量，今天**没有任何测试断言它「恰好两个成员」或「不含未经查证的值」**——`test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed` 只查了两个具体值各自在不在集合里，不查集合本身的边界。**实测**：把文件里的常量临时改成 `frozenset({"5396...", "f"*64})`（多塞一个凭空捏造的哈希）后，跑 `tests/test_gt_raw_layer.py + test_gt_promotion_path.py + test_tarch_converter_reproducibility.py` 全部 **106 passed，零变红**（验证后已用备份逐字节还原，`diff` 确认恢复干净，未留痕）。**如实回答主控的问题：今天什么都不会红。** 这正是「以向后兼容为名加回旧口径」曾经骗过 6 把锁的同一形状——本单只是把它诚实地摆出来给跨家族审当攻击面，**没有加锁**（主控原话「不是让你现在去加锁」）。

### R5 · 落盘位置 + 谁能写（⛔ 未触发停下上报，推理见下）

先判断派工单点名的张力本身是否成立：`gt/` 与 `gt_sources/` 确实都受「只有晋升 / 只有签字流程能写」的纪律约束（前者 F-117 明文、后者 `gt_raw_layer.py` 自己的文档也在讲 `gt_sources/` 是「case-owned persistent home」）——**这条张力是真的，不是派工方想多了**。

三条候选路里：
- `gt/` —— 排除，本单不改 `promote_gt_v3`，写这里等于绕过晋升唯一写者纪律；
- `gt_sources/` —— 排除，理由更细：这个目录已经有一个先例（`request_as_measured.json`，②-1a 留下的），但那是"对已签字 request 的纯确定性字节变换"（`derive_as_measured_request`，可逐位重算验证）；`revisions.json`/`as_signed.json` 是**判断性产物**（哪怕还没签字，它的存在形式本身就承载了"这是一份待判断的清单"这个语义），把它和"签字输入的确定性派生"混在同一目录会模糊掉这条区别；
- **新目录 `case_tests/test_baseline/gt_staging/<case>/facts/`** —— 采用。它不与 `gt/`、`gt_sources/` 任何一条既有纪律冲突（因为它是全新的、今天没有任何东西签在这里），代价是**它自己也没有任何写保护**——这是本单留下的一个明确的、没有解决的口子，见 §六「最薄弱处」。

**接缝说明**（将来怎么接进晋升，`AI_agent/logs/experiments/.../build_sm25_facts_staging.py` 和 `src/agent/judge/gt_facts_staging.py` 模块 docstring 里都写了）：
`promote_gt_v3`（本单未改）将来应该在 `revisions.json` 被真正签字（ledger §五 step5）之后，① 对 `gt_staging/<case>/facts/` 跑一次 `verify_as_signed_reproduction` 门 ② 门过了再把三份文件拷进 `gt/<case>/facts/`，与它现有拷 `gt.json`+renders+review 五件的逻辑并列。**F-128**（`promote_gt_v3` 的 `except` 只清 `gt/` 侧不清 `gt_sources/` 侧）本单**只记不修**，在 `gt_facts_staging.py` 的模块文档里点名。

---

## 三、验收项逐条兑现（派工单 §三）

| # | 验收 | 兑现 | 证据（命令 + 结果） |
|---|---|---|---|
| 1 | 三份 facts 文件真的产出来了，`as_measured` 与 ②-1a 的 `content_sha256` 逐位相同 | ✅ | `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/{as_measured,revisions,as_signed}.json` 已落盘（见 §五 git numstat）；`tests/test_gt_facts_staging_sm25.py::test_1_as_measured_matches_the_as_received_build_bit_for_bit` PASSED —— ⚠️ 说明：本单同时完成了 R3（给 `as_measured` 新增必填的指纹字段），所以这里比对的是「派生过程本身（本单的 R1/R2）没有再动一次事实层」，不是「与加 B1 字段前的旧 schema 逐位相同」（那两者必然不同，因为 schema 变了，属 R3 的预期变化，不是 R1/R2 的回归）|
| 2 | 未签字的 revision 结构性地进不了 `as_signed` | ✅ | `RevisionV1` 模型验证器：`verdict=="unsigned"` 时 `action` 必须为空，构造反例直接 `ValidationError`（`test_r1_unsigned_cannot_carry_an_authoritative_action`、`test_r1_verdict_null_is_rejected_by_the_type_itself`）；派生层面再证一次：全 unsigned 的账本派生出的 `as_signed` 与 `as_measured` 几何完全一致（`test_r2_an_unsigned_record_cannot_influence_as_signed`）|
| 3 | 可复现门有牙：手改 `as_signed` 整数⇒响亮失败；手改 `revisions` 一条 action⇒`as_signed` 跟着变且新旧哈希不同 | ✅ | 合成夹具：`test_gate_a_hand_tampered_integer_in_as_signed_is_caught`（raise）、`test_gate_editing_a_revisions_action_moves_as_signed_and_its_hash`（`as_signed_content_sha256` 前后不同，且旧 as_signed 不能从新账本复现）；**真实 sm25 产物同款两条**：`test_3_a_hand_tampered_integer_in_the_staged_as_signed_is_caught`、`test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash` |
| 4 | `translate` 之外的 action 值被拒绝且具名 | ✅ | `TranslateActionV1.kind: Literal["translate"]`，构造 `kind="merge"` 直接 `ValidationError`，报错文本含 `kind` 字段名（`test_r1_unsupported_action_kind_is_rejected_and_named`）——落在 pydantic 的具名校验里，不会掉进 `else: pass` |
| 5 | 指纹加宽双向变异各一格，且每格自证变异真的生效 | ✅ | 见 §二 R4；`test_f_d_a_...` 里额外断言了"旧定义在同一处编辑前后确实不同"，证明注释编辑不是无效编辑；`test_f_d_b_...` 断言的是加宽后的哈希本身翻转，而不是某个代理量 |
| 6 | 5 条线待签清单机器产出，`verdict` 全为未签 | ✅ | `detect_translate_candidates` 是纯函数（geo diff → RevisionV1 list），`build_sm25_facts_staging.py` 里断言 `all(r.verdict=="unsigned")` 且已实跑；`test_6_the_five_line_worklist_is_all_unsigned_with_two_well_formed_candidates` 重新独立算一遍并核对与落盘文件一致 |
| 7 | B1 锚「谁签谁」写成一张表 | ✅ | 见下方表格 + `as_measured.py` 里 `converter_implementation_fingerprint` 字段的完整 docstring |
| 8 | 权威全量绿，带 `.pth` 前后哨兵 | ✅ 见 §四：`3292 passed, 13 xfailed, 0 failed`，`.pth` 哨兵跑前跑后哈希相同（`58f547fa…`）。⛔ **这次不是权威门**——权威全量归主控，本单这次只是交付前自证，主控已在其读到的日志上核对过同一行原文 |
| 9 | `request.json` 的 `compute_request_sha256` 逐位不变 | ✅ | 见下方前后对照 |

**验收项 7 的表**（B1「谁签谁」）：

| 层 | 签的是什么 | 载体 / 谁签 |
|---|---|---|
| **输入**（`source.dxf` + `request`） | `source_dxf_sha256` / `request_sha256`，内容寻址 | 本单未跑签字流程（as-received 版本的正式签字属 ledger §五，是后续单）；将来由人经 `revisions.json` 的 `signed_by`/`signed_at` 签 |
| **实现**（转换闭包） | `converter_implementation_fingerprint` = 13 文件 AST 归一化哈希（F-D 加宽后的 `converter_sha256()`）| ⛔ 无人工/密码学签名（本仓库未开 GPG，`commit.gpgsign` 未设置，已实测）；锚点退化为「计算方法本身可审计、可复现、双向有牙」（`CONVERTER_CLOSURE_FILES` 的出处测试 + 双向变异测试），本质仍是 §二 R3 里说的「甲」，⛔ 没有升级成真正的外部签名 —— 这是本单留下的、明确没解决的缺口 |
| **facts**（`as_measured` 自身）| `content_sha256` 覆盖以上全部字节，含指纹字段本身 | 由 `canonical_bytes`/`content_sha256` 计算；`test_b1_content_sha256_covers_the_fingerprint_field` 证明篡改该字段会移动这个哈希 |

**验收项 9 前后对照**（本单全程未写 `case_tests/test_baseline/gt_sources/` 或 `gt/` 任何字节，`git diff`/`git status` 对这两个目录均为空，见 §一表格下方及 §五）：

```
sm25-L_anchor  compute_request_sha256(request.json) = d738d0ac230f… （前后相同，未改）
sm24_anchor    compute_request_sha256(request.json) = ae0fec087ef2… （前后相同，未改）
```

---

## 四、跑测

**中间轮受影响子集**（工具算出，逐字）：

```
跑测声明：受影响子集 = tests/test_affected_tests_map.py tests/test_as_drawn_denominator_consistency_readout.py
tests/test_as_drawn_denominator_f126.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py
tests/test_gt_from_dxf.py tests/test_gt_multifloor_world_snap.py tests/test_gt_overlay.py
tests/test_gt_promotion_path.py tests/test_gt_raw_layer.py tests/test_gt_revisions_and_as_signed.py
tests/test_tarch_converter_gate_mutations.py tests/test_tarch_converter_p1_geometry.py
tests/test_tarch_converter_p2_geometry.py tests/test_tarch_converter_reproducibility.py
tests/test_tarch_elevation_must_red.py tests/test_tarch_opening_carriers.py
（依据 affected_tests.py --changed src/agent/judge/tarch_normalize.py src/agent/judge/gt_raw_layer.py
src/agent/judge/as_measured.py src/agent/judge/gt_revisions.py src/agent/judge/gt_facts_staging.py
tests/test_as_measured_facts_layer.py tests/test_tarch_converter_reproducibility.py
tests/test_gt_revisions_and_as_signed.py tests/test_gt_facts_staging_sm25.py）

结果：385 passed, 1 xfailed, 28 warnings in 181.87s (0:03:01)，exit 0
```

**`.pth` 哨兵**（跑前跑后一致，未被第三方改指）：

```
跑前 2026-08-29T10:39:31Z  58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/.../_editable_impl_energyplus_agent.pth -> /workspaces/EnergyPlus-Agent-dev
跑后 2026-08-29T10:51:13Z  58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/.../_editable_impl_energyplus_agent.pth -> /workspaces/EnergyPlus-Agent-dev
```

**交付前全仓**（⛔ 本单交付前这次不叫权威门，权威归主控；跑前 `ps aux | grep pytest` 确认无其他席位在跑）：

```
$ python -m pytest -p no:cacheprovider -q
...
3292 passed, 13 xfailed, 212 warnings in 674.29s (0:11:14)
EXIT:0
```

对照基线 `a40d56d` 的权威全量「3253 passed, 13 xfailed」（②-1a-R，主控核对）：**0 failed**，xfailed 计数不变（13），passed 净增 **39**。逐文件拆分（`git show HEAD:<path> | grep -c "^def test_"` vs 改动后同一条命令，均无 `@pytest.mark.parametrize` 装饰，逐条定义即逐条用例）：

```
tests/test_gt_revisions_and_as_signed.py      新文件           23 条
tests/test_gt_facts_staging_sm25.py           新文件            5 条
tests/test_as_measured_facts_layer.py         39 -> 43         +4 条（B1）
tests/test_tarch_converter_reproducibility.py  6 -> 13         +7 条（F-D）
                                                          合计   39 条
```

`23 + 5 + 4 + 7 = 39`，与 `3292 - 3253 = 39` 逐位对上。⚠️ 过程记一笔：我最初口算成 40（把 `test_tarch_converter_reproducibility.py` 记成 8 条），核对 `git show HEAD:... | grep -c` 的精确 diff 后发现是 **7 条**——之前 `-k "f_d"` 选中的「8 items」里有一条 `test_ezdxf_default_writer_matches_converter_writer_except_pinned_metadata`（改动前就有的旧测试）被字符串 `f_d` 意外命中（`ezd**xf_d**efault` 里的子串），不是我加的第 8 条。这条也写进来，作为「算总数先看 diff 不看子串命中」的一次实测记录。

---

## 五、`git diff --cached --numstat`

⛔ 只 add 了下列明确列出的路径，未用 `-A`/`.`；⛔ 未 add 主控自己的 `AI_agent/logs/reviews/request/2026-08-29_o21c_answer_compiler_DRAFT.md`。

```
68	0	AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py
234	0	AI_agent/logs/reviews/execution/2026-08-29_o21b_facts_ledger_execution.md
1	0	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
1	0	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
1	0	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
38	7	src/agent/judge/as_measured.py
93	0	src/agent/judge/gt_facts_staging.py
59	6	src/agent/judge/gt_raw_layer.py
427	0	src/agent/judge/gt_revisions.py
136	2	src/agent/judge/tarch_normalize.py
48	0	tests/test_as_measured_facts_layer.py
109	0	tests/test_gt_facts_staging_sm25.py
334	0	tests/test_gt_revisions_and_as_signed.py
181	0	tests/test_tarch_converter_reproducibility.py
```

（⚠️ 自指说明：上面这份 `numstat` 是贴入那一刻算的；此后又追加了本条脚注和 §六 两处补写，文件字节数还会再涨——不追着重新贴一遍最终值，这是自指滞后，不是数错。）

---

## 六、我认为最薄弱的一处

**`case_tests/test_baseline/gt_staging/` 目前没有任何写保护**——它是我为了绕开「`gt/`、`gt_sources/` 都只能被各自唯一流程写」这条纪律新开的第三个目录，今天没有任何东西签在里面，所以我判断它不需要继承那条纪律；但这也意味着：任何后续会话都可以不经任何门直接往这里写任意内容，而这里的文件命名（`as_measured.json`/`revisions.json`/`as_signed.json`）和 `gt/<case>/facts/` 将来要放的东西**同名**——如果哪次晋升实现疏忽了校验、直接整目录拷贝，一份从未跑过可复现门的假货可能被当真货晋升。本单没有为它加任何一把锁（既没有"谁能写"的强制、也没有"晋升前必须验证"的代码，只有 docstring 里的文字承诺），⛔ 建议审阅方重点检查这一处：这个目录该不该在本单就配一把"至少写入必须经过 `write_facts_candidate` 这一个函数"的结构性限制，而不是仅凭文档自律。
⭐ **我判断最小的结构性限制应该长什么样**（一句话）：让 `write_facts_candidate` 在落盘前**强制调用一次 `verify_as_signed_reproduction`**（今天是调用方自己决定要不要调用，见 R2 的函数文档），这样"写进 `gt_staging/` 的东西"和"能通过可复现门的东西"就是同一个不可分的动作，而不是两个靠纪律绑在一起的动作——不解决"谁能写这个目录"，但至少让"写进去的一定是真的"从约定变成代码事实。

其次是 R3（B1）本身：我判断"外部锚"在当前约束下只能退化为"计算方法可审计"而不是真正的签名，这个判断依赖两个事实核查（无 GPG、无既有签字字段），如果审阅方发现这两个前提有误，R3 的结论需要重新推。

---

## 七、Commit

`9f0266b` on `08.23_AsDrawnReading`（14 files changed, 1751 insertions(+), 15 deletions(-)）
