# 执行日志 · F-2c + F-7 返工 r1（GLM 席位）—— sol 对抗审四条 MAJOR

- **日期**：2026-08-05
- **席位**：GLM-5.2，主工作树 `/workspaces/EnergyPlus-Agent-dev`（分支 `6.15_ValidationArchM0toM4`）
- **上游**：[sol 对抗审 REWORK](../verdict/2026-08-05_f2c_f7_crossreview_sol.md)（1 BLOCKER / 4 MAJOR）
- **派工单**：[../request/2026-08-05_f2c_f7_rework_r1_dispatch_glm.md](../request/2026-08-05_f2c_f7_rework_r1_dispatch_glm.md)
- **基线 HEAD**：`ca5e26c`（2212 绿 / 10 xfail / 0 红）
- **状态**：✅ **DONE —— 四条 MAJOR 全修并落库，BLOCKER 按派工单 §5 不在本单范围（随 F-9 解）**

| 条目 | 判定 | 提交 |
|---|---|---|
| §1 逐点审计 category 归类 | ✅ 2 处归错已修 + 2 锁 | `cac457a` |
| §2 catalog 静默回退 → v3 前置条件 | ✅ 修 + 4 锁 | `49e5f42` |
| §3 parse.py 死标注 | ✅ 选 (b)：诚实注释 + 1 锁 | `49e5f42` |
| §4 MAJOR ④ 真实前态实测 | ✅ **实测证实 sol 成立**，已修 + 1 锁 | `5797653` |

**全仓尾巴三数（主工作树，`-n auto` 不加 `-m`）**：**2220 passed / 10 xfailed / 0 failed**（318 s）。基线 2212 + 本批新增 8 锁 = 2220，零回归。

---

## 派工单与代码实情的一处出入（已按 §0 纪律处理，未硬做）

派工单 §3 称 `parse_correction_draw`「只被 `_schema_only_correction_validator`（pipeline.py:587）与 `_make_correction_validator`（:611）调用」。
**实情**：还有两处调用——`pipeline.py:697`（`run_correction` 内，包成 `RuntimeError`）与 `finalize.py:94`（`finalize_correction_draw` 内）。
**但这不改变 §3 结论**：`pipeline.py:697` 同样把异常包成 `RuntimeError`（不到分类路由）；`finalize.py:94` 仅当传入 **dict** 时才调 `parse_correction_draw`，而生产 live 路径（`_draw_correction`:416、`run_pipeline`:1081）都传**已解析的 geom 对象**，走 `ensure_corrected_geometry` 分支，不调它。⇒ 两处额外调用点同样不到达分类路由，**「死标注」结论成立**，只是 orchestrator 的枚举不全。已在 §3 提交信息与下方如实登记。

---

## §1 —— 逐点审计全部 `category` 归类（window_sources 50 + finalize 2 + parse 2 = 54）

**判据**（派工单 §1）：触发条件由「模型这次抽签写的内容（`producer.*`）」决定 ⇒ `model_draw_error`（归档重抽）；由「上游产物/manifest/哈希/接线」决定 ⇒ `input_integrity_error`（硬崩）。复合条件拆开各归各的。

### 审计表

判据列：**M**=读模型产物（producer.*）/ **U**=读上游（manifest/readings/hash）/ **P**=读冻结的持久产物（re-auth，无重抽可能，两类都硬崩）/ **W**=读调用方接线。

#### window_sources.py（50 处）

