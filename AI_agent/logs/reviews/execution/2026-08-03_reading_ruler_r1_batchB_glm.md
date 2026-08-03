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

### 6.7 R1-3（validate_case / evidence_preflight 不把四态折回 bool）✅ 完成

**病灶**（派工单 §1.3 + 裁定追加约束 #1「不得在任何一层折回 bool」）：生产 gate① 路径
（`check_reading_stage`）r0 已 4 态保真（manifest → `dimensioned_state`），但**两条离线路径**
仍 bool 折叠：
- `validation_run.py:132` 调 `dimensioned_view_names(case_dir)`（返回 `set[str]`），其 `add()`
  （`case_metadata.py:55-57`）对**非字符串直接 return** ⇒ 结构化对象声明被整个丢；`:140` 折
  `view_metadata={"dimensioned": stem in names}`（bool）且**不传 `dimensioned_state`**。
- `evidence_preflight.py:222`（`compute_reading_report_from_vector_dir`）同型 bool 折叠。
⇒ 一个结构化 `declared_true` 声明在这两条路径退回 `legacy_default`/N/A；`declared_false` 折成
`legacy_default`（与裁定追加约束 #2「legacy_default ≠ declared_false」直接冲突）。

**改动**（克制范围：只修两条离线路径，不动 run_stage cmd_judge/_draw_reading 的 fallback —— 那是
R1-1/R1-5 范围；生产 gate① 已保真）：
- `case_metadata.py`：抽 `_dimensioned_view_names_from_data(data)`（纯函数，`dimensioned_view_names`
  行为零变）+ 新增 `dimensioned_states_from_data(data) → dict[stem,str]`（4 态：legacy 信号 →
  `declared_true`；结构化对象 → per-view `declared_true`/`declared_false`；absent 不在 map）+
  `dimensioned_view_states(case_dir)`。
- `validation_run.py:132,140`：改用 `dimensioned_view_states(case_dir)` + 传
  `dimensioned_state=states.get(stem,"legacy_default")`（去掉 bool view_metadata）。
- `evidence_preflight.py`：`compute_reading_report_from_vector_dir` / `compute_evidence_debt_from_vector_dir`
  加 `dimensioned_states: dict|None` 参数（向后兼容：未传时从 `dimensioned_views` set 推
  `{stem:"declared_true"}`，与 r0 行为逐字等价）+ 传 `dimensioned_state`。
- `pipeline.py:574,895`：两处改传 `dimensioned_states`（`dimensioned_states_from_data(parse_testdata_text(...))`），
  删未用的 `dimensioned_view_names_from_testdata_text` import。

**为何不重构 `dimensioned_view_names`**：它被 run_stage cmd_judge/_draw_reading（R1-1/R1-5 范围）作
fallback 用。抽 `_dimensioned_view_names_from_data` 是纯重构（行为零变），`dimensioned_view_states`
是独立 4 态版，两者并存，爆破半径最小。

**锁**（`tests/test_reading_ruler_r1_batchB.py`，三条）：
- **R1-3a 单元**：`dimensioned_states_from_data` 解析结构化对象 → declared_true/declared_false 保真 +
  legacy Floor-plans 信号 → declared_true + absent 不在 map。
- **R1-3b evidence_preflight 入口**：`compute_reading_report_from_vector_dir(dimensioned_states={...})`
  ⇒ `dimensions_present` evidence 保 declared_false（不折回 legacy_default）。
- **R1-3c validate_case 入口**（M4 离线校验端到端）：结构化 dimensioned_views 声明 → per-view checks
  evidence 保 declared_true/declared_false。

**neuter 自查**（`/tmp/neuter_r1_3.py`，三处改动各短路一次）：
- neuter **case_metadata 结构化解析**（对象分支 `if False`）⇒ 红 **R1-3a + R1-3c**（R1-3c 端到端依赖
  解析）、绿 R1-3b（硬编码 states）。
- neuter **evidence_preflight 传参**（`dimensioned_state="legacy_default"` 恒值）⇒ 红 **R1-3b**、
  绿 R1-3a/R1-3c。
- neuter **validation_run 传参**（同恒值）⇒ 红 **R1-3c**、绿 R1-3a/R1-3b。
⇒ 三处改动各精确命中、零假锁；R1-3c 被解析 + 传参两处共同保证（端到端锁合理，r0 L-10/L-11 同型）。
POST-RESTORE 3 passed。

**受影响子集**（13 文件：batchB + validation/pipeline/evidence/isolation/merge/run_config/
run_stage_flow/check_parity/orchestrate/provenance，`-n 6`）⇒ **404 passed + 9 xfailed，零红**
（含 r0 13 锁 + R1-1 三锁 + R1-2 两锁 + J-2 三锁 + R1-3 三锁 + 保哈希守卫）。

### 6.8 R1-4（provision applicability 校验前置，失败不留可用产物）✅ 完成

**病灶**（派工单 §1.4）：`provision_run`（`run_provision.py:84-93`）顺序 = 写 view manifest →
写 run policy → **才**校验 applicability。strict 档失败时磁盘**已有**可用的 manifest + policy；
而 isolation build/merge **不调这道 gate**（只读已冻结 manifest+policy）⇒「跑一次 provision、
无视报错、继续走 isolation」即绕过 applicability 门。**本项目「raise ≠ 没落盘」教训同族**。

**改动**（`src/agent/execution/run_provision.py` `provision_run`）：把 strict 档 applicability 校验
**前置**到任何写盘前 —— 先 `build_view_manifest(case_dir)`（in-memory）→
`validate_dimensioned_applicability` → 通过才 `provision_view_manifest`（写）+ `provision_run_policy`
（写）。`build_view_manifest` 跑两次（前置 in-memory + `provision_view_manifest` 内部写时各一次），
但同 case_data、确定性 ⇒ 字节一致。失败 ⇒ `view_manifest.json` + `run_policy.json` 都不落盘。

**为何取「前置」而非「事务化清理」**：派工单 §1.4 给「校验前置，或失败时不留可用产物（事务化）」
二选一。前置在写盘前 raise ⇒ 根本不写 ⇒ 满足「不留可用产物」，且无需跟踪清理 `provision_view_manifest`
可能写的多个文件（view_manifest.json + exam_scope.json）。事务化清理是 nice-to-have，前置已满足要求。

**锁**（`tests/test_reading_ruler_r1_batchB.py`，走真实 `provision_run` 入口）：**R1-4 strict
applicability refusal leaves no artifact** —— SM21 结构化声明只覆盖 1/6 required view（与 r0
L-20_unknown 同款 fixture）⇒ `provision_run(regression)` raise `dimensioned_applicability_unknown` +
**view_manifest.json / run_policy.json 均未落盘**。r0 L-20_unknown 只断言 raises、不查盘；R1-4 补
「盘上无产物」断言。

