# （orchestrator 前言）· 本文正文为 GLM 家族裁决原文，逐字未改

- **落库**：2026-08-26　**审阅方**：GLM 家族（`glm-5.3`，`scripts/glm_code.sh` headless）
- **被审**：`b735db4` + `8ea9aca`（起点 `10f1469`）· 施工方 = **GPT 家族**（`gpt-5.6-sol`）
- 请求单 → [`../request/2026-08-26_f90_rework_crossreview_glm.md`](../request/2026-08-26_f90_rework_crossreview_glm.md) ·
  派工单 → [`../request/2026-08-26_f90_rework_four_blockers_dispatch.md`](../request/2026-08-26_f90_rework_four_blockers_dispatch.md) ·
  施工报告 → [`../execution/2026-08-26_f90_rework_construction_report.md`](../execution/2026-08-26_f90_rework_construction_report.md)

## ⭐ 结论：**APPROVE-WITH-FINDINGS**（0 阻断 / 7 不阻断）

**orchestrator 认为本轮复核最值钱的三件**（⛔ 不是复述结论，是它做了送审方没做的事）：

1. ⭐⭐⭐ **它自己造了一个「两层楼 + 二层零窗」的端到端用例**，实测 `boundary_complete 32/32 pass`
   ⇒ **换信任根的核心收益是真实可兑现的**，不是纸面推理（旧根按窗户 fail-closed，零窗层根本进不了桥）。
2. ⭐⭐⭐ **它做了施工方没做的「逐分支摘除」**，把「变红」升级成「**定向**变红」：
   摘 F-101 的修复 ⇒ 只有 `[locator]` 红、`[view_observation]` 仍绿。
   ⇒ 并由此撞出 **实验 2c：「locator 不在 catalog」那个分支目前零锁覆盖**（把它的 reason 错标，七锁全绿）。
3. ⭐⭐ **它点了 orchestrator 一处流程问题**（findings #4）：我把复核请求单里的「范围」文件清单
   **改写成了实际 diff 的文件集** ⇒ **验收标准跟着结果走**。这条我认。

**⚠️ 必须防的一句话**（复核方原话，orchestrator 全文照收）：
> 任何把本单记成「sm25 真实产物判分已恢复」或「F-90 已在真实 case 上验收」的表述**都是错的**。

---

# GLM 跨家族复核裁决 · F-90 返工五项（含 F-102/F-103 验收通道）

- **被审 commit**：`b735db4` + `8ea9aca`（起点 `10f1469`，diff `git diff 10f1469..8ea9aca`）　**审阅方**：GLM 家族（glm-5.3）
- **请求单** → `AI_agent/logs/reviews/request/2026-08-26_f90_rework_crossreview_glm.md` · 派工单 → `…four_blockers_dispatch.md` · 施工报告 → `…execution/2026-08-26_f90_rework_construction_report.md`（工作树更正版） · 上游裁决 → `…verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md`
- ⚠️ **口径变化声明**：复核期间 orchestrator 落了用户 08-26 纠偏（plan.md「五之四」）：**旧 sm25 产物不再作验收对象**，判据 A/B 作废，改为「五处各自在夹具上有分辨力 + 全仓绿」；并预告「裁决回来后作废第 2 问 + 必答第 1 问」。我按新口径裁决，**两问的实测读数仍完整给出**（信息本身有效，只是不再作验收锚）。

## 结论：**APPROVE-WITH-FINDINGS**

五项修复在对抗性实测上全部成立——含一个我构造的、比现有任何锁都强的形态（**两层楼且二层零窗，端到端 32/32 pass**）；锁具备真实的**定向**分辨力（逐分支摘除只红对应锁，非整体变红）；范围与容差合规；全量 `3029 passed, 13 xfailed` 独立复现。发现 **0 条阻断、7 条不阻断 findings**，其中两条（「查无此源」分支**零锁**且错命名；reading 侧 NA `detail` 语义变化未升 helper identity = F-102 病理微型重演）应尽快开小单处理。

程序合规：主树未改任何被跟踪文件、无 add/commit/push/stash/切分支；对照实验全部在 `/tmp/glm-f90-review/wt`（8ea9aca detached worktree），**已 `git worktree remove --force` 并确认列表无残留**；未 `pip install -e`、未动 `/opt/venv`；实验产物只在 `/tmp`。主树现存三处未提交修改（CLAUDE.md / plan.md / 施工报告）均为 orchestrator 既有改动，非我所写。

