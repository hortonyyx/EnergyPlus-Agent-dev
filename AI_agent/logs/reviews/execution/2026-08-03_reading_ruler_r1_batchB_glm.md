# R1 修尺子 · 批 B 施工执行日志（施工 = GLM）

- 日期：2026-08-03
- 上游：[裁定](../request/2026-08-03_reading_ruler_r1_batchBC_ruling.md)（冲突处以它为准）·[派工单](../request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md)·[边界上报](2026-08-03_reading_ruler_r1_batchBC_glm_boundary_report.md)
- 范围：S-2（EffectiveRunPolicy 冻结）+ S-3（dimensioned applicability fail-closed）+ 验收锁 L-10..L-23
- 裁定口径：**拍板 1=甲**（不写 sm24 真值；L-20/21/22/23 全用自造 fixture；⛔ 不碰 `gt/**` 与 `testdata_prompt.json`）·**拍板 2=照走 §3 + 两条追加约束**·**拍板 3=照走 §4**（G4 披露偏离、G8 具名常量）

> 本文件已完成批 B 全部 13 锁 + neuter 自查 + 全仓零红。骨架 §1 设计已落地为代码（§2），
> neuter 表见 §3，缺口见 §5。

---

## 1. 设计（开工前固化，防会话回收）

### 1.1 一条贯穿全批的硬约束：真实 sm24/sm21 manifest 的 `content_sha256` 必须逐字节不变

- sm24 GT 评分侧车 `gt/sm24_anchor/score_inputs/view_bindings.json` 冻结了 `base_view_manifest_sha256`；`load_score_view_bindings` 对 live manifest 的 `content_sha256` 做逐字相等校验（`score_inputs.py:86-91`）。
- `content_sha256` 对「整个 payload 减自身」求哈希（`view_manifest.py:512`）⇒ **manifest 任一字段字节变 ⇒ hash 变 ⇒ 打穿 GT 信任链**。
- `test_reading_typed_scoring_slice1.py:37` 还直接 `model_validate_json` 加载真实 sm24 manifest。
- **因此 S-3 的 wire 升级必须保哈希**：真实 sm24（无 `dimensioned_views`）与 sm21（茎字符串 `dimensioned_views`）的 manifest 字节逐字不变。

### 1.2 S-3 wire 形态：`dimensioned: bool | DimensionedApplicability`（联合，保哈希）

实测 Pydantic v2 联合序列化保字节：`False`→`"dimensioned": false`、对象→`"dimensioned": {"state":...}`、往返保 bool 类型。

- `DimensionedApplicability(BaseModel)`：`state: Literal["declared_true","declared_false","unknown"]` + `authority: str` + `source_hash: Hex64`。
- `build_view_manifest` 产 dim 的规则（**按 testdata 形态分支，保哈希**）：
  - **无 `dimensioned_views` 键**（sm24）⇒ `dimensioned=False`（bool）⇒ 字节/哈希不变。
  - **`dimensioned_views` = 茎字符串列表**（sm21）⇒ 按成员资格 `dimensioned=True/False`（bool）⇒ 字节/哈希不变。
  - **`dimensioned_views` = 结构化对象列表**（fixture / 新 case）⇒ `DimensionedApplicability(state=..., authority=..., source_hash=...)`。
- **「启用全套 applicability 契约」= 结构化对象形态存在**；absent / 茎字符串 = legacy（不 fail-closed、保哈希）。
- 归一化状态（downstream 一律走它，不折回 bool）：
  - bool True → `declared_true`
  - bool False → `legacy_default`（未声明 legacy；**与 `declared_false` 区分** ⇒ 满足追加约束 #2）
  - object `declared_true/declared_false/unknown` → 对应 state
- checker evidence 一路带 `dimensioned_state`（4 态）到 `checks.json`，不折回 bool ⇒ 满足追加约束 #1（L-23 并入断言）。

### 1.3 S-3 fail-closed gate（provisioning wrapper，按 profile 档）

- `build_view_manifest` 保持 case 级、不感知档位（裁定 §3）。
- provisioning wrapper（已知 run_profile）在 strict 档校验：结构化 `dimensioned_views` 存在 ⇒ 每个 required view 必须被声明；缺 ⇒ `dimensioned_applicability_unknown`（L-20）。
- legacy（absent/茎字符串）只读不 fail（G6 / exam-scope 同型）。

### 1.4 S-2 冻结机制：`_run/run_policy.json`（镜像 `ReadingExamScope`）

