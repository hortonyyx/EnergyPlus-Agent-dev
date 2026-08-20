# 裁决 · 立面洞口载体方言层（GLM 审 GPT 施工）

- **日期**：2026-08-20 · **审阅席**：GLM `glm-5.3` · **施工席**：GPT `gpt-5.6-sol`
- **请求书**：`reviews/request/2026-08-20_tarch_elevation_carriers_crossreview_glm.md`
- **依据**：派工单 + 主控两次追加裁决（执行日志 §2）+ `git diff` + 本席实跑输出。
  ⛔ 施工席自述（执行日志 §3）未用作任何结论的依据，仅作对账靶。

## 裁决：**APPROVE**

零 BLOCKER、零 MAJOR。3 MINOR + 2 NIT，均不阻断本批合入，修否由主控定。

---

## 1. 我实跑了什么、看到什么（逐条对请求书 §二）

### §二#2 ⭐ 四条既有 must-red 诊断码逐个对账表

探针（`/tmp/glm_probe_mustred.py`，复刻 `test_door_structural_union_mutations_make_g3_red`
的四条变异：INSERT `B04` 平移，其余不动）：

| 变异 | G3 | `door_structure_invalid` | `entities_unconsumed` | `entity_double_consumed` | `door_block_drift` | 判定 |
|---|---|---|---|---|---|---|
| positive_gap (−100,0) | **False** | ×1，handles `[B03,B04]`，`module_union_strategy=same_band_strict_union` | 0 | 0 | 0 | 未被顶替 |
| positive_overlap (+100,0) | **False** | ×1 `[B03,B04]` | 0 | 0 | 0 | 未被顶替 |
| t_shape (+400,+1200) | **False** | ×1 `[B03,B04]` | 0 | 0 | 0 | 未被顶替 |
| different_z (0,+1000) | **False** | ×1 `[B03,B04]` | 0 | 0 | 0 | 未被顶替 |
| （green 基线，不扰动） | True | 0 | 0 | 0 | 0 | 14 records |

四条的红**仍由 union 门本身拥有**（诊断 context 明示 `same_band_strict_union` 平铺校验失败），
两个新门（对账/双重消费）零参与。另：该文件 42 条在自证前提轮全绿 ⇒ 断言
`any(diag.code == door_structure_invalid)` 本身已蕴含「未被顶替」（顶替 ⇒ 断言炸），
探针是眼见为实的独立复证。**最重的一条通过。**

### §二#1 每把锁的 neuter（本席自己做，未采信施工席）

自证前提：扰动前 `test_tarch_opening_carriers.py + test_tarch_elevation_must_red.py`
= **58 passed**（两文件全绿）。

| 锁 | 摘了什么（临时改生产码，已还原） | 红了什么 | 连带 | 自证前提 |
|---|---|---|---|---|
| L1 sm24 等价 | neuter-1：`_translate_legacy_opening_carrier_rules` 开头 `return []` | observable-must-red、needs-no-ignore、unknown-insert + must_red 文件 11F/10E + reproducibility 4 条（全部 sm24 立面直接消费者） | 平面侧 p0/p1/p2/gate_mutations **84 全绿** ⇒ 平面零牵连 | ✅ |
| ⚠️ L1 本体 | 同上 | **未红**——两侧同坏 ⇒ `[]==[]` 仍成立（见 F-1） | — | — |
| L2 撤块载体 | neuter-2：`_audit_opening_carrier_consumption` 开头 `return []` | `test_l2_...is_loud` 红 | must_red 42 条全绿 | ✅ |
| L3 删窗规则 | 同 neuter-2 | `test_l3_...14_unconsumed_handles` 红 | 同上 | ✅ |
| 未知门块响度 | 同 neuter-2 | `test_unknown_insert_...` 红（G3 对未知 INSERT 保持绿 = 正是静默缺陷） | 同上 | ✅ |
| L4 块指纹 | neuter-3：`fingerprint_bad = False`（先两次替换失败致语法红，第三次干净） | must_red `test_door_block_fingerprint_drift...` 红（G3 由红转绿）+ `test_block_definition_tamper...` 红（reason 从 `sha256_mismatch` 退为 `roles_drift`，断言炸） | 其余 56 条绿 | ✅ |
| L5 双重消费 | neuter-4：仅 `double_consumed = []`（比 neuter-2 窄，只摘这一段） | **只红 L5 一条**，57 绿 | 零 | ✅ |
| L6 同带间距 | neuter-5：`shares_cluster` 的 touching 分支 `return False` | **只红 L6 一条**，57 绿（100 mm 缝变两樘 ⇒ `merged==[]` 断言炸） | 零 | ✅ |

