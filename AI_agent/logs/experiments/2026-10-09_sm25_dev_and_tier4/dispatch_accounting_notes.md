# Stage 2 人工调度账本说明

核对来源为终态 `final_runtime_accounting.json`、根 `receipt.json`、完整 `events.jsonl` 与 `manual_receipts/`；未读取 GT。终态为 `completed`，交付 `candidate_10`，但 `source_fidelity=not_evaluated`、`evaluation_status=not_run`、`quality_passed=null`，不能据此声称质量通过。

总计 98 次模型请求均有响应，无 pending/failed；prompt 4,933,811，缓存 3,740,544（75.81%，是 prompt 子集，不能重复相加），output 325,190，provider total 5,259,001。reported image 为 667,777；预算计费 token 5,926,778，另计了已结算的图像收费行。运行时结算估价 8.7029404 CNY，属于配置费率估算，不是供应商账单。settlement mismatch、残尾、坏行、capture error 均为 0。

| 任务 | 请求 | 任务/模型/工具秒 | prompt / cache（率） | output / reported image | CNY | 工具错误 |
|---|---:|---:|---:|---:|---:|---:|
| plan_f1 | 15 | 1901.412 / 1801.985 / 9.865 | 1,020,539 / 650,880（63.78%） | 112,610 / 149,480 | 3.2992650 | 4 |
| plan_f2 | 15 | 1549.877 / 1502.641 / 4.846 | 1,024,263 / 654,336（63.88%） | 80,289 / 212,470 | 3.1032606 | 5 |
| plan_f1_rework | 11 | 471.532 / 389.190 / 9.859 | 878,965 / 729,344（82.98%） | 18,511 / 34,994 | 1.2135834 | 3 |
| elevation_north | 12 | 452.936 / 435.158 / 2.655 | 437,518 / 372,992（85.25%） | 27,021 / 51,363 | 0.2342512 | 0 |
| elevation_south | 9 | 249.898 / 240.872 / 2.531 | 219,508 / 173,824（79.19%） | 13,642 / 52,486 | 0.1564784 | 0 |
| elevation_east | 14 | 463.445 / 446.367 / 0.906 | 517,807 / 449,792（86.86%） | 27,512 / 69,196 | 0.2647262 | 0 |
| elevation_west | 14 | 550.500 / 525.171 / 4.557 | 500,715 / 431,872（86.25%） | 30,857 / 73,216 | 0.2778172 | 0 |
| elevation_east_rework | 8 | 384.102 / 325.033 / 7.265 | 334,496 / 277,504（82.96%） | 14,748 / 24,572 | 0.1535584 | 0 |

模型请求累计 5,666.417 秒，大于 2,731.985 秒墙钟，因为 readers 并行，不能相加解释为实际耗时。181/181 个 reader 工具执行均有 duration，总和 42.484 秒（plan 24.570、elevation 17.914），也可能并行。各 reader 的任务时长合计 6,023.703 秒；扣除模型和已观测工具后剩余 314.802 个“任务秒”，包含排队、准备、校验、写盘等未细分本地时间，并非根流程墙钟开销。

根 receipt 的 `elapsed_seconds=2728.486` 在 `finalize_building` 前取样；root stop 位于初始化后 2731.985 秒，差 3.499 秒。其中约 2.542 秒发生在取样至 receipt 时间戳，约 0.957 秒发生在 receipt 时间戳至 stop 事件，覆盖交付生成及 stop 前持久化；stop 后的 aggregate、summary、behaviour 写入不在该差值内。

`manual_receipts/` 有 2 次 delegate 和 8 次成功的人工协调工具调用：2 次 `assemble_from_readers`、1 次 `check_openings`、4 次 `view_elevation_candidate`、1 次 `finish_bim`，全部 `isError=false`。这些 receipt 没有执行时长字段，只能可靠计数。`coordinator_model_requests=0` 仅表示项目运行时没有 coordinator 模型请求；外部根 GPT/Codex 调度员不在该账本中，不能表述为“根 GPT 用量为 0”。