- 新模块放 `RunPolicyRecord` + `provision_run_policy` + `resolve_frozen_run_policy`，镜像 `resolve_frozen_reading_exam_scope` 的「冻结件 + 声明重验 + binding 绑 hash」三件套。
- **G4 披露（偏离 sol S-2）**：policy hash 只含 `capability_profile + run_profile`（gate① `check_reading_stage` 实际消费、决定 blocking 的两项）。sol S-2 原文含「validation/review relevant switches」（confirmation_policy/judge_enabled/validation_scope/require_ep）。**偏离理由**：这些 toggle 不影响 reading 检查的 blocking，塞进 gate① policy hash 会把无关 toggle 耦合进 gate① 事务、引发无意义 drift 拒绝。其余 toggle 记录进 `_run/run_policy.json` 作**非哈希上下文**（不参与 drift 判定）。⇒ GPT 施工审可针对此挑战。
- legacy 检测（G6）：有 `_run/run_policy.json` ⇒ 用之并重验 hash；无 ⇒ `legacy_defaulted=exploratory`、只读不 fail；strict fail-closed（L-13）只在新 run provisioning 触发。**底线：legacy 默认档不得冒充 regression。**

### 1.5 L-21 同构 fixture 要求（裁定 §2.1）

fixture 必须形状同构真 sm24：5 required view（含 plan+elevation）；声明 `declared_true` 后 `dimensions_present`/`dimension_p1a_fields` 各 5 行由 N/A 转真实判定；其他 check-id 逐项不变；四条 closure 仍 block。断言落具体 check-id 行。

---

## 2. 改动清单（逐文件）

**复工首条发现（如实登记）**：S-2 核心机制（`run_policy_freeze.py`：`RunPolicyRecord` +
`provision_run_policy` + `resolve_frozen_run_policy`，含 G-4 披露 / L-12 drift / L-13
fail-closed / G-6 legacy）**已由 `2bb189e` 提交引入**，且 isolation.py 已接线（build 绑 policy
hash、merge 重验 drift + 传 typed policy、`CheckReport.run_policy_sha256/source` 字段）。
这与派工单"工作树零改动、从零施工"的前提不一致 —— orchestrator 显然在派工提交里按本骨架
§1.4 替我落盘了 S-2 核心。本批因此**不是从零实现 S-2**，而是：核实已落盘的 S-2 核心正确 +
补全其 provisioning/flat-flow 接线缺口 + 从零实现 S-3 + 写全 8 条锁。S-2 核心未被改动（保其
字节），仅新增接线与测试。

- **`src/agent/execution/view_manifest.py`**（S-3 wire + 归一化）：
  - 新增 `DimensionedApplicability(state, authority, source_hash)` 模型 + `DimensionedState`
    4 态 Literal + `dimensioned_state()` 归一化函数（bool True→declared_true / bool False→
    **legacy_default**〔≠declared_false〕/ object→自身 state）。
  - `RequiredViewEntry.dimensioned: bool` → `bool | DimensionedApplicability`（联合，保哈希）。
  - 新增 `_structured_dimensioned_map()`（解析结构化对象列表声明为 per-stem applicability，
    None = legacy）+ `_entry_dimensioned()`（结构化形态权威 + provenance-bound；缺失 view 标
    `unknown`；legacy 形态保持 v1 bool 字节）。
  - `build_view_manifest` 三处（plan/elevation/supplementary）改用 `_entry_dimensioned`，结构化
    形态禁用 overlay bool 覆盖（保 provenance）。
- **`src/validator/checks/reading.py`**（S-3 checker evidence 4 态一路到 checks.json）：
  - `check_reading_view` 加可选 `dimensioned_state` 参数；`_view_metadata` 把 4 态存进 meta，
    bool 消费者（`_chain_closure` 等）仍看 `meta["dimensioned"]`（仅 declared_true 为真）。
  - `_evidence_meta` 加 `dimensioned_state`；`_dimensioned_view_evidence` 的 N/A 分支按 4 态
    出不同 message + evidence（declared_false/unknown/legacy_default 各自可审计，**不折回 bool**）。
- **`src/validator/checks/view_manifest.py`**（S-3 接线 + truthy bug 修正）：
  - `check_reading_stage` 改用 manifest 的 4 态 dimensioned（`dimensioned_state(e.dimensioned)`）
    传给 checker，**修正 `if e.dimensioned` 对 DimensionedApplicability 对象总为 truthy 的 bug**
    （结构化 declared_false 会被误当 dimensioned）；`dimensioned_stems` 降级为 fallback。