| 行 | 函数 | 触发条件读 | 原 category | 判定 | 改 |
|---|---|---|---|---|---|
| 297 | `_parse_manifest` | U（manifest 字节） | input_integrity | ✓ | — |
| 302, 306 | `_interval` | U（reading 几何） | input_integrity | ✓ | — |
| 314 | `_window_strokes` | U（reading 解析） | input_integrity | ✓ | — |
| 341 | `_catalog` | U（reading 输入 vs manifest） | input_integrity | ✓ | — |
| 355, 357, 359 | `_validate_catalog` | U（catalog 去重，reading 派生） | input_integrity | ✓ | — |
| 370 | `verify_window_resolver_inputs` | P（持久产物 hash） | input_integrity | ✓ | — |
| 376, 379 | 同上 | P（持久 link/input 一致） | input_integrity | ✓ | — |
| 385, 387, 389 | 同上 | P（持久 claim 校验；live 等价 817/824/828 归 model_draw） | input_integrity | ✓ | — |
| 402, 407, 416, 427 | `verify_..._against_raw_artifacts` | P/U（持久 vs raw） | input_integrity | ✓ | — |
| 546, 556 | `derive_manifest_direction_facts` | U（manifest/reading 方向） | input_integrity | ✓ | — |
| 594, 603 | `build_verified_window_inputs_from_run` | U（盘上 manifest/reading） | input_integrity | ✓ | — |
| 658, 666, 686, 690 | `verify_reading_stage_root_against_accepted_attempt` | U/hash（accepted 绑定） | input_integrity | ✓ | — |
| 702, 707, 711, 715, 720, 723 | `_check_direction_facts` | U（manifest/reading 方向） | input_integrity | ✓ | — |
| 734, 737 | `_producer_preflight` | M（producer 预填） | model_draw | ✓ | — |
| 776/779, 784/787, 792/795 | `_translate_observation_reference` | M（模型引用串） | model_draw | ✓ | — |
| 807 | `_claim_links` existence | M | model_draw | ✓ | — |
| 815 | `_claim_links` source None | M（模型引用） | model_draw | ✓ | — |
| 817 | `_claim_links` claim undeclared | M | model_draw | ✓ | — |
| 820/822 | `_claim_links` entry not found | U（catalog/manifest，defensive） | input_integrity | ✓ | — |
| 824 | `_claim_links` claim not observable | M | model_draw | ✓ | — |
| 828 | `_claim_links` claim not permitted | M | model_draw | ✓ | — |
| 831 | `_claim_links` duplicate existence | M | model_draw | ✓ | — |
| **841/842** | `_check_floor_order` 首检 **复合 `A or B`** | A=U（manifest 楼层 ref 非连续）/ B=M（`producer.floors` 层数） | input_integrity（整条） | **A✓ / B✗** | **拆分**：A 留 `manifest_floor_ref_non_contiguous`/input_integrity；B 新码 `producer_floor_count_mismatch`/model_draw |
| 850 | `_check_floor_order` floor mismatch | M | model_draw | ✓ | — |
| 856/857 | `_check_floor_order` elevation floor mismatch | M | model_draw | ✓ | — |
| **858/859** | `_check_floor_order` 防御性 set 比较 | M（两侧都读 `producer.floors`） | input_integrity | **✗** | **改** → model_draw（dead/防御性，但按判据诚实归类） |
| 908, 928 | `verify_window_resolver_inputs_artifact` | P（持久 replay） | input_integrity | ✓ | — |

#### finalize.py（2 处）

| 行 | 触发条件读 | 原 category | 判定 | 改 |
|---|---|---|---|---|
| 107 | W（`producer_bytes` ≠ verified_inputs；注释明说「caller wiring defect, not model draw」） | input_integrity | ✓ | — |
| 112 | W（v3 缺 verified_window_inputs） | input_integrity | ✓ | — |

#### parse.py（2 处，另见 §3）

| 行 | 触发条件读 | 原 category | 判定 | 处理 |
|---|---|---|---|---|
| 87, 91 | M（producer 预填） | model_draw | 标注语义对（确为模型错），**但永远到不了外层分类**（死标注） | §3：诚实注释 + 锁钉内层重试路径 |

### §1 关键发现

- **842 复合条件**（派工单反例，已核实）：`refs != list(range(1,len(refs)+1)) or len(refs) != len(producer.floors)`。其中 **A** 纯读 manifest（且 ViewManifest 自身 validator view_manifest.py:505 已强制 plan floor_ref 1..N 连续 ⇒ A 实际是 dead 防御性重检，归类仍诚实）；**B** 读 `producer.floors`（模型产物）⇒ 必须是 model_draw。原整条归 input_integrity ⇒ 模型画错楼层数硬崩不重抽。
- **859**：两侧 set 都从 `producer.floors` 派生，按判据应 model_draw（dead/防御性，重归类无行为影响、无测试覆盖）。
- **re-auth 路径**（`verify_window_resolver_inputs*`、`verify_window_resolver_inputs_artifact`）的 claim 校验（385/387/389 等）归 input_integrity **正确**：这些跑在冻结的持久产物上（re-auth），无重抽可能，两类都硬崩；live 路径同条件由 `_claim_links`（817/824/828）以 model_draw 覆盖且可达分类路由。判据中的「模型这次抽签」对冻结产物不适用。
- **结论**：54 处中仅 **2 处归错**（842-B、859），均在 live 路径。未「统一改成某一类」、未靠消息串判类。

### §1 锁（test_f7_observation_reference_translation.py）