---

## 一、六条重点

### 1. ⭐⭐⭐ 新信任根换了，换对了吗？——**换对了，信任链变强了**（附零窗楼层端到端实测）

**a) `_check_floor_order` 是否在所有到达判分的路径上都必然跑过？——是，且至少三遍，无绕过路径。**

信任链逐环核实（可复现：读以下四处代码，无需运行）：

- `VerifiedWindowHostProof` 构造被 `_PROOF_CONSTRUCTION_TOKEN` 锁死（`src/agent/geometry/build.py:100-103`：`if _token is not _PROOF_CONSTRUCTION_TOKEN: raise TypeError`）——**外部无法伪造 proof 实例**。
- 唯一签发口 `_issue_verified_window_host_proof`（`build.py:179-197`）无条件先调 `_reverify_window_host_proof`（`build.py:146-165`）。
- `_reverify` → `_proof_parts`（`build.py:124-143`）→ `verify_window_resolver_inputs_artifact`（`src/agent/correction/window_sources.py:1105-1141`）——该函数**不是**「解析+信任」，而是 `window_sources.py:1131` 重新调 `build_verified_window_resolver_inputs` 全链重建（`_catalog` → `_claim_links` → **`_check_floor_order`，window_sources.py:1083**），并逐字段比对 `rebuilt.inputs != artifact.inputs` 即拒（`:1137-1140`）。
- 判分侧：`score_service.py:525` 先 reverify 一次、`:547-549` `_resolver_inputs_from_verified_proof` 内部**又** reverify 一次；`window_host_proof=None` 时 `:521-528` 直接 `_raise_score_input_contract("score_product_identity_invalid")`——不存在无 proof 的 correction 判分路。
- 官方口子上 bindings↔catalog↔gt 三方另有一道：`scripts/tool_scripts/run_stage.py:2149` 调 `validate_score_view_bindings_against_gt`（`src/agent/judge/score_inputs.py:151-175`，含 floor_ref 与 gt 楼层位置的 B-M 校验）。

**b) `_resolver_inputs_from_verified_proof` → `_reverify_window_host_proof` 验什么、不验什么？**

- **验**：三份 raw bytes 可解析；`artifact.output_sha256 == sha256(raw_output_bytes)` 与 `claims.resolver_inputs_sha256 == inputs.content_sha256` 双哈希绑定（`build.py:138-142`）；resolver artifact canonical 字节（`window_sources.py:1115-1120`）；direction facts **独立重派生**不信任持久化元组（`:1124-1127`，docstring 明言未来 azimuth 适配器不得回退）；catalog 全链（含 `_check_floor_order`）重建重跑；`recompute_window_host_claims(output) == artifact.claims`（`build.py:158-164`）。
- **不验**：output 的几何合法性（归 deterministic_core_proof / validator，另案）；score_bindings 与 catalog 的一致性（归上面 run_stage:2149 那道门）。边界划分清楚，没有发现既当运动员又当裁判的地方。

**c) 零窗楼层实测（⛔ 按要求构造用例，不是只读代码）**：`/tmp/glm-f90-review/zero_window_floor.py`——完整真实链（`build_verified_window_resolver_inputs` → `finalize_correction_draw` → `WindowHostsArtifactV1` → `_issue_verified_window_host_proof` → `build_geometry` → `score_typed_attempt`），两层楼 `f1(z=0, 一扇窗)` + `f2(z=3.0, **零窗**)`，manifest 两个 plan entry（floor_ref 1/2），GT 两层 `F1/F2`，bindings `plan-1f→F1, plan-2f→F2`。实测输出：

```text
windows [('w1', 'f1')]   floors [('f1', 0.0), ('f2', 3.0)]
DERIVED_BRIDGE {'f1': 'plan-1f', 'f2': 'plan-2f'}      ← 零窗层 f2 入桥
payload_kind c2_scored
boundary_complete eligible=True verdict=pass denom=32.0 passing=32.0 failing=0.0
windows_placed / window_plan_geometry eligible=True verdict=pass
existence/host/along/width eligible_units=1.0 result=complete   extras ()
ZERO_WINDOW_FLOOR_SCORED_OK
```

`32/32` = 两层全部边界段都判了（单层锁只有 16）。**换根的核心收益（零窗楼层可判分）是真实可兑现的**，不是纸面推理。旧根（窗户 host 溯源 fail-closed per-window）下零窗层根本进不了桥。