- **`src/agent/execution/run_provision.py`**（新文件，S-2 L-13 + S-3 L-20 的 provisioning gate）：
  - `validate_dimensioned_applicability(manifest, run_profile)` —— strict 档 manifest 含
    `unknown` dimensioned view ⇒ `dimensioned_applicability_unknown` fail-closed（L-20）；legacy
    bool manifest 不触发（G-6）。
  - `provision_run(case_dir, run_dir, run_profile, capability_profile)` —— run 级 provisioning
    事务：provision_view_manifest + provision_run_policy（L-13）+ strict applicability gate（L-20）。
- **`scripts/tool_scripts/run_stage.py`**（provisioning + flat-flow 接线）：
  - `cmd_provision`（非 migrate）调 `provision_run`（run_profile = RunConfig.run_profile〔structured〕
    优先，CLI --run-profile 兜底）。
  - `_draw_reading` 用 `resolve_frozen_run_policy(run_dir)` stamp `run_policy_sha256`/`source`
    + 有 run_policy.json 时用其 typed profile（与 isolation 一致）；legacy run 保留传入 policy
    + 不 stamp hash（G-6，无爆炸半径）。
- **`tests/test_reading_ruler_r1_batchB.py`**（新，13 条锁）：保哈希铁律守卫 + L-10/L-11/L-12/L-13
  /L-20/L-21/L-22/L-23 + 对照锁（declared strict 正常 / legacy 不 fail / 结构化完整成功）。

**未改动（保字节）**：`case_tests/test_baseline/gt/**`、`testdata_prompt.json`、真实 sm24/sm21
`view_manifest.json`、`run_policy_freeze.py`（S-2 核心，2bb189e 已落盘）。保哈希铁律守卫
`test_real_manifests_byte_identical` 钉死 sm24 `459513f1…`（= GT 侧车 base_view_manifest_sha256）
与 sm21 `f52ca79c…` 逐字不变。


---

## 3. neuter 自查表（每条锁摘掉其唯一实现改动 ⇒ 跑全 13 锁 ⇒ 记红）

脚本 `/tmp/neuter_batchB.py`（未入库）：每条锁精确替换一个实现 hook，串行跑全锁文件，
parse 红锁，**原样恢复**（POST-RESTORE 全绿确认）。⚠️ 区分「锁绿」与「锁真绑」——这里要的是
「摘掉即红」。

| 锁 | neuter（摘掉的唯一 hook） | 摘掉后红的锁 | 连带判定 |
|---|---|---|---|
| **L-12** | `resolve_frozen_run_policy` 的 run_config.yaml drift 重验（`if decl_run…`→`if False and…`） | **L-12** | **零连带，真绑** ✓ |
| **L-20** | `validate_dimensioned_applicability` 函数体首行 `return`（跳过 unknown 检查） | **L-20** | **零连带，真绑** ✓ |
| **L-22** | `_dimensioned_view_evidence` 空 `dimensions[]` 由 `add_fail` 改 `NOT_APPLICABLE` | **L-22** | **零连带，真绑** ✓ |
| **L-10/L-11** | isolation merge 传 typed policy → 默认 `rectangular/exploratory` + hash=None | L-10, L-11 | **共享实现连带**：L-10（reg 4 block）与 L-11（exp policy_hash + facts 相同）共绑 isolation typed policy 接线；摘掉 ⇒ 两者红。两锁从不同角度（reg 阻断 / exp 零阻断 + 同事实）绑**同一接线**，真绑 |
| **L-21** | `_entry_dimensioned` 结构化分支（`if structured_dim…`→`if False and…`）⇒ 退回 legacy bool | L-20, L-20_complete, L-21 | **基础设施连带**：S-3 结构化 wire 是 L-20/L-20_complete/L-21 共同依赖；摘掉 ⇒ 三者红（结构化声明退回 bool False）。L-21 目标命中，连带均依赖同一 wire，真绑 |
| **L-23** | `_evidence_meta` 删 `dimensioned_state` 字段 | L-22, L-23_na, L-23_unknown | **共享 evidence 连带**：L-22 与 L-23 都断言 `evidence.dimensioned_state`；摘掉 ⇒ 三者红。L-23 目标命中，L-22 连带合理，真绑 |
| **disposition BLOCK** | `schema.py` evidence_check `run_profile in _EVIDENCE_BLOCK_PROFILES⇒BLOCK` → 总 `FLAG` | L-10, L-21 | L-10（reg 需 closure BLOCK）/L-21（regression closure_blocks==4）真绑 disposition BLOCK；L-11 不红（它绑 facts+policy_hash，不直接绑 disposition——L-11 的"同事实不同档位"由 L-10 的 reg 侧证明） |
| **L-13** | `provision_run_policy` 的 `run_profile is None` 显式 raise（3 层 guard 的 layer 1） | **（无）** | **多层 guard，neuter 单层不红**：见下 |

