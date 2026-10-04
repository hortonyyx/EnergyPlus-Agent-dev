# A1-R 交付记录（进行中）

派工依据：[brief.md](brief.md) 与统一 Agent 验收记录 A1-R。开始于 2026-10-04 14:38 UTC，计划约 110 分钟内交付。

## 范围与执行边界

仅在 `dev/astra-a1r-20261004`、当前 A1-R 工作树修改并小步提交；不合入、不推送，不改主工作树与 A1-T。优先完整完成 A，再做 B。模型调用上限为 GLM 订阅 6 次小请求，Paratera／DeepSeek／整案均为 0。检查使用本树 `PYTHONPATH`、树内临时目录及 `pytest -n 2 -s`。

## 验收进度

| 项 | 当前状态与待交内容 |
|---|---|
| A 图片引用存档 | 已完成实现与定向检查；42/42 历史请求逐字节重建通过，57 项相关检查通过；完整联合检查见 E。 |
| B Anthropic 订阅线路 | 已实现、提交 `eb34f968`；新增协议的 17 项定向检查通过。 |
| C 订阅小测 | 4/6 次全部完成；工具／图片／思考与签名接续／截断恢复／第二轮缓存读均有实际证据。 |
| D sm24 配置 | 已准备并 check-only 通过，未运行；6000 秒、节点回归同任务正文、medium。 |
| E 检查 | 全部联合检查进行中；阶段 0–3、R1–R3、C1 及新增反例。R3 三例离线核对已通过并新增协议设置记录。 |

## 已确认的协议差异

抓包的 `thinking` 实际是 `{"type":"adaptive","display":"omitted"}`，并有 `context_management.edits=[{"type":"clear_thinking_20251015","keep":"all"}]`；系统提示最后两块及最新消息末块有 ephemeral 缓存标记。实现将明确保留这些字段与标记策略，非流式差异单列。尚未把本地实现或接口可用等同整案提速／质量成立。

## 检查、提交与用量

报告初稿已先提交。当前 GLM 4，Paratera 0，DeepSeek 0，整案 0；GLM 四次共报告 8,090 tokens（输入 4,165、缓存读 3,712、输出 213），未报告缓存写入。订阅没有按 token 计的货币估价。图片保守估计另计 54 tokens，预算口径合计 8,144；这与服务端报告值分开列出。

## A 阶段结果（14:52 UTC 更新）

- 实现提交 `869707cc`，初稿 `a75bda84`。新 `image_references` 捕获保存正文模板、图片 JSON 位置、原始图片哈希和发送正文哈希；非规范但可解码的 base64 拼写也完整保留。发送前重建比对实际 wire bytes，不改变 OpenAI 线路的发送内容。
- [历史重放证据](image_storage_replay.json)：42/42 请求重建字节与原请求附件一致；发送图片逐一对上正文，来源图与发送图分别校验。原历史中部分工具视图与来源整图不同，本包没有改其字节，也未强行将两种哈希说成相同。
- 逻辑文件体积 **144,945,549 → 76,888,685 字节（−46.95%）**，包含行为报告 **35,867,439 → 9,241,475 字节**。这是离线转换估算，不是新整案。保留了其他产物和仍被检查点／来源引用的 26 个旧附件；只移除 140 个已无引用的旧捕获附件。
- [定向检查日志](validation_a.log)：57 passed（251.68 秒），涵盖新引用反例、原图片字节、单角色工具往返、上下文恢复、真实冻结工具离线入口、订阅旧线路、行为记录读取。
- 原发送字节断言改为 `capture_bytes(final_request_body)`，继续对每份实际发送字节作全等比较；原始图片与发送图片相等的专门检查保持。准备但未发送的工具结果仍严格要求 `prepared` 且没有 presentation 事件，仅存储形状改为图片引用。
- 剩余体积含完整模型产物、检查点及其他历史记录；本包未做通用垃圾回收或更改源图／源 BIM。

## B：新线路与协议边界

新增 `glm-subscription-anthropic`；只读调用者显式指定凭据文件的 `GLM_API_KEY`、`GLM_ANTHROPIC_BASE_URL`，不从进程环境补值。原 OpenAI 兼容线路仍保留。Messages URL、版本及 beta header 按 [request_02 抓包](../2026-10-03_migration_comparison/evidence/claude_code_request_capture/request_02.json) 对齐；认证头不进入请求证据。

- 默认 `max_tokens=32000`、adaptive、display omitted、effort medium；effort 可配置。系统提示最后两个实质块（本 Agent 只有一个操作指南块）及最新消息末块设置 ephemeral 缓存。保留 `clear_thinking_20251015 / keep: all`。
- 原样保存并在下一轮回传原生思考块及签名；不把签名或 redacted opaque 块当作公开思考文字。工具调用、错误工具结果、图片转换到 Messages，并记录实际发送块及其来源。
- `max_tokens` 对接 R2：整批被截断的工具调用均不执行，不把截断半句或思考块带进恢复请求；补救与计数沿用已有规则，包括崩溃后恢复。
- C1 原有失败分类继续使用，支持 Anthropic 错误正文；用量合并输入、缓存读、缓存写、输出，并保留缺失值。嵌套缓存写入时长明细不重复累加。
- 原生返回块、签名、坏工具批次、截断、失败分类、凭据隔离、缓存计数及恢复共 17 项定向检查通过；最终联合检查另列于 E。
- [多工具顺序复核](native_tool_order_check.json)：实际离线请求为 `tool_result, tool_result, text, image`。原底座本就将工具结果集中在前，转换保留此顺序，符合 [Messages 工具结果要求](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)，没有为此增添另一套排序逻辑。

