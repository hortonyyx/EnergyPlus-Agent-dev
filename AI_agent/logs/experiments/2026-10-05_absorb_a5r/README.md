# A5-R：共用输入准备与评价侧约定差

状态：本分支实现与离线证据已交付；**A、C 的入口验证以独立登记建议为条件，默认入口仍待 Opus 集成登记后验收**。派工：Opus 5.5；执行：Astra。模型请求 0 次。

## 范围与交付边界

- 按 [派工单](brief.md) 和 [验收 A–C](../../../project/unified_agent_acceptance.md#吸收包第五批-a5-r两底座共用输入准备评价侧约定差10-05-派出astra) 执行；分支 `dev/astra-a5r-20261005`，基准 `f4d48cf7`。开工初稿已先提交为 `76c4797a`。
- 只在本分支提交，未合入 main、未推送；未改 A5-T 所属工具、指引、命名和版本登记。范围核对见 [scope_audit.json](scope_audit.json)。
- 原始输入、源模型和 GT 未改；历史数据按压缩包和逐文件哈希核验后重评，没有重新生成。解包和检查临时目录位于本工作树。

`run_bim_agent.py` 被 `agent_versions.json` 按整文件哈希登记，提取 `run_experiment` 必然改变该哈希。派工单把登记文件归 A5-T，本分支保持原归属，另在报告目录生成独立登记建议并保留全部哈希和工具目录校验。默认入口的实际阻挡见 `validation/default_registration_check.json`；**不能将条件验证解释为本分支默认入口已可运行**。

## A：两套入口共用输入

`src/agent/bim_inputs.py::prepare_bim_inputs` 是两入口唯一的清单生成与输入冻结实现。保留原 Claude Code 的 PNG、原生网格、用户声明、候选恢复和失败平面恢复行为；时间、楼层范围、输入内容及实现哈希不再各写一份。Claude Code 的运行根目录和新底座的 `bim/` 都是同一种 BIM 工作目录；底座事件、账目等仍在外层。

新底座结束时直接保存 `bim/summary.json`。评价器接受两种入口的运行根目录或 BIM 目录；老底座运行缺少 summary 时直接读已有终态 receipt，不复制目录、不补写 `inputs.json`。旧的清单字段缺项不再阻挡评分。没有修改工具、指引或 `run_experiment` 以外的 Claude Code 入口代码，见 [范围核对](scope_audit.json)。

## B：评价口径与七份重评

约定规则只在评价侧生效，以原参照和独立原图观测的 SHA-256 锁定；目标线来自既有参照线，不能由候选或平均值决定。保留原比较 2 cm 残余误差口径；地坪必须是已记录的首层 0.2 m 门槛、顶标高不变且外门高度能佐证；单线规则只允许记录的半墙厚转换；跨层对齐限相关墙厚内的既有目标线。拆并房、多漏空间/开口、改变门窗挂接或连通、超限位移另行保留，不参与降级。

每份运行同时保存 `reading_readings.json`（所有已保存草稿、读数、原值和哈希，失败及损坏草稿亦保留）与 `delivery_quality.json`（各候选质量及完整子报告链接）。有原编译记录时，对未施加约定差的读数另做严格分区比较。历史运行没有独立的规整前后账本，报告明确写为“未单独记录”，不会根据最后模型反推“模型已经读准”。原始分区的 severe 只表示与照图 GT 的原值有差，不自动等于读错，其中也可能含约定差。报告是所列几何、原图开口位置/挂接/连通和外部高度的诊断；内部高度、竖向空洞等没有据此获验收。

[汇总及逐项差异](reevaluation.json)包含每项改记依据、原严重项、仍保留的严重项、原图位置/挂接/连通读数，以及所有被保护文件重评前后的哈希。压缩包与逐文件核验见 [archive_verification.json](archive_verification.json)。本次无重新生成。

| 历史交付 | 原严格分区 → 约定后分区 | 改记为约定差 | 交付诊断仍保留 |
|---|---|---|---|
| [节点 sm24，新底座](evaluation/sm24_runtime_anthropic/index.html)，candidate_03 | severe → severe | 无 | 7 项边界差、内部隔墙差；开口位置 18/21，3 项位置偏差 |
| [节点 sm25，新底座](evaluation/sm25_runtime_anthropic/index.html)，candidate_07 | severe → severe | 无 | 首层 14 项标高差、29 项边界差、走廊错拆；额外门/窗；位置 48/61、挂接 58/61、门连通 28/30；外部高度 33/34 |
| [27B 首次](evaluation/sm24_qwen27b_paratera/index.html)，candidate_06 | minor → minor | 无 | 原有微小分区差；开口位置 20/21，1 项位置偏差，因此交付诊断仍 severe |
| [27B A2 后](evaluation/sm24_qwen27b_after_a2/index.html)，candidate_01 | severe → severe | 无 | 7 项边界差、内部隔墙差、额外外窗；已有参照开口 21/21 对位不抵消多窗 |
| [Opus 10-01 sm21](evaluation/opus_dev_sm21/index.html)，candidate_04 | pass → pass | 无 | 29/29 开口位置/挂接、14/14 门连通、17/17 外部高度；本报告范围内 pass |
| [Opus 10-01 sm24](evaluation/opus_dev_sm24/index.html)，candidate_02 | severe → pass | 8 个首层空间的 0.2 m 地坪差 | 21/21 开口位置/挂接、10/10 门连通、14/14 外部高度；本报告范围内 pass |
| [Opus 10-01 sm25](evaluation/opus_dev_sm25/index.html)，candidate_04 | severe → minor | 14 个首层地坪差；6 个空间边界半墙厚差（对应两层共 4 段墙）；2 个被这些差异完全覆盖的楼层隔墙汇总项 | 12 项原有微小分区差；61/61 位置/挂接、30/30 门连通、34/34 外部高度；本报告范围内 minor |

七份最终稿均没有实际采用办公室跨层对齐，因此本次没有历史跨层差异被改记。该规则用保存的 sm25 复制数据做离线正反例验证：只将首层既有办公室隔墙对齐至二层既有 16.06 m 线；原历史模型及其 6 cm 接触细条保持原样。本包不把它称为已规整完成。

## C：检查结果与集成依赖

完整范围共 82 个测试文件：保留阶段 0–3、R1–R3、C1、A1-R～A4-R，加入直接引用两入口/新评价模块的文件，以及测试辅助模块的传递引用。清单见 `validation/selected_tests.json`。始终显式使用本树 `PYTHONPATH`、树内 `TMPDIR` / `--basetemp`、`pytest -n 2 -s`。结果见 [effective.json](validation/effective.json)：

| 检查 | 结果 | 证据 |
|---|---|---|
| 默认登记完整检查 | 880 项：830 通过、50 被旧登记阻挡；无其他失败、无跳过 | `validation/all.json`、`.log`、`.xml`；`baseline_failure_causes.json` |
| 相同代码下补验受阻的短检查 | 48/48 通过 | `validation/proposed-failed.json`、`.log`、`.xml` |
| 独立登记下完整历史工具重放文件 | 4/4 通过，覆盖另 2 项受阻检查 | `validation/proposed-frozen.log`、`.xml` |
| 部分推理兼容修正后的全部评分检查 | 23/23 通过，含新增反例 | `validation/judge-compat.log`、`.xml` |
| 去重后的有效检查 | **82 个文件、881 项通过，0 失败、0 跳过；登记依赖仍为条件** | `validation/effective.json` |

完整检查和受阻短检查补验期间，源文件均保持不变；两轮源哈希一致。最后仅改评价脚本及对应测试，所有直接引用该脚本的测试文件已完整重跑，差异哈希写入 `effective.json`。阶段 0–3、R1–R3、C1、A1-R～A4-R 的其余实现未改，复用同代码检查结果。

已用现有登记接口在本报告目录生成 **独立的登记建议文件**，核对四种真实本地 MCP 目录；没有改生产登记，也没有关闭哈希校验。三例核对已通过，见 [runner_parity.json](runner_parity.json)：每例 Claude Code 恰好到达一次被拦截的进程启动边界，未启动模型；任务、指引、工具目录和三份 8.6–8.8 KB 完整输入清单（同范围、同钟表，仅 provider 路由不同）均逐字节一致，新底座均产出可直接评分的 summary。核对脚本只在自己的进程内显式选择该建议登记，结果明确是**以建议登记为条件**，当前默认入口未因此放行。默认校验阻挡的唯一文件为 `run_bim_agent.py`，证据在 `validation/default_registration_check.json`。

为了在不越权修改登记的前提下把集成改动验证完，另备离线 pytest 配置 `proposed_registry_checks.py`，把登记选择指向该建议文件；原校验函数、四种真实工具目录、历史版本和文件篡改断言全部保留。登记复制测试仅改其 JSON 输入来源。补验与原默认登记失败分别保存。75 步历史真实工具重放已在此条件下通过，模型响应均为录制的本地脚本：4 项通过，实际流程 799 秒，75 次工具执行、76 个脚本响应、69 次压缩、3 次旧图片逐字节取回；原有 7 个错误准确复现，无新增错误。见 [frozen_summary.json](validation/frozen_summary.json)、`proposed-frozen.log` / `.xml`；完整报告、事件、回执和版本以 gzip 保存于 `validation/`。这不是一次新的工作模型整案运行。

收尾时修正了部分推理模式的兼容语义：完整参照差异继续保留为诊断，交付质量标为 `not_evaluated`，不把未提供的内部格局变成交付验收目标。复现见 `validation/partial_inference_before.json`；新反例及还原模式检查均通过。这不改变上表七份还原任务重评的结果。

## 交接与提交

唯一的集成后必做项：Opus 合并 A5-R/A5-T 后，按合并后的实际文件与工具目录重新登记共同版本，将 `src/agent/bim_inputs.py` 作为 `task_description` 纳入登记；随后核对默认入口。报告内的独立登记用于本包离线验证，合并后的文件会有新的哈希。

- `76c4797a`：开工报告初稿。
- `0f1f4bb0`：共用输入准备与对应检查。
- `d8747fc4`：约定差、原读数/交付分离及反例。
- `086802f8`：七份重评和三例入口核对证据。
- `b8d6296e`：部分推理参照比较保持诊断性质。

最后的交付记录提交保存本报告、完整检查与清理证据。解包及测试目录清理见 [cleanup.json](cleanup.json)，必要的重放报告/事件/回执/版本已压缩保留。未合入、未推送。