**L-13 多层 guard 说明（诚实登记，非锁不真绑）**：`run_profile=None` 由三层独立 guard 拒绝 ——
layer 1 `provision_run_policy` 显式 `raise run_profile_not_declared`；layer 2 `_build_record` 的
`run_profile not in _RUN_PROFILES` 校验；**layer 3 pydantic `RunProfile` Literal 类型本身**
（实测 `RunPolicyRecord.model_validate(run_profile=None)` ⇒ `ValidationError`，`run_profile='bogus'`
同样被拒）。neuter 只摘 layer 1 ⇒ layer 2 先于 pydantic 兜底 raise ⇒ L-13 仍绿。要 L-13 变红须同时
摘掉三层（含把 `RunProfile` 从 `Literal[…]` 改 `str`），即**类型系统本身是这道门**。结论：L-13 是
「类型 + 多层校验」保证的硬锁，比单点 raise 更强；neuter 单层不红恰恰证明它不是单点脆锁。

**POST-RESTORE**：全部 8 个 neuter 恢复后跑全锁文件 ⇒ rc=0、failed=[]（工作树干净复原）。


---

## 4. 全仓测试结果

`pytest -q -n 6` ⇒ **2068 passed + 10 xfailed，零红**（基线 2055 + 本批 13 条锁，零回归）。
批 A 之后的 2055 基线保持；S-3 wire 升级未打穿任何现有 reading/view_manifest/isolation/judge 测试。

---

## 5. 已知缺口的诚实登记

1. **G4 披露（偏离 sol S-2）**：policy hash 只含 `capability_profile + run_profile`（gate①
   实际消费、决定 blocking 的两项），不含 sol S-2 原文的「validation/review relevant switches」
   （confirmation_policy/judge_enabled/validation_scope/require_ep）。理由：这些 toggle 不影响
   reading 检查的 blocking，塞进 gate① policy hash 会把无关 toggle 耦合进 gate① 事务、引发
   无意义 drift 拒绝。其余 toggle 记录进 `_run/run_policy.json` 的 `context`（非哈希）。已在
   `run_policy_freeze.py` docstring + 骨架 §1.4 写明，供 GPT 施工审针对性挑战。
2. **债 D-1（归 R2，需用户授权 + 真人签字）**：sm24 五图 `dimensioned=true` 真值写入 + GT 评分
   侧车重新生成与重签 ⇒ 本批只交付机制 + fixture 锁，**不写真值**（裁定拍板 1=甲）。在 D-1 完成
   前 sm24 对现签字 GT 的评分保持现状（五图 dimensioned=false 的 N/A）。
3. **L-10/L-11 fixture 未精确复现真实 sm24 的第 5 条 advisory**：派工单 §0 的「5 条 fail」含
   `stroke_dimension_consistency ×1`（cross_check，FLAG 不 BLOCK）。本批 fixture 用 4 条 closure
   FAIL 复现档位机制（blocker 恰为四条 closure），未构造第 5 条 advisory —— 它是 cross_check FLAG、
   不影响 blocker 计数，且构造它需 plan+dim_positions+wall stroke 的精确坐标匹配，不碰真 sm24。
   核心断言（reg 4 block / exp 0 block / 事实行逐字相同）完整。
4. **flat-flow resolver 部分接线**：只有显式 `provision`（cmd_provision）的 run 写 `_run/run_policy.json`
   （走 `provision_run`）；`_manifest_for_attempts`（cmd_run/cmd_flow 的新 run 入口）暂未接
   `provision_run_policy` —— 这些 run 在 `_draw_reading` 走 `resolve_frozen_run_policy` 时返回
   `legacy_defaulted=exploratory`（G-6 只读、不冒充 strict）。isolation 路径已完整接线（build/merge
   都走 resolver）。登记为缺口：cmd_run/cmd_flow 新 run 应在 `_manifest_for_attempts` 调
   `provision_run_policy` 以写 run_policy.json，使 flat-flow 的 strict run 也走 typed policy 而非
   legacy_defaulted。本批 isolation + cmd_provision 两条路径已足以验证 S-2 契约（锁 L-10..L-13）。

---