**neuter 自查**（`/tmp/neuter_r1_4.py`）：把前置 validate 移回写盘后（恢复 r0 顺序）⇒ 红 **R1-4**
（写盘成功后再 raise ⇒ 盘上有产物 ⇒ assert not exists 失败）、**绿 L-20 三条**（raises 仍发生，只是
写盘后；L-20 只查 raises）⇒ **R1-4 锁唯一绑前置、零连带**。POST-RESTORE 4 passed。

**受影响子集**（8 文件：batchB + run_stage_flow + isolation + merge + run_pipeline_self_checks +
validation_run_baseline + a8_evidence_routing + view_manifest_generator，`-n 6`）⇒
**325 passed + 8 xfailed，零红**（含 r0 13 锁 + R1-1 三锁 + R1-2 两锁 + J-2 三锁 + R1-3 三锁 +
R1-4 一锁 + 保哈希守卫）。

### 6.9 R1-6（provenance: source.image_sha256 必须比对真实图像 hash）✅ 完成

**病灶**（派工单 §1.6）：`_structured_dimensioned_map`（`view_manifest.py`）只校验 `source.reviewer`
非空；`image_sha256` / `date` / `basis` 一律不查；**`image_sha256` 从不与该 view 的真实图像 hash
比对**。`source_hash = hash_obj(source)` 只证明「声明后来没被改」、证明不了「当初是真的」。锁 fixture
用 `"0"*64` 当图像 hash 并期望通过 ⇒ **一份伪造的「hortonyyx 已签字」声明可畅通无阻**——而这正是
S-3 要建的那个信任根。

**改动**（`src/agent/execution/view_manifest.py`，保哈希：sm24/sm21 不含结构化声明 ⇒ 不触发）：
- `_structured_dimensioned_map` 改返回 `(structured_dim, declared_image_hashes)` + 校验
  `source.image_sha256` 为非空字符串（提取进 `declared_hashes`）。
- `build_view_manifest` 在所有 required entry 构造后（Floor plans/elevation/supplementary 三段
  `_register` 完）加 **R1-6 校验循环**：对每个结构化声明的 `declared_image_hashes[stem]` 与该 entry
  的真实 `image_sha256` 比对；不等 ⇒ `source.image_sha256 mismatch` raise（伪造签字被拒）；声明的
  stem 无对应 required view ⇒ raise。legacy（`declared_image_hashes={}`）跳过 ⇒ sm24/sm21 字节不变。

**为何校验放 build_view_manifest 而非 _structured_dimensioned_map**：真实 image_hash 在 entry 构造
时算（`_normalize_declared_path` 的 `hash_file`），晚于 `_structured_dimensioned_map`（:940）。把
declared_hashes 一路带到 entry 构造后比对，避免重复 family 解析；DimensionedApplicability schema
**不加字段**（`source.image_sha256` 只用于校验、不进 manifest）⇒ 保哈希。

**fixture 真值**（`tests/test_reading_ruler_r1_batchB.py` `_set_structured_dim`）：先 `build_view_manifest`
原 testdata 算每个 required view 的真实 image_hash，写进 declarations 的 `source.image_sha256`
（覆盖 `"0"*64` 占位）⇒ r0 锁（L-20_complete/L-20_unknown/L-21）+ R1-4 锁用真 hash 继续 绿。

**锁**：**R1-6 forged image hash rejected** —— SM21 结构化声明 `1f_view` + `source.image_sha256="f"*64`
（非真实 hash，不经 `_set_structured_dim`）⇒ `build_view_manifest` raise `source.image_sha256 mismatch`。
对照 = r0 L-20_structured_complete（`_set_structured_dim` 填真 hash ⇒ build 成功）。

**neuter 自查**（`/tmp/neuter_r1_6.py`）：短路校验循环（`if False and declared_image_hashes:`）⇒
红 **R1-6**（假 hash 通过 ⇒ DID NOT RAISE）、**绿 L-20_structured_complete + 保哈希守卫**（真 hash
不校验也通过 / sm24·sm21 legacy 不进）⇒ **R1-6 锁唯一绑 hash 比对、零连带**。POST-RESTORE 3 passed。

**受影响子集**（14 文件：batchB + view_manifest_generator/schema/coverage + isolation + merge +
reading_typed_scoring_slice0/1 + reading_typed_adapter/score_integration + c2_b4b_phase_d/contract +
run_pipeline_self_checks + run_stage_flow，`-n 6`）⇒ **437 passed，零红**（含 r0 13 锁 + R1-1/2/3/4 +
J-2 + R1-6 + 保哈希守卫）。

### 6.10 R1-7（config/CLI 冲突改报错）✅ 完成

**病灶**（派工单 §1.7）：`_resolve_run_profiles`（R1-1 写）与 cmd_provision 的 config/CLI 解析都是
「config 声明优先、CLI 兜底」的 `or` —— 当 config 与 CLI **都显式声明且不一致**时静默取 config
（声明被 CLI 偷换而无人知）。属未在执行日志披露的规格偏离。派工单给「改成报错，或写进执行日志由 sol
挑战」二选一；§3.1 明确 R1-7 的锁必须走 CLI ⇒ 取「改成报错」。

**改动**（`scripts/tool_scripts/run_stage.py`）：
- `_resolve_run_profiles` 加 **冲突检测**：config 声明 run_profile/capability_profile（非 None）+
  CLI **显式传了非默认且不同**的值 ⇒ raise `run_profile conflict` / `capability_profile conflict`。
  argparse CLI 默认（exploratory/rectangular）计为「未传」——声明 regression 在 CLI 默认下仍是
  regression（R1-1 冻结权威意图）；只有 CLI 显式传了**冲突值**（如 --run-profile golden）才 raise。
  显式传**同值**（--run-profile regression 同 config）不报错。
- 新增模块常量 `_RUN_PROFILE_CLI_DEFAULT`/`_CAPABILITY_PROFILE_CLI_DEFAULT`（须与 main() 的 argparse
  default 一致）+ 返回值兜底 `or _..._DEFAULT`（兼容测试 `_args` 不设 capability_profile ⇒ None 的情形，
  与真实 argparse default="rectangular" 行为一致）。
- cmd_provision 改用 `_resolve_run_profiles`（统一冲突检测，不再自造 config/CLI 解析）。

