# orchestrator 轻门 · F-10 `check_mep` 签名漂移

- **日期**：2026-08-05（深夜）
- **裁决**：**PASS（含派工方自认题错 + 验收 B 改判）**
- **施工席**：GLM-5.2（主工作树）
- **派工单**：[`request/2026-08-05_f10_check_mep_signature_dispatch.md`](../request/2026-08-05_f10_check_mep_signature_dispatch.md)
- **执行日志**：[`execution/2026-08-05_f10_check_mep_signature_glm.md`](../execution/2026-08-05_f10_check_mep_signature_glm.md)

---

## 1. ⛔ 派工方（orchestrator）的题错了 —— 本轮第 7 次「停下上报」

**派工单 §4 原文**：「现状 4_mep 的报告恒以默认 `exploratory` 构造 ⇒ 它的检查在 `regression` 档下**从来没有真正阻断过**。」
**据此定的验收 B**：同一 check-id 在 `exploratory` 不阻断、在 `regression` 阻断。

**⇒ 前提是错的，B 结构上不可达。** GLM 停下上报，orchestrator **独立核实属实**：

1. **`disposition()`（`src/validator/checks/schema.py:178-243`）对所有 `mep.*` 是 profile-无关的。**
   受档位管的只有 `is_plan_frame_check_id` / `is_ocr_anchor_check_id` / `is_dimension_endpoint_bounds_check_id` /
   `correction.evidence_debt_coverage` / `is_evidence_check_id` 五类；`mep.*` 一律落到尾部两行：
   `INVARIANT → BLOCK`（任何档）、`else → FLAG`（任何档）。
   **该函数 docstring 逐字写着** *"today the default rules below are profile-agnostic"*。
2. **仓库既有测试直接证伪该前提**：`test_bad_mep_semantics_all_three_fire`（`tests/test_checks_mep_assembly.py:52`）
   调 `check_mep(mep, zone_names={"Z1"})`（**不传 run_profile ⇒ 默认 exploratory**）并断言
   `mep.simpleglazing_standalone` 等 INVARIANT **在 `blocking()` 里** ⇒ mep 检查在 exploratory 下**本来就阻断**。

**⇒ F-10 不是「行为变更」，是纯粹的 ①止崩 + ②让报告如实记录自己是在哪个档位下被判定的。** 风险比派工单估计的低。

**新错误类别（第三类）**：前两类是「代码事实」的题与「环境/基点」的题；这次是**「验收条件本身不可达」**——
我从「参数没传进去」反推出「一定存在行为差异」，**却没去读那段策略代码**。
**自检问法（已入规约）：这个差异，我在代码里指得出是哪一行产生的吗？**

## 2. 验收 B 裁定 = 采纳 (a)+(b)

- **(a)** 以「`run_profile` 流入报告」锁作为 B 的诚实替身 —— 它表达的正是本修法实际交付的语义；
- **(b)** 确认「mep 检查非 profile-gated」是代码事实、派工单 B 措辞有误，以 **A + C + flow 锁**收口。
- **⛔ 否决 (c)**（改 `disposition()` 让某 mep check-id 按档位区分阻断）：那是**改变阻断语义面**，
  需用户拍板，且本轮**没有任何需求要求它**。⛔ 不得为了凑一条验收条件去改策略层。

## 3. orchestrator 独立验证（不采信施工方数字）

| 项 | 结果 |
|---|---|
| **独立全量** `pytest -n auto`（无 `-m` 过滤） | **2223 passed / 10 xfailed / 0 红**（304.78s）；基线 2220 ⇒ **净增 3 锁、零回归**。与施工方数字**逐字一致** |
| **独立 neuter（换方向：完整复原 F-10 本尊）** | 撤回整个修法（形参 + 接线全删，`git diff` 先确认落地、非空操作）⇒ **A 锁与 flow 锁红**，报的是生产环境原句 `TypeError: check_mep() got an unexpected keyword argument 'run_profile'` @ `run_stage.py:572`；**C 保持绿** ⇒ **分辨力两向成立、锁真绑 F-10 本尊** |
| **POST-RESTORE** | 恢复后 F-10 三把锁全绿，diff 与交付一致 |
| **亲核 diff** | `src/validator/checks/mep.py` **仅 +7/−2**：加 `RunProfile` import、加 `run_profile` 关键字参数、传给 `CheckReport`。**照抄 `check_assembly` 模式，零额外改动** |
| **施工方预警的隔离跑红条** | `test_assembly_backstop_attributes_owner_to_mep` 单跑红 —— **orchestrator 独立验证：换成 HEAD 原版 `mep.py` 单跑同样红** ⇒ 基线既有、与 F-10 无关（**F-8 同族：测试的绿依赖跑序/全局 IDD 初始化状态**）|

**锁的质量**（亲核）：
- **A 锁走真实入口** —— 直接驱动 `run_stage._draw_mep`，只 stub 掉 LLM（`run_mep`）与几何 I/O（`_geometry_zone_meta`），
  真实走到 `run_stage.py:572-578` 那个调用点。⛔ 不是「测试里直接调 `check_mep(run_profile=…)`」的形状。
- **夹具自包含**（`_f10_minimal_mep_dict()`），**零 gitignored 文件依赖** ⇒ 不给 F-8 添砖。
- 施工方把「B 为何不可达」**写进了测试文件的注释**，后人改这里能直接看到，不会重犯。

## 4. 结转

- **F-10 CLOSED。** 4_mep 的硬崩解除 ⇒ **下一步可第一次撞到 5_intakeoutput（至今零证据）**。
- **墙 3 未动**：`run_mep` 产的 load 引用未定义 schedule（`mep.load_to_schedule` 14 条），未定性未修。
  ⚠️ 该检查是 `INVARIANT` ⇒ **任何档位都阻断**，所以 F-10 修完后它会立刻挡在下一步。
- **F-8 又添一例**：`test_assembly_backstop_attributes_owner_to_mep` 与 `test_s5_unconditional_override_all_thetas[*]`
  隔离跑红、全仓跑绿 ⇒ 「全仓绿」的不可靠性不止「gitignored 活输入」一种成因，**还有跑序/全局状态**。已登记。