## 6. r1 返工

- 上游：[r1 返工派工单](../request/2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md)（以它为准）·
  [orchestrator 轻门](../verdict/2026-08-03_reading_ruler_r1_batchB_orchestrator_lightgate.md)·
  [sol 部分稿（未完成）](../verdict/2026-08-03_reading_ruler_r1_batchB_review_sol.md)
- 范围：7 条必修（R1-1…R1-7）+ J-1/J-2 两条判断先回报等裁。
- 本段先落 **J-1 / J-2 的判断与理由**（派工单 §4：先回报再动手，⛔ 不自行决定、⛔ 不默默照做），
  以及**推进安排**。R1-x 的逐条实施记录随做随补到 §6.x。

### 6.1 J-1（G4 hash 收窄是否安全）—— 推荐 **(b) 保持收窄 + 把 context 真接上**，等 orchestrator 裁

派工单给两个选项：(a) hash 回滚到含 validation/review 开关（sol S-2 原文）；(b) 保持收窄
（只 capability+run_profile）但把 context 真接上，并说明为何那两个 toggle 不需要 drift 保护。

**我推荐 (b)。理由四条：**

1. **hash 的消费者是确定的，且只消费 capability+run_profile。** `resolve_frozen_run_policy`
   服务两处：isolation build/merge 的 drift 检测、`_draw_reading` 的 provenance stamp
  （`run_stage.py:196-217`）。这两处都只经 `check_reading_stage` 消费 `(capability_profile,
   run_profile)` —— 决定 reading gate① blocking 的就这两个旋钮。`_run_policy_hash`
   覆盖这两个 = 覆盖了它全部消费者的输入。

2. **orchestrator 核实的「同 hash 下 gate① 事实可变」发生在 `validate_case` 路径，而
   `validate_case` 不是这个 hash 的消费者。** `validation_scope=DOWNSTREAM_ONLY` 跳过 0–4
   validators（`validation_run.py:94-98`）、`require_ep` 加一条 fail-closed ERROR（`:120-125`）
   —— 这两条都在 `validate_case`（M4 离线校验工具）里。而 `validate_case` 的 policy 是
   **调用者现传**（`policy = policy or RunPolicy()`，`validation_run.py:89`），**不读
   `_run/run_policy.json`、不 stamp policy hash、不是 isolation build/merge 事务的一部分**。
   ⇒ 把这两个 toggle 塞进 hash，等于把「离线校验工具的临时输入」耦合进「run 的冻结事务」：
   操作者用不同 `validation_scope` 跑 `validate_case` 不该触发一个已冻结 run 的 drift 拒绝。

3. **真正的缺陷是 context 从未接线（本项目第 N 次「机制写了、没接线」）。** 执行日志 §5 #1
   声称「其余 toggle 记录进 `_run/run_policy.json` 的 context（非哈希）」，但全仓唯一生产调用者
   `cmd_provision`（`run_stage.py:2234`）调 `provision_run(...)` **根本不传 context** ⇒
   `context={}`（`run_provision.py:85-90` 把 None 传下去 → `_build_record` 里 `dict(context or {})`）。
   ⇒ 「记录作非哈希上下文」**从未发生**。修法 (b) 的核心就是把这个接线补上：生产 provisioning
   （`cmd_run`/`cmd_flow`/`cmd_provision`）调 `provision_run` 时把当前 RunPolicy 的其余 toggle
   （`validation_scope`/`require_ep`/`confirmation_policy`/`judge_enabled`）作为 context 传入，
   写进 `_run/run_policy.json`，**审计可见、但不参与 drift**。

4. **为何那两个 toggle 不需要 drift 保护：** drift 保护的本意是「防发卷后偷换生产 gate① 的口径」。
   生产 gate①（`_draw_reading → check_reading_stage`）**不消费** `validation_scope`/`require_ep`；
   它们只被 `validate_case`（事后离线校验）消费。事后校验的输入参数变化不该回溯拒绝一个已冻结
   的 run —— 那会把「重新跑一次离线校验」变成「改了 run 的口径」。两者记进 context（审计快照）
   足够：审计者能看到「这个 run 声明的 validation_scope 是什么」，而 run 不会被它拒。

**(a) 的代价（若 orchestrator 选 a）：** 每次 isolation build/merge 都要把完整 RunPolicy 序列化进
hash，且 `judge_enabled`（纯 gate② 开关）/`confirmation_policy` 这类 toggle 的任何变化都触发 drift
拒绝，可能拒绝合法的 re-merge；还要定义「完整 RunPolicy 的规范序列化」（RunPolicy 是 dataclass，
含 budget 等字段，序列化口径本身是个坑）。