**边界（诚实登记）**：argparse `--run-profile` default="exploratory"（非 None），「用户显式传 exploratory」
与「未传（默认 exploratory）」不可区分 ⇒ config=regression + CLI --run-profile exploratory 不报错
（config 赢）。这是有意的（exploratory 是更宽松档，config regression 冻结权威赢更安全；要降档应改 config、
不是传 CLI）。R1-7 抓的是「两个不同的严格档冲突」（regression vs golden）这类明显冲突。

**锁**（`tests/test_run_stage_flow.py`，走真实 `cmd_flow` CLI）：
- **R1-7 conflict**：run_config 声明 regression + CLI --run-profile golden ⇒ raise `run_profile conflict`。
- **R1-7 same-value 对照**：run_config 声明 regression + CLI --run-profile regression（同值）⇒ 不报错、
  config 赢（record.run_profile==regression）。证明 R1-7 只对「不同值」raise。

**neuter 自查**（`/tmp/neuter_r1_7.py`）：短路 run_profile 冲突 if（`if False and ...`）⇒ 红 **R1-7 conflict**
（不 raise ⇒ DID NOT RAISE）、**绿 R1-7 same-value + R1-1a**（同值/默认不涉及冲突检测）⇒ **R1-7 conflict
锁唯一绑冲突检测、零连带**。POST-RESTORE 3 passed。

**受影响**：`run_stage_flow` 全文件 `-n 6` ⇒ **26 passed，零红**（R1-7 两锁 + R1-1 三锁 + R1-2 两锁 +
既有 flow 锁）。

### 6.11 R1-1 context 补接（J-1 §1.2：context 真接上 + 不进 hash）✅ 完成

**裁定**（orchestrator 2026-08-03 §1.2）：采纳施工席的 (b) 保持 hash 收窄（R1-1 已做），但 **context 必须真
接上** —— 收窄的正当性建立在「其余项有记录、只是不参与 drift 判定」之上，而 R1-1 的 `context=None`
（全仓唯一生产调用者 `run_provision.py` 的 `provision_run` 从不传）⇒ 记录从未发生、收窄成了单纯丢信息。
**并要有一条锁断言它落盘且不进 hash**。

**改动**（`scripts/tool_scripts/run_stage.py`）：
- 新增 `_run_policy_context(args, run_config) -> dict`：构造非哈希审计快照，含
  `validation_scope`/`require_ep`/`confirmation_policy`/`judge_enabled` 四 toggle 的**实际取值 + 来源**
  （`structured_config` / `cli` / `default` / `sop`）。`judge_mode` 优先 structured（`run_config.judge_mode`），
  其次 CLI（`args.judge`），否则 default `"off"`；用 `hasattr` 兜底兼容测试 SimpleNamespace 不全的 args
  （v1 拒绝测试的 args 无 `judge`/`with_ep`）。
- cmd_run / cmd_flow / cmd_resample 的 `_manifest_for_attempts` 调用 + cmd_provision 的 `provision_run`
  调用**都传** `context=_run_policy_context(args, run_config)`（4 处）。R1-1 的 `# TODO awaits J-1 ruling`
  注释填掉。

**为何 context 仍不进 hash**（裁定 §1.2 锁要求）：`_run_policy_hash`（`run_policy_freeze.py:53-57`）只含
`(capability_profile, run_profile)` —— gate① 实际消费、决定 blocking 的两个旋钮。`provision_run_policy`
的 drift 检测（`:226`）只比 `policy_hash`，不比 `context` ⇒ toggle 变（如 judge_mode stop→off）不改
`policy_hash`、不触发 drift。context 是审计快照（操作者声明了什么），不是 drift 口径。

**锁**（`tests/test_run_stage_flow.py`）：
- **R1-1 context recorded with sources**（走真实 `cmd_flow`）：run_config 声明 `judge.mode=stop` + CLI
  `--with-ep` ⇒ `run_policy.json` 的 `context` 含四 toggle + 来源（`judge_enabled.judge_mode=="stop"`、
  `source=="structured_config"`、`require_ep.value is True`、`source=="cli"`、`confirmation_policy=="required"`、
  `validation_scope=="full"`）。
- **R1-1 context not in hash, no drift**（走 `provision_run_policy`）：同 `(capability, run_profile)` + **不同**
  context ⇒ `policy_hash` 逐字相同 + 第二次 provision idempotent（返回 existing，不 drift）。

**neuter 自查**（`/tmp/neuter_r1_1ctx.py`，两个 hook）：
- neuter **A**（`_run_policy_context` 返回 `{}`）⇒ 红 **context recorded**（context 空 ⇒ KeyError）、绿
  **context not in hash**（不用 `_run_policy_context`）。
- neuter **B**（drift 检测加 `or existing.context != expected.context`）⇒ 红 **context not in hash**（不同
  context ⇒ drift raise）、绿 **context recorded**（一次 provision 不 drift）。
⇒ 两 hook 各绑一锁、零假锁。POST-RESTORE 2 passed。

**受影响**：`run_stage_flow` + `batchB` `-n 6` ⇒ **49 passed，零红**（R1-1 context 两锁 + R1-7 两锁 + R1-1
三锁 + R1-2 两锁 + r0 锁 + 既有 flow/v1 测试）。

### R1-5 (terra) ✅ 完成

**接手判断**：GLM 留下的约 59 行起点方向正确（`approve_geometry` / `geometry_is_approved` /
`record_baseline` 改走 frozen resolver），但 `record_baseline` 对 legacy run 仍以 CLI
`require_ep` / `run_profile` 自造 `RunPolicy`。这会让没有 `_run/run_policy.json` 的只读 replay
冒充 regression/golden；我删掉该 fallback，legacy 一律为显式 `legacy_defaulted` 的
`exploratory/rectangular`。

**文件与理由**：

- `src/agent/execution/run_policy_freeze.py`：新增 `effective_run_policy`，从冻结 record + 非哈希
  context 重建 validation 所需 policy；异常 context 值保守回落到默认，避免 `"false"` 这类字符串误变真。
- `src/agent/execution/step_orchestrator.py`、`src/agent/execution/approval.py`：两个人工几何调用方
  均消费 frozen policy；approval 持久化 `run_policy_source` / legacy 位 / tier，使旧 replay 可见为 legacy。
- `scripts/tool_scripts/record_baseline.py`：记账只消费 frozen policy，`baseline.json.run_policy` 写出
  source、legacy、profile、capability、hash；兼容保留 CLI 形参但不允许其重造 tier。
- `scripts/tool_scripts/run_stage.py`：`cmd_run` / `cmd_flow` 在 provision 后、`cmd_judge` 在只读 replay
  时以 `_policy_with_frozen_tier` 覆盖本地 capability/run profile。因此 correction、modelling、grade 和
  typed scorer 的生产调用均得到 frozen tier；golden record warning 同样改读该 policy。
