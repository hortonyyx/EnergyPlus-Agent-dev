# 彻底关闭桶③：check_assembly inline + kernel 其余 INVARIANT 升级 run_pipeline raise —— 方案

> 状态：**方案待 Codex 审**（2026-07-01，Claude 出）。用户选定「先把 A 做了」= 彻底关桶③。
> 前置：`7.01_RunPipelineSelfCheck`（commit `7c4ac78`）已把 check_correction/check_mep inline 进 run_pipeline，桶③剩这两条同类小尾巴。
> 关联：A8（evidence inline）、S23-16（kernel InterZone inline）、上一轮 review `2026-07-01_run_pipeline_self_check_review.md`（其中「不要把 kernel 折进通用 `_gate`」是**当时 scope 外**的提醒，本轮 scope 内、故意反转，见 §2 决策 D1）。

---

## 1. 目标 + 现状

**目标**：把主线 `run_pipeline` 的自校覆盖**完全**对齐 `validate_case`，收口桶③。

| 剩余项 | validate_case | run_pipeline 现状 | 本轮 |
|---|---|---|---|
| **S5 `check_assembly`** | ✅ 写 `5_intakeoutput/assembly_checks.json`（`validation_run.py:230/240`）| ❌ 只有 `validate_contract`（全 profile raise，`pipeline.py:1011-1021`），无 `assembly_checks.json` 产物 | **piece 1** |
| **S2 kernel 其余 INVARIANT** | ✅ `_finalize` 对 `kernel_report.blocking()` **全部**阻塞（zone_closure/normals/pairing/spec/coverage）| ⚠️ 只对 **InterZone**（`kernel_issues`）在 golden/regression raise（`pipeline.py:957-961`），zone_closure/normals/spec/coverage 只写报告不 raise | **piece 2** |

**关键事实（已核）**：
- **`check_assembly`（几何路径）= `validate_contract` 的 backstop 包装**（`assembly.py:23-41`：re-run 同一 `validate_contract`，记 `assembly.contract_backstop` INVARIANT）。**无新校验逻辑** → piece 1 = 纯加 `assembly_checks.json` 产物做 validate_case 口径对齐 + 可见性，**不改任何阻塞行为**（`validate_contract` 已全 profile raise）。
- **`check_kernel` 的 5 个门全是 INVARIANT**（`kernel.py`：zone_closure/normals/pairing_gate/spec_self_consistency/coverage_completeness，coverage 在非矩形 profile 记 NOT_APPLICABLE）；**`interzone_issues` 已被纳入 report**（`_pairing_gate` 记 `kernel.pairing_gate` INVARIANT，`kernel.py:177-196`）→ 故 `kernel_report.blocking()` **含 InterZone**，改用它**不会丢** InterZone raise（仅消息变），只**新增**其余四门在 strict profile 的 raise。

---

## 2. 改动落点（`src/agent/pipeline.py`，全在 `run_pipeline` 内；复用已有 `_gate_self_check_report`）

### piece 1 — S5：inline `check_assembly`（纯加产物，零阻塞行为变化）
现 `pipeline.py:1004-1027`（assemble → validate_contract → 全 profile raise → 写 intake_output.json）。改为：
```python
intake = assemble_intake_output(...)                 # 不变
from src.validator.checks.assembly import check_assembly
assembly_report = check_assembly(intake, used_constructions, capability_profile=capability_profile)
if s5 is not None:
    (s5 / "assembly_checks.json").write_text(assembly_report.model_dump_json(indent=2), encoding="utf-8")
contract_issues = validate_contract(intake, used_constructions)   # 保留：全 profile 硬 raise
if contract_issues:
    if s5 is not None: (s5 / "contract_issues.json").write_text(...)   # 不变
    raise RuntimeError(...)                                            # 不变（全 profile）
if s5 is not None: (s5 / "intake_output.json").write_text(...)         # 不变
```
- **为何不走 `_gate`**：`_gate_self_check_report` 只在 golden/regression raise；但 contract 失败=坏 IntakeOutput、下游不可消费，**必须全 profile 硬停**。故 piece 1 **保留既有 `validate_contract` 全 profile raise 不动**，只加 `assembly_checks.json` 产物（且**故意在 raise 之前写**，contract 失败时 validate_case 口径下 assembly_checks.json 仍在）。
- **`validate_contract` 双跑**（check_assembly 内一次 + inline 一次）：成本 trivial（construction_specs 上的整词正则）。**审阅需求 A1**：接受双跑（清晰）vs 单跑 validate_contract 再据 issues 构 report（须不改 check_assembly 签名）。倾向双跑。