与 Claude Code 的可见差异已写入 [R3 核对](runner_parity.json)：本线路非流式；不复制 Claude Code 私有系统包装、工具命名空间、客户端身份和设备会话元数据；工具图片紧随工具结果、同属用户消息，未嵌套进结果；保留自有底座原先按 token 阈值压缩上下文的机制。操作指南、工具定义、任务正文三例仍一致。服务端没有回报已应用参数，所以记录为“发送设置匹配，实际参数效果未经服务端证明”；本包不据此声称整案速度或质量已改善。

## C：四次订阅小测及可复核证据

| 次序 | 目的与实际结果 | 服务端用量（输入／缓存读／输出） |
|---|---|---|
| 1 | 红色图片 + 计算，模型返回带签名的思考块并调用一次工具，记录 red、941 | 3,765／0／45 |
| 2 | 原样带回前轮思考块和签名，工具返回蓝图；模型正确报告红／蓝、941，缓存读取非零 | 195／3,712／23 |
| 3 | 输出上限 128，要求长文，实际 `stop_reason=max_tokens` | 84／0／128 |
| 4 | R2 补救正常返回 `OK`，没有执行任何半截工具调用 | 121／0／17 |

两组均完成，无额外重试。缓存写入计数服务未提供，实际汇总留空；写入字段的累计与避免重复计算另由离线反例覆盖。工具／图片组使用约 3,700 token 的固定无害前缀以实际观察缓存，没有加载 BIM 服务或建筑任务。截断组显式用 128 上限，仅用于补救小测。

- [工具／图片组摘要](smoke_roundtrip.json)、[截断组摘要](smoke_truncation.json)。
- [原始证据压缩包](subscription_smoke_evidence.tar.gz)、[80 个文件哈希清单](subscription_smoke_manifest.json)，52,818 字节。两份与仓库 `uv.lock` 完全相同的附件由清单指向已存在文件，不重复装包；其余附件、事件、收据及请求配额账全部保留。归档前确认不含所用凭据值。
- [恢复校验](smoke_verification.json)：从压缩包在新目录恢复全部 80 个文件；四份请求发送哈希全部一致，三次图片出现均与原图字节相同；实际第一轮思考块和签名与第二轮请求完全相同；两组事件契约、行为记录读取通过。此校验额外模型请求为 0。
- `subscription_smoke.py` 有持久化六次总请求上限，并拒绝覆盖已有输出；不要把本报告的复核命令误作再次调用许可。

## D：只准备 sm24

[sm24_anthropic.json](configs/sm24_anthropic.json) 仅准备，审批字段明确未批准运行。6000 秒、输出 32000、medium、新线路。任务正文与节点回归原配置逐字相同，SHA-256 为 `381c609265ee48aa866d1b232c533fd909e88199f933596a72d93320ab45a93d`；[check-only](config_check.json) 为 ready。本轮没有启动该配置。

## E：联合检查（进行中）

使用 `validate.py short`、`long`、`frozen` 顺序执行；`PYTHONPATH` 指向当前工作树、`PYTHONDONTWRITEBYTECODE=1`、树内 TMPDIR、pytest 显式 `-n 2 -s`。保存日志、JUnit、检查期间源码哈希，全部离线。R3 `compare_runners.py` 核对 sm24／sm25／sm21，三例通过，模型请求 0；新增“协议与思考设置”对照。

短程联合检查已 **387 passed**（555.30 秒）；[完整命令与源码哈希](validation/short.json)。因修改行为记录读取，额外补跑 `test_behaviour_c2.py`，**2 passed**（6.56 秒）。长任务与冻结工具长回放尚在执行。

早期失败及修复后的定向日志保存在 `validation/test-*.log.gz`：A 初版严格 tuple 反序列化、共享对象引用和旧存储形状断言已修复；B 初版 R2 只看 OpenAI choices、协议转换误要求上下文压缩事件已修复。未删除原图片字节检查或允许半截工具执行。

C2 补查首次因指定临时目录的父目录尚未创建，在收集测试前退出；创建本树目录后通过，保留 `validation/behaviour_c2_setup.log`。

## 提交与复核入口

基点 `6deee38c`，分支 `dev/astra-a1r-20261004`。当前提交：

| 提交 | 内容 |
|---|---|
| `a75bda84` | 报告初稿与执行边界 |
| `869707cc` | A 图片引用存档与无损重建 |
| `27fa5d6d` | A 历史体积估算、42 请求与 57 项检查证据 |
| `eb34f968` | B 新线路、记账、恢复、反例；D 配置；R3 协议核对 |
| `c214a42d` | C 四次订阅小测、可恢复证据包与报告更新 |

源码范围为 `src/agent_runtime/`、`src/harness_contracts/`、四个 `src/agent/runtime_*.py` 文件，另有 R3 核对脚本及对应测试。A1-T 工具目录、Agent 版本登记、全局项目目标与交接未改动；没有合入、推送或改写其他工作树文件。主工作树的 `.env` 仅作为用户明确允许的只读凭据来源。

离线复核入口（均在当前树，先创建 `.a1r-tmp` 并设置上述环境）：

```bash
python AI_agent/logs/experiments/2026-10-04_absorb_a1r/validate.py short
python AI_agent/logs/experiments/2026-10-04_absorb_a1r/validate.py long
python AI_agent/logs/experiments/2026-10-04_absorb_a1r/validate.py frozen
python AI_agent/logs/experiments/2026-10-04_absorb_a1r/verify_smoke_evidence.py --scratch .a1r-tmp/smoke-restored-review
python -m src.agent.runtime_r1_preparation check AI_agent/logs/experiments/2026-10-04_absorb_a1r/configs/sm24_anthropic.json
```

B、C 只确认了协议和小请求行为；整案速度、建模质量、长上下文缓存收益尚未验证。本轮没有启动整案，后续由 Opus 接收本分支并按节点安排处理。