- `tests/test_run_stage_flow.py`、`tests/test_orchestrate_baseline.py`：新增 R1-5 四锁。

| Lock | 真实入口 / 精确断言 |
|---|---|
| `approve_geometry` | `cmd_approve_geometry` → 真 `validate_case`；`downstream.build` 行存在，CheckReport headers = regression / orthogonal_polygon。 |
| `geometry_is_approved` | 真实 resume predicate → 真 `validate_case`；同一 `downstream.build` + headers。 |
| `record_baseline` frozen | 真 `record_baseline` 调用，`baseline.run_policy` header = structured regression / orthogonal，且 `downstream.build` blocking 行存在，即冻结 context 的 `require_ep=true` 生效而 CLI false 不得覆盖。 |
| `record_baseline` legacy control | 真 `record_baseline` 调用；`baseline.run_policy` 显式 legacy-defaulted / exploratory / rectangular，且严格-only `downstream.build` 不出现。 |

**neuter self-check**（`/tmp/neuter_r1_5.py`，精确把 `effective_run_policy` 短路成
`RunPolicy()`，同一四锁，随后 restore + `git diff --exit-code`）：红 = `approve_geometry`、
`geometry_is_approved`、`record_baseline frozen`；绿 = `record_baseline legacy control`。这是一个共享的
frozen-policy reconstruction hook，三条依赖锁的连带是预期的；legacy 对照不依赖该 hook。restore 后
四锁 **4 passed**。

**验证**：相关集（flow / baseline / step orchestrator / batch-B）**117 passed + 1 xfailed，零红**；
全仓 `pytest -q -n 6` ⇒ **2089 passed + 10 xfailed，零红**。sm24/sm21 manifest byte guard 仍随全仓绿。

**register**：无开放 gap。派工单点名的 correction / modelling / grade（含 typed scoring strict rejection）
不是另留 local tier：它们由 run/flow provision 后的 `_policy_with_frozen_tier` 统一覆写；judge-only replay
也走同一 helper。非 tier 的 draw-budget / reread-availability 仍是调用期操作旋钮，未注册为 frozen policy。


---

## 7. r2 返工

- 上游：[r2 派工单](../request/2026-08-04_reading_ruler_r1_batchB_r2_dispatch.md)（以它为准）·
  [交叉审裁定 + r2 清单](../request/2026-08-03_reading_ruler_r1_crossreview_ruling_and_r2.md)
- 范围：r2-1 → r2-2 → r2-3 → r2-4（先小后大）。
- **本段状态**：r2-1 ✅、r2-2 ✅ 已落库（commit `6ff9f4e` / `d601130`）；**r2-3 ⛔ 停下上报（锁结构性不可绑，已实证）**；
  **r2-4 ⛔ 停下上报（(a)/(b) 二选一无可行 in-scope 解，需 orchestrator 裁）**。详见 7.3 / 7.4。

### 7.1 r2-1（capability_profile 拼错 fail-closed）✅ 完成 · commit `6ff9f4e`

**病灶**：`_parse_capability_profile`（`run_config.py:193`）对非法值 warn+None ⇒ `run_config.capability_profile=None`
⇒ `_resolve_run_profiles` 落回 CLI 默认 rectangular；`run_policy_freeze.py:209` `capability_profile or "rectangular"`
又静默兜一次。**`orthogonal_polygone`（拼错一字母）⇒ 静默降 rectangular**，冻结件仍标 structured_config。
capability 决定 correction v2/v3 schema，影响面宽于判卷严格度。

**改动**（与 r1 `_parse_run_profile` 完全对称）：
- `run_config._parse_capability_profile`：present-but-invalid 由 warn+None 改 **raise `ValueError(capability_profile_invalid)`**；
  absent（`value is None`）仍返回 None、CLI/legacy 权威。raises 经 `load_run_config` 在所有新 run provisioning 路径生效；
  `_declared_policy` 只读 replay 自读 YAML 照旧容忍标 legacy（历史 replay 不受影响）。
- `run_policy_freeze._build_record`：新 source-conditional 守卫 —— 新 run（`source != legacy_defaulted`）
  `capability_profile=None` ⇒ raise `capability_profile_not_declared`（新 run 不得靠 rectangular 兜，与 run_profile
  的 `run_profile_not_declared` 对称）；legacy replay 保留 rectangular 兜底。
- `run_policy_freeze.provision_run_policy`：去掉冗余 `capability_profile or "rectangular"`（resolver 是 CLI 权威）。

**锁**（`tests/test_run_stage_flow.py`，走真实 `cmd_flow`，形态照抄 R1-2 那对）：
- **r2-1a typo**：`capability_profile: orthogonal_polygone` ⇒ raise `capability_profile_invalid` + 冻结前
  （`_run/run_policy.json` 与 `run_manifest.json` 均不存在）。
- **r2-1b absent 对照**：不声明 capability ⇒ CLI 默认 rectangular 兜底冻结成功（不 fail-closed）。

**neuter 自查**（`/tmp/neuter_r2_1_*.py`，精确替换→跑→立即恢复）：
- neuter point1（`_parse_capability_profile` 回 warn+None）⇒ 红 **r2-1a**、绿 **r2-1b**（零连带，point1 由 r2-1a 绑）。
- neuter point2（恢复 `or "rectangular"` + 摘 `_build_record` 守卫）⇒ **两条 CLI 锁皆绿** ——
  ⚠️ **诚实披露**：point2 守卫 CLI 不可达（`_resolve_run_profiles` 恒给非 None capability，provisioning 永不靠兜底），
  故无 CLI 锁能绑它。守卫为**防御性结构强制**（防未来 resolver 回归把 None 漏到冻结层），r2-1 主诉求
  （typo fail-closed）由 r2-1a CLI 锁绑定。point2 的价值是结构执行「新 run 不得靠它兜」，非回归锁。

**受影响子集**（run_stage_flow + batchB + orchestrate_baseline + run_pipeline_self_checks + isolation）⇒
**301 passed + 1 xfailed 零红**。

### 7.2 r2-2（冻结记录 source 真实反映来源）✅ 完成 · commit `d601130`

**病灶**：`run_policy_freeze.py:210` `_build_record(..., source="structured_config", ...)` **写死**。全仓新 run 一律
structured_config、replay 一律 legacy_defaulted ⇒ 纯 CLI 冻结（`run_config.yaml` 没声明、靠 `--run-profile` 兜）
也被标成「来自结构化配置」；连带 R1-1b `assert source == structured_config` **恒真**（空转断言）。