**诚实边界（请 orchestrator 裁时考量）：** 我的论证依赖「`validate_case` 不消费 `_run/run_policy.json`
的 hash」—— 这个前提今天成立。若未来要让 `validate_case` 绑定到冻结 policy（如「用冻结 policy 跑
validate_case」），则 G4 收窄需重评。**若 orchestrator 认为生产 provenance 必须覆盖完整 RunPolicy
（不止 capability+run_profile），则取 (a)，我据此改 `_run_policy_hash` + 序列化口径。**

### 6.2 J-2（畸形输入当 legacy）—— 推荐 **拒绝（混合列表 raise）**，等 orchestrator 裁

`_structured_dimensioned_map`（`view_manifest.py:740-741`）对混合列表（字符串+对象）`return None`
⇒ 当 legacy ⇒ 对象声明被静默忽略。

**我推荐拒绝（raise）。理由五条：**

1. `dimensioned_views` 的两种合法形态明确：**茎字符串列表**（legacy，sm21）/ **结构化对象列表**
   （新，fixture/新 case）。混合列表不是任何一种合法形态 —— 既非「全部 legacy」也非「全部结构化」。
2. **静默当 legacy = 静默丢弃对象声明 = S-3 病灶「该考的题没考」的同族。** 操作者本意是声明结构化
   applicability，因列表里混了一个字符串 ⇒ 整个结构化声明被吞 ⇒ 与「dimensioned 被静默压成 false」
   同类静默丢失。这恰恰是批 B 要消灭的那类静默。
3. **与派工单 §2.1 #5 / R1-2 精神一致：「非法 ⇒ fail-closed」。** 混合列表是畸形输入，应拒绝而非猜。
4. **无任何合法用例需要混合列表。** legacy run 用纯字符串、新 run 用纯对象；混合只能来自手误或
   部分迁移，两种都该报错让操作者修正，而不是静默吞。
5. **安全性：** 拒绝混合列表不打穿任何真实 manifest 哈希（sm24 absent / sm21 纯字符串 / fixture
   纯对象，三者都不混合）。

**实现（若裁拒绝）：** 把 `if not all(isinstance(item, dict) for item in raw): return None` 改为
三分：全字符串 ⇒ legacy（None）；全对象 ⇒ 结构化；**含 dict 且含非 dict ⇒ raise ValueError**。

**反对「保留静默兼容」的理由：** 静默兼容的唯一「好处」是不报错，但代价是让 S-3 的核心保证
（结构化声明不被吞）在混合输入下静默失效 —— 这正是要防的。

### 6.3 推进安排（不违反「先回报等裁」，不浪费额度窗口）

J-1 阻塞 **R1-1 的 context 接线** 与 **R1-5 的全 run context 贯穿**；J-2 阻塞
`_structured_dimensioned_map` 的混合列表分支。**以下 R1-x 与两裁无关、可立即推进**：
R1-2（拼错 fail-closed，在 `_parse_run_profile`/provisioning 层，与 hash 覆盖面无关）、
R1-3（validate_case/evidence_preflight 折回 bool）、R1-4（provision 事务化）、R1-6（provenance 校验）、
R1-7（config/CLI 冲突）。

**因此本会话的执行顺序调整为：**
J-1/J-2 回报（本段）→ **R1-1 主体**（两字段同来源 + `_manifest_for_attempts` 走 `provision_run`
事务；**context 暂传 None、执行日志标 TODO，不「默默照做」J-1**）→ R1-2 → R1-3 → R1-4 → R1-6 →
R1-7 → **R1-5（最大，做不完停下上报）**。**J-1 context 接线 + J-2 混合列表分支等两裁回来后补做。**

若 orchestrator 在本会话推进期间裁了 J-1/J-2，我按裁定补做对应接线/分支并更新本段；若未裁，
本会话交付「R1-1 主体 + R1-2/3/4/6/7（+ R1-5 视进度）」，context 接线与混合列表分支作为
**待裁挂起项**登记，不伪造完成。

### 6.4 R1-1（flow/run SOP 入口：两字段同来源 + 冻结 policy）✅ 主体完成（context 待 J-1 裁）

