# 运行底座的按模型请求估算

阶段 2 原先把 JSON 字节数与解码后的图片像素数直接当 token。停止和降级机制本身可用，
但数量比真实输入大几百倍，只能配 1,200 万的假上下文上限。阶段 3 将估算拆成文字、图片、
输出预留和模型上下文四部分，让预算判断使用与服务数量同一量级的值。

## 对外接口

`src.agent_runtime.estimation` 提供：

- `get_model_profile(model, strict=False)`：查模型档案。严格模式拒绝未登记模型；默认模式为旧离线
  桩返回显式的 `unverified_conservative_approximation`，其上下文长度为 `None`，因此不会冒认
  真实模型或使阶段 0–2 的假模型测试失效。
- `estimate_chat_request(body, profile=None, strict=False)`：从最终 Chat Completions 请求体估算。
  返回文字、图片、点估算、安全上界、输出预留、上下文长度、是否装得下、来源、不确定性和逐图
  明细。调用方也能注入审阅过的档案。
- `qwen_image_tokens(width, height, profile)`：公开确定性的 Qwen 图像网格计算，方便入场检查和测试。

`prepare_request` 自动调用估算器。`PreparedRequest.input_token_upper_bound` 和
`token_reservation_estimate` 保持旧接口语义，另增加 `token_estimate`、
`context_window_tokens` 与 `estimate_source`。主循环应把 `estimate_source` 写入预算事件，并以
`input upper bound + output limit + reasoning allowance` 对模型档案的上下文长度做请求前检查。用户另设的本地上限可与
模型上限取较小值；模型档案没有上限时，只能执行显式用户上限，不能虚构一个模型上限。

## 文字与图片算法

文字使用不下载模型权重的近似分词器：Qwen 特殊标记算一个 token，CJK/其他宽字符逐字计数，
ASCII 词按最长八字符一个近似片段，数字按三字符一个，标点逐个计数。模型档案再加由实报校准
的固定模板差值。点估算便于报告偏差；预算上界对文字点估算乘 1.08 并加 12 token。它不是
计费依据，也不应被描述成服务 tokenizer 的精确结果。

图像按官方 processor 配置计算。图片先按 `patch_size × merge_size = 32` 对齐；低于
65,536 像素时放大，高于 16,777,216 像素时缩小；网格数为
`resized_width × resized_height / 32²`，再加 vision 起止两个特殊 token。输入必须是已经捕获的
data URL；远程 URL 会在估算前拒绝，避免“没拿到真实字节却声称已估算”。

## 两个首批档案

`Qwen3.8-27B` 的官方模型卡与 `config.json` 都写明原生上下文 262,144，可扩展到
1,000,000。Paratera 没有公开其具体部署是否启用扩展，因此档案使用 262,144 作为保守真实上限。
来源：<https://huggingface.co/Qwen/Qwen3.8-27B#model-overview>。

`Qwen3.8-Flash` 的官方托管服务写明上下文 1,000,000、最大输入 991,808；公开的
Flash-Next checkpoint 原生为 262,144、可扩展到 1,000,000。Paratera 列出并实际返回
`Qwen3.8-Flash`，但没有提供部署上限证明。档案将原生 262,144、可扩展 1,000,000 和
Paratera endpoint 未核实三项分开保存；请求入场保守使用 262,144，不把官方另一托管端点的
1,000,000 当成 Paratera 已验证上限。来源：<https://docs.qwencloud.com/developer-guides/getting-started/latest-model>
与 <https://huggingface.co/Qwen/Qwen3.8-Flash-Next>。

两个图像档案分别引用官方 `preprocessor_config.json`。Flash 托管版未公开独立 processor，
所以其图片算法以官方 Flash-Next 为最接近的公开来源；Paratera 实报用于部署侧校验，不能证明
未公开的上游实现身份。

## 校准结果与判断影响

本批 12 次请求、0 重试、0 回退，输入 15,674、输出 34。三条文字尺度与三条图片尺度在两个
模型上成对执行。最终点估算最大绝对偏差 9.45%；安全上界 12/12 覆盖实报输入，最小余量
1.14%。图像六条全部逐 token 吻合，既有 sm24 两张真实立面图片也吻合。