**d) 变强还是变弱？** 变强，理由三点：① 新根不是引入**第二份**信任输入，而是把**同一 proof** 已冻结的 catalog 信息（manifest floor_ref 1..N 连续 + 与产物楼层数量一致，`window_sources.py:1042-1049`）用全——没有新增攻击面；② 窗溯源没有丢，降级为**佐证**且不一致响亮失败（`score_service.py:308-319`，reason `window_host_disagrees_with_verified_plan_floor_catalog`，摘除该检查时对应锁定向变红，见重点 3 实验 2a）；③ 重建逻辑**镜像了生产者定义**（judge 侧 `sorted(floors, key=z_floor)` + `enumerate(start=1)`，`score_service.py:261-263` ↔ 生产侧 rank，`window_sources.py:1051`）——符合本项目 [[recompute-gate-must-mirror-producer-definition]] 的教训。一个代价记为观察项：两侧排名逻辑互不引用，未来改生产侧排名定义时 judge 侧会静默分歧（findings #7）。

### 2. ⭐⭐ 判据 A 复现——**复现成功，逐位一致**；含义判断：**同意 orchestrator 的「只证明不再是第一块拦路石」**，且可更精确

复现命令：`python /tmp/glm-f90-review/criterion_a.py`（复制真实 R0 到 `/tmp`，走 `scripts.tool_scripts.run_stage._grade_typed_attempt_artifacts`，patch `score_schema.load_cached_score` 观测缓存）。实测输出：

```text
module_under_test /workspaces/EnergyPlus-Agent-dev/src/agent/judge/score_service.py
before_helper reading_opening_global_assignment_v1
before_payload rejected score_view_binding_invalid
cache_hits [False]
after_helper correction_opening_global_assignment_v5
after_payload not_applicable / unsupported_view_contract / score_identity_support_ambiguous
official_score_payload_detail score_identity_support_ambiguous
score_criteria_count 0
```

与施工报告 §七 逐位一致；我未采信其贴文，是独立跑出来的。

**「报错码换了一个」证明了什么**：我同意 orchestrator 的判断，并可更精确——这次前进**主要证明第 4 项（F-101）与第 1 项（F-102）**：真实 R0 的 host source 是 `src:<64hex>` 形式（上游裁决 §三实测 `host_source_ids ['src:d2cf…']`），旧 `split("/",1)[0]` 必然把它错拒为 `window_host_source_not_a_registered_plan_input` ⇒ `score_view_binding_invalid`；修复后走通并 cache miss 重算。而**第 2 项（plan matcher 桥）与第 3 项（source-view 桥）的缺陷形态挡在 F-99 之后**（`score_identity_support_ambiguous` 在 `scoring.input_identity` gate，先于 matching gate 炸）——判据 A 对这两项的证明力弱，它们的证据是我的定向摘除实验（重点 3）。**不证明「四条各自都修对了」——每条的对错要各自的锁来证，好在这次锁是真的有分辨力（见下）。**

⚠️ 按 08-26 纠偏，本问已作废（旧产物不再作验收对象）；读数留作参考——它仍证明判分器层的修复在真实数据上工作。

### 3. ⭐⭐⭐ 七把 fail-closed 锁——**有真实定向分辨力**（我做了施工没做的逐分支摘除）；两个错命名分支**该给专属 reason，且其中一个分支目前零锁**

施工的「摘掉两个 bridge helper ⇒ 七条全红」只证明**接线**。我在 worktree 做了六个更强的实验（均可复现，改动均为「摘单分支/错标 reason」级别）：

| 实验 | 操作 | 结果 | 判定 |
|---|---|---|---|
| 2a | 只删 `window_host_disagrees…` 一致性检查 | `[disagrees]` 1 红 6 绿 | **定向分辨力 ✓** |
| 2b | 只删 `verified_plan_floor_not_registered…` 检查 | `[not_registered]` 1 红 6 绿 | **定向分辨力 ✓** |
| 2c | 保留检查、把「locator 不在 catalog」分支的 reason 错标为 `missing_source_ids` | **7 全绿** | **该分支零锁覆盖**（见 findings #1） |
| 摘 ITEM2 | 不做 `_normalize_correction_plan_floor_ids` 重键 | 双形式红，失败断言 `assert 'fail' == 'pass'`（boundary_complete） | 变红方向正确 = 正是第 6 处缺陷的读数形态 |
| 摘 ITEM3 | `source_view_to_gt_view_ids` 返回 `{}` | 双形式红 | 接线 + 行为双证 |
| 摘 ITEM4（F-101） | 摘回旧 `split("/",1)[0]` | `[locator]` 红、**`[view_observation]` 仍绿** | **完美定向**：旧 split 本来只坏 hash 形式，锁的两种形式各自对准自己的分支 |

