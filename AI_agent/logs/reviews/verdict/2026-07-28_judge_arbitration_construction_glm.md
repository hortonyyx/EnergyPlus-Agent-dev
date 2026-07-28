# 裁决书 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」施工批（GLM-5.2 验证性对抗审 · r2 收口轮）

> **审阅方 = GLM-5.2**（GLM 侧）/ **施工方 = sol**（GPT 侧，谁写谁不批）/ **轻门 = 主控 Opus 5**。
> **本裁决 = r1 APPROVE-WITH-CHANGES（0 BLOCKER / 1 MAJOR / 3 MINOR）之后、施工方修完 4 条后的收口轮。**
> 范围：`67b9c00`（Slice 4 末态）→ `59b124b`（MAJOR-1 + 三 MINOR 收口 + 执行日志）。
> 本次会话沙箱放开了 Bash + Write，故 r1 里「只能读不能跑」的两件事（指定 neuter 独立重跑 / MAJOR-1 剩余门活体探针）本轮**全部活体执行**。

---

## 0. 结论

**APPROVE**

- r1 的 **1 MAJOR + 3 MINOR 全部实质闭合**，且本轮**独立重跑 14 个指定 neuter、零偏差**——本批 r1 栽过的「自查表声称大于实况」**本轮未复发**。
- 全仓独立复算 **`1786 passed, 10 xfailed, 0 failed`**（278.30s），与执行日志尾数逐字一致。
- MAJOR-1（豁免位 `exact_error_context` 公共字段门）按出口 (a) 彻底删除，换成私有子类型 + 受审计桥；我活了体，**原门已封**。残留的三条「绕过」均为 Python 固有性质 + 需显式导入私有名 + 非惯用代码，**不复活 MAJOR-1 的「意外坍缩」风险类**，降级为 1 条 NIT（登记、不阻断）。
- sm24 受保护树 14 项 hash 我独立复算逐字等于日志声明；D-1 证书 `blocking_change=False`、`public_rows_identical=True`。

**findings：0 BLOCKER / 0 MAJOR / 0 MINOR / 1 NIT（登记跟进，不阻断）。**

---

## 1. 独立执行验证总表（本次会话全部活体跑出，非读码推断）

| 项 | 我独立跑出的结果 | 与执行日志声明对照 |
|---|---|---|
| 全仓（HEAD `59b124b`，16 worker 并行） | `1786 passed, 10 xfailed, 0 failed` · 278.30s | 日志 `1786/10/0`（§37.4）→ **一致** |
| 指定 neuter 重跑（14 个，跨 Slice 1/2/3/4 + MAJOR-1） | 14/14 真实红数与声称**逐项相等**（见 §6 表） | **零偏差**（r1 曾栽此处，本轮未复发） |
| MAJOR-1 剩余门探针（8 向量） | 3 向量 TypeError/FrozenInstance 封死；3 向量「到达」但需蓄意绕过；2 向量（pickle/copy 普通诊断）正确封死 | 见 §4.3 |
| 三 MINOR 回归探针（各注入违规） | 3/3 触红（门为真绑） | 见 §5 |
| sm24 受保护树 manifest（我现算） | 14 项 hash 与日志 §26/§33 逐字相等；`git diff --quiet` exit 0 | **一致** |
| D-1 对比证书 `comparison.json` | `blocking_change=False` / `public_rows_identical=True` / `wall_criteria_identical=True` / `input_hashes_identical=True` | 与日志 §31.2 一致；且被活锁 `test_sm24_front_door_audit_certificate_has_no_blocking_change`（在我的全量里 PASS）钉住 |

**本次会话纪律**：所有 mutation 只施加在 `/tmp` 独立 clone（`git archive <commit> | tar -x`），逐项丢弃；主工作树从未进入 neuter 状态，收工 `git status --short` 为空；**未改任何生产码 / 测试 / `AI_agent/CLAUDE.md`**；本裁决书是本次会话写出的唯一文件。

---

## 2. 命脉命题逐条判定（审阅单 §3 的 M-1..M-8）