档案中的 `1.08 × 文字点估算 + 12 token + 图片估算` 安全边界直接来自上述 12 条：
27B 的 6/6 与 Flash 的 6/6 都覆盖，模型各自最小整体余量为 1.14% 与 1.19%。这是首批校准
边界，不是 tokenizer 证明。角色请求会附带较长且标点密集的工具 schema；本批没有覆盖这种
分布，因此主线程角色小测应把每次实际 schema 请求的估算/实报差继续作为保留验证，若低估就
提高文字安全系数后再跑整案。

这意味着停止判断不再需要千万级假阈值。安全上界仍可能让接近窗口边缘的请求提早停止：当前
校准中短文本的相对余量较大（固定 12 token 所致），中长文本上限余量约 6%–20%；大图请求因
图像部分精确，整体余量约 1%–3%。真实长任务一旦接近上下文边缘，应停止或压缩，不能把点估算
当成保证。校准输入没有覆盖超长工具 schema、几十万 token 历史或多图极限；Paratera
endpoint 的真实最大上下文也没有通过文档或实测核实。这些仍是未核实项，不用撞超长窗口试错
来冒充规格核验。

完整证据与逐条误差在
`AI_agent/logs/experiments/2026-10-02_harness_stage3/calibration/`。每个运行保留完整请求、回包和
usage；汇总不替代原始事件。

## 10-03 角色请求独立核对

三批角色实际发送 42 次，41 次取得服务用量。按各请求发送前保留的估算对比实报，27B 的 19 次输入点估平均绝对偏差 10.53%、最大 14.51%；Flash 的 22 次分别为 9.96%、14.71%。安全上界覆盖 41/41，图像 token 也全部吻合。此结果覆盖了本轮真实工具 schema 和多轮上下文，未出现需要提高安全系数的低估；仍未验证接近窗口上限的超长请求。一次超时用量未知，排除误差统计并保留本地预留，不能按零计算。逐请求记录见 [角色用量](../logs/experiments/2026-10-02_harness_stage3/role_usage.json)。

## GLM-5.3-Flash 档案（R1）

R1 将 Paratera 返回的精确型号 `GLM-5.3-Flash` 加入受审档案。上游配置给出
1,048,576 的原生上下文位置数、14 像素视觉 patch 和 2× 空间合并；Paratera
未公开部署上下文上限，因此运行仍可另设更小的本地上限，不能把上游规格写成
服务承诺。上游模型卡只接受 `low/high/max` 三种 `reasoning_effort`，其他值
回落到 `max`。

Paratera 五次有界校准为两条文字、三种图片尺寸，总计 6,359 token。文字点
估算最大偏差 7.64%；224²、896² 图片与官方网格精确一致，1600×1200 图片的
官方网格高估 84.68%。当前预算估算保留这个保守高估，因为服务端未说明预处理，
不能为了贴合单点引入可能低估长宽图的经验截断。具体原回执、票据和偏差见
`AI_agent/logs/experiments/2026-10-03_runtime_r1/glm_calibration/`。

## R1b：思考余量与超预留结算

模型档案新增 `reasoning_may_exceed_max_tokens`、`reasoning_token_allowance` 和
证据来源；旧档案默认 false／0。GLM 实报显示 max_tokens=8 时 completion
最高为 37，余量设 32；Qwen 两档已知实报未超，余量为 0。请求前预算、上下文
检查、输出降级和有价格时的费用预留均保留这项余量，不修改实际发送的 max_tokens。

请求预留是入场估算，服务端原 usage 是结算证据。token 超预留时完整结算并产生
独立 `budget_overrun` 事件；`BudgetSettlement.token_overrun` 必须精确等于
实际减预留的正差，并由原 usage 证明。根账/子账总量允许保留服务已经实报的超额，
可用余额最低为零，新预留仍逐事件严格核对实际剩余额度，不能借历史超额放大上限。
只有子额度不足时，子任务返回明确停止，根账完整计费，兄弟继续。

恢复先结算已持久响应再准入；已有结算不会重复计费，缺失的超额事件可由原请求和
原用量补回。事件记录的是发送时的档案余量；旧请求未记录则为 0，缺失 request
或 completion usage 时，余量覆盖判断为未知。超额判断不依据之后修改的模型档案。

校准及 Qwen 复核见 [R1b 输出余量证据](../logs/experiments/2026-10-03_runtime_r1/r1b/README.md)。