结论：**没有发现「无论修没修都红」或「随便动点别的也红」的锁**——每把锁都能区分「自己的修复在不在」。

**两个命名与实情不符的分支——实测坐实，该给专属 reason**。直接调 `_derive_window_floor_plan_sources`（`/tmp` 脚本，SimpleNamespace 构造）：

```text
BRANCH1 locator-not-in-catalog:   {'window_id': 'w1', 'reason': 'window_host_claim_ambiguous_source', 'candidate_inputs': []}
BRANCH2 window-without-host-link: {'floor_id': 'f1', 'window_id': 'w1', 'reason': 'window_host_claim_ambiguous_source', 'candidate_inputs': []}
REFERENCE genuine-ambiguity:      {'floor_id': 'f1', 'window_id': 'w1', 'reason': 'window_host_claim_ambiguous_source', 'candidate_inputs': ['plan-a', 'plan-b']}
```

三种**不同谓词**（catalog 损坏 / 证据缺失 / 真歧义）挤进同一 reason，只能靠 `candidate_inputs` 空不空反推。位置：`score_service.py:205-215`（source is None 分支）与 `:231`（`host_inputs_by_window.get(window.id, set())` 空集分支）。补充两点：① 生产链上这两个分支**不可达**（`_claim_links` 在 `window_sources.py:1004-1006` 保证 link 的 locator 必在 catalog；provenance 有 host 必有 host link），所以它们是纯防御分支——但正因如此，一旦到达就意味着 catalog 损坏这类严重事件，报错名却指向「歧义」会误导分诊方向（本项目 [[whole-stage-redraw-cannot-fix-systematic-field-confusion]] 的教训：门报症状还是病因）；② 实验 2c 证明该分支连 reason 都没被锁断言。**结论：该给（成本≈一个字符串常量 + 一条参数化锁案例）；BRANCH2 与 `missing_source_ids` 是近亲，也应区分。**

### 4. ⭐⭐ 缓存 identity 手工版本——**判定：执行机制，不是根治机制。下一次有人改了语义忘提版本，没有任何东西拦住他**

证据（复现：`grep -rn "CORRECTION_OPENING_MATCHER_HELPER_VERSION\|READING_OPENING_MATCHER_HELPER_VERSION" src scripts tests --include='*.py'`）：全部用法 = 常量定义（`score_schema.py:53-54`）+ `score_service.py:335-337` 引用 + `test_f102` 三处断言。**没有任何机制把实现内容（源码哈希、语义指纹、输出样例）绑进版本号**——`inspect.getsource` 在本仓测试里有先例（如 `test_c2_b4b_score_inputs` 的源码隔离锁）但从不用于版本绑定。

推演「忘提版本」场景：改了 correction 规范化语义、版本仍 v5 ⇒ `ScoreIdentityV9` 完全不变 ⇒ 旧 sidecar cache hit 照常返回修复前结论 ⇒ **test_f102 全绿、全仓全绿、无人察觉**——锁构造旧版本 sidecar 的手法防的是「版本号不同却命中」，防不了「版本号相同但语义已换」。这与 D-1 被点掉的话（一次性检查、非防漂移门）**同构**，明说。本轮明令不许实施派生摘要 ⇒ 维持现状是对的，但派生摘要（从实现闭包派生组合摘要）应尽快另开单，在那之前 code review 惯例是唯一防线。

### 5. ⭐ `test_f102` 的前提——**响亮红，不会静默恒真**（忠实模拟实测）

施工 §12.4 担心前提消失。我做忠实模拟（不是手工构造 sidecar——那会被 `ScoreSidecarV9` 的 artifact-contract 校验拒掉——而是把判据 A 实验中官方口子**真实跑出的** v5 sidecar 拷进 worktree 的 R0 归档，模拟「重跑并提交」）：

