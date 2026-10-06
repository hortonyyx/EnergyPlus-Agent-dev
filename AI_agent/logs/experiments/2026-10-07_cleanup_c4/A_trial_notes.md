# C4 A：平面试建反馈去重与真实回放

## 设计

- `PlanTrial.run()`、`self.receipts` 与磁盘 `trial_###.json` 继续保存完整收据，包含逐图来源、原始元数据、差异、精度、拓扑、错误定位和操作审计。
- `PlanTrial.call()` 只在模型边界生成简要投影。逐图只给文件与 SHA-256；`operations` 与 `plan_revision` 改为指向完整收据 JSON 指针及内容哈希的引用；`changes` 和所有可执行诊断照常返回。
- 成功与失败都用同一份投影对象作为文本 JSON 和 `structuredContent`。失败说明放进 `message` 字段，让现有 adapter 从文本开头识别同一 JSON，不再追加第二份；不改共用 adapter。
- 图片 content block 继续逐字节返回。去重只动文字与结构化视图，不重做几何、不改图片。

## 文件

- `src/agent/runtime_roles/trial.py`
- `tests/test_role_trial_feedback.py`
- `AI_agent/logs/experiments/2026-10-07_cleanup_c4/trial_replay.py`
- `AI_agent/logs/experiments/2026-10-07_cleanup_c4/trial_replay.json`
- 本记录

## 验证范围

`trial_replay.py` 从主树只读提取 sm24 run3/run6 的真实 `trial_plan_bim` envelope，在本工作树 `AI_agent/archive/local_backup/c4/trial_replay_cases/` 保存临时副本。每例都用真实完整 receipt 和 image blocks 注入 `PlanTrial.call()`，再走 `convert_tool_result()` 计算模型实际可见字符，并核对图片哈希、完整来源、错误定位、拓扑、差异和精度。

本机正在跑整案，本工作包不自行运行 pytest。只执行上述轻量内存复放；0 次模型请求、0 次几何重跑。

## 复放结果

字符口径分两层记录，不能混用：`tool text` 是 `PlanTrial.call()` 原始 text block；`adapter visible` 是再经 `convert_tool_result()` 后模型实际收到的工具文字。历史失败回执因为 text 前有说明句，adapter 认不出后面的 JSON，又追加一份 `structuredContent`，所以后一口径明显更大。

| 真实事件 | 状态 | 历史 tool text | 历史 adapter visible | 改后 tool text | 改后 adapter visible | adapter visible 降幅 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| run3 event-000456 | 成功 | 59,111 | 59,111 | 6,002 | 6,002 | 89.8% |
| run3 event-000478 | 成功 | 61,604 | 61,604 | 6,894 | 6,894 | 88.8% |
| run3 event-000653 | 成功 | 62,878 | 62,878 | 7,265 | 7,265 | 88.4% |
| run6 event-000537 | 失败 | 13,925 | 27,292 | 6,716 | 6,742 | 75.3% |
| run6 event-000548 | 失败 | 9,099 | 17,706 | 3,855 | 3,881 | 78.1% |
| run6 event-000574 | 失败 | 20,545 | 39,925 | 6,475 | 6,501 | 83.7% |
| run6 event-000585 | 成功 | 57,211 | 57,211 | 5,814 | 5,814 | 89.8% |

三个历史失败事件中，完整 `reason` 在 adapter 可见文字分别出现 4、4、6 次；改后均只出现 1 次。计数高于两次是因为原始图片来源元数据也内嵌整份结果。改后 26 字符的 tool text / adapter visible 差值只是 `Tool error (isError=true):` 标记，不是第二份 JSON。

7 例的实际 image block 哈希全部不变；完整逐图 origin 仍在历史 receipt 中；模型可见的 `returned_images` 均只含文件与 SHA-256。收据里原有的 `reason`、`repair_hint`、`source_findings`、`unhosted_openings`、`loose_partition_ends`、`drawing_differences`、`building_precision`、`topology_issues`、`topology_dividers` 与 `changes` 在适用例中逐字段相同。完整明细见 `trial_replay.json`。
