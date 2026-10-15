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

代码修复为`c1342bc2`，冻结登记为`8b7126839cf198752376bf1a1e116db063f82154`，runtime v19/domain v80。两轮均使用Go订阅、`claude-haiku-5-5`、single_model、48请求/240工具、无整案时间或tokens硬截止、图片历史3批、64候选，原六PNG与两层范围冷启动，不提供GT、旧候选或开发者几何提示。任务scope依用户新指令优先完成流程、保存可编译草稿并标明暂定假设，独立质量延后；不是原侧栏提示词的严格模型对照。第二轮仅将第一轮的high/32k改为medium/64k。

| 运行 | 思考/输出上限 | 终态 | 请求/响应/工具 | runtime / 含启动收尾 | 供应商实报tokens |
|---|---|---|---|---|---:|
| `haiku55-sm25-20261015-complete-01` | high / 32,000 | incomplete_response，未交付；3次连续输出截断 | 7 / 7（其中3次截断） / 11 | 594.716秒 / 602.016秒 | 461,844 |
| `haiku55-sm25-20261015-complete-02` | medium / 64,000 | completed，task_completed=true，completion_valid=true | 17 / 17 / 20 | 507.494秒 / 518.860秒 | 1,300,297 |

第一轮0 HTTP错误、0重试、0候选。状态快照和签名历史已稳定，但32k输出中思考消耗很大：实报输出122,506，其中thinking 120,797。恢复两次后按既有截断保护停止，没有再把文本收尾标成完成。

第二轮自主执行输入读取、两层试建和返工、整楼装配、立面对照、修订重装配和`finish_bim`。17个响应均正常tool_use，0截断、0 HTTP错误、0重试；5次业务校验拒绝（2次空间种子、3次高度边界）均由模型自行处理。工具调用为inputs 1、view_image 5、get_bim_reference 1、build_plan_bim 2、revise_plan_bim 7、assemble_plan_bim 2、view_elevation_candidate 1、finish_bim 1。最终由模型主动选定`candidate_06`：2层、29空间、190边界、60开口、30连接，源几何检查pass。

第二轮输出72,882，其中供应商thinking 52,914；两轮合计24次真实请求、31次工具、1,762,141实报tokens。均有完整usage；订阅实际费用未知，不等于免费。未切账号、未回退付费provider、未调用DeepSeek。

两个运行结束时，冻结源码、版本登记、配置、原件及输入副本SHA均不变，没有开发者中途提示、改稿或补步骤。独立只读审阅确认第二轮receipt、summary、completion一致，`inputs.json`、`delivery_selection.json`、`delivery.json`、`delivery.html`、`candidate_06/source_model.json`、`candidate_06/viewer.html`六个交付文件SHA全部吻合。原始证据分别位于两个外部run目录下的`run.json`、`preflight.json`、`launch-result.json`、`result-audit.json`及`cold1/receipt.json`、`cold1/events.jsonl`；不将大日志复制入Git。

浏览器实开第二轮交付页和独立查看器，整楼模型及2层/29空间/60开口已显示。控制台捕获一条无来源URL的MutationObserver错误，当前查看器源码未找到此API调用，归因未确认；没有阻止模型渲染，不将本次观察写成控制台零错误。

质量边界：输入共六图，实际直接view_image覆盖1F、2F和North，East/South/West没有直接看图事件；不可写成六图均目视核验。交付保留5个未解决项和暂定开口高度。GT未读，几何保真、5/10/30cm分档、空间用途、遗漏开口和跨次稳定性未评。一次成功交付仅证明这次自主流程跑通。

## 产品配置与发布

新增`product/config.opencode-go-haiku.example.json`，采用成功轮的medium/64k及相同预算，scope改为可配置楼层的通用模板。默认`config.example.json`的6 Sol/high及原Go Kimi示例保持。真实成功来自上述冻结运行；产品示例已复用现有产品配置检查，并核对实际CLI生成的provider/model/effort/output上限，检查通过、0模型请求。版本指纹verify通过。

发布`2d55b764c0b30c5605ae427066431288753a6f5e`已原位更新`C:/Users/Horton/Desktop/Sim BIM Agent`，runtime v19/domain v80。安装自身环境的离线验收44.812秒通过、0真实模型请求；507个文件SHA与发布包全部一致。保留上一版`previous.zip`（4,462,706字节）且SHA核验通过，更新临时目录已清空。审计为`D:/Sim-BIM-Agent/cache/haiku-complete-20261015/product-install-audit.json`。开发库正常提交/推送；原侧栏开发检出和运行证据保留。收尾C盘剩余47.63 GiB、D盘139.30 GiB。
