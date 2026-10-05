# C3-R 交付报告

2026-10-05 09:34 UTC 开工，10:59 UTC 验证及临时目录清理完成，11:02 UTC 最终交付，约 89 分钟。Astra；基准 `a5baa32d`，分支 `dev/astra-c3r-20261005`，工作树 `/root/worktrees/astra-c3r`。按 [派工单](brief.md) 与 [验收 A–E](../../../project/unified_agent_acceptance.md#清理包-c3-r底座开销思考回传按实际额度收尾检查全量第二次完整审查后10-05-派出astra) 交付。开工报告已先行提交；只提交本分支，未合入、未推送。

## 当前结果

| 验收 | 结果 |
|---|---|
| A 底座开销 | 检查点复用、显式运行根目录已实现；恢复与 run99 通过；9p 完成只读快照序列计时，完整底座回放只在本机盘做 |
| B 思考回传 | 两种设置已接通；GLM Anthropic 请求保持；51 次 27B A2 请求属于同一连续工具链，因此字符数没有减少 |
| C 实际额度收尾 | 一句显示启用额度，按最紧维度触发原有两条规则；两次 27B 账本反例通过 |
| D 全量检查 | 336 个文件、5539 项完整跑完；5518 过、6 失、2 跳过、13 预期失败；6 失已修复复查 |
| E 范围回归 | 最终有效结果：底座/契约 43 文件 459 项全过，BIM 消费者 34 文件 319 项全过；0 模型请求 |

**0 次模型服务请求，0 次 DeepSeek。** 脚本模型桩、MCP 本地子进程、只读官方文档检索不算模型请求。未读取或打印凭据；外部开发模型自身 token/费用接口不可见，不将底座子请求账本当作全系统账单。

## A：检查点与运行位置

先用真实 run99 冻结重放分阶段计时，再修改。每次检查点复用最近一次已观察的工具状态；每个实际工具执行前、后仍分别取完整快照，恢复仍重新读盘核对。未知写操作仍返回待检查状态，不凭快照推定写入成功，也不自动重做。新检查证明 2 个工具只需初始 1 次及前后 4 次扫描，写前/写后内容与随后检查点一致。

本机盘 run99 的 75 步真实工具、76 次脚本模型响应完整重放：

| 指标 | 改前 | 改后 |
|---|---:|---:|
| 整次重放 | 122.048 s | 130.366 s |
| 检查点数 | 303 | 303 |
| 单检查点中位数（包含日志追加） | 0.071476 s | 0.072168 s |
| 检查点累计（包含其内部工作） | 26.622 s | 27.453 s |
| 运行内完整快照扫描 | 453 次 | 151 次 |
| 事件追加独占累计 | 57.513 s | 63.267 s |
| 上下文投影累计 | 9.308 s | 10.122 s |
| 请求准备累计 | 2.779 s | 3.024 s |
| 建筑上下文更新累计 | 0.444 s | 0.432 s |

计时见 [改前](timing_before.json)、[改后](timing_after.json) 和 [复现脚本](profile_runtime.py)，每个检查点都有原始记录；扫描统计另含 6 次独立目录采样，表中已扣除。本机盘事件追加是主要开销，本包保留其完整验证及落盘要求。两次测量期间还有并行检查负载，**本机盘完整回放没有观察到提速**，不能据扫描次数减少宣称整案更快。

另对经过原清单校验的 27B A2 目录，固定同一份最终 BIM，按其历史全部 238 个检查点及工具前后扫描的顺序做只读回放：

| 文件系统 | 整个快照序列改前 → 改后 | 单检查点中位数改前 → 改后 | 完整扫描次数 |
|---|---:|---:|---:|
| 本机 overlay | 3.918 → 1.485 s | 0.008686 → 0.00001427 s | 404 → 167 |
| 9p | 523.247 → 219.328 s | 1.258265 → 0.00001387 s | 404 → 167 |

两边末尾快照哈希均为 `62d9577289d8a0fe80848e45b739ab3fa94fa9262653300a99de7b6e8397ed19`。原始逐点计时见 [快照序列证据](timing_snapshot_replay.json)、[脚本](replay_snapshots.py)。改后第一个检查点仍需初始化扫描；中位数代表后续复用，不能理解为首次扫描也只需十几微秒。

**计时边界：** 9p 挂载只有主线工作树可用，因此那里只读；上述 9p 总计不含工具执行、日志写入或模型耗时，未完成“9p 上写入运行目录的完整底座回放”。没有为计时写进另一工作树。

新增 `--run-root` / 配置 `run_root`：默认仍在本代码树内，CLI 相对路径仍按启动目录解释，配置相对路径仍按代码树解释；显式根须为绝对路径，输出不能越过选定根，解析符号链接后还会拒绝其他登记工作树和独立 Git 仓库。[27B 待回归配置](configs/qwen27b.json) 已离线验证，运行根为 `/root/bim-agent-runs`，输出 `c3r-qwen27b/sm24_anchor`；没有创建或启动该运行。

## B：思考历史的真实边界

`reasoning_history` 可设 `all` 或 `current_tool_chain`。后者保留同一真实用户轮次中连续的工具调用批次，清除更早已完成轮次的思考字段；工具图片、机器状态不作为新的用户提问。可见正文、工具参数、调用 ID、结果、原始响应和审计历史保留。传出内容经过选择时记录来源转换。GLM Anthropic 不走这层选择，测试对两种设置比较了完整请求字节。

新 27B 配置选 `current_tool_chain`，改回 `all` 即恢复原设置。没有把“一整串工具调用”缩成“最近一个批次”。该历史整案没有新用户轮次，因而 **51 次请求每次的改前/改后字符数均相同**：

| 口径 | 改前 | 改后 |
|---|---:|---:|
| 51 次请求文本累计 | 12,770,364 | 12,770,364 |
| 最后一次请求文本 | 257,373 | 257,373 |
| 51 次请求完整 JSON 累计（含图像 base64） | 46,243,174 | 46,243,174 |
| 最后一次完整 JSON | 460,308 | 460,308 |

逐次结果见 [51 行 CSV](request_characters_after_a2.csv) 与 [完整重建记录](replay_qwen_after_a2.json)。文本口径是紧凑请求 JSON 的 Unicode 字符数，图像 base64 替换为统一占位符；含工具定义及请求参数，不是供应商 token 数，也不是实际费用。本轮只证明机制与字符数，**没有证明 27B 单次长整案的输入减量或质量改善**。若后续要截短同一链中的累计思考，需要另定策略并经节点回归验证。

只读查阅：Qwen 官方 [function calling](https://qwen.readthedocs.io/en/stable/framework/function_call.html) 示例将思考与工具结果留在后续输入；[QwenCloud thinking](https://docs.qwencloud.com/developer-guides/text-generation/thinking) 提醒多轮工具调用省略思考可能降低准确率。文档不能替代对 Paratera 当前 27B 服务模板的验证，本包没有实请求探测。

## C：一句按最紧额度收尾

运行底座在执行工具前，将原账本的保守余额写到该运行的临时状态；工具沿用原尾部提示位置，替换为一句显示已启用的时间、token、USD/CNY 金额及模型/工具调用余额。金额标为估计值；根任务与本任务取更紧余额，保留已承诺/结果未知请求的占用；原额度、预留和硬停止机制没有放大。

原“过半补缺层草稿”和“不足 15% 停止新范围探索、只复核已列严重问题”仍是两条规则，改为最紧维度触发；FINISHING 只修改获派的对应两句。没有启用任何额度的旧入口继续显示原“未启用计时”提示，避免改动 C3-T 的消费者检查。

| 历史运行及最后一次交付工具 | 原提示 | 新提示关键部分 |
|---|---|---|
| A2 后 27B，`event-000756` | 已用 58.9／剩余 41.1 分钟 | 时间 41.0 分钟；token **214,291，3.6%**；模型调用 100、工具调用 218；触发不足15%收尾 |
| 首次 27B，`event-000837` | 已用 63.1／剩余 36.9 分钟 | 时间 36.9 分钟；token **157,097，2.6%**；模型调用 96、工具调用 204；触发不足15%收尾 |

两次历史分别重建 82、96 个实际交付的工具尾部；账本取该工具意图已记账之后、按原执行事件时刻计算，并保持历史模型输入/用量固定。见 [A2 后记录](replay_qwen_after_a2.json)、[首次记录](replay_qwen_initial.json)、[复现脚本](replay_evidence.py)。原两次没有启用金额上限，因此没有凭空显示金额余额；六维分别成为最紧维度的情形均有离线检查。

账本范围明确为 `runtime_managed_requests_only`，外部开发模型自身用量为 `unavailable`。当前桥接落在获派的单模型入口；未修改归 C3-T 的外部协调入口。

## D：11 项旧失败与全量检查

基准确认使用本机工作树中与主线 `a5baa32d` 相同的未修改源码，不在主线目录产生测试文件。6 个文件共 **132 通过、11 失败，84.29 s**，失败项逐一对应审查清单。见 [基准日志](checks/baseline.log)、[XML](checks/baseline.xml)。

| 原失败 | 数量 | 处理及保留的保护 |
|---|---:|---|
| `test_gt_raw_layer` | 5 | 原人工审核 GT 继续明确报 VG 实现漂移；临时测试副本以 `synthetic-offline-test` 身份更新实现指纹、候选内容哈希、清单链及 G10 身份字段；几何不改，先全量重现，再检查单厚度、G6、重复 gate、实现漂移及签名篡改的精确拒绝 |
| `test_gt_facts_staging_sm25` | 2 | 从真实源重建临时事实副本；先断言除转换器指纹外所有字段与旧事实完全相同，再更新空修订账本的内容关联；读写路径的篡改/未签收拒绝保留 |
| `test_tarch_converter_reproducibility` | 1 | 仅纠正“旧转换器豁免意味着整案仍 reproduced”的过时判断；断言 sm25 的独立 VG 漂移必须 fatal，sm24 的转换器漂移也必须 fatal；没有扩展豁免集合 |
| `test_f97_vector_contract` | 1 | 语料改为 Git 跟踪文件，避免扫入并行测试暂存物；9 个试点元数据账本逐文件锁路径/哈希/用途，生产分类器仍须拒绝它们；其他未知矢量仍失败 |
| `test_scripts_bootstrap_lock` | 1 | 撤销每个辅助模块必须具备某种文本写法的断言，改为真实入口跨目录启动并检查实际导入路径；含故意错误入口的反证 |
| `test_affected_tests_map` | 1 | 撤销已退出开发约定的全生产模块映射覆盖门；其余映射工具现存消费者的 14 项行为检查保留 |

原 GT、事实归档和真实人工签名没有改写。两项退役约定在旧 [映射执行报告](../../reviews/execution/2026-07-26_test_speedup_and_affected_map.md) 和 [bootstrap 执行报告](../../reviews/execution/2026-08-25_f94_bootstrap_construction_report.md) 加了明确退役标记，原始历史记录保留。

真实裸脚本入口检查覆盖 `run_bim_agent.py`、`run_stage.py`、`diagnose_source_bim.py`、`gt_from_dxf.py`；viewer 使用 `PYTHONPATH=<本树> python -P -m scripts.tool_scripts.render_geometry_viewer ...` 并实际产出 HTML、执行延迟导入。`-P` 避免当前目录冒充另一个 `src`；这没有宣称任意未配置的裸 viewer 启动都安全。没有为这些检查修改工具脚本。

全量首轮主动停止于 360.67 s：2904 通过、14 失败、15 setup 错误、1 跳过，不计作全量完成。新增问题除未启用额度时的旧提示外，均为旧隔离测试要求暂存目录在其代码根之外，而本次要求所有临时文件留在工作树。现以逐文件校验一致的临时代码副本作为这 11 个旧模块的源根，暂存目录与之相邻，二者都在本树内；真实越界拒绝、复制、合并、manifest 和篡改检查保留。fixture 还先验证原根拒绝树内暂存、再验证副本根仍拒绝其内部目录。生产 isolation 代码未改。

完整全量：**336 个文件，5539 项；5518 passed、6 failed、2 skipped、13 xfailed，1504.23 s（25 分 04 秒）**，`-n 2 -s`，本机盘，TMPDIR/PYTHONPATH/basetemp 都显式指定本树。见 [完整日志](checks/full_final.log) 和 [XML](checks/full_final.xml)。

全量新增 6 失均已处理并复查：

- 3 项 `test_reading_ruler_r1_batchB`：补入同样的隔离源副本 fixture，原 policy 阻断/漂移断言不改。
- 1 项 `test_affected_tests_map`：合法测试消费者已由 9 个增到 13 个，删除过时的数量上限，换成对全部边的“生产代码字符串路径不得指向测试节点”断言；原特定拒绝和不得选入无关 GT 测试仍保留。
- 1 项 `test_orchestrate_baseline`：幂等测试原来把正在变化的 Git 未跟踪文件数量当成相同输入；现在固定实际采集的 Git 元数据输入，仍逐字节比较输出并检验用户编辑保留，生产基线记录逻辑不改。
- 1 项 `test_runtime_r3`：只将两处旧时间文案断言换成新预算句；超时硬停、晚工具拒绝、未保存候选和审计证据断言全部保留。

同次补齐 CLI 相对输出路径的原有 cwd 语义及配置的代码树语义，新增两个边界检查。上述 10 文件复查 **181 passed、1 个原有 xfailed，106.60 s**；额外配置消费者 **7 passed，2.88 s**。未再次重复全量；未改代码/范围的长任务与 run99 复用完整全量的通过结果。最终有效结果并集为 **5526 passed、2 skipped、13 xfailed**（比完整一轮新增 2 项路径检查），剩余失败 0；这不是宣称某一次完整全量全绿。逐项覆盖见 [闭环记录](verification_closure.json)、[各次汇总](validation_summary.json)。2 个 skipped 都需要 live 模型，依 0 请求约束不运行；13 个 xfailed 为原有的 9 个命名基准待重录、3 个隔离 guard 已知缺口、1 个 free-end 证明路径待实现，本包没有新增跳过或预期失败。

## E：验证清单与复现

| 检查 | 已得结果 | 证据 |
|---|---|---|
| 恢复、阶段2长任务、run99、运行根初检 | 27 passed，398.09 s | [a.log](checks/a.log) |
| 两种思考设置、Anthropic 字节保持、六维尾部、登记拒绝、跨目录入口 | 56 passed，10.94 s | [bc_final.log](checks/bc_final.log) |
| BIM 消费者定位（修复前） | 318 passed，1 failed（未启用额度旧提示），131.32 s | [bim_consumers.log](checks/bim_consumers.log) |
| 旧隔离消费者定位 | 505 passed，1 failed（源路径相对性），3 xfailed，76.68 s | [isolation_consumers.log](checks/isolation_consumers.log) |
| 隔离路径修复后整模块 | 322 passed，20.49 s | [isolation_final.log](checks/isolation_final.log) |
| 新 27B 配置读取/参数生成 | 通过，未启动 | [configuration.json](checks/configuration.json) |
| 两份历史压缩包及全部解包文件 | 压缩包哈希及 5983 文件均一致 | [source_evidence.json](source_evidence.json) |
| 完整全量 | 5518 passed、6 failed、2 skipped、13 xfailed，1504.23 s | [full_final.log](checks/full_final.log) |
| 6 失修复及路径兼容，10 文件 | 181 passed、1 原有 xfailed，106.60 s | [final_repairs.log](checks/final_repairs.log) |
| 额外配置消费者 | 7 passed，2.88 s | [subscription_final.log](checks/subscription_final.log) |
| 最终有效结果并集 | 5526 passed、2 skipped、13 xfailed；剩余失败 0 | [verification_closure.json](verification_closure.json) |

最终直接按模块名检索到的 43 个消费者文件已全部纳入完整检查，无未收集文件；其中预算断言的 1 失已在复查中通过。全部底座/契约检查（阶段 0–3、R1–R3、C1、A1-R～A5-R）最终有效 459 项通过，34 个 BIM 消费者文件 319 项通过。

正式 `src/agent_runtime/agent_versions.json` 属于 C3-T，未修改。本包指引/预算改动会使旧正式登记拒绝启动，合并后须由 Opus/C3-T 统一登记共同版本。离线检查用显式、绝对的 `BIM_AGENT_REGISTRY_PATH` 选取临时登记 JSON，仍由原登记器生成并逐文件/目录哈希验证；没有自动登记或跳过检查，默认正式登记位置不变，错哈希/相对路径均有拒绝检查。

复现临时登记与全量的示例（登记器仅启动本地 MCP 读取目录，不调用模型）：

```bash
cd /root/worktrees/astra-c3r
mkdir -p .c3r_validation/tmp
cp src/agent_runtime/agent_versions.json .c3r_validation/agent_versions.json
PYTHONPATH="$PWD" python -m src.agent_runtime.agent_registry register \
  --version c3r-offline-review --registry .c3r_validation/agent_versions.json
TMPDIR="$PWD/.c3r_validation/tmp" PYTHONPATH="$PWD" \
BIM_AGENT_REGISTRY_PATH="$PWD/.c3r_validation/agent_versions.json" \
python -m pytest -n 2 -s --basetemp="$PWD/.c3r_validation/pytest"
```

## 提交与交接边界

- `eb804753`：开工报告。
- `03c9cf8a`：检查点复用、显式运行根、思考配置、额度提示与历史证据。
- `b080ede6`：11 项旧失败的测试修复及旧约定退役标记。
- `40bd682a`：旧隔离测试源副本、未启用额度兼容、9p 快照计时。
- `f77c0c66`：6 项全量失败修复、默认路径兼容及收工报告主体。
- `5be74b24`：检查 XML、验证汇总、来源哈希及最终报告。
- 随后的证据格式提交：补入被全局 `*.log` 忽略的完整日志，并规范化生成证据的行尾空白。

未改 C3-T 的工具返回、工具名表、当前稿选择、协调入口或登记表；仅改获派预算模块和 FINISHING 两句。后续节点实模型回归仍需项目经理按既定流程安排，本包没有代行。临时历史运行和测试目录已全部清理（仅本任务的 `.c3r_tmp`）；保留原证据包来源及哈希、逐请求/逐检查点结果、全部检查日志/XML。生成的日志/XML 仅规范化行尾空白，测试身份、结果及计时属性逐项核对不变；原始与存储哈希见 [capture_format.json](checks/capture_format.json)。
