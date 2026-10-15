# Haiku 整案运行修复

## 范围与已确认原因

用户先要求排查侧栏 Haiku 5.5 无法跑完整案，随后授权“先修复到能跑完整案吧，先不管结果怎么样”。本轮以相同 sm25 六图、自主建两层源 BIM、装配、保存查看器并正式 finish 为验收；独立几何/GT质量暂不评价。默认产品 gpt-6-sol/high 保持。

原始运行保留在 `D:/Sim-BIM-Agent/runs/haiku55-sm25-20261015-side-01`、`side-02`（完整目录名均有相同日期前缀）以及 `haiku55-sm25-20261015-fixed-01`。前两轮第三请求 HTTP 400；侧栏修复后的第三轮14请求、31工具、833.922秒，只读图和量测，没有保存候选。末轮输出截断后的恢复提示允许简短回答，模型诚实报告未建模，但 runtime 把普通文字收尾记为 completed，summary 同时误报 task_completed。

另一个确定问题是 ContextManager 每次将相同 Current runtime state 移到新末尾，改变已签名 thinking 的原始消息前缀。第三轮第3至14请求仅保留最早一轮 thinking；状态内容本身没变。第9至13请求还存在正常图片轮换。上下文丢失已证实，对整体建筑推理的影响仍需真实运行验证，不能只凭接口修复推断模型能力。

## 实现

- 合入侧栏 `673e2469f83acfb69a91d1c1a4ace3af6dd26b06` 的 Go Haiku Messages 签名前缀兜底：只移除已不匹配原请求前缀的完整 thinking 块，保留原始日志、普通文本、工具和图片及转换审计。
- Go Haiku 的 token 上下文启用 append_state_history。实际请求中的状态快照在响应入历史前固化，变化才追加；纯投影/估算不写历史，空状态明确清除旧约束，压缩后重新提供当前状态，恢复按日志幂等重建。
- 有 domain_completion 的 runtime 必须取得域完成证据；普通文字改为中间状态，按原预算最多再续行两次，第三次连续无工具回复以 domain_completion_unmet 停止。通用与只读文字任务保持原行为。截断后的域任务继续工具步骤；摘要请求仍遵守摘要契约。
- BIM task_completed 同时要求 runtime completed、completion 记录、交付哈希复核通过与 complete_building。兜底候选与部分楼层不冒充自主完成。
- 图片历史仍为最近3批，真实压缩/图片替换仍可触发签名兜底；预算、并发、共享记账和恢复保护保留。没有变更建筑规则、几何 kernel、GT 或产品默认模型。

## 离线与独立审阅

| 范围 | 结果 | 耗时 | 真实模型调用 |
|---|---|---:|---:|
| context、Go、thinking binding（含中断恢复/图片轮换/状态清空） | 50通过 | 17.64秒 | 0 |
| 完成契约、文字续行、预算、截断、恢复专项 | 37通过 | 14.64秒 | 0 |
| R3真实本地工具、Anthropic、角色上下文 | 首批46通过，2项Windows测试日志默认GBK读取失败；显式UTF-8修正后2项复验通过，有效48项通过 | 219.43＋25.55秒 | 0 |
| 独立组合检查：签名历史＋状态＋文字续行，正常/after_response恢复 | 2通过 | 0.422/0.422秒 | 0 |

独立审阅未发现剩余P1/P2；其边界是代码与离线行为。最初未登记时23个R3拒绝冻结属预期保护；使用待登记指纹后实际工具已运行。另有3个既有generic用例在原HEAD独立复现同样失败（asyncio包装StopIteration、两项context终态预期），不归为本轮回归，不据此声称全量测试绿色。

证据：`D:/Sim-BIM-Agent/cache/haiku-complete-context-20261015-01.xml`、`haiku-complete-domain-20261015-01.xml`、`haiku-complete-domain-20261015-02.xml`；完成专项在 `cache/haiku-completion-fix-20261015/b73fa154824f/results.xml`；独立组合在 `cache/haiku-review-cross-zdbezzy6/review-results.json`。所有缓存位于D盘，无新付费探针。

## 真实整案配置与验收记录

准备运行 `haiku55-sm25-20261015-complete-01`：Go订阅、claude-haiku-5-5/high、single_model、32,000输出tokens、48请求/240工具、无整案时间或tokens硬截止、图片历史3批、64候选。仍用原六PNG与两层范围，冷启动，不提供GT、旧候选或开发者几何提示。

任务scope依用户新指令明确优先完成流程、保存可编译草稿并标明暂定假设，独立质量延后；因此不是原提示词的严格模型对照。代码、版本、配置、六图在启动时封存，结束后核验。真实结果与固定桌面发布在验证后补充。
