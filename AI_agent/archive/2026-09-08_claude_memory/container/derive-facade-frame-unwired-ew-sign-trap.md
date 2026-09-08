---
name: derive-facade-frame-unwired-ew-sign-trap
description: derive_facade_frame ✅已接线为 gate① flag-only 交叉校验(2026-07-06 be23d12,体检 A1-1 中间态);E/W sign 陷阱已解除(6.30 翻正+gt 锚定);真替 LLM 落位仍归 Phase B/B5
metadata: 
  node_type: memory
  type: project
  originSessionId: 92906b65-e3a9-4c4e-97ff-68ebac314559
---

`src/agent/correction/facade.py:derive_facade_frame` 是一个**已经写好但全未接线**的确定性 facade→world 翻译函数（contracts §158b "应补"=全局坐标侧；当前 pipeline 仍由 correction LLM 填 `Window.span` 世界坐标，该函数无任何生产消费者，只有测试引用）。

**陷阱**：它的 East/West sign（`_CONVENTION["East"]=("y","x_max",-1)`、West `+1`）与**活口径相反**。活口径 = 老 reading guide §4（2026-06-27 搬进 correction `A1_coordinate_normalization.md §2.2`）= **East→+y(north)、West→−y(south)**，sm21 的 E2/W1 立面窗在该口径下命中 gt。而 `derive_facade_frame` 的 E/W = East→−y、West→+y（与外立面从外看的标准约定按物理推理相悖）。更糟：它的测试 `test_facade_frames_standard_convention` 只断言 East 的 axis+base_world，**没断言 E/W 的 sign**，所以这个分歧一直没被测出。

**纪律**：把 `derive_facade_frame` 接进确定性核（做 local→world、替 LLM 翻译）= 用户定缓做的"全局坐标可审变换"主线。**接核前必须先用 sm21（或有 E/W 窗的图）gt 校验 E/W sign 再定取舍，勿凭推理擅改任何一边**（呼应 [[judge-gt-authoritative-images-auxiliary]]：gt 才是裁判）。South/North 两边两口径一致（+x/−x）、无争议。

**⚠️ 2026-06-30 更新（Phase A A10 已处置）**：E/W sign **已 test-first 翻正** = `_CONVENTION["East"]=("y","x_max",+1)`、West `−1`（对齐 A1 活口径 + gt-validated）。新增测试锚 sm21 gt East-F2/West-F2 窗世界 x（judge-side gt load），先 fail on 旧 East−1/West+1、翻常量后 pass。**但 `derive_facade_frame` 仍未接线**（仅测试引用），翻常量安全；**真接线进确定性核仍归 Phase B**（届时再做 local→world 替 LLM 翻译，仍以 gt 为裁判）。详 [[reading-evolution-and-phase-a]]。

**2026-07-05 Fable5 体检复核(A2-4)**:零调用点再次坐实(唯一提及是 checks/correction.py docstring、未 import);体检建议**接线不必等完整 Phase B**——先作 gate① 交叉校验(LLM 落位 vs 确定性落位,不一致 flag)是零风险中间态,详 [[fable5-audit-2026-07-05]]。

**✅ 2026-07-06 接线完成（体检 A1-1 中间态,`be23d12`）**：接成 gate① `correction.facade_frame_cross_check`（CROSS_CHECK 层 flag-only 不改 gate 判定）——per-facade 确定性变换 reading 立面窗位→世界坐标 vs correction LLM 落位,超容差 flag（`facade_frame_cross_check_tol_m=0.300` 进 correction.yaml+A0）,缺产物 NOT_APPLICABLE,validate_case+run_pipeline 双路进 parity 锁;真数据探针 sm21 权威 run 15 窗 0 flag。**"未接线"自此不成立**;剩余=①per-segment 版(C2 B5)②真替 LLM 做 local→world 落位(Phase B,届时 flag→block 需另拍板)。

发现于 2026-06-27 reading 迁移完整性审计（该轮 reading 修法已**回滚**、reading 暂收口待测试结果再续；本 finding 是关于**现有代码的独立事实**、不随回滚失效）。详 [[reading-quality-investigation-2026-06-24]] 与 plan.md N1f/N1g。