neuter-2 附带：`test_sm24_legacy_translation_needs_no_ignore_declarations` 摘门后仍绿
（它断言 `audit == []`，恒绿）——它锁的是「翻译不产 ignore + sm24 全消费」，不锁门存在性，
如实在表，不算缺陷。

### §二#3 翻译层 = 纯翻译，无第二条执行路

- **代码面**：`_translate_legacy_opening_carrier_rules` 全文只构造 `OpeningCarrierRuleV1`
  数据对象（窗：selector→`connected_line_group_rect`；门：`dialect_rules`→`block_entity_rect`
  + `same_band_strict_union`），不接触 msp、不做任何几何。
- **行为面**（进程内 monkeypatch，不改文件）：`_resolve_opening_carriers` 换成
  `lambda *a: ([], [])` ⇒ sm24 **`elevation_records = 0`、G3=False**
  （`entities_unconsumed` 报出 25 个句柄）。**旧请求再无任何路径产洞口几何。**
- 观察记录：摘 resolver 时 G9 仍绿——G9 preflight 的 pairing postcheck 受 `elevation_bound`
  守卫（`tarch_normalize.py:3069-3076`，E0–E4 已 BLOCK 时跳过次要诊断），G3 已红 ⇒ 属编排
  设计而非残留路径。判据「还能不能出洞口」= records 0 ⇒ 通过。

### §二#4 对账门真落成 G3 门失败

探针（复刻 unknown-insert 测试的 red 分支，独立于测试跑）：加一个
`UNDECLARED_DOOR_BLOCK` INSERT 到声明层 ⇒ ① `tarch_elevation_entities_unconsumed`
出现 ② **G3 `passed=False`** ③ 诊断 `handles=['CA3'], context={'view_id':'South_view'}`
逐句柄列出。registry 侧两新码均 `BLOCK + gates=("G3",)`（测试
`test_new_ledger_diagnostics_are_blocking_g3_owners`，本席实跑绿）。

### §二#5 门合并策略边界

- **`same_band_strict_union` 逐条等价**（读码逐字符比对 + L1 等价锁 + 58 全绿）：
  旧 touch 四不等式 ≡ `_rects_touch_or_intersect`；旧 same-z 两不等式 ≡ `_same_z_band`；
  旧合并条件（same-z OR touch）≡ 新 strategy 分支；簇扩张算法（pending 连通分量）与
  平铺校验（Σ面积==包围盒面积）同型；产物字段 min/max + sorted ⇒ 序无关。
- **恰等行为**：`_horizontal_gap < min_gap_native` 是**严格 `<`** ⇒ 间距恰等于声明值
  ⇒ 不并簇 ⇒ 两樘且绿。实跑 `modules(1300.0)`（gap=500 units=0.5 m=声明值）⇒ merged=2、
  诊断空。与施工席自述一致。
- **schema 侧**：窗禁声明 union（validator 拒）；门必须声明；`touching_rect_union`
  必须给 `module_union_min_gap_m`（⛔ 无默认值，字段默认 None）；`same_band_strict_union`
  禁给 min_gap；请求级还强制所有门规则同一 policy，`_merge_door_carriers` 二次校验。
- **sm25 实况独立清点**（本席 ezdxf 直数，防测试数字循环论证）：西 533×4+621×2 ·
  南 533×7 · 北 533×6+闭合LWPOLYLINE×2 · 东 LWPOLYLINE×12+621×2；块 533=8 LINE
  （外框 316/317/319/31B）、块 621=1 LWPOLYLINE+19 LINE+1 CIRCLE（外框
  35E/35F/360/361）⇒ **31 窗 3 门**，与派工单 §2.2 及测试 expected
  West(4,2)/South(7,0)/North(8,0)/East(12,1) 全部一致。主控 §7#1 的「可能数错」排除。

### §二#6 全仓回归对账（本席自跑）

- **干净树 `python -m pytest -n auto` = `2937 passed, 14 xfailed`，exit 0，零红零闪**
  （667 s）。与施工席报数、主控两次权威跑一致；xfail 14 与基线 `32ab707`（2917+14）持平未变。
- ⚠️ 披露一次本席操作事故：第一次全量与本席 neuter 循环并行跑，被中途改动污染
  （2926+11F），**该次作废**；11 条失败经查全部落在 sm24 依赖面（含 gt_promotion_path 4 条），
  2926+11=2937 恰与总数吻合。第二次为还原后干净跑（跑前 md5 快照、跑后校验一致）。

### §二#7 拓展性行数（机械判据）

