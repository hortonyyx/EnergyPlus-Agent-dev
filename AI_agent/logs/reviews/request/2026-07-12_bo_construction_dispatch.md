# B-O 批施工派发（Sonnet 5 执行档，2026-07-12）

**任务**：按 [AI_agent/proposals/c2_e4_output_contract_spec.md](../../proposals/c2_e4_output_contract_spec.md) **v2 定稿**施工 B-O 批（真北接线：EP 出口切 Relative + Zone 零原点 + Building.North Axis=θ 唯一 owner）。该稿是**唯一施工合同**（累计式自包含）：`OutputCoordinateContract` strict 类型、派生器、sidecar、S4 占位 0 硬门、S5 无条件 θ override、GlobalGeometryRules A3/A4/A5 完整建模、Zone Origin 归零与迁移门、building-bound 坐标对象闭世界 registry 三层审计、六入口对等、EP 25.1 端到端断言与全部测试族，均以稿为准。

## 硬边界

- 基座 = 当前 HEAD（B2b 已收录，工作树干净）。**只放行 B-O**：不动 B2b/Vg/B4/B5 顺带施工；不旋转 correction/kernel/BuildingGeometry/specs 顶点；不把 N/S/E/W facade 标签改真北方位；不扩 IntakeOutput 11 字段契约；不动 golden/gt/case anchors；不改管理文档；本批**不创建 commit**。
- 施工前先按稿的前置门机械断言（只查已收录依赖）；v1/v2 与无法证明属 E4 的旧 IntakeOutput 继续走 World legacy；**禁止任何 `if theta != 0` / truthiness / 数值猜分支**（v3/E4 即使 θ==0.0 也走 Relative）。
- E4 orientation helper claims 注册中央 correction release map 为 release `"4"`，writer 只经 `correction_stage_version()` 派生（稿 E4-R3）；`completion_mode=prior_fill` + 零受信 orientation 证据时由 enrichment finalize 确定性生成 `NorthAxisEvidence(0.0, assumed)`（稿 E4-R2）。
- 改 `src/`/`scripts/`/`tests/` 前先备份既有将改文件到 `backup/src_history/2026-07-12_bo_north_axis_wiring/`（按仓库相对路径）。
- 探针基线 = [logs/experiments/2026-07-10_e4_relative_north_axis_probe/RESULTS.md](../../logs/experiments/2026-07-10_e4_relative_north_axis_probe/RESULTS.md)（EP 25.1 五条全过）；端到端验收断言以稿为准（θ=0/90/270 azimuth 对账、非零用例无 "ignored" 警告）。

## 测试纪律

- 定向分组跑（新增测试文件+被改模块对应组），逐组记录 passed 数；**全量 pytest 由主控终审独立跑（唯一权威门）**。
- EP 端到端用例若需真跑 EnergyPlus，容器内 `$ENERGYPLUS_EXE`（25.1.0）可用；跑不动/超时的项在简报"未决"如实列明。
- 稿内测试族全数落地；确有未竟逐条列明，不得静默。稿章节→测试映射表写进简报。

## 交付

1. 工作树内完成全部代码+测试改动（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-12_bo_construction_brief.md`（结构：改动映射/备份/验收与测试/预期行为变化/未决·偏离事项/**review-ask**）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要），不贴 diff。

审向：sol 执行审（Claude 侧施工→GPT 侧审，谁写谁不批）+ 主控大节点全面审（独立全量 pytest+逐行 diff）。