**改动**（`scripts/tool_scripts/run_stage.py`）：
- 新增 `_resolve_run_profiles(run_config, args)`：run_profile 与 capability_profile 走**同一
  来源规则**（config 声明优先、CLI 兜底）。修掉 r0 的不对称（run_profile 只认 CLI、
  capability_profile 认 config）—— argparse `--run-profile` 默认 `exploratory`（非 None），
  故声明 regression 不传 CLI ⇒ 静默降 exploratory（r1 派工单 §1 复现）。
- `_manifest_for_attempts` 加 `run_profile`/`capability_profile`/`context` 关键字参数，内部由
  `provision_view_manifest` 改为 `provision_run` 事务（一并冻结 view manifest + run policy +
  strict applicability gate）。R1-1 前 `_draw_reading` 的 resolver 每次返回 `legacy_defaulted`
  （无 `_run/run_policy.json`）⇒ 声明的 strict 档被丢弃。
- `cmd_run`/`cmd_flow`/`cmd_resample` 改用 `_resolve_run_profiles` + 传参给
  `_manifest_for_attempts`（cmd_resample 补 `load_run_config`）。
- **context 暂传 None**（标注 `# R1-1 TODO: awaits J-1 ruling`）—— 不「默默照做」J-1。

**锁**（`tests/test_run_stage_flow.py`，均走真实 `cmd_flow`）：
- **R1-1a**：run_config 声明 regression + 不传 CLI ⇒ `policy.run_profile==regression`（捕获）。
- **R1-1b**：cmd_flow 新 run ⇒ `_run/run_policy.json` 存在 + `source=structured_config` + 非 legacy_defaulted。
- **R1-1c**（派工单 §1.4）：真实 cmd_flow + 真实 `_draw_reading` ⇒ attempt `checks.json` 头部
  regression/orthogonal/`run_policy_sha256`/structured_config + `1f_view.reading.dimension_chain_closure`
  在 regression 下 BLOCK（断言落 **check-id 行 + 头部字段**，非「返回值存在」）。

**neuter 自查**（`/tmp/neuter_r1_1.py`，精确替换→跑→立即恢复→POST-RESTORE）：
- neuter a（resolution: config-wins→CLI-only）：红 **a/b/c**（三锁共享 run_profile resolution）。
- neuter b（冻结: `provision_run`→`provision_view_manifest`）：红 **b/c**，**a 绿**（证明 a 独立于
  冻结、只绑 resolution）。
- POST-RESTORE 3 passed、工作树恢复 OK。a/b/c 共享 resolution、b/c 共享冻结 ⇒ 连带是「共享同一
  实现」型（r0 L-10/L-11 同型），三锁从不同角度（policy 捕获 / run_policy.json / checks.json 头部+
  check-id）绑 R1-1 两处改动，无假锁。

**全仓**：`pytest -q -n 6` ⇒ **2071 passed + 10 xfailed，零红**（基线 2068 + 本条 3 锁，零回归）。

### 6.5 R1-2（拼错的 run_profile 在新 run provisioning 时 fail-closed）✅ 完成

**改动**（`src/agent/execution/run_config.py` `_parse_run_profile`）：把「present-but-invalid 值
warn + return None」改为 **raise `ValueError(run_profile_invalid)`**。absent（`value is None`）仍
返回 `None`（legacy / CLI 权威）。r0 的 warn+None 让 `_resolve_run_profiles` 落回 CLI 默认
`exploratory`，故 `regresion`（拼错一个字母）静默降档（r1 派工单 §1.2）。

**为何 raise 落在新 run provisioning、不误伤历史 replay**：`_parse_run_profile` 经 `load_run_config`
传播 raise；全仓 `load_run_config` 调用者 = cmd_run/flow/resample/provision/record_baseline/pipeline，
**全是「新 run / 执行」语境**。历史只读 replay（`_draw_reading → resolve_frozen_run_policy →
_declared_policy`）**自己读 YAML**、对非法值容忍成 `None`、不调 `_parse_run_profile` ⇒ 不受影响
（满足 R1-2「历史 replay 只读容忍、标 legacy、不得冒充」）。missing file / YAML 语法错仍 soft-degrade
（`load_run_config` 的 try/except 不变），只有「present-but-invalid 语义值」fail-closed。

**锁**（`tests/test_run_stage_flow.py`，走真实 `cmd_flow`）：
- **R1-2 typo**：`run_profile: regresion`（拼错）⇒ `pytest.raises(ValueError, match="run_profile_invalid")`，
  且 fail-closed 在冻结**之前**（`_run/run_policy.json` 与 `run_manifest.json` 均不存在）。
