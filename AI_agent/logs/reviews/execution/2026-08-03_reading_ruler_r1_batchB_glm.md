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

