# F-10 `check_mep()` 签名漂移 — 执行日志（GLM 施工席）

- **日期**：2026-08-05
- **席位**：执行档 GLM-5.2（主工作树）
- **基点**：`6.15_ValidationArchM0toM4` @ `ce27167` ✅
  - `git log --oneline -1` = `ce27167 08.05_WrapUp_ProbeAB_F8_F9_F10_ReworkR1_LightGatesPassed`，分支一致。
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_f10_check_mep_signature_dispatch.md`

---

## ⚠️ 状态总览：STOP-AND-REPORT（验收 B 按字面不可达）

| 项 | 状态 | 说明 |
|---|---|---|
| 代码修法（mep.py） | ✅ 已落、已验 | 照抄 `check_assembly` 模式，零设计自由度 |
| A 真实入口锁 | ✅ 已落、已验 | 直调 `run_stage._draw_mep`，断言落在 `rep.run_profile` |
| **B 行为锁** | ⛔ **不可达（已停下上报）** | **不存在"exploratory 不阻断 / regression 阻断"的 mep check-id** |
| C 默认值锁 | ✅ 已落、已验 | 默认 `run_profile == "exploratory"` |
| D neuter 两向 | ✅ 已验（D1+D2） | 均 `git diff` 确认落地后再跑，红在断言不在空操作 |
| E 全仓 | ✅ 2223 绿 / 10 xfail / 0 红 | 基线 2220 → **净增 3 锁、零回归** |
| run_profile 流入锁（B 的诚实替身，待裁定） | ✅ 已落、已验 | 见 §6 |

**未 commit**：B 是派工单「缺一不可」的强制项。修法与 A/C/D/E/flow 全部就绪并取证，但 B 按字面做不到；在派工方裁定 B 如何收口前**不提交非合规交付物**（避免造一把假锁——本项目最贵的错误）。

---

## 1. 事实复核（派工单 §2，独立核实）

| 侧 | 位置 | 派工单陈述 | 实测 |
|---|---|---|---|
| 被调方 | `src/validator/checks/mep.py:95-104` | `check_mep` 形参无 `run_profile` | ✅ 属实（修前 `grep run_profile src/validator/checks/mep.py` = 0 命中） |
| 调用方 | `scripts/tool_scripts/run_stage.py:572-578` | 传 `run_profile=policy.run_profile` | ✅ 属实（`_draw_mep` 内 `check_mep(..., run_profile=policy.run_profile)`） |
| 唯一性 | `check_mep` 是 checks/ 里唯一不收 run_profile 的 | ✅ 属实（assembly/kernel/correction×2/reading/view_manifest×2 全收并原样传 CheckReport） |

`RunProfile` 定义于 `src/validator/checks/schema.py:42`（`Literal["exploratory","dev","golden","regression"]`）；`CheckReport.run_profile` 默认 `"exploratory"`（`schema.py:253`），其 `dispositions()/blocking()` 用 `self.run_profile` 喂 `disposition()`（`schema.py:304`）。

崩溃真实：任何走 `flow` 到 4_mep 的 run，`_draw_mep` 调 `check_mep(run_profile=...)` 当场 `TypeError`。

---

## 2. 修法（唯一形态，照抄 `check_assembly`）

`git diff -- src/validator/checks/mep.py`（终态）：

```diff
-from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus
+from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus, RunProfile
 ...
     capability_profile: str = "rectangular",
+    run_profile: RunProfile = "exploratory",
 ) -> CheckReport:
-    rep = CheckReport(stage="4_mep", capability_profile=capability_profile)
+    rep = CheckReport(
+        stage="4_mep",
+        capability_profile=capability_profile,
+        run_profile=run_profile,
+    )
```

与 `assembly.py:28,33-37` 逐字同形。**未改**任何检查的 `status`/`layer`/`check_id`，未放宽/跳过任何断言，未动调用方。

**行为变化**：修前——真实路径 `_draw_mep` 当场 `TypeError`，4_mep 永远不出报告。修后——真实路径出报告，且 `report.run_profile` 如实记录 `policy.run_profile`（可审计，喂 `run_policy_sha256` 等）。对所有**不传** run_profile 的既有调用方，`CheckReport` 默认仍是 `"exploratory"`，**行为字节不变 ⇒ 零回归**（全仓已证）。

---

## 3. ⛔ 验收 B 为什么不可达（核心，已实测坐实）

### 3.1 派工单 B 的字面要求

> 构造一份必然产生 FAIL 的 mep 输入，断言**同一个 check-id**：
> - `run_profile="exploratory"` ⇒ 出现在报告里且**不进** `blocking()`
> - `run_profile="regression"` ⇒ **进** `blocking()`

### 3.2 代码事实：`disposition()` 对所有 `mep.*` 是 profile-无关的

`disposition()`（`schema.py:178-243`）把一条 FAIL 映射到 BLOCK/FLAG。**按 profile 区分阻断**（regression/golden 才 BLOCK，其余 FLAG）的分支**只认这些 check-id**：

- `reading.plan_scale_origin_usable`（`PLAN_FRAME`，`schema.py:65`）
- `reading.ocr_anchors_in_bounds`（`OCR_ANCHOR`，已降为 advisory、永不阻断，`schema.py:93`）
- `reading.dimension_endpoints_in_bounds`（同上，`schema.py:107`）
- `correction.evidence_debt_coverage`（element_local，`schema.py:56,228`）
- `is_evidence_check_id`（全部 `reading.*`，`schema.py:44-53`）

**没有任何 `mep.*` check-id 在此列。** 所有 mep FAIL 都落到 `disposition()` 的通用尾分支：

```python
if result.layer == CheckLayer.INVARIANT:
    return Disposition.BLOCK        # 任意 profile 都 BLOCK