### piece 2 — S2：kernel gate 升级为全 blocking（复用 `_gate_self_check_report`）
现 `pipeline.py:953-961`（手写 kernel_checks.json + **仅 InterZone** 在 golden/regression raise）→ 替换为：
```python
_gate_self_check_report(
    stage_name="2_modelling",
    report=kernel_report,
    stage_dir=s2,
    filename="kernel_checks.json",
    run_profile=run_profile,
)
```
- 效果：写 `kernel_checks.json`（不变）+ golden/regression 下 `kernel_report.blocking()` 非空则 raise（**InterZone 保留 + 新增 zone_closure/normals/spec/coverage**）+ exploratory 只 warn 续行。
- **保留不动**：`materialize_kernel_geometry` 的 `kernel_gate_report.json`（advisory）+ `if bg is None: raise`（硬 build 错，全 profile）+ 上方 `if kernel_issues:` advisory warning 日志（`pipeline.py:928-935`）。**审阅需求 A2**：exploratory 下 advisory warning（928-935）与 `_gate` 的 warn 会对 InterZone 双日志（各自指 kernel_gate_report.json vs kernel_checks.json blocking）——接受（信息不同）vs 精简。倾向接受、不动 advisory。

### D1 — 「反转上轮 kernel 提醒」是故意的
上一轮 review 说「别把 kernel 折进通用 `report.blocking()` gate，会把 kernel 收紧到 InterZone 之外」。**那是当时 scope（只做 correction/mep）外的保护性提醒**。本轮**桶③收口就是要这个收紧**（用户定），故**故意反转**：kernel 现走全 blocking gate。**这不是回归、是设计目标**。请 Codex 按「本轮 scope 含 kernel 收紧」重新裁定，确认反转正确、无非预期副作用。

---

## 3. run_profile 分档（不变，沿用既定）
- exploratory（含生产 intake_node 默认）：写产物 + warn 可见但**续行** → 生产路径**零新硬失败**（kernel 其余门在 exploratory 本就不 raise、现在也不）。
- golden/regression：`kernel_report.blocking()` 非空 → fail-closed raise（新增其余四门）。
- **向后兼容论证**：golden baseline 都是**干净几何**（经 validate_case 录制、validate_case 本就对全 kernel blocking 阻塞）→ 不存在「有 kernel 其余门阻塞却已入册」的 golden，故无既有 golden 被本轮新 raise 打破。piece 1 零行为变化。

---

## 4. 测试 / 影响
1. **piece 2 消息变更**：`test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles` 现断言 InterZone raise；新消息由 `_gate_self_check_report` 出（`"2_modelling self-check blocked under run_profile=..."`）。若测试 match 旧串 `"InterZone pairing gate blocked"` → 更新断言（仍 `pytest.raises(RuntimeError)`，match 改新串或去 match）。**审阅需求 A3**：Codex 核该测试与其它 kernel 相关测试的 match。
2. **新增测试**：
   - piece 1：成功路径写 `assembly_checks.json`（passed）；contract 失败路径 `assembly_checks.json` 在 raise 前已写 + `assembly.contract_backstop` fail；与 validate_case 的 assembly 报告 status 一致（parity）。
   - piece 2：构造「bg 能 build 但 kernel 其余门（如 coverage_completeness / spec_self_consistency）blocking」的 fixture → golden 下经新 gate raise、exploratory 下 warn+续行且写 kernel_checks.json。若难构造非 InterZone 的可 build-但-blocking geom，退而用 monkeypatch `check_kernel` 返回带非 pairing blocking 的 report（执行器判断，回报选择）。
3. 全量 `pytest`（当前 **393 绿 / 9 xfail**）作回归基线。零 golden 改动预期。

## 5. 明确不做
- 不改 `check_assembly`/`check_kernel`/`validate_contract` 签名或语义——只在 run_pipeline 侧接线。
- 不动 stepwise（run_stage.py）/ validate_case。
- Phase B（#2/#3/#6）、`total_floor_area` 软核对、A8 backlog 等另线。