1. `test_f7_category_producer_floor_count_mismatch_is_model_draw_error` —— helper 级：2 层 producer vs 1 层 manifest ⇒ `producer_floor_count_mismatch` / model_draw。
2. `test_f7_floor_count_mismatch_archived_as_failed_attempt_and_resampled` —— **真实入口**（`run_one_stage` 随机循环）：错楼层数 draw ⇒ 归档为失败 attempt + 盲重抽（非硬崩），坏 attempt 的 check 记录含精确码。

### §1 双向 neuter（原样）

neuter：把新 `producer_floor_count_mismatch` 的 category 临时改回 `input_integrity_error`。
```
FAILED tests/test_f7_observation_reference_translation.py::test_f7_category_producer_floor_count_mismatch_is_model_draw_error
FAILED tests/test_f7_observation_reference_translation.py::test_f7_floor_count_mismatch_archived_as_failed_attempt_and_resampled
2 failed in 10.10s
```
还原后：`2 passed in 9.27s`。

---

## §2 —— catalog 静默回退升为 v3 前置条件

`build_observation_reference_catalog_from_run`（window_sources.py:493）加 `required_for_v3: bool = False`。默认 False ⇒ 行为不变（仍返回 None，保留 advisory 契约与既有测试 test_f7:232）。两个 v3 调用方（`run_stage._draw_correction`:331、`run_pipeline`:1031）传 `required_for_v3=True` ⇒ 清单不可导出时抛 `observation_reference_catalog_unavailable`（input_integrity_error），错误 context 指名 `missing_artifact`（缺失文件路径）+ `artifact`（view_manifest/reading）+ `produced_by_stage="0_reading"`。catalog 调用在 run_correction 之前、无 try/except ⇒ 抛出即硬崩（缺上游 reading 文件，重抽无益）。

### §2 锁（4 格）

1. `test_f7_v3_catalog_missing_manifest_raises_naming_path` —— 缺 manifest ⇒ 抛，含路径 + produced_by_stage。
2. `test_f7_v3_catalog_missing_reading_raises_naming_path` —— manifest 齐但缺某张 reading ⇒ 抛，含 `south.json` 路径 + expected_output_id。
3. `test_f7_v3_catalog_complete_injects_normally` —— 齐全 ⇒ 正常返回（== advisory 文本）。
4. `test_f7_v3_missing_catalog_hard_fails_at_draw_correction_entry` —— **真实入口**：v3 policy + 无 manifest ⇒ `_draw_correction` 入口即抛。

### §2 双向 neuter

neuter：manifest 缺失分支临时改成静默返回 None。
```
FAILED tests/test_f7_observation_reference_translation.py::test_f7_v3_catalog_missing_manifest_raises_naming_path   # 缺 manifest 格
（缺 reading 格 / 齐全格未受 manifest neuter 影响，同 _unavailable 机制结构等价 ⇒ 仍绿）
2 failed, 2 passed
```
还原后：全 22 passed。

---

## §3 —— parse.py 两处死标注（选 (b)）

**判断**：选 **(b)**。理由：
1. 两处 raise 不是死**代码**——它们触发内层盲重试（给模型 3 次机会别再预填），有用；死的只是 `category` 标注暗示的「会被外层分类」。
2. 选 (a)（让 WindowResolverInputError 穿透 validator）会改变内层重试语义、与 F-4（内层=schema/格式、外层=语义）冲突。
3. 同一预填条件已被 `_producer_preflight`（734/737，model_draw_error，可达分类）在 live 后置路径覆盖，分类覆盖不依赖这两处。

**改法**：raise 不动（仍是 `category="model_draw_error"`，类型必填且语义诚实——预填确为模型错），把误导性隐含「会被分类」改成**显式诚实注释**：说明实际走内层盲重试通道、包成 RuntimeError、外层 classifier 看不到；同条件被 `_producer_preflight` 后置覆盖。（据 neuter 实测微调：移除 raise 后 V3 schema 自身仍以 ValidationError「unknown facade_segment_id」拒掉预填 facade_segment_id，丢的是**稳定命名 code** 不是重试触发本身——注释如实写。）

### §3 锁

`test_f7_parse_prefilled_raises_in_inner_validator_not_outer_classifier` —— 钉住**实际路径**：`_draw_correction` 实际接的 `_schema_only_correction_validator` 对预填 payload 抛 WindowResolverInputError（内层重试触发器）。移除该 raise ⇒ validator 改抛 ValidationError ⇒ 锁红。