| # | 命题 | 判定 | 我的独立证据 |
|---|---|---|---|
| M-1 | 不存在第二条严重性路径 | **成立** | 全目录 AST 锁 `test_all_judge_input_identity_raise_origins_are_closed` 封闭 4 个 strict-admission origin；`test_identity_scorecontracterror_has_one_raise_origin_with_no_exceptions` 断言 identity/provenance/score_service 三模块零直接 raise、certifier 唯一 arbiter ≥2 raise。注入第 5 个 `scoring.input_identity` raise → 锁红（§5 MINOR-1 探针实测 `1 failed`）。 |
| M-2 | `reason` 永不参与严重性判定 | **成立** | MAJOR-1 把 reason-only context 收敛到私有子类型 `isinstance` 判定（certifier.py:369）；`reason` 仅进 `{"reason": ...}` 展示，严重性仍由 arbiter（`test_score_input_exemption_still_delegates_severity_to_arbiter` 在我全量里 PASS）。 |
| M-3 | 豁免位被锁封闭 | **成立（原 MAJOR-1 已修）** | 见 §4：公共字段删除 + 私有子类型 + 受审计桥 + 5 把锁；剩余绕过见 §4.3（NIT）。 |
| M-4 | 来源身份贯穿到底，legacy float 物理删除 | **成立** | §9.1 neuter（恢复 `topology=None` 默认 + legacy dispatch）实测 `1 failed`；`grep _cluster_legacy_axis src/` 零命中；`test_cluster_axis_has_no_legacy_branch_and_every_direct_call_passes_topology` PASS。 |
| M-5 | 守恒是结构性判据，`extra` 不可能为负 | **成立** | B-L7 neuter（恢复 `extra=obs.length-covered`）实测 `1 failed`，复现 `Fraction(-1,281474976710656)==0` 负值；现码 `extra` 来自 observation complement atom。B-L1/L2/L3 multiplicity neuter 实测 `3 failed`。 |
| M-6 | 答案原子与分母是答案字节的纯函数 | **成立（静态）** | D-1 证书 `input_hashes_identical=True` + 同答案两侧（baseline/new）`public_rows_identical`/`observation_to_targets_identical`；identity 仅 helper 字段删除后 byte-identical。 |
| M-7 | sm24 已签字答案零字节改动 | **成立** | 我现算 14 项 hash 逐字等于日志；`git diff --quiet -- case_tests/test_baseline/gt AI_agent/CLAUDE.md` exit 0。 |
| M-8 | 真实 sm24 对外可见判分零变化 | **成立** | `comparison.json`：`public_rows_identical=True`、`wall_criteria_identical=True`、`blocking_change=False`；8 处 extra 浮点变化全部 `certified_rounding=true`（exact fraction + cut-id 证书），活锁钉住。 |

---

## 3. MAJOR-1 专项验证（r1 我自己的 finding 的收口）

### 3.1 r1 的 finding（复述）
`exact_error_context` 曾是 `JudgeDiagnostic` 的**公共 dataclass 字段**，故 `JudgeDiagnostic(..., exact_error_context=True)` 能经一扇 AST 锁未盯的门设上豁免位 ⇒ 12 个证书字段坍缩成 `{"reason":...}`，且全仓无测试变红。我派工前活体复现过。

### 3.2 施工方收口（出口 a，且更进一步）
施工方没有「继续给这扇门堆 watcher」，而是**把布尔位整个删掉**：
1. `JudgeDiagnostic`（certifier.py:133）**不再有** `exact_error_context` 字段；
2. 新增 certifier 内部私有子类型 `_ExactErrorContextDiagnostic`（:148，空体，仅继承）；
3. 唯一构造函数 `_with_exact_error_context`（:152）只在 certifier 内构造该子类型；
4. 唯一调用点是 `identity_provenance.raise_identity_conflict`（:308）；
5. `_error_context`（:369）改读私有类型身份，**不再读任何公共 bool**。