**改动**（source 三态 + legacy_defaulted）：
- `RunPolicyRecord.source` Literal 扩为 `structured_config` / `cli` / `mixed` / `legacy_defaulted`。
- `_resolve_run_profiles` 返回 `(run_profile, capability_profile, source)`：两者都 config 声明 ⇒ structured_config；
  都不声明 ⇒ cli；恰一个 ⇒ mixed。
- `provision_run_policy` / `provision_run` / `_manifest_for_attempts` 全链接受 `source` 并透传（默认 structured_config
  供直接/测试调用；production SOP 由 `_resolve_run_profiles` 计算）；`_build_record` 用传入 source。
- 修 `provision_run_policy` existing-record 检查：原 `source != "structured_config"` 在新语义下会误拒合法 cli/mixed
  幂等重冻结，改为只拒 `legacy_defaulted`（权威 flag）。
- **修恒真断言**：`test_R1_2_absent`（config 都不声明）source 由 structured_config 改 **cli**；r2-1b（只声明 run_profile）
  改 **mixed**。

**漂移复验按来源判**：`resolve_frozen_run_policy` 本就只对 config 声明字段（`decl` 非 None）做 drift 复核 ——
cli run 无声明故 N/A、mixed run 只复核声明侧。source 现让该适用面机器可见（**无需改 drift 逻辑，已正确**）。

**锁**（`tests/test_run_stage_flow.py`，走真实 `cmd_flow`）：
- **r2-2 lock A cli**：都不声明 + CLI `--run-profile` ⇒ `source == "cli"`（≠ structured_config）。
- **r2-2 lock B structured**：两者都声明 ⇒ `source == "structured_config"`（原恒真断言，现有意义）。
- **r2-2 lock C mixed**：只声明 run_profile ⇒ `source == "mixed"`。

**neuter 自查**（`/tmp/neuter_r2_2.py`）：`_resolve_run_profiles` source 计算回硬编码 structured_config ⇒
红 **lock A + lock C**、绿 **lock B**（参考态）⇒ source 计算由 A/C 绑定。

**受影响子集**（run_stage_flow + batchB + orchestrate_baseline + isolation + execution_foundation +
provenance_baseline + validation_run_baseline）⇒ **328 passed + 9 xfailed 零红**。

### 7.3 r2-3（`_policy_with_frozen_tier` 零回归守卫）⛔ 停下上报 —— 锁结构性不可绑（已实证）

**派工单要求**：补一条走真实 CLI（cmd_run/cmd_flow）的锁 —— 构造「冻结档=regression/orthogonal_polygon、
而 CLI 与 run_config 当次给 exploratory/rectangular」的 run，断言 checks.json 头部=regression/orthogonal +
某条严格档才 BLOCK 的 check-id 行；**摘掉 `_policy_with_frozen_tier`（改回 `return policy`）必须红**。

**⛔ 实证结论：此锁按派工单指定的形态结构性不可绑。** 两条独立证据（探针 `/tmp/probe_r2_3.py`，真实 `_draw_reading`）：

1. **派工单指定的散度场景（冻结=regression、当次 CLI/config=exploratory）在到达 `_policy_with_frozen_tier` 之前
   就被 provisioning 的 drift 门挡掉。** 实跑：先 `provision_run_policy(regression/orthogonal)` 预冻结，再
   `cmd_flow`（config 不声明 + CLI exploratory）⇒ **直接 raise `run_policy_drift: the run policy changed after
   this run was provisioned`**。provisioning 的幂等性 drift 检查（`existing.policy_hash != expected.policy_hash`）
   在 `_policy_with_frozen_tier` 之前触发 ⇒ 散度根本到不了 `_policy_with_frozen_tier`。

2. **非散度场景（config 声明 regression、CLI 默认 exploratory）能到 `_policy_with_frozen_tier`，但它改变不了任何东西。**
   实跑：`_policy_with_frozen_tier` 被调用时 in/out 的 (run_profile, capability_profile) **完全相同**
   （`('regression','orthogonal_polygon') → ('regression','orthogonal_polygon')`，override 改变 = False）。
   把它 neuter 成 `return policy` 后，0_reading checks.json 头部**仍是 regression/orthogonal_polygon**
   （与未 neuter 逐字相同）⇒ **neuter 不红任何头部/check-id 断言**。

**根因分析**：派工单 r2-3 的前提是「摘掉 `_policy_with_frozen_tier` ⇒ correction/modelling/grade/typed-scoring
退回读 CLI/默认档（= r0 MAJOR 原状）」。这个前提在 **r0 成立、在 R1-1 之后不成立**：
- R1-1 的 `_resolve_run_profiles`（config-wins）让 cmd_run/cmd_flow 的 `_make_policy` 直接拿到 resolved 档位；
- `_manifest_for_attempts` 用**同一对** resolved (run_profile, capability_profile) 冻结；
- 所以 `_make_policy` 的档位 **恒等于** 冻结档位，`_policy_with_frozen_tier` 的 override 是**恒空操作**。
- 而 provisioning 的 drift 门又保证「冻结档 ≠ 当次 resolved」的散度场景在到达 `_policy_with_frozen_tier` 前 raise。

⇒ **`_policy_with_frozen_tier` 在 cmd_run/cmd_flow 上是结构性冗余**（R1-1 已从根上保证 `_make_policy` 带冻结档）。
派工单把它当「正文实现」、把 `effective_run_policy`（approve_geometry/record_baseline）当「旁支」——
**实际上 `effective_run_policy` 才是承载 legacy/散度 diverge 的那根线**（它读冻结 record 重建 policy，
对 legacy_defaulted run 返回 expl/rect 默认；已被 R1-5 四锁绑住）。`_policy_with_frozen_tier` 反而是冗余第二层。

**与派工单 §0② 的呼应**：派工单说「r2-1 正是停下上报被接住的」。本条同型 —— 我**不伪造锁**（伪造一个
neuter 不红的锁 = 假锁，违「锁绿 ≠ 锁真绑」）。请 orchestrator 裁其一：
- (i) 接受「冻结档到达下游」**已由 R1-1c 绑定**（config 声明 regression ⇒ checks.json 头部 regression + closure BLOCK），
  `_policy_with_frozen_tier` 是冗余防御、无独立锁可达 —— r2-3 视为已由 R1-1c 覆盖、本条收口；
- (ii) 若要 `_policy_with_frozen_tier` 真正承载（可绑），需让它成为**唯一**档位权威 —— 即 `_make_policy` 不再
  用 resolved 档位、改用占位/默认，由 `_policy_with_frozen_tier` 统一覆写。但这是**改生产码逻辑**，r2-3 明令禁止；
- (iii) 其它 orchestrator 指定的形态。

**未改任何生产码**（遵守「⛔ 本条不许改生产码逻辑」）。r2-3 无 commit。