新增一种画法（如「窗=一个 HATCH」）需要动：
1. `OpeningOutlineV1.kind` Literal 加值（声明面，预期内）；
2. `_OPENING_CARRIER_RESOLVERS`（`tarch_normalize.py:1797`）加一项（注册表，预期内）；
3. 新 resolver 函数（新增，预期内）；
4. **`tarch_converter_schema.py:575-579` `_entity_type_matches_outline` 里的 `expected`
   映射必须加一行 —— 已有代码 1 行。** 未注册的 kind 会被 schema 拒绝 / resolver 处
   `raise`（fail-loud，非静默）。机械数 = **1 行已有代码 > 0**，见 F-3。

---

## 2. Findings

### F-1 · MINOR · L1 等价锁缺正向锚（两侧同坏恒绿）
neuter-1（摘翻译层）下 `test_sm24_legacy_translation_preserves_records_and_normalized_dxf_bytes`
**不红**：monkeypatch 的 legacy 参考与新实现两侧同产 0 记录，`[]==[]` 仍相等。
该锁单独不证明「sm24 产物存在且 = 14 条」。锁网整体不漏（observable-must-red 的
green 分支断言 `len(records)==14` + G9 绿），但按「每把锁单独可观测」口径这是缺口。
建议（主控定）：L1 内补 `assert len(legacy.elevation_records) == 14`。

### F-2 · MINOR · 旧行为两处诊断面迁移（产物面零漂移，均有实跑支撑）
a) 门 union 平铺失败诊断的 handles 由「簇首一个 INSERT」扩为「全部 raw_handles」——
   信息更全，方向良性。
b) 旧：门层上块名不匹配规则的 INSERT ⇒ `door_block_drift`；新：不消费 ⇒
   `entities_unconsumed`。门仍 BLOCK 红（G3），仅诊断码迁移；对已签字 sm24
   （名字全匹配，§1 探针 green 基线零诊断）无影响。建议知悉即可，下游若按诊断码
   分诊需更新对照。

### F-3 · MINOR · 拓展性机械判据 = 已有代码 1 行（`tarch_converter_schema.py:575-579`）
派工单 §1#1 字面要求「0 处已有分支」。`expected` 是 kind→entity_type 的数据映射而非
逻辑分支，未加会导致 schema 拒绝（响亮失败），性质上更接近第二张注册表；但机械数 >0。
是否算违背 §1#1 由主控定性；若要归零，可把该映射挪成 resolver 注册表的属性。

### F-4 · NIT · 「窗规则声明 union 策略被拒」无专门负例
validator 有此逻辑（diff 可见），参数化负例只盖 layers 无序 / INSERT 字段误用 /
类型不匹配三种。补一条负例更完整。

### F-5 · NIT · `module_union_min_gap_m` ≤ 量化容差时的理论退化
接触判定自带 q 容差（`<= … + q`）；若声明间距换算后 ≤ q_native，「小于声明值必红」
的独立区间为空，退化为纯 touching 语义。现实声明（0.5 m ≫ q）不触发；可在 schema
加下界（如 ≥ 10×quant）防御，非本批义务。

### 附带核销（请求书/派工单的「可能错前提」逐项）
- 派工单 §7#1 sm25 计数：本席独立清点一致，**主控没数错**（本轮）。
- 派工单 §7#4 门合并误并风险：sm25 西 2 樘（9440 mm）在 touching+0.5 m 下正确分开
  （测试西 (4,2) 绿，本席实跑）。
- 派工单 §7#5 平面侧牵连：neuter-1 下平面侧 4 文件 84 全绿 + 干净全量绿 ⇒ 无牵连。
- 主控裁决 B（`module_union_min_gap_m` 领域参数化）：已按裁决落地——无默认值、
  请求签名绑定、恰等分开、小于必红（L6 neuter 独立证明）。

---

## 3. 边界自证

- 全部 neuter 已还原：两生产文件 md5 与审阅开始时快照一致
  （`935fd1f1…` / `94f12299…`），`git diff --stat` 仍为
  `126 ++ / 485 ++ 67 --`（544 insertions, 67 deletions），零 neuter 标记残留。
- 全程未 `git add` / `commit` / `push` / `stash`；未碰 `case_tests/test_baseline/gt/**`、
  `skills/**`；`AI_agent/` 下仅写本裁决文件；全部探针在 `/tmp`。
- ⚠️ 留痕：审阅中途 git status 出现未跟踪目录
  `AI_agent/logs/experiments/2026-08-20_sm25_elevation_carriers/`——**非本席创建**
  （本席未向 AI_agent/ 写过任何文件），疑为并行席位产物，未动，请主控知悉。

## 4. 结论

五把锁 + 未知门块响度锁全部实绑目标门且自证前提成立；四条既有 must-red 未被新诊断
顶替；翻译层确无第二条执行路；对账门真落 G3 BLOCK；sm25 31 窗 3 门独立复算成立；
全仓 2937+14 本席自跑复现。**APPROVE**，F-1/F-3 是否补由主控拍板。
