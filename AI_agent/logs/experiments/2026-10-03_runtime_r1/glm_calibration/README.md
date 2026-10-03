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
直接视为含思考在内的总输出硬上限。R1 原估算器按“输入上界＋8”预留时，五次
总预留依次为 54、4,387、120、1,080、2,507，实际依次为 55、3,793、105、
1,059、1,347；首条已超预留，第二条只是输入侧余量抵消了输出超额。

R1 原运行时会因单次超预留停止；此行为已由 [R1b](../r1b/README.md) 修正。
GLM 档案增加经验思考余量 32，首条新预留为 86；超预留时仍按实报完整结算，
只有根账或子账总额度不够才停止相应范围。32 来自最大已见差值 29，不是服务
硬上限。这里的原始响应、票据与 summary 保持 R1 原字节和原 54 等历史预留。
`verify_calibration.py` 离线读取 `fcbbda75` 档案重建旧估算，核验输出与原 summary
逐字节相同；本次不新增校准请求。

校准时为了直接检验“订阅 medium”字符串，送出了 `medium`。服务接收不代表
参数生效：上游规则会把不支持的值落到默认 `max`。后续迁移配置显式使用
`high`，它是支持列表中最接近中档且不会静默落到 `max` 的选择；这项差异必须
随整案结果一并报告。
