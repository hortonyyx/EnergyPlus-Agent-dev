# 阶段 1：七份历史记录分层重放

本报告把附件哈希、确定性工具重放、跨版本语义比较分开。表中的 `exact` 只表示保存的建模声明在本报告记录的当前代码快照下逐字段重建一致；不表示重新调用模型，也不表示整案质量正确。

run99 与 run100 保存了 44 个实现文件、逐文件哈希和运行时快照，可对保存的确定性工具层做同快照重建；其余五份没有同等代码快照，不能把当前代码的 `exact` 改称同版本复现。两份快照都未固定 Python 依赖锁，这一限制保留。

当前重放代码仓库提交：`f15111d0b1a79ead1ff452a7ec7ca0cf3f2c3f6c`；具体重放文件和依赖锁哈希见 `replay_report.json`。

| 样本 | 归档文件 | Git 完整副本 | 当前代码交付重建 | 装配重建 | 历史工具快照 | 候选版本变化 |
|---|---:|---|---|---|---|---:|
| run99 | 253 | complete_in_git_head | semantic_match | exact | exact_for_archived_tool_snapshot | 2 |
| run100 | 198 | complete_in_git_head | exact | not_applicable | exact_for_archived_tool_snapshot | 1 |
| opus_sm21 | 298 | complete_in_git_head | exact | exact | not_verifiable | 2 |
| opus_sm24 | 160 | complete_in_git_head | exact | not_applicable | not_verifiable | 0 |
| opus_sm25 | 264 | complete_in_git_head | exact | exact | not_verifiable | 2 |
| sol_61 | 525 | complete_in_git_head | semantic_match | not_applicable | not_verifiable | 3 |
| sol_6 | 877 | complete_in_git_head | semantic_match | not_applicable | not_verifiable | 3 |

## run99

交付候选 `candidate_05`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`semantic_match`；装配重放：`exact`；历史工具快照：`exact_for_archived_tool_snapshot`。

缺口：

- 未单独保存服务端最终请求体和原始 MCP 返回字节；现有材料是 CLI 转换后的传输记录。
- 思考正文不可得；签名块和估算 token 数不能还原思考内容。
- 本运行的 44 个实现文件全部匹配归档哈希清单。用归档命名模块以及哈希匹配的导出器和源构建器重放保存 proposal，可逐字段复现 source_model.json 与 display_geometry.json。这证明的是保存的确定性工具切片；没有重放模型对话，且运行当时未归档依赖锁。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

当前版本重建的顶层差异字段：`public_names`, `source_model_sha256`。对象、几何、宿主、连通的逐项差异见 `replay_report.json`。

当前导出器在提交 2b83a7592a7a7ecd9b990aa3182b0b857992156e 后改用源楼层的显式名称或 ID；保存产物使用顺序 F# 显示名。最终 proposal 不含 public_names，而候选修订会保留源候选已有的命名映射，所以重建 proposal 会按所选导出器重新命名；差异不是漏跑 finish_bim。public_names 因而变化，覆盖完整源载荷的 source_model_sha256 随之变化。对象、几何、宿主、连通差异仍在下方独立逐项列出。
公开名称映射变化：新增 0，删除 0，改名 16；示例和完整键清单在 `replay_report.json`。

旧命名算法兼容重建：`exact`（`this_run_archived_naming_plus_current_hash-matched_exporter_source_builder`）。这逐字段验证了名称映射与其派生源哈希可重建；只有本运行自己的完整快照才能据此标为同快照工具重建。

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 58/59/0 | 58/59/6 | 50/51/6 | 6/8 |
| candidate_02→candidate_03 | 128/63/0 | 128/63/0 | 113/56/0 | 14/6 |
| candidate_03→candidate_04 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_04→candidate_05 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## run100

交付候选 `candidate_03`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`exact`；装配重放：`not_applicable`；历史工具快照：`exact_for_archived_tool_snapshot`。

缺口：

- 未单独保存服务端最终请求体和原始 MCP 返回字节；现有材料是 CLI 转换后的传输记录。
- 思考正文不可得；签名块和估算 token 数不能还原思考内容。
- 本运行的 44 个实现文件全部匹配归档哈希清单。用归档命名模块以及哈希匹配的导出器和源构建器重放保存 proposal，可逐字段复现 source_model.json 与 display_geometry.json。这证明的是保存的确定性工具切片；没有重放模型对话，且运行当时未归档依赖锁。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 25/9/0 | 25/9/2 | 22/8/6 | 5/3 |
| candidate_02→candidate_03 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## opus_sm21

交付候选 `candidate_04`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`exact`；装配重放：`exact`；历史工具快照：`not_verifiable`。

缺口：

- dev_calls.jsonl 指向的原始桥接调用目录未随历史目录归档。
- tools.jsonl 只有返回侧审计行，缺完整调用参数、模型实际所见传输、模型文字、思考和用量。
- 开发模型桥接调用没有服务端实际型号回执。
- 该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使能逐字节复现，也不能证明它就是运行时的精确版本。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 11/12/0 | 11/12/53 | 9/10/0 | 1/3 |
| candidate_02→candidate_03 | 128/63/0 | 128/63/0 | 113/56/0 | 14/6 |
| candidate_03→candidate_04 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## opus_sm24

交付候选 `candidate_02`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`exact`；装配重放：`not_applicable`；历史工具快照：`not_verifiable`。

缺口：

- dev_calls.jsonl 指向的原始桥接调用目录未随历史目录归档。
- tools.jsonl 只有返回侧审计行，缺完整调用参数、模型实际所见传输、模型文字、思考和用量。
- 开发模型桥接调用没有服务端实际型号回执。
- 该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使能逐字节复现，也不能证明它就是运行时的精确版本。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## opus_sm25