### §3 双向 neuter

neuter：注释掉 parse.py 两处 raise（改 `pass`）。
```
FAILED tests/test_f7_observation_reference_translation.py::test_f7_parse_prefilled_raises_in_inner_validator_not_outer_classifier
（暴露：移除后 ensure_corrected_geometry 抛 ValidationError "unknown facade_segment_id"，非 WindowResolverInputError）
2 failed, 2 passed
```
还原后：全 22 passed。

---

## §4 —— MAJOR ④ 真实前态实测：**证实 sol 成立**（非推翻）

sol 此条**无人实测**（沙箱坏、pytest 没跑起来）。派工单 §4 要求先构造真实前态实测再决定改法。**结论：sol 成立。**

### 实测证据（修法前，RED）

真实前态：`run_dir/0_reading` 已有一个陈旧多余 `stale_view.json`（上一轮留下）+ 正常隔离 merge。
```
test_f2c_rework_r1_stale_stage_root_mirrors_cleaned_before_accept
>   assert "stale_view.json" not in mirrors
E   AssertionError: assert 'stale_view.json' in ['1f_view.json', '2f_view.json',
    'East_view.json', 'North_view.json', 'South_view.json', 'West_view.json', ...]
1 failed
```
即：merge 的「只覆写 accepted views」循环**不清**陈旧文件 ⇒ 下一段 `verify_reading_stage_root_against_accepted_attempt` glob 全部 `*_view.json` 重建 `current`（含 stale 多余键）⇒ canonical hash ≠ accepted ⇒ `accepted_attempt_mismatch` 硬崩。这正是 sol 的「先接受、下一段再崩」，干净 tmp fixture 掩盖了它。

落盘次序（isolation.py 原状）：`save_run_manifest`（accepted 指针，:462）**先于** mirror 写循环（:476-479）⇒ 二者之间中断留「已接受但未 mirror」。sol 两点都坐实。

### 改法（isolation.py `merge_isolated_output`，accept 路径）

1. 写 mirror **前**先 `for stale in stage_dir.glob("*_view.json"): stale.unlink()`（保守范围：只删 `*_view.json`，在 `_merge_lock` 内；非 mirror 文件如 `reading_summary.md` 不动）⇒ stage root 收敛到恰好 accepted 集合。
2. **先写 mirrors 再 `save_run_manifest`**（指针最后）⇒ 中断留「未接受」（verify 在无 accepted 时 early-return），不留「已接受未 mirror」。

### §4 锁 + 双向 neuter

`test_f2c_rework_r1_stale_stage_root_mirrors_cleaned_before_accept`：陈旧文件在场 ⇒ merge 后恰好 accepted views、verify 通过。
neuter（删 stale 清理循环）：
```
>   assert "stale_view.json" not in mirrors
E   AssertionError: assert 'stale_view.json' in [...]
1 failed
```
还原后：F-2c 全套 8 passed（含既有 f2c1 清格/f2c2 反篡改/f2c3 flat 路径，零回归）。

> 排序改动（mirrors-before-pointer）是防御性增强，中断测试非确定、未单独上锁；行为锁（stale 清理）已 neuter 证实绑定，排序理由见代码注释。

---

## §5 BLOCKER —— 按派工单不在本单范围

sol BLOCKER（真实 sm21 `1_correction` accepted attempt 未产生）事实属实，但直接原因是下一道墙 **F-9**（`resolve_window_hosts` 拒收），非这两批实现错。F-9 只读调查已另派席位并行（独立 worktree `.claude/worktrees/f7-manual`，本席未进）。⇒ 本单 ⛔ 不碰 F-9、⛔ 不改口径绕过；BLOCKER 作为出口条件继续持有，随 F-9 一并解。

---

## 纪律遵守

- ⛔ 未碰 F-9（未进 `.claude/worktrees/f7-manual`）；⛔ 全程逐文件 `git add`，未 `git add -A`；⛔ 未 push。
- 全仓在主工作树跑（干净检出会因 F-8 红 5 条，与本单无关——未触发）。
- 派工单与实情一处出入（§3 调用点枚举）已停下如实登记，未硬做。
- 「做完一件存一件」：§1 / §2+§3 / §4 各自独立提交。
- ⭐ §0.2 新纪律（机制级 neuter ≠ 逐点审计）：§1 对 54 处**逐点**审计（非靠 F-7 三格 neuter 外推），仅 2 处归错——正是该纪律的实证。
