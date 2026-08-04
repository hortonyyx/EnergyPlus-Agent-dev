# 施工简报 · sm21 e2e-break r2（承接 4a11097）

- **日期**：2026-08-05
- **施工席**：GLM-5.2（承接 `4a11097` 同一席位）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-04_sm21_e2e_break_dispatch_r2.md`
- **基线**：工作树 @ `4a11097` = **2164 / 10 / 0**
- **收工三数字**：**2170 passed / 10 xfailed / 0 failed**（净增 6 锁，零回归）

---

## 0. 一句话

三条都按派工单施工并各自上了「摘掉即红」的真锁（自跑 neuter 逐条验过，零连带）。
**但 F-2 有一条派工单没列、却让「隔离产物走得进 correction」这个目标达不到的兄弟墙**——
我在第 5 节如实披露，没有自行扩范围去改，留 orchestrator 裁定。

---

## 1. 逐条改了什么

### F-3（最重）· correction 接受未 finalize 的草稿

**F-3a（根因）** `scripts/tool_scripts/run_stage.py` `_draw_correction`
把早退判据从「有没有 FAIL」改成「按档位阻不阻断」：

```python
# 旧：if any(result.status == CheckStatus.FAIL for result in pre_core_debt.results):
# 新：
if pre_core_debt.blocking():
    return geom, pre_core_debt
```

`evidence_debt_coverage` 在 `exploratory` 下是 advisory（`FLAG`），旧判据用 `any(FAIL)`
把这条 advisory 也算进早退 ⇒ 返回**原始 geom**（不是 `FinalizeResult`）⇒ StageRunner
把它按 `base_v2` accept，但产物 `schema_version="3"` ⇒ 两段后 `load_verified_accepted_correction`
fail-closed。新判据只在**阻断**时早退；advisory 则继续走到 `finalize_correction_draw`，
最终 `check_correction(..., evidence_debt=...)` 会**再评一次** debt——所以 advisory 既没丢
（记进最终报告）、也没记两遍（`pre_core_debt` 被丢弃）。

**F-3b（写入点锁）** `src/agent/execution/stage_runner.py` `StageRunner.record`
在 `artifact_contract` 决策的 `else: base_v2` 分支里，对 `stage=="1_correction"` 加：

```python
if str(getattr(output_obj, "schema_version", "") or "") == "3":
    raise ValueError("an unfinalized v3 correction draft ... may not be accepted "
                     "under a 'base_v2' record — feature-state sidecar is mandatory for v3 (F-3b)")
