# R1 D：实测准备交付

本项已完成 GLM-5.3-Flash 的 Paratera 模型档案、5 次估算校准和两份可直接
启动的整案配置；没有运行整案，没有调用 DeepSeek，也没有把 GLM 订阅接入
新底座。真实整案仍保留项目批准门。

## GLM 档案与校准

请求前核对了 10-02 Paratera 原始回执：请求／返回型号均为
`GLM-5.3-Flash`，并核对上游模型卡与配置。上游原生上下文为 1,048,576，
视觉配置为 14 像素 patch、2× merge；Paratera 部署上限、缓存和价格未核实。
上游 `reasoning_effort` 只支持 `low/high/max`，不支持订阅基线记录的
`medium`。

校准用已有 `QuotaAdapter` 请求前占票，限额 5，实际 5，0 重试、0 回退。
凭据只读主树 `.env` 两个字段，未输出。实报如下：

| 题 | 输入 | 输出 | 合计 | 点估 | 输入安全上界 | 输入上界余量 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 短文字 | 31 | 24 | 55 | 31 | 46 | 48.39% |
| 长文字 | 3,756 | 37 | 3,793 | 4,043 | 4,379 | 16.59% |
| 224×224 图 | 97 | 8 | 105 | 97 | 112 | 15.46% |
| 896×896 图 | 1,057 | 2 | 1,059 | 1,057 | 1,072 | 1.42% |
| 1600×1200 图 | 1,345 | 2 | 1,347 | 2,484 | 2,499 | 85.80% |

总计输入 6,286、输出 73、合计 6,359 token，金额未核实。表中五条上界只
覆盖实报输入，不能解释为完整请求总 token 上界。五次请求都写了
`max_tokens=8`，但短文字和长文字分别实报 24（其中思考 22）和 37（其中思考
28）个 completion token；长文字还以 `finish_reason=length` 截断。由此可知，
Paratera 上该字段至少不能直接当作包含思考 token 的 completion usage 总上限。
按现有运行时的“输入上界＋所填输出上限”口径，五次完整请求预留分别为 54、
4,387、120、1,080、2,507 token；短文字实际 55，已超预留 1 token。长文字虽
因输入侧高估而偶然落在总预留内，也不能据此认为输出估算已经校准。

最后一条输入高估较大，原因是 Paratera 未公开的图片预处理；档案保留
官方 patch 网格，避免按一个合成图经验截断后低估其他长宽比图片。本批没有
再留票覆盖真实工具 catalog 长上下文，这是校准覆盖限制；10-02 Qwen 校准与
角色实测覆盖过同一冻结 catalog，但不能替代 GLM 的 tokenizer 实报。

现有运行时会先按输入上界和请求中的输出上限持久预留，再用服务端
`total_tokens` 结算。若总实报超过该次预留，原始模型响应和 usage 已先持久保存，
随后以 `token_reservation_exceeded` 停机，不接受该响应进入下一轮，也不执行它
新提出的工具动作；恢复时仍识别为致命超预留而不会继续。因此这项缺口不会被
静默吞掉，但可能让迁移试跑在首个短上下文请求就保守停机。

待迁移观察点是逐请求记录 `max_tokens`、completion、reasoning、可见输出和
`finish_reason`，分别核对普通回答与工具调用，并据此为 GLM 建立独立的思考
预留；在有实证前不能以 16,384 的配置输出值宣称单次完整输出或总请求已经
封顶。全程 token 预计和 400 万硬停仍是规划值，不是本次五点校准证明的安全
上界。

原请求（图像改为哈希引用）、完整响应、持久票据和计算结果位于
[`glm_calibration/`](glm_calibration/README.md)。

## 迁移对照配置

[`migration_sm24_glm_paratera.json`](configs/migration_sm24_glm_paratera.json)
固定：Paratera `GLM-5.3-Flash` 单工作模型、sm24 五张原图、3000 秒、24 候选、
60 请求／120 工具／400 万 token 硬停、无委派、重试或回退。任务正文与
10-02 基线 `preflight_glm_sm24.json.prompt` 逐字相同，SHA-256 为
`a05ae6d543fdd14076a46859c8b4e2fa781f560a0ddfcce6d1948597632fa795`；冻结
绘图指引 SHA-256 为
`9ca4fdcda8b446a58fd97466f4849628a54e6a2966b4db480407bb7131516b34`。
五张输入图哈希也与基线逐一相同；字节仍引用仓库原件，没有重复打包。

订阅基线为 Claude Code `effort=medium`，没有该客户端向上游转换后的参数回执；
Paratera 公开参数不存在 medium。本配置显式用受支持的 `high`，避免无效值
静默落到 `max`。订阅 temperature 未报告；新配置依上游评测值固定 1.0。
这是已知对照差异。预计约 45 请求、264 万 provider token，依据基线 44 轮及
2,640,187 个输入＋缓存读＋输出 token；硬停 60／400 万。

离线检查命令：

```bash
PYTHONPATH=$PWD python -m src.agent.runtime_r1_preparation check \
  AI_agent/logs/experiments/2026-10-03_runtime_r1/configs/migration_sm24_glm_paratera.json
```

获批后的直接启动命令只需把 `check` 改为
`launch ... --case sm24_glm_paratera`。本包未执行 launch。

## 首批整案配置

[`first_full_cases.json`](configs/first_full_cases.json) 保持阶段 3 方案：Astra／
Codex 作外层协调，Qwen3.8-27B 经 Paratera 作只读局部观察；sm24 与 Voimatalo
各一次独立冷启动、最多三轮有依据修订、每子任务 3 请求／6 工具／10 万 token／
600 秒，无自动重试或换模。两例均以 6600 秒（110 分钟）硬停，且分别使用
持久票据；失败或超时也占票。外层 Codex 请求和 token 仍明确为未获取。

| 案例 | 预计请求／token | 硬停请求／token | 输入 |
| --- | ---: | ---: | --- |
| sm24 | 24／360,000 | 30／500,000 | 仓库原五图 |
| Voimatalo | 32／520,000 | 40／750,000 | 仓库原单体 GLB |

预计值按阶段 3 角色小测每请求约 1.38 万 token 再结合案例复杂度规划；上限照
原方案，实际以统一日志的 Paratera usage 为准。Voimatalo 原 GLB SHA-256 为
`9a73349d9d024a128160e8771d4bccba79b6e3462ae4f35d787f35f4ddf337fc`，
未重复打包。配置中的 `outer_coordinator_instruction` 需在启动 MCP 时原样交给
外层协调者。

两份配置均经 `runtime_r1_preparation check` 与 `command` 离线检查；命令可解析
到当前树、输入存在、模型档案受审、时间和请求上限固定、凭据只引用主树 `.env`。
实现和使用边界见
[`runtime_full_case_preparation.md`](../../../design/runtime_full_case_preparation.md)。

本项开发代理为 `gpt-5.6-sol`／high；协作接口未提供开发 token 用量，记为未知。
