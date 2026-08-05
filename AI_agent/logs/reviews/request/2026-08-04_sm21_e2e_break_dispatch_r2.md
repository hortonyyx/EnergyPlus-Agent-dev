# 派工单 r2 · sm21 端到端烟测撞出的三条真缺陷

- **日期**：2026-08-04 夜 → 08-05 凌晨
- **派工方**：orchestrator（Opus 5）
- **施工席**：GLM-5.2（承接上一单 `4a11097` 的同一席位）
- **审阅席**：Claude 侧子代理（已就位，本单完工后再审一轮）
- **前置**：上一单 `4a11097` 已过 Claude 侧对抗审 = **APPROVE-WITH-CHANGES**
  （裁决书 `AI_agent/logs/reviews/verdict/2026-08-04_sm21_legacy_scoring_envelope_review_claude.md`）。
  本单第 3 项就是那份裁决里的**唯一 MAJOR**。
- **基线**：工作树 @ `4a11097` 实测 **2164 passed / 10 xfailed / 0 failed**（审阅席独立复算一致）。

---

## 背景（为什么突然冒出三条）

orchestrator 今晚拿**已知满分**的 07-07 sm21 识图产物做了一次**下游机械烟测**
（run `run_2026-08-04_smoke_downstream`，`--judge off --with-ep`，只为回答「除识图外这条链今天还通不通」）。
结果：**通不了**，而且死在两个不同的地方。这三条都不是识图质量问题，识图再好也照撞。

---

## 1. 【F-3 · 最重】correction 只要有一条「FAIL 但当前档位不阻断」的检查，就会把**未 finalize 的草稿**当成品接受，两段之后炸

**现象（实跑原样）**：
```
[1_correction] deterministic_pass  (attempts=1, accepted=1)
  → gate① passed — no enabled judge for this stage → advance
  gate①: {'passed': True, 'block': 0, 'flag': 1}
    ⚠️  correction.evidence_debt_coverage: 6 view/global evidence debt item(s) were not mentioned in correction audit
...
ValueError: a v3 accepted correction may not travel under a 'base_v2' record
        — feature-state sidecar is mandatory for v3
  （src/agent/output_coordinates.py:457，由 2_modelling 的 _load_snapped_with_proof 触发）
```

**根因（orchestrator 已定位到行）**：`scripts/tool_scripts/run_stage.py:331`

```python
pre_core_debt = check_evidence_debt_coverage(geom, evidence_debt, ...)
if any(result.status == CheckStatus.FAIL for result in pre_core_debt.results):
    return geom, pre_core_debt          # ← 返回的是**原始 geom**，不是 FinalizeResult
```

判据用的是「**有没有 FAIL**」，而不是「**在当前 run_profile 下阻不阻断**」。
`evidence_debt_coverage` 在 `exploratory`（dev 默认档）下是**advisory**：`block=0, flag=1`。
于是：
- `report.blocking()` 为空 ⇒ stage_runner 判 `check_passed=True` ⇒ **该 attempt 被 accept**；
- 但返回对象不是 `FinalizeResult` ⇒ `stage_runner.py:532` 落到 `artifact_contract="base_v2"`；
- 产物本身 `schema_version="3"` ⇒ 下一段的 `load_verified_accepted_correction` **fail-closed** 报上面那句。

⇒ **exploratory 档跑 flow，correction 一旦有 advisory FAIL，端到端必断在 2_modelling。**

**要修两处（都要，缺一不可）**：

- **F-3a（根因）**：`run_stage.py:331` 的早退判据改成**按档位判阻断**（`pre_core_debt.blocking()` 非空才早退）。
  不阻断时必须继续走到 `finalize_correction_draw`，让 accept 的是 `FinalizeResult`。
  ⚠️ 注意 `check_correction(..., evidence_debt=evidence_debt)` 内部还会再评一次 debt——
  **别把同一条 FAIL 记两遍**，也**别因此把它从最终报告里弄丢**。
- **F-3b（该有的锁在写入点缺位）**：`stage_runner` 接受 `1_correction` 记录时，
  **`schema_version=="3"` 且 `artifact_contract=="base_v2"` 必须当场 fail-closed**，
  错误信息说清「未 finalize 的草稿不得被 accept」。
  现在这条不变量只长在**两段之后的读取端**，属本项目反复犯的「门是真的、但锁装错了地方」——
  错误在离案发现场两站地的地方爆，且爆的是一句看不懂的话。

## 2. 【F-2】硬隔离 merge 不搬 `reading_summary.md` ⇒ 隔离产物**永远走不进 correction**