交付候选 `candidate_04`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`exact`；装配重放：`exact`；历史工具快照：`not_verifiable`。

缺口：

- dev_calls.jsonl 指向的原始桥接调用目录未随历史目录归档。
- tools.jsonl 只有返回侧审计行，缺完整调用参数、模型实际所见传输、模型文字、思考和用量。
- 开发模型桥接调用没有服务端实际型号回执。
- 该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使能逐字节复现，也不能证明它就是运行时的精确版本。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 76/74/0 | 76/74/66 | 66/65/13 | 9/11 |
| candidate_02→candidate_03 | 281/141/0 | 281/141/0 | 251/126/0 | 30/14 |
| candidate_03→candidate_04 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## sol_61

交付候选 `candidate_04`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`semantic_match`；装配重放：`not_applicable`；历史工具快照：`not_verifiable`。

缺口：

- 协作桥接器只保留请求的型号覆盖，没有服务端实际型号、token 或账单回执。
- 未归档模型对话文字、思考以及服务端最终请求和响应。
- 逐步 request/reply JSON 保留了部分桥接操作，但不能证明模型实际所见传输完全相同。
- 该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使能逐字节复现，也不能证明它就是运行时的精确版本。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

当前版本重建的顶层差异字段：`public_names`, `source_model_sha256`。对象、几何、宿主、连通的逐项差异见 `replay_report.json`。

当前导出器在提交 2b83a7592a7a7ecd9b990aa3182b0b857992156e 后改用源楼层的显式名称或 ID；保存产物使用顺序 F# 显示名。最终 proposal 不含 public_names，而候选修订会保留源候选已有的命名映射，所以重建 proposal 会按所选导出器重新命名；差异不是漏跑 finish_bim。public_names 因而变化，覆盖完整源载荷的 source_model_sha256 随之变化。对象、几何、宿主、连通差异仍在下方独立逐项列出。
公开名称映射变化：新增 0，删除 0，改名 211；示例和完整键清单在 `replay_report.json`。

旧命名算法兼容重建：`exact`（`run99_archived_pre-change_naming_module_compatibility_only`）。这逐字段验证了名称映射与其派生源哈希可重建；只有本运行自己的完整快照才能据此标为同快照工具重建。

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 8/0/0 | 8/0/6 | 8/0/5 | 1/0 |
| candidate_02→candidate_03 | 13/1/0 | 13/1/20 | 11/1/1 | 2/2 |
| candidate_03→candidate_04 | 1/0/0 | 1/0/68 | 1/0/0 | 1/0 |

## sol_6

交付候选 `candidate_11`；附件归档：`hashed_complete_for_defined_archive_set`；交付重放：`semantic_match`；装配重放：`not_applicable`；历史工具快照：`not_verifiable`。

缺口：

- 协作桥接器只保留请求的型号覆盖，没有服务端实际型号、token 或账单回执。
- 未归档模型对话文字、思考以及服务端最终请求和响应。
- 逐步 request/reply JSON 保留了部分桥接操作，但不能证明模型实际所见传输完全相同。
- 该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使能逐字节复现，也不能证明它就是运行时的精确版本。

非确定或未核实字段：

- 事件时间戳、耗时和剩余时间
- 没有服务端回执时的服务商/实际型号
- 历史未提供的 token、费用和额度窗口
- 历史未捕获的模型文字与思考
- 渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）

当前版本重建的顶层差异字段：`public_names`, `source_model_sha256`。对象、几何、宿主、连通的逐项差异见 `replay_report.json`。

当前导出器在提交 2b83a7592a7a7ecd9b990aa3182b0b857992156e 后改用源楼层的显式名称或 ID；保存产物使用顺序 F# 显示名。最终 proposal 不含 public_names，而候选修订会保留源候选已有的命名映射，所以重建 proposal 会按所选导出器重新命名；差异不是漏跑 finish_bim。public_names 因而变化，覆盖完整源载荷的 source_model_sha256 随之变化。对象、几何、宿主、连通差异仍在下方独立逐项列出。
公开名称映射变化：新增 0，删除 0，改名 222；示例和完整键清单在 `replay_report.json`。

旧命名算法兼容重建：`exact`（`run99_archived_pre-change_naming_module_compatibility_only`）。这逐字段验证了名称映射与其派生源哈希可重建；只有本运行自己的完整快照才能据此标为同快照工具重建。

保存候选的跨版本比较：

| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |
|---|---:|---:|---:|---:|
| candidate_01→candidate_02 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_02→candidate_03 | 16/0/0 | 16/0/16 | 12/0/0 | 0/0 |
| candidate_03→candidate_04 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_04→candidate_05 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_05→candidate_06 | 110/0/0 | 110/0/94 | 110/0/62 | 0/0 |
| candidate_06→candidate_07 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_07→candidate_08 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_08→candidate_09 | 6/0/0 | 6/0/15 | 6/0/6 | 4/0 |
| candidate_09→candidate_10 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| candidate_10→candidate_11 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |

## 结论边界

2,575 个原始文件均以逐文件 Git blob 对照证明存在于报告所列 HEAD，清单不仅是指向本机目录的哈希。换机后检出该提交即可按 repository_path、git_blob_oid 和 SHA-256 复核。

本次没有模型调用。当前代码的确定性重放只覆盖保存声明可重建的源 BIM 和完整保存的平面装配；桥接调用参数或模型上下文缺失的步骤未重做。候选间比较是保存源 BIM 的对象、几何、宿主、连通差异，不判断这些差异是否符合原图或用户意图。当前重建中的公开名称变化发生在proposal 导出重新生成命名映射时，不是遗漏了 finish_bim；保存的候选修订会保留其原有命名映射。
