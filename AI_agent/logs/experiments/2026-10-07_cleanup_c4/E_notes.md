# E：sm24 run6 保存装配的离线续改核对

## 结论

真实的 `sm24_run6` 保存装配 `candidate_02` 可以在复制出的注册表上继续调用确定性 `revise_bim` 和 `finish_bim`。本次没有调用外部模型，没有运行 pytest，没有修改公共源码，也没有改动主树产物。

一步建楼写入的 8 个 safe matched height 在 `candidate_02` 上都仍有当前、已采用的图像型 `z` 绑定，`claim_0001` 状态为 `applied_current`。但这不等于最终交付表认可 8 个洞口都已定位：严格交付表只把 13 个外部洞口中的 `D2`、`W_B1` 两个记为 `located_applied`，其余 11 个为 `missing`。最终表除了当前 claim 绑定，还要求立面校准有效，并且证据框能落到该具体外部洞口；因此“8 个已安全应用”与“8 个已通过最终定位覆盖”是两层不同结论。

`finish_bim` 当前不会因高度覆盖不完整而阻断交付。它会把缺失高度证据和未完全应用的 claim 写入回执，`height_coverage.delivery_blocked` 仍为 `false`。直接工具回放中 `generation_status.state` 仍是 `in_progress`，但 `agent_selected` 的 `delivery_selection.json` 已真实持久化；因此这里能证明候选已被 finish 选中，不能把回执外推为整案完成认证。

## 两条有限续改

1. 从 `candidate_02` 把 `W_E2` 窗头从 `2.80 m` 改为 `2.81 m`，生成 `candidate_03`。修改没有新的 claim，工具明确记录 `z` 为 `parameters_without_claims`。原 claim 变成 `partially_satisfied`，图像型高度绑定从 8 个降为 7 个，`W_E2` 变为 `unchecked`。`finish_bim` 仍成功并选中 `candidate_03`，同时在 `adopted_unapplied_claims` 中保留 `claim_0001`，没有静默丢失这一风险。
2. 从 `candidate_02` 只替换一条假设说明，不改 source XY 或洞口高度，生成 `candidate_04`。8 个图像型高度绑定全部保留，`claim_0001` 仍为 `applied_current`。`finish_bim` 成功选中 `candidate_04`，没有未应用 claim。

两条修改在 `revise_bim` 后的普通检查和 finish 前的 `require_all=True` 检查中都得到 `unchanged`。这说明当前装配审查关注房间、邻接、门窗平面位置等源平面内容；本次无 source XY 的有限修改不需要 `review_role_assembly`。高度改动仍由 claim/height coverage 独立暴露，不能用 `unchanged` 解释为高度证据仍有效。

## 重放范围

脚本只从 52,572,388 字节的主运行复制 `candidate_01`、`candidate_02`、claims、图像与立面校准、6 个 reader 任务的真实 record/artifact 及其 11 个引用 blob、plan reader 已接受的 trial source、role operations 和楼层绑定。回放前复制 165 个文件、7,239,016 字节。执行时 `AI_agent/archive/local_backup/c4/e_replay` 的快照为 204 个文件、10,929,379 字节（约 10.42 MiB）；完整逐洞口状态与问题已压缩进 `E_evidence.json`，该临时重放目录由主助手统一清理。

可复跑脚本为 `E_replay.py`；汇总结论在 `E_evidence.json`。脚本每次只清理并重建自己的 `AI_agent/archive/local_backup/c4/e_replay` 目录。

## D 集成意见

主助手已把 blocked 回执的 blocker/coverage 投影和 `assembly_delivery_blocked` 返回补入，并保留由新 assemble 修复旧 blocked 审查的路径。这个处理符合离线核对看到的边界：旧 blocked 不能永久锁死重组，但新候选的阻断原因必须在最终回执中可见，且不能误记为完成。