return Disposition.FLAG             # cross_check / perceptual：任意 profile 都 FLAG
```

（`schema.py:241-243`）

⇒ mep 的 INVARIANT FAIL **在 exploratory 和 regression 下都 BLOCK**；mep 的 CROSS_CHECK FAIL **在两档下都 FLAG**。**不存在"exploratory 不阻断 / regression 阻断"的 mep check-id。**

### 3.3 实测坐实（`/tmp/b_probe.py`，构造同时触发 INVARIANT + CROSS_CHECK FAIL 的夹具）

夹具：空 `Construction`（→ `mep.construction_to_material`/`construction_thermal_mass`，INVARIANT）+ 名字含非法字符 `Concrete(block)`（→ `mep.name_charset`，CROSS_CHECK）。

```
--- run_profile=exploratory ---
  FAIL check_ids (layer): {'mep.name_charset': 'cross_check', 'mep.construction_to_material': 'invariant', 'mep.construction_thermal_mass': 'invariant'}
  blocking()           : ['mep.construction_thermal_mass', 'mep.construction_to_material']
--- run_profile=regression ---
  FAIL check_ids (layer): {'mep.name_charset': 'cross_check', 'mep.construction_to_material': 'invariant', 'mep.construction_thermal_mass': 'invariant'}
  blocking()           : ['mep.construction_thermal_mass', 'mep.construction_to_material']
```

**两档 `blocking()` 集合逐字相同。** INVARIANT 两档都阻断（证伪"exploratory ⇒ 不阻断"），CROSS_CHECK 两档都不阻断（证伪"regression ⇒ 阻断"）。

### 3.4 仓库里既有测试直接证伪派工单 §4 的前提

派工单 §4 称「它的检查在 regression 档下从来没有真正阻断过」——前提是 mep 检查像 evidence 检查那样按 profile 区分。**实际不是。** 既有测试 `tests/test_checks_mep_assembly.py::test_bad_mep_semantics_all_three_fire`（line 52-58）：

```python
rep = check_mep(mep, zone_names={"Z1"})          # 不传 run_profile ⇒ 默认 exploratory
ids = _blocking(rep)
assert "mep.simpleglazing_standalone" in ids      # INVARIANT：exploratory 下就阻断
assert "mep.nomass_positive_resistance" in ids
assert "mep.load_to_schedule" in ids
```

**mep INVARIANT 检查在默认 exploratory 下就进 `blocking()`** —— 直接证伪 §4「regression 档下才阻断」的前提。

### 3.5 结论

B 按字面做不到，且**在不放宽约束的前提下做不到**：
- 不能改 `disposition()`（在 `schema.py`，**超出"只动 mep.py"的范围**）；
- 不能改任何 mep 检查的 `layer`/`check_id`/`status`（派工单 §3 明禁）；
- `check_mep` 修后对 run_profile 只"原样传给 CheckReport"，**逻辑不分支**——`results` 在两档下字节相同，只有 `report.run_profile` 字段不同。

⇒ 触发派工单 §8 合法出口：「验收条件 B 在不放宽断言的前提下做不到」「本单陈述的任何代码事实与你看到的不符」。

---

## 4. 验收 A — 真实入口锁 ✅

`tests/test_checks_mep_assembly.py::test_draw_mep_real_path_no_typeerror_and_wires_run_profile`

直调真实 `scripts.tool_scripts.run_stage._draw_mep`（即 `run_stage.py:564-579` 那条路径），仅 stub 掉 LLM（`pipeline.run_mep`）与几何 I/O（`rs._geometry_zone_meta`）——**真实调用点 `check_mep(..., run_profile=policy.run_profile)` 原样跑**。断言落在具体字段 `rep.run_profile == "regression"`（不是"非 None / 总数变了"）。

```
$ python -m pytest tests/test_checks_mep_assembly.py -q -k "draw_mep_real_path"
...                                                                      [100%]
1 passed
```

（修前同样路径抛 `TypeError: check_mep() got an unexpected keyword argument 'run_profile'`。）

> 注：A 不构造 `MepOutput`（会触发 `BuildingSchema` 的 IDD 描述符、在隔离跑下依赖 schema 前置初始化），改 stub 一个带 `.model_dump()` 的对象——`_draw_mep` 只消费 `mep.model_dump()`，等价且自包含。

---

## 5. 验收 C — 默认值锁 ✅

`test_mep_default_run_profile_is_exploratory`：不传 `run_profile` ⇒ `rep.run_profile == "exploratory"`。

```
$ python -m pytest tests/test_checks_mep_assembly.py -q -k "mep_default_run_profile_is_exploratory"
1 passed
```

---

## 6. run_profile 流入锁（B 的诚实替身，**待派工方裁定**）✅

B 的**意图**（让 run_profile 真正管辖 4_mep 报告）可诚实表达为"传入的 run_profile 真的流进报告"：

`test_mep_run_profile_flows_into_report`：

```python
rep_default   = check_mep(_f10_minimal_mep_dict())
rep_regression = check_mep(_f10_minimal_mep_dict(), run_profile="regression")
assert rep_default.run_profile == "exploratory"
assert rep_regression.run_profile == "regression"
```

```
$ python -m pytest tests/test_checks_mep_assembly.py -q -k "mep_run_profile_flows_into_report"
1 passed
```

这是本次修法**实际交付**的行为变化（修前：真实路径直接崩；修后：run_profile 如实进报告、可审计）。

---

## 7. 验收 D — neuter 两向 ✅（均先 `git diff` 确认落地再跑）

### D2：形参默认值 `exploratory`→`regression`（期望 C 红）

`git diff` 确认 `run_profile: RunProfile = "regression"` 落地后：

```
FAILED tests/...::test_mep_default_run_profile_is_exploratory
E   AssertionError: assert 'regression' == 'exploratory'
```

✅ C 红（默认值被改 ⇒ 默认报告不再是 exploratory）。已恢复。

### D1：摘掉 `CheckReport(..., run_profile=run_profile)` 接线、保留形参（期望"C 之外的行为锁"红）

`git diff` 确认 CheckReport 调用退回 `CheckReport(stage="4_mep", capability_profile=capability_profile)`、形参仍在：

```
2 failed, 1 passed
  flow-lock: E  assert 'exploratory' == 'regression'   (传 regression 被丢 ⇒ 报告留默认)
  A        : E  assert 'exploratory' == 'regression'   (真实路径 policy.run_profile 被丢)
  C        : passed                                  (默认仍 exploratory)