### 7.4 r2-4（context 已成判定面，漂移面没扩 + G-4 免责声明成假注释）⛔ 停下上报 —— (a)/(b) 无可行 in-scope 解

**病灶**（派工单 + 路审 MAJOR-3，已核实）：`run_policy_freeze.py:22-30` G-4 注释把 context 排除在漂移检测外的
理由写成「they do not affect reading-check blocking」；但 R1-5 后 `effective_run_policy`（`:292-335`）从 context 取
`require_ep` 等，而 `validation_run.py:120` `require_ep` 决定 `downstream.build` 是否成为 fail-closed 必需件 ⇒
**理由不成立**。实跑：篡改 `context.require_ep.value` true→false 并自行重算 `content_sha256`（该哈希是 payload
自身的哈希、不绑外部信任根）⇒ 校验与漂移复核照常通过 ⇒ baseline 记账静默不再记缺失 EP 为阻断行、头部仍 regression。
精确划界：几何签字门不受影响（只读 geometry_digest/geometry_approved），**受影响只有 baseline 记账**。

**⛔ 核心难点（实证推导）**：`require_ep` 是 CLI `--with-ep` 标志，**在 `run_config.yaml` 里没有外部信任根**。
- **option (a)「纳入 policy_hash / 漂移复核」挡不住 require_ep 篡改**：`policy_hash` 与 `content_sha256` 都是 payload
  自身的哈希、可自行重算；drift 复核的唯一外部信任根是 `run_config.yaml`（profiles），而 require_ep 不在其中。
  （context 里其余三项 judge_enabled/confirmation_policy/validation_scope 可从 run_config/SOP/default 重推导，
  故 (a) 对它们有效；唯独 require_ep 无外部根 ⇒ (a) 对派工单点名的 require_ep 篡改无效。）
- **option (b)「收回 effective_run_policy 对 context 的消费，只从冻结档位 + 当次显式入参推导」能消除 require_ep
  篡改面**（require_ep 改从当次显式入参来，冻结 context.require_ep 不再被消费）—— 但 require_ep 不再是冻结属性
  意味着 R1-5 的 approve_geometry 锁（断言「frozen context.require_ep=true ⇒ downstream.build 行存在」）的**前提
  失效**，需把该锁改写成「显式 require_ep=true ⇒ downstream.build」（锁的意图保留、来源改）。这会动到**刚被路审
  验为真锁的 R1-5 锁**，r2-4 派工单未授权改这些锁。

⇒ **(a) 对命名威胁（require_ep）无效；(b) 可行但需改 R1-5 锁（超出 r2-4 派工单明示范围）。** 两条都非干净的
in-scope 解。请 orchestrator 裁其一：
- (i) 采纳 (b) 并**授权我改写受影响的 R1-5 锁**（approve_geometry / record_baseline 的 downstream.build 断言由
  「frozen context」改「显式入参」），我把 require_ep 从冻结 context 消费收回 + 改 G-4 注释 + 补 r2-4 锁；
- (ii) 采纳 (a) 的**升级版**：把 require_ep（及/或 validation_scope）**声明进 `run_config.yaml`** 给它外部信任根，
  再纳入 drift 复核（含 schema 改动，较大）；
- (iii) 其它 orchestrator 指定的形态。

**未改任何生产码**（(a)/(b) 选择未定，不动）。r2-4 无 commit。G-4 假注释**暂未改写**（派工单明令「⛔ 不接受只改注释」，
故等 (a)/(b) 落定后一并改，避免出现「只改了注释」的中间态）。

### 7.5 全仓测试结果（r2-1 + r2-2 回归核验）

`pytest -q -n 6`（交付前一次全仓，⛔ 无 `-m`）⇒ **2094 passed + 10 xfailed，零红**
（基线 2089 + r2-1 ×2 锁 + r2-2 ×3 锁 = 2094，精确符合）。

⚠️ **复证「交付前跑一次全仓」纪律**：r2-1 首次全仓抓到 1 红 ——
`tests/test_run_config.py::test_run_config_invalid_capability_profile_falls_back_to_cli_authority`
编码了 r2-1 要修的旧缺陷（非法 capability warn+None 回退 CLI）。我 r2-1 受影响子集（run_stage_flow/batchB/
orchestrate/run_pipeline_self_checks/isolation）未覆盖 `test_run_config.py`，故漏扫；**只有全仓抓到**。
已改写为断言新 fail-closed 行为（commit `b9923f0`），二次全仓 2094 绿零红。教训：改 `_parse_*` 类解析函数的
失败语义时，受影响子集须含其**直接单测文件**（`affected_tests.py` 的 AST import 边对此未捕获，因 test_run_config
不 import 被改符号、只通过 `load_run_config` 间接走到）。

### 7.6 给 orchestrator 的上报摘要

- **r2-1 / r2-2 已落库**（commit `6ff9f4e` / `d601130`），neuter 自查 + 受影响子集零红，全仓结果见 7.5。
- **r2-3 停下上报**：锁按派工单指定形态**结构性不可绑**（两条独立实证：散度场景被 drift 门前置拦、非散度场景
  override 是恒空操作）。根因 = R1-1 的 `_resolve_run_profiles` 已让 `_make_policy` 带冻结档 ⇒
  `_policy_with_frozen_tier` 冗余。**未改生产码、未伪造锁。** 请裁 (i)/(ii)/(iii)（见 7.3）。
- **r2-4 停下上报**：(a) 对命名威胁 require_ep 无效（无外部信任根）；(b) 可行但需授权改 R1-5 锁。
  **未改生产码、未只改注释。** 请裁 (i)/(ii)/(iii)（见 7.4）。

遵守派工单「再遇欠规格边界，停下上报 —— 不要自行降级为假设」。等 orchestrator 裁 r2-3 / r2-4 后续作。


---

## 8. r2b（r2-3 / r2-4 裁定后返工）

- 上游：[r2b 裁定 + 续派工单](../request/2026-08-04_reading_ruler_r1_batchB_r2b_ruling_and_dispatch.md)（**本轮唯一权威任务书**）·
  [r2 派工单](../request/2026-08-04_reading_ruler_r1_batchB_r2_dispatch.md)·
  [交叉审裁定 + r2 清单](../request/2026-08-03_reading_ruler_r1_crossreview_ruling_and_r2.md)
- 前置状态：HEAD `25b94dc`（批 B r2 §7 收尾）。r2-1 / r2-2 已落库（`6ff9f4e` / `d601130`）。
  **两条停下上报（§7.3 r2-3 / §7.4 r2-4）orchestrator 都判成立、裁定已出**：
  - **r2-3 改判**：解除原派工单「不许改生产码」限制；删冗余 + 内联 judge + 核实 R1-1 既有锁。
  - **r2-4 采纳 (b)**：effective_run_policy 停止从 context 取判定值；授权改写受影响 R1-5 锁。
