---
name: seed-bypass-exposes-hidden-downstream-blocker
description: 08-05 探针 A：播种 legacy 产物绕开已知 blocker(F-9)，暴露了被它遮蔽的下游第二处 blocker(4_mep)；+ zone 命名漂移/validate_case stage 根接缝两条 gotcha
metadata: 
  node_type: memory
  type: project
  originSessionId: 050264fa-1a28-4b7e-a21f-b19ad0339a84
---

2026-08-05 探针 A（GLM，报告 `AI_agent/logs/reviews/execution/2026-08-05_probe_a_legacy_snapped_glm.md`，commit `a3018eb`）：把 6 月【内核后】legacy v1 几何（`correction_geometry_snapped.json`）播种成 accepted 1_correction，绕开 F-9，灌进今天的 2→5。

**⭐ 元教训（可复用方法）**：**下游 blocker 会被上游 blocker 遮蔽**——派工单说真链路卡在 1_correction(F-9)，但绕开 F-9 后撞出 **4_mep 这第二处 blocker**。⇒ 「链路卡在 X」≠「X 之后都没问题」；**播种已知好产物绕开 X，是暴露 X 之后隐藏 blocker 的有效探针手法**（与 [[real-chain-run-exposes-what-tests-cannot]] 同族：真链路/绕行才暴露得了）。

**探到的具体缺陷（v1/rectangular 档；v3 专有接线本探针测不到）**：
1. **4_mep flow 路径硬崩**（被 F-9 遮蔽）：`_draw_mep`（`scripts/tool_scripts/run_stage.py:577`）给 `check_mep` 传 `run_profile=`，但 `check_mep`（`src/validator/checks/mep.py:95`）签名无此形参 ⇒ `TypeError`。**任何**走 flow/`run_stage.py run` 到 4_mep 的 run 必崩。注：`run_mep`(LLM) 在 check_mep 之前已成功产出 → 是 gate① 调用签名崩、非 LLM 路径崩。
2. **今天 check_mep 对任何 mep 都不放行**：今天 `run_mep` 产出缺 14 schedule（`load_to_schedule` block）；June 已知好 mep 又因 **zone 命名漂移**被拒。
3. **zone 命名漂移**：June mep 用 `R_1F_TL/R_2F_B4`（R=层+位置），今天 geometry(`build_geometry`) 用 `Z01_F1_Office_NW`（Z0n_F<层>_<角色>_<方位>）——**零交集**。⇒ June-era mep 与今天 geometry 不兼容（CLAUDE.md「命名/外包确定性化」的副作用）。⚠️今天 14 zone 名还有重复后缀嫌疑（Z11/Z12 都 `_F2_Office_SW`、Z13/Z14 都 `_F2_Office_SE`）。

**⭐ gotcha（seeding/复用场景必撞）**：`validate_case`（`src/agent/execution/validation_run.py:101/188/192`）的几何 digest 从 **stage 根** `1_correction/correction_geometry_snapped.json` 读，**不**读 manifest accepted attempt 的 `attempts/NNN/output.json`。而 `StageRunner.record` 用**裸 dict**（base_v2、非 FinalizeResult）播种**不写** stage 根便利副本（只有 `is_correction_write` 才写，`stage_runner.py:560-563`）。⇒ 绕开 LLM draw 用裸 dict 播种的几何，`--geometry auto` 会报 "no consistent checkpoint"（`approve_geometry`→`validate_case` 算不出 digest）。补 stage 根镜像（= accepted attempt 内容逐字节拷）即可；正常 flow 走 FinalizeResult 两个都写、故不可见。

**正面**：0_reading/1_correction/2_modelling/3_split_pairing 在 legacy v1 上 gate① 全绿（block=0）——几何内核本身没坏、F-9 是 v3 专属（v1 的 `check_correction` 不跑 `check_window_host_resolution`）。

**派工方本轮又一处疏漏**：命令漏写 `--geometry auto`（flow 把 `confirmation_policy=REQUIRED` 写死 + `GEOMETRY_CHECKPOINT_STAGE="3_split_pairing"`，不带该旗标必停于几何确认门、到不了 4/5）。续 [[stop-and-report-catches-dispatcher-errors]]。