- 读图器**按产品契约必须写** `out/reading_summary.md`（`kickoff_prompt.md` 明写），今晚两次抽签都写了；
- `merge_isolated_output`（`src/agent/execution/isolation.py`）**只搬 `output.json`**，不搬 summary；
- `src/agent/pipeline.py:300 _build_correction_messages` 里 `summary = _read(vector_dir / "reading_summary.md")`
  是**硬依赖**，缺文件直接 `FileNotFoundError`（`pipeline.py:105` 裸 `read_text`）。
- 对照：所有**前隔离时代**的 run（如 `run_2026-07-07_haiku_cv_retest/0_reading/`）都有这个文件。

⇒ **任何走 clean-room staging 的识图产物，都跨不过 0_reading → 1_correction 这一步。**
（今晚 e1 run 没暴露它，是因为 gate① 先把识图挡住了；一旦识图合格，立刻撞。）

**要修**：
- **F-2a**：merge 把 `out/reading_summary.md` 一并搬进 `<run>/0_reading/`（进产物哈希/provenance 记录，
  与 `output.json` 同等对待；⛔ 别只 copy 不记账）。
- **F-2b**：缺 summary 时给**命名的、可定位的**失败（建议在 reading 侧 gate① 或 correction 入口做前置检查），
  ⛔ 不要留裸 `FileNotFoundError` 冒到用户面前。

## 3. 【MAJOR-1 · 来自 Claude 侧对抗审】`SCORER_SCHEMA` 没随判分语义 bump ⇒ 旧 sidecar 短路，上一单的修复在**触发它的那份产物上原样复现**

审阅席活体复现（我复核过其方法，成立）：用修好的代码重判今晚那份 sm21 产物，
**四条 headline 仍是 pass**；删掉旧的 `score_vs_gt.json` sidecar 才变 severe。
`_grade_attempt_artifacts` 命中旧 sidecar 就整个跳过重算，而 `SCORER_SCHEMA` 常量没动 ⇒ 命中。

**要修**：bump `SCORER_SCHEMA`（该常量 `43b79e3` 引入正是为此），并**补一条锁**：
sidecar schema 落后 ⇒ 必须重算，不得复用。**注意别牵动 typed v3 路径**。

---

## 4. 锁的要求（与上一单相同，逐条硬性）

1. 每条修法配「摘掉即红」的锁；⛔ 探针不算锁。
2. ⭐ **neuter 变红只证明实现被调用，不证明判据有分辨力**：
   - F-3a 是**档位相关**判据 ⇒ 必须**两格实测**：`exploratory`（advisory FAIL）⇒ 走完 finalize 且 accept 的是
     `FinalizeResult`；`regression`（同一条 FAIL 变阻断）⇒ 照旧早退、记 attempt、不 finalize。
   - F-3b ⇒ 构造「v3 产物 + base_v2 记录」必须被拒。
   - MAJOR-1 ⇒ 旧 schema sidecar 在场时必须重算（用**真实**旧 sidecar 形状，⛔ 不许空文件糊弄）。
3. 载荷用**真实量级**（sm21 真 gt / 真产物），⛔ 退化 fixture 不算。
4. **自己跑 neuter**，把红了哪几条、有没有连带，原样写进简报。
5. 全仓 `python -m pytest -q -n auto`，报三个数字；基线 **2164 / 10 / 0**，只许增不许减。

## 5. 交付物

1. 代码 + 新测试；`git commit`（`08.05_<英文标签>`），**⛔ 不 push**；
2. 简报落 `AI_agent/logs/reviews/execution/2026-08-05_sm21_e2e_break_glm_r2.md`：
   逐条改了什么 + neuter 原始输出 + 分格实测 + 三数字 + **诚实披露**（没做到的/绕过的/不确定的）。
3. ⚠️ **提交前先看工作树**：今晚仓里有 orchestrator 的未跟踪产物
   （`case_tests/e2e_tests/sm25-L_anchor/`、`case_tests/e2e_tests/sm21_anchor/run_2026-08-04_*`、
   `case_tests/test_baseline/gt_sources/sm25-L_anchor/`）——**⛔ 一律不要 `git add -A`**，只 add 你自己改的文件。

## 6. 边界

- ⛔ 不碰识图侧算法、不碰 gt、不碰 typed v3 判卷语义、不动容差。
- **有异议就停下上报**（上一单你照单施工无异议；本单 F-3a 涉及「advisory 还该不该早退」的语义判断，
  如果你认为按档位放行会漏掉真问题，**写清理由停下**，别硬改）。