## 6. 审阅需求汇总（Codex 逐条裁 + 补漏）
- **A1**：piece 1 `validate_contract` 双跑 vs 单跑；assembly_checks.json 写在 raise 前（parity）确认。
- **A2**：kernel exploratory 双 warning（advisory + gate）接受 vs 精简。
- **A3**：piece 2 消息变更对既有 kernel 测试断言的影响（枚举 + 改法）。
- **A4**：D1 反转——确认本轮 scope 含 kernel 收紧、反转正确、无非预期副作用（尤其：有无既有 exploratory 测试依赖「kernel 其余门在 run_pipeline 不 raise 且不 warn」的静默行为）。
- **A5**：`_gate_self_check_report` 复用于 kernel 是否需要任何调整（它当前 filename/profile 显式、warn 带 check id、先写产物再 raise——对 kernel 语义是否完全合适）。

---

## 7. 定案（Claude 裁决，2026-07-01，Codex 审 APPROVE-WITH-CHANGES 全采纳）

Codex 审 = **APPROVE-WITH-CHANGES**（`logs/review/review/2026-07-01_bucket3_close_review.md`），设计 sound、findings 全程序性。全采纳，执行按下列定案：

1. **piece 1（S5 assembly）**：assemble 后 inline `check_assembly(intake, used_constructions, capability_profile=capability_profile)`，**在既有 `validate_contract` raise 之前**写 `5_intakeoutput/assembly_checks.json`（contract 失败时诊断产物仍在）。**保留既有全 profile `validate_contract` raise + `contract_issues.json` 写 + intake_output.json 写不动**。`validate_contract` 双跑（check_assembly 内 + inline）可接受（A1，成本 trivial、check_assembly 保持 validate_case 规范包装）。**S5 不走 `_gate`**（必须全 profile 硬停）。
2. **piece 2（S2 kernel）**：把现 `pipeline.py:953-961`（手写 kernel_checks.json + interzone-only strict raise）**整段替换**为 `_gate_self_check_report(stage_name="2_modelling", report=kernel_report, stage_dir=s2, filename="kernel_checks.json", run_profile=run_profile)`——**无重复写**（旧手写删净）。保留 `check_kernel(..., run_profile=run_profile)` 传参不变（helper 的 `blocking()` 吃 `report.run_profile`，故 check_kernel 必须继续收到 run_profile，A5）。`materialize_kernel_geometry` 的 advisory `kernel_gate_report.json` + `if bg is None: raise` + 928-935 advisory warning **保留不动**（A2 双 warn 接受）。
3. **测试**：① 改 `tests/test_a8_evidence_routing.py::test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles`（:381 的 `match="InterZone pairing gate blocked"` → match 新 helper 串 `"2_modelling self-check blocked under run_profile=..."` 且断言 `kernel.pairing_gate` 在异常串，或去 match 改断言 exc 串含 `kernel.pairing_gate`）；② **新增**非-pairing kernel 测试（monkeypatch `src.validator.checks.kernel.check_kernel` 返回带 `kernel.coverage_completeness`/`normals`/`spec_self_consistency` blocking 的 report，run_pipeline 惰性 import 故 monkeypatch 有效）：**golden 下经新 gate raise**（断言 artifact 边界：`building_geometry.json`+`kernel_gate_report.json`+`kernel_checks.json` 存在、`3_split_pairing/geometry_specs.md` **不存在**）+ **exploratory 下写 kernel_checks.json + warn + 续行到 S5**；③ **新增**（可选）piece 1 assembly parity 测试（成功写 assembly_checks.json passed / contract 失败时 raise 前已写 + `assembly.contract_backstop` fail / 与 validate_case assembly 报告 status 一致）。
4. **向后兼容表述软化**（Codex e/#4/#5）：不宣称「baseline 录制使 blocked kernel report 不可能」（record_baseline 默认 exploratory + 记 blocked 不 abort）；改为**观察到的仓库事实**——现 checked-in 6 个 run 目录 kernel_checks.json 五门全 pass、read-only rebuild 无 `run_profile=golden` blocker，故本轮升级不会新打破现有 anchor。piece 1 零行为变化。
5. **不做**：不改 check_assembly/check_kernel/validate_contract 签名（含不给 check_assembly 加 run_profile——S5 由独立全 profile raise 管，A5/#5）；不动 stepwise/validate_case；Phase B 等另线。

**验收**：全量 pytest（当前 **393 绿 / 9 xfail**）；零 golden 改动预期；Claude 大节点全面审（自跑 pytest + 逐行 diff）。
