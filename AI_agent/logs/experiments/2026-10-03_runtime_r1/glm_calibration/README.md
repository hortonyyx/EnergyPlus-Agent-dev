# GLM-5.3-Flash Paratera 档案校准

本批只校准请求估算，不跑整案。请求前先核仓库已有 Paratera 原始回执：请求与
返回型号均为 `GLM-5.3-Flash`，`reasoning_effort=low` 已被实际服务接受。上游
模型卡说明该参数只支持 `low/high/max`；10-02 Claude Code＋订阅基线所写的
`medium` 不是同一接口参数，不能假称完全对齐。

本次用现有 `QuotaAdapter` 在发出前持久占票，固定 5 张票、0 重试、0 回退；
凭据只从主树 `/workspaces/EnergyPlus-Agent-dev/.env` 读取两个 Paratera 字段，
未保存或输出。五次请求均返回同一型号，总计输入 6,286、输出 73、合计
6,359 token。原请求（图片改为哈希引用）、原响应、票据分别保存在
`responses.json` 与 `quota.jsonl`，汇总在 `summary.json`。

文字输入估算在两个点的最大绝对偏差为 7.64%。官方 14 像素 patch、2× merge
公式在 224² 与 896² 两点精确一致；1600×1200 上 Paratera 实报比官方网格少
1,139 个图片 token，说明服务端还有未公开预处理。为避免预算低估，档案保留
官方网格，因而该点高估 84.68%；五次输入上界均覆盖实报输入。上游配置的
原生上下文为 1,048,576；Paratera 部署上限、缓存和价格仍未核实。

本批没有校准完整请求总量或输出上限。五次请求均设置 `max_tokens=8`，但
`text_control` 实报 completion 24、reasoning 22、`finish_reason=stop`；
`text_long` 实报 completion 37、reasoning 28、`finish_reason=length`。这说明
该端点的思考 token 可使 completion usage 超过所填值；`max_tokens` 至少不能
直接视为含思考在内的总输出硬上限。现有估算器按“输入上界＋8”预留时，五次
总预留依次为 54、4,387、120、1,080、2,507，实际依次为 55、3,793、105、
1,059、1,347；首条已超预留，第二条只是输入侧余量抵消了输出超额。

现有运行时遇到这种超预留会先保存原始响应与 usage，再在结算时以
`token_reservation_exceeded` 停机；响应不会被接受进下一轮，其新工具动作也
不会执行，恢复仍保持致命停机。这个行为保住审计和硬停语义，但在 GLM 思考
开销未单独预留时可能提前终止迁移。首个迁移观察应逐请求保留 completion、
reasoning、可见输出、`finish_reason` 与请求上限，覆盖普通回答和工具调用，再
决定 GLM 专用思考预留；本次数据不能支持完整输出或完整请求安全上界。

校准时为了直接检验“订阅 medium”字符串，送出了 `medium`。服务接收不代表
参数生效：上游规则会把不支持的值落到默认 `max`。后续迁移配置显式使用
`high`，它是支持列表中最接近中档且不会静默落到 `max` 的选择；这项差异必须
随整案结果一并报告。