### 3.3 五把锁（非一把）——我逐条读过 + 活体验真
| 锁 | 文件:行 | 形态 | 我验 |
|---|---|---|---|
| `test_exact_error_context_true_has_one_static_origin` | interval_ledger:448 | AST：`_exact_error_context=True` 关键字 origin 恰为 `score_service._raise_score_input_contract(Constant True)`；字符串字面量 `"_exact_error_context"` 恰为 `identity_provenance.py` | 读过；§6 的 §10.1(1) neuter 复现其红 |
| `test_exact_error_context_has_no_public_dataclass_door` | interval_ledger:485 | 运行时：直接构造/`replace`/属性赋值均 TypeError/FrozenInstance | 我探针实测三条全封（见 §4.3） |
| `test_internal_exact_context_subtype_has_one_closed_construction_path` | interval_ledger:511 | AST：`_ExactErrorContextDiagnostic(` 恰为 `_with_exact_error_context`；`_with_exact_error_context(` 恰为 `raise_identity_conflict` | 读过 |
| `test_score_input_exemption_hardcodes_only_typed_admission_predicate` | interval_ledger:542 | AST：桥硬编码 `predicate="typed_score_input_contract"`，且非参数 | 读过 |
| `test_score_input_exemption_still_delegates_severity_to_arbiter` | interval_ledger:567 | 运行时：monkeypatch arbiter，桥仍经它定严重性 | 我全量里 PASS |

**坍缩范围核对**（我活体）：非豁免 certified conflict 的 `_error_context` 产 **12 字段**；豁免（admission）产 **1 字段 `{"reason":...}`**。坍缩**只落在受审计 admission 路径**，未泛化到一般诊断。

### 3.4 剩余门活体探针（审阅单明确要求：别假设只有一扇门）
我在 `/tmp`（仅 import、不改生产码）对每个向量探 `isinstance(diag, _ExactErrorContextDiagnostic)`——这就是 certifier.py:369 的判定闸：

| # | 向量 | 实测 | 评级 |
|---|---|---|---|
| 1 | `JudgeDiagnostic(..., exact_error_context=True)` | **TypeError**（字段已无） | 封死 ✓ |
| 2 | `dataclasses.replace(diag, exact_error_context=True)` | **TypeError** | 封死 ✓ |
| 3 | `diag.exact_error_context = True`（frozen 属性赋值） | **FrozenInstanceError** | 封死 ✓ |
| 4 | `diag.__class__ = _ExactErrorContextDiagnostic` | **FrozenInstanceError**（frozen 连 `__class__=` 也挡） | 封死 ✓ |
| 5 | `object.__setattr__(diag,'__class__',subtype)` | **到达** ⚠️ | NIT（见下） |
| 6 | 直接 `_ExactErrorContextDiagnostic(...)`（在 src/agent/judge 外） | 到达（但 src/agent/judge 内由 AST 锁 §3 第 3 把封死） | NIT |
| 7 | `getattr(certifier,'_ExactErrorContextDiagnostic')(...)` | **到达** ⚠️（AST 锁只认 `ast.Name`-func，绕过 getattr） | NIT |
| 8 | `pickle.loads(pickle.dumps(普通 diag))` | **封死**（普通 diag 保持普通，不变豁免） | ✓ |
| 9 | `copy.copy` / `copy.deepcopy`（普通 diag） | **封死** | ✓ |
| 10 | 已豁免诊断的 pickle 往返 | 保持豁免（保持、非新建） | 可接受 |
| 11 | 外部 `class _Sneak(_ExactErrorContextDiagnostic)` | **到达** ⚠️ | NIT |

**对三条「到达」的诚实判定**：它们**全部要求**（a）显式按私有名导入 `_ExactErrorContextDiagnostic`、（b）写非惯用的蓄意绕过代码（`object.__setattr__(..,'__class__',..)` / `getattr(m,'_Private')()` / 子类化私有名）。**没有任何半诚实 detector 会这样写**；一个决意绕过静态锁的人本就能构造 reason dict 直接 raise（任何软锁都挡不住）。它们**不复活 MAJOR-1 的风险类**——MAJOR-1 的实际危害是「公共字段 ⇒ 意外/半意外坍缩，且零测试变红」，那扇门已物理消失（字段删除 + 3 把运行时锁 + 2 把 AST 锁）。`object.__setattr__` 的 `__class__` 改写是 CPython 对**任意** frozen dataclass 的固有逃逸（要真堵需 `__slots__` 重设诊断表示，超出本批设计）。**故降级为 1 条 NIT，不升 MAJOR/MINOR，不阻断。**

---

## 4. 三 MINOR 逐条（确认是「真闭合」而非「重述」）