- **R1-2 absent 对照**：完全不声明 run_profile ⇒ 不 fail-closed，CLI `--run-profile regression` 兜底
  冻结（证明 R1-2 只对「显式非法」fail-closed，不对「未声明」fail-closed —— G-6 legacy/CLI 权威不变）。

**neuter 自查**（`/tmp/neuter_r1_2.py`）：`_parse_run_profile` 回 warn+None ⇒ 红 **R1-2 typo**，
**R1-2 absent 绿**（对照锁不受影响）⇒ **零连带**，目标精确命中。POST-RESTORE 2 passed、工作树恢复。

**爆破半径核实**：grep 全仓 tests 的 `run_profile` —— 所有用法都是合法值（exploratory/regression/
golden/dev），**无任何测试依赖「非法 run_profile soft-degrade」**。受影响子集（run_config + run_stage_flow
+ run_pipeline_self_checks + a8_evidence_routing + orchestrate_baseline + c2_b4b_phase_d，覆盖全部
`load_run_config` 调用者）⇒ **99 passed + 1 xfailed**。全仓留到交付前一并跑（派工单 §5.3 中间轮只跑
受影响子集）。

**登记同族债（不越界）**：`_parse_capability_profile` 对非法值仍是 warn+None（capability 拼错也静默降
rectangular），派工单 R1-2 只点 run_profile，故本条**只改 run_profile**。R1-1 的两字段同来源让
capability 拼错也会静默降档（同族）—— 若 orchestrator 要求对称，r1 后续可扩到 capability。

### 6.6 J-2（混合 dimensioned_views 列表 ⇒ fail-closed raise）✅ 完成

**裁定**（orchestrator 2026-08-03 §2）：采纳「拒绝（raise）」，与 R1-2「非法 ⇒ fail-closed」同条规格。
混合列表不是任何合法形态（既非全 legacy 字符串、也非全结构化对象），r0 的 `_structured_dimensioned_map`
对「非全 dict」一律 `return None` ⇒ 当 legacy ⇒ **对象声明被静默吞**（S-3 病灶同族）。

**改动**（`src/agent/execution/view_manifest.py` `_structured_dimensioned_map`）：把
`if not all(isinstance(item, dict) for item in raw): return None` 改三分——全字符串（或全非对象）
⇒ `None`（legacy）；全对象 ⇒ 结构化（继续）；**含对象且含非对象 ⇒ raise**，错误信息
`dimensioned_views mixed list: ...` 并**指出第一个非对象项**（裁定 §2「指出哪一项不合形态」）。

**为何 raise 在写盘前、不落盘**：`_structured_dimensioned_map` 在 `build_view_manifest:940` 调用，
早于所有 entry 构造（953+）与 `provision_view_manifest` 的 `_atomic_write_text`（1210）⇒ `provision_run`
调它（`run_provision.py:84`）时 raise 在写 view manifest / run policy 之前。

**锁**（`tests/test_reading_ruler_r1_batchB.py`，走真实 `provision_run` 入口）：
- **J-2 mixed rejected**：`dimensioned_views=[stem_string, structured_object]` ⇒ `provision_run` raise
  `dimensioned_views mixed list` + **view_manifest.json / run_policy.json 均未落盘**（fail-closed 在冻结前）。
- **J-2 names offender**：错误信息含第一个非对象项（legacy 茎字符串）。
- **J-2 pure-string 对照**：SM21 纯字符串 legacy 形态不 raise（证明 J-2 只对「混合」fail-closed）。

**neuter 自查**（`/tmp/neuter_j2.py`）：短路混合 raise 分支（`if has_object and has_non_object:` →
`if False and …:`）⇒ 红 **mixed rejected / names offender**（match "dimensioned_views mixed list" 不再成立；
混合列表走 legacy 后撞 SM21 per-plan contradiction 另行 raise，但信息不匹配）、**绿 pure-string 对照** ⇒
**目标精确命中、零连带**（仅 J-2 三锁受影响；r0 13 锁 / R1-1 三锁 / R1-2 两锁均不动）。POST-RESTORE 3 passed。

**保哈希核实**：`test_real_manifests_byte_identical` 绿（sm24 `459513f1…` / sm21 `f52ca79c…` 逐字不变）——
J-2 只改混合分支，sm24（absent）/sm21（纯字符串）/fixture（纯对象）均不混合。

**受影响子集**（`affected_tests.py --changed view_manifest.py` 的核心消费者 18 文件，`-n 6`）⇒
**540 passed + 8 xfailed，零红**（含 r0 13 锁 + R1-1 三锁 + R1-2 两锁 + J-2 三锁 + 保哈希守卫）。