```text
simulated committed sidecar matcher: correction_opening_global_assignment_v5
FAILED tests/test_f102_score_cache_identity.py::test_pre_f102_real_sidecar_misses_through_official_flow
tests/test_f102_score_cache_identity.py:44: AssertionError     ← assert before[...opening_matcher] == v1
（恢复归档后 1 passed）
```

**前提断言本身就是锁的第一道**（`test_f102:44-46`），前提消失 ⇒ 立即 AssertionError——满足「回归用例自证前提」的精神，良性失败。但前提确实依赖「归档 R0 的 sidecar 永不被重跑提交」这条**仓库纪律而非机制**；锁的 docstring 应写明这一前提与失效后果（现为隐式）。另附「摘得动」复现：worktree 里把 v5 常量改回 v4 ⇒ `E assert [False, False, False, True] == [False, False, False, False]`（第 4 次调用错误命中 v4 sidecar = F-102 复发路径），恢复后绿。

### 6. ⭐ F-103 只加信息没改分类——**查得实，全仓（含扩大面）零值消费者；但发现一个施工没报的侧面**

我的 grep（复现命令照抄即可）：

```text
payload.detail 属性访问：全仓 0 处（唯一 = 新增 run_stage.py:2189 getattr(result.payload, "detail", None)）
["detail"] 键访问：仅 render_reading_grade.py:93 —— 读的是 reading grade 文件自己的行数据，与 NotApplicablePayloadV9 无关
judge_packet 新键 score_payload_detail（run_stage.py:2253）：纯加法，不挤占既有键
reason 的 Literal（score_schema.py:1179-1185，5 个取值）在 diff 中未动 ✓
```

施工「改前 grep 全仓零个 `payload.detail` 消费者」**属实**。两处小勘误/缝隙：① 施工与请求单都说「reason 的**四个**取值」——schema Literal 是 **5** 个（`unsupported_reading_contract/unsupported_gt_profile/unsupported_view_contract/no_scorable_reading_channel/scorer_internal_failure`），「四个」是 `_total_failure_result` 实际能产出的子集，表述不精确（不影响结论）；② **新缝隙（findings #2）**：`detail` 取值变化（`reason` → `error.code`，`score_service.py:899`）同样作用于 **reading 侧** NA payload（`_total_failure_result` 两 stage 共用，调用点 `:1003,:1010`），而 reading 的 `opening_matcher` 恒为 v1（`score_schema.py:53`）——旧 reading NA sidecar 会 cache 命中并继续返回旧 detail 值。**这是 F-102「语义变了 identity 没变」的微型重演**；当前 detail 零代码消费者 ⇒ 无实害，但结构上应记。

---

## 二、验收判据

**1. 全量绿——独立复现，逐位一致**：`python -m pytest -n auto -q`（主树 `840ffc3`；已核 `git diff 8ea9aca..840ffc3` 仅 3 个 `AI_agent` 管理文档，**代码与被审 `8ea9aca` 等价**）：

```text
3029 passed, 13 xfailed, 212 warnings in 831.93s (0:13:51)   EXIT=0
```

与施工报告 §九（`3029 passed, 13 xfailed, 212 warnings in 948.23s`）passed/xfailed/warnings 三数逐位相同。已知 `test_zone_agent` 凭据坑未触发（环境有凭据），无任何红。

**2. 范围——实质合规，但有三处表述不一致须记录**：`git diff --name-only 10f1469..8ea9aca` = 9 个文件，全部落在允许的目录级范围（`src/agent/judge/` 4 文件 + `run_stage.py` + `tests/` 3 文件 + 那一份施工报告）；`src/agent/pipeline*`、`state.py`、`src/validator/`、`src/agent/correction/`、gt **零改动**（逐一核对过 `git diff --name-only` 输出）。但：**派工单 §一 的括号列举（score_service/segment_score/opening_claim_score/score_schema）不含实际被碰的 `score_inputs.py` 与 `reading_typed_score.py`**——主句「允许碰 `src/agent/judge/`」在目录级覆盖它们、且第 3 项「复用已有实现、不写第二套」必然要求抽共享 helper，**故不判越权**；然而请求单验收判据 2 的文件列表已悄悄改写成实际 diff 的文件集——**验收标准跟着结果走**这个动作本身应点名（findings #4）。同理 `run_stage.py` 的 2 行是 F-103 的 `score_payload_detail` 暴露，超出派工单「仅第 1 项的缓存 identity 相关处」的字面——F-103 是施工中发现、orchestrator 采纳新增的「第 1b 项」，**派工单从未回写这一范围演进**。另：施工报告的工作树版（含更正与 §12）与提交版 `8ea9aca` 不同——更正内容我逐字读过，属诚实更正（撤回 cell gap 误报），非篡改证据，但「送审 diff 应含报告最终态」这一点留档。

