# derive_facade_frame 单平面接线 = gate① 交叉校验（体检 A1-1 中间态）执行简报

- **日期**: 2026-07-06；**依据**: Fable5 体检 [FABLE5_REPORT.md A1-1 + Top10#5](../../../AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md)（"先作 gate① 交叉校验接线,不等完整 Phase B"）+ C2 设计 D4 接线顺序建议（"先按 A1-1 中间态把单平面版本接成 gate① 交叉校验(C1 情形即可用),C2 批内再升 per-segment"——per-segment 属 B5,本批不做）。
- **流程注记**: 同 B0 批——Claude 出简报,Codex 执行前对照体检 A1-1 与 facade.py 现状先审简报（发现设计空洞先报再动手）,审+执同线程,痕迹记执行日志。

## 背景

`src/agent/correction/facade.py:derive_facade_frame`（确定性 facade image-local → world 变换,E/W sign 已翻正 `23a0e47`+gt 锚定测试）**全仓库零调用点**。现状=窗世界落位由 correction LLM 按 A1 §2.2 prose 手工换算符号（pipeline.py prompt "mind the North/West sign flip"),每 run 掷骰子。本批不夺 LLM 的落位权,只加确定性交叉校验让掷错骰子可见。

## 范围（单项）

新 gate① check `correction.facade_frame_cross_check`（**CROSS_CHECK 层,flag 不 block,任何 profile 下都不改 gate 判定结果**）：

1. 输入 = accepted `CorrectedGeometry`（窗世界坐标+facade）+ 该 run 的 0_reading 立面视图产物（窗 image-local along-x/宽度）。读的是 run 自产物,**绝不触 gt**。
2. 对每个立面：用 `derive_facade_frame`（单平面版,锚定权威 envelope/footprint bounds）把 reading 立面窗位变换到世界坐标 → 与 correction 同 facade 窗集合按最近沿面坐标贪心配对 → 偏差超容差 → flag,evidence 带 per-window（reading 局部坐标/确定性世界坐标/LLM 世界坐标/delta）。
3. 容差 = 新命名配置进 `correction.yaml` + A0 登记（禁裸字面量,D9#4 教训;量级建议对齐既有 envelope/吸附容差族,由你按现有常数族选定并在执行日志说明理由）。
4. 缺输入诚实降级：无立面 reading 产物 / envelope 不可得 / facade 数据不足 → `NOT_APPLICABLE`（对齐 `mep.site_matches_testdata` 姿态）,不编造。
5. 两路消费一致：`validate_case` 与 `run_pipeline` 都接（M1 parity 锁自动覆盖,验证新 check 进锁范围）。

## 明确不做

不改 correction prompt/prose（LLM 仍负责落位）;不改 reading/correction schema;不做 per-segment（B5）;不把 flag 升 block（那是后续拍板）;不动 facade.py 的变换本体与既有 gt 锚定测试（若发现接线暴露的真 bug,停下来报,不静默修）。

## 验收

- 全量 pytest 绿 + 零 golden 改动。
- 新测试：① 合成一致数据 → PASS;② 人为把 LLM 窗 x 挪偏超容差 → FLAG 且 evidence 齐全;③ 无立面 reading 数据 → NOT_APPLICABLE;④ E/W 翻转朝向情形与 facade.py gt 锚定测试口径一致。
- **真数据 read-only 抽查**：对既有 anchor（sm21 `run_2026-07-02_sonnet_flow_e2e`）跑一次该 check,报 flag 计数与样例进执行日志（只读、informational、不改 run 产物）。