```

不变量原本只长在**两段之后的读取端**（`output_coordinates.py:456`），现在在**写入端**也 fail-closed。

### F-2 · 隔离 merge 不搬 reading_summary.md

**F-2a** `src/agent/execution/isolation.py` `merge_isolated_output`：在写完 `output.json` 后，
把 staging `out/reading_summary.md` **搬进 `<run>/0_reading/reading_summary.md`**（correction 读它的位置），
并把它的 hash 记进**审计 isolation provenance**（`reading_summary_sha256`）。
`reading_isolated_v2` 契约只许 `output/checks/isolation_provenance` 三个 manifest artifact 键
（多一个会被 `_CONTRACT_ALLOWED_KEYS` 拒），所以 summary **不进 manifest artifact_hashes**，
只进被 `isolation_provenance` 哈希绑住的 provenance（与 output.json 同等可审计）。

**F-2b** 派工单建议命名失败位置在「reading gate① **或** correction 入口」。我取**correction 入口**
（`src/agent/pipeline.py` `_build_correction_messages`）：把裸 `_read(vector_dir/"reading_summary.md")`
换成命名 `FileNotFoundError`（指明 kickoff 契约 + 哪个段需要它）。
**理由**：merge 硬要求 summary 会让 8 个既有 merge 测试（都不写 summary）整片红，而派工单
明确允许 correction 入口这个位置。merge 侧改成 **copy-if-present**——summary 在则搬+记账，
不在则 provenance 记显式 `None`（可审计、不藏），命名失败由 correction 入口兜。

### MAJOR-1 · SCORER_SCHEMA 没 bump

`scripts/tool_scripts/run_stage.py`：`SCORER_SCHEMA = "8"` → **`"9"`**。
这是 legacy（reading+correction）sidecar 的缓存键。`_load_valid_score_sidecar` 已比对该常量，
bump 即让所有 v8 sidecar 失效重算。**没动 typed 侧** `src/agent/judge/score_schema.SCORER_SCHEMA`
（仍是 `"8"`，是另一把独立常量）——契合「别牵动 typed v3 路径」。
顺手把 `test_c2_b4b_contract.py` 里那行旧断言（两常量都 `=="8"`）改写成钉死新值
（legacy `"9"` / typed `"8"`）并更名，记录这是 MAJOR-1 故意引入的分歧。

---

## 2. 新锁（6 条，全部「摘掉即红」）

文件 `tests/test_e2e_break_r2_locks.py`，载荷均用真实量级（committed sm21 真 gt / 真产物 /
真 element_local evidence_debt），⛔ 无退化 fixture。

| 锁 | 分格 / 载荷 | neuter 摘掉后红了哪条 |
|---|---|---|
| `test_f3a_debt_early_exit_two_cell_profile_matrix` | **两格**：同一条 element_local debt · exploratory(advisory)⇒finalize 跑完且返回 `FinalizeResult` · regression(同条变阻断)⇒早退返回原始 geom、finalize 不跑 | 探索格：`spy_exp == []`（finalize 没跑）✅ |
| `test_f3b_stage_runner_rejects_v3_draft_but_allows_v2` | **两格**：v3 草稿+base_v2 拒 · v2 草稿+base_v2 放行(legacy) | v3 格：`DID NOT RAISE ValueError` ✅ |
| `test_f2a_merge_carries_reading_summary_to_stage_root_with_hash` | 真 clean-room build + 真 6 视图聚合 + 真 summary | stage 根 summary 文件不存在 ✅ |
| `test_f2b_merge_without_summary_succeeds_and_records_null_hash` | summary 缺席 ⇒ 不发明文件、provenance 记 `None` | （此锁守 copy-if-present 语义，neutering F-2a 时一并覆盖） |
| `test_f2b_correction_entry_names_missing_summary` | correction 入口缺 summary ⇒ 命名 `FileNotFoundError`（match `"1_correction requires"`，裸 OS 错配不上） | 裸 `_read` 的 OS 错信息不含 `"1_correction requires"` ✅ |
| `test_major1_stale_schema_sidecar_recomputed_current_reused` | **两格**：真形 stale(sidecar schema `"8"`)⇒重算(scorer 被调、结果 schema `"9"`) · current(`"9"`)⇒复用(scorer 不调) | `sidecar["scorer_schema"] == rs.SCORER_SCHEMA == "9"` 及 c2_b4b 字面锁 ✅ |

**判据类四格/两格实测**（吸取 08-04「neuter 变红只证明实现被调用」教训）：
- F-3a 是档位相关判据 ⇒ 两格（exploratory advisory vs regression 阻断），用**同一条** FAIL
  证明 `pre_core_debt.blocking()` 在两档下分出两种结局；
- F-3b 两格（v3 拒 / v2 放）证明锁是窄的、不误伤 legacy；
- MAJOR-1 两格（stale 重算 / current 复用）证明缓存键有分辨力，不是「scorer 被接上」。

---

## 3. neuter 原始输出（自跑，全部在 `/tmp/neuter_r2` clone，工作树零改动）

clone 基线 6 锁全绿。逐条 neuter（每条 run 完用 pristine 文件复原）：

```
F-3a  (blocking() → any(FAIL))        : exploratory 格红  AssertionError: assert [] == [True]   （finalize 没跑）
F-3b  (删 v3+base_v2 拒)               : v3 格红          Failed: DID NOT RAISE <class 'ValueError'>
F-2a  (删 copy-if-present)             : 红               AssertionError: assert False  (stage_summary.is_file())
F-2b  (correction 入口回退裸 _read)     : 红               Actual message: "[Errno 2] No such file..."（match "1_correction requires" 失败）
MAJOR-1 (SCORER_SCHEMA 9→8)            : 红 2 条          AssertionError: assert '8' == '9'  （test_major1 + test_c2_b4b 字面锁）
全部复原后 clone 6 锁重新全绿。
```

每条 neuter 都恰好红目标锁、零连带。MAJOR-1 红两条是预期的（schema bump 同时绑了重算锁和字面锁）。

---

## 4. 全仓三数字

```
python -m pytest -q -n auto
2170 passed, 10 xfailed, 209 warnings in 297.33s (0:04:57)
```

**2170 / 10 / 0**。基线 2164 + 6 新锁 = 2170，xfail 不变，**零回归**（只增不减）。

---

## 5. ⚠️ 诚实披露

### 5.1 【最重要】F-2 单做 summary 不够——还有一堵派工单没列的兄弟墙（建议立项 F-2c）

派工单 F-2 的目标是「让走 clean-room staging 的识图产物走得进 correction」。我**实测**发现：
**一条真隔离 run（聚合 `{"views":{...}}` 落 `attempts/NNN/output.json`、stage 根无 `*_view.json`）
会在读到 summary 之前就死在 `verify_reading_stage_root_against_accepted_attempt`**。

- 位置：`scripts/tool_scripts/run_stage.py:312`（`_draw_correction` 里，**先于** `run_correction` 读 summary）。
- 该校验（`src/agent/correction/window_sources.py:498`）把 **stage 根 `*_view.json` 的扁平聚合哈希**
  与 accepted attempt 的 `output_hash` 比对。隔离 run stage 根**没有** `*_view.json`（merge 只写 attempt 目录，
  O-1 已把渲染改成读 attempt 目录）；且隔离 accepted 输出是**信封形** `{"views":{...}}`，与扁平聚合**形状都对不上**。
- 我在 /tmp 实跑复现：构造隔离形 accepted reading（无 stage 根视图）⇒ 该校验直接抛
  `WindowResolverInputError("source_identity_invalid", reason="accepted_attempt_mismatch")`。

⇒ **F-2a（搬 summary）+ F-2b（命名失败）本身正确且必要，但不足以打通隔离→correction。**
这堵墙（姑且叫 **F-2c**）是设计决策：校验器该如何对待隔离形 accepted 输出 + stage 根缺视图？
我**没有自行扩范围去改它**（动它会牵动 O-1 渲染契约 / 隔离 accepted 的权威来源口径，属 orchestrator 裁定的事）。
今晚的 smoke_downstream 没撞到它，是因为 smoke 复用了 **07-07 扁平**识图（stage 根有视图），
校验过、直接死在 F-3。

### 5.2 F-2b 位置选择

取 correction 入口（非 merge），原因见 §1：merge 硬要求会让 8 个既有 merge 测试整片红，
派工单又明确允许 correction 入口。代价：summary 缺席的命名失败晚到 correction 才爆（而非 merge 早爆）；
但 §5.1 的校验墙更早，所以对真隔离 run 的体感无差别。

### 5.3 F-3a 语义判断（派工单 §6 要我有异议就停）

**无异议，照单施工。** advisory debt 放行不会漏真问题：advisory 仍记进最终 `check_correction` 报告（不丢），
finalize+accept 产出合法 v3 件（远好于现在的崩）。早退改 `.blocking()` 也与原注释
「a blocked draw is still filed as an attempt」的字面意图一致——旧代码用 `any(FAIL)` 是 bug。

### 5.4 F-3 测试高度

F-3a 的 `_draw_correction` 测试 stub 了 LLM（`run_correction`）、finalize 算法、以及**与 F-3a 无关的**
draw_quality 早退 / reading-root 校验 / `check_correction`，但**保留** `check_evidence_debt_coverage`
+ 早退那一行 + 路由为**真**，载荷是 committed 真 geom + 真 element_local debt——精确隔离 F-3a 改的那个决策。
F-3b 的 v3 载荷用最小真形 v3 payload（`model_validate` 过，与 b5 legacy 套件同形）：
唯一 committed 真 v3 correction 件是未跟踪的 smoke_downstream run，引用它会在干净 clone 上 fail-open。

### 5.5 没做到 / 绕过的

- **没跑端到端真隔离 flow** 验证「隔离→correction 真通」（因 §5.1 的墙，本来就通不了；且跑真隔离要冷启子代理，
  超本单范围）。F-2 的端到端验证须 F-2c 落地后才有意义。
- MAJOR-1 只 bump 了 legacy 常量；**没去重判今晚 e1/smoke 那两份产物的 sidecar**（它们是未跟踪件，
  派工单禁止动；bump 后下次判卷自然失效重算）。

---

## 6. 边界

⛔ 未碰识图侧算法 / 未碰 gt / 未碰 typed v3 判卷语义 / 未动容差。
`git diff --name-only` = 5 个源/测试文件 + 1 新测试文件 + 本简报。提交**只 add 这 7 个**，
⛔ 未 `git add -A`：orchestrator 的未跟踪产物（`sm25-L_anchor/`、`run_2026-08-04_*`、两份 request/verdict）
一律留在外。