- 本段交付：r2-3 ✅ commit `2ea029f` · r2-4 ✅ commit `7dc31bd`。全仓 **2095 passed + 10 xfailed 零红**（基线 2094 + r2-4 新增 tamper 锁 1）。

### 8.1 r2-3（删冗余 `_policy_with_frozen_tier` + cmd_judge 内联 + 核实 R1-1c 既有锁）✅ commit `2ea029f`

**裁定要点**：`_policy_with_frozen_tier` 在 cmd_run/cmd_flow 上是结构性冗余——R1-1 的
`_resolve_run_profiles`(config-wins) 已让 `_make_policy` 直接带冻结档 ⇒ 冻结档恒等于当次
resolved 档 ⇒ override 是恒空操作（§7.3 已双实证、裁定 §1.1 orchestrator 独立核实并补证 cmd_judge
第三路同样恒空）。其 docstring 声称「every correction/modelling/grade/check consumer gets the
frozen tier」今天是假的——与 r2-4 的 G-4 假注释同族（模块声称在守、其实没守）。

**改动**（`scripts/tool_scripts/run_stage.py`，-22/+13）：
1. **删除 `_policy_with_frozen_tier` 函数体**（原 1707–1721）+ **cmd_run / cmd_flow 两处调用**
   （原 1965 / 2164）。删除后档位一致性由三处真守卫保证：① R1-1 `_resolve_run_profiles`
   （config-wins）；② provisioning drift 门；③ R1-5 `effective_run_policy`。
2. **cmd_judge 不删，改成内联「档位来自冻结记录」**：原 `_make_policy(args.run_profile,
   args.capability_profile)` + `_policy_with_frozen_tier` → 改为 `resolve_frozen_run_policy(run_dir)`
   取冻结档（取不到标 legacy），注释写明「本路当前无 tier 消费者（submit_verdict 只读 draw
   budget + reading_runner_available），此处只保证来源正确」。
3. **⛔ 不新增「断言未被消费的值」式锁**（本项目「记录了就以为守住」第二类假锁）。
   **登记债 D-4**（注释内已写明）：若将来 judge 路出现读档位的消费者，必须同时补回归锁。

**R1-1c 既有锁真绑——双 neuter 复跑**（`/tmp/neuter_r2_3_r11c.py` + `_header.py`）：

R1-1c（`test_R1_1_flow_regression_freezes_to_reading_checks_header`）断言：config 声明
regression+orthogonal ⇒ 真 cmd_flow + 真 `_draw_reading` ⇒ attempt checks.json 头部
run_profile=regression / capability=orthogonal / run_policy_sha256 / structured_config +
`1f_view.reading.dimension_chain_closure` 在 regression 下 BLOCK。**关键**：checks.json 头部来自
`_draw_reading` 内的 `resolve_frozen_run_policy`（读冻结记录），**不经过被删的
`_policy_with_frozen_tier`**——故删它不影响 R1-1c。

| neuter | 摘掉处 | R1-1c 结果 | 失败模式 |
|---|---|---|---|
| config-wins → CLI-only | `_resolve_run_profiles` 解析行（`cfg_run or` → `cli_run or`） | **红** | drift 门 guard② 拦住：`run_policy_drift: run_config.yaml run_profile='regression' differs from frozen 'exploratory'`（散度在产 checks.json 前即 raise） |
| `_draw_reading` 冻结档读取 → exploratory | else 分支 `eff_run_profile = policy_record.run_profile` → `"exploratory"` | **红** | **经自身头部断言**：`assert report.run_profile == "regression"` → `AssertionError: assert 'exploratory' == 'regression'`（且 exploratory 下 closure 为 FLAG 非 BLOCK，`report.blocking()` 亦红） |

两条 neuter 都红 ⇒ **R1-1c 真绑**（删 `_policy_with_frozen_tier` 后冻结档到达 checks.json 的性质
仍由 R1-1c 守住，经 config-wins 解析 + `_draw_reading` 冻结读取两根线）。两脚本均精确替换→跑→
**立即恢复**，工作树复原（`git diff` 仅余未提交编辑，无 neuter 残留）。

**受影响子集**（test_run_stage_flow + test_orchestrate_baseline + test_step_orchestrator +
test_reading_ruler_r1_batchB，`-n 6`）⇒ **123 passed + 1 xfailed 零红**（删冗余不破坏行为）。

### 8.2 r2-4（effective_run_policy 收回 context 消费 + 改写 R1-5 锁 + 补篡改面锁）✅ commit `7dc31bd`

**判据**（裁定 §2.1，写进 G-4 注释）：**只有在 `run_config.yaml` 里声明的东西才有外部信任根，
才配冻结成「档位政策」并参与防漂移；命令行运行期开关（`--with-ep` / draw budget / reread
availability / judge 开关 / validation_scope）一律来自当次调用、不冻结、不据以判定。** 据此 (a) 从
一开始就不成立（`content_sha256`/`policy_hash` 都能自行重算，`require_ep` 不在 config 里 ⇒ 无外部根）。

**改动逐条**：

1. **`effective_run_policy` 停止从 context 取判定值**（`run_policy_freeze.py:329`）：签名改为
   `effective_run_policy(run_dir, *, require_ep=False, confirmation_policy=None,
   judge_enabled=False, validation_scope=None)`——4 个操作旋钮由**调用方按当次调用传入**
   （默认 `RunPolicy()` 默认值）；档位仍取冻结 record 的 run_profile / capability_profile（有外部根）。
   删除原 `_ctx` / `_bool_ctx` / `_enum_ctx` 三段 context 解析逻辑。**从结构上消除篡改面**：
   编辑 context（哪怕重算 `content_sha256`）改不了任何判定，因为 context 不再是判定输入。
   - `record_baseline.py:508` 改传 `effective_run_policy(run_dir, require_ep=require_ep)`（require_ep
     来自 CLI `--with-ep` / `--require-ep`）。
   - geometry 门（`step_orchestrator.py:485 / 507` 的 approve_geometry / geometry_is_approved，无
     `--with-ep` 入口）用默认 `require_ep=False`（生产亦然：flow 的 auto-approve 也不传 require_ep）。
2. **context 块标注为非权威审计快照**（`run_policy_freeze.py` `RunPolicyRecord.context` 字段注释）：
   「NON-AUTHORITATIVE audit snapshot … NEVER authoritative, NEVER consumed for decisions
   (effective_run_policy sources these from the caller, not here)」。