**3. 容差零改动——独立确认**：`git diff 10f1469..8ea9aca -- src/configs/` 输出为**空**（`case_tests/test_baseline/gt/` 同为空）。

---

## 三、必答

**1. 判据 B 的「做不到」——认，且我认为这不是偷懒，是题目自相矛盾。** 证据链：① 0.12m 不是某个可拨的输入参数，而是**全部 16 段 facade 的系统性坐标基准差**——实测 R0 `output.json`：`North 14.88/24.89`、`South 0.12/14.12`、`East/West` 同构（每段都带半个 240 墙厚的偏移，两层共 16 段）；「中和它」= 改产物几何 = 新 `output_sha256` = 六件套（`output.json`/`window_resolver_inputs.json`/`window_hosts.json`/`deterministic_core_proof.json`…，已 ls 核实齐全且被跟踪）全部作废重签——而判据 B 同时要求「其余一切保持真实（同一份产物）」，**逻辑上不可同时满足**。② 冻结结构核实：`window_resolver_inputs.json` 内嵌 `producer_draw_canonical_bytes`，`verify_window_resolver_inputs_artifact`（`window_sources.py:1131-1140`）对其全链重建比对——改 producer 任何一处即拒；output 与 proof 双哈希绑定（`build.py:138-142`）。三次尝试的 validator 拒绝（`zero_segment_candidates` / `invalid_interior_edge_pair` / `cell 边长 0.005 < 0.100`）与该结构完全自洽，可信。③ 施工**没有伪造十判据表**，停报了——这正是上一轮缺的动作。我没有再花一轮去试第四条中和路径：用户 08-26 纠偏已把验收对象整体作废、F-99 挂起，在「题已被判错」的前提下复现「题做不成」没有增量信息；我核实的是「为什么做不成」的结构性原因（如上）。若必须一句话回答「有没有既不绕过 proof、又不扩范围的路」：**没有——任何路要么改产物（重签=扩范围）要么绕过 proof。**

**2. 五条停报——逐条认同五条全成立；第 6 条候选：有（弱）。** 29 = 上一单验收判据「必须真的判出分」无合法出口（派工单 §〇 自认）✓；30 = helper 版本应逐项提档 v3/v4/v5 而非一次（`8ea9aca` 提交信息明文「施工席位指出…自相矛盾，属实，已采纳」）✓；31 = fail-closed reason 数量写错（派工判据 C 第 6 条列 4 个、实际 7 个；「新加两个」实为三个）✓——我实测七锁参数表确认 7 个；32 = 换根第三条路（派工单没给）✓——且我实测了它的实质收益（零窗楼层 32/32，旧根做不到）；33 = 判据 B 不可独立中和 ✓（见必答 1）。**第 6 条候选（我提，弱）**：判据 A 原版把「前进到 `score_product_segment_unresolved`」**写死**为通过标志，实际到达的是 `score_identity_support_ambiguous`（`scoring.input_identity` gate，比派工单预期的 matching gate 更早）——按字面判据 A 应 FAIL，orchestrator 当场更正接受（同为 F-99 的 14.0/14.12 家族，更正合法）；但「把具体报错码写死为判据」又一次被证明脆弱，与 28 条「写死期望」同病。次弱候选：派工单位置指针与范围列表与实际不一致（验收判据 2 详述）。

**3. 证据强度直说。** 在「真实 case 十判据读数至今不存在」的前提下：**按 08-26 纠偏后的现行口径（五处各自在夹具上有分辨力 + 全仓绿），证据充分**——五处各有定向红绿对照（我全部独立复现，且给出了比施工更强的定向性证据：ITEM4 摘除只红 `[locator]` 不红 `[view_observation]`、2a/2b 只红对应锁、2c 暴露无锁分支），外加零窗楼层端到端 32/32。**按旧口径（真实 case 判出分），证据强度为零**——而这不是本单施工的错（F-99 挡着、验收对象已被作废）。必须防的一句话：**任何把本单记成「sm25 真实产物判分已恢复」或「F-90 已在真实 case 上验收」的表述都是错的**；施工报告 §12.5 自己写清了这点，诚实。最后提醒：本单修复全部在**产物无关的判分器层**，换新产物后行为没有真实数据背书——一体改落地后的第一考要盯，尤其是换根后的 catalog 桥在新 reading 产物形态（如 elevation 主导）下的表现。