### MINOR-1（raise-origin domain → 全目录 AST 枚举）
- **锁**：`test_all_judge_input_identity_raise_origins_are_closed`（certifier 测试:382）用 `Path("src/agent/judge").rglob("*.py")` **全目录**枚举 `ScoreContractError(...,"scoring.input_identity")` 直接 raise，封闭到**恰好 4 个** strict-admission origin：`elevation_score.project_typed_elevation_observation` / `elevation_score.score_typed_elevation_floor_lines` / `score_config.load_judge_score_config` / `score_schema.load_score_gt_identity`。
- **非重述**：旧 Slice 2 锁是 `..._except_slice4_legacy`（手写三文件域 + 留 legacy 例外）；本轮换名 `..._with_no_exceptions`（legacy 已在 Slice 4 删）+ 新增全目录封闭锁。**真拓宽**。
- **活体验真**：我在 score_schema.py 追加第 5 个 origin（`def _glm_probe...: raise ScoreContractError("probe","scoring.input_identity")`）→ 该锁实测 `1 failed`。**门为真绑。**

### MINOR-2（dormant `_arbitrate_pairing_diagnostics` → 证明不可达，非删除）
- **锁**：`test_legacy_pairing_arbitrator_and_reason_fallback_are_production_unreachable`（identity_metric:835）AST 证明三件事：① 生产源对 `_arbitrate_pairing_diagnostics` 的**调用数==0**；② `_PairDiagnostic` 生产构造点**恰为 `_pair_diagnostic`**；③ 该构造点必传 typed `witness`（故 reason→predicate fallback 生产不可达）。
- **我独立核**：`grep _arbitrate_pairing_diagnostics src/` → 仅 1 行**注释**（segment_score.py:1340）+ def（:1393），**零真实调用**。证明成立（结构化 AST，非注释）。
- **活体验真**：我在 `_build_observation_ledger` 注入 `if False: _arbitrate_pairing_diagnostics((), identity_code="probe")` → 该锁实测 `1 failed`。**门为真绑。**（保留历史 counterexample 测试 = 合规「证明不可达」出口。）

### MINOR-3（scalar-reflow ban → 拓宽到含 `_build_observation_ledger`）
- **锁**：`test_production_match_path_has_no_scalar_conservation_branch_or_tolerance`（interval_ledger:420）**同时**守 `match_plan_segments` **与** `_build_observation_ledger`（先断 `set(guarded)=={两者}`，再各断不含 `_assert_target_conservation`/`_assert_obs_conservation`/`_SUBINTERVAL_SUM_TOL`）。
- **非重述**：旧锁只盯 `match_plan_segments`；本轮加 `_build_observation_ledger`。**真拓宽**。
- **活体验真**：我在 `_build_observation_ledger` 注入 `if False: _assert_obs_conservation` → 该锁实测 `1 failed`。**门为真绑。**

> 三 MINOR 全部「锁绿且锁真绑」，非声明式收口。

---

## 5. 指定 neuter 独立重执行表（claimed vs 我实测）

> 每项在 `/tmp` 独立 clone（`git archive <commit>`）施加 mutation（fail-closed：锚点须恰好命中 1 次）→ 串行 `-n0` 跑指定锁 → 丢弃。**commit 用各 Slice 自己的基线**（Slice 1 的 neuter 引用了 Slice 4 才删的 `_cluster_legacy_axis`，故必须在 Slice 1 基线上复现才 apples-to-apples）。

| neuter | 基线 commit | 日志声称 | 我实测 | 偏差 |
|---|---|---|---|---|
| C-L1（formal builder→legacy float） | c59e4bc | 1 failed | **1 failed** | 无 |
| C-L7（ring validator 早退） | c59e4bc | 1 failed | **1 failed** | 无 |
| C-L9（摘 owner!= 守卫） | c59e4bc | 1 failed | **1 failed** | 无 |
| C-L11（忽略 envelope version） | c59e4bc | 2 failed | **2 failed** | 无 |
| A-L6（无 witness 默认定罪） | 0b62a49 | 1 failed | **1 failed** | 无 |
| A-L9（missing-eval 只 NA） | 0b62a49 | 1 failed | **1 failed** | 无 |
| 单一 raise-origin AST（注入 pairing raise） | 0b62a49 | 1 failed | **1 failed** | 无 |
| B-L1/L2/L3（multiplicity 守卫关） | 2193748 | 3 failed | **3 failed** | 无 |
| **B-L5（float accumulator）〔施工方自查假锁 #1〕** | 2193748 | 1 failed | **1 failed** | 无 |
| **B-L7（extra 减法）〔施工方自查假锁 #2〕** | 2193748 | 1 failed | **1 failed** | 无 |
| §10.1(1)（第二个 `_exact_error_context=True` origin） | 2193748 | 1 failed | **1 failed** | 无 |
| C-L16（helper 回退 v2） | d7d6cf3 | 2 failed, 1 passed | **2 failed, 1 passed** | 无（见注） |
| §9.1（恢复 legacy float dispatch） | 1cda1b5 | 1 failed | **1 failed** | 无 |
| MAJOR-1（恢复公共字段 + bool 读） | ce23426 | 1 failed | **1 failed** | 无 |