3. **改写 G-4 免责声明**（`run_policy_freeze.py` 模块 docstring）：写成实况 + §2.1 判据，⛔ 删除
   「这些开关不影响 reading-check blocking 所以不进哈希」旧理由（已不成立：require_ep 经
   effective_run_policy 决定 downstream.build fail-closed）。
4. **改写受影响 R1-5 锁**（裁定授权）：
   - **2 条 geometry 锁**（`test_run_stage_flow.py`）：require_ep 不再来自 frozen context ⇒ geometry
     门（require_ep=False）不再产 downstream 行；锁改为断言**冻结 tier 头**（`reports["1_correction"]`
     的 run_profile=regression / capability=orthogonal，非 RunPolicy 默认）+ `downstream not in reports`。
   - **record_baseline frozen 锁**（`test_orchestrate_baseline.py`）：改为断言冻结 tier 头 +
     **调用方** `require_ep=True` ⇒ downstream.build 阻断行（require_ep 来自调用方、非 frozen context）。
   - **legacy 对照锁**：`require_ep=True→False`（r2-4 后 require_ep 是调用方旋钮、与 legacy 状态独立；
     legacy 仍标 legacy-defaulted/exploratory/rectangular 不冒充严格档）。
5. **补篡改面消失锁** `test_R1_5_record_baseline_context_tamper_does_not_change_blocking`
   （`test_orchestrate_baseline.py`）：provision 冻结 regression/orthogonal（context.require_ep=False）
   → **篡改 run_policy.json 的 context.require_ep=True 并重算 content_sha256**（用 `hash_obj` 重算
   payload 自哈希，使篡改件仍通过完整性校验）→ `record_baseline(require_ep=False)` ⇒ 断言 baseline
   阻断行**仍无 downstream.build**（篡改的 context 被忽略）+ 冻结 tier 头仍 regression/orthogonal
   （篡改只动 context、未动 tier）。

**neuter 自查表**（`/tmp/neuter_r2_4.py`，两 neuter 各替换→跑 5 锁→立即恢复）：

| neuter | 摘掉处 | 红的锁 | 绿的锁（合理） |
|---|---|---|---|
| **A**（`effective_run_policy` → `return RunPolicy()` 全默认） | 最终 return | **2 geometry 锁 + record_baseline frozen 锁**（裁定 §2.4 要求「这两条锁」= geometry 两锁必红；frozen 锁亦红，bonus） | legacy 对照（legacy 默认 == RunPolicy 默认）；**tamper 锁**（其 tier 断言取自 `frozen` 非 `effective`，downstream.build 缺席断言在 require_ep=False 下成立——tamper 锁只该被 neuter B 红） |
| **B**（`effective_run_policy` 读 `record.context.require_ep`、覆盖调用方） | `record = resolve…` 后注入 `_ctx_req` | **tamper 锁**（篡改 True 覆盖调用方 False ⇒ downstream.build 出现 ⇒ 「缺席」断言红，裁定 §2.5 要求）+ record_baseline frozen 锁（空 context 覆盖调用方 True，副作用） | 2 geometry 锁（neuter B 只动 require_ep、geometry 锁断言 tier 不受影响）；legacy 对照 |

⇒ **neuter A 红 geometry 两锁（r1 轻门验过的性质保留、未在改写中丢掉）；neuter B 红 tamper 锁
（(b) 实现真绑）**。两 neuter 各精确命中、零假锁。脚本立即恢复，工作树无残留。

**受影响子集**（test_orchestrate_baseline + test_run_stage_flow + test_step_orchestrator +
test_reading_ruler_r1_batchB，`-n 6`）⇒ **124 passed + 1 xfailed 零红**（含新增 tamper 锁）。

### 8.3 全仓测试结果（交付前一次全仓，⛔ 无 `-m`）

`pytest -q -n 6` ⇒ **2095 passed + 10 xfailed，零红**（基线 2094 + r2-4 新增 tamper 锁 1 = 2095，
精确符合、零回归）。sm24/sm21 manifest byte guard 仍随全仓绿（r2b 未碰 manifest / gt / testdata）。

### 8.4 合规自检

| 项 | 结论 |
|---|---|
| 锁走真实 CLI 入口（argparse/cmd_*） | ✅ r2-3 删冗余无新锁；R1-1c 经真 cmd_flow；r2-4 改写锁经真 cmd_approve_geometry / 真 record_baseline / 真 geometry_is_approved |
| 断言落具体 check-id 行 + checks.json/baseline 头部字段 | ✅ R1-1c 落 `report.run_profile`+`dimension_chain_closure` BLOCK；r2-4 锁落 stage-report tier 头 + baseline `run_policy` 头 + `blocking` 行 |
| 每条 neuter 自查如实登记 | ✅ r2-3 双 neuter（R1-1c）；r2-4 双 neuter（A/B）均贴结果 |
| neuter 选点覆盖本单正文点名的实现 | ✅ r2-3 点名 `_policy_with_frozen_tier`（已删）+ R1-1c；r2-4 点名 `effective_run_policy` context 消费 |
| 不 push | ✅ HEAD `7dc31bd`，未 push |
| 不碰 `gt/**` 与 sm24 `testdata_prompt.json` | ✅ r2b 零触碰（4 文件 = run_policy_freeze / record_baseline / 2 测试） |
| 不读 GT | ✅ |
| 不做批 C/D/R1.5 | ✅ 批 C 半截仍在 stash 未取 |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ plan.md M 为前置既有、非本次 |
| 做完一件存一件、每条改完即 commit | ✅ r2-3 `2ea029f` / r2-4 `7dc31bd` 两条本地 commit |

### 8.5 给 orchestrator 的交付摘要

- **r2-3 已落库**（`2ea029f`）：删 `_policy_with_frozen_tier` 函数体 + cmd_run/cmd_flow 调用；
  cmd_judge 内联冻结档来源；债 D-4 已登记（注释 + 本段）。R1-1c 既有锁经双 neuter 证实真绑
  （删冗余后冻结档到达 checks.json 的性质未失）。**未伪造锁、未改不该改的生产码逻辑。**
- **r2-4 已落库**（`7dc31bd`）：采纳 (b)，effective_run_policy 收回 context 消费、4 旋钮改调用方
  传入；context 标非权威审计快照；G-4 改写实况 + §2.1 判据；改写受影响 R1-5 锁（neuter A 红
  geometry 两锁、性质保留）；补篡改面消失锁（neuter B 红）。**未只改注释（G-4 与代码改动同落）。**
- 全仓 2095 passed + 10 xfailed 零红。

本轮未遇新的欠规格边界（裁定书已把 r2-3/r2-4 的形态与判据给定死），照裁定执行完毕。