---

## Findings

### 阻断（无）

### 不阻断

1. **「locator 不在 catalog」分支：错命名 + 零锁覆盖。** `src/agent/judge/score_service.py:205-215`。复现：worktree 实验 2c——保留检查、只把该分支 reason 错标为 `missing_source_ids`，七锁**全绿**；纯调用实测该分支报 `window_host_claim_ambiguous_source` + `candidate_inputs: []`，与真歧义（双候选）同名。「查无此源」在生产链不可达（`window_sources.py:1004-1006` 已保证），但一旦到达= catalog 损坏级事件，错名误导分诊。处置：给专属 reason（如 `window_host_claim_source_not_in_catalog`）并补参数化锁案例；同文件 `:231` 的「有 host provenance 但无 host link」空集分支同理。
2. **reading 侧 NA `detail` 语义变化未伴随 helper identity 升版（F-102 病理微型重演）。** `score_service.py:899`（`_total_failure_result` 两 stage 共用）+ `score_schema.py:53`（reading 恒 v1）。旧 reading NA sidecar 将 cache 命中并返回旧 detail 值。当前 detail 零代码消费者 ⇒ 无实害。处置：下次动 reading 判分语义时必须升 `READING_OPENING_MATCHER_HELPER_VERSION`，或现在就升一档并加旧 sidecar miss 锁。
3. **手工 helper 版本 = 执行机制非根治机制。** `score_schema.py:53-54`；全仓无任何实现内容→版本绑定。忘提版本时零拦截（锁全绿、缓存照常命中旧 sidecar）。处置：派生摘要另开单（本轮禁令维持）；在那之前 review 惯例是唯一防线，应在派工单模板里写明「动 judge 语义必查 helper 版本」。
4. **范围表述不一致（验收标准跟着结果走的痕迹）。** 派工单 §一 括号列举 ≠ 实际 diff ≠ 请求单验收判据 2 列表；`run_stage.py` 2 行（F-103）超出「仅第 1 项」字面。目录级主句覆盖 ⇒ 不判越权，但派工单应回写范围演进（F-103 第 1b 项系施工中发现后采纳）。复现：对照三个文档的文件列表与 `git diff --name-only 10f1469..8ea9aca`。
5. **`test_f102` 前提依赖仓库纪律而非机制。** 忠实模拟实测：sidecar 被重跑提交 ⇒ 锁在 `test_f102_score_cache_identity.py:44` **响亮红**（良性），但前提本身一次性。处置：锁 docstring 写明前提与失效后果；长期看随 findings #3 的派生摘要一并根治。
6. **施工报告小勘误**：「reason 的四个取值」—— schema Literal 为 5 个（`score_schema.py:1179-1185`），四个是 `_total_failure_result` 实际产出的子集。不影响结论，改字即可。
7. **（观察项）judge 侧 z 排名逻辑镜像生产者定义但两侧无互引锁。** `score_service.py:261-263` ↔ `window_sources.py:1051`。未来改 `_check_floor_order` 排名定义时 judge 侧会静默分歧。处置：在 `_check_floor_order` 的 docstring 或改名处加指针；或加一把「两侧行为一致」的对照锁。

---

## 附：复现环境说明

- 所有实验脚本与输出存于 `/tmp/glm-f90-review/`（`criterion_a.py` · `zero_window_floor.py` · `pytest_full.log` 等），worktree `/tmp/glm-f90-review/wt` 已 `git worktree remove --force` 并经 `git worktree list` 确认无残留。
- 零窗实验首跑曾在 `derive_reference_ledger` 炸 `va_claim_ledger_invalid`——那是**我 fixture 的毛病**（两个 plan binding 共指同一 `gt-plan` view），修正为 `gt-plan-1f/2f` 后通过；非被审代码缺陷，留档以防后人误读。
- 被审对象为主树代码（`840ffc3` 的 `src/`/`tests/`/`scripts/` 与 `8ea9aca` 逐字节等价，已核 `git diff 8ea9aca..840ffc3` 仅 `AI_agent/` 三文档）；worktree 实验则跑在被审 commit `8ea9aca` 原文上。
