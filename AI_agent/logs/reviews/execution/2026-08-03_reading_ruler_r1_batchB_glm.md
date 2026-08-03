# R1 修尺子 · 批 B 施工执行日志（施工 = GLM）

- 日期：2026-08-03
- 上游：[裁定](../request/2026-08-03_reading_ruler_r1_batchBC_ruling.md)（冲突处以它为准）·[派工单](../request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md)·[边界上报](2026-08-03_reading_ruler_r1_batchBC_glm_boundary_report.md)
- 范围：S-2（EffectiveRunPolicy 冻结）+ S-3（dimensioned applicability fail-closed）+ 验收锁 L-10..L-23
- 裁定口径：**拍板 1=甲**（不写 sm24 真值；L-20/21/22/23 全用自造 fixture；⛔ 不碰 `gt/**` 与 `testdata_prompt.json`）·**拍板 2=照走 §3 + 两条追加约束**·**拍板 3=照走 §4**（G4 披露偏离、G8 具名常量）

> ⚠️ 本文件为**骨架/进行中**。随施工推进逐节填充；骨架里的暂定结论不得当最终结论汇报。

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

## 2. 改动清单（逐文件，施工中填充）

（待填充）

---

## 3. neuter 自查表（每条锁摘掉即红、零连带）

（待填充）

---

## 4. 全仓测试结果

（待填充；基线 2055 passed + 10 xfailed 零红）

---

## 5. 已知缺口的诚实登记

（待填充）