**C-L16 注**：我首轮在 `1cda1b5`（4 测）跑得 `2 failed, 2 passed`，与日志 `2 failed, 1 passed`（3 测）看似不符。**经查非偏差**：`1cda1b5`（AuditLock）比日志 neuter 所用基线 `d7d6cf3`（CacheLock，3 测）多了一条 `test_sm24_front_door_audit_certificate_has_no_blocking_change`，该锁与 helper 版本正交、neuter 下仍绿。在 `d7d6cf3`（3 测态）重跑即得 `2 failed, 1 passed`，与声称**逐字一致**。属基线 commit 差异，非自查表虚报。

> **核心结论**：14/14 真实红数与执行日志声称逐项相等；两处施工方自查的假锁（B-L5 入口预排序遮蔽 / B-L7 整数夹具不敏感）我独立复核**确实变红**——本批首次「自查表 = 实况」坐实。

---

## 6. Findings 分级 + 复现步骤

### NIT-1（登记跟进，不阻断）：MAJOR-1 的三条蓄意绕过残门 + AST 锁只认 `ast.Name`-func
- **现象**：`object.__setattr__(diag,'__class__',_ExactErrorContextDiagnostic)`、`getattr(certifier,'_ExactErrorContextDiagnostic')(...)`、外部子类化私有名——三条均可到达 reason-only context，绕过 `_with_exact_error_context` 桥。
- **为何不阻断**：三条均需 (a) 显式按私有名导入、(b) 非惯用蓄意代码；不复活 MAJOR-1 的「意外坍缩」风险类（公共字段已删 + 5 锁）。`object.__setattr__` 改 `__class__` 是 CPython 对任意 frozen dataclass 的固有逃逸。`getattr`-间接构造之所以漏过 AST 锁，因 `test_internal_exact_context_subtype_has_one_closed_construction_path` 只匹配 `call.func` 为 `ast.Name`。
- **复现**：`python /tmp/.../major1_probe.py`（脚本见会话）→ 第 5/7/11 行 `reached`。
- **建议（非本批必须）**：若将来要对「蓄意绕过」设防，可 (i) 给该 AST 锁加扫字符串字面量 `"_ExactErrorContextDiagnostic"`（对齐既有 `"_exact_error_context"` 字符串扫），(ii) 在 `_error_context` 走一个运行时 allowlist。当前威胁模型下两者皆非必需。

**无 BLOCKER / 无 MAJOR / 无 MINOR。**

---

## 7. 「执行验证」vs「静态读码」的明确划分

**由我活体执行验证（机器跑出，非推断）**：
- 全仓 `1786/10/0`；
- 14 个指定 neuter 的真实红数（§5）；
- MAJOR-1 的 11 向量探针（§3.4）+ 坍缩范围 12↔1 字段（§3.3）；
- 3 MINOR 各自的回归探针（§4，触红）；
- sm24 manifest 现算 + `git diff --quiet`（§1）。

**由我静态读码 + grep 验证（未跑但逻辑闭合）**：
- 5 把 MAJOR-1 锁的 AST/运行时形态（§3.3 表，逐行读过）；
- M-1 全目录封闭锁的 4 origin 列表；
- MINOR-2「0 生产调用」的 grep（§4）；
- M-6（答案原子纯函数）——依赖 D-1 证书字段（已活锁钉住），未单独构造反例。

---

## 8. 一句话给主控

**r1 的 1 MAJOR + 3 MINOR 全部实质闭合；本轮独立重跑 14 neuter 零偏差（r1 翻车点未复发）；MAJOR-1 原门已封、剩余三条为 Python 固有蓄意绕过（NIT 不阻断）；全仓 1786/10/0、sm24 零改动、D-1 `blocking_change=False`。建议 APPROVE，过审后跑 sm24 端到端。**