```

✅ 两把行为锁（flow + A）**红在断言**（传 regression 被丢、报告恒为默认 exploratory），C 保持绿。锁真绑接线、非空操作。已恢复。

> 派工单 D1 原文是"C 之外的 B 必须红"——B 既不可达，此处用 flow+A 替身证明：摘接线 ⇒ 行为锁红、C 不红，分辨力成立。

---

## 8. 验收 E — 全仓 ✅

```
$ python -m pytest -n auto -q   （不加 -m）
2223 passed, 10 xfailed, 209 warnings in 304.52s (0:05:04)
```

基线 2220 绿 / 10 xfail / 0 红 → **2223 绿 / 10 xfail / 0 红**。**净增 3 锁、零回归。**

> 单文件隔离跑会红 `test_assembly_backstop_*` / `test_s5_unconditional_override_all_thetas[*]`（`ModelPrivateAttr ... 'Building'`，IDD schema 前置初始化的跑序问题，F-8 同族）。**已 `git stash` 验证：基线（无 F-10 改动）隔离跑同样红** ⇒ 与 F-10 无关；全仓跑全绿。

---

## 9. ⚠️ 并行席位 WIP 误入工作树（已规避）

会话开始时 `git status` 干净（仅 4 个 untracked）。施工中 `AI_agent/plan.md` 变成 modified——内容是 **orchestrator 的 "F-9 定性作废 / 手性" 叙述**（非我所写，与本单无关）。判定为并行 orchestrator 席位的半成品。
**本单 commit 将只 `git add` 自己的三个文件**（`src/validator/checks/mep.py`、`tests/test_checks_mep_assembly.py`、本日志），**绝不 `git add -A`**（参 memory `wrapup-commit-sweeps-other-seats-wip`）。

---

## 10. 结论与请派工方裁定

1. **修法正确、必要、零回归**（照抄 check_assembly，全仓 2223 绿）。
2. **A/C/D/E + run_profile 流入锁全部就绪并取证。**
3. **B 按字面不可达**（mep 检查在 `disposition()` 里 profile-无关；§3 已用代码追踪 + 实测 + 既有测试三重坐实）。

**请裁定 B 如何收口**（三选一，我推荐 a）：
- **(a) 采纳 §6 的 "run_profile 流入报告" 锁作为 B 的诚实替身**（已落、已验、neuter 已证真绑）——它表达的就是"4_mep 第一次真正受 run_profile 管辖"的实际语义；
- (b) 派工方确认"mep 检查非 profile-gated"是已知事实、B 措辞有误，直接以 A/C/flow 收口；
- (c) 若确实要"某 mep check-id 按 profile 区分阻断"，那需另开单改 `disposition()`（schema.py，超出本单范围）+ 用户拍板（属于改变阻断语义面）。

裁定后我立即按"只 add 三文件、不 push"提交。
